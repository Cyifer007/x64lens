#!/usr/bin/env python3
"""Prove independently built native/container private role/property parity.

One exact staged Git tree is materialized as a Git-less source authority.  The
native analyzer/probe and container analyzer/probe are built independently from
that tree.  The container image is bound by immutable image ID plus candidate-
tree label; it receives only the authenticated held-out objects read-only and
one dedicated empty output root.  The live repository, host binaries, source
snapshot, and completed native plane are never mounted into the container.

Each plane records 288 private-probe executions, 5,184 private field cells, and
384 public command closures.  Comparison preserves separate build identities
while requiring exact facts and normalized public-output agreement.  This gate
does not expose private fields or authorize public PIE/DSO, IBT, or SHSTK policy.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACT_FIELDS = (
    "status", "phnum", "role_state", "role_evidence", "interp_count",
    "flags1_count", "soname_count", "property_view_count",
    "property_contributor_count", "property_note_count",
    "property_feature_count", "property_feature_and", "property_feature_or",
    "property_unknown_count", "property_conflict_count",
    "property_overlap_count", "ibt_state", "shstk_state",
)


class ParityError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ParityError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def identity(path: Path, label: str, *, executable: bool = False) -> dict[str, Any]:
    requested = Path(os.path.abspath(path))
    require(not requested.is_symlink(), f"{label} may not be a symlink: {requested}")
    resolved = requested.resolve(strict=True)
    metadata = resolved.stat()
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file: {resolved}")
    if executable:
        require(os.access(resolved, os.X_OK), f"{label} is not executable: {resolved}")
    data = resolved.read_bytes()
    return {
        "path": str(resolved),
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }


def run(
    command: list[str],
    *,
    timeout: float = 30.0,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
        env={**os.environ, "LC_ALL": "C", "LANG": "C", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1"},
    )


CHECKSUM_NAME = "SHA256SUMS.txt"
TREE_MANIFEST_NAME = "TREE_CUSTODY.json"
TREE_FORMAT = "x64lens-parity-tree-custody-v1"
O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def safe_relative(raw: str) -> str:
    pure = PurePosixPath(raw)
    require(raw and not pure.is_absolute() and all(part not in {"", ".", ".."} for part in pure.parts),
            f"unsafe parity tree path: {raw!r}")
    require(pure.as_posix() == raw and "\\" not in raw, f"noncanonical parity tree path: {raw!r}")
    return raw


def hash_regular(path: Path, relative: str) -> tuple[str, int, os.stat_result]:
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode), f"non-regular parity member: {relative}")
    require(before.st_nlink == 1, f"hard-linked parity member: {relative}")
    fd = os.open(path, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        identity_fields = lambda item: (
            item.st_dev, item.st_ino, stat.S_IFMT(item.st_mode), stat.S_IMODE(item.st_mode),
            item.st_size, item.st_mtime_ns, item.st_ctime_ns, item.st_nlink,
        )
        require(identity_fields(before) == identity_fields(opened), f"parity member changed while opening: {relative}")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
        post_fd = os.fstat(fd)
        post_path = path.lstat()
        require(identity_fields(opened) == identity_fields(post_fd) == identity_fields(post_path),
                f"parity member changed while hashing: {relative}")
        require(total == opened.st_size, f"parity member size changed: {relative}")
        return digest.hexdigest(), total, opened
    finally:
        os.close(fd)


def tree_snapshot(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    root_meta = root.lstat()
    require(stat.S_ISDIR(root_meta.st_mode) and not root.is_symlink(), f"parity tree is not a real directory: {root}")
    directories: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = {(root_meta.st_dev, root_meta.st_ino)}
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = safe_relative(path.relative_to(root).as_posix())
        metadata = path.lstat()
        key = (metadata.st_dev, metadata.st_ino)
        require(key not in seen, f"duplicate parity inode topology: {relative}")
        seen.add(key)
        if stat.S_ISDIR(metadata.st_mode):
            require(not path.is_symlink(), f"parity tree contains a directory link: {relative}")
            directories.append({"path": relative, "mode": f"{stat.S_IMODE(metadata.st_mode):04o}"})
        elif stat.S_ISREG(metadata.st_mode):
            digest, size, opened = hash_regular(path, relative)
            files.append({
                "path": relative,
                "sha256": digest,
                "size_bytes": size,
                "mode": f"{stat.S_IMODE(opened.st_mode):04o}",
                "nlink": opened.st_nlink,
            })
        else:
            raise ParityError(f"parity tree contains a link or special member: {relative}")
    return directories, files


def verify_legacy_checksums(root: Path) -> None:
    """Authenticate one upstream held-out result before parity-owned resealing."""
    manifest = root / CHECKSUM_NAME
    require(manifest.is_file() and not manifest.is_symlink(), f"legacy checksum manifest missing: {root}")
    listed: set[str] = set()
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        require(len(line) >= 67 and line[64:66] == "  " and re.fullmatch(r"[0-9a-f]{64}", line[:64]),
                f"invalid legacy checksum line {number}: {root}")
        name = safe_relative(line[66:])
        require(name not in listed and name != CHECKSUM_NAME, f"duplicate legacy checksum path: {name}")
        path = root / name
        digest, _size, _metadata = hash_regular(path, name)
        require(digest == line[:64], f"legacy checksum mismatch: {name}")
        listed.add(name)
    _directories, files = tree_snapshot(root)
    actual = {item["path"] for item in files if item["path"] != CHECKSUM_NAME}
    require(actual == listed,
            f"legacy checksum membership mismatch: missing={sorted(listed-actual)} extra={sorted(actual-listed)}")


def unseal_for_reseal(root: Path) -> None:
    metadata = root.lstat()
    require(stat.S_ISDIR(metadata.st_mode) and not root.is_symlink(), "parity reseal root is unsafe")
    root.chmod(0o700)
    for path in sorted(root.rglob("*")):
        current = path.lstat()
        require(not path.is_symlink() and (stat.S_ISDIR(current.st_mode) or stat.S_ISREG(current.st_mode)),
                f"parity reseal member is unsafe: {path}")
        if stat.S_ISDIR(current.st_mode):
            path.chmod(0o700)
    for name in (CHECKSUM_NAME, TREE_MANIFEST_NAME):
        control = root / name
        if control.exists():
            require(control.is_file() and not control.is_symlink(), f"unsafe parity control member: {name}")
            control.chmod(0o600)
            control.unlink()


def seal_tree(root: Path) -> None:
    """Seal one exact parity tree while preserving executable input modes."""
    require(not (root / CHECKSUM_NAME).exists() and not (root / TREE_MANIFEST_NAME).exists(),
            f"parity tree is already sealed: {root}")
    directories, files = tree_snapshot(root)
    payload_files = [item for item in files]
    final_directories = [{"path": item["path"], "mode": "0555"} for item in directories]
    final_files = []
    for item in payload_files:
        final_mode = "0555" if int(item["mode"], 8) & 0o111 else "0444"
        final_files.append({"path": item["path"], "mode": final_mode, "nlink": 1})
    final_files.extend([
        {"path": CHECKSUM_NAME, "mode": "0444", "nlink": 1},
        {"path": TREE_MANIFEST_NAME, "mode": "0444", "nlink": 1},
    ])
    final_files.sort(key=lambda item: item["path"])
    tree_manifest = {
        "format": TREE_FORMAT,
        "root_mode": "0555",
        "directories": final_directories,
        "files": final_files,
    }
    (root / TREE_MANIFEST_NAME).write_text(
        json.dumps(tree_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksummed = payload_files + [{
        "path": TREE_MANIFEST_NAME,
        "sha256": sha256_bytes((root / TREE_MANIFEST_NAME).read_bytes()),
    }]
    (root / CHECKSUM_NAME).write_text(
        "".join(f"{item['sha256']}  {item['path']}\n" for item in sorted(checksummed, key=lambda row: row["path"])),
        encoding="utf-8",
    )
    for item in final_files:
        (root / item["path"]).chmod(int(item["mode"], 8))
    for item in reversed(final_directories):
        (root / item["path"]).chmod(0o555)
    root.chmod(0o555)
    verify_checksums(root)


def verify_checksums(root: Path) -> None:
    root_meta = root.lstat()
    require(stat.S_ISDIR(root_meta.st_mode) and not root.is_symlink(), f"parity tree is unavailable: {root}")
    require(stat.S_IMODE(root_meta.st_mode) == 0o555, f"parity tree root mode changed: {root}")
    manifest_path = root / TREE_MANIFEST_NAME
    checksum_path = root / CHECKSUM_NAME
    require(manifest_path.is_file() and not manifest_path.is_symlink(), f"parity tree manifest missing: {root}")
    require(checksum_path.is_file() and not checksum_path.is_symlink(), f"checksum manifest missing: {root}")
    value = load_json(manifest_path)
    require(isinstance(value, dict) and set(value) == {"format", "root_mode", "directories", "files"},
            "parity tree manifest fields changed")
    require(value["format"] == TREE_FORMAT and value["root_mode"] == "0555",
            "parity tree manifest identity changed")
    expected_directories = value["directories"]
    expected_files = value["files"]
    require(isinstance(expected_directories, list) and isinstance(expected_files, list),
            "parity tree manifest collections changed")
    for item in expected_directories:
        require(isinstance(item, dict) and set(item) == {"path", "mode"}
                and safe_relative(item["path"]) == item["path"] and item["mode"] == "0555",
                "invalid parity directory record")
    for item in expected_files:
        require(isinstance(item, dict) and set(item) == {"path", "mode", "nlink"}
                and safe_relative(item["path"]) == item["path"]
                and item["mode"] in {"0444", "0555"}
                and type(item["nlink"]) is int and item["nlink"] == 1,
                "invalid parity file record")
    dir_paths = [item["path"] for item in expected_directories]
    file_paths = [item["path"] for item in expected_files]
    require(dir_paths == sorted(dir_paths) and len(dir_paths) == len(set(dir_paths)),
            "parity directory paths changed")
    require(file_paths == sorted(file_paths) and len(file_paths) == len(set(file_paths)),
            "parity file paths changed")
    require({CHECKSUM_NAME, TREE_MANIFEST_NAME}.issubset(file_paths), "parity control files are undeclared")

    observed_directories, observed_files = tree_snapshot(root)
    observed_dir_modes = [{"path": item["path"], "mode": item["mode"]} for item in observed_directories]
    observed_file_modes = [{"path": item["path"], "mode": item["mode"], "nlink": item["nlink"]}
                           for item in observed_files]
    require(observed_dir_modes == expected_directories, "parity directory membership or modes changed")
    require(observed_file_modes == expected_files, "parity file membership, modes, or topology changed")

    listed: set[str] = set()
    for number, line in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), 1):
        require(len(line) >= 67 and line[64:66] == "  " and re.fullmatch(r"[0-9a-f]{64}", line[:64]),
                f"invalid checksum line {number}: {root}")
        name = safe_relative(line[66:])
        require(name not in listed and name != CHECKSUM_NAME, f"duplicate checksum path: {name}")
        path = root / name
        digest, _size, _metadata = hash_regular(path, name)
        require(digest == line[:64], f"checksum mismatch: {name}")
        listed.add(name)
    actual = {item["path"] for item in observed_files if item["path"] != CHECKSUM_NAME}
    require(actual == listed,
            f"checksum membership mismatch: missing={sorted(listed-actual)} extra={sorted(actual-listed)}")


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def normalize_output(value: bytes, target: Path) -> bytes:
    replacements = {
        os.fsencode(str(target)),
        os.fsencode(str(target.resolve(strict=True))),
    }
    result = value
    for item in sorted(replacements, key=len, reverse=True):
        result = result.replace(item, b"<TARGET>")
    return result


def probe_once(probe: Path, target: Path) -> tuple[subprocess.CompletedProcess[bytes], dict[str, int]]:
    cp = run([str(probe), str(target)], timeout=20.0)
    require(cp.returncode == 0, f"private fact probe returned {cp.returncode}: {target.name}\n{cp.stderr[:500]!r}")
    value = json.loads(cp.stdout, object_pairs_hook=strict_object)
    require(isinstance(value, dict) and tuple(value) == FACT_FIELDS,
            f"private fact probe shape changed: {target.name}")
    require(all(isinstance(value[field], int) for field in FACT_FIELDS),
            f"private fact probe emitted noninteger facts: {target.name}")
    return cp, {field: int(value[field]) for field in FACT_FIELDS}


def plane(args: argparse.Namespace) -> int:
    require(args.execution_stratum in {"native", "container", "logic-only"},
            "execution stratum must be native, container, or logic-only")
    heldout_root = args.heldout_result.resolve(strict=True)
    readelf_mod = load_module("p072_parity_readelf", ROOT / "tools/sprint12-role-property-readelf-smoke.py")
    heldout_mod = load_module("p072_parity_heldout", ROOT / "tools/sprint12-role-property-heldout-smoke.py")
    manifest, source_rows, heldout_identity = readelf_mod.load_heldout(heldout_root)
    require(tuple(heldout_mod.FACT_FIELDS) == FACT_FIELDS, "held-out private fact fields changed")
    harness_identity = identity(Path(__file__), "environment parity harness", executable=True)
    analyzer_identity = identity(args.analyzer, "analyzer", executable=True)
    probe_identity = identity(args.fact_probe, "private fact probe", executable=True)
    schema_identity = identity(args.schema, "public schema")
    schema = load_json(args.schema)
    require(isinstance(schema, dict) and schema.get("$schema"), "public schema is malformed")

    result = Path(os.path.abspath(args.result_dir))
    require(not result.exists(), f"environment plane already exists: {result}")
    result.mkdir(parents=True)
    probe_root = result / "probe"
    public_root = result / "public"
    probe_root.mkdir()
    public_root.mkdir()
    object_rows: list[dict[str, Any]] = []
    probe_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []

    for source_row in source_rows:
        name = source_row["name"]
        target = heldout_root / "objects" / name
        require(target.is_file() and not target.is_symlink(), f"held-out object missing: {name}")
        target_identity = identity(target, f"held-out object {name}")
        expected = {field: int(source_row[f"expected_{field}"]) for field in FACT_FIELDS}
        retained_observed = {field: int(source_row[f"observed_{field}"]) for field in FACT_FIELDS}
        require(expected == retained_observed, f"held-out source result has expected/observed drift: {name}")
        object_rows.append({
            "object": name,
            "sha256": target_identity["sha256"],
            "size_bytes": target_identity["size_bytes"],
            "source_stratum": source_row["stratum"],
            "source_family": source_row["family"],
        })

        target_probe = probe_root / name
        target_probe.mkdir()
        repeat_bytes: list[bytes] = []
        for repeat in range(3):
            cp, observed = probe_once(args.fact_probe, target)
            require(observed == expected, f"private fact mismatch: {args.environment_id}/{name}/repeat-{repeat}")
            repeat_bytes.append(cp.stdout)
            (target_probe / f"repeat-{repeat}.stdout").write_bytes(cp.stdout)
            (target_probe / f"repeat-{repeat}.stderr").write_bytes(cp.stderr)
            probe_rows.append({
                "environment_id": args.environment_id,
                "execution_stratum": args.execution_stratum,
                "object": name,
                "repeat": repeat,
                "exit_code": cp.returncode,
                "stdout_sha256": sha256_bytes(cp.stdout),
                "stderr_sha256": sha256_bytes(cp.stderr),
                "stdout_size": len(cp.stdout),
                "stderr_size": len(cp.stderr),
            })
            for field in FACT_FIELDS:
                private_rows.append({
                    "environment_id": args.environment_id,
                    "object": name,
                    "repeat": repeat,
                    "field": field,
                    "expected": expected[field],
                    "observed": observed[field],
                    "match": int(expected[field] == observed[field]),
                })
        require(repeat_bytes[0] == repeat_bytes[1] == repeat_bytes[2],
                f"private fact probe is nondeterministic: {args.environment_id}/{name}")

        public = heldout_mod.public_commands(args.analyzer, target, expected, schema)
        target_public = public_root / name
        target_public.mkdir()
        for record in public:
            command_id = record["command_id"]
            normalized_stdout = normalize_output(record["stdout"], target)
            normalized_stderr = normalize_output(record["stderr"], target)
            (target_public / f"{command_id}.stdout").write_bytes(record["stdout"])
            (target_public / f"{command_id}.stderr").write_bytes(record["stderr"])
            metadata = {key: value for key, value in record.items() if key not in {"stdout", "stderr"}}
            metadata.update({
                "normalized_stdout_sha256": sha256_bytes(normalized_stdout),
                "normalized_stderr_sha256": sha256_bytes(normalized_stderr),
                "replay_target": f"objects/{name}",
            })
            (target_public / f"{command_id}.json").write_text(
                json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            public_rows.append({
                "environment_id": args.environment_id,
                "execution_stratum": args.execution_stratum,
                "object": name,
                "command_id": command_id,
                "exit_code": record["exit_code"],
                "stdout_sha256": record["stdout_sha256"],
                "stderr_sha256": record["stderr_sha256"],
                "normalized_stdout_sha256": sha256_bytes(normalized_stdout),
                "normalized_stderr_sha256": sha256_bytes(normalized_stderr),
            })

    write_tsv(result / "objects.tsv", object_rows,
              ["object", "sha256", "size_bytes", "source_stratum", "source_family"])
    write_tsv(result / "probe-runs.tsv", probe_rows,
              ["environment_id", "execution_stratum", "object", "repeat", "exit_code",
               "stdout_sha256", "stderr_sha256", "stdout_size", "stderr_size"])
    write_tsv(result / "private-fields.tsv", private_rows,
              ["environment_id", "object", "repeat", "field", "expected", "observed", "match"])
    write_tsv(result / "public-commands.tsv", public_rows,
              ["environment_id", "execution_stratum", "object", "command_id", "exit_code",
               "stdout_sha256", "stderr_sha256", "normalized_stdout_sha256", "normalized_stderr_sha256"])

    require(len(object_rows) == 96, "environment plane object denominator changed")
    require(len(probe_rows) == 288, "environment plane probe denominator changed")
    require(len(private_rows) == 5184 and all(row["match"] == 1 for row in private_rows),
            "environment plane private field denominator or agreement changed")
    require(len(public_rows) == 384, "environment plane public denominator changed")
    end_analyzer_identity = identity(args.analyzer, "analyzer after plane", executable=True)
    end_probe_identity = identity(args.fact_probe, "private fact probe after plane", executable=True)
    end_schema_identity = identity(args.schema, "public schema after plane")
    require(end_analyzer_identity["sha256"] == analyzer_identity["sha256"], "analyzer changed during environment plane")
    require(end_probe_identity["sha256"] == probe_identity["sha256"], "fact probe changed during environment plane")
    require(end_schema_identity["sha256"] == schema_identity["sha256"], "schema changed during environment plane")

    require(isinstance(args.build_origin, str) and args.build_origin, "plane build origin is required")
    require(isinstance(args.candidate_tree, str) and len(args.candidate_tree) == 40
            and all(char in "0123456789abcdef" for char in args.candidate_tree),
            "plane candidate tree is invalid")
    plane_manifest = {
        "format": "x64lens-sprint12-role-property-environment-plane-v2",
        "environment_id": args.environment_id,
        "execution_stratum": args.execution_stratum,
        "build_origin": args.build_origin,
        "candidate_tree": args.candidate_tree,
        "container_image_id": args.image_id or None,
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "object_count": 96,
        "probe_process_count": 288,
        "private_field_count": 5184,
        "public_command_count": 384,
        "private_field_mismatch_count": 0,
        "public_policy_decision_authorized": False,
        "target_execution": False,
        "identities": {
            "heldout_manifest": heldout_identity,
            "heldout_authority_id": manifest["authority_id"],
            "parity_harness": harness_identity,
            "analyzer": analyzer_identity,
            "fact_probe": probe_identity,
            "schema": schema_identity,
            "python_runtime": {"version": sys.version, "executable": sys.executable},
        },
        "objects_sha256": sha256_bytes((result / "objects.tsv").read_bytes()),
        "probe_runs_sha256": sha256_bytes((result / "probe-runs.tsv").read_bytes()),
        "private_fields_sha256": sha256_bytes((result / "private-fields.tsv").read_bytes()),
        "public_commands_sha256": sha256_bytes((result / "public-commands.tsv").read_bytes()),
    }
    (result / "manifest.json").write_text(json.dumps(plane_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seal_tree(result)
    print(
        "sprint12-role-property-environment-plane: ok "
        f"environment={args.environment_id} stratum={args.execution_stratum} objects=96 "
        "probe_processes=288 private_fields=5184 public_commands=384 mismatches=0"
    )
    return 0


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def indexed(rows: list[dict[str, str]], keys: tuple[str, ...], label: str) -> dict[tuple[str, ...], dict[str, str]]:
    result: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = tuple(row[field] for field in keys)
        require(key not in result, f"duplicate {label} key: {key}")
        result[key] = row
    return result


def compare(args: argparse.Namespace) -> int:
    left = args.left.resolve(strict=True)
    right = args.right.resolve(strict=True)
    verify_checksums(left)
    verify_checksums(right)
    lm = load_json(left / "manifest.json")
    rm = load_json(right / "manifest.json")
    require(lm.get("format") == rm.get("format") == "x64lens-sprint12-role-property-environment-plane-v2",
            "environment plane format changed")
    if not args.logic_only:
        require({lm.get("execution_stratum"), rm.get("execution_stratum")} == {"native", "container"},
                "acceptance parity requires one native and one container plane")
    require(lm["environment_id"] != rm["environment_id"], "environment ids must be distinct")
    require(lm["candidate_tree"] == rm["candidate_tree"], "native/container source trees differ")
    for key in ("heldout_manifest", "parity_harness", "schema"):
        require(lm["identities"][key]["sha256"] == rm["identities"][key]["sha256"],
                f"shared parity authority differs across environments: {key}")
    if not args.logic_only:
        require(lm["build_origin"] == "native-gitless-build", "native build origin changed")
        require(rm["build_origin"] == "container-image-build", "container build origin changed")
        require(lm.get("container_image_id") is None, "native plane unexpectedly names a container image")
        require(isinstance(rm.get("container_image_id"), str) and rm["container_image_id"].startswith("sha256:"),
                "container plane lacks immutable image identity")

    left_objects = indexed(read_tsv(left / "objects.tsv"), ("object",), "object")
    right_objects = indexed(read_tsv(right / "objects.tsv"), ("object",), "object")
    require(left_objects.keys() == right_objects.keys() and len(left_objects) == 96,
            "environment object sets differ")
    for key in left_objects:
        require(left_objects[key]["sha256"] == right_objects[key]["sha256"],
                f"environment target bytes differ: {key}")

    left_probe = indexed(read_tsv(left / "probe-runs.tsv"), ("object", "repeat"), "probe")
    right_probe = indexed(read_tsv(right / "probe-runs.tsv"), ("object", "repeat"), "probe")
    require(left_probe.keys() == right_probe.keys() and len(left_probe) == 288,
            "environment probe process sets differ")
    for key in left_probe:
        require(left_probe[key]["exit_code"] == right_probe[key]["exit_code"] == "0"
                and left_probe[key]["stdout_sha256"] == right_probe[key]["stdout_sha256"]
                and left_probe[key]["stderr_sha256"] == right_probe[key]["stderr_sha256"],
                f"private probe process parity mismatch: {key}")

    left_private = indexed(read_tsv(left / "private-fields.tsv"), ("object", "repeat", "field"), "private field")
    right_private = indexed(read_tsv(right / "private-fields.tsv"), ("object", "repeat", "field"), "private field")
    require(left_private.keys() == right_private.keys() and len(left_private) == 5184,
            "environment private-field sets differ")
    for key in left_private:
        require(left_private[key]["match"] == right_private[key]["match"] == "1"
                and left_private[key]["expected"] == right_private[key]["expected"]
                and left_private[key]["observed"] == right_private[key]["observed"],
                f"private field parity mismatch: {key}")

    left_public = indexed(read_tsv(left / "public-commands.tsv"), ("object", "command_id"), "public command")
    right_public = indexed(read_tsv(right / "public-commands.tsv"), ("object", "command_id"), "public command")
    require(left_public.keys() == right_public.keys() and len(left_public) == 384,
            "environment public-command sets differ")
    for key in left_public:
        require(left_public[key]["exit_code"] == right_public[key]["exit_code"]
                and left_public[key]["normalized_stdout_sha256"] == right_public[key]["normalized_stdout_sha256"]
                and left_public[key]["normalized_stderr_sha256"] == right_public[key]["normalized_stderr_sha256"],
                f"public command parity mismatch: {key}")

    result = Path(os.path.abspath(args.result_dir))
    require(not result.exists(), f"parity result already exists: {result}")
    result.mkdir(parents=True)
    manifest = {
        "format": "x64lens-sprint12-role-property-environment-parity-v1",
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "logic_only": bool(args.logic_only),
        "environment_ids": [lm["environment_id"], rm["environment_id"]],
        "execution_strata": [lm["execution_stratum"], rm["execution_stratum"]],
        "object_count": 96,
        "private_fields_per_environment": 5184,
        "private_fields_combined": 10368,
        "paired_private_field_agreements": 5184,
        "probe_processes_per_environment": 288,
        "paired_probe_process_agreements": 288,
        "public_oracle_closures_combined": 768,
        "paired_public_tuples": 384,
        "private_mismatches": 0,
        "public_mismatches": 0,
        "public_policy_decision_authorized": False,
        "source_tree": lm["candidate_tree"],
        "build_origins": [lm["build_origin"], rm["build_origin"]],
        "native_analyzer_sha256": lm["identities"]["analyzer"]["sha256"],
        "container_analyzer_sha256": rm["identities"]["analyzer"]["sha256"],
        "native_fact_probe_sha256": lm["identities"]["fact_probe"]["sha256"],
        "container_fact_probe_sha256": rm["identities"]["fact_probe"]["sha256"],
        "container_image_id": rm.get("container_image_id"),
        "plane_manifest_sha256": {
            lm["environment_id"]: sha256_bytes((left / "manifest.json").read_bytes()),
            rm["environment_id"]: sha256_bytes((right / "manifest.json").read_bytes()),
        },
    }
    (result / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seal_tree(result)
    label = "logic-only" if args.logic_only else "native-container"
    print(
        "sprint12-role-property-environment-parity-smoke: ok "
        f"mode={label} objects=96 private_fields_per_environment=5184 "
        "private_fields_combined=10368 paired_probe_processes=288 "
        "public_oracle_closures=768 paired_public_tuples=384 mismatches=0 public_policy=deferred"
    )
    return 0


def capture_cleanup(path: Path) -> tuple[Any, Any]:
    cleanup = load_module("p073_parity_cleanup", ROOT / "tools/remove-owned-tree.py")
    return cleanup, cleanup.parse_identity(cleanup.identify(path))


def recursive_tree_identity(root: Path) -> dict[str, Any]:
    """Return a mode-aware identity for one sealed retained evidence tree."""
    require(root.is_dir() and not root.is_symlink(), f"retained tree is unavailable: {root}")
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        require(not path.is_symlink(), f"retained parity tree contains a link: {relative}")
        if path.is_dir():
            records.append({"path": relative, "type": "directory", "mode": f"{stat.S_IMODE(metadata.st_mode):04o}"})
        else:
            require(path.is_file(), f"retained parity tree contains a special member: {relative}")
            data = path.read_bytes()
            records.append({
                "path": relative,
                "type": "file",
                "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                "size_bytes": len(data),
                "sha256": sha256_bytes(data),
            })
    encoded = (json.dumps(records, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return {"member_count": len(records), "sha256": sha256_bytes(encoded)}


def build_container_command(
    *,
    docker: str,
    image_id: str,
    candidate_tree: str,
    heldout: Path,
    container_write_root: Path,
) -> list[str]:
    """Build one isolated, independently compiled container plane command."""
    script = (
        "set -euo pipefail; "
        "python3 /work/tools/gitless-source-manifest.py verify "
        "--root /work --manifest /x64lens-source-manifest.json; "
        "rm -rf /tmp/x64lens-role-build; mkdir /tmp/x64lens-role-build; "
        "cp -a /work/. /tmp/x64lens-role-build/; "
        "chmod -R u+rwX /tmp/x64lens-role-build; "
        "cd /tmp/x64lens-role-build; "
        "make clean; make; make build/tests/role-property-fact-probe; "
        "python3 /work/tools/sprint12-role-property-environment-parity-smoke.py plane "
        "--environment-id container --execution-stratum container "
        "--heldout-result /heldout "
        "--analyzer /tmp/x64lens-role-build/build/x64lens "
        "--schema /work/schemas/x64lens-report.schema.json "
        "--fact-probe /tmp/x64lens-role-build/build/tests/role-property-fact-probe "
        "--build-origin container-image-build "
        f"--candidate-tree {candidate_tree} --image-id {image_id} "
        "--result-dir /output/plane; "
        "python3 /work/tools/gitless-source-manifest.py verify "
        "--root /work --manifest /x64lens-source-manifest.json"
    )
    return [
        docker, "run", "--rm", "--read-only", "--network", "none",
        "-e", "HOME=/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "LC_ALL=C", "-e", "LANG=C", "-e", "TZ=UTC",
        "-e", f"X64LENS_CANDIDATE_TREE={candidate_tree}",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
        "-v", f"{heldout}:/heldout:ro",
        "-v", f"{container_write_root}:/output:rw",
        "-w", "/tmp",
        image_id,
        "bash", "-lc", script,
    ]


def path_covers(ancestor: Path, child: Path) -> bool:
    ancestor = Path(os.path.realpath(ancestor))
    child = Path(os.path.realpath(child))
    return ancestor == child or ancestor in child.parents


def validate_container_mount_policy(
    command: list[str],
    *,
    native_result: Path,
    heldout: Path,
    container_write_root: Path,
) -> dict[str, Any]:
    """Authenticate exact mounts and reject any host ancestor covering native or source."""
    mounts: list[tuple[Path, str, str]] = []
    # The reviewed parity protocol deliberately accepts one exact Docker bind
    # grammar only.  Alternate spellings must not create unparsed host mounts
    # that bypass native-plane isolation accounting.
    rejected_mount_forms = {
        "--mount", "--volume", "--volumes-from",
    }
    for item in command:
        require(item not in rejected_mount_forms,
                f"alternate Docker mount syntax is not permitted: {item}")
        require(not item.startswith("--mount=") and not item.startswith("--volume=")
                and not (item.startswith("-v") and item != "-v"),
                f"compact or alternate Docker mount syntax is not permitted: {item}")

    for index, item in enumerate(command[:-1]):
        if item != "-v":
            continue
        raw = command[index + 1]
        parts = raw.rsplit(":", 2)
        require(len(parts) == 3 and parts[2] in {"ro", "rw"}, f"invalid parity mount: {raw!r}")
        host = Path(os.path.abspath(parts[0]))
        mounts.append((host, parts[1], parts[2]))
    expected = [
        (Path(os.path.abspath(heldout)), "/heldout", "ro"),
        (Path(os.path.abspath(container_write_root)), "/output", "rw"),
    ]
    require(mounts == expected, f"container parity mount set changed: {mounts!r}")
    covering = [str(host) for host, _target, _mode in mounts if path_covers(host, native_result)]
    require(not covering, f"container mount exposes native parity plane through an ancestor: {covering}")
    require(container_write_root.is_dir() and not container_write_root.is_symlink()
            and not any(container_write_root.iterdir()),
            "container parity write root is not an empty real directory before launch")
    return {
        "native_plane_exposed_to_container": False,
        "covering_native_mount_count": 0,
        "container_write_scope": "dedicated-empty-container-plane-root-only",
        "writable_mount_count": 1,
        "mount_count": len(mounts),
        "host_mounts": [
            {"host": str(host), "container": target, "mode": mode}
            for host, target, mode in mounts
        ],
    }


def _make_writable(root: Path) -> None:
    root.chmod(stat.S_IMODE(root.stat().st_mode) | stat.S_IWUSR | stat.S_IXUSR)
    for path in root.rglob("*"):
        metadata = path.lstat()
        require(not path.is_symlink(), f"build copy contains a link: {path}")
        if stat.S_ISDIR(metadata.st_mode):
            path.chmod(stat.S_IMODE(metadata.st_mode) | stat.S_IWUSR | stat.S_IXUSR)
        elif stat.S_ISREG(metadata.st_mode):
            path.chmod(stat.S_IMODE(metadata.st_mode) | stat.S_IWUSR)
        else:
            raise ParityError(f"build copy contains a special member: {path}")


def _build_native(source_root: Path, build_root: Path) -> tuple[Path, Path]:
    shutil.copytree(source_root, build_root, symlinks=False)
    _make_writable(build_root)
    for command in (
        ["make", "clean"],
        ["make"],
        ["make", "build/tests/role-property-fact-probe"],
    ):
        cp = run(command, cwd=build_root, timeout=300.0)
        require(
            cp.returncode == 0,
            f"native parity build failed ({' '.join(command)}):\n{cp.stdout[-1000:]!r}\n{cp.stderr[-2000:]!r}",
        )
    analyzer = build_root / "build/x64lens"
    probe = build_root / "build/tests/role-property-fact-probe"
    identity(analyzer, "independently built native analyzer", executable=True)
    identity(probe, "independently built native fact probe", executable=True)
    return analyzer, probe


def _inspect_image(docker: str, image: str, candidate_tree: str) -> tuple[str, dict[str, Any]]:
    cp = run([docker, "image", "inspect", image], timeout=30.0)
    require(cp.returncode == 0, f"cannot inspect Docker image {image}: {cp.stderr.decode(errors='replace')}")
    value = json.loads(cp.stdout, object_pairs_hook=strict_object)
    require(isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict), "Docker image inspect shape changed")
    record = value[0]
    image_id = record.get("Id")
    labels = ((record.get("Config") or {}).get("Labels") or {})
    require(isinstance(image_id, str) and image_id.startswith("sha256:"), "Docker image lacks immutable ID")
    require(labels.get("org.x64lens.candidate-tree") == candidate_tree,
            "Docker image candidate-tree label disagrees with the source authority")
    return image_id, {
        "image_id": image_id,
        "candidate_tree_label": labels.get("org.x64lens.candidate-tree"),
        "repository_tag": image,
    }


def run_full(args: argparse.Namespace) -> int:
    docker = shutil.which(args.docker)
    require(docker is not None, "Docker command is unavailable")
    repo = Path(os.path.abspath(args.repo))
    require((repo / ".git").exists(), "parity source repository Git metadata is missing")
    final_result = Path(os.path.abspath(args.result_dir))
    require(not final_result.exists(), f"retained parity result already exists: {final_result}")
    final_result.parent.mkdir(parents=True, exist_ok=True)
    staging = final_result.parent / f".{final_result.name}.staging.{os.getpid()}.{os.urandom(8).hex()}"
    require(not staging.exists(), "parity staging identity collision")
    staging.mkdir(mode=0o700)
    cleanup, cleanup_identity = capture_cleanup(staging)
    completed = False
    try:
        source_root = staging / "source-authority"
        source_manifest = staging / "source-manifest.json"
        gitless = load_module("p079_role_gitless", repo / "tools/gitless-source-manifest.py")
        source_authority = gitless.create(repo, source_root, source_manifest)
        candidate_tree = source_authority["candidate_tree"]
        gitless.verify(source_root, source_authority)

        native_build = staging / "native-build"
        native_analyzer, native_probe = _build_native(source_root, native_build)
        source_schema = source_root / "schemas/x64lens-report.schema.json"
        if args.schema is not None:
            require(identity(args.schema, "supplied schema")["sha256"] == identity(source_schema, "source schema")["sha256"],
                    "supplied schema differs from the staged source authority")

        inputs = staging / "inputs"
        heldout = staging / "heldout"
        native_result = staging / "native"
        container_write_root = staging / "container-write-root"
        container_result = staging / "container"
        parity_result = staging / "parity"
        inputs.mkdir()
        container_write_root.mkdir(mode=0o777)
        container_write_root.chmod(0o777)
        shutil.copy2(native_analyzer, inputs / "x64lens")
        shutil.copy2(native_probe, inputs / "role-property-fact-probe")
        shutil.copy2(source_schema, inputs / "schema.json")
        shutil.copy2(source_manifest, inputs / "source-manifest.json")
        tools_root = inputs / "tools"
        tools_root.mkdir()
        parity_tools = (
            "sprint12-role-property-environment-parity-smoke.py",
            "sprint12-role-property-heldout-smoke.py",
            "sprint12-role-property-readelf-smoke.py",
            "sprint12-role-property-metamorphic-smoke.py",
            "sprint12-gnu-property-smoke.py",
        )
        for name in parity_tools:
            shutil.copy2(source_root / "tools" / name, tools_root / name)
            (tools_root / name).chmod(0o555)
        (inputs / "x64lens").chmod(0o555)
        (inputs / "role-property-fact-probe").chmod(0o555)
        (inputs / "schema.json").chmod(0o444)
        (inputs / "source-manifest.json").chmod(0o444)
        before = {
            name: identity(inputs / name, name, executable=name in {"x64lens", "role-property-fact-probe"})
            for name in ("x64lens", "role-property-fact-probe", "schema.json", "source-manifest.json")
        }
        before["parity_harness"] = identity(
            tools_root / "sprint12-role-property-environment-parity-smoke.py",
            "parity_harness",
            executable=True,
        )
        seal_tree(inputs)

        generate = [
            sys.executable,
            str(source_root / "tools/sprint12-role-property-heldout-smoke.py"),
            "--authority", str(args.heldout_authority),
            "--analyzer", str(inputs / "x64lens"),
            "--schema", str(inputs / "schema.json"),
            "--provisional-corpus", str(args.provisional_corpus),
            "--fact-probe", str(inputs / "role-property-fact-probe"),
            "--result-dir", str(heldout),
        ]
        cp = run(generate, timeout=240.0)
        require(cp.returncode == 0, f"held-out generation failed:\n{cp.stdout[-500:]!r}\n{cp.stderr[-1000:]!r}")
        verify_legacy_checksums(heldout)
        unseal_for_reseal(heldout)
        seal_tree(heldout)
        verify_checksums(heldout)

        copied_harness = inputs / "tools/sprint12-role-property-environment-parity-smoke.py"
        native = [
            sys.executable, str(copied_harness), "plane",
            "--environment-id", "native", "--execution-stratum", "native",
            "--heldout-result", str(heldout),
            "--analyzer", str(inputs / "x64lens"),
            "--schema", str(inputs / "schema.json"),
            "--fact-probe", str(inputs / "role-property-fact-probe"),
            "--build-origin", "native-gitless-build",
            "--candidate-tree", candidate_tree,
            "--result-dir", str(native_result),
        ]
        cp = run(native, timeout=240.0)
        require(cp.returncode == 0, f"native environment plane failed:\n{cp.stdout[-500:]!r}\n{cp.stderr[-1000:]!r}")
        verify_checksums(native_result)
        native_before_container = recursive_tree_identity(native_result)

        image_id, image_identity = _inspect_image(docker, args.docker_image, candidate_tree)
        container_command = build_container_command(
            docker=docker,
            image_id=image_id,
            candidate_tree=candidate_tree,
            heldout=heldout,
            container_write_root=container_write_root,
        )
        mount_policy = validate_container_mount_policy(
            container_command,
            native_result=native_result,
            heldout=heldout,
            container_write_root=container_write_root,
        )
        cp = run(container_command, timeout=1200.0)
        require(cp.returncode == 0, f"container environment plane failed:\n{cp.stdout[-1000:]!r}\n{cp.stderr[-3000:]!r}")
        generated_container = container_write_root / "plane"
        require(generated_container.is_dir() and not generated_container.is_symlink(),
                "container plane did not publish a real dedicated result")
        require(set(container_write_root.iterdir()) == {generated_container},
                "container write root contains undeclared members")
        verify_checksums(generated_container)
        write_root_before = container_write_root.lstat()
        generated_before = generated_container.lstat()
        container_write_root.chmod(0o700)
        generated_container.chmod(0o700)
        require((container_write_root.lstat().st_dev, container_write_root.lstat().st_ino)
                == (write_root_before.st_dev, write_root_before.st_ino),
                "container write-root identity changed before publication")
        require((generated_container.lstat().st_dev, generated_container.lstat().st_ino)
                == (generated_before.st_dev, generated_before.st_ino),
                "container plane identity changed before publication")
        generated_container.rename(container_result)
        container_result.chmod(0o555)
        require((container_result.lstat().st_dev, container_result.lstat().st_ino)
                == (generated_before.st_dev, generated_before.st_ino),
                "container plane identity changed across publication")
        container_write_root.rmdir()
        verify_checksums(container_result)
        native_after_container = recursive_tree_identity(native_result)
        require(native_after_container == native_before_container,
                "native parity plane changed during container execution")

        comparison = [
            sys.executable, str(copied_harness), "compare",
            "--left", str(native_result),
            "--right", str(container_result),
            "--result-dir", str(parity_result),
        ]
        cp = run(comparison, timeout=30.0)
        require(cp.returncode == 0, f"environment parity comparison failed:\n{cp.stdout[-500:]!r}\n{cp.stderr[-1000:]!r}")
        verify_checksums(parity_result)
        gitless.verify(source_root, source_authority)
        after = {
            "x64lens": identity(inputs / "x64lens", "x64lens", executable=True),
            "role-property-fact-probe": identity(
                inputs / "role-property-fact-probe", "role-property-fact-probe", executable=True
            ),
            "schema.json": identity(inputs / "schema.json", "schema.json"),
            "source-manifest.json": identity(inputs / "source-manifest.json", "source-manifest.json"),
            "parity_harness": identity(copied_harness, "parity_harness", executable=True),
        }
        require(all(before[name]["sha256"] == after[name]["sha256"] for name in before),
                "native retained parity inputs changed during execution")

        # Build products are represented by retained binary identities; the
        # writable build copy itself is not part of the final evidence plane.
        shutil.rmtree(native_build)
        run_manifest = {
            "format": "x64lens-sprint12-role-property-environment-parity-run-v4",
            "evidence_class": "diagnostic",
            "frozen": False,
            "publication_eligible": False,
            "actual_native_container_parity_executed": True,
            "independent_native_container_builds": True,
            "source_tree": candidate_tree,
            "native_plane_exposed_to_container": mount_policy["native_plane_exposed_to_container"],
            "live_repository_mounted_into_container": False,
            "source_snapshot_mounted_into_container": False,
            "host_analyzer_or_probe_mounted_into_container": False,
            "container_write_scope": mount_policy["container_write_scope"],
            "container_mount_policy": mount_policy,
            "container_image": image_identity,
            "planes_retained_and_sealed": True,
            "public_policy_decision_authorized": False,
            "target_execution": False,
            "input_identities": before,
            "native_plane_identity_before_container": native_before_container,
            "native_plane_identity_after_container": native_after_container,
            "container_plane_identity": recursive_tree_identity(container_result),
            "parity_identity": recursive_tree_identity(parity_result),
            "container_command": container_command,
        }
        (staging / "run-manifest.json").write_text(
            json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        seal_tree(staging)
        os.rename(staging, final_result)
        verify_checksums(final_result)
        completed = True
        print(cp.stdout.decode("utf-8", errors="replace").strip())
        print(
            "sprint12-role-property-environment-parity-run: ok "
            f"result={final_result} source_tree={candidate_tree} independent_builds=1 "
            "native_exposed=0 live_repo_mounted=0 host_binaries_mounted=0 "
            "container_write_scope=exclusive planes_retained=1 public_policy=deferred"
        )
        return 0
    finally:
        if not completed and staging.exists():
            cleanup.remove(staging, cleanup_identity)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plane_parser = sub.add_parser("plane")
    plane_parser.add_argument("--environment-id", required=True)
    plane_parser.add_argument("--execution-stratum", required=True)
    plane_parser.add_argument("--heldout-result", type=Path, required=True)
    plane_parser.add_argument("--analyzer", type=Path, required=True)
    plane_parser.add_argument("--schema", type=Path, required=True)
    plane_parser.add_argument("--fact-probe", type=Path, required=True)
    plane_parser.add_argument("--build-origin", default="logic-only")
    plane_parser.add_argument("--candidate-tree", default="0" * 40)
    plane_parser.add_argument("--image-id", default="")
    plane_parser.add_argument("--result-dir", type=Path, required=True)

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--left", type=Path, required=True)
    compare_parser.add_argument("--right", type=Path, required=True)
    compare_parser.add_argument("--result-dir", type=Path, required=True)
    compare_parser.add_argument("--logic-only", action="store_true")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--repo", type=Path, default=ROOT)
    run_parser.add_argument("--heldout-authority", type=Path, required=True)
    run_parser.add_argument("--provisional-corpus", type=Path, required=True)
    run_parser.add_argument("--analyzer", type=Path)
    run_parser.add_argument("--schema", type=Path)
    run_parser.add_argument("--fact-probe", type=Path)
    run_parser.add_argument("--docker-image", required=True)
    run_parser.add_argument("--docker", default="docker")
    run_parser.add_argument("--result-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "plane":
        return plane(args)
    if args.command == "compare":
        return compare(args)
    return run_full(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ParityError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"sprint12-role-property-environment-parity-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
