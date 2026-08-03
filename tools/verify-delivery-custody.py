#!/usr/bin/env python3
"""Create or verify an exact descriptor-bound delivery-custody manifest.

Schema v2 authenticates the root mode, manifest path/mode, every directory
path/mode, and every regular payload path/hash/size/mode.  Verification opens
objects descriptor-relatively with ``O_NOFOLLOW``, hashes the bytes from the
same descriptor whose metadata is checked, and reauthenticates the caller-
visible pathname after hashing.  Symlinks, special files, unsafe or duplicate
paths, undeclared objects, mode drift, and pathname substitution fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
from typing import Any, Callable, NamedTuple

SCHEMA_ID = "x64lens-delivery-custody-v2"
BUFFER_SIZE = 1024 * 1024
O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)

# Test-only injection point.  It runs after a file has been hashed through its
# retained descriptor and before the descriptor/path post-checks.  Production
# callers leave it unset.
_TEST_AFTER_FILE_HASH_HOOK: Callable[[int, str, str], None] | None = None


class CustodyError(RuntimeError):
    """Raised when a delivery tree is incomplete, unsafe, or unauthenticated."""


class Fingerprint(NamedTuple):
    device: int
    inode: int
    file_type: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    nlink: int


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CustodyError(message)


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CustodyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json_loads(raw: str) -> Any:
    return json.loads(raw, object_pairs_hook=reject_duplicate_pairs)


def safe_relative(raw: str) -> str:
    require(isinstance(raw, str) and raw != "", "manifest path must be a nonempty string")
    path = PurePosixPath(raw)
    require(not path.is_absolute(), f"absolute manifest path: {raw}")
    require(all(part not in {"", ".", ".."} for part in path.parts), f"unsafe manifest path: {raw}")
    normalized = path.as_posix()
    require(normalized == raw and "\\" not in raw, f"noncanonical manifest path: {raw}")
    return normalized


def parse_mode(raw: Any, label: str) -> int:
    require(isinstance(raw, str) and len(raw) == 4 and all(char in "01234567" for char in raw),
            f"invalid mode: {label}")
    return int(raw, 8)


def mode_text(mode: int) -> str:
    return f"{stat.S_IMODE(mode):04o}"


def fingerprint(metadata: os.stat_result) -> Fingerprint:
    return Fingerprint(
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        stat.S_IMODE(metadata.st_mode),
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        metadata.st_nlink,
    )


def same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino, stat.S_IFMT(left.st_mode)) == (
        right.st_dev, right.st_ino, stat.S_IFMT(right.st_mode)
    )


def manifest_relative(root: Path, manifest: Path) -> str:
    root_absolute = Path(os.path.abspath(root))
    manifest_absolute = Path(os.path.abspath(manifest))
    try:
        relative = manifest_absolute.relative_to(root_absolute).as_posix()
    except ValueError as exc:
        raise CustodyError("custody manifest must be inside the custody root") from exc
    return safe_relative(relative)


def open_root(root: Path) -> tuple[int, os.stat_result]:
    requested = Path(os.path.abspath(root))
    before = os.stat(requested, follow_symlinks=False)
    require(stat.S_ISDIR(before.st_mode), f"custody root is not a real directory: {requested}")
    fd = os.open(requested, os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        require(same_identity(before, opened), "custody root changed while opening")
        after = os.stat(requested, follow_symlinks=False)
        require(fingerprint(after) == fingerprint(opened), "custody root changed after opening")
        return fd, opened
    except BaseException:
        os.close(fd)
        raise


def open_directory(parent_fd: int, name: str, relative: str) -> tuple[int, os.stat_result]:
    before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    require(stat.S_ISDIR(before.st_mode), f"non-directory traversal member: {relative}")
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
    try:
        opened = os.fstat(fd)
        require(fingerprint(before) == fingerprint(opened), f"directory changed while opening: {relative}")
        after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(fingerprint(after) == fingerprint(opened), f"directory pathname changed after opening: {relative}")
        return fd, opened
    except BaseException:
        os.close(fd)
        raise


def hash_open_regular(parent_fd: int, name: str, relative: str) -> tuple[dict[str, Any], Fingerprint]:
    before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    require(stat.S_ISREG(before.st_mode), f"non-regular delivery member: {relative}")
    fd = os.open(name, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
    try:
        opened = os.fstat(fd)
        require(fingerprint(before) == fingerprint(opened), f"file changed while opening: {relative}")
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, BUFFER_SIZE)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
        hook = _TEST_AFTER_FILE_HASH_HOOK
        if hook is not None:
            hook(parent_fd, name, relative)
        post_fd = os.fstat(fd)
        require(fingerprint(post_fd) == fingerprint(opened), f"file changed while hashing: {relative}")
        post_path = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(fingerprint(post_path) == fingerprint(opened), f"file pathname changed after hashing: {relative}")
        require(total == opened.st_size, f"file size changed while hashing: {relative}")
        return ({
            "path": relative,
            "sha256": digest.hexdigest(),
            "size_bytes": total,
            "mode": mode_text(opened.st_mode),
        }, fingerprint(opened))
    finally:
        os.close(fd)


def open_parent_fd(root_fd: int, relative: str) -> tuple[int, str]:
    parts = PurePosixPath(safe_relative(relative)).parts
    fd = os.dup(root_fd)
    try:
        prefix: list[str] = []
        for component in parts[:-1]:
            prefix.append(component)
            child, _metadata = open_directory(fd, component, "/".join(prefix))
            os.close(fd)
            fd = child
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def read_manifest(root_fd: int, relative: str) -> tuple[dict[str, Any], Fingerprint]:
    parent_fd, name = open_parent_fd(root_fd, relative)
    try:
        entry, observed = hash_open_regular(parent_fd, name, relative)
        fd = os.open(name, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
        try:
            raw = b""
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, BUFFER_SIZE)
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks)
            require(len(raw) == entry["size_bytes"], "manifest changed between authenticated reads")
            require(hashlib.sha256(raw).hexdigest() == entry["sha256"], "manifest bytes changed between reads")
        finally:
            os.close(fd)
        value = strict_json_loads(raw.decode("utf-8"))
        require(isinstance(value, dict), "delivery manifest must be an object")
        return value, observed
    finally:
        os.close(parent_fd)


def scan_tree(root_fd: int, manifest_path: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Fingerprint | None]:
    directories: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    manifest_fingerprint: Fingerprint | None = None

    def walk(fd: int, prefix: str) -> None:
        nonlocal manifest_fingerprint
        start = fingerprint(os.fstat(fd))
        names = sorted(os.listdir(fd), key=os.fsencode)
        for name in names:
            require(name not in {"", ".", ".."} and "/" not in name, f"unsafe delivery name: {name!r}")
            relative = f"{prefix}/{name}" if prefix else name
            safe_relative(relative)
            metadata = os.stat(name, dir_fd=fd, follow_symlinks=False)
            file_type = stat.S_IFMT(metadata.st_mode)
            if file_type == stat.S_IFDIR:
                child, opened = open_directory(fd, name, relative)
                directories.append({"path": relative, "mode": mode_text(opened.st_mode)})
                try:
                    walk(child, relative)
                    post = os.fstat(child)
                    require(fingerprint(post) == fingerprint(opened), f"directory changed during traversal: {relative}")
                finally:
                    os.close(child)
                path_post = os.stat(name, dir_fd=fd, follow_symlinks=False)
                require(fingerprint(path_post) == fingerprint(opened), f"directory pathname changed after traversal: {relative}")
            elif file_type == stat.S_IFREG:
                entry, observed = hash_open_regular(fd, name, relative)
                if relative == manifest_path:
                    manifest_fingerprint = observed
                else:
                    files.append(entry)
            else:
                raise CustodyError(f"link or special delivery member rejected: {relative}")
        require(fingerprint(os.fstat(fd)) == start, f"directory changed while listing: {prefix or '.'}")

    walk(root_fd, "")
    directories.sort(key=lambda item: item["path"])
    files.sort(key=lambda item: item["path"])
    return directories, files, manifest_fingerprint


def validate_directory(raw: Any, index: int) -> dict[str, Any]:
    require(isinstance(raw, dict) and set(raw) == {"path", "mode"},
            f"manifest directory fields changed: {index}")
    path = safe_relative(raw["path"])
    parse_mode(raw["mode"], path)
    return {"path": path, "mode": raw["mode"]}


def validate_file(raw: Any, index: int) -> dict[str, Any]:
    require(isinstance(raw, dict), f"manifest file {index} is not an object")
    require(set(raw) == {"path", "sha256", "size_bytes", "mode"}, f"manifest file fields changed: {index}")
    path = safe_relative(raw["path"])
    sha = raw["sha256"]
    require(isinstance(sha, str) and len(sha) == 64 and all(char in "0123456789abcdef" for char in sha),
            f"invalid SHA-256: {path}")
    require(type(raw["size_bytes"]) is int and raw["size_bytes"] >= 0, f"invalid size: {path}")
    parse_mode(raw["mode"], path)
    return {"path": path, "sha256": sha, "size_bytes": raw["size_bytes"], "mode": raw["mode"]}


def create(root: Path, manifest: Path, label: str) -> dict[str, Any]:
    relative = manifest_relative(root, manifest)
    root_fd, root_metadata = open_root(root)
    try:
        directories, files, _existing_manifest = scan_tree(root_fd, relative)
    finally:
        os.close(root_fd)
    value = {
        "schema_id": SCHEMA_ID,
        "root_label": label,
        "root": {"mode": mode_text(root_metadata.st_mode)},
        "manifest": {"path": relative, "mode": "0444"},
        "directories": directories,
        "files": files,
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{manifest.name}.", dir=manifest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o444)
        os.replace(temporary, manifest)
        directory_fd = os.open(manifest.parent, os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return value


def verify(root: Path, manifest: Path) -> dict[str, Any]:
    relative = manifest_relative(root, manifest)
    root_fd, root_opened = open_root(root)
    try:
        value, initial_manifest = read_manifest(root_fd, relative)
        require(set(value) == {"schema_id", "root_label", "root", "manifest", "directories", "files"},
                "manifest top-level fields changed")
        require(value["schema_id"] == SCHEMA_ID, "wrong delivery-custody schema")
        require(isinstance(value["root_label"], str) and value["root_label"], "invalid root label")
        require(isinstance(value["root"], dict) and set(value["root"]) == {"mode"}, "invalid root record")
        expected_root_mode = parse_mode(value["root"]["mode"], ".")
        require(stat.S_IMODE(root_opened.st_mode) == expected_root_mode, "custody root mode mismatch")
        require(isinstance(value["manifest"], dict) and set(value["manifest"]) == {"path", "mode"},
                "invalid manifest record")
        require(safe_relative(value["manifest"]["path"]) == relative, "manifest path disagreement")
        expected_manifest_mode = parse_mode(value["manifest"]["mode"], relative)
        require(initial_manifest.mode == expected_manifest_mode, "custody manifest mode mismatch")
        require(isinstance(value["directories"], list), "manifest directories must be an array")
        require(isinstance(value["files"], list), "manifest files must be an array")
        expected_directories = [validate_directory(raw, index) for index, raw in enumerate(value["directories"])]
        expected_files = [validate_file(raw, index) for index, raw in enumerate(value["files"])]
        dir_paths = [entry["path"] for entry in expected_directories]
        file_paths = [entry["path"] for entry in expected_files]
        require(dir_paths == sorted(dir_paths) and len(dir_paths) == len(set(dir_paths)),
                "manifest directory paths are not unique and sorted")
        require(file_paths == sorted(file_paths) and len(file_paths) == len(set(file_paths)),
                "manifest file paths are not unique and sorted")
        require(relative not in file_paths and relative not in dir_paths, "manifest self-entry is invalid")
        require(not (set(dir_paths) & set(file_paths)), "manifest path is both file and directory")
        observed_directories, observed_files, observed_manifest = scan_tree(root_fd, relative)
        require(observed_manifest is not None, "custody manifest disappeared during tree scan")
        require(observed_manifest == initial_manifest, "custody manifest changed during verification")
        require(observed_directories == expected_directories, "delivery directory set or modes disagree")
        require(observed_files == expected_files, "delivery file set, bytes, sizes, or modes disagree")
        root_post_fd = os.fstat(root_fd)
        require(fingerprint(root_post_fd) == fingerprint(root_opened), "custody root changed during verification")
        root_post_path = os.stat(Path(os.path.abspath(root)), follow_symlinks=False)
        require(fingerprint(root_post_path) == fingerprint(root_opened), "custody root pathname changed during verification")
        return value
    finally:
        os.close(root_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", action="store_true")
    action.add_argument("--verify", action="store_true")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--label", default="x64lens-delivery")
    args = parser.parse_args()
    if args.create:
        value = create(args.root, args.manifest, args.label)
        print(
            "delivery-custody-create: ok "
            f"schema={SCHEMA_ID} directories={len(value['directories'])} "
            f"files={len(value['files'])} manifest={args.manifest}"
        )
    else:
        value = verify(args.root, args.manifest)
        print(
            "delivery-custody-verify: ok "
            f"schema={SCHEMA_ID} directories={len(value['directories'])} "
            f"files={len(value['files'])} manifest={args.manifest}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CustodyError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"verify-delivery-custody: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
