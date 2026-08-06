#!/usr/bin/env python3
"""Prove private dynamic-metadata parity from one Git-less source authority.

The harness snapshots the exact staged Git index into a read-only, Git-less
source tree and derives its root tree from file bytes and modes.  Native and
container binaries are built in separate writable copies of that same snapshot.
The container receives only the authenticated snapshot and fixtures read-only,
plus one empty writable output root; the completed native plane and live host
repository are never mounted.  Publication uses renameat2 no-replace.
"""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, Callable

RENAME_NOREPLACE = 1
SOURCE_SCHEMA = "x64lens-p077-parity-source-v2"
_TEST_BEFORE_PUBLISH_RENAME_HOOK: Callable[[Path, Path], None] | None = None


class Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Error(message)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def strict_json(raw: str) -> Any:
    return json.loads(raw, object_pairs_hook=strict_pairs)


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def safe(raw: str) -> str:
    path = PurePosixPath(raw)
    require(
        raw
        and not path.is_absolute()
        and path.as_posix() == raw
        and "\\" not in raw
        and all(part not in {"", ".", ".."} for part in path.parts),
        f"unsafe source path: {raw!r}",
    )
    return raw


def parent(raw: str) -> str:
    return "/".join(PurePosixPath(raw).parts[:-1])


def run(argv: list[str], cwd: Path | None = None, timeout: int = 180) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def load_matrix(repo: Path):
    path = repo / "tools/sprint12-search-path-matrix-smoke.py"
    spec = importlib.util.spec_from_file_location("x64lens_search_path_matrix", path)
    require(spec is not None and spec.loader is not None, "cannot load search-path matrix")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git_object(kind: bytes, payload: bytes) -> str:
    return hashlib.sha1(kind + b" " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def derive_tree(files: list[dict[str, Any]], directories: list[str]) -> str:
    directory_set = set(directories)
    all_dirs = {"", *directory_set}
    children: dict[str, list[tuple[str, bool, str, str]]] = {item: [] for item in all_dirs}
    for directory in directory_set:
        require(parent(directory) in all_dirs, f"source directory parent missing: {directory}")
    for item in files:
        path = item["path"]
        require(parent(path) in all_dirs, f"source file parent missing: {path}")
        children[parent(path)].append((PurePosixPath(path).name, False, item["git_mode"], item["git_oid"]))
    for directory in sorted(directory_set, key=lambda item: (-item.count("/"), os.fsencode(item))):
        entries = children[directory]
        require(entries, f"source authority contains an empty Git directory: {directory}")
        payload = b"".join(
            mode.encode("ascii") + b" " + name_bytes + b"\0" + bytes.fromhex(oid)
            for name_bytes, is_directory, mode, oid in sorted(
                ((os.fsencode(name) + (b"/" if is_dir else b""), is_dir, mode, oid)
                 for name, is_dir, mode, oid in entries),
                key=lambda row: row[0],
            )
            for name_bytes in [name_bytes[:-1] if is_directory else name_bytes]
        )
        oid = git_object(b"tree", payload)
        children[parent(directory)].append((PurePosixPath(directory).name, True, "40000", oid))
    root = children[""]
    require(root, "source authority has no root entries")
    payload = b"".join(
        mode.encode("ascii") + b" " + name_bytes + b"\0" + bytes.fromhex(oid)
        for name_bytes, is_directory, mode, oid in sorted(
            ((os.fsencode(name) + (b"/" if is_dir else b""), is_dir, mode, oid)
             for name, is_dir, mode, oid in root),
            key=lambda row: row[0],
        )
        for name_bytes in [name_bytes[:-1] if is_directory else name_bytes]
    )
    return git_object(b"tree", payload)


def index_records(repo: Path) -> tuple[str, list[tuple[str, str, str]]]:
    require(run(["git", "diff", "--quiet", "--"], cwd=repo).returncode == 0,
            "working tree differs from staged source authority")
    tree = run(["git", "write-tree"], cwd=repo)
    require(tree.returncode == 0, "git write-tree failed")
    listing = run(["git", "ls-files", "-s", "-z"], cwd=repo)
    require(listing.returncode == 0, "git ls-files failed")
    rows: list[tuple[str, str, str]] = []
    for raw in listing.stdout.split(b"\0"):
        if not raw:
            continue
        header, path_raw = raw.split(b"\t", 1)
        mode_raw, oid_raw, stage_raw = header.split()
        require(stage_raw == b"0", "non-stage-zero source entry")
        mode = mode_raw.decode("ascii")
        require(mode in {"100644", "100755"}, f"unsupported parity source mode: {mode}")
        rows.append((safe(os.fsdecode(path_raw)), mode, oid_raw.decode("ascii")))
    rows.sort(key=lambda row: os.fsencode(row[0]))
    return tree.stdout.decode().strip(), rows


def create_source_snapshot(repo: Path, root: Path) -> tuple[dict[str, Any], Path]:
    require(not root.exists(), "source snapshot already exists")
    root.mkdir(mode=0o755)
    tree, records = index_records(repo)
    directories = sorted(
        {prefix for path, _mode, _oid in records for prefix in (
            "/".join(PurePosixPath(path).parts[:index])
            for index in range(1, len(PurePosixPath(path).parts))
        ) if prefix},
        key=lambda item: (item.count("/"), os.fsencode(item)),
    )
    for directory in directories:
        target = root / directory
        target.mkdir(mode=0o755)
        target.chmod(0o755)
    files: list[dict[str, Any]] = []
    for path, git_mode, expected_oid in records:
        content = run(["git", "show", f":{path}"], cwd=repo)
        require(content.returncode == 0, f"cannot read staged source blob: {path}")
        observed_oid = git_object(b"blob", content.stdout)
        require(observed_oid == expected_oid, f"staged source blob identity changed: {path}")
        target = root / path
        target.write_bytes(content.stdout)
        transport_mode = 0o555 if git_mode == "100755" else 0o444
        target.chmod(transport_mode)
        files.append({
            "path": path,
            "git_mode": git_mode,
            "git_oid": expected_oid,
            "mode": f"{transport_mode:04o}",
            "sha256": hashlib.sha256(content.stdout).hexdigest(),
            "size_bytes": len(content.stdout),
        })
    for directory in sorted(directories, key=lambda item: -item.count("/")):
        (root / directory).chmod(0o555)
    root.chmod(0o555)
    manifest = {
        "schema": SOURCE_SCHEMA,
        "candidate_tree": tree,
        "directories": directories,
        "files": files,
        "git_metadata_required": False,
    }
    manifest_path = root.parent / "source-manifest.json"
    manifest_path.write_bytes(canonical_json(manifest))
    manifest_path.chmod(0o444)
    verify_source(root, manifest)
    return manifest, manifest_path


def verify_source(root: Path, manifest: dict[str, Any]) -> None:
    require(
        isinstance(manifest, dict)
        and set(manifest) == {"schema", "candidate_tree", "directories", "files", "git_metadata_required"}
        and manifest["schema"] == SOURCE_SCHEMA
        and manifest["git_metadata_required"] is False,
        "source manifest changed",
    )
    directories = manifest["directories"]
    files = manifest["files"]
    require(isinstance(directories, list) and directories == sorted(directories, key=lambda item: (item.count("/"), os.fsencode(item))),
            "source directory authority changed")
    require(isinstance(files, list), "source file authority changed")
    expected_files: set[str] = set()
    expected_directories = set(directories)
    seen_inodes: set[tuple[int, int]] = set()
    for item in files:
        require(isinstance(item, dict) and set(item) == {"path", "git_mode", "git_oid", "mode", "sha256", "size_bytes"},
                "source record changed")
        path = safe(item["path"])
        require(path not in expected_files, f"duplicate source path: {path}")
        expected_files.add(path)
        full = root / path
        metadata = full.lstat()
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1, f"unsafe source member: {path}")
        key = (metadata.st_dev, metadata.st_ino)
        require(key not in seen_inodes, f"source hard-link topology changed: {path}")
        seen_inodes.add(key)
        require(f"{stat.S_IMODE(metadata.st_mode):04o}" == item["mode"], f"source mode changed: {path}")
        digest, size = sha(full)
        require((digest, size) == (item["sha256"], item["size_bytes"]), f"source bytes changed: {path}")
        raw = full.read_bytes()
        require(git_object(b"blob", raw) == item["git_oid"], f"source Git object changed: {path}")
        require((item["git_mode"] == "100755") == bool(metadata.st_mode & 0o111),
                f"source executable mode changed: {path}")
    observed_files: set[str] = set()
    observed_directories: set[str] = set()
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative_root = current_path.relative_to(root)
        for name in dirnames:
            path = current_path / name
            require(not path.is_symlink() and path.is_dir(), f"unsafe source directory: {path}")
            observed_directories.add((relative_root / name).as_posix())
        for name in filenames:
            observed_files.add((relative_root / name).as_posix())
    require(observed_files == expected_files, "source file membership changed")
    require(observed_directories == expected_directories, "source directory membership changed")
    require(derive_tree(files, directories) == manifest["candidate_tree"], "source tree identity changed")


