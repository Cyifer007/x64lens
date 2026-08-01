#!/usr/bin/env python3
"""Remove one caller-owned temporary tree without following substituted paths.

The caller records a versioned creation-time directory identity immediately
before use. Cleanup traverses parent components descriptor-relatively, moves
members through fixed-length no-replace quarantine names, and reauthenticates
the final name inside the low-level unlink boundary. Foreign replacements are
preserved and cleanup fails closed.

Linux does not provide unlink-by-file-descriptor. The remaining trust boundary
is a same-UID process that can predict a fresh 128-bit quarantine name and win
the final identity-check-to-unlink interval. Quarantine names are random,
shorter than NAME_MAX, and never derived from hostile member names.
"""
from __future__ import annotations

import argparse
import ctypes
import os
from pathlib import Path
import stat
import sys
from typing import NamedTuple
import uuid

RENAME_NOREPLACE = 1
AT_REMOVEDIR = 0x200
O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
O_PATH = getattr(os, "O_PATH", os.O_RDONLY)
IDENTITY_VERSION = "v3"
LIBC = ctypes.CDLL(None, use_errno=True)
RENAMEAT2 = getattr(LIBC, "renameat2", None)
UNLINKAT = getattr(LIBC, "unlinkat", None)
if RENAMEAT2 is not None:
    RENAMEAT2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    RENAMEAT2.restype = ctypes.c_int
if UNLINKAT is not None:
    UNLINKAT.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    UNLINKAT.restype = ctypes.c_int


class StatxTimestamp(ctypes.Structure):
    _fields_ = [
        ("tv_sec", ctypes.c_longlong),
        ("tv_nsec", ctypes.c_uint),
        ("__reserved", ctypes.c_int),
    ]


class Statx(ctypes.Structure):
    _fields_ = [
        ("stx_mask", ctypes.c_uint),
        ("stx_blksize", ctypes.c_uint),
        ("stx_attributes", ctypes.c_ulonglong),
        ("stx_nlink", ctypes.c_uint),
        ("stx_uid", ctypes.c_uint),
        ("stx_gid", ctypes.c_uint),
        ("stx_mode", ctypes.c_ushort),
        ("__spare0", ctypes.c_ushort),
        ("stx_ino", ctypes.c_ulonglong),
        ("stx_size", ctypes.c_ulonglong),
        ("stx_blocks", ctypes.c_ulonglong),
        ("stx_attributes_mask", ctypes.c_ulonglong),
        ("stx_atime", StatxTimestamp),
        ("stx_btime", StatxTimestamp),
        ("stx_ctime", StatxTimestamp),
        ("stx_mtime", StatxTimestamp),
        ("stx_rdev_major", ctypes.c_uint),
        ("stx_rdev_minor", ctypes.c_uint),
        ("stx_dev_major", ctypes.c_uint),
        ("stx_dev_minor", ctypes.c_uint),
        ("stx_mnt_id", ctypes.c_ulonglong),
        ("stx_dio_mem_align", ctypes.c_uint),
        ("stx_dio_offset_align", ctypes.c_uint),
        ("__spare3", ctypes.c_ulonglong * 12),
    ]


STATX_BASIC_STATS = 0x07FF
STATX_BTIME = 0x0800
STATX_MNT_ID = 0x1000
AT_SYMLINK_NOFOLLOW = 0x100
AT_EMPTY_PATH = 0x1000
STATX = getattr(LIBC, "statx", None)
if STATX is not None:
    STATX.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Statx)]
    STATX.restype = ctypes.c_int


