#!/usr/bin/env python3
"""Recover one exact candidate source tree through retained descriptors.

The manifest and TAR are independent authorities: the manifest supplies the
exact Git paths, modes, object IDs, sizes, and SHA-256 values, while the TAR
supplies the bytes.  Recovery writes into an unpredictable sibling staging
root beneath an already existing, no-follow destination parent.  Every created
directory and file descriptor is retained through a second full closure pass.
Publication uses Linux ``renameat2(RENAME_NOREPLACE)`` and therefore cannot
replace a destination raced into place.

Failure cleanup is ownership-qualified.  The helper first moves the staging
name to fresh quarantine names without replacement and reauthenticates the
retained root descriptor before recursive removal.  A foreign substitution is
preserved and reported rather than deleted.  Linux has no atomic compare-and-
unlink-by-descriptor primitive; a malicious concurrent same-UID process remains
an explicit external threat boundary, but the deterministic check/use and
path-based rollback defects covered by the project regressions fail closed.
"""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import errno
import hashlib
import json
import os
import signal
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
import resource
import shutil
import stat
import sys
import tarfile
from typing import Any, BinaryIO, Callable, NamedTuple

BUFFER_SIZE = 1024 * 1024
MAX_SOURCE_FILES = 4096
MAX_SOURCE_DIRECTORIES = 1024
MAX_SOURCE_FILE_BYTES = 64 * 1024 * 1024
MAX_SOURCE_TOTAL_BYTES = 512 * 1024 * 1024
MAX_SOURCE_ARCHIVE_BYTES = 1024 * 1024 * 1024
MIN_FD_HEADROOM = 64
O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
RENAME_NOREPLACE = 1

# Durable regressions inject races only through these hooks.
_TEST_AFTER_STAGE_MKDIR_EFFECT_HOOK: Callable[[int, str], None] | None = None
_TEST_AFTER_PUBLISH_RENAME_EFFECT_HOOK: Callable[[int, str], None] | None = None
_TEST_AFTER_INITIAL_VERIFY_HOOK: Callable[[int, str, int], None] | None = None
_TEST_BEFORE_PUBLISH_HOOK: Callable[[int, str, str], None] | None = None
_TEST_AFTER_PUBLISH_HOOK: Callable[[int, str, int], None] | None = None
_TEST_BEFORE_CLEANUP_HOOK: Callable[[int, str, int], None] | None = None
_TEST_BEFORE_FINAL_RMTREE_HOOK: Callable[[int, str, int], None] | None = None


class RecoveryError(RuntimeError):
    """Raised when source bytes, topology, identity, or publication disagree."""


class CatchableTermination(RecoveryError):
    """Raised when a catchable termination signal interrupts recovery."""


@contextmanager
def defer_catchable_signals():
    """Defer HUP/INT/TERM across filesystem effect/bookkeeping pairs."""
    guarded = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM}
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, guarded)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


@contextmanager
def catchable_termination_guard(label: str):
    """Turn HUP/INT/TERM into recoverable exceptions during mutation."""
    guarded = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    previous = {sig: signal.getsignal(sig) for sig in guarded}

    def handler(signum, _frame):
        for candidate in guarded:
            signal.signal(candidate, signal.SIG_IGN)
        raise CatchableTermination(f"{label} interrupted by {signal.Signals(signum).name}")

    for sig in guarded:
        signal.signal(sig, handler)
    try:
        yield
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)


class StableIdentity(NamedTuple):
    device: int
    inode: int
    file_type: int
    uid: int
    gid: int


class FileFingerprint(NamedTuple):
    """Stable file topology/content metadata excluding read-mutated atime."""

    device: int
    inode: int
    mode: int
    links: int
    uid: int
    gid: int
    size: int
    mtime_ns: int
    ctime_ns: int


@dataclass
class AncestorBinding:
    parent_fd: int
    name: str
    child_fd: int
    opened: StableIdentity
    display: str


@dataclass
class ParentHandle:
    requested: Path
    fd: int
    bindings: list[AncestorBinding]


@dataclass
class DirectoryRecord:
    path: str
    name: str
    parent_fd: int
    fd: int
    opened: StableIdentity


@dataclass
class FileRecord:
    path: str
    name: str
    parent_fd: int
    fd: int
    opened: StableIdentity
    sha256: str
    size: int
    mode: int
    git_oid: str


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RecoveryError(message)


def open_fd_count() -> int:
    """Return the current process descriptor population without retaining it."""
    try:
        return sum(1 for name in os.listdir("/proc/self/fd") if name.isdigit())
    except OSError:
        return 16


def recovery_fd_requirement(destination: Path, directory_count: int, file_count: int) -> int:
    """Bound the full retained-descriptor and cleanup peak before mutation."""
    absolute = Path(os.path.abspath(os.fspath(destination)))
    ancestor_count = max(1, len(absolute.parent.parts) - 1)
    current = open_fd_count()
    retained_tree = 1 + directory_count + file_count
    authority_inputs = 4  # TAR, manifest, destination parent, and root.
    cleanup_peak = 4 + min(directory_count + file_count, 8)
    return current + ancestor_count + retained_tree + authority_inputs + cleanup_peak + MIN_FD_HEADROOM


