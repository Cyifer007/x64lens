#!/usr/bin/env python3
"""Create and verify one exact descriptor-bound Git-less source authority.

The create path freezes one staged Git tree, reads every payload from that tree
rather than from the mutable index/worktree path, materializes only regular
Git blobs, and emits canonical root/directory/file modes.  The verify path uses
retained directory and file descriptors so hashing, Git-object derivation,
membership, topology, and caller-visible identity refer to one object graph.

``create-context`` produces the only supported Docker build context.  The
transport Dockerfile is copied from the already materialized and verified
``source/Dockerfile`` object, preventing the source tree and transport file from
coming from different index snapshots.  Ignored, untracked, generated, and
private worktree members never enter the context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from typing import Any, BinaryIO

SCHEMA = "x64lens-gitless-source-v2"
CONTEXT_SCHEMA = "x64lens-exact-docker-context-v2"
BUFFER = 1024 * 1024
MAX_FILES = 8192
MAX_DIRECTORIES = 2048
ROOT_MODE = 0o755
DIRECTORY_MODE = 0o755
MANIFEST_MODE = 0o444
REGULAR_MODES = {"100644": 0o644, "100755": 0o755}


class SourceError(RuntimeError):
    """Raised when source identity, topology, or exact membership disagrees."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceError(message)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def safe(raw: Any) -> str:
    require(isinstance(raw, str) and raw, "source path must be a nonempty string")
    path = PurePosixPath(raw)
    require(
        not path.is_absolute()
        and path.as_posix() == raw
        and "\\" not in raw
        and all(part not in {"", ".", ".."} for part in path.parts),
        f"unsafe source path: {raw!r}",
    )
    return raw


def parent(raw: str) -> str:
    return "/".join(PurePosixPath(raw).parts[:-1])


def git_object(kind: bytes, payload: bytes) -> str:
    return hashlib.sha1(kind + b" " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def hash_stream(handle: BinaryIO) -> tuple[str, int, str]:
    sha = hashlib.sha256()
    metadata = os.fstat(handle.fileno())
    require(stat.S_ISREG(metadata.st_mode), "source hash input is not a regular file")
    blob = hashlib.sha1(b"blob " + str(metadata.st_size).encode("ascii") + b"\0")
    total = 0
    while True:
        chunk = handle.read(BUFFER)
        if not chunk:
            break
        sha.update(chunk)
        blob.update(chunk)
        total += len(chunk)
    require(total == metadata.st_size, "source member size changed while hashing")
    return sha.hexdigest(), total, blob.hexdigest()


def hash_file(path: Path) -> tuple[str, int]:
    with path.open("rb") as handle:
        sha, size, _oid = hash_stream(handle)
    return sha, size


def run_git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(cp.returncode == 0, f"git {' '.join(args)} failed: {cp.stderr.decode(errors='replace').strip()}")
    return cp.stdout


def index_records(repo: Path) -> tuple[str, list[tuple[str, str, str]]]:
    """Freeze one stage-zero Git tree and return its regular blob records."""
    repo = Path(os.path.abspath(repo))
    require((repo / ".git").exists(), "source repository Git metadata is missing")
    require(
        subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "--"], check=False).returncode == 0,
        "worktree differs from staged source authority",
    )
    tree = run_git(repo, "write-tree").decode("ascii").strip()
    require(len(tree) == 40 and all(c in "0123456789abcdef" for c in tree), "invalid staged Git tree")
    rows: list[tuple[str, str, str]] = []
    for raw in run_git(repo, "ls-tree", "-r", "-z", "--full-tree", tree).split(b"\0"):
        if not raw:
            continue
        header, path_raw = raw.split(b"\t", 1)
        mode_raw, type_raw, oid_raw = header.split()
        path = safe(os.fsdecode(path_raw))
        mode = mode_raw.decode("ascii")
        require(type_raw == b"blob", f"unsupported source Git object type: {path}")
        require(mode in REGULAR_MODES, f"unsupported Docker source Git mode {mode}: {path}")
        rows.append((path, mode, oid_raw.decode("ascii")))
    rows.sort(key=lambda row: os.fsencode(row[0]))
    require(0 < len(rows) <= MAX_FILES, f"source file count outside bound: {len(rows)}")
    # Reauthenticate the staged authority after inventory.  A concurrent index
    # replacement cannot silently combine records from two trees.
    require(run_git(repo, "write-tree").decode("ascii").strip() == tree, "staged Git tree changed during inventory")
    require(
        subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "--"], check=False).returncode == 0,
        "worktree changed during staged source inventory",
    )
    return tree, rows