def make_build_copy(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, symlinks=False)
    for current, dirnames, filenames in os.walk(destination, topdown=True, followlinks=False):
        path = Path(current)
        path.chmod(0o755)
        for name in filenames:
            file_path = path / name
            mode = 0o755 if file_path.stat().st_mode & 0o111 else 0o644
            file_path.chmod(mode)
        for name in dirnames:
            (path / name).chmod(0o755)


def build_native(source: Path, destination: Path) -> tuple[Path, Path]:
    make_build_copy(source, destination)
    cp = run(["make", "clean"], cwd=destination, timeout=300)
    require(cp.returncode == 0, f"native parity clean failed: {cp.stderr.decode(errors='replace')[-2000:]}")
    cp = run(["make"], cwd=destination, timeout=900)
    require(cp.returncode == 0, f"native parity build failed: {cp.stderr.decode(errors='replace')[-2000:]}")
    cp = run(["make", "build/tests/dynamic-metadata-fact-probe"], cwd=destination, timeout=300)
    require(cp.returncode == 0, f"native parity probe build failed: {cp.stderr.decode(errors='replace')[-2000:]}")
    return destination / "build/x64lens", destination / "build/tests/dynamic-metadata-fact-probe"


def normalized_stream(command: str, stdout: bytes, target: Path, status: int) -> bytes:
    """Normalize one public stream without inventing output on failure.

    Expected malformed/unsupported gadget and analyze closures are defined by
    their nonzero exit, empty stdout, and normalized stderr.  Empty failure
    output is therefore retained as empty bytes and is never passed to the JSON
    parser.  Successful JSON-producing commands still require one complete
    canonical object.
    """
    marker = os.fsencode(str(target))
    if status != 0:
        require(stdout == b"", f"nonzero {command} outcome emitted partial stdout")
        return b""
    if command in {"gadgets", "analyze"}:
        value = strict_json(stdout.decode("utf-8"))
        require(isinstance(value, dict), "public JSON is not object")
        if isinstance(value.get("target"), dict) and "path" in value["target"]:
            value["target"]["path"] = "<target>"
        return canonical_json(value)
    return stdout.replace(marker, b"<target>")