def mkdir_exact(name: str, mode: int, *, dir_fd: int) -> None:
    """Create one directory with a usable exact initial mode under any umask."""
    previous = os.umask(0)
    try:
        os.mkdir(name, mode, dir_fd=dir_fd)
    finally:
        os.umask(previous)


def strict(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def safe(raw: Any) -> str:
    require(isinstance(raw, str), f"member path must be a string: {type(raw).__name__}")
    path = PurePosixPath(raw)
    require(
        raw
        and not path.is_absolute()
        and path.as_posix() == raw
        and "\\" not in raw
        and all(part not in {"", ".", ".."} for part in path.parts),
        f"unsafe member path: {raw!r}",
    )
    return raw


def safe_component(raw: str, label: str) -> str:
    require(raw not in {"", ".", ".."} and "/" not in raw and "\0" not in raw,
            f"unsafe {label}: {raw!r}")
    return raw


def parent(raw: str) -> str:
    return "/".join(PurePosixPath(raw).parts[:-1])


def stable(metadata: os.stat_result) -> StableIdentity:
    return StableIdentity(
        metadata.st_dev,
        metadata.st_ino,
        stat.S_IFMT(metadata.st_mode),
        metadata.st_uid,
        metadata.st_gid,
    )


def file_fingerprint(metadata: os.stat_result) -> FileFingerprint:
    return FileFingerprint(
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def same_path_object(parent_fd: int, name: str, fd: int, label: str) -> os.stat_result:
    descriptor = os.fstat(fd)
    current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    require(stable(descriptor) == stable(current), f"{label} pathname identity changed")
    return descriptor


def git_object(kind: bytes, payload: bytes) -> str:
    return hashlib.sha1(kind + b" " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def git_blob_hasher(size: int) -> Any:
    require(type(size) is int and 0 <= size <= MAX_SOURCE_FILE_BYTES, "invalid bounded Git blob size")
    digest = hashlib.sha1()
    digest.update(b"blob " + str(size).encode("ascii") + b"\0")
    return digest


def load_regular_bytes(path: Path, label: str, limit: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1,
                f"{label} must be one regular non-hard-linked file")
        require(opened.st_size <= limit, f"{label} exceeds bounded size")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(fd, BUFFER_SIZE)
            if not chunk:
                break
            total += len(chunk)
            require(total <= limit, f"{label} exceeds bounded size")
            chunks.append(chunk)
        final = os.fstat(fd)
        require(
            (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size, opened.st_nlink)
            == (final.st_dev, final.st_ino, final.st_mode, final.st_size, final.st_nlink),
            f"{label} changed while reading",
        )
        return b"".join(chunks)
    finally:
        os.close(fd)


def load_manifest(path: Path) -> dict[str, Any]:
    raw = load_regular_bytes(path, "source manifest", 32 * 1024 * 1024)
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=strict)
    require(
        isinstance(value, dict)
        and set(value) == {"schema_id", "candidate_tree", "directories", "files"},
        "source manifest shape changed",
    )
    require(value["schema_id"] == "x64lens-candidate-source-tree-v1", "wrong source manifest schema")
    require(
        isinstance(value["candidate_tree"], str)
        and len(value["candidate_tree"]) == 40
        and all(char in "0123456789abcdef" for char in value["candidate_tree"]),
        "invalid candidate tree",
    )
    require(isinstance(value["directories"], list) and isinstance(value["files"], list),
            "invalid manifest arrays")
    return value


def derive_tree(files: dict[str, dict[str, Any]], directories: set[str]) -> str:
    all_dirs = {"", *directories}
    children: dict[str, list[tuple[str, bool, str, str]]] = {directory: [] for directory in all_dirs}
    for directory in directories:
        require(parent(directory) in all_dirs, f"undeclared directory parent: {directory}")
    for path, item in files.items():
        require(parent(path) in all_dirs, f"undeclared file parent: {path}")
        children[parent(path)].append((PurePosixPath(path).name, False, item["git_mode"], item["git_oid"]))
    for directory in sorted(directories, key=lambda item: (-item.count("/"), os.fsencode(item))):
        entries = children[directory]
        require(entries, f"manifest contains an empty non-Git directory: {directory}")
        payload = b"".join(
            mode.encode("ascii") + b" " + name_bytes + b"\0" + bytes.fromhex(oid)
            for name_bytes, is_directory, mode, oid in sorted(
                (
                    (os.fsencode(name) + (b"/" if is_dir else b""), is_dir, mode, oid)
                    for name, is_dir, mode, oid in entries
                ),
                key=lambda item: item[0],
            )
            for name_bytes in [name_bytes[:-1] if is_directory else name_bytes]
        )
        oid = git_object(b"tree", payload)
        children[parent(directory)].append((PurePosixPath(directory).name, True, "40000", oid))
    root_entries = children[""]
    require(root_entries, "source manifest has no root entries")
    payload = b"".join(
        mode.encode("ascii") + b" " + name_bytes + b"\0" + bytes.fromhex(oid)
        for name_bytes, is_directory, mode, oid in sorted(
            (
                (os.fsencode(name) + (b"/" if is_dir else b""), is_dir, mode, oid)
                for name, is_dir, mode, oid in root_entries
            ),
            key=lambda item: item[0],
        )
        for name_bytes in [name_bytes[:-1] if is_directory else name_bytes]
    )
    return git_object(b"tree", payload)


def parse_manifest(value: dict[str, Any]) -> tuple[dict[str, int], dict[str, dict[str, Any]], str]:
    directories: dict[str, int] = {}
    ordered_directories: list[str] = []
    for item in value["directories"]:
        require(isinstance(item, dict) and set(item) == {"path", "mode"}, "invalid directory record")
        path = safe(item["path"])
        require(item["mode"] == "0755", f"noncanonical directory mode: {path}")
        require(path not in directories, f"duplicate directory: {path}")
        directories[path] = 0o755
        ordered_directories.append(path)
    files: dict[str, dict[str, Any]] = {}
    for item in value["files"]:
        require(
            isinstance(item, dict)
            and set(item) == {"path", "type", "git_oid", "git_mode", "mode", "sha256", "size_bytes"},
            "invalid file record",
        )
        path = safe(item["path"])
        require(path not in files and path not in directories, f"duplicate source path: {path}")
        require(item["type"] == "blob", f"invalid source object type: {path}")
        require(
            isinstance(item["git_oid"], str)
            and len(item["git_oid"]) == 40
            and all(char in "0123456789abcdef" for char in item["git_oid"]),
            f"invalid Git object id: {path}",
        )
        require(item["git_mode"] in {"100644", "100755"} and item["mode"] in {"0644", "0755"},
                f"invalid source mode: {path}")
        require((item["git_mode"] == "100755") == (item["mode"] == "0755"),
                f"Git/recovery mode mismatch: {path}")
        require(
            isinstance(item["sha256"], str)
            and len(item["sha256"]) == 64
            and all(char in "0123456789abcdef" for char in item["sha256"]),
            f"invalid digest: {path}",
        )
        require(type(item["size_bytes"]) is int and 0 <= item["size_bytes"] <= MAX_SOURCE_FILE_BYTES,
                f"invalid or over-capacity size: {path}")
        files[path] = item
    require(len(directories) <= MAX_SOURCE_DIRECTORIES, "source directory capacity exceeded")
    require(len(files) <= MAX_SOURCE_FILES, "source file capacity exceeded")
    total_bytes = sum(item["size_bytes"] for item in files.values())
    require(total_bytes <= MAX_SOURCE_TOTAL_BYTES,
            f"source aggregate byte capacity exceeded: {total_bytes} > {MAX_SOURCE_TOTAL_BYTES}")
    require(ordered_directories == sorted(ordered_directories) and list(files) == sorted(files),
            "manifest paths must be sorted")
    all_dirs = {"", *directories}
    for directory in directories:
        require(parent(directory) in all_dirs, f"undeclared directory parent: {directory}")
    for path in files:
        require(parent(path) in all_dirs, f"undeclared file parent: {path}")
    derived = derive_tree(files, set(directories))
    require(derived == value["candidate_tree"],
            f"manifest candidate tree disagrees: derived={derived} declared={value['candidate_tree']}")
    return directories, files, derived


def open_parent_chain(destination: Path) -> ParentHandle:
    absolute = Path(os.path.abspath(os.fspath(destination)))
    require(absolute != Path("/") and absolute.name, "destination must have a basename")
    parent_path = absolute.parent
    current_fd = os.open("/", os.O_RDONLY | O_DIRECTORY | O_CLOEXEC)
    bindings: list[AncestorBinding] = []
    display = ""
    try:
        for component in parent_path.parts[1:]:
            safe_component(component, "destination-parent component")
            display = f"{display}/{component}"
            before = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
            require(stat.S_ISDIR(before.st_mode), f"destination ancestor is not a real directory: {display}")
            child = os.open(component, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=current_fd)
            opened = stable(os.fstat(child))
            require(opened == stable(before), f"destination ancestor changed while opening: {display}")
            after = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
            require(stable(after) == opened, f"destination ancestor changed after opening: {display}")
            bindings.append(AncestorBinding(current_fd, component, child, opened, display))
            current_fd = child
        require(bindings, "destination parent path has no retained binding")
        return ParentHandle(parent_path, current_fd, bindings)
    except BaseException:
        close_parent(ParentHandle(parent_path, current_fd, bindings))
        raise


def close_parent(handle: ParentHandle) -> None:
    seen: set[int] = set()
    for binding in reversed(handle.bindings):
        for fd in (binding.child_fd, binding.parent_fd):
            if fd in seen:
                continue
            seen.add(fd)
            try:
                os.close(fd)
            except OSError:
                pass
    if handle.fd not in seen:
        try:
            os.close(handle.fd)
        except OSError:
            pass


def reauthenticate_parent(handle: ParentHandle) -> None:
    for binding in handle.bindings:
        descriptor = stable(os.fstat(binding.child_fd))
        current = stable(os.stat(binding.name, dir_fd=binding.parent_fd, follow_symlinks=False))
        require(descriptor == binding.opened, f"destination ancestor descriptor changed: {binding.display}")
        require(current == binding.opened, f"destination ancestor binding changed: {binding.display}")


def rename_noreplace(old_parent: int, old: str, new_parent: int, new: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    function = getattr(libc, "renameat2", None)
    require(function is not None, "renameat2 is unavailable on this Linux runtime")
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    result = function(old_parent, os.fsencode(old), new_parent, os.fsencode(new), RENAME_NOREPLACE)
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), new)


def hash_fd(fd: int, expected_size: int | None = None) -> tuple[str, int, str]:
    observed_size = os.fstat(fd).st_size
    if expected_size is None:
        expected_size = observed_size
    else:
        require(type(expected_size) is int and expected_size == observed_size,
                "declared file size differs from descriptor size")
    require(type(expected_size) is int and 0 <= expected_size <= MAX_SOURCE_FILE_BYTES,
            "invalid bounded file size")
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    git_digest = git_blob_hasher(expected_size)
    total = 0
    while True:
        chunk = os.read(fd, BUFFER_SIZE)
        if not chunk:
            break
        total += len(chunk)
        require(total <= expected_size, "file exceeds declared bounded size while hashing")
        digest.update(chunk)
        git_digest.update(chunk)
    require(total == expected_size, "file size changed while hashing")
    return digest.hexdigest(), total, git_digest.hexdigest()


def open_archive(path: Path) -> tuple[int, BinaryIO, FileFingerprint]:
    """Open and authenticate the source archive without leaking on rejection."""
    fd = -1
    duplicate = -1
    try:
        fd = os.open(path, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW)
        metadata = os.fstat(fd)
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
                "source archive must be one regular non-hard-linked file")
        require(metadata.st_size <= MAX_SOURCE_ARCHIVE_BYTES, "source archive exceeds bounded size")
        opened = file_fingerprint(metadata)
        visible = os.stat(path, follow_symlinks=False)
        require(file_fingerprint(visible) == opened, "source archive pathname differs from opened descriptor")
        duplicate = os.dup(fd)
        stream = os.fdopen(duplicate, "rb", closefd=True)
        duplicate = -1
        return fd, stream, opened
    except BaseException:
        if duplicate >= 0:
            try:
                os.close(duplicate)
            except OSError:
                pass
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        raise