def directory_path(item: Any) -> str:
    if isinstance(item, str):
        return safe(item)
    require(isinstance(item, dict) and set(item) == {"path", "mode"}, "source directory record shape changed")
    require(item["mode"] == f"{DIRECTORY_MODE:04o}", f"invalid source directory mode: {item.get('path')}")
    return safe(item["path"])


def derive_tree(files: list[dict[str, Any]], directories: list[Any]) -> str:
    directory_set = {directory_path(item) for item in directories}
    all_directories = {"", *directory_set}
    children: dict[str, list[tuple[str, bool, str, str]]] = {item: [] for item in all_directories}
    for directory in directory_set:
        require(parent(directory) in all_directories, f"directory parent missing: {directory}")
    for item in files:
        path = safe(item["path"])
        require(parent(path) in all_directories, f"file parent missing: {path}")
        children[parent(path)].append((PurePosixPath(path).name, False, item["git_mode"], item["git_oid"]))
    for directory in sorted(directory_set, key=lambda item: (-item.count("/"), os.fsencode(item))):
        entries = children[directory]
        require(entries, f"empty directory cannot belong to a Git tree: {directory}")
        payload = tree_payload(entries)
        children[parent(directory)].append((PurePosixPath(directory).name, True, "40000", git_object(b"tree", payload)))
    require(children[""], "source tree has no root members")
    return git_object(b"tree", tree_payload(children[""]))


def tree_payload(entries: list[tuple[str, bool, str, str]]) -> bytes:
    ordered = sorted(
        (
            (os.fsencode(name) + (b"/" if is_dir else b""), is_dir, mode, oid)
            for name, is_dir, mode, oid in entries
        ),
        key=lambda row: row[0],
    )
    chunks: list[bytes] = []
    for ordered_name, is_dir, mode, oid in ordered:
        name = ordered_name[:-1] if is_dir else ordered_name
        chunks.append(mode.encode("ascii") + b" " + name + b"\0" + bytes.fromhex(oid))
    return b"".join(chunks)


def _write_regular(parent_fd: int, name: str, payload: bytes, mode: int) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode, dir_fd=parent_fd)
    try:
        view = memoryview(payload)
        written = 0
        while written < len(view):
            count = os.write(fd, view[written:])
            require(count > 0, "short source write")
            written += count
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def _open_directory_chain(root_fd: int, raw: str) -> int:
    current = os.dup(root_fd)
    try:
        for part in PurePosixPath(raw).parts:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=current)
            os.close(current)
            current = nxt
        return current
    except Exception:
        os.close(current)
        raise


