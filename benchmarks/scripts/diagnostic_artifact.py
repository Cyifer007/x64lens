#!/usr/bin/env python3
"""Shared authenticated-artifact helpers for Sprint 11 diagnostic tooling.

The module is development infrastructure, not part of the x64lens runtime.  It
opens campaign members without following symlinks, authenticates runner rows to
retained tool/target/output objects, and publishes derived JSON through a
same-directory no-replace transaction with pre- and post-commit input
reauthentication.
"""
from __future__ import annotations

import csv
import ctypes
from dataclasses import dataclass
import errno
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Callable, Iterable
import uuid

MAX_JSON_BYTES = 32 * 1024 * 1024
MAX_ROWS_BYTES = 256 * 1024 * 1024
MAX_MEMBER_BYTES = 512 * 1024 * 1024
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
RENAME_NOREPLACE = 1
AT_FDCWD = -100


class ArtifactError(RuntimeError):
    """Raised when retained diagnostic evidence is unsafe or inconsistent."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ArtifactError(message)


def safe_id(value: Any, label: str) -> str:
    require(isinstance(value, str) and SAFE_ID.fullmatch(value) is not None, f"unsafe {label}: {value!r}")
    return value


def require_sha256(value: Any, label: str) -> str:
    require(isinstance(value, str) and HEX_SHA256.fullmatch(value) is not None, f"invalid {label}")
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, separators=(",", ": ")) + "\n").encode("utf-8")


def _open_regular_at(parent_fd: int, name: str, maximum_bytes: int, label: str) -> int:
    require(PurePosixPath(name).name == name and name not in {"", ".", ".."}, f"unsafe {label} name")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise ArtifactError(f"cannot open {label}: {exc}") from exc
    try:
        metadata = os.fstat(fd)
        require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file")
        require(0 <= metadata.st_size <= maximum_bytes, f"{label} exceeds the {maximum_bytes}-byte bound")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _open_directory_at(parent_fd: int, name: str, label: str) -> int:
    require(PurePosixPath(name).name == name and name not in {"", ".", ".."}, f"unsafe {label} name")
    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        fd = os.open(name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise ArtifactError(f"cannot open {label}: {exc}") from exc
    try:
        metadata = os.fstat(fd)
        require(stat.S_ISDIR(metadata.st_mode), f"{label} is not a directory")
        return fd
    except BaseException:
        os.close(fd)
        raise


def open_real_directory(path: Path, label: str) -> tuple[Path, int, dict[str, Any]]:
    absolute = Path(os.path.abspath(path))
    metadata = os.lstat(absolute)
    require(stat.S_ISDIR(metadata.st_mode), f"{label} is not a real directory")
    fd = os.open(
        absolute,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        observed = os.fstat(fd)
        require(
            stat.S_ISDIR(observed.st_mode)
            and (observed.st_dev, observed.st_ino) == (metadata.st_dev, metadata.st_ino),
            f"{label} changed while being opened",
        )
        resolved = Path(f"/proc/self/fd/{fd}").resolve(strict=True)
        return resolved, fd, {
            "path_requested": str(path),
            "path_resolved": str(resolved),
            "device": observed.st_dev,
            "inode": observed.st_ino,
            "mode": stat.S_IMODE(observed.st_mode),
        }
    except BaseException:
        os.close(fd)
        raise


def _read_fd(fd: int, size: int, label: str) -> bytes:
    chunks: list[bytes] = []
    offset = 0
    while offset < size:
        chunk = os.pread(fd, min(1024 * 1024, size - offset), offset)
        require(chunk, f"short read while reading {label}")
        chunks.append(chunk)
        offset += len(chunk)
    data = b"".join(chunks)
    require(len(data) == size, f"{label} size changed while being read")
    return data


def _identity_from_fd(fd: int, data: bytes, requested: str, resolved: str) -> dict[str, Any]:
    metadata = os.fstat(fd)
    return {
        "path_requested": requested,
        "path_resolved": resolved,
        "size_bytes": metadata.st_size,
        "sha256": sha256_bytes(data),
        "mode": stat.S_IMODE(metadata.st_mode),
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mtime_ns": metadata.st_mtime_ns,
    }


def parse_relative_path(value: Any, label: str) -> tuple[str, ...]:
    require(isinstance(value, str) and value, f"{label} must be a nonempty relative path")
    pure = PurePosixPath(value)
    require(not pure.is_absolute(), f"{label} must be relative")
    require("\\" not in value and "\x00" not in value, f"{label} contains an unsafe character")
    require(pure.parts and all(part not in {"", ".", ".."} for part in pure.parts), f"{label} is unsafe")
    return pure.parts


def open_member_fd(root_fd: int, relative: str, *, directory: bool, maximum_bytes: int, label: str) -> int:
    parts = parse_relative_path(relative, label)
    current = os.dup(root_fd)
    try:
        for index, component in enumerate(parts):
            final = index == len(parts) - 1
            if final:
                result = (
                    _open_directory_at(current, component, label)
                    if directory
                    else _open_regular_at(current, component, maximum_bytes, label)
                )
            else:
                next_fd = _open_directory_at(current, component, f"{label} parent")
                os.close(current)
                current = next_fd
        return result
    finally:
        os.close(current)


def load_member(root_fd: int, root_path: Path, relative: str, maximum_bytes: int, label: str) -> tuple[bytes, dict[str, Any]]:
    fd = open_member_fd(root_fd, relative, directory=False, maximum_bytes=maximum_bytes, label=label)
    try:
        before = os.fstat(fd)
        data = _read_fd(fd, before.st_size, label)
        after = os.fstat(fd)
        require(
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            f"{label} changed while being read",
        )
        resolved = str(root_path.joinpath(*parse_relative_path(relative, label)))
        return data, _identity_from_fd(fd, data, relative, resolved)
    finally:
        os.close(fd)


def directory_member_identity(root_fd: int, root_path: Path, relative: str, label: str) -> dict[str, Any]:
    fd = open_member_fd(root_fd, relative, directory=True, maximum_bytes=0, label=label)
    try:
        metadata = os.fstat(fd)
        return {
            "path_requested": relative,
            "path_resolved": str(root_path.joinpath(*parse_relative_path(relative, label))),
            "device": metadata.st_dev,
            "inode": metadata.st_ino,
            "mode": stat.S_IMODE(metadata.st_mode),
        }
    finally:
        os.close(fd)


def require_member_identity(
    root_fd: int,
    root_path: Path,
    relative: str,
    expected: dict[str, Any],
    maximum_bytes: int,
    label: str,
) -> None:
    data, observed = load_member(root_fd, root_path, relative, maximum_bytes, label)
    del data
    for field in ("device", "inode", "mode", "size_bytes", "sha256"):
        require(observed[field] == expected[field], f"{label} {field} changed")


def require_directory_member_identity(
    root_fd: int,
    root_path: Path,
    relative: str,
    expected: dict[str, Any],
    label: str,
) -> None:
    observed = directory_member_identity(root_fd, root_path, relative, label)
    for field in ("device", "inode", "mode"):
        require(observed[field] == expected[field], f"{label} {field} changed")


@dataclass
class CampaignContext:
    root: Path
    root_fd: int
    root_identity: dict[str, Any]
    manifest: dict[str, Any]
    manifest_identity: dict[str, Any]
    rows_identity: dict[str, Any]
    rows: list[dict[str, str]]
    tools: dict[str, dict[str, Any]]
    targets: dict[str, dict[str, Any]]

    def close(self) -> None:
        if self.root_fd >= 0:
            os.close(self.root_fd)
            self.root_fd = -1

    def row(self, run_id: str) -> dict[str, str]:
        safe_id(run_id, "run id")
        matches = [row for row in self.rows if row.get("run_id") == run_id]
        require(len(matches) == 1, f"campaign must contain exactly one row named {run_id}")
        return matches[0]

    def load_row_member(self, row: dict[str, str], stream: str) -> tuple[bytes, dict[str, Any]]:
        require(stream in {"stdout", "stderr"}, "invalid row stream")
        relative = row[f"{stream}_path"]
        maximum = int(row[f"{stream}_limit_bytes"])
        data, identity = load_member(self.root_fd, self.root, relative, maximum, f"row {row['run_id']} {stream}")
        require(identity["size_bytes"] == int(row[f"{stream}_bytes"]), f"row {row['run_id']} {stream} size mismatch")
        require(identity["sha256"] == require_sha256(row[f"{stream}_sha256"], f"row {row['run_id']} {stream} hash"), f"row {row['run_id']} {stream} hash mismatch")
        return data, identity

    def reauthenticate(self, selected: Iterable[tuple[str, dict[str, Any], int, str]]) -> None:
        require_member_identity(self.root_fd, self.root, "manifest.json", self.manifest_identity, MAX_JSON_BYTES, "campaign manifest")
        rows_path = self.manifest["artifacts"]["rows"]
        require_member_identity(self.root_fd, self.root, rows_path, self.rows_identity, MAX_ROWS_BYTES, "campaign rows")
        for relative, identity, maximum, label in selected:
            require_member_identity(self.root_fd, self.root, relative, identity, maximum, label)


def _parse_rows(data: bytes) -> list[dict[str, str]]:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ArtifactError(f"campaign rows are not valid UTF-8: {exc}") from exc
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    require(reader.fieldnames is not None and "run_id" in reader.fieldnames, "campaign rows header is invalid")
    rows = [dict(row) for row in reader]
    require(rows, "campaign rows are empty")
    run_ids = [row.get("run_id", "") for row in rows]
    require(all(SAFE_ID.fullmatch(value or "") is not None for value in run_ids), "campaign contains an unsafe run id")
    require(len(run_ids) == len(set(run_ids)), "campaign contains duplicate run ids")
    return rows


def load_campaign(path: Path) -> CampaignContext:
    root, root_fd, root_identity = open_real_directory(path, "campaign result")
    try:
        manifest_data, manifest_identity = load_member(root_fd, root, "manifest.json", MAX_JSON_BYTES, "campaign manifest")
        try:
            manifest = json.loads(manifest_data.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"cannot parse campaign manifest: {exc}") from exc
        require(isinstance(manifest, dict), "campaign manifest must be an object")
        require(manifest.get("schema_version") == 2, "unsupported campaign manifest schema")
        require(manifest.get("evidence_class") == "diagnostic", "campaign is not diagnostic evidence")
        require(manifest.get("frozen") is False, "campaign unexpectedly claims frozen state")
        require(manifest.get("publication_eligible") is False, "campaign unexpectedly claims publication eligibility")
        safe_id(manifest.get("campaign_id"), "campaign id")
        artifacts = manifest.get("artifacts")
        require(isinstance(artifacts, dict), "campaign artifact record is missing")
        rows_path = artifacts.get("rows")
        parse_relative_path(rows_path, "campaign rows path")
        rows_data, rows_identity = load_member(root_fd, root, rows_path, MAX_ROWS_BYTES, "campaign rows")
        require(rows_identity["sha256"] == require_sha256(artifacts.get("rows_sha256"), "campaign rows SHA-256"), "campaign rows hash mismatch")
        rows = _parse_rows(rows_data)
        outcomes = manifest.get("outcomes")
        require(isinstance(outcomes, dict) and outcomes.get("row_count") == len(rows), "campaign row count mismatch")

        tools_raw = manifest.get("tools")
        targets_raw = manifest.get("targets")
        require(isinstance(tools_raw, list) and tools_raw, "campaign tool records are missing")
        require(isinstance(targets_raw, list) and targets_raw, "campaign target records are missing")
        tools: dict[str, dict[str, Any]] = {}
        targets: dict[str, dict[str, Any]] = {}
        for record in tools_raw:
            require(isinstance(record, dict), "campaign tool record is invalid")
            tool_id = safe_id(record.get("id"), "tool id")
            require(tool_id not in tools, f"duplicate campaign tool id: {tool_id}")
            tools[tool_id] = record
            snapshot = record.get("snapshot_path")
            data, identity = load_member(root_fd, root, snapshot, MAX_MEMBER_BYTES, f"tool {tool_id} snapshot")
            require(identity["sha256"] == require_sha256(record.get("sha256"), f"tool {tool_id} SHA-256"), f"tool {tool_id} snapshot hash mismatch")
            require(identity["size_bytes"] == record.get("size_bytes"), f"tool {tool_id} snapshot size mismatch")
            del data
            for stream in ("stdout", "stderr"):
                key = f"version_{stream}_path"
                result = record.get("version_result")
                require(isinstance(result, dict), f"tool {tool_id} version result is missing")
                member_data, member_identity = load_member(root_fd, root, record.get(key), MAX_MEMBER_BYTES, f"tool {tool_id} version {stream}")
                require(member_identity["size_bytes"] == result.get(f"{stream}_bytes"), f"tool {tool_id} version {stream} size mismatch")
                require(member_identity["sha256"] == require_sha256(result.get(f"{stream}_sha256"), f"tool {tool_id} version {stream} hash"), f"tool {tool_id} version {stream} hash mismatch")
                del member_data
        for record in targets_raw:
            require(isinstance(record, dict), "campaign target record is invalid")
            target_id = safe_id(record.get("id"), "target id")
            require(target_id not in targets, f"duplicate campaign target id: {target_id}")
            targets[target_id] = record
            data, identity = load_member(root_fd, root, record.get("snapshot_path"), MAX_MEMBER_BYTES, f"target {target_id} snapshot")
            require(identity["sha256"] == require_sha256(record.get("sha256"), f"target {target_id} SHA-256"), f"target {target_id} snapshot hash mismatch")
            require(identity["size_bytes"] == record.get("size_bytes"), f"target {target_id} snapshot size mismatch")
            del data

        for row in rows:
            tool_id = safe_id(row.get("tool_id"), "row tool id")
            target_id = safe_id(row.get("target_id"), "row target id")
            require(tool_id in tools and target_id in targets, f"row {row['run_id']} references an unknown tool or target")
            require(row.get("campaign_id") == manifest["campaign_id"], f"row {row['run_id']} campaign id mismatch")
            require(row.get("tool_sha256") == tools[tool_id]["sha256"], f"row {row['run_id']} tool hash mismatch")
            require(row.get("target_sha256") == targets[target_id]["sha256"], f"row {row['run_id']} target hash mismatch")
            directory_member_identity(root_fd, root, row.get("command_cwd"), f"row {row['run_id']} command cwd")
            for stream in ("stdout", "stderr"):
                data, identity = load_member(root_fd, root, row.get(f"{stream}_path"), int(row.get(f"{stream}_limit_bytes", "0")), f"row {row['run_id']} {stream}")
                require(identity["size_bytes"] == int(row.get(f"{stream}_bytes", "-1")), f"row {row['run_id']} {stream} size mismatch")
                require(identity["sha256"] == require_sha256(row.get(f"{stream}_sha256"), f"row {row['run_id']} {stream} hash"), f"row {row['run_id']} {stream} hash mismatch")
                del data

        return CampaignContext(root, root_fd, root_identity, manifest, manifest_identity, rows_identity, rows, tools, targets)
    except BaseException:
        os.close(root_fd)
        raise



def load_regular_path(path: Path, maximum_bytes: int, label: str) -> tuple[bytes, dict[str, Any]]:
    absolute = Path(os.path.abspath(path))
    parent, parent_fd, _ = open_real_directory(absolute.parent, f"{label} parent")
    try:
        return load_member(parent_fd, parent, absolute.name, maximum_bytes, label)
    finally:
        os.close(parent_fd)


def require_regular_path_identity(path: Path, expected: dict[str, Any], maximum_bytes: int, label: str) -> None:
    data, observed = load_regular_path(path, maximum_bytes, label)
    del data
    for field in ("device", "inode", "mode", "size_bytes", "sha256"):
        require(observed[field] == expected[field], f"{label} {field} changed")


def directory_path_identity(path: Path, label: str) -> dict[str, Any]:
    resolved, fd, identity = open_real_directory(path, label)
    identity["path_resolved"] = str(resolved)
    os.close(fd)
    return identity


def require_directory_path_identity(path: Path, expected: dict[str, Any], label: str) -> None:
    observed = directory_path_identity(path, label)
    for field in ("device", "inode", "mode"):
        require(observed[field] == expected[field], f"{label} {field} changed")

def load_authority(path: Path, *, schema_version: int, authority_id: str) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    absolute = Path(os.path.abspath(path))
    parent, parent_fd, _ = open_real_directory(absolute.parent, "task-authority parent")
    try:
        data, identity = load_member(parent_fd, parent, absolute.name, MAX_JSON_BYTES, "task authority")
    finally:
        os.close(parent_fd)
    try:
        value = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot parse task authority: {exc}") from exc
    require(isinstance(value, dict), "task authority must be an object")
    require(value.get("schema_version") == schema_version, "unsupported task-authority schema")
    require(value.get("authority_id") == authority_id, "unexpected task-authority identity")
    return value, identity, data


def _renameat2(parent_fd: int, source_name: str, destination_name: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    require(renameat2 is not None, "Linux renameat2 is required for no-replace publication")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(parent_fd, os.fsencode(source_name), parent_fd, os.fsencode(destination_name), RENAME_NOREPLACE)
    if result != 0:
        code = ctypes.get_errno()
        if code == errno.EEXIST:
            raise ArtifactError(f"output already exists: {destination_name}")
        raise ArtifactError(f"cannot publish output: {os.strerror(code)}")


def _write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        require(written > 0, "short write while publishing derived artifact")
        offset += written


def atomic_publish_bytes(
    output: Path,
    data: bytes,
    *,
    reauthenticate: Callable[[], None],
    mode: int = 0o444,
) -> dict[str, Any]:
    """Publish one derived artifact with two input-authentication barriers.

    The callback runs after the temporary file is durable and again after the
    no-replace rename.  A post-commit authentication failure removes only the
    exact inode created by this transaction; a substituted foreign path is never
    deleted.
    """
    absolute = Path(os.path.abspath(output))
    require(absolute.name not in {"", ".", ".."}, "unsafe output name")
    parent, parent_fd, _ = open_real_directory(absolute.parent, "output parent")
    temporary_name = f".{absolute.name}.tmp-{uuid.uuid4().hex}"
    fd = -1
    temp_identity: tuple[int, int] | None = None
    committed = False
    try:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        fd = os.open(temporary_name, flags, 0o600, dir_fd=parent_fd)
        _write_all(fd, data)
        os.fchmod(fd, mode)
        os.fsync(fd)
        metadata = os.fstat(fd)
        temp_identity = (metadata.st_dev, metadata.st_ino)
        reauthenticate()
        _renameat2(parent_fd, temporary_name, absolute.name)
        committed = True
        observed = os.stat(absolute.name, dir_fd=parent_fd, follow_symlinks=False)
        require(stat.S_ISREG(observed.st_mode), "published output is not a regular file")
        require((observed.st_dev, observed.st_ino) == temp_identity, "published output was substituted")
        os.fsync(parent_fd)
        try:
            reauthenticate()
            observed = os.stat(absolute.name, dir_fd=parent_fd, follow_symlinks=False)
            require((observed.st_dev, observed.st_ino) == temp_identity, "published output changed after commit")
            require(observed.st_size == len(data), "published output size changed")
            require(stat.S_IMODE(observed.st_mode) == mode, "published output mode changed")
            check_fd = _open_regular_at(parent_fd, absolute.name, len(data), "published output")
            try:
                check_data = _read_fd(check_fd, len(data), "published output")
            finally:
                os.close(check_fd)
            require(check_data == data, "published output bytes changed")
        except BaseException:
            try:
                current = os.stat(absolute.name, dir_fd=parent_fd, follow_symlinks=False)
            except OSError:
                pass
            else:
                if (current.st_dev, current.st_ino) == temp_identity:
                    os.unlink(absolute.name, dir_fd=parent_fd)
                    os.fsync(parent_fd)
            raise
        return {
            "path": str(parent / absolute.name),
            "size_bytes": len(data),
            "sha256": sha256_bytes(data),
            "mode": mode,
            "device": temp_identity[0],
            "inode": temp_identity[1],
        }
    finally:
        if fd >= 0:
            os.close(fd)
        if not committed:
            try:
                metadata = os.stat(temporary_name, dir_fd=parent_fd, follow_symlinks=False)
            except OSError:
                pass
            else:
                if temp_identity is not None and (metadata.st_dev, metadata.st_ino) == temp_identity:
                    os.unlink(temporary_name, dir_fd=parent_fd)
                    os.fsync(parent_fd)
        os.close(parent_fd)