def reauthenticate_archive(path: Path, fd: int, opened: FileFingerprint) -> None:
    """Bind the final recovery result to the same single-link archive object."""
    descriptor = os.fstat(fd)
    visible = os.stat(path, follow_symlinks=False)
    require(file_fingerprint(descriptor) == opened, "source archive descriptor changed during recovery")
    require(file_fingerprint(visible) == opened, "source archive pathname changed during recovery")
    require(stat.S_ISREG(descriptor.st_mode) and descriptor.st_nlink == 1,
            "source archive topology changed during recovery")


def expected_children(directories: dict[str, int], files: dict[str, dict[str, Any]]) -> dict[str, tuple[str, ...]]:
    rows: dict[str, list[str]] = {"": []}
    for directory in directories:
        rows.setdefault(directory, [])
        rows[parent(directory)].append(PurePosixPath(directory).name)
    for path in files:
        rows[parent(path)].append(PurePosixPath(path).name)
    return {key: tuple(sorted(value, key=os.fsencode)) for key, value in rows.items()}


def final_verify(
    parent_handle: ParentHandle,
    root_parent_fd: int,
    root_name: str,
    root_fd: int,
    root_identity: StableIdentity,
    directories: dict[str, int],
    files: dict[str, dict[str, Any]],
    directory_records: dict[str, DirectoryRecord],
    file_records: dict[str, FileRecord],
) -> None:
    reauthenticate_parent(parent_handle)
    root_metadata = same_path_object(root_parent_fd, root_name, root_fd, "recovery root")
    require(stable(root_metadata) == root_identity, "recovery root descriptor identity changed")
    require(stat.S_IMODE(root_metadata.st_mode) == 0o755, "recovery root mode changed")
    children = expected_children(directories, files)
    require(tuple(sorted(os.listdir(root_fd), key=os.fsencode)) == children[""],
            "recovery root membership changed")
    for path, record in directory_records.items():
        metadata = same_path_object(record.parent_fd, record.name, record.fd, f"directory {path}")
        require(stable(metadata) == record.opened, f"directory descriptor identity changed: {path}")
        require(stat.S_IMODE(metadata.st_mode) == 0o755, f"directory mode changed: {path}")
        require(tuple(sorted(os.listdir(record.fd), key=os.fsencode)) == children[path],
                f"directory membership changed: {path}")
    for path, record in file_records.items():
        before = same_path_object(record.parent_fd, record.name, record.fd, f"file {path}")
        require(stable(before) == record.opened, f"file descriptor identity changed: {path}")
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                f"file topology changed: {path}")
        require(stat.S_IMODE(before.st_mode) == record.mode, f"file mode changed: {path}")
        before_fingerprint = file_fingerprint(before)
        observed, size, observed_oid = hash_fd(record.fd)
        after = same_path_object(record.parent_fd, record.name, record.fd, f"file {path}")
        require(
            file_fingerprint(after) == before_fingerprint,
            f"file topology or metadata changed while hashing: {path}",
        )
        require(observed == record.sha256 and size == record.size, f"file bytes changed: {path}")
        require(observed_oid == record.git_oid, f"Git blob identity changed: {path}")