def stable_fd_identity(fd: int) -> RootIdentity:
    """Return a generation-qualified identity for one already-open object."""
    require(STATX is not None, "Linux statx is required for ABA-resistant cleanup identity")
    value = Statx()
    mask = STATX_BASIC_STATS | STATX_BTIME | STATX_MNT_ID
    rc = STATX(fd, b"", AT_EMPTY_PATH | AT_SYMLINK_NOFOLLOW, mask, ctypes.byref(value))
    if rc != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    require(value.stx_mask & STATX_BTIME, "filesystem does not expose statx birth time for cleanup identity")
    require(value.stx_mask & STATX_MNT_ID, "kernel does not expose statx mount identity for cleanup")
    birth_ns = int(value.stx_btime.tv_sec) * 1_000_000_000 + int(value.stx_btime.tv_nsec)
    require(birth_ns > 0, "filesystem returned an unusable birth time for cleanup identity")
    metadata = os.fstat(fd)
    statx_device = os.makedev(int(value.stx_dev_major), int(value.stx_dev_minor))
    require(
        (statx_device, int(value.stx_ino), stat.S_IFMT(int(value.stx_mode)))
        == (metadata.st_dev, metadata.st_ino, stat.S_IFMT(metadata.st_mode)),
        "statx and fstat identity disagree",
    )
    return RootIdentity(metadata.st_dev, metadata.st_ino, birth_ns, int(value.stx_mnt_id))


class CleanupError(RuntimeError):
    """Raised when cleanup cannot prove ownership of the object being removed."""


class RootIdentity(NamedTuple):
    """Creation-time root identity carried by the command-line token."""

    device: int
    inode: int
    birth_ns: int
    mount_id: int


class Fingerprint(NamedTuple):
    """Generation-qualified fingerprint checked immediately inside unlinkat()."""

    device: int
    inode: int
    birth_ns: int
    mount_id: int
    ctime_ns: int
    file_type: int
    uid: int
    gid: int
    size: int
    nlink: int


# The entry exists only while unlinkat_expected() is making one authenticated
# call. Keeping the expectation outside the public function arguments also lets
# an adversarial regression wrap unlinkat(), replace the name, and call the real
# function while the real function still performs the final check.
_PENDING_REMOVALS: dict[tuple[int, str, bool], Fingerprint] = {}


def require(ok: bool, message: str) -> None:
    if not ok:
        raise CleanupError(message)


def safe_name(name: str, label: str) -> None:
    require(name not in {"", ".", ".."} and "/" not in name, f"unsafe removal name: {label}")


def fingerprint_fd(fd: int) -> Fingerprint:
    metadata = os.fstat(fd)
    generation = stable_fd_identity(fd)
    return Fingerprint(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        birth_ns=generation.birth_ns,
        mount_id=generation.mount_id,
        ctime_ns=metadata.st_ctime_ns,
        file_type=stat.S_IFMT(metadata.st_mode),
        uid=metadata.st_uid,
        gid=metadata.st_gid,
        size=metadata.st_size,
        nlink=metadata.st_nlink,
    )


def same_object(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        stat.S_IFMT(left.st_mode),
    ) == (
        right.st_dev,
        right.st_ino,
        stat.S_IFMT(right.st_mode),
    )


def quarantine_name(parent_fd: int, phase: str) -> str:
    """Return a fixed-length, unguessable component within the filesystem cap."""
    require(phase in {"owned", "final", "root"}, f"unknown quarantine phase: {phase}")
    name = f".x64lens-cleanup.{os.getpid():x}.{uuid.uuid4().hex}.{phase}"
    try:
        name_max = os.fpathconf(parent_fd, "PC_NAME_MAX")
    except (OSError, ValueError):
        name_max = 255
    require(len(os.fsencode(name)) <= int(name_max), "generated quarantine name exceeds NAME_MAX")
    return name


def rename_noreplace(parent_fd: int, old: str, new: str) -> None:
    require(RENAMEAT2 is not None, "Linux renameat2 is required")
    safe_name(old, old)
    safe_name(new, new)
    rc = RENAMEAT2(parent_fd, os.fsencode(old), parent_fd, os.fsencode(new), RENAME_NOREPLACE)
    if rc != 0:
        value = ctypes.get_errno()
        raise OSError(value, os.strerror(value), old)


def unlinkat(parent_fd: int, name: str, *, directory: bool = False) -> None:
    """Perform one unlink only after an in-function final fingerprint check."""
    require(UNLINKAT is not None, "Linux unlinkat is required")
    safe_name(name, name)
    key = (parent_fd, name, directory)
    expected = _PENDING_REMOVALS.get(key)
    require(expected is not None, f"unauthenticated unlink attempt: {name}")
    try:
        observed_fd = open_nofollow(parent_fd, name, directory=directory)
    except FileNotFoundError as exc:
        raise CleanupError(f"authenticated removal name disappeared: {name}") from exc
    try:
        require(fingerprint_fd(observed_fd) == expected,
                f"object changed at final unlink boundary: {name}")
    finally:
        os.close(observed_fd)
    rc = UNLINKAT(parent_fd, os.fsencode(name), AT_REMOVEDIR if directory else 0)
    if rc != 0:
        value = ctypes.get_errno()
        raise OSError(value, os.strerror(value), name)