def build_fixtures(repo: Path, out: Path) -> dict[str, Any]:
    matrix = load_matrix(repo)
    out.mkdir(mode=0o755)
    rows: list[dict[str, Any]] = []
    for case in matrix.CASES:
        built = matrix.build(case)
        target = out / f"{case.name}.elf"
        target.write_bytes(built.image)
        target.chmod(0o444)
        digest, size = sha(target)
        rows.append({"case": case.name, "path": target.name, "sha256": digest, "size_bytes": size, "mode": "0444"})
    manifest = {"schema": "x64lens-p077-parity-fixtures-v1", "count": len(rows), "files": rows}
    (out / "manifest.json").write_bytes(canonical_json(manifest))
    (out / "manifest.json").chmod(0o444)
    return manifest


def verify_fixtures(root: Path, manifest: dict[str, Any]) -> None:
    require(manifest.get("schema") == "x64lens-p077-parity-fixtures-v1" and manifest.get("count") == 36,
            "fixture manifest changed")
    for item in manifest["files"]:
        target = root / item["path"]
        metadata = target.lstat()
        require(stat.S_ISREG(metadata.st_mode) and stat.S_IMODE(metadata.st_mode) == 0o444 and metadata.st_nlink == 1,
                f"fixture mode/type changed: {item['path']}")
        require(sha(target) == (item["sha256"], item["size_bytes"]), f"fixture bytes changed: {item['path']}")


