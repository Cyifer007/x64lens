#!/usr/bin/env python3
"""Remove one caller-owned temporary tree without following substituted paths.

The caller records the temporary directory's device/inode identity immediately
at creation. Removal atomically quarantines only that exact directory beneath
its retained parent, restores owner traversal on retained directory descriptors,
removes members descriptor-relatively, and never follows symlinks. A foreign
replacement at the original pathname is preserved.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import os
from pathlib import Path
import stat
import sys
import uuid

RENAME_NOREPLACE = 1
AT_REMOVEDIR = 0x200
O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
LIBC = ctypes.CDLL(None, use_errno=True)
RENAMEAT2 = getattr(LIBC, "renameat2", None)
UNLINKAT = getattr(LIBC, "unlinkat", None)
if RENAMEAT2 is not None:
    RENAMEAT2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    RENAMEAT2.restype = ctypes.c_int
if UNLINKAT is not None:
    UNLINKAT.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    UNLINKAT.restype = ctypes.c_int

class CleanupError(RuntimeError):
    pass

def require(ok: bool, message: str) -> None:
    if not ok:
        raise CleanupError(message)

def rename_noreplace(parent_fd: int, old: str, new: str) -> None:
    require(RENAMEAT2 is not None, "Linux renameat2 is required")
    rc = RENAMEAT2(parent_fd, os.fsencode(old), parent_fd, os.fsencode(new), RENAME_NOREPLACE)
    if rc != 0:
        value = ctypes.get_errno()
        raise OSError(value, os.strerror(value), old)

def unlinkat(parent_fd: int, name: str, *, directory: bool = False) -> None:
    require(UNLINKAT is not None, "Linux unlinkat is required")
    rc = UNLINKAT(parent_fd, os.fsencode(name), AT_REMOVEDIR if directory else 0)
    if rc != 0:
        value = ctypes.get_errno()
        raise OSError(value, os.strerror(value), name)

def open_parent(path: Path) -> tuple[int, str]:
    absolute = Path(os.path.abspath(path))
    name = absolute.name
    require(name not in {"", ".", ".."}, "unsafe final component")
    flags = os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for component in absolute.parent.parts[1:]:
            require(component not in {"", ".", ".."}, "unsafe parent component")
            child = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, name
    except BaseException:
        os.close(fd)
        raise

def parse_identity(raw: str) -> tuple[int, int]:
    parts = raw.split(":")
    require(len(parts) == 2 and all(value.isdigit() for value in parts), "identity must be DEV:INO")
    return int(parts[0]), int(parts[1])

def clear(directory_fd: int, device: int, label: str) -> None:
    metadata = os.fstat(directory_fd)
    require(stat.S_ISDIR(metadata.st_mode) and metadata.st_dev == device, f"{label} changed filesystem/type")
    os.fchmod(directory_fd, 0o700)
    for name in sorted(os.listdir(directory_fd)):
        require(name not in {"", ".", ".."} and "/" not in name, f"unsafe member: {name!r}")
        member = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        require(member.st_dev == device, f"member crossed filesystem boundary: {name}")
        if stat.S_ISDIR(member.st_mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=directory_fd)
            try:
                opened = os.fstat(child)
                require((opened.st_dev, opened.st_ino) == (member.st_dev, member.st_ino), f"directory changed: {name}")
                clear(child, device, f"{label}/{name}")
            finally:
                os.close(child)
            unlinkat(directory_fd, name, directory=True)
        else:
            # Symlinks and other non-directory members are unlinked as names;
            # no target is followed. Result producers are expected to retain
            # regular files only, but cleanup must still be bounded and safe.
            unlinkat(directory_fd, name)

def identify(path: Path) -> str:
    parent_fd, name = open_parent(path)
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(stat.S_ISDIR(metadata.st_mode), "owned path is not a directory")
        return f"{metadata.st_dev}:{metadata.st_ino}"
    finally:
        os.close(parent_fd)

def remove(path: Path, expected: tuple[int, int]) -> None:
    parent_fd, name = open_parent(path)
    quarantine = f".{name}.x64lens-cleanup.{os.getpid()}.{uuid.uuid4().hex}"
    moved = False
    try:
        try:
            metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        require(stat.S_ISDIR(metadata.st_mode), "owned path became non-directory")
        require((metadata.st_dev, metadata.st_ino) == expected, "owned path identity changed before cleanup")
        rename_noreplace(parent_fd, name, quarantine)
        moved = True
        qmeta = os.stat(quarantine, dir_fd=parent_fd, follow_symlinks=False)
        require(stat.S_ISDIR(qmeta.st_mode), "quarantined path is not a directory")
        require((qmeta.st_dev, qmeta.st_ino) == expected, "quarantined path identity changed")
        root_fd = os.open(quarantine, os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
        try:
            opened = os.fstat(root_fd)
            require((opened.st_dev, opened.st_ino) == expected, "quarantined path changed while opening")
            clear(root_fd, opened.st_dev, str(path))
        finally:
            os.close(root_fd)
        unlinkat(parent_fd, quarantine, directory=True)
        moved = False
        os.fsync(parent_fd)
    finally:
        # If cleanup fails after quarantine, preserve the authenticated object
        # at the quarantine name rather than deleting an unproven replacement.
        os.close(parent_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--identify", type=Path)
    group.add_argument("--remove", type=Path)
    parser.add_argument("--identity")
    args = parser.parse_args()
    if args.identify is not None:
        print(identify(args.identify))
        return 0
    require(args.identity is not None, "--identity is required with --remove")
    remove(args.remove, parse_identity(args.identity))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CleanupError, OSError) as exc:
        print(f"remove-owned-tree: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