def _snapshot_cleanup_records(root_fd: int) -> tuple[
    dict[str, tuple[int, str, int, StableIdentity]],
    dict[str, tuple[int, str, int, StableIdentity]],
]:
    """Snapshot one descriptor-bound tree for direct cleanup callers.

    Normal recovery passes the original creation records instead.  This fallback
    exists for regression and administrative callers that own a complete tree
    before entering cleanup.  The snapshot is taken before the final injectable
    namespace boundary so later substitutions are preserved.
    """
    directories: dict[str, tuple[int, str, int, StableIdentity]] = {}
    files: dict[str, tuple[int, str, int, StableIdentity]] = {}

    def visit(current_fd: int, prefix: str) -> None:
        for name in sorted(os.listdir(current_fd), key=os.fsencode):
            safe_component(name, "cleanup member")
            metadata = os.stat(name, dir_fd=current_fd, follow_symlinks=False)
            path = name if not prefix else f"{prefix}/{name}"
            if stat.S_ISDIR(metadata.st_mode):
                fd = os.open(name, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=current_fd)
                opened = stable(os.fstat(fd))
                require(opened == stable(metadata), f"cleanup directory changed while opening: {path}")
                directories[path] = (current_fd, name, fd, opened)
                visit(fd, path)
            elif stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1:
                fd = os.open(name, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW, dir_fd=current_fd)
                opened = stable(os.fstat(fd))
                require(opened == stable(metadata), f"cleanup file changed while opening: {path}")
                files[path] = (current_fd, name, fd, opened)
            else:
                raise RecoveryError(f"cleanup encountered linked or special member; preserved: {path}")

    try:
        visit(root_fd, "")
        return directories, files
    except BaseException:
        for _path, (_parent_fd, _name, fd, _opened) in files.items():
            try:
                os.close(fd)
            except OSError:
                pass
        for _path, (_parent_fd, _name, fd, _opened) in sorted(
            directories.items(), key=lambda item: -item[0].count("/")
        ):
            try:
                os.close(fd)
            except OSError:
                pass
        raise