def restore_or_preserve(parent_fd: int, quarantine: str, original: str, label: str) -> None:
    """Restore a rejected object without overwriting a late replacement."""
    try:
        rename_noreplace(parent_fd, quarantine, original)
    except OSError as restore_error:
        raise CleanupError(
            f"object changed and remains quarantined as {quarantine}: {label}: {restore_error}"
        ) from restore_error


def open_nofollow(parent_fd: int, name: str, *, directory: bool) -> int:
    flags = O_PATH | O_CLOEXEC | O_NOFOLLOW
    if directory:
        flags |= os.O_DIRECTORY
    return os.open(name, flags, dir_fd=parent_fd)


def quarantine_expected(
    parent_fd: int,
    name: str,
    expected: os.stat_result,
    *,
    label: str,
) -> tuple[str, int, os.stat_result]:
    """Hold, move, and prove the exact object observed at one directory name."""
    safe_name(name, label)
    held_fd = open_nofollow(parent_fd, name, directory=stat.S_ISDIR(expected.st_mode))
    try:
        held = os.fstat(held_fd)
        require(same_object(held, expected), f"object changed while opening before quarantine: {label}")
        quarantine = quarantine_name(parent_fd, "owned")
        rename_noreplace(parent_fd, name, quarantine)
        observed = os.stat(quarantine, dir_fd=parent_fd, follow_symlinks=False)
        require(same_object(observed, os.fstat(held_fd)), f"object changed before quarantine: {label}")
        return quarantine, held_fd, observed
    except BaseException:
        os.close(held_fd)
        raise


def unlinkat_expected(
    parent_fd: int,
    name: str,
    *,
    held_fd: int,
    directory: bool,
    label: str,
) -> None:
    """Move to a fresh final name and remove only the descriptor-held object."""
    safe_name(name, label)
    final = quarantine_name(parent_fd, "final")
    rename_noreplace(parent_fd, name, final)
    observed = os.stat(final, dir_fd=parent_fd, follow_symlinks=False)
    held = os.fstat(held_fd)
    if not same_object(observed, held):
        restore_or_preserve(parent_fd, final, name, label)
        raise CleanupError(f"object changed before final removal: {label}")
    require(stat.S_ISDIR(observed.st_mode) == directory, f"object type changed before final removal: {label}")
    key = (parent_fd, final, directory)
    require(key not in _PENDING_REMOVALS, "duplicate pending removal key")
    _PENDING_REMOVALS[key] = fingerprint_fd(held_fd)
    try:
        unlinkat(parent_fd, final, directory=directory)
        os.fsync(parent_fd)
    except (CleanupError, OSError) as exc:
        raise CleanupError(f"authenticated removal failed for {label}: {exc}") from exc
    finally:
        _PENDING_REMOVALS.pop(key, None)


def open_parent(path: Path) -> tuple[int, str]:
    absolute = Path(os.path.abspath(path))
    name = absolute.name
    require(name not in {"", ".", ".."}, "unsafe final component")
    flags = os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        for component in absolute.parent.parts[1:]:
            require(component not in {"", ".", ".."}, "unsafe parent component")
            expected = os.stat(component, dir_fd=fd, follow_symlinks=False)
            require(stat.S_ISDIR(expected.st_mode), f"parent component is not a directory: {component}")
            child = os.open(component, flags, dir_fd=fd)
            try:
                opened = os.fstat(child)
                require(
                    (opened.st_dev, opened.st_ino) == (expected.st_dev, expected.st_ino),
                    f"parent component changed while opening: {component}",
                )
            except BaseException:
                os.close(child)
                raise
            os.close(fd)
            fd = child
        return fd, name
    except BaseException:
        os.close(fd)
        raise


