#!/usr/bin/env python3
"""Create or verify an exact descriptor-bound delivery-custody manifest.

Schema v3 authenticates the caller-visible root name, semantic label, root mode,
manifest path/mode/link count, every directory path/mode, and every regular
payload path/hash/size/mode/link count.  Root ancestors are opened one component
at a time with ``O_NOFOLLOW`` and retained through verification.  Every payload
and directory descriptor is also retained until a final closure pass, which
rehashes files, relists directories, and reauthenticates every pathname binding.

The verifier rejects symlinks, special files, hard links, unsafe or duplicate
paths, undeclared members, mode drift, late subtree mutation, and root/ancestor
substitution.  It is intentionally Linux/POSIX-specific and bounded.  It does
not claim a kernel-atomic filesystem snapshot against a malicious concurrent
same-UID process; any detected disagreement fails closed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import resource
import stat
import sys
from typing import Any, Callable, NamedTuple

SCHEMA_ID = "x64lens-delivery-custody-v3"
BUFFER_SIZE = 1024 * 1024
MAX_DIRECTORIES = 256
# The complete tree may contain at most 511 payload files plus the custody
# manifest.  Create reserves the manifest slot before publication.
MAX_PAYLOAD_FILES = 511
MAX_FILES = MAX_PAYLOAD_FILES + 1
MIN_FD_HEADROOM = 64
FD_TRANSACTION_OVERHEAD = 12
O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)

# Test-only injection points.  Production callers leave these unset.
_TEST_AFTER_FILE_HASH_HOOK: Callable[[int, str, str], None] | None = None
_TEST_AFTER_TREE_SCAN_HOOK: Callable[[Path], None] | None = None


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
    uid: int
    gid: int


@dataclass
class AncestorBinding:
    parent_fd: int
    name: str
    child_fd: int
    opened: Fingerprint
    display: str


@dataclass
class RootHandle:
    requested: Path
    basename: str
    fd: int
    opened: Fingerprint
    bindings: list[AncestorBinding]


@dataclass
class DirectoryObservation:
    path: str
    name: str
    parent_fd: int
    fd: int
    opened: Fingerprint
    children: tuple[str, ...] = field(default_factory=tuple)

    def manifest_entry(self) -> dict[str, Any]:
        return {"path": self.path, "mode": mode_text(self.opened.mode)}


@dataclass
class FileObservation:
    path: str
    name: str
    parent_fd: int
    fd: int
    opened: Fingerprint
    sha256: str
    size_bytes: int

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "mode": mode_text(self.opened.mode),
            "nlink": self.opened.nlink,
        }


@dataclass
class TreeObservation:
    root: RootHandle
    directories: list[DirectoryObservation]
    files: list[FileObservation]
    manifest: FileObservation | None

    def close(self, *, keep_root: bool = False) -> None:
        for item in reversed(self.files):
            try:
                os.close(item.fd)
            except OSError:
                pass
        self.files.clear()
        if self.manifest is not None:
            try:
                os.close(self.manifest.fd)
            except OSError:
                pass
            self.manifest = None
        for item in reversed(self.directories):
            if keep_root and item.path == "":
                continue
            try:
                os.close(item.fd)
            except OSError:
                pass
        self.directories[:] = [item for item in self.directories if keep_root and item.path == ""]
        if not keep_root:
            close_root(self.root)


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


def safe_relative(raw: Any) -> str:
    require(isinstance(raw, str) and raw != "", "manifest path must be a nonempty string")
    path = PurePosixPath(raw)
    require(not path.is_absolute(), f"absolute manifest path: {raw}")
    require(all(part not in {"", ".", ".."} for part in path.parts), f"unsafe manifest path: {raw}")
    normalized = path.as_posix()
    require(normalized == raw and "\\" not in raw, f"noncanonical manifest path: {raw}")
    return normalized


def safe_component(raw: str, label: str) -> str:
    require(raw not in {"", ".", ".."} and "/" not in raw and "\0" not in raw,
            f"unsafe {label}: {raw!r}")
    return raw


def parse_mode(raw: Any, label: str) -> int:
    require(isinstance(raw, str) and len(raw) == 4 and all(char in "01234567" for char in raw),
            f"invalid mode: {label}")
    return int(raw, 8)


def mode_text(mode: int) -> str:
    return f"{stat.S_IMODE(mode):04o}"


def same_identity(left: Fingerprint, right: Fingerprint) -> bool:
    """Compare stable object identity while allowing expected directory timestamps."""
    return (
        left.device == right.device
        and left.inode == right.inode
        and left.file_type == right.file_type
        and left.mode == right.mode
        and left.nlink == right.nlink
        and left.uid == right.uid
        and left.gid == right.gid
    )


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
        metadata.st_uid,
        metadata.st_gid,
    )


def manifest_relative(root: Path, manifest: Path) -> str:
    root_absolute = Path(os.path.abspath(os.fspath(root)))
    manifest_absolute = Path(os.path.abspath(os.fspath(manifest)))
    try:
        relative = manifest_absolute.relative_to(root_absolute).as_posix()
    except ValueError as exc:
        raise CustodyError("custody manifest must be inside the custody root") from exc
    return safe_relative(relative)


def current_fd_count() -> int:
    try:
        return len(os.listdir("/proc/self/fd"))
    except OSError:
        soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        ceiling = 4096 if soft == resource.RLIM_INFINITY else min(int(soft), 4096)
        count = 0
        for fd in range(ceiling):
            try:
                os.fstat(fd)
            except OSError:
                continue
            count += 1
        return count


def check_fd_capacity(root: Path) -> None:
    soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft == resource.RLIM_INFINITY:
        return
    live = current_fd_count()
    root_depth = len(Path(os.path.abspath(os.fspath(root))).parts)
    required = (
        live
        + root_depth
        + MAX_DIRECTORIES
        + MAX_FILES
        + FD_TRANSACTION_OVERHEAD
        + MIN_FD_HEADROOM
    )
    require(
        soft >= required,
        "file-descriptor limit cannot guarantee the advertised custody capacity: "
        f"soft={soft} live={live} root_depth={root_depth} required={required}",
    )


def open_root(root: Path) -> RootHandle:
    """Open every absolute path component without following a symlink."""
    requested = Path(os.path.abspath(os.fspath(root)))
    require(requested != Path("/"), "custody root may not be the filesystem root")
    parts = requested.parts
    require(parts and parts[0] == "/", "custody root must resolve to an absolute POSIX path")
    current_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC)
    bindings: list[AncestorBinding] = []
    display = ""
    try:
        for component in parts[1:]:
            safe_component(component, "custody-root component")
            display = f"{display}/{component}"
            before = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
            require(stat.S_ISDIR(before.st_mode), f"custody path component is not a real directory: {display}")
            child_fd = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW,
                dir_fd=current_fd,
            )
            opened = fingerprint(os.fstat(child_fd))
            require(opened == fingerprint(before), f"custody path component changed while opening: {display}")
            after = os.stat(component, dir_fd=current_fd, follow_symlinks=False)
            require(fingerprint(after) == opened, f"custody path component changed after opening: {display}")
            bindings.append(AncestorBinding(current_fd, component, child_fd, opened, display))
            current_fd = child_fd
        require(bindings, "custody root path has no basename")
        root_binding = bindings[-1]
        return RootHandle(requested, root_binding.name, root_binding.child_fd, root_binding.opened, bindings)
    except BaseException:
        # Every child is also the next binding's parent; close each unique fd once.
        seen: set[int] = set()
        for binding in reversed(bindings):
            for fd in (binding.child_fd, binding.parent_fd):
                if fd not in seen:
                    seen.add(fd)
                    try:
                        os.close(fd)
                    except OSError:
                        pass
        if current_fd not in seen:
            try:
                os.close(current_fd)
            except OSError:
                pass
        raise


def close_root(root: RootHandle) -> None:
    seen: set[int] = set()
    for binding in reversed(root.bindings):
        for fd in (binding.child_fd, binding.parent_fd):
            if fd not in seen:
                seen.add(fd)
                try:
                    os.close(fd)
                except OSError:
                    pass


def reauthenticate_root(root: RootHandle) -> None:
    for index, binding in enumerate(root.bindings):
        observed_fd = fingerprint(os.fstat(binding.child_fd))
        current = fingerprint(os.stat(binding.name, dir_fd=binding.parent_fd, follow_symlinks=False))
        if index == len(root.bindings) - 1:
            # Publication inside the root legitimately changes directory size and
            # timestamps.  Device/inode/type/mode/link/owner identity must remain.
            require(same_identity(observed_fd, binding.opened),
                    f"custody root descriptor identity changed: {binding.display}")
            require(same_identity(current, binding.opened),
                    f"custody root binding changed: {binding.display}")
        else:
            require(observed_fd == binding.opened,
                    f"custody path descriptor changed: {binding.display}")
            require(current == binding.opened,
                    f"custody path binding changed: {binding.display}")
    require(same_identity(fingerprint(os.fstat(root.fd)), root.opened),
            "custody root descriptor identity changed")


def refresh_root_metadata(root: RootHandle) -> None:
    """Refresh expected root directory metadata after an authenticated write."""
    observed = fingerprint(os.fstat(root.fd))
    require(same_identity(observed, root.opened), "custody root identity changed during publication")
    current = fingerprint(os.stat(root.basename, dir_fd=root.bindings[-1].parent_fd, follow_symlinks=False))
    require(same_identity(current, root.opened), "custody root binding changed during publication")
    require(observed == current, "custody root descriptor/path metadata disagree after publication")
    root.opened = observed
    root.bindings[-1].opened = observed


def open_directory(parent_fd: int, name: str, relative: str, root_device: int) -> DirectoryObservation:
    before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    require(stat.S_ISDIR(before.st_mode), f"non-directory traversal member: {relative}")
    require(before.st_dev == root_device, f"cross-device delivery directory rejected: {relative}")
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
    try:
        opened = fingerprint(os.fstat(fd))
        require(opened == fingerprint(before), f"directory changed while opening: {relative}")
        after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(fingerprint(after) == opened, f"directory pathname changed after opening: {relative}")
        return DirectoryObservation(relative, name, parent_fd, fd, opened)
    except BaseException:
        os.close(fd)
        raise


def hash_fd(fd: int) -> tuple[str, int]:
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    total = 0
    while True:
        chunk = os.read(fd, BUFFER_SIZE)
        if not chunk:
            break
        digest.update(chunk)
        total += len(chunk)
    return digest.hexdigest(), total


def open_regular(parent_fd: int, name: str, relative: str, root_device: int) -> FileObservation:
    before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    require(stat.S_ISREG(before.st_mode), f"non-regular delivery member: {relative}")
    require(before.st_dev == root_device, f"cross-device delivery file rejected: {relative}")
    require(before.st_nlink == 1, f"hard-linked delivery file rejected: {relative}")
    fd = os.open(name, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
    try:
        opened = fingerprint(os.fstat(fd))
        require(opened == fingerprint(before), f"file changed while opening: {relative}")
        require(opened.nlink == 1, f"hard-linked delivery file rejected after open: {relative}")
        digest, total = hash_fd(fd)
        hook = _TEST_AFTER_FILE_HASH_HOOK
        if hook is not None:
            hook(parent_fd, name, relative)
        require(fingerprint(os.fstat(fd)) == opened, f"file changed while hashing: {relative}")
        post_path = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(fingerprint(post_path) == opened, f"file pathname changed after hashing: {relative}")
        require(total == opened.size, f"file size changed while hashing: {relative}")
        return FileObservation(relative, name, parent_fd, fd, opened, digest, total)
    except BaseException:
        os.close(fd)
        raise


def scan_tree(
    root: RootHandle,
    manifest_path: str,
    *,
    reserve_manifest_slot: bool = False,
) -> TreeObservation:
    directories: list[DirectoryObservation] = []
    files: list[FileObservation] = []
    manifest: FileObservation | None = None
    seen_objects: set[tuple[int, int]] = {(root.opened.device, root.opened.inode)}

    def walk(fd: int, prefix: str) -> tuple[str, ...]:
        nonlocal manifest
        names = tuple(sorted(os.listdir(fd), key=os.fsencode))
        for name in names:
            safe_component(name, "delivery member name")
            relative = f"{prefix}/{name}" if prefix else name
            safe_relative(relative)
            metadata = os.stat(name, dir_fd=fd, follow_symlinks=False)
            key = (metadata.st_dev, metadata.st_ino)
            require(key not in seen_objects, f"duplicate delivery inode topology rejected: {relative}")
            seen_objects.add(key)
            file_type = stat.S_IFMT(metadata.st_mode)
            if file_type == stat.S_IFDIR:
                require(len(directories) < MAX_DIRECTORIES, "delivery directory capacity exceeded")
                child = open_directory(fd, name, relative, root.opened.device)
                directories.append(child)
                child.children = walk(child.fd, relative)
            elif file_type == stat.S_IFREG:
                current_total = len(files) + int(manifest is not None)
                if relative == manifest_path:
                    require(current_total < MAX_FILES, "delivery file capacity exceeded")
                else:
                    payload_limit = MAX_PAYLOAD_FILES if reserve_manifest_slot else MAX_FILES
                    require(len(files) < payload_limit and current_total < MAX_FILES,
                            "delivery file capacity exceeded")
                observed = open_regular(fd, name, relative, root.opened.device)
                if relative == manifest_path:
                    require(manifest is None, "duplicate custody manifest pathname")
                    manifest = observed
                else:
                    files.append(observed)
            else:
                raise CustodyError(f"link or special delivery member rejected: {relative}")
        return names

    try:
        # Root membership is authenticated by a synthetic observation retained
        # in the final closure pass below.
        root_names = walk(root.fd, "")
        root_directory = DirectoryObservation(
            "", root.basename, root.bindings[-1].parent_fd,
            root.fd, root.opened, root_names,
        )
        directories.sort(key=lambda item: item.path)
        files.sort(key=lambda item: item.path)
        observation = TreeObservation(root, [root_directory, *directories], files, manifest)
        hook = _TEST_AFTER_TREE_SCAN_HOOK
        if hook is not None:
            hook(root.requested)
        return observation
    except BaseException:
        # scan_tree owns every descriptor it opened, but not the caller-owned
        # retained root/ancestor chain.  Rejected late members must not leak the
        # descriptors accumulated before the failure.
        for item in reversed(files):
            try:
                os.close(item.fd)
            except OSError:
                pass
        if manifest is not None:
            try:
                os.close(manifest.fd)
            except OSError:
                pass
        for item in reversed(directories):
            try:
                os.close(item.fd)
            except OSError:
                pass
        raise


def read_observed_file(observed: FileObservation) -> bytes:
    os.lseek(observed.fd, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(observed.fd, BUFFER_SIZE)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    require(total == observed.size_bytes, f"file size changed between authenticated reads: {observed.path}")
    raw = b"".join(chunks)
    require(hashlib.sha256(raw).hexdigest() == observed.sha256,
            f"file bytes changed between authenticated reads: {observed.path}")
    return raw


def validate_directory(raw: Any, index: int) -> dict[str, Any]:
    require(isinstance(raw, dict) and set(raw) == {"path", "mode"},
            f"manifest directory fields changed: {index}")
    path = safe_relative(raw["path"])
    parse_mode(raw["mode"], path)
    return {"path": path, "mode": raw["mode"]}


def validate_file(raw: Any, index: int) -> dict[str, Any]:
    require(isinstance(raw, dict), f"manifest file {index} is not an object")
    require(set(raw) == {"path", "sha256", "size_bytes", "mode", "nlink"},
            f"manifest file fields changed: {index}")
    path = safe_relative(raw["path"])
    sha = raw["sha256"]
    require(isinstance(sha, str) and len(sha) == 64 and all(char in "0123456789abcdef" for char in sha),
            f"invalid SHA-256: {path}")
    require(type(raw["size_bytes"]) is int and raw["size_bytes"] >= 0, f"invalid size: {path}")
    parse_mode(raw["mode"], path)
    require(type(raw["nlink"]) is int and raw["nlink"] == 1, f"invalid link count: {path}")
    return {
        "path": path,
        "sha256": sha,
        "size_bytes": raw["size_bytes"],
        "mode": raw["mode"],
        "nlink": 1,
    }


def final_closure(observation: TreeObservation) -> None:
    # Rehash every retained file descriptor and reauthenticate its pathname.
    all_files = ([observation.manifest] if observation.manifest is not None else []) + observation.files
    for item in all_files:
        assert item is not None
        digest, total = hash_fd(item.fd)
        require(digest == item.sha256 and total == item.size_bytes,
                f"file changed after initial scan: {item.path}")
        require(fingerprint(os.fstat(item.fd)) == item.opened,
                f"file descriptor changed after initial scan: {item.path}")
        current = os.stat(item.name, dir_fd=item.parent_fd, follow_symlinks=False)
        require(fingerprint(current) == item.opened,
                f"file pathname changed after initial scan: {item.path}")
        require(current.st_nlink == 1, f"file became hard linked after initial scan: {item.path}")

    # Relist and reauthenticate every retained directory.  The synthetic root
    # observation uses an empty path and the retained root descriptor.
    for item in reversed(observation.directories):
        label = item.path or "."
        current_names = tuple(sorted(os.listdir(item.fd), key=os.fsencode))
        require(current_names == item.children, f"directory membership changed after scan: {label}")
        require(fingerprint(os.fstat(item.fd)) == item.opened,
                f"directory descriptor changed after scan: {label}")
        current = os.stat(item.name, dir_fd=item.parent_fd, follow_symlinks=False)
        require(fingerprint(current) == item.opened,
                f"directory pathname changed after scan: {label}")
    reauthenticate_root(observation.root)


def open_parent_fd(root_fd: int, relative: str) -> tuple[int, str]:
    parts = PurePosixPath(safe_relative(relative)).parts
    fd = os.dup(root_fd)
    try:
        for index, component in enumerate(parts[:-1]):
            prefix = "/".join(parts[: index + 1])
            before = os.stat(component, dir_fd=fd, follow_symlinks=False)
            require(stat.S_ISDIR(before.st_mode), f"manifest parent is not a real directory: {prefix}")
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=fd)
            require(fingerprint(os.fstat(child)) == fingerprint(before),
                    f"manifest parent changed while opening: {prefix}")
            os.close(fd)
            fd = child
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def write_manifest_atomic(root: RootHandle, relative: str, raw: bytes) -> Fingerprint:
    reauthenticate_root(root)
    parent_fd, name = open_parent_fd(root.fd, relative)
    temporary = f".custody.{os.getpid()}.{os.urandom(16).hex()}"
    fd = -1
    linked = False
    published_fingerprint: Fingerprint | None = None
    try:
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise CustodyError("custody manifest already exists")
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | O_CLOEXEC | O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        written = 0
        while written < len(raw):
            count = os.write(fd, raw[written:])
            require(count > 0, "short zero-length manifest write")
            written += count
        os.fsync(fd)
        os.fchmod(fd, 0o444)
        os.fsync(fd)
        # Hard-link publication is no-replace.  The temporary name is removed
        # immediately, returning the published manifest to nlink=1.
        os.link(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)
        linked = True
        os.unlink(temporary, dir_fd=parent_fd)
        linked = False
        published = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(stat.S_ISREG(published.st_mode) and published.st_nlink == 1,
                "published custody manifest topology is invalid")
        published_fingerprint = fingerprint(published)
        os.fsync(parent_fd)
        reauthenticate_root(root)
        refresh_root_metadata(root)
    finally:
        if fd >= 0:
            os.close(fd)
        if not linked:
            try:
                os.unlink(temporary, dir_fd=parent_fd)
            except FileNotFoundError:
                pass
        os.close(parent_fd)
    require(published_fingerprint is not None, "custody manifest publication did not complete")
    return published_fingerprint


def remove_published_manifest(root: RootHandle, relative: str, expected: Fingerprint) -> None:
    parent_fd, name = open_parent_fd(root.fd, relative)
    try:
        current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(fingerprint(current) == expected,
                "refusing to remove a changed custody manifest during rollback")
        os.unlink(name, dir_fd=parent_fd)
        os.fsync(parent_fd)
        reauthenticate_root(root)
    finally:
        os.close(parent_fd)


def verify_open_root(root_handle: RootHandle, relative: str) -> dict[str, Any]:
    observation: TreeObservation | None = None
    try:
        observation = scan_tree(root_handle, relative)
        require(observation.manifest is not None, "custody manifest is missing")
        raw = read_observed_file(observation.manifest)
        value = strict_json_loads(raw.decode("utf-8"))
        require(isinstance(value, dict), "delivery manifest must be an object")
        require(set(value) == {"schema_id", "root_label", "root", "manifest", "directories", "files"},
                "manifest top-level fields changed")
        require(value["schema_id"] == SCHEMA_ID, "wrong delivery-custody schema")
        require(isinstance(value["root_label"], str) and value["root_label"], "invalid root label")
        require(isinstance(value["root"], dict)
                and set(value["root"]) == {"name", "label", "mode"}, "invalid root record")
        require(value["root"]["name"] == root_handle.basename, "custody root basename mismatch")
        require(value["root"]["label"] == value["root_label"], "custody root label mismatch")
        expected_root_mode = parse_mode(value["root"]["mode"], ".")
        require(root_handle.opened.mode == expected_root_mode, "custody root mode mismatch")
        require(isinstance(value["manifest"], dict)
                and set(value["manifest"]) == {"path", "mode", "nlink"}, "invalid manifest record")
        require(safe_relative(value["manifest"]["path"]) == relative, "manifest path disagreement")
        expected_manifest_mode = parse_mode(value["manifest"]["mode"], relative)
        require(observation.manifest.opened.mode == expected_manifest_mode, "custody manifest mode mismatch")
        require(type(value["manifest"]["nlink"]) is int and value["manifest"]["nlink"] == 1
                and observation.manifest.opened.nlink == 1, "custody manifest link count mismatch")
        require(isinstance(value["directories"], list), "manifest directories must be an array")
        require(isinstance(value["files"], list), "manifest files must be an array")
        expected_directories = [validate_directory(item, index) for index, item in enumerate(value["directories"])]
        expected_files = [validate_file(item, index) for index, item in enumerate(value["files"])]
        dir_paths = [entry["path"] for entry in expected_directories]
        file_paths = [entry["path"] for entry in expected_files]
        require(dir_paths == sorted(dir_paths) and len(dir_paths) == len(set(dir_paths)),
                "manifest directory paths are not unique and sorted")
        require(file_paths == sorted(file_paths) and len(file_paths) == len(set(file_paths)),
                "manifest file paths are not unique and sorted")
        require(relative not in file_paths and relative not in dir_paths, "manifest self-entry is invalid")
        require(not (set(dir_paths) & set(file_paths)), "manifest path is both file and directory")
        observed_directories = [item.manifest_entry() for item in observation.directories if item.path]
        observed_files = [item.manifest_entry() for item in observation.files]
        require(observed_directories == expected_directories, "delivery directory set or modes disagree")
        require(observed_files == expected_files,
                "delivery file set, bytes, sizes, modes, or link counts disagree")
        final_closure(observation)
        reauthenticate_root(root_handle)
        return value
    finally:
        if observation is not None:
            observation.close(keep_root=True)


def verify(root: Path, manifest: Path) -> dict[str, Any]:
    check_fd_capacity(root)
    relative = manifest_relative(root, manifest)
    root_handle = open_root(root)
    try:
        return verify_open_root(root_handle, relative)
    finally:
        close_root(root_handle)


def create(root: Path, manifest: Path, label: str) -> dict[str, Any]:
    """Create a v3 manifest through one retained root and self-verify it."""
    check_fd_capacity(root)
    relative = manifest_relative(root, manifest)
    root_handle = open_root(root)
    observation: TreeObservation | None = None
    published: Fingerprint | None = None
    try:
        require(isinstance(label, str) and label != "", "invalid root label")
        observation = scan_tree(root_handle, relative, reserve_manifest_slot=True)
        require(observation.manifest is None, "custody manifest already exists")
        final_closure(observation)
        value = {
            "schema_id": SCHEMA_ID,
            "root_label": label,
            "root": {"name": root_handle.basename, "label": label, "mode": mode_text(root_handle.opened.mode)},
            "manifest": {"path": relative, "mode": "0444", "nlink": 1},
            "directories": [item.manifest_entry() for item in observation.directories if item.path],
            "files": [item.manifest_entry() for item in observation.files],
        }
        raw = (json.dumps(value, indent=2, sort_keys=False) + "\n").encode("utf-8")
        observation.close(keep_root=True)
        observation = None
        published = write_manifest_atomic(root_handle, relative, raw)
        verified = verify_open_root(root_handle, relative)
        require(verified == value, "created custody manifest failed semantic self-verification")
        reauthenticate_root(root_handle)
        return value
    except BaseException as exc:
        if published is not None:
            try:
                remove_published_manifest(root_handle, relative, published)
            except BaseException as rollback_exc:
                raise CustodyError(
                    f"custody creation failed: {exc}; manifest rollback failed: {rollback_exc}"
                ) from exc
        raise
    finally:
        if observation is not None:
            observation.close(keep_root=True)
        close_root(root_handle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", action="store_true")
    action.add_argument("--verify", action="store_true")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--label")
    args = parser.parse_args()
    if args.create:
        label = args.label if args.label is not None else Path(os.path.abspath(args.root)).name
        value = create(args.root, args.manifest, label)
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