def create(repo: Path, root: Path, manifest_path: Path) -> dict[str, Any]:
    repo = Path(os.path.abspath(repo))
    root = Path(os.path.abspath(root))
    manifest_path = Path(os.path.abspath(manifest_path))
    require(not root.exists() and not root.is_symlink(), "source root already exists")
    require(manifest_path.parent.is_dir() and not manifest_path.parent.is_symlink(), "manifest parent is missing or linked")
    tree, records = index_records(repo)
    directory_names = sorted(
        {
            "/".join(PurePosixPath(path).parts[:index])
            for path, _mode, _oid in records
            for index in range(1, len(PurePosixPath(path).parts))
        },
        key=lambda item: (item.count("/"), os.fsencode(item)),
    )
    require(len(directory_names) <= MAX_DIRECTORIES, "source directory count exceeds bound")

    os.mkdir(root, ROOT_MODE)
    os.chmod(root, ROOT_MODE)
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    files: list[dict[str, Any]] = []
    try:
        for directory in directory_names:
            parent_name = parent(directory)
            parent_fd = _open_directory_chain(root_fd, parent_name) if parent_name else os.dup(root_fd)
            try:
                os.mkdir(PurePosixPath(directory).name, DIRECTORY_MODE, dir_fd=parent_fd)
                child_fd = os.open(
                    PurePosixPath(directory).name,
                    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                    dir_fd=parent_fd,
                )
                try:
                    os.fchmod(child_fd, DIRECTORY_MODE)
                    os.fsync(child_fd)
                finally:
                    os.close(child_fd)
            finally:
                os.close(parent_fd)

        for path, git_mode, expected_oid in records:
            payload = run_git(repo, "cat-file", "blob", expected_oid)
            require(git_object(b"blob", payload) == expected_oid, f"frozen Git blob changed: {path}")
            parent_name = parent(path)
            parent_fd = _open_directory_chain(root_fd, parent_name) if parent_name else os.dup(root_fd)
            try:
                mode = REGULAR_MODES[git_mode]
                _write_regular(parent_fd, PurePosixPath(path).name, payload, mode)
            finally:
                os.close(parent_fd)
            files.append(
                {
                    "path": path,
                    "git_mode": git_mode,
                    "git_oid": expected_oid,
                    "mode": f"{mode:04o}",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                }
            )
        os.fsync(root_fd)
    finally:
        os.close(root_fd)

    directories = [{"path": item, "mode": f"{DIRECTORY_MODE:04o}"} for item in directory_names]
    manifest = {
        "schema": SCHEMA,
        "candidate_tree": tree,
        "root_mode": f"{ROOT_MODE:04o}",
        "directories": directories,
        "files": files,
        "git_metadata_required": False,
    }
    require(derive_tree(files, directories) == tree, "materialized source does not derive the frozen Git tree")
    manifest_parent_fd = os.open(
        manifest_path.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        manifest_fd = os.open(
            manifest_path.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            MANIFEST_MODE,
            dir_fd=manifest_parent_fd,
        )
        try:
            payload = canonical(manifest)
            view = memoryview(payload)
            written = 0
            while written < len(view):
                count = os.write(manifest_fd, view[written:])
                require(count > 0, "short source-manifest write")
                written += count
            os.fchmod(manifest_fd, MANIFEST_MODE)
            os.fsync(manifest_fd)
        finally:
            os.close(manifest_fd)
        os.fsync(manifest_parent_fd)
    finally:
        os.close(manifest_parent_fd)
    verify(root, manifest)
    return manifest


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    require(isinstance(value, dict), "source manifest must be an object")
    return value


def _identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
    )


