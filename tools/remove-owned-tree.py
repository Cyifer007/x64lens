#!/usr/bin/env python3
"""Remove one caller-owned temporary tree without following substituted paths.

The caller records the temporary directory's device/inode identity immediately
at creation. Removal atomically quarantines only that exact directory beneath
its retained parent, restores owner traversal on retained directory descriptors,
and removes every observed member through an identity-bound two-stage
quarantine. A foreign replacement at an original or quarantined pathname is
preserved and cleanup fails closed.
"""
from __future__ import annotations

import argparse
import ctypes
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
    """Raised when cleanup cannot prove ownership of the object being removed."""


def require(ok: bool, message: str) -> None:
    if not ok:
        raise CleanupError(message)


def safe_name(name: str, label: str) -> None:
    require(name not in {"", ".", ".."} and "/" not in name, f"unsafe removal name: {label}")


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


def restore_or_preserve(parent_fd: int, quarantine: str, original: str, label: str) -> None:
    """Restore a rejected object without overwriting a late replacement."""
    try:
        rename_noreplace(parent_fd, quarantine, original)
    except OSError as restore_error:
        raise CleanupError(
            f"object changed and remains quarantined as {quarantine}: {label}: {restore_error}"
        ) from restore_error


def quarantine_expected(
    parent_fd: int,
    name: str,
    expected: os.stat_result,
    *,
    label: str,
) -> tuple[str, os.stat_result]:
    """Move one name, then prove the moved object is the one just observed."""
    safe_name(name, label)
    quarantine = f".{name}.x64lens-cleanup.{os.getpid()}.{uuid.uuid4().hex}.owned"
    rename_noreplace(parent_fd, name, quarantine)
    observed = os.stat(quarantine, dir_fd=parent_fd, follow_symlinks=False)
    if (
        observed.st_dev,
        observed.st_ino,
        stat.S_IFMT(observed.st_mode),
    ) != (
        expected.st_dev,
        expected.st_ino,
        stat.S_IFMT(expected.st_mode),
    ):
        restore_or_preserve(parent_fd, quarantine, name, label)
        raise CleanupError(f"object changed before quarantine: {label}")
    return quarantine, observed


def unlinkat_expected(
    parent_fd: int,
    name: str,
    *,
    expected_identity: tuple[int, int],
    expected_type: int,
    directory: bool,
    label: str,
) -> None:
    """Atomically remove only one exact quarantined object.

    The name is moved a second time before identity is inspected. A late
    replacement is restored when possible and is never unlinked. The UUID name
    is private to this invocation; a same-UID principal able to predict and race
    those names is outside this helper's trust boundary.
    """
    safe_name(name, label)
    final = f".{name}.x64lens-cleanup.{os.getpid()}.{uuid.uuid4().hex}.final"
    rename_noreplace(parent_fd, name, final)
    observed = os.stat(final, dir_fd=parent_fd, follow_symlinks=False)
    if (
        observed.st_dev,
        observed.st_ino,
        stat.S_IFMT(observed.st_mode),
    ) != (
        expected_identity[0],
        expected_identity[1],
        expected_type,
    ):
        restore_or_preserve(parent_fd, final, name, label)
        raise CleanupError(f"object changed before final removal: {label}")
    try:
        unlinkat(parent_fd, final, directory=directory)
        os.fsync(parent_fd)
    except OSError as exc:
        raise CleanupError(f"authenticated removal failed for {label}: {exc}") from exc


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
            opened = os.fstat(child)
            require(
                (opened.st_dev, opened.st_ino) == (expected.st_dev, expected.st_ino),
                f"parent component changed while opening: {component}",
            )
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
    """Clear one retained directory without deleting a late replacement."""
    metadata = os.fstat(directory_fd)
    require(stat.S_ISDIR(metadata.st_mode) and metadata.st_dev == device, f"{label} changed filesystem/type")
    os.fchmod(directory_fd, 0o700)
    for name in sorted(os.listdir(directory_fd)):
        safe_name(name, f"{label}/{name}")
        member = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        require(member.st_dev == device, f"member crossed filesystem boundary: {name}")
        quarantine, moved = quarantine_expected(directory_fd, name, member, label=f"{label}/{name}")
        member_type = stat.S_IFMT(moved.st_mode)
        identity = (moved.st_dev, moved.st_ino)
        if stat.S_ISDIR(moved.st_mode):
            child = os.open(
                quarantine,
                os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW,
                dir_fd=directory_fd,
            )
            try:
                opened = os.fstat(child)
                require(
                    (opened.st_dev, opened.st_ino, stat.S_IFMT(opened.st_mode))
                    == (identity[0], identity[1], member_type),
                    f"directory changed while opening: {label}/{name}",
                )
                clear(child, device, f"{label}/{name}")
            finally:
                os.close(child)
            unlinkat_expected(
                directory_fd,
                quarantine,
                expected_identity=identity,
                expected_type=member_type,
                directory=True,
                label=f"{label}/{name}",
            )
        else:
            # No target is followed for symlinks or other non-directory names.
            # Final removal remains bound to the observed device/inode/type.
            unlinkat_expected(
                directory_fd,
                quarantine,
                expected_identity=identity,
                expected_type=member_type,
                directory=False,
                label=f"{label}/{name}",
            )


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
    quarantine = f".{name}.x64lens-cleanup.{os.getpid()}.{uuid.uuid4().hex}.root"
    try:
        try:
            metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return
        require(stat.S_ISDIR(metadata.st_mode), "owned path became non-directory")
        require((metadata.st_dev, metadata.st_ino) == expected, "owned path identity changed before cleanup")
        rename_noreplace(parent_fd, name, quarantine)
        qmeta = os.stat(quarantine, dir_fd=parent_fd, follow_symlinks=False)
        require(stat.S_ISDIR(qmeta.st_mode), "quarantined path is not a directory")
        require((qmeta.st_dev, qmeta.st_ino) == expected, "quarantined path identity changed")
        root_fd = os.open(
            quarantine,
            os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW,
            dir_fd=parent_fd,
        )
        try:
            opened = os.fstat(root_fd)
            require((opened.st_dev, opened.st_ino) == expected, "quarantined path changed while opening")
            clear(root_fd, opened.st_dev, str(path))
        finally:
            os.close(root_fd)
        unlinkat_expected(
            parent_fd,
            quarantine,
            expected_identity=expected,
            expected_type=stat.S_IFDIR,
            directory=True,
            label=str(path),
        )
    finally:
        # A failed proof leaves the authenticated or foreign object at a unique
        # quarantine name. Never delete a name whose current identity is unknown.
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