def _delete_recorded_tree(
    root_fd: int,
    root_parent_fd: int,
    root_name: str,
    directory_rows: dict[str, tuple[int, str, int, StableIdentity]],
    file_rows: dict[str, tuple[int, str, int, StableIdentity]],
) -> None:
    """Delete only originally authenticated descendants.

    Unknown, replaced, linked, or special descendants cause a fail-closed
    residue.  No recursive pathname walker is allowed to reinterpret a foreign
    descendant as owned cleanup material.
    """
    expected_children: dict[str, set[str]] = {"": set()}
    for path in directory_rows:
        expected_children.setdefault(path, set())
        expected_children.setdefault(parent(path), set()).add(PurePosixPath(path).name)
    for path in file_rows:
        expected_children.setdefault(parent(path), set()).add(PurePosixPath(path).name)

    # Confirm exact membership before any destructive operation.  A foreign
    # replacement is therefore preserved rather than consumed by cleanup.
    directory_fd_by_path = {"": root_fd}
    directory_fd_by_path.update({path: row[2] for path, row in directory_rows.items()})
    for path, fd in directory_fd_by_path.items():
        observed = set(os.listdir(fd))
        require(
            observed == expected_children.get(path, set()),
            f"cleanup membership changed; residue preserved at {path or '.'}",
        )

    for path, (parent_fd, name, fd, opened) in sorted(
        file_rows.items(), key=lambda item: (-item[0].count("/"), os.fsencode(item[0]))
    ):
        current = same_path_object(parent_fd, name, fd, f"cleanup file {path}")
        require(stable(current) == opened and stat.S_ISREG(current.st_mode) and current.st_nlink == 1,
                f"cleanup file identity changed; residue preserved: {path}")
        os.unlink(name, dir_fd=parent_fd)
        require(os.fstat(fd).st_nlink == 0, f"cleanup file unlink did not remove owned inode: {path}")

    for path, (parent_fd, name, fd, opened) in sorted(
        directory_rows.items(), key=lambda item: (-item[0].count("/"), os.fsencode(item[0]))
    ):
        current = same_path_object(parent_fd, name, fd, f"cleanup directory {path}")
        require(stable(current) == opened and stat.S_ISDIR(current.st_mode),
                f"cleanup directory identity changed; residue preserved: {path}")
        require(not os.listdir(fd), f"cleanup directory contains foreign residue: {path}")
        os.rmdir(name, dir_fd=parent_fd)
        require(os.fstat(fd).st_nlink == 0, f"cleanup directory unlink did not remove owned inode: {path}")

    require(not os.listdir(root_fd), "cleanup root contains foreign residue")
    os.rmdir(root_name, dir_fd=root_parent_fd)
    require(os.fstat(root_fd).st_nlink == 0, "cleanup root unlink did not remove owned inode")