def verify(root: Path, manifest: dict[str, Any]) -> None:
    expected_shape = {"schema", "candidate_tree", "root_mode", "directories", "files", "git_metadata_required"}
    require(set(manifest) == expected_shape, "source manifest shape changed")
    require(manifest["schema"] == SCHEMA and manifest["git_metadata_required"] is False, "source manifest identity changed")
    require(manifest["root_mode"] == f"{ROOT_MODE:04o}", "source root authority mode changed")
    candidate_tree = manifest["candidate_tree"]
    require(
        isinstance(candidate_tree, str)
        and len(candidate_tree) == 40
        and all(c in "0123456789abcdef" for c in candidate_tree),
        "invalid source candidate tree",
    )
    directories = manifest["directories"]
    files = manifest["files"]
    require(isinstance(directories, list) and isinstance(files, list), "source member authorities must be arrays")
    require(len(directories) <= MAX_DIRECTORIES and len(files) <= MAX_FILES, "source authority exceeds bounds")

    root = Path(os.path.abspath(root))
    visible_before = os.lstat(root)
    require(stat.S_ISDIR(visible_before.st_mode) and not root.is_symlink(), "source root must be one real directory")
    require(stat.S_IMODE(visible_before.st_mode) == ROOT_MODE, "source root mode changed")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    directory_fds: dict[str, int] = {"": root_fd}
    seen_inodes: set[tuple[int, int]] = set()
    normalized_files: list[dict[str, Any]] = []
    try:
        root_meta = os.fstat(root_fd)
        require(_identity(root_meta) == _identity(visible_before), "source root identity changed during open")
        seen_inodes.add((root_meta.st_dev, root_meta.st_ino))

        expected_directories: set[str] = set()
        ordered_directory_paths = [directory_path(item) for item in directories]
        require(
            ordered_directory_paths == sorted(ordered_directory_paths, key=lambda item: (item.count("/"), os.fsencode(item))),
            "source directory order changed",
        )
        for record, raw in zip(directories, ordered_directory_paths, strict=True):
            require(isinstance(record, dict) and record["mode"] == f"{DIRECTORY_MODE:04o}", f"invalid source directory authority: {raw}")
            require(raw not in expected_directories, f"duplicate source directory: {raw}")
            expected_directories.add(raw)
            parent_fd = directory_fds.get(parent(raw))
            require(parent_fd is not None, f"source directory parent authority missing: {raw}")
            fd = os.open(PurePosixPath(raw).name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
            metadata = os.fstat(fd)
            require(stat.S_ISDIR(metadata.st_mode) and stat.S_IMODE(metadata.st_mode) == DIRECTORY_MODE, f"source directory mode/type changed: {raw}")
            key = (metadata.st_dev, metadata.st_ino)
            require(key not in seen_inodes, f"source directory inode topology changed: {raw}")
            seen_inodes.add(key)
            directory_fds[raw] = fd

        expected_files: set[str] = set()
        children: dict[str, set[str]] = {item: set() for item in directory_fds}
        for raw in expected_directories:
            children[parent(raw)].add(PurePosixPath(raw).name)
        for item in files:
            require(
                isinstance(item, dict)
                and set(item) == {"path", "git_mode", "git_oid", "mode", "sha256", "size_bytes"},
                "source file record shape changed",
            )
            path = safe(item["path"])
            require(path not in expected_files, f"duplicate source file: {path}")
            expected_files.add(path)
            require(item["git_mode"] in REGULAR_MODES, f"invalid Git mode: {path}")
            expected_mode = REGULAR_MODES[item["git_mode"]]
            require(item["mode"] == f"{expected_mode:04o}", f"transport mode disagrees with Git mode: {path}")
            require(isinstance(item["git_oid"], str) and len(item["git_oid"]) == 40, f"invalid Git object: {path}")
            require(isinstance(item["sha256"], str) and len(item["sha256"]) == 64, f"invalid SHA-256: {path}")
            require(type(item["size_bytes"]) is int and item["size_bytes"] >= 0, f"invalid size: {path}")
            parent_fd = directory_fds.get(parent(path))
            require(parent_fd is not None, f"source file parent authority missing: {path}")
            name = PurePosixPath(path).name
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
            try:
                before = os.fstat(fd)
                require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, f"unsafe source member: {path}")
                require(stat.S_IMODE(before.st_mode) == expected_mode, f"source mode changed: {path}")
                key = (before.st_dev, before.st_ino)
                require(key not in seen_inodes, f"source hard-link topology changed: {path}")
                seen_inodes.add(key)
                with os.fdopen(os.dup(fd), "rb", closefd=True) as handle:
                    observed_sha, observed_size, observed_oid = hash_stream(handle)
                after = os.fstat(fd)
                require(_identity(before) == _identity(after), f"source member changed while hashing: {path}")
                visible = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                require(_identity(visible) == _identity(after), f"source path identity changed after hashing: {path}")
                require((observed_sha, observed_size) == (item["sha256"], item["size_bytes"]), f"source bytes changed: {path}")
                require(observed_oid == item["git_oid"], f"source Git object changed: {path}")
            finally:
                os.close(fd)
            children[parent(path)].add(name)
            normalized_files.append(item)

        for raw, fd in directory_fds.items():
            observed = set(os.listdir(fd))
            require(observed == children[raw], f"source directory membership changed: {raw or '.'}")
        require(derive_tree(normalized_files, directories) == candidate_tree, "source Git tree derivation changed")
        root_after = os.fstat(root_fd)
        visible_after = os.lstat(root)
        require(_identity(root_after) == _identity(root_meta) == _identity(visible_after), "source root changed during verification")
        require(stat.S_IMODE(visible_after.st_mode) == ROOT_MODE, "source root mode changed after verification")
    finally:
        for raw, fd in sorted(directory_fds.items(), key=lambda row: -row[0].count("/")):
            try:
                os.close(fd)
            except OSError:
                pass


def _read_manifest_file(source: Path, manifest: dict[str, Any], path: str) -> bytes:
    """Read one transport member through the authenticated source object graph."""
    path = safe(path)
    record = next((item for item in manifest["files"] if item["path"] == path), None)
    require(record is not None, f"source manifest does not contain {path}")
    source = Path(os.path.abspath(source))
    visible_root = os.lstat(source)
    require(
        stat.S_ISDIR(visible_root.st_mode)
        and not source.is_symlink()
        and stat.S_IMODE(visible_root.st_mode) == ROOT_MODE,
        "source transport root changed",
    )
    root_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    parent_fd = -1
    fd = -1
    try:
        root_meta = os.fstat(root_fd)
        require(_identity(root_meta) == _identity(visible_root), "source transport root identity changed")
        raw_parent = parent(path)
        parent_fd = _open_directory_chain(root_fd, raw_parent) if raw_parent else os.dup(root_fd)
        name = PurePosixPath(path).name
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        before = os.fstat(fd)
        expected_mode = REGULAR_MODES[record["git_mode"]]
        require(
            stat.S_ISREG(before.st_mode)
            and before.st_nlink == 1
            and stat.S_IMODE(before.st_mode) == expected_mode,
            f"unsafe source transport member: {path}",
        )
        with os.fdopen(os.dup(fd), "rb", closefd=True) as handle:
            observed_sha, observed_size, observed_oid = hash_stream(handle)
        require(
            (observed_sha, observed_size, observed_oid)
            == (record["sha256"], record["size_bytes"], record["git_oid"]),
            f"source transport identity changed: {path}",
        )
        os.lseek(fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, BUFFER)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        after = os.fstat(fd)
        visible = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(
            total == record["size_bytes"]
            and _identity(before) == _identity(after) == _identity(visible),
            f"source transport member changed while reading: {path}",
        )
        root_after = os.fstat(root_fd)
        visible_after = os.lstat(source)
        require(
            _identity(root_meta) == _identity(root_after) == _identity(visible_after),
            "source transport root changed while reading",
        )
        return b"".join(chunks)
    finally:
        if fd >= 0:
            os.close(fd)
        if parent_fd >= 0:
            os.close(parent_fd)
        os.close(root_fd)