def execute_plane(
    repo: Path,
    source_root: Path,
    source_path: Path,
    fixtures: Path,
    result: Path,
    analyzer: Path,
    probe: Path,
    schema: Path,
    authority: Path,
    plane_id: str,
) -> dict[str, Any]:
    require(not result.exists(), "plane result already exists")
    result.mkdir(mode=0o755)
    source = strict_json(source_path.read_text())
    verify_source(source_root, source)
    fixture_manifest = strict_json((fixtures / "manifest.json").read_text())
    verify_fixtures(fixtures, fixture_manifest)
    matrix = load_matrix(repo)
    matrix.load_authority(authority)
    matrix.load_schema(schema)
    for binary, label in ((analyzer, "analyzer"), (probe, "fact_probe"), (schema, "schema"), (authority, "authority")):
        require(binary.is_file() and not binary.is_symlink(), f"missing {label}")
    identities: dict[str, Any] = {}
    for binary, label in (
        (analyzer, "analyzer"),
        (probe, "fact_probe"),
        (schema, "schema"),
        (authority, "authority"),
        (source_path, "source_manifest"),
        (fixtures / "manifest.json", "fixture_manifest"),
    ):
        digest, size = sha(binary)
        identities[label] = {
            "path": str(binary),
            "sha256": digest,
            "size_bytes": size,
            "mode": f"{stat.S_IMODE(binary.stat().st_mode):04o}",
        }
    rows: list[dict[str, Any]] = []
    private_cells = 0
    public_cells = 0
    cases = {case.name: case for case in matrix.CASES}
    for item in fixture_manifest["files"]:
        case = cases[item["case"]]
        target = fixtures / item["path"]
        built = matrix.build(case)
        proc = run([str(probe), str(target)])
        require(proc.returncode == 0, f"{plane_id} probe process failed: {case.name}")
        matrix.validate_probe(case, built, proc.stdout)
        facts = strict_json(proc.stdout.decode())
        private_cells += len(matrix.PROBE_KEYS) - 1 + sum(len(record) for record in facts["paths"])
        normalized_private = canonical_json(facts)
        rows.append({
            "case": case.name,
            "surface": "private",
            "status": facts["status"],
            "normalized_sha256": hashlib.sha256(normalized_private).hexdigest(),
            "normalized_size": len(normalized_private),
            "facts": facts,
        })
        for command in matrix.COMMANDS:
            argv = [str(analyzer), command]
            if command in ("gadgets", "analyze"):
                argv += ["--format", "json", "--max-depth", "4"]
            argv.append(str(target))
            cp = run(argv)
            expected = 0 if command == "info" or case.expected_status == 0 else case.expected_status
            require(cp.returncode == expected, f"{plane_id} public exit mismatch {case.name}/{command}")
            require(expected == 0 or not cp.stdout, f"{plane_id} partial stdout {case.name}/{command}")
            normalized = normalized_stream(command, cp.stdout, target, cp.returncode)
            rows.append({
                "case": case.name,
                "surface": command,
                "status": cp.returncode,
                "normalized_sha256": hashlib.sha256(normalized).hexdigest(),
                "normalized_size": len(normalized),
                "stderr_sha256": hashlib.sha256(cp.stderr.replace(os.fsencode(str(target)), b"<target>")).hexdigest(),
                "stderr_size": len(cp.stderr),
            })
            public_cells += 1
    manifest = {
        "schema": "x64lens-p077-dynamic-parity-plane-v1",
        "plane": plane_id,
        "source_tree": source["candidate_tree"],
        "objects": 36,
        "private_processes": 36,
        "public_processes": 144,
        "private_field_cells": private_cells,
        "public_closures": public_cells,
        "identities": identities,
        "rows": rows,
    }
    verify_source(source_root, source)
    (result / "manifest.json").write_bytes(canonical_json(manifest))
    (result / "manifest.json").chmod(0o444)
    return manifest