def parse_identity(raw: str) -> RootIdentity:
    parts = raw.split(":")
    require(
        len(parts) == 5 and parts[0] == IDENTITY_VERSION and all(value.isdigit() for value in parts[1:]),
        "identity must be v3:DEV:INO:BIRTH_NS:MOUNT_ID",
    )
    return RootIdentity(int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))


def clear(directory_fd: int, device: int, label: str) -> None:
    """Clear one retained directory without deleting a late replacement."""
    metadata = os.fstat(directory_fd)
    require(stat.S_ISDIR(metadata.st_mode) and metadata.st_dev == device, f"{label} changed filesystem/type")
    os.fchmod(directory_fd, 0o700)
    for name in sorted(os.listdir(directory_fd)):
        safe_name(name, f"{label}/{name}")
        member = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        require(member.st_dev == device, f"member crossed filesystem boundary: {name}")
        quarantine, held_fd, moved = quarantine_expected(directory_fd, name, member, label=f"{label}/{name}")
        try:
            if stat.S_ISDIR(moved.st_mode):
                # Reopen for directory reads because O_PATH descriptors cannot be
                # listed, then authenticate that descriptor against the held one.
                child = os.open(
                    quarantine,
                    os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW,
                    dir_fd=directory_fd,
                )
                try:
                    require(same_object(os.fstat(child), os.fstat(held_fd)),
                            f"directory changed while opening: {label}/{name}")
                    clear(child, device, f"{label}/{name}")
                finally:
                    os.close(child)
                unlinkat_expected(
                    directory_fd,
                    quarantine,
                    held_fd=held_fd,
                    directory=True,
                    label=f"{label}/{name}",
                )
            else:
                unlinkat_expected(
                    directory_fd,
                    quarantine,
                    held_fd=held_fd,
                    directory=False,
                    label=f"{label}/{name}",
                )
        finally:
            os.close(held_fd)


def identify(path: Path) -> str:
    parent_fd, name = open_parent(path)
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(stat.S_ISDIR(metadata.st_mode), "owned path is not a directory")
        held_fd = open_nofollow(parent_fd, name, directory=True)
        try:
            require(same_object(os.fstat(held_fd), metadata), "owned path changed while identifying")
            value = stable_fd_identity(held_fd)
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            require(same_object(current, os.fstat(held_fd)), "owned path changed before identity return")
            return f"{IDENTITY_VERSION}:{value.device}:{value.inode}:{value.birth_ns}:{value.mount_id}"
        finally:
            os.close(held_fd)
    finally:
        os.close(parent_fd)


def remove(path: Path, expected: RootIdentity) -> None:
    require(isinstance(expected, RootIdentity), "strong v3 root identity is required")
    parent_fd, name = open_parent(path)
    root_fd = -1
    quarantine = quarantine_name(parent_fd, "root")
    try:
        try:
            metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        require(stat.S_ISDIR(metadata.st_mode), "owned path became non-directory")
        root_fd = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        opened = os.fstat(root_fd)
        require(same_object(opened, metadata), "owned path changed while opening")
        observed_identity = stable_fd_identity(root_fd)
        require(observed_identity == expected, "owned path identity changed before cleanup")
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(same_object(current, opened), "owned path changed before quarantine")
        rename_noreplace(parent_fd, name, quarantine)
        qmeta = os.stat(quarantine, dir_fd=parent_fd, follow_symlinks=False)
        require(same_object(qmeta, os.fstat(root_fd)), "quarantined path identity changed")
        clear(root_fd, opened.st_dev, str(path))
        unlinkat_expected(
            parent_fd,
            quarantine,
            held_fd=root_fd,
            directory=True,
            label=str(path),
        )
    finally:
        if root_fd >= 0:
            os.close(root_fd)
        os.close(parent_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--identify", type=Path)
    action.add_argument("--remove", type=Path)
    parser.add_argument("--identity")
    args = parser.parse_args()
    if args.identify is not None:
        require(args.identity is None, "--identity is not valid with --identify")
        print(identify(args.identify))
        return 0
    require(args.remove is not None and args.identity is not None, "--remove requires --identity")
    remove(args.remove, parse_identity(args.identity))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CleanupError, OSError, ValueError) as exc:
        print(f"remove-owned-tree: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