def cleanup_owned_root(
    parent_fd: int,
    name: str,
    root_fd: int,
    expected: StableIdentity,
    directory_records: dict[str, DirectoryRecord] | None = None,
    file_records: dict[str, FileRecord] | None = None,
) -> None:
    if _TEST_BEFORE_CLEANUP_HOOK is not None:
        _TEST_BEFORE_CLEANUP_HOOK(parent_fd, name, root_fd)
    first = f".x64lens-recovery-quarantine.{os.getpid()}.{os.urandom(16).hex()}"
    second = f".x64lens-recovery-delete.{os.getpid()}.{os.urandom(16).hex()}"
    snapshot_directories: dict[str, tuple[int, str, int, StableIdentity]] = {}
    snapshot_files: dict[str, tuple[int, str, int, StableIdentity]] = {}
    close_snapshot = directory_records is None or file_records is None
    try:
        rename_noreplace(parent_fd, name, parent_fd, first)
    except FileNotFoundError:
        raise RecoveryError("owned recovery root binding disappeared; residue preserved")
    first_fd = os.open(first, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
    try:
        require(stable(os.fstat(first_fd)) == expected == stable(os.fstat(root_fd)),
                f"recovery cleanup encountered a foreign replacement; preserved as {first}")
        if close_snapshot:
            snapshot_directories, snapshot_files = _snapshot_cleanup_records(first_fd)
        else:
            assert directory_records is not None and file_records is not None
            snapshot_directories = {
                path: (record.parent_fd, record.name, record.fd, record.opened)
                for path, record in directory_records.items()
            }
            snapshot_files = {
                path: (record.parent_fd, record.name, record.fd, record.opened)
                for path, record in file_records.items()
            }
        rename_noreplace(parent_fd, first, parent_fd, second)
        second_fd = os.open(second, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
        try:
            require(stable(os.fstat(second_fd)) == expected,
                    f"recovery cleanup identity changed; preserved as {second}")
            if _TEST_BEFORE_FINAL_RMTREE_HOOK is not None:
                _TEST_BEFORE_FINAL_RMTREE_HOOK(parent_fd, second, root_fd)
            final_fd = os.open(second, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
            try:
                require(stable(os.fstat(final_fd)) == expected,
                        f"recovery cleanup identity changed; preserved as {second}")
                _delete_recorded_tree(
                    final_fd,
                    parent_fd,
                    second,
                    snapshot_directories,
                    snapshot_files,
                )
            finally:
                os.close(final_fd)
        finally:
            os.close(second_fd)
    finally:
        if close_snapshot:
            for _path, (_parent_fd, _name, fd, _opened) in snapshot_files.items():
                try:
                    os.close(fd)
                except OSError:
                    pass
            for _path, (_parent_fd, _name, fd, _opened) in sorted(
                snapshot_directories.items(), key=lambda item: -item[0].count("/")
            ):
                try:
                    os.close(fd)
                except OSError:
                    pass
        os.close(first_fd)
    os.fsync(parent_fd)


def cleanup_unopened_stage(parent: ParentHandle, name: str, opened: StableIdentity) -> None:
    """Remove only the empty staging directory created before its first open.

    This path exists for failures in the first directory open itself.  The
    namespace entry is deleted only when it is still the exact directory that
    was created and remains empty; a replacement is preserved and reported.
    """
    reauthenticate_parent(parent)
    metadata = os.stat(name, dir_fd=parent.fd, follow_symlinks=False)
    require(stable(metadata) == opened, "unopened staging root was replaced; residue preserved")
    require(stat.S_ISDIR(metadata.st_mode), "unopened staging root changed type; residue preserved")
    probe = os.open(name, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent.fd)
    try:
        require(stable(os.fstat(probe)) == opened, "unopened staging root changed while reopening")
        require(not os.listdir(probe), "unopened staging root is not empty; residue preserved")
        os.rmdir(name, dir_fd=parent.fd)
        require(os.fstat(probe).st_nlink == 0, "unopened staging root removal did not detach owned inode")
    finally:
        os.close(probe)
    os.fsync(parent.fd)


def recover(archive_path: Path, manifest_path: Path, destination: Path) -> tuple[str, int, int, Path]:
    value = load_manifest(manifest_path)
    directories, files, derived_tree = parse_manifest(value)
    destination = Path(os.path.abspath(os.fspath(destination)))
    soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft != resource.RLIM_INFINITY:
        required = recovery_fd_requirement(destination, len(directories), len(files))
        require(
            soft >= required,
            f"file-descriptor limit cannot retain and clean the source tree: {soft} < {required}",
        )

    safe_component(destination.name, "destination basename")
    parent_handle = open_parent_chain(destination)
    stage_name = f".x64lens-recovery-stage.{os.getpid()}.{os.urandom(16).hex()}"
    root_fd = -1
    stage_created = False
    unopened_stage_identity: StableIdentity | None = None
    published = False
    current_name = stage_name
    directory_records: dict[str, DirectoryRecord] = {}
    file_records: dict[str, FileRecord] = {}
    archive_fd = -1
    archive_file: BinaryIO | None = None
    archive_identity: FileFingerprint | None = None
    try:
        reauthenticate_parent(parent_handle)
        try:
            os.stat(destination.name, dir_fd=parent_handle.fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise RecoveryError("destination already exists")
        with defer_catchable_signals():
            mkdir_exact(stage_name, 0o700, dir_fd=parent_handle.fd)
            if _TEST_AFTER_STAGE_MKDIR_EFFECT_HOOK is not None:
                _TEST_AFTER_STAGE_MKDIR_EFFECT_HOOK(parent_handle.fd, stage_name)
            stage_created = True
            unopened_stage_identity = stable(
                os.stat(stage_name, dir_fd=parent_handle.fd, follow_symlinks=False)
            )
        require(unopened_stage_identity.file_type == stat.S_IFDIR, "staging root changed type before open")
        root_fd = os.open(stage_name, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_handle.fd)
        root_identity = stable(os.fstat(root_fd))
        require(root_identity.file_type == stat.S_IFDIR, "staging root changed type")
        directory_fds: dict[str, int] = {"": root_fd}
        seen_directories: set[str] = set()
        seen_files: set[str] = set()

        archive_fd, archive_file, archive_identity = open_archive(archive_path)
        with tarfile.open(fileobj=archive_file, mode="r:*") as archive:
            for member in archive:
                raw_name = member.name[:-1] if member.name.endswith("/") else member.name
                name = safe(raw_name)
                require(
                    not member.issym()
                    and not member.islnk()
                    and not member.isdev()
                    and not member.isfifo(),
                    "linked or special source member rejected",
                )
                parent_name = parent(name)
                require(parent_name in directory_fds, f"member parent not declared first: {name}")
                parent_fd = directory_fds[parent_name]
                basename = PurePosixPath(name).name
                if member.isdir():
                    require(name in directories and name not in seen_directories,
                            f"undeclared/duplicate directory: {name}")
                    require(member.mode & 0o7777 == 0o755, f"TAR directory mode disagrees: {name}")
                    mkdir_exact(basename, 0o700, dir_fd=parent_fd)
                    fd = os.open(basename, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
                    os.fchmod(fd, 0o755)
                    opened = stable(os.fstat(fd))
                    require(opened.file_type == stat.S_IFDIR, f"recovered directory changed type: {name}")
                    directory_fds[name] = fd
                    directory_records[name] = DirectoryRecord(name, basename, parent_fd, fd, opened)
                    seen_directories.add(name)
                elif member.isfile():
                    require(name in files and name not in seen_files, f"undeclared/duplicate file: {name}")
                    expected = files[name]
                    expected_mode = int(expected["mode"], 8)
                    require(member.mode & 0o7777 == expected_mode, f"TAR file mode disagrees: {name}")
                    require(member.size == expected["size_bytes"], f"TAR file size disagrees: {name}")
                    source = archive.extractfile(member)
                    require(source is not None, f"cannot read member: {name}")
                    fd = os.open(
                        basename,
                        os.O_RDWR | os.O_CREAT | os.O_EXCL | O_CLOEXEC | O_NOFOLLOW,
                        0o600,
                        dir_fd=parent_fd,
                    )
                    opened_stat = same_path_object(parent_fd, basename, fd, f"file {name}")
                    opened = stable(opened_stat)
                    require(opened_stat.st_nlink == 1, f"recovered file has hard-link aliases: {name}")
                    file_records[name] = FileRecord(
                        name,
                        basename,
                        parent_fd,
                        fd,
                        opened,
                        expected["sha256"],
                        expected["size_bytes"],
                        expected_mode,
                        expected["git_oid"],
                    )
                    digest = hashlib.sha256()
                    git_digest = git_blob_hasher(expected["size_bytes"])
                    total = 0
                    try:
                        while True:
                            chunk = source.read(BUFFER_SIZE)
                            if not chunk:
                                break
                            total += len(chunk)
                            require(total <= expected["size_bytes"], f"TAR member exceeds declared size: {name}")
                            digest.update(chunk)
                            git_digest.update(chunk)
                            view = memoryview(chunk)
                            while view:
                                written = os.write(fd, view)
                                require(written > 0, f"zero-length source write: {name}")
                                view = view[written:]
                        require(total == expected["size_bytes"], f"TAR member size changed: {name}")
                        os.fsync(fd)
                        os.fchmod(fd, expected_mode)
                        os.fsync(fd)
                        current_stat = same_path_object(parent_fd, basename, fd, f"file {name}")
                        require(stable(current_stat) == opened and current_stat.st_nlink == 1,
                                f"recovered file identity changed: {name}")
                        observed_sha = digest.hexdigest()
                        observed_oid = git_digest.hexdigest()
                        require(observed_sha == expected["sha256"], f"file SHA-256 disagrees: {name}")
                        require(observed_oid == expected["git_oid"], f"Git blob identity disagrees: {name}")
                        seen_files.add(name)
                    except BaseException:
                        # Keep the retained descriptor open for identity-qualified
                        # rollback.  Closing it here leaves a stale FileRecord and
                        # prevents cleanup from authenticating and deleting the
                        # owned corrupt member.  The outer finally block closes all
                        # retained descriptors after rollback completes.
                        raise
                else:
                    raise RecoveryError(f"unsupported TAR member type: {name}")
        require(archive_identity is not None, "source archive identity was not retained")
        reauthenticate_archive(archive_path, archive_fd, archive_identity)
        require(seen_directories == set(directories), "source directory membership changed")
        require(seen_files == set(files), "source file membership changed")
        os.fchmod(root_fd, 0o755)
        for record in sorted(directory_records.values(), key=lambda item: -item.path.count("/")):
            os.fsync(record.fd)
        os.fsync(root_fd)
        os.fsync(parent_handle.fd)
        final_verify(
            parent_handle,
            parent_handle.fd,
            stage_name,
            root_fd,
            root_identity,
            directories,
            files,
            directory_records,
            file_records,
        )
        if _TEST_AFTER_INITIAL_VERIFY_HOOK is not None:
            _TEST_AFTER_INITIAL_VERIFY_HOOK(parent_handle.fd, stage_name, root_fd)
        final_verify(
            parent_handle,
            parent_handle.fd,
            stage_name,
            root_fd,
            root_identity,
            directories,
            files,
            directory_records,
            file_records,
        )
        reauthenticate_archive(archive_path, archive_fd, archive_identity)
        if _TEST_BEFORE_PUBLISH_HOOK is not None:
            _TEST_BEFORE_PUBLISH_HOOK(parent_handle.fd, stage_name, destination.name)
        with defer_catchable_signals():
            rename_noreplace(parent_handle.fd, stage_name, parent_handle.fd, destination.name)
            if _TEST_AFTER_PUBLISH_RENAME_EFFECT_HOOK is not None:
                _TEST_AFTER_PUBLISH_RENAME_EFFECT_HOOK(parent_handle.fd, destination.name)
            published = True
            current_name = destination.name
        if _TEST_AFTER_PUBLISH_HOOK is not None:
            _TEST_AFTER_PUBLISH_HOOK(parent_handle.fd, destination.name, root_fd)
        final_verify(
            parent_handle,
            parent_handle.fd,
            destination.name,
            root_fd,
            root_identity,
            directories,
            files,
            directory_records,
            file_records,
        )
        os.fsync(parent_handle.fd)
        reauthenticate_archive(archive_path, archive_fd, archive_identity)
        return derived_tree, len(directories), len(files), destination
    except BaseException as exc:
        cleanup_error: BaseException | None = None
        if root_fd >= 0:
            try:
                cleanup_owned_root(
                    parent_handle.fd,
                    current_name,
                    root_fd,
                    stable(os.fstat(root_fd)),
                    directory_records,
                    file_records,
                )
            except BaseException as candidate:
                cleanup_error = candidate
        elif stage_created and unopened_stage_identity is not None:
            try:
                cleanup_unopened_stage(parent_handle, stage_name, unopened_stage_identity)
            except BaseException as candidate:
                cleanup_error = candidate
        if cleanup_error is not None:
            raise RecoveryError(f"source recovery failed: {exc}; cleanup failed closed: {cleanup_error}") from exc
        raise
    finally:
        for record in reversed(list(file_records.values())):
            try:
                os.close(record.fd)
            except OSError:
                pass
        for record in reversed(list(directory_records.values())):
            try:
                os.close(record.fd)
            except OSError:
                pass
        if root_fd >= 0:
            try:
                os.close(root_fd)
            except OSError:
                pass
        if archive_file is not None:
            try:
                archive_file.close()
            except OSError:
                pass
        if archive_fd >= 0:
            try:
                os.close(archive_fd)
            except OSError:
                pass
        close_parent(parent_handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    with catchable_termination_guard("candidate source recovery"):
        tree, directory_count, file_count, destination = recover(
            Path(os.path.abspath(args.archive)),
            Path(os.path.abspath(args.manifest)),
            args.destination,
        )
    print(
        "recover-candidate-source: ok "
        f"tree={tree} derived_tree=1 directories={directory_count} files={file_count} "
        f"destination={destination} descriptor_bound=1 no_replace=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RecoveryError, OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError, tarfile.TarError) as exc:
        print(f"recover-candidate-source: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
