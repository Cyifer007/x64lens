#!/usr/bin/env python3
"""Create or verify an exact recursive delivery-custody manifest.

The manifest authenticates every regular file below one root by relative path,
SHA-256, byte size, and mode. The manifest file itself is excluded to avoid a
self-reference. Symlinks, devices, sockets, FIFOs, duplicate paths, unsafe
relative names, missing members, undeclared files, and undeclared empty
directories fail closed.
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
from typing import Any

SCHEMA_ID = "x64lens-delivery-custody-v1"
BUFFER_SIZE = 1024 * 1024


class CustodyError(RuntimeError):
    """Raised when a delivery tree is incomplete, unsafe, or unauthenticated."""


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
    require(normalized == raw, f"noncanonical manifest path: {raw}")
    return normalized


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(BUFFER_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def manifest_relative(root: Path, manifest: Path) -> str | None:
    try:
        return manifest.resolve(strict=False).relative_to(root.resolve(strict=True)).as_posix()
    except ValueError:
        return None


def implied_directories(paths: list[str]) -> list[str]:
    directories: set[str] = set()
    for raw in paths:
        parent = PurePosixPath(raw).parent
        while parent != PurePosixPath("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return sorted(directories)


def scan(root: Path, manifest: Path) -> list[dict[str, Any]]:
    require(root.is_dir() and not root.is_symlink(), f"custody root is not a real directory: {root}")
    excluded = manifest_relative(root, manifest)
    entries: list[dict[str, Any]] = []
    observed_directories: list[str] = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        directories.sort()
        files.sort()
        for name in list(directories):
            path = current_path / name
            metadata = path.lstat()
            require(stat.S_ISDIR(metadata.st_mode), f"non-directory traversal member: {path}")
            require(not path.is_symlink(), f"symbolic-link directory rejected: {path}")
            observed_directories.append(path.relative_to(root).as_posix())
        for name in files:
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            safe_relative(relative)
            if relative == excluded:
                continue
            metadata = path.lstat()
            require(stat.S_ISREG(metadata.st_mode), f"non-regular delivery member: {relative}")
            require(not path.is_symlink(), f"symbolic-link file rejected: {relative}")
            entries.append(
                {
                    "path": relative,
                    "sha256": sha256_file(path),
                    "size_bytes": metadata.st_size,
                    "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                }
            )
    entries.sort(key=lambda entry: entry["path"])
    represented_paths = [entry["path"] for entry in entries]
    if excluded is not None:
        represented_paths.append(excluded)
    expected_directories = implied_directories(represented_paths)
    observed_directories.sort()
    require(
        observed_directories == expected_directories,
        "delivery directory set is not exactly implied by manifested files: "
        f"expected={expected_directories!r} observed={observed_directories!r}",
    )
    return entries


def create(root: Path, manifest: Path, label: str) -> dict[str, Any]:
    entries = scan(root, manifest)
    value = {"schema_id": SCHEMA_ID, "root_label": label, "files": entries}
    manifest.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{manifest.name}.", dir=manifest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, manifest)
        directory_fd = os.open(manifest.parent, os.O_RDONLY | os.O_DIRECTORY)
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


def validate_entry(raw: Any, index: int) -> dict[str, Any]:
    require(isinstance(raw, dict), f"manifest entry {index} is not an object")
    require(set(raw) == {"path", "sha256", "size_bytes", "mode"}, f"manifest entry fields changed: {index}")
    path = safe_relative(raw["path"])
    sha = raw["sha256"]
    require(isinstance(sha, str) and len(sha) == 64 and all(char in "0123456789abcdef" for char in sha),
            f"invalid SHA-256: {path}")
    require(type(raw["size_bytes"]) is int and raw["size_bytes"] >= 0, f"invalid size: {path}")
    mode = raw["mode"]
    require(isinstance(mode, str) and len(mode) == 4 and all(char in "01234567" for char in mode),
            f"invalid mode: {path}")
    return {"path": path, "sha256": sha, "size_bytes": raw["size_bytes"], "mode": mode}


def verify(root: Path, manifest: Path) -> dict[str, Any]:
    metadata = manifest.lstat()
    require(stat.S_ISREG(metadata.st_mode) and not manifest.is_symlink(),
            f"custody manifest is not a regular non-symlink file: {manifest}")
    value = strict_json_loads(manifest.read_text(encoding="utf-8"))
    require(isinstance(value, dict) and set(value) == {"schema_id", "root_label", "files"},
            "manifest top-level fields changed")
    require(value["schema_id"] == SCHEMA_ID, "wrong delivery-custody schema")
    require(isinstance(value["root_label"], str) and value["root_label"], "invalid root label")
    require(isinstance(value["files"], list), "manifest files must be an array")
    expected = [validate_entry(raw, index) for index, raw in enumerate(value["files"])]
    paths = [entry["path"] for entry in expected]
    require(paths == sorted(paths), "manifest paths are not sorted")
    require(len(paths) == len(set(paths)), "duplicate manifest path")
    observed = scan(root, manifest)
    require(observed == expected, "delivery tree does not match the exact custody manifest")
    return value


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
        print(f"delivery-custody-create: ok files={len(value['files'])} manifest={args.manifest}")
    else:
        value = verify(args.root, args.manifest)
        print(f"delivery-custody-verify: ok files={len(value['files'])} manifest={args.manifest}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CustodyError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"verify-delivery-custody: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