def compare(native: dict[str, Any], container: dict[str, Any], out: Path) -> dict[str, Any]:
    require(native["source_tree"] == container["source_tree"], "plane source trees differ")
    native_rows = {(row["case"], row["surface"]): row for row in native["rows"]}
    container_rows = {(row["case"], row["surface"]): row for row in container["rows"]}
    require(set(native_rows) == set(container_rows), "plane row membership differs")
    mismatches: list[dict[str, str]] = []
    private = public = 0
    for key in sorted(native_rows):
        left = native_rows[key]
        right = container_rows[key]
        fields = ("status", "normalized_sha256", "normalized_size") if key[1] == "private" else (
            "status", "normalized_sha256", "normalized_size", "stderr_sha256", "stderr_size"
        )
        if any(left[field] != right[field] for field in fields):
            mismatches.append({"case": key[0], "surface": key[1]})
        if key[1] == "private":
            private += 1
        else:
            public += 1
    require(not mismatches, f"native/container dynamic parity mismatch: {mismatches[:8]}")
    result = {
        "schema": "x64lens-p077-dynamic-parity-comparison-v1",
        "source_tree": native["source_tree"],
        "objects": 36,
        "private_records_compared": private,
        "public_closures_compared": public,
        "mismatches": 0,
        "native_analyzer_sha256": native["identities"]["analyzer"]["sha256"],
        "container_analyzer_sha256": container["identities"]["analyzer"]["sha256"],
        "native_probe_sha256": native["identities"]["fact_probe"]["sha256"],
        "container_probe_sha256": container["identities"]["fact_probe"]["sha256"],
        "separate_build_origins": True,
        "native_plane_mounted_into_container": False,
        "live_repository_mounted_into_container": False,
    }
    out.write_bytes(canonical_json(result))
    out.chmod(0o444)
    return result


def rename_noreplace(source: Path, destination: Path) -> None:
    """Publish no-replace and prove the caller-visible destination binding.

    The source object and parent directory are retained by descriptor across the
    test hook and rename.  After publication the caller-visible parent is
    reopened and must still name the retained directory; the destination must
    resolve to the retained source inode.  A parent replacement may leave an
    authenticated result in the detached original directory, but it can no
    longer be reported as success at the requested path.
    """
    require(source.parent == destination.parent, "parity publication must remain in one parent")
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    require(function is not None, "renameat2 is unavailable on this Linux runtime")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    parent_fd = os.open(source.parent, flags)
    source_fd = os.open(source.name, flags, dir_fd=parent_fd)
    parent_identity = os.fstat(parent_fd)
    source_identity = os.fstat(source_fd)
    try:
        if _TEST_BEFORE_PUBLISH_RENAME_HOOK is not None:
            _TEST_BEFORE_PUBLISH_RENAME_HOOK(source, destination)
        if function(parent_fd, os.fsencode(source.name), parent_fd, os.fsencode(destination.name), RENAME_NOREPLACE) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), destination.name)
        os.fsync(parent_fd)
        visible_parent = os.open(source.parent, flags)
        try:
            current_parent = os.fstat(visible_parent)
            require(
                (current_parent.st_dev, current_parent.st_ino, stat.S_IFMT(current_parent.st_mode))
                == (parent_identity.st_dev, parent_identity.st_ino, stat.S_IFMT(parent_identity.st_mode)),
                "result parent binding changed during publication",
            )
            visible_result = os.open(destination.name, flags, dir_fd=visible_parent)
            try:
                current_result = os.fstat(visible_result)
                require(
                    (current_result.st_dev, current_result.st_ino, stat.S_IFMT(current_result.st_mode))
                    == (source_identity.st_dev, source_identity.st_ino, stat.S_IFMT(source_identity.st_mode)),
                    "caller-visible parity result is not the published object",
                )
            finally:
                os.close(visible_result)
        finally:
            os.close(visible_parent)
    finally:
        os.close(source_fd)
        os.close(parent_fd)