def create_context(repo: Path, context: Path) -> dict[str, Any]:
    context = Path(os.path.abspath(context))
    require(not context.exists() and not context.is_symlink(), "Docker context already exists")
    os.mkdir(context, ROOT_MODE)
    os.chmod(context, ROOT_MODE)
    source = context / "source"
    manifest_path = context / "source-manifest.json"
    manifest = create(repo, source, manifest_path)
    verify(source, manifest)
    dockerfile_payload = _read_manifest_file(source, manifest, "Dockerfile")
    transport = context / "Dockerfile.transport"
    transport.write_bytes(dockerfile_payload)
    transport.chmod(0o644)
    dockerignore = context / ".dockerignore"
    dockerignore.write_text("# exact generated context; no path exclusions\n", encoding="utf-8")
    dockerignore.chmod(0o644)
    source_record = next(item for item in manifest["files"] if item["path"] == "Dockerfile")
    authority = {
        "schema": CONTEXT_SCHEMA,
        "candidate_tree": manifest["candidate_tree"],
        "context_root_mode": f"{ROOT_MODE:04o}",
        "source_root_mode": manifest["root_mode"],
        "source_manifest_sha256": hash_file(manifest_path)[0],
        "source_dockerfile_sha256": source_record["sha256"],
        "transport_dockerfile_sha256": hashlib.sha256(dockerfile_payload).hexdigest(),
        "source_and_transport_dockerfile_identical": True,
        "source_files": len(manifest["files"]),
        "source_directories": len(manifest["directories"]),
        "ignored_or_untracked_members_copied": 0,
    }
    require(authority["source_dockerfile_sha256"] == authority["transport_dockerfile_sha256"], "transport Dockerfile differs from frozen source snapshot")
    context_authority = context / "context-authority.json"
    context_authority.write_bytes(canonical(authority))
    context_authority.chmod(0o444)
    require(stat.S_IMODE(os.lstat(context).st_mode) == ROOT_MODE, "Docker context root mode changed")
    verify(source, manifest)
    require(set(os.listdir(context)) == {"source", "source-manifest.json", "Dockerfile.transport", ".dockerignore", "context-authority.json"}, "Docker context membership changed")
    return authority


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create_parser = sub.add_parser("create")
    create_parser.add_argument("--repo", type=Path, required=True)
    create_parser.add_argument("--root", type=Path, required=True)
    create_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--root", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)
    context_parser = sub.add_parser("create-context")
    context_parser.add_argument("--repo", type=Path, required=True)
    context_parser.add_argument("--context", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "create":
        value = create(args.repo, args.root, args.manifest)
        print(f"gitless-source-manifest: ok action=create tree={value['candidate_tree']} files={len(value['files'])} directories={len(value['directories'])} schema={SCHEMA}")
    elif args.command == "verify":
        value = load_manifest(args.manifest)
        verify(args.root, value)
        print(f"gitless-source-manifest: ok action=verify tree={value['candidate_tree']} files={len(value['files'])} directories={len(value['directories'])} schema={SCHEMA}")
    else:
        value = create_context(args.repo, args.context)
        print(f"gitless-source-manifest: ok action=create-context tree={value['candidate_tree']} files={value['source_files']} ignored_or_untracked=0 schema={CONTEXT_SCHEMA}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, SourceError, subprocess.SubprocessError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"gitless-source-manifest: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