def publish(stage: Path, destination: Path) -> None:
    rename_noreplace(stage, destination)


def command_run(ns: argparse.Namespace) -> int:
    repo = Path(os.path.abspath(ns.repo))
    destination = Path(os.path.abspath(ns.result_dir))
    require(destination.parent.is_dir() and not destination.parent.is_symlink(), "result parent missing or linked")
    with tempfile.TemporaryDirectory(prefix="x64lens-p077-parity-", dir=destination.parent) as raw:
        work = Path(raw)
        source_root = work / "source"
        source, source_path = create_source_snapshot(repo, source_root)
        authority_root = work / "authority"
        authority_root.mkdir(mode=0o755)
        authority_source = authority_root / "source-manifest.json"
        shutil.copy2(source_path, authority_source)
        authority_source.chmod(0o444)
        authority_root.chmod(0o555)

        fixtures = work / "fixtures"
        build_fixtures(repo, fixtures)
        fixtures.chmod(0o555)
        native_build = work / "native-build"
        native_analyzer, native_probe = build_native(source_root, native_build)
        native_dir = work / "native"
        native = execute_plane(
            native_build,
            source_root,
            authority_source,
            fixtures,
            native_dir,
            native_analyzer,
            native_probe,
            source_root / "schemas/x64lens-report.schema.json",
            source_root / "benchmarks/task-definitions/sprint12-search-path-private-evidence-v1.json",
            "native",
        )

        container_output = work / "container-output"
        container_output.mkdir(mode=0o777)
        os.chmod(container_output, 0o777)
        docker_script = (
            "set -euo pipefail; "
            "python3 /source/tools/sprint12-dynamic-metadata-environment-parity-smoke.py verify-source "
            "--root /source --manifest /authority/source-manifest.json; "
            "rm -rf /x64lens-build/repo; cp -a /source /x64lens-build/repo; "
            "chmod -R u+rwX /x64lens-build/repo; cd /x64lens-build/repo; "
            "make clean; make; make build/tests/dynamic-metadata-fact-probe; "
            "python3 tools/sprint12-dynamic-metadata-environment-parity-smoke.py plane "
            "--repo /x64lens-build/repo --source-root /source "
            "--source-manifest /authority/source-manifest.json --fixtures /inputs "
            "--result /output/container --analyzer /x64lens-build/repo/build/x64lens "
            "--fact-probe /x64lens-build/repo/build/tests/dynamic-metadata-fact-probe "
            "--schema /source/schemas/x64lens-report.schema.json "
            "--authority /source/benchmarks/task-definitions/sprint12-search-path-private-evidence-v1.json "
            "--plane-id container; "
            "python3 /source/tools/sprint12-dynamic-metadata-environment-parity-smoke.py verify-source "
            "--root /source --manifest /authority/source-manifest.json"
        )
        docker_cmd = [
            ns.docker,
            "run",
            "--rm",
            "--tmpfs",
            "/x64lens-build:rw,exec,nosuid,nodev,size=512m",
            "-v",
            f"{source_root}:/source:ro",
            "-v",
            f"{fixtures}:/inputs:ro",
            "-v",
            f"{authority_source}:/authority/source-manifest.json:ro",
            "-v",
            f"{container_output}:/output:rw",
            ns.docker_image,
            "bash",
            "-lc",
            docker_script,
        ]
        cp = run(docker_cmd, timeout=1200)
        require(cp.returncode == 0, f"Docker dynamic parity failed: {cp.stderr.decode(errors='replace')[-3000:]}")
        container = strict_json((container_output / "container/manifest.json").read_text())
        compare(native, container, work / "comparison.json")
        verify_source(source_root, source)

        stage = destination.parent / f".{destination.name}.staging.{os.getpid()}.{os.urandom(16).hex()}"
        require(not stage.exists(), "staging result exists")
        stage.mkdir(mode=0o755)
        shutil.copytree(native_dir, stage / "native")
        shutil.copytree(container_output / "container", stage / "container")
        shutil.copy2(work / "comparison.json", stage / "comparison.json")
        shutil.copy2(authority_source, stage / "source-manifest.json")
        shutil.copytree(fixtures, stage / "fixtures")
        manifest = {
            "schema": "x64lens-p077-dynamic-parity-result-v1",
            "source_tree": source["candidate_tree"],
            "objects": 36,
            "private_records_compared": 36,
            "public_closures_compared": 144,
            "mismatches": 0,
            "native_plane_mounted_into_container": False,
            "live_repository_mounted_into_container": False,
            "container_writable_roots": 1,
            "comparison_sha256": sha(stage / "comparison.json")[0],
        }
        (stage / "manifest.json").write_bytes(canonical_json(manifest))
        (stage / "manifest.json").chmod(0o444)
        publish(stage, destination)
    print(
        "sprint12-dynamic-metadata-environment-parity-smoke: ok "
        "objects=36 private_records=36 public_closures=144 mismatches=0 "
        "separate_build_origins=1 native_plane_mounted=0 live_repo_mounted=0 "
        f"result={destination}"
    )
    return 0


def command_plane(ns: argparse.Namespace) -> int:
    execute_plane(
        Path(ns.repo),
        Path(ns.source_root),
        Path(ns.source_manifest),
        Path(ns.fixtures),
        Path(ns.result),
        Path(ns.analyzer),
        Path(ns.fact_probe),
        Path(ns.schema),
        Path(ns.authority),
        ns.plane_id,
    )
    return 0


def command_verify_source(ns: argparse.Namespace) -> int:
    source_root = Path(ns.root)
    source = strict_json(Path(ns.manifest).read_text())
    verify_source(source_root, source)
    print("p077-parity-source-verify: ok git_metadata_required=0")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--repo", default=".")
    run_parser.add_argument("--authority", required=True)  # retained CLI compatibility; source authority selects exact path
    run_parser.add_argument("--analyzer")  # retained compatibility; native plane rebuilds separately
    run_parser.add_argument("--fact-probe")
    run_parser.add_argument("--schema")
    run_parser.add_argument("--docker", default="docker")
    run_parser.add_argument("--docker-image", required=True)
    run_parser.add_argument("--result-dir", required=True)
    plane = sub.add_parser("plane")
    plane.add_argument("--repo", required=True)
    plane.add_argument("--source-root", required=True)
    plane.add_argument("--source-manifest", required=True)
    plane.add_argument("--fixtures", required=True)
    plane.add_argument("--result", required=True)
    plane.add_argument("--analyzer", required=True)
    plane.add_argument("--fact-probe", required=True)
    plane.add_argument("--schema", required=True)
    plane.add_argument("--authority", required=True)
    plane.add_argument("--plane-id", required=True)
    verify = sub.add_parser("verify-source")
    verify.add_argument("--root", required=True)
    verify.add_argument("--manifest", required=True)
    args = parser.parse_args()
    return {"run": command_run, "plane": command_plane, "verify-source": command_verify_source}[args.cmd](args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Error, OSError, subprocess.TimeoutExpired, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"sprint12-dynamic-metadata-environment-parity-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
