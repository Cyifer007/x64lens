#!/usr/bin/env python3
"""Run provenance-bound Sprint 11 diagnostic benchmark conditions.

The runner is development and research infrastructure, not a runtime dependency
of x64lens. It uses only Python's standard library, retains hashed input
snapshots, executes write-sealed copies, measures each process with monotonic
nanosecond timing and Linux wait4 resource data, retains failed rows, and
publishes one complete campaign tree transactionally.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
from dataclasses import dataclass
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import selectors
import shutil
import signal
import statistics
import stat
import subprocess
import sys
import time
from typing import Any, Iterable
import uuid

RUNNER_SCHEMA_VERSION = 2
EVIDENCE_CLASS = "diagnostic"
PUBLICATION_ELIGIBLE = False
RENAME_NOREPLACE = 1
RENAME_EXCHANGE = 2
MFD_NOEXEC_SEAL_FLAG = 0x0008
MFD_EXEC_FLAG = 0x0010
F_SEAL_EXEC_FLAG = 0x0020
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SAFE_ENV = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TASK_SCOPES = {
    "core_scanner",
    "gadget_report",
    "integrated_analysis",
    "baseline_gadget_report",
    "mitigation_metadata",
}
EXTRACTORS = {"none", "x64lens_json_0_2"}
ORDER_POLICIES = {"listed", "alternating"}
CACHE_POLICIES = {"warm", "uncontrolled"}
SIGNALS = {signal.SIGINT, signal.SIGTERM}
MAX_CAPTURE_BYTES = 256 * 1024 * 1024
RESERVED_ENVIRONMENT_KEYS = {
    "HOME",
    "TMPDIR",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "LANG",
    "LC_ALL",
    "TZ",
    "PATH",
    "X64LENS_BENCHMARK_EVIDENCE_CLASS",
}
ACTIVE_PROCESS_GROUP: int | None = None
SPAWNING_PROCESS = False
CREATING_STAGE = False
INTERRUPTED_BY: int | None = None
WAIT4_RESOURCE_SCOPE = (
    "Linux wait4 rusage for the selected child, including descendants that child waited for; "
    "descendants reaped separately by the runner are excluded; not complete process-tree accounting"
)
WAIT4_MAX_RSS_UNIT = (
    "kilobytes on Linux; maximum across the selected child and descendants it waited for, "
    "not a process-tree sum"
)

ROW_FIELDS = (
    "runner_schema_version",
    "campaign_id",
    "evidence_class",
    "frozen",
    "publication_eligible",
    "run_id",
    "phase",
    "round",
    "order_index",
    "included_in_primary_summary",
    "summary_exclusion_reason",
    "condition_id",
    "task_scope",
    "profile_id",
    "worker_count",
    "output_scope",
    "tool_id",
    "tool_version",
    "tool_sha256",
    "target_id",
    "target_sha256",
    "target_size_bytes",
    "target_license",
    "command_json",
    "command_cwd",
    "stdout_path",
    "stderr_path",
    "stdout_limit_bytes",
    "stderr_limit_bytes",
    "output_limit_streams",
    "start_monotonic_ns",
    "end_monotonic_ns",
    "wall_time_ns",
    "user_time_ns",
    "system_time_ns",
    "max_rss_kb",
    "minor_faults",
    "major_faults",
    "voluntary_context_switches",
    "involuntary_context_switches",
    "throughput_mib_s",
    "stdout_bytes",
    "stdout_sha256",
    "stderr_bytes",
    "stderr_sha256",
    "exit_code",
    "signal",
    "signal_name",
    "timed_out",
    "descendant_cleanup_required",
    "descendants_reaped",
    "process_outcome",
    "outcome",
    "timer_floor_ns",
    "timing_class",
    "batch_size",
    "extractor",
    "schema_version",
    "report_command",
    "analysis_complete",
    "raw_candidate_count",
    "exact_pattern_count",
    "semantic_candidate_count",
    "unknown_candidate_count",
    "scored_candidate_count",
    "error",
)


class RunnerError(RuntimeError):
    """Raised for invalid campaign input or an unsafe benchmark state."""


class RunnerInterrupted(RunnerError):
    """Raised when SIGINT or SIGTERM interrupts a campaign."""


def restore_signal_mask_deferred(previous_mask: set[signal.Signals]) -> None:
    """Restore a signal mask without allowing pending campaign signals to abort cleanup."""
    global INTERRUPTED_BY
    handlers = {signum: signal.getsignal(signum) for signum in SIGNALS}

    def record_only(signum: int, _frame: Any) -> None:
        global INTERRUPTED_BY
        if INTERRUPTED_BY is None:
            INTERRUPTED_BY = signum

    for signum in SIGNALS:
        signal.signal(signum, record_only)
    try:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
    finally:
        for signum, handler in handlers.items():
            signal.signal(signum, handler)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RunnerError(message)


@dataclass
class OwnedStage:
    """Creation-time identity for one same-parent staging directory.

    A held descriptor remains authoritative if a measured tool renames the
    directory. Cleanup follows that descriptor, blocks campaign signals, and
    removes only the captured device/inode. A replacement at the original name
    is foreign and is preserved.
    """

    path: Path
    parent: Path
    name: str
    parent_fd: int
    directory_fd: int
    device: int
    inode: int
    committed: bool = False

    @classmethod
    def create(
        cls,
        parent: Path,
        name: str,
        registry: list["OwnedStage"] | None = None,
    ) -> "OwnedStage":
        resolved_parent = parent.resolve(strict=True)
        require(Path(name).name == name and name not in {"", ".", ".."}, "unsafe staging directory name")
        parent_fd = os.open(
            resolved_parent,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        created_identity: tuple[int, int] | None = None
        directory_fd = -1
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
            created = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            require(stat.S_ISDIR(created.st_mode), "created staging object is not a directory")
            created_identity = (created.st_dev, created.st_ino)
            directory_fd = os.open(
                name,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
            metadata = os.fstat(directory_fd)
            require(
                stat.S_ISDIR(metadata.st_mode)
                and (metadata.st_dev, metadata.st_ino) == created_identity,
                "created staging directory changed while being opened",
            )
            owned = cls(
                path=resolved_parent / name,
                parent=resolved_parent,
                name=name,
                parent_fd=parent_fd,
                directory_fd=directory_fd,
                device=metadata.st_dev,
                inode=metadata.st_ino,
            )
            if registry is not None:
                registry.append(owned)
            return owned
        except BaseException as failure:
            if directory_fd >= 0:
                os.close(directory_fd)
            cleanup_failure: BaseException | None = None
            if created_identity is not None:
                try:
                    observed = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                    if stat.S_ISDIR(observed.st_mode) and (observed.st_dev, observed.st_ino) == created_identity:
                        os.rmdir(name, dir_fd=parent_fd)
                        os.fsync(parent_fd)
                except FileNotFoundError:
                    pass
                except BaseException as exc:
                    cleanup_failure = exc
            os.close(parent_fd)
            if cleanup_failure is not None:
                raise RunnerError(
                    f"staging creation failed with {type(failure).__name__}; partial-stage cleanup also failed: {cleanup_failure}"
                ) from failure
            raise

    @classmethod
    def adopt(cls, path: Path, expected_parent: Path, label: str) -> "OwnedStage":
        parent = expected_parent.resolve(strict=True)
        candidate = Path(os.path.abspath(path))
        require(candidate.parent == parent, f"{label} is outside its expected parent")
        metadata = os.lstat(candidate)
        require(stat.S_ISDIR(metadata.st_mode), f"{label} is not a real directory")
        parent_fd = os.open(
            parent,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            directory_fd = os.open(
                candidate.name,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
            observed = os.fstat(directory_fd)
            require(
                (observed.st_dev, observed.st_ino) == (metadata.st_dev, metadata.st_ino),
                f"{label} changed while being adopted",
            )
            return cls(candidate, parent, candidate.name, parent_fd, directory_fd, metadata.st_dev, metadata.st_ino)
        except BaseException:
            os.close(parent_fd)
            raise

    @property
    def authoritative_path(self) -> Path:
        """Descriptor-rooted path that continues to name the owned directory."""
        require(self.directory_fd >= 0, "staging directory descriptor is closed")
        return Path(f"/proc/self/fd/{self.directory_fd}")

    def close(self) -> None:
        if self.directory_fd >= 0:
            os.close(self.directory_fd)
            self.directory_fd = -1
        if self.parent_fd >= 0:
            os.close(self.parent_fd)
            self.parent_fd = -1

    def require_named_identity(self, label: str) -> None:
        metadata = os.stat(self.name, dir_fd=self.parent_fd, follow_symlinks=False)
        require(
            stat.S_ISDIR(metadata.st_mode)
            and (metadata.st_dev, metadata.st_ino) == (self.device, self.inode),
            f"{label} path no longer names the runner-owned staging directory",
        )

    def _current_parent_and_name(self, label: str) -> tuple[int, str]:
        """Open the directory's current parent through the held descriptor."""
        for _attempt in range(32):
            parent_fd = os.open(
                f"/proc/self/fd/{self.directory_fd}/..",
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
            )
            matches: list[str] = []
            try:
                with os.scandir(parent_fd) as entries:
                    for entry in entries:
                        try:
                            metadata = entry.stat(follow_symlinks=False)
                        except FileNotFoundError:
                            continue
                        if stat.S_ISDIR(metadata.st_mode) and (metadata.st_dev, metadata.st_ino) == (self.device, self.inode):
                            matches.append(entry.name)
                if len(matches) == 1:
                    return parent_fd, matches[0]
            except BaseException:
                os.close(parent_fd)
                raise
            os.close(parent_fd)
        raise RunnerError(f"{label} creation-time identity is not reachable from its current parent")

    def cleanup(self, label: str) -> None:
        previous = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
        try:
            _clear_directory_fd(self.directory_fd, label, self.device)
            for _attempt in range(32):
                parent_fd, current_name = self._current_parent_and_name(label)
                try:
                    metadata = os.stat(current_name, dir_fd=parent_fd, follow_symlinks=False)
                    require(
                        (metadata.st_dev, metadata.st_ino) == (self.device, self.inode),
                        f"{label} changed before final removal",
                    )
                    try:
                        os.rmdir(current_name, dir_fd=parent_fd)
                    except FileNotFoundError:
                        continue
                    os.fsync(parent_fd)
                    return
                finally:
                    os.close(parent_fd)
            raise RunnerError(f"{label} could not be removed after repeated relocation")
        finally:
            restore_signal_mask_deferred(previous)


def _rename_exchange(parent_fd: int, left: str, right: str, label: str) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    require(renameat2 is not None, "Linux renameat2 is required for authenticated publication")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(parent_fd, os.fsencode(left), parent_fd, os.fsencode(right), RENAME_EXCHANGE)
    if result != 0:
        code = ctypes.get_errno()
        raise RunnerError(f"{label} exchange failed: {os.strerror(code)}")


def _remove_placeholder(parent_fd: int, name: str, identity: tuple[int, int], label: str) -> None:
    metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    require(
        stat.S_ISDIR(metadata.st_mode) and (metadata.st_dev, metadata.st_ino) == identity,
        f"{label} placeholder identity changed",
    )
    os.rmdir(name, dir_fd=parent_fd)


def _publish_owned_stage(stage: OwnedStage, final: Path, label: str) -> None:
    """Commit exactly the creation-time stage inode with exchange-and-verify CAS.

    A private placeholder reserves the final name. An atomic exchange moves the
    object currently named as the stage to the final name; post-exchange inode
    authentication either commits the owned directory or exchanges a substituted
    object back and removes the placeholder.
    """
    final_absolute = Path(os.path.abspath(final))
    require(final_absolute.parent == stage.parent, f"{label} final path is outside the staging parent")
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
    placeholder_fd = -1
    placeholder_identity: tuple[int, int] | None = None
    exchanged = False
    try:
        stage.require_named_identity(label)
        try:
            os.mkdir(final_absolute.name, 0o700, dir_fd=stage.parent_fd)
        except FileExistsError as exc:
            raise RunnerError(f"campaign result already exists: {final_absolute}") from exc
        placeholder_fd = os.open(
            final_absolute.name,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=stage.parent_fd,
        )
        placeholder_stat = os.fstat(placeholder_fd)
        placeholder_identity = (placeholder_stat.st_dev, placeholder_stat.st_ino)
        _rename_exchange(stage.parent_fd, stage.name, final_absolute.name, label)
        exchanged = True
        final_stat = os.stat(final_absolute.name, dir_fd=stage.parent_fd, follow_symlinks=False)
        if not (
            stat.S_ISDIR(final_stat.st_mode)
            and (final_stat.st_dev, final_stat.st_ino) == (stage.device, stage.inode)
        ):
            _rename_exchange(stage.parent_fd, final_absolute.name, stage.name, f"{label} rollback")
            exchanged = False
            _remove_placeholder(stage.parent_fd, final_absolute.name, placeholder_identity, label)
            placeholder_identity = None
            os.fsync(stage.parent_fd)
            raise RunnerError(f"{label} publication refused a substituted directory")
        stage_placeholder = os.stat(stage.name, dir_fd=stage.parent_fd, follow_symlinks=False)
        require(
            stat.S_ISDIR(stage_placeholder.st_mode)
            and (stage_placeholder.st_dev, stage_placeholder.st_ino) == placeholder_identity,
            f"{label} placeholder changed after exchange",
        )
        os.rmdir(stage.name, dir_fd=stage.parent_fd)
        placeholder_identity = None
        os.fsync(stage.parent_fd)
        stage.committed = True
    except BaseException as failure:
        recovery_failure: BaseException | None = None
        if placeholder_identity is not None:
            try:
                try:
                    final_stat = os.stat(final_absolute.name, dir_fd=stage.parent_fd, follow_symlinks=False)
                    final_identity = (final_stat.st_dev, final_stat.st_ino)
                except FileNotFoundError:
                    final_identity = None
                try:
                    stage_stat = os.stat(stage.name, dir_fd=stage.parent_fd, follow_symlinks=False)
                    stage_identity = (stage_stat.st_dev, stage_stat.st_ino)
                except FileNotFoundError:
                    stage_identity = None

                owned_identity = (stage.device, stage.inode)
                if final_identity == owned_identity:
                    if stage_identity == placeholder_identity:
                        _remove_placeholder(stage.parent_fd, stage.name, placeholder_identity, label)
                    stage.committed = True
                    placeholder_identity = None
                    os.fsync(stage.parent_fd)
                elif final_identity == placeholder_identity:
                    _remove_placeholder(stage.parent_fd, final_absolute.name, placeholder_identity, label)
                    placeholder_identity = None
                    os.fsync(stage.parent_fd)
                elif stage_identity == placeholder_identity and final_identity is not None:
                    _rename_exchange(stage.parent_fd, final_absolute.name, stage.name, f"{label} recovery")
                    _remove_placeholder(stage.parent_fd, final_absolute.name, placeholder_identity, label)
                    placeholder_identity = None
                    os.fsync(stage.parent_fd)
            except BaseException as exc:
                recovery_failure = exc
        if recovery_failure is not None:
            raise RunnerError(
                f"{label} publication failed with {type(failure).__name__}; recovery also failed: {recovery_failure}"
            ) from failure
        raise
    finally:
        if placeholder_fd >= 0:
            os.close(placeholder_fd)
        restore_signal_mask_deferred(previous)


def _clear_directory_fd(directory_fd: int, label: str, device: int) -> None:
    """Remove one owned staging directory without following symlinks."""
    os.fchmod(directory_fd, 0o700)
    with os.scandir(directory_fd) as entries:
        snapshot = list(entries)
    for entry in snapshot:
        metadata = entry.stat(follow_symlinks=False)
        if stat.S_ISDIR(metadata.st_mode):
            require(metadata.st_dev == device, f"{label} crosses a filesystem boundary: {entry.name}")
            os.chmod(entry.name, 0o700, dir_fd=directory_fd, follow_symlinks=False)
            child_fd = os.open(
                entry.name,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            try:
                observed = os.fstat(child_fd)
                require(
                    (observed.st_dev, observed.st_ino) == (metadata.st_dev, metadata.st_ino),
                    f"{label} directory changed during cleanup: {entry.name}",
                )
                _clear_directory_fd(child_fd, f"{label}/{entry.name}", device)
            finally:
                os.close(child_fd)
            os.rmdir(entry.name, dir_fd=directory_fd)
        else:
            os.unlink(entry.name, dir_fd=directory_fd)


def remove_staging_tree(path: Path, expected_parent: Path, label: str) -> None:
    """Compatibility wrapper for tests that adopt and remove one real tree."""
    owned = OwnedStage.adopt(path, expected_parent, label)
    try:
        owned.cleanup(label)
    finally:
        owned.close()


def positive_int(value: Any, name: str, *, minimum: int = 1) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{name} must be an integer")
    require(value >= minimum, f"{name} must be >= {minimum}")
    return value


def nonnegative_int(value: Any, name: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{name} must be an integer")
    require(value >= 0, f"{name} must be non-negative")
    return value


def positive_number(value: Any, name: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{name} must be numeric")
    parsed = float(value)
    require(math.isfinite(parsed) and parsed > 0, f"{name} must be finite and positive")
    return parsed


def safe_identifier(value: Any, name: str) -> str:
    require(isinstance(value, str) and SAFE_ID.fullmatch(value) is not None, f"{name} has an unsafe identifier")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_identity(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def file_identity_fd(fd: int) -> dict[str, Any]:
    metadata = os.fstat(fd)
    digest = hashlib.sha256()
    offset = 0
    while offset < metadata.st_size:
        chunk = os.pread(fd, min(1024 * 1024, metadata.st_size - offset), offset)
        require(chunk, "short read while capturing measured output")
        digest.update(chunk)
        offset += len(chunk)
    return {
        "size_bytes": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
        "sha256": digest.hexdigest(),
    }


def capture_open_artifact_identity(handle: Any, path: Path, label: str) -> dict[str, Any]:
    handle.flush()
    descriptor_metadata = os.fstat(handle.fileno())
    path_metadata = path.lstat()
    require(stat.S_ISREG(descriptor_metadata.st_mode), f"{label} descriptor is not a regular file")
    require(stat.S_ISREG(path_metadata.st_mode), f"{label} path is not a regular file")
    require(
        (descriptor_metadata.st_dev, descriptor_metadata.st_ino)
        == (path_metadata.st_dev, path_metadata.st_ino),
        f"{label} path changed during execution",
    )
    os.fchmod(handle.fileno(), 0o444)
    read_fd = os.open(
        f"/proc/self/fd/{handle.fileno()}",
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        read_metadata = os.fstat(read_fd)
        require(
            (descriptor_metadata.st_dev, descriptor_metadata.st_ino)
            == (read_metadata.st_dev, read_metadata.st_ino),
            f"{label} descriptor changed while reopening for capture",
        )
        return file_identity_fd(read_fd)
    finally:
        os.close(read_fd)


def require_snapshot_identity(
    path: Path,
    record: dict[str, Any],
    label: str,
    expected_mode: int,
) -> None:
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode), f"{label} snapshot is not a regular file")
    require(stat.S_IMODE(metadata.st_mode) == expected_mode, f"{label} snapshot mode changed during execution")
    identity = file_identity(path)
    require(
        identity["size_bytes"] == record["size_bytes"] and identity["sha256"] == record["sha256"],
        f"{label} snapshot changed during execution",
    )


def require_artifact_identity(
    path: Path,
    *,
    expected_size: int,
    expected_sha256: str,
    label: str,
) -> None:
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file")
    identity = file_identity(path)
    require(
        identity["size_bytes"] == expected_size and identity["sha256"] == expected_sha256,
        f"{label} changed after capture",
    )


def write_all(fd: int, value: bytes) -> None:
    offset = 0
    while offset < len(value):
        written = os.write(fd, value[offset:])
        require(written > 0, "short write while creating sealed execution input")
        offset += written


def create_execution_memfd(label: str, *, executable: bool) -> tuple[int, str]:
    require(hasattr(os, "memfd_create"), "Linux memfd_create is required for sealed execution inputs")
    base_flags = getattr(os, "MFD_CLOEXEC", 0x0001) | getattr(os, "MFD_ALLOW_SEALING", 0x0002)
    name = f"x64lens-{label}"[:200]
    if not executable:
        try:
            return (
                os.memfd_create(
                    name,
                    base_flags | getattr(os, "MFD_NOEXEC_SEAL", MFD_NOEXEC_SEAL_FLAG),
                ),
                "explicit_mfd_noexec_seal",
            )
        except OSError as exc:
            raise RunnerError(
                "Linux MFD_NOEXEC_SEAL support is required to guarantee that measured target bytes cannot execute"
            ) from exc
    try:
        return os.memfd_create(name, base_flags | getattr(os, "MFD_EXEC", MFD_EXEC_FLAG)), "explicit_mfd_exec"
    except OSError as exc:
        if exc.errno != errno.EINVAL:
            raise RunnerError(f"cannot create executable Linux memfd: {exc}") from exc
        try:
            return os.memfd_create(name, base_flags), "legacy_implicit_exec"
        except OSError as fallback_exc:
            raise RunnerError(f"cannot create legacy executable Linux memfd: {fallback_exc}") from fallback_exc


def execution_seal_mask(*, executable: bool) -> int:
    required = (
        fcntl.F_SEAL_SEAL
        | fcntl.F_SEAL_SHRINK
        | fcntl.F_SEAL_GROW
        | fcntl.F_SEAL_WRITE
    )
    if not executable:
        required |= getattr(fcntl, "F_SEAL_EXEC", F_SEAL_EXEC_FLAG)
    return required


def add_execution_seals(fd: int, label: str, *, executable: bool) -> int:
    required_seals = execution_seal_mask(executable=executable)
    fcntl.fcntl(fd, fcntl.F_ADD_SEALS, required_seals)
    observed_seals = fcntl.fcntl(fd, fcntl.F_GET_SEALS)
    require(observed_seals & required_seals == required_seals, f"cannot seal execution input: {label}")
    return observed_seals


def sealed_execution_copy(source: Path, label: str, expected_mode: int) -> dict[str, Any]:
    required_constants = (
        "F_ADD_SEALS",
        "F_GET_SEALS",
        "F_SEAL_SEAL",
        "F_SEAL_SHRINK",
        "F_SEAL_GROW",
        "F_SEAL_WRITE",
    )
    require(
        all(hasattr(fcntl, name) for name in required_constants),
        "Linux file seals are required for sealed execution inputs",
    )
    executable = bool(expected_mode & 0o111)
    fd, creation_mode = create_execution_memfd(label, executable=executable)
    try:
        with source.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                write_all(fd, chunk)
        try:
            os.fchmod(fd, expected_mode)
        except OSError as exc:
            raise RunnerError(
                f"cannot set sealed execution input mode for {label}; "
                f"Linux memfd execution policy may prohibit executable memfds: {exc}"
            ) from exc
        observed_seals = add_execution_seals(fd, label, executable=executable)
        execution_path = Path(f"/proc/self/fd/{fd}")
        identity = file_identity(execution_path)
        source_identity = file_identity(source)
        require(
            identity["size_bytes"] == source_identity["size_bytes"]
            and identity["sha256"] == source_identity["sha256"],
            f"sealed execution input mismatch: {label}",
        )
        return {
            "execution_fd": fd,
            "execution_absolute": execution_path,
            "execution_protection": (
                "linux_memfd_write_sealed" if executable else "linux_memfd_noexec_write_sealed"
            ),
            "execution_memfd_creation": creation_mode,
            "execution_sha256": identity["sha256"],
            "execution_size_bytes": identity["size_bytes"],
            "execution_seals": (
                ["seal", "shrink", "grow", "write"]
                if executable
                else ["seal", "shrink", "grow", "write", "exec"]
            ),
            "execution_seal_mask": observed_seals,
        }
    except BaseException:
        os.close(fd)
        raise


def diagnostic_platform_preflight() -> str:
    require(platform.system() == "Linux" and hasattr(os, "wait4"), "diagnostic runner requires Linux wait4")
    required_constants = (
        "F_ADD_SEALS",
        "F_GET_SEALS",
        "F_SEAL_SEAL",
        "F_SEAL_SHRINK",
        "F_SEAL_GROW",
        "F_SEAL_WRITE",
    )
    require(
        all(hasattr(fcntl, name) for name in required_constants),
        "Linux file seals are required for sealed execution inputs",
    )
    fd, creation_mode = create_execution_memfd("platform-preflight", executable=True)
    try:
        write_all(fd, b"#!/bin/sh\nexit 0\n")
        try:
            os.fchmod(fd, 0o555)
        except OSError as exc:
            raise RunnerError(
                "cannot make the diagnostic preflight memfd executable; "
                f"Linux memfd execution policy rejected it: {exc}"
            ) from exc
        add_execution_seals(fd, "platform-preflight", executable=True)
        completed = subprocess.run(
            [f"/proc/self/fd/{fd}"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=command_environment({}),
            close_fds=True,
            pass_fds=(fd,),
            timeout=5,
            check=False,
        )
        require(
            completed.returncode == 0,
            "sealed executable memfd preflight failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip(),
        )
    finally:
        os.close(fd)

    noexec_fd, noexec_creation_mode = create_execution_memfd("platform-noexec-preflight", executable=False)
    try:
        with Path("/bin/true").open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                write_all(noexec_fd, chunk)
        os.fchmod(noexec_fd, 0o444)
        add_execution_seals(noexec_fd, "platform-noexec-preflight", executable=False)
        noexec_path = f"/proc/self/fd/{noexec_fd}"
        try:
            os.fchmod(noexec_fd, 0o555)
        except OSError:
            pass
        else:
            raise RunnerError("MFD_NOEXEC_SEAL allowed executable mode to be added")
        try:
            denied = subprocess.run(
                [noexec_path],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                pass_fds=(noexec_fd,),
                timeout=5,
                check=False,
            )
        except OSError as exc:
            require(
                exc.errno in {errno.EACCES, errno.EPERM},
                f"unexpected MFD_NOEXEC_SEAL execution error: {exc}",
            )
        else:
            require(denied.returncode != 0, "MFD_NOEXEC_SEAL target executed during platform preflight")
        return f"{creation_mode};target={noexec_creation_mode}"
    finally:
        os.close(noexec_fd)


def require_execution_identity(record: dict[str, Any], label: str, expected_mode: int) -> None:
    path = record["execution_absolute"]
    fd = record["execution_fd"]
    metadata = path.stat()
    require(stat.S_ISREG(metadata.st_mode), f"{label} sealed execution copy is not a regular file")
    require(
        stat.S_IMODE(metadata.st_mode) == expected_mode,
        f"{label} sealed execution copy mode changed during execution",
    )
    required_seals = execution_seal_mask(executable=bool(expected_mode & 0o111))
    observed_seals = fcntl.fcntl(fd, fcntl.F_GET_SEALS)
    require(observed_seals & required_seals == required_seals, f"{label} execution seals changed")
    identity = file_identity(path)
    require(
        identity["size_bytes"] == record["execution_size_bytes"]
        and identity["sha256"] == record["execution_sha256"]
        and identity["sha256"] == record["sha256"],
        f"{label} sealed execution copy changed during execution",
    )


def close_execution_inputs(
    tools: dict[str, dict[str, Any]],
    targets: dict[str, dict[str, Any]],
    probe: dict[str, Any] | None,
) -> None:
    records = [*tools.values(), *targets.values()]
    if probe is not None:
        records.append(probe)
    for record in records:
        fd = record.pop("execution_fd", None)
        if isinstance(fd, int):
            try:
                os.close(fd)
            except OSError:
                pass


def require_campaign_snapshot_identities(
    *,
    spec_snapshot: Path,
    spec_record: dict[str, Any],
    runner_snapshot: Path,
    runner_record: dict[str, Any],
    tools: dict[str, dict[str, Any]],
    targets: dict[str, dict[str, Any]],
    probe: dict[str, Any],
) -> None:
    require_snapshot_identity(spec_snapshot, spec_record, "campaign spec", 0o444)
    require_snapshot_identity(runner_snapshot, runner_record, "diagnostic runner", 0o555)
    for tool_id, tool in tools.items():
        require_snapshot_identity(tool["snapshot_absolute"], tool, f"tool {tool_id}", 0o555)
        require_execution_identity(tool, f"tool {tool_id}", 0o555)
    for target_id, target in targets.items():
        require_snapshot_identity(target["snapshot_absolute"], target, f"target {target_id}", 0o444)
        require_execution_identity(target, f"target {target_id}", 0o444)
    require_snapshot_identity(probe["snapshot_absolute"], probe, "timer floor probe", 0o555)
    require_execution_identity(probe, "timer floor probe", 0o555)




def open_directory_nofollow(path: Path, label: str) -> int:
    """Open a directory without accepting symlink ancestors.

    A descriptor-rooted ``/proc/self/fd/<n>`` prefix is accepted only for an
    already-open directory descriptor owned by this process. Every remaining
    component is opened relative to the preceding descriptor with O_NOFOLLOW.
    """
    absolute = Path(os.path.abspath(path))
    parts = absolute.parts
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    proc_prefix = (os.sep, "proc", "self", "fd")
    if len(parts) >= 5 and parts[:4] == proc_prefix and parts[4].isdigit():
        source_fd = int(parts[4])
        try:
            current_fd = os.dup(source_fd)
        except OSError as exc:
            raise RunnerError(f"{label} descriptor root is unavailable") from exc
        remaining = parts[5:]
    else:
        current_fd = os.open(os.sep, flags)
        remaining = parts[1:]
    try:
        metadata = os.fstat(current_fd)
        require(stat.S_ISDIR(metadata.st_mode), f"{label} root is not a directory")
        for component in remaining:
            require(component not in {"", ".", ".."}, f"{label} contains an unsafe component")
            next_fd = os.open(component, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
            metadata = os.fstat(current_fd)
            require(stat.S_ISDIR(metadata.st_mode), f"{label} component is not a directory: {component}")
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise

def write_json(path: Path, value: Any) -> None:
    data = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    parent_fd = open_directory_nofollow(path.parent, f"JSON parent {path.parent}")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path.name, flags, 0o600, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise RunnerError(f"refusing pre-existing JSON artifact: {path}") from exc
        try:
            write_all(fd, data)
            os.fchmod(fd, 0o444)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def fsync_tree(root: Path) -> None:
    """Validate and flush a complete staging tree before publication.

    Measured tools may write inside their isolated work directory. Result
    publication accepts only ordinary files and directories so a symlink, FIFO,
    socket, or device cannot redirect or stall the durability walk.
    """
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    cloexec = getattr(os, "O_CLOEXEC", 0)
    for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        metadata = path.lstat()
        is_directory = stat.S_ISDIR(metadata.st_mode)
        require(
            is_directory or stat.S_ISREG(metadata.st_mode),
            f"campaign staging tree contains a non-regular artifact: {path.relative_to(root)}",
        )
        flags = os.O_RDONLY | nofollow | cloexec
        if is_directory:
            flags |= getattr(os, "O_DIRECTORY", 0)
        fd = os.open(path, flags)
        try:
            observed = os.fstat(fd)
            require(
                (observed.st_dev, observed.st_ino) == (metadata.st_dev, metadata.st_ino),
                f"campaign staging member changed during durability walk: {path.relative_to(root)}",
            )
            os.fsync(fd)
        finally:
            os.close(fd)
    fd = open_directory_nofollow(root, "campaign staging root")
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_publish_noreplace(stage: Path, final: Path) -> None:
    """Publish a result directory atomically without replacing any sibling."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    require(renameat2 is not None, "Linux renameat2 is required for no-replace publication")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        -100,
        os.fsencode(stage),
        -100,
        os.fsencode(final),
        1,  # RENAME_NOREPLACE
    )
    if result != 0:
        code = ctypes.get_errno()
        if code == errno.EEXIST:
            raise RunnerError(f"campaign result already exists: {final}")
        raise RunnerError(f"cannot publish campaign result: {os.strerror(code)}")
    parent_fd = os.open(final.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def percentile(values: list[int], fraction: float) -> int:
    require(values, "percentile requires at least one value")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * fraction
    lower = int(math.floor(rank))
    upper = int(math.ceil(rank))
    if lower == upper:
        return ordered[lower]
    interpolated = ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)
    return int(math.ceil(interpolated))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_optional_text(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def cpu_model() -> str | None:
    value = read_optional_text(Path("/proc/cpuinfo"))
    if value is None:
        return None
    for line in value.splitlines():
        if line.lower().startswith("model name") and ":" in line:
            return line.split(":", 1)[1].strip()
    return None


def memory_total_kb() -> int | None:
    value = read_optional_text(Path("/proc/meminfo"))
    if value is None:
        return None
    for line in value.splitlines():
        if line.startswith("MemTotal:"):
            fields = line.split()
            if len(fields) >= 2 and fields[1].isdigit():
                return int(fields[1])
    return None


def environment_manifest(subreaper_enabled: bool) -> dict[str, Any]:
    monotonic = time.get_clock_info("monotonic")
    affinity: list[int] | None = None
    if hasattr(os, "sched_getaffinity"):
        try:
            affinity = sorted(os.sched_getaffinity(0))
        except OSError:
            affinity = None
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_executable": str(Path(sys.executable).resolve()),
        "python_executable_sha256": sha256_file(Path(sys.executable).resolve()),
        "logical_cpu_count": os.cpu_count(),
        "cpu_model": cpu_model(),
        "memory_total_kb": memory_total_kb(),
        "page_size_bytes": os.sysconf("SC_PAGE_SIZE"),
        "clock": {
            "implementation": monotonic.implementation,
            "monotonic": monotonic.monotonic,
            "adjustable": monotonic.adjustable,
            "reported_resolution_ns": max(1, int(math.ceil(monotonic.resolution * 1_000_000_000))),
        },
        "cpu_affinity": affinity,
        "cpu_governor": read_optional_text(Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")),
        "subreaper_enabled": subreaper_enabled,
        "max_rss_unit": WAIT4_MAX_RSS_UNIT,
        "resource_scope": WAIT4_RESOURCE_SCOPE,
    }


def enable_subreaper() -> bool:
    require(platform.system() == "Linux" and hasattr(os, "wait4"), "diagnostic runner requires Linux wait4")
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    prctl.restype = ctypes.c_int
    result = prctl(36, 1, 0, 0, 0)  # PR_SET_CHILD_SUBREAPER
    if result != 0:
        code = ctypes.get_errno()
        raise RunnerError(f"cannot enable Linux child subreaper: {os.strerror(code)}")
    return True


def signal_handler(signum: int, _frame: Any) -> None:
    global INTERRUPTED_BY
    first_signal = INTERRUPTED_BY is None
    if first_signal:
        INTERRUPTED_BY = signum
    if ACTIVE_PROCESS_GROUP is not None:
        try:
            os.killpg(ACTIVE_PROCESS_GROUP, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            pass
    if not first_signal or SPAWNING_PROCESS or CREATING_STAGE:
        return
    raise RunnerInterrupted(f"interrupted by {signal.Signals(signum).name}")


def install_signal_handlers() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def ignore_campaign_signals() -> None:
    """Keep repeated termination from replacing the controlled interrupted exit."""
    for signum in SIGNALS:
        signal.signal(signum, signal.SIG_IGN)


def process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def direct_child_pids() -> set[int]:
    """Return current children using the task file or a bounded /proc scan."""
    path = Path(f"/proc/self/task/{os.getpid()}/children")
    try:
        text = path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        proc = Path("/proc")
        require(proc.is_dir(), "Linux /proc child enumeration is unavailable")
        parent_pid = os.getpid()
        children: set[int] = set()
        for candidate in proc.iterdir():
            if not candidate.name.isdigit():
                continue
            try:
                status_text = (candidate / "status").read_text(encoding="ascii", errors="strict")
            except (FileNotFoundError, ProcessLookupError, PermissionError, OSError, UnicodeError):
                continue
            ppid: int | None = None
            for line in status_text.splitlines():
                if line.startswith("PPid:"):
                    try:
                        ppid = int(line.split(":", 1)[1].strip())
                    except ValueError as exc:
                        raise RunnerError(f"invalid PPid in {candidate}/status") from exc
                    break
            if ppid == parent_pid:
                children.add(int(candidate.name))
        return children
    except OSError as exc:
        raise RunnerError(f"cannot inspect Linux child process state: {exc}") from exc
    if not text:
        return set()
    try:
        return {int(value) for value in text.split()}
    except ValueError as exc:
        raise RunnerError(f"invalid Linux child process state: {text!r}") from exc


def reap_group_children(pgid: int, deadline: float) -> int:
    reaped = 0
    while time.monotonic() < deadline:
        progress = False
        while True:
            try:
                waited, _status, _usage = os.wait4(-pgid, os.WNOHANG)
            except ChildProcessError:
                waited = 0
            except InterruptedError:
                continue
            if waited <= 0:
                break
            progress = True
            reaped += 1
        if not process_group_exists(pgid):
            break
        if not progress:
            time.sleep(0.005)
    return reaped


def cleanup_process_group(pgid: int) -> tuple[bool, int]:
    if not process_group_exists(pgid):
        return False, 0
    required = True
    reaped = 0
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return required, reaped
    reaped += reap_group_children(pgid, time.monotonic() + 0.15)
    if process_group_exists(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        reaped += reap_group_children(pgid, time.monotonic() + 0.5)
    require(not process_group_exists(pgid), f"process group {pgid} survived cleanup")
    return required, reaped


def reap_any_children() -> int:
    reaped = 0
    while True:
        try:
            waited, _status, _usage = os.wait4(-1, os.WNOHANG)
        except ChildProcessError:
            break
        except InterruptedError:
            continue
        if waited <= 0:
            break
        reaped += 1
    return reaped


def cleanup_adopted_descendants() -> tuple[bool, int]:
    """Terminate descendants that escaped the measured process group.

    The runner is single-command-at-a-time and requires no unrelated child
    processes before each launch. After the direct child is reaped, any child
    visible here was adopted through PR_SET_CHILD_SUBREAPER. Iterating after
    each reap also catches grandchildren orphaned by an adopted helper.
    """
    children = direct_child_pids()
    if not children:
        return False, 0

    required = True
    reaped = 0
    for child in children:
        try:
            os.kill(child, signal.SIGTERM)
        except ProcessLookupError:
            pass

    term_deadline = time.monotonic() + 0.15
    while time.monotonic() < term_deadline:
        reaped += reap_any_children()
        children = direct_child_pids()
        if not children:
            return required, reaped
        time.sleep(0.005)

    kill_deadline = time.monotonic() + 2.0
    while time.monotonic() < kill_deadline:
        children = direct_child_pids()
        for child in children:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
        reaped += reap_any_children()
        if not direct_child_pids():
            return required, reaped
        time.sleep(0.005)

    raise RunnerError(f"adopted descendants survived cleanup: {sorted(direct_child_pids())}")


def wait_for_process(pid: int, timeout_seconds: float) -> tuple[int, resource.struct_rusage, bool]:
    deadline = time.monotonic() + timeout_seconds
    timed_out = False
    term_deadline: float | None = None
    reap_deadline: float | None = None
    while True:
        try:
            waited, status, usage = os.wait4(pid, os.WNOHANG)
        except InterruptedError:
            continue
        if waited == pid:
            return status, usage, timed_out
        now = time.monotonic()
        if now >= deadline and not timed_out:
            timed_out = True
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            term_deadline = now + 0.15
        if timed_out and term_deadline is not None and now >= term_deadline:
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            term_deadline = None
            reap_deadline = now + 2.0
        if reap_deadline is not None and now >= reap_deadline:
            raise RunnerError(f"measured process {pid} did not reap after SIGKILL")
        time.sleep(0.001)


def best_effort_reap_main(pid: int, timeout_seconds: float = 0.5) -> int | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            waited, status, _usage = os.wait4(pid, os.WNOHANG)
        except ChildProcessError:
            return None
        except InterruptedError:
            continue
        if waited == pid:
            return status
        time.sleep(0.005)
    return None


def _signal_process_group(pid: int, signum: int) -> None:
    try:
        os.killpg(pid, signum)
    except ProcessLookupError:
        pass


def _open_capture_directory(path: Path, label: str) -> int:
    """Create one result directory exclusively below a real existing parent."""
    parent = path.parent
    parent_fd = open_directory_nofollow(parent, f"{label} parent")
    try:
        try:
            os.mkdir(path.name, 0o700, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise RunnerError(f"refusing pre-existing {label}: {path}") from exc
        try:
            directory_fd = os.open(
                path.name,
                os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=parent_fd,
            )
        except BaseException:
            try:
                os.rmdir(path.name, dir_fd=parent_fd)
            except OSError:
                pass
            raise
        metadata = os.fstat(directory_fd)
        require(stat.S_ISDIR(metadata.st_mode), f"{label} is not a directory")
        return directory_fd
    finally:
        os.close(parent_fd)


def _create_child_directory(parent_fd: int, name: str, label: str) -> int:
    require(Path(name).name == name and name not in {"", ".", ".."}, f"unsafe {label} name")
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
    except FileExistsError as exc:
        raise RunnerError(f"refusing pre-existing {label}: {name}") from exc
    try:
        return os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except BaseException:
        try:
            os.rmdir(name, dir_fd=parent_fd)
        except OSError:
            pass
        raise


def _persist_captured_artifact(directory_fd: int, name: str, data: bytes, label: str) -> dict[str, Any]:
    require(Path(name).name == name and name not in {"", ".", ".."}, f"unsafe {label} name")
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        fd = os.open(name, flags, 0o600, dir_fd=directory_fd)
    except FileExistsError as exc:
        raise RunnerError(f"refusing pre-existing retained {label}: {name}") from exc
    try:
        write_all(fd, data)
        os.fchmod(fd, 0o600)
        os.fsync(fd)
        return file_identity_fd(fd)
    finally:
        os.close(fd)


def execute_process(
    argv: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
    environment: dict[str, str],
    maximum_stdout_bytes: int,
    maximum_stderr_bytes: int,
    pass_fds: tuple[int, ...] = (),
) -> dict[str, Any]:
    """Execute one measured child with exact bounded parent-side capture."""
    global ACTIVE_PROCESS_GROUP, SPAWNING_PROCESS
    require(argv and Path(argv[0]).is_absolute(), "measured executable path must be absolute")
    require(stdout_path.parent == stderr_path.parent, "stdout and stderr must share one capture directory")
    positive_int(maximum_stdout_bytes, "maximum_stdout_bytes")
    positive_int(maximum_stderr_bytes, "maximum_stderr_bytes")
    require(maximum_stdout_bytes <= MAX_CAPTURE_BYTES, "maximum_stdout_bytes exceeds the runner bound")
    require(maximum_stderr_bytes <= MAX_CAPTURE_BYTES, "maximum_stderr_bytes exceeds the runner bound")
    require(cwd.parent == stdout_path.parent, "work directory must be a direct child of the capture directory")
    capture_fd = -1
    work_fd = -1
    try:
        capture_fd = _open_capture_directory(stdout_path.parent, "capture directory")
        work_fd = _create_child_directory(capture_fd, cwd.name, "command work directory")
        child_environment = isolated_child_environment(environment, cwd, work_fd)
        require(not direct_child_pids(), "runner has unrelated child processes before measurement")
    except BaseException:
        if work_fd >= 0:
            os.close(work_fd)
        if capture_fd >= 0:
            os.close(capture_fd)
        if os.path.lexists(stdout_path.parent):
            try:
                remove_staging_tree(stdout_path.parent, stdout_path.parent.parent, "partial capture directory")
            except BaseException as cleanup_failure:
                raise RunnerError(f"execution setup failed and capture cleanup failed: {cleanup_failure}")
        raise
    start_ns = time.monotonic_ns()
    process: subprocess.Popen[bytes] | None = None
    pid: int | None = None
    selector = selectors.DefaultSelector()
    status: int | None = None
    usage: resource.struct_rusage | None = None
    end_ns: int | None = None
    timed_out = False
    termination_reason: str | None = None
    output_limit_streams: list[str] = []
    term_deadline: float | None = None
    kill_deadline: float | None = None
    cleanup_required = False
    descendants_reaped = 0
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    stream_limits = {"stdout": maximum_stdout_bytes, "stderr": maximum_stderr_bytes}
    streams: dict[int, tuple[str, Any]] = {}
    try:
        with open(os.devnull, "rb") as stdin_handle:
            SPAWNING_PROCESS = True
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=f"/proc/self/fd/{work_fd}",
                    stdin=stdin_handle,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=child_environment,
                    close_fds=True,
                    pass_fds=tuple(dict.fromkeys((*pass_fds, work_fd))),
                    start_new_session=True,
                )
            except OSError as exc:
                raise RunnerError(f"cannot start measured command {argv[0]}: {exc}") from exc
            pid = process.pid
            ACTIVE_PROCESS_GROUP = pid
            SPAWNING_PROCESS = False
            if INTERRUPTED_BY is not None:
                raise RunnerInterrupted(f"interrupted by {signal.Signals(INTERRUPTED_BY).name}")
            require(process.stdout is not None and process.stderr is not None, "measured capture pipes are missing")
            for label, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                descriptor = stream.fileno()
                os.set_blocking(descriptor, False)
                streams[descriptor] = (label, stream)
                selector.register(stream, selectors.EVENT_READ, descriptor)

            deadline = time.monotonic() + timeout_seconds
            cleanup_done = False
            while status is None or selector.get_map():
                if INTERRUPTED_BY is not None:
                    raise RunnerInterrupted(f"interrupted by {signal.Signals(INTERRUPTED_BY).name}")
                now = time.monotonic()
                if status is None:
                    try:
                        waited, observed_status, observed_usage = os.wait4(pid, os.WNOHANG)
                    except InterruptedError:
                        waited = 0
                    if waited == pid:
                        status = observed_status
                        usage = observed_usage
                        end_ns = time.monotonic_ns()

                if status is None and termination_reason is None and now >= deadline:
                    timed_out = True
                    termination_reason = "timeout"
                    _signal_process_group(pid, signal.SIGTERM)
                    term_deadline = now + 0.15
                    kill_deadline = now + 2.15
                if status is None and term_deadline is not None and now >= term_deadline:
                    _signal_process_group(pid, signal.SIGKILL)
                    term_deadline = None
                if status is None and kill_deadline is not None and now >= kill_deadline:
                    raise RunnerError(f"measured process {pid} did not reap after SIGKILL")

                selected = selector.select(0.01 if status is None else 0)
                for key, _events in selected:
                    descriptor = key.data
                    label, stream = streams[descriptor]
                    buffer = buffers[label]
                    limit = stream_limits[label]
                    room = limit - len(buffer)
                    try:
                        chunk = os.read(descriptor, min(65536, max(1, room + 1)))
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(stream)
                        stream.close()
                        continue
                    if len(chunk) > room:
                        if room > 0:
                            buffer.extend(chunk[:room])
                        if label not in output_limit_streams:
                            output_limit_streams.append(label)
                        if termination_reason is None:
                            termination_reason = "output_limit"
                            _signal_process_group(pid, signal.SIGTERM)
                            term_deadline = time.monotonic() + 0.15
                            kill_deadline = time.monotonic() + 2.15
                    else:
                        buffer.extend(chunk)

                if status is not None and not cleanup_done:
                    group_cleanup_required, group_descendants_reaped = cleanup_process_group(pid)
                    adopted_cleanup_required, adopted_descendants_reaped = cleanup_adopted_descendants()
                    cleanup_required = group_cleanup_required or adopted_cleanup_required
                    descendants_reaped = group_descendants_reaped + adopted_descendants_reaped
                    cleanup_done = True
                if status is not None and not selector.get_map():
                    break

            assert status is not None and usage is not None and end_ns is not None and process is not None
            process.returncode = os.waitstatus_to_exitcode(status)
    except BaseException:
        SPAWNING_PROCESS = False
        if work_fd >= 0:
            os.close(work_fd)
            work_fd = -1
        if capture_fd >= 0:
            os.close(capture_fd)
            capture_fd = -1
        if pid is not None:
            _signal_process_group(pid, signal.SIGKILL)
            try:
                emergency_status = best_effort_reap_main(pid)
                if emergency_status is not None and process is not None:
                    process.returncode = os.waitstatus_to_exitcode(emergency_status)
            except OSError:
                pass
            try:
                cleanup_process_group(pid)
            except RunnerError:
                pass
            try:
                cleanup_adopted_descendants()
            except RunnerError:
                pass
        raise
    finally:
        SPAWNING_PROCESS = False
        ACTIVE_PROCESS_GROUP = None
        selector.close()
        for _label, stream in streams.values():
            try:
                stream.close()
            except OSError:
                pass

    if work_fd >= 0:
        os.close(work_fd)
        work_fd = -1
    try:
        stdout_identity = _persist_captured_artifact(capture_fd, stdout_path.name, bytes(buffers["stdout"]), "stdout")
        stderr_identity = _persist_captured_artifact(capture_fd, stderr_path.name, bytes(buffers["stderr"]), "stderr")
    finally:
        os.close(capture_fd)

    exit_code: int | None = None
    signal_number: int | None = None
    if os.WIFEXITED(status):
        exit_code = os.WEXITSTATUS(status)
    elif os.WIFSIGNALED(status):
        signal_number = os.WTERMSIG(status)

    if termination_reason == "output_limit":
        process_outcome = "output_limit"
    elif timed_out:
        process_outcome = "timeout"
    elif signal_number is not None:
        process_outcome = "signal"
    elif exit_code != 0:
        process_outcome = "nonzero_exit"
    elif cleanup_required:
        process_outcome = "unexpected_descendants"
    else:
        process_outcome = "success"

    return {
        "start_monotonic_ns": start_ns,
        "end_monotonic_ns": end_ns,
        "wall_time_ns": end_ns - start_ns,
        "user_time_ns": int(round(usage.ru_utime * 1_000_000_000)),
        "system_time_ns": int(round(usage.ru_stime * 1_000_000_000)),
        "max_rss_kb": int(usage.ru_maxrss),
        "minor_faults": int(usage.ru_minflt),
        "major_faults": int(usage.ru_majflt),
        "voluntary_context_switches": int(usage.ru_nvcsw),
        "involuntary_context_switches": int(usage.ru_nivcsw),
        "stdout_limit_bytes": maximum_stdout_bytes,
        "stderr_limit_bytes": maximum_stderr_bytes,
        "output_limit_streams": "|".join(output_limit_streams),
        "stdout_bytes": stdout_identity["size_bytes"],
        "stdout_sha256": stdout_identity["sha256"],
        "stderr_bytes": stderr_identity["size_bytes"],
        "stderr_sha256": stderr_identity["sha256"],
        "exit_code": exit_code,
        "signal": signal_number,
        "signal_name": signal.Signals(signal_number).name if signal_number is not None else None,
        "timed_out": timed_out,
        "descendant_cleanup_required": cleanup_required,
        "descendants_reaped": descendants_reaped,
        "process_outcome": process_outcome,
    }


def resolve_spec_path(spec_dir: Path, raw: Any, name: str) -> tuple[str, Path]:
    require(isinstance(raw, str) and raw and "\x00" not in raw, f"{name} must be a nonempty path string")
    requested = raw
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = spec_dir / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise RunnerError(f"cannot resolve {name} {raw!r}: {exc}") from exc
    require(resolved.is_file(), f"{name} is not a regular file: {resolved}")
    return requested, resolved


def immutable_snapshot(source: Path, destination: Path, *, executable: bool) -> dict[str, Any]:
    before = file_identity(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    os.chmod(destination, 0o555 if executable else 0o444)
    after = file_identity(source)
    copied = file_identity(destination)
    require(before == after, f"source mutated while being snapshotted: {source}")
    require(before["sha256"] == copied["sha256"] and before["size_bytes"] == copied["size_bytes"], f"snapshot mismatch: {source}")
    return {
        "source_size_bytes": before["size_bytes"],
        "source_mtime_ns": before["mtime_ns"],
        "sha256": copied["sha256"],
        "size_bytes": copied["size_bytes"],
    }


def parse_spec(path: Path, campaign_override: str | None) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    try:
        before = file_identity(path)
        raw = path.read_bytes()
        after = file_identity(path)
        require(before == after, "campaign spec mutated while being read")
        require(before["size_bytes"] == len(raw) and before["sha256"] == sha256_bytes(raw), "campaign spec read identity mismatch")
        spec = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"cannot load campaign spec: {exc}") from exc
    require(isinstance(spec, dict), "campaign spec must be a JSON object")
    require(spec.get("schema_version") == RUNNER_SCHEMA_VERSION, "unsupported campaign spec schema")
    require(spec.get("evidence_class") == EVIDENCE_CLASS, "runner accepts diagnostic evidence only")
    require(spec.get("frozen") is False, "diagnostic campaign must declare frozen=false")
    require(spec.get("publication_eligible") is False, "diagnostic campaign must declare publication_eligible=false")
    campaign_id = safe_identifier(campaign_override or spec.get("campaign_id"), "campaign_id")
    spec["campaign_id"] = campaign_id

    spec["warmup_runs"] = nonnegative_int(spec.get("warmup_runs"), "warmup_runs")
    spec["measured_runs"] = positive_int(spec.get("measured_runs"), "measured_runs")
    spec["timeout_seconds"] = positive_number(spec.get("timeout_seconds"), "timeout_seconds")
    require(spec.get("order_policy") in ORDER_POLICIES, f"order_policy must be one of {sorted(ORDER_POLICIES)}")
    require(spec.get("cache_policy") in CACHE_POLICIES, f"cache_policy must be one of {sorted(CACHE_POLICIES)}")
    if spec["cache_policy"] == "warm":
        require(spec["warmup_runs"] >= 1, "cache_policy=warm requires at least one warmup run")
    require(isinstance(spec.get("fail_campaign_on_error"), bool), "fail_campaign_on_error must be boolean")

    capture_limits = spec.get("capture_limits")
    require(
        isinstance(capture_limits, dict)
        and set(capture_limits) == {"maximum_stdout_bytes", "maximum_stderr_bytes"},
        "capture_limits must contain maximum_stdout_bytes and maximum_stderr_bytes",
    )
    capture_limits["maximum_stdout_bytes"] = positive_int(
        capture_limits.get("maximum_stdout_bytes"), "capture_limits.maximum_stdout_bytes", minimum=4096
    )
    capture_limits["maximum_stderr_bytes"] = positive_int(
        capture_limits.get("maximum_stderr_bytes"), "capture_limits.maximum_stderr_bytes", minimum=4096
    )
    require(
        capture_limits["maximum_stdout_bytes"] <= MAX_CAPTURE_BYTES
        and capture_limits["maximum_stderr_bytes"] <= MAX_CAPTURE_BYTES,
        "capture limit exceeds the runner maximum",
    )

    environment = spec.get("environment", {})
    require(isinstance(environment, dict), "environment must be an object")
    for key, value in environment.items():
        require(isinstance(key, str) and SAFE_ENV.fullmatch(key), f"unsafe environment key: {key!r}")
        require(key not in RESERVED_ENVIRONMENT_KEYS, f"environment key is reserved by the runner: {key}")
        require(isinstance(value, str) and "\x00" not in value, f"environment value for {key} must be a string")

    timer_floor = spec.get("timer_floor")
    require(isinstance(timer_floor, dict), "timer_floor must be an object")
    timer_floor["runs"] = positive_int(timer_floor.get("runs"), "timer_floor.runs", minimum=5)
    timer_floor["threshold_multiplier"] = positive_number(timer_floor.get("threshold_multiplier"), "timer_floor.threshold_multiplier")
    require(isinstance(timer_floor.get("probe", "/bin/true"), str), "timer_floor.probe must be a path string")
    timer_floor.setdefault("probe", "/bin/true")

    tools = spec.get("tools")
    targets = spec.get("targets")
    conditions = spec.get("conditions")
    require(isinstance(tools, list) and tools, "tools must be a nonempty list")
    require(isinstance(targets, list) and targets, "targets must be a nonempty list")
    require(isinstance(conditions, list) and conditions, "conditions must be a nonempty list")

    tool_ids: set[str] = set()
    for index, tool in enumerate(tools):
        require(isinstance(tool, dict), f"tools[{index}] must be an object")
        tool_id = safe_identifier(tool.get("id"), f"tools[{index}].id")
        require(tool_id not in tool_ids, f"duplicate tool id: {tool_id}")
        tool_ids.add(tool_id)
        require(isinstance(tool.get("path"), str), f"tools[{index}].path must be a string")
        require(isinstance(tool.get("version"), str) and tool["version"], f"tools[{index}].version must be nonempty")
        version_argv = tool.get("version_argv")
        require(isinstance(version_argv, list) and version_argv and all(isinstance(arg, str) for arg in version_argv), f"tools[{index}].version_argv must be a string array")
        require(version_argv[0] == "{tool}", f"tools[{index}].version_argv must begin with {{tool}}")
        require(all("{target}" not in arg for arg in version_argv), f"tools[{index}].version_argv cannot use {{target}}")

    target_ids: set[str] = set()
    for index, target in enumerate(targets):
        require(isinstance(target, dict), f"targets[{index}] must be an object")
        target_id = safe_identifier(target.get("id"), f"targets[{index}].id")
        require(target_id not in target_ids, f"duplicate target id: {target_id}")
        target_ids.add(target_id)
        require(isinstance(target.get("path"), str), f"targets[{index}].path must be a string")
        require(isinstance(target.get("license"), str) and target["license"], f"targets[{index}].license must be nonempty")

    condition_ids: set[str] = set()
    for index, condition in enumerate(conditions):
        require(isinstance(condition, dict), f"conditions[{index}] must be an object")
        condition_id = safe_identifier(condition.get("id"), f"conditions[{index}].id")
        require(condition_id not in condition_ids, f"duplicate condition id: {condition_id}")
        condition_ids.add(condition_id)
        require(condition.get("tool") in tool_ids, f"conditions[{index}] names an unknown tool")
        require(condition.get("target") in target_ids, f"conditions[{index}] names an unknown target")
        require(condition.get("task_scope") in TASK_SCOPES, f"conditions[{index}] has an unsupported task_scope")
        safe_identifier(condition.get("profile_id"), f"conditions[{index}].profile_id")
        condition["worker_count"] = positive_int(condition.get("worker_count"), f"conditions[{index}].worker_count")
        require(condition.get("extractor") in EXTRACTORS, f"conditions[{index}] has an unsupported extractor")
        require(isinstance(condition.get("output_scope"), str) and condition["output_scope"], f"conditions[{index}].output_scope must be nonempty")
        argv = condition.get("argv")
        require(isinstance(argv, list) and argv and all(isinstance(arg, str) and "\x00" not in arg for arg in argv), f"conditions[{index}].argv must be a string array")
        require(argv[0] == "{tool}", f"conditions[{index}].argv must begin with {{tool}}")
        require(any("{target}" in arg for arg in argv), f"conditions[{index}].argv must include {{target}}")
        for arg in argv:
            residual = arg.replace("{tool}", "").replace("{target}", "")
            require("{" not in residual and "}" not in residual, f"conditions[{index}].argv uses an unsupported placeholder")
        if condition["extractor"] == "x64lens_json_0_2":
            require(condition.get("expected_report_command") in {"gadgets", "analyze"}, f"conditions[{index}] needs expected_report_command")
        else:
            require(condition.get("expected_report_command") in (None, ""), f"conditions[{index}] cannot expect a report command without an extractor")

    return spec, raw, {
        "source_size_bytes": before["size_bytes"],
        "source_mtime_ns": before["mtime_ns"],
        "sha256": before["sha256"],
        "size_bytes": len(raw),
    }


def command_environment(extra: dict[str, str]) -> dict[str, str]:
    environment = {
        "LANG": "C",
        "LC_ALL": "C",
        "TZ": "UTC",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "X64LENS_BENCHMARK_EVIDENCE_CLASS": EVIDENCE_CLASS,
    }
    environment.update(extra)
    return environment


def isolated_child_environment(base: dict[str, str], workdir: Path, work_fd: int) -> dict[str, str]:
    """Create per-command roots through the held work-directory descriptor."""
    environment_fd = _create_child_directory(work_fd, "environment", "command environment directory")
    try:
        names = {
            "HOME": "home",
            "TMPDIR": "tmp",
            "XDG_CACHE_HOME": "cache",
            "XDG_CONFIG_HOME": "config",
            "XDG_DATA_HOME": "data",
        }
        for name in names.values():
            child_fd = _create_child_directory(environment_fd, name, f"command environment {name}")
            os.close(child_fd)
    finally:
        os.close(environment_fd)
    environment = dict(base)
    environment.update({key: f"/proc/self/fd/{work_fd}/environment/{name}" for key, name in names.items()})
    return environment


def expand_argv(template: Iterable[str], tool: Path, target: Path | None = None) -> list[str]:
    values: list[str] = []
    for raw in template:
        value = raw.replace("{tool}", str(tool))
        if target is not None:
            value = value.replace("{target}", str(target))
        require("{tool}" not in value and "{target}" not in value, f"unresolved command placeholder: {raw!r}")
        values.append(value)
    return values


def path_from_workdir(path: Path, workdir: Path) -> Path:
    """Return a relative path that remains valid after staging publication."""
    return Path(os.path.relpath(path, workdir))


def observed_version(stdout_path: Path, stderr_path: Path) -> str:
    for path in (stdout_path, stderr_path):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if line.strip():
                return line.strip()
    return ""


def snapshot_inputs(
    spec: dict[str, Any],
    spec_dir: Path,
    stage: Path,
    environment: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    tools: dict[str, dict[str, Any]] = {}
    targets: dict[str, dict[str, Any]] = {}
    probe: dict[str, Any] | None = None
    try:
        for tool in spec["tools"]:
            requested, source = resolve_spec_path(spec_dir, tool["path"], f"tool {tool['id']}")
            require(os.access(source, os.X_OK), f"tool is not executable: {source}")
            snapshot = stage / "inputs" / "tools" / tool["id"]
            identity = immutable_snapshot(source, snapshot, executable=True)
            tools[tool["id"]] = {
                **tool,
                **identity,
                **sealed_execution_copy(snapshot, f"tool-{tool['id']}", 0o555),
                "source_path_requested": requested,
                "source_path_resolved": str(source),
                "snapshot_path": str(snapshot.relative_to(stage)),
                "snapshot_absolute": snapshot,
            }

        for target in spec["targets"]:
            requested, source = resolve_spec_path(spec_dir, target["path"], f"target {target['id']}")
            snapshot = stage / "inputs" / "targets" / target["id"]
            identity = immutable_snapshot(source, snapshot, executable=False)
            targets[target["id"]] = {
                **target,
                **identity,
                **sealed_execution_copy(snapshot, f"target-{target['id']}", 0o444),
                "source_path_requested": requested,
                "source_path_resolved": str(source),
                "snapshot_path": str(snapshot.relative_to(stage)),
                "snapshot_absolute": snapshot,
            }

        requested_probe, probe_source = resolve_spec_path(spec_dir, spec["timer_floor"]["probe"], "timer floor probe")
        require(os.access(probe_source, os.X_OK), f"timer floor probe is not executable: {probe_source}")
        probe_snapshot = stage / "inputs" / "timer-floor" / "probe"
        probe_identity = immutable_snapshot(probe_source, probe_snapshot, executable=True)
        probe = {
            **probe_identity,
            **sealed_execution_copy(probe_snapshot, "timer-floor-probe", 0o555),
            "source_path_requested": requested_probe,
            "source_path_resolved": str(probe_source),
            "snapshot_path": str(probe_snapshot.relative_to(stage)),
            "snapshot_absolute": probe_snapshot,
        }

        versions_root = stage / "inputs" / "versions"
        try:
            versions_root.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise RunnerError("refusing pre-existing tool-version directory") from exc
        for tool_id, tool in tools.items():
            version_dir = versions_root / tool_id
            version_workdir = version_dir / "work"
            require_snapshot_identity(tool["snapshot_absolute"], tool, f"tool {tool_id}", 0o555)
            require_execution_identity(tool, f"tool {tool_id}", 0o555)
            result = execute_process(
                expand_argv(tool["version_argv"], tool["execution_absolute"]),
                cwd=version_workdir,
                stdout_path=version_dir / "stdout.bin",
                stderr_path=version_dir / "stderr.bin",
                timeout_seconds=min(5.0, spec["timeout_seconds"]),
                environment=environment,
                maximum_stdout_bytes=spec["capture_limits"]["maximum_stdout_bytes"],
                maximum_stderr_bytes=spec["capture_limits"]["maximum_stderr_bytes"],
                pass_fds=(tool["execution_fd"],),
            )
            require_snapshot_identity(tool["snapshot_absolute"], tool, f"tool {tool_id}", 0o555)
            require_execution_identity(tool, f"tool {tool_id}", 0o555)
            require(result["process_outcome"] == "success", f"version command failed for {tool_id}: {result['process_outcome']}")
            observed = observed_version(version_dir / "stdout.bin", version_dir / "stderr.bin")
            require(tool["version"] in observed, f"declared version {tool['version']!r} not found in {tool_id} version output {observed!r}")
            tool["version_observed"] = observed
            tool["version_command"] = expand_argv(
                tool["version_argv"],
                path_from_workdir(tool["snapshot_absolute"], version_workdir),
            )
            tool["version_command_cwd"] = str(version_workdir.relative_to(stage))
            tool["version_result"] = {
                key: value for key, value in result.items()
                if key not in {"start_monotonic_ns", "end_monotonic_ns"}
            }
            tool["version_stdout_path"] = str((version_dir / "stdout.bin").relative_to(stage))
            tool["version_stderr_path"] = str((version_dir / "stderr.bin").relative_to(stage))

        return tools, targets, probe
    except BaseException:
        close_execution_inputs(tools, targets, probe)
        raise


def timer_floor_campaign(
    spec: dict[str, Any],
    stage: Path,
    probe: dict[str, Any],
    environment: dict[str, str],
) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    samples_root = stage / "timer-floor-samples"
    try:
        samples_root.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RunnerError("refusing pre-existing timer-floor sample directory") from exc
    for index in range(1, spec["timer_floor"]["runs"] + 1):
        sample_dir = samples_root / f"probe-{index:03d}"
        require_snapshot_identity(probe["snapshot_absolute"], probe, "timer floor probe", 0o555)
        require_execution_identity(probe, "timer floor probe", 0o555)
        result = execute_process(
            [str(probe["execution_absolute"])],
            cwd=sample_dir / "work",
            stdout_path=sample_dir / "stdout.bin",
            stderr_path=sample_dir / "stderr.bin",
            timeout_seconds=min(5.0, spec["timeout_seconds"]),
            environment=environment,
            maximum_stdout_bytes=spec["capture_limits"]["maximum_stdout_bytes"],
            maximum_stderr_bytes=spec["capture_limits"]["maximum_stderr_bytes"],
            pass_fds=(probe["execution_fd"],),
        )
        require_snapshot_identity(probe["snapshot_absolute"], probe, "timer floor probe", 0o555)
        require_execution_identity(probe, "timer floor probe", 0o555)
        require(result["process_outcome"] == "success", f"timer floor probe {index} failed: {result['process_outcome']}")
        samples.append({
            "run": index,
            **result,
            "stdout_path": str((sample_dir / "stdout.bin").relative_to(stage)),
            "stderr_path": str((sample_dir / "stderr.bin").relative_to(stage)),
        })

    wall_values = [sample["wall_time_ns"] for sample in samples]
    clock_resolution = max(1, int(math.ceil(time.get_clock_info("monotonic").resolution * 1_000_000_000)))
    p95 = percentile(wall_values, 0.95)
    reliable_floor = max(clock_resolution, int(math.ceil(p95 * spec["timer_floor"]["threshold_multiplier"])))
    result = {
        "schema_version": RUNNER_SCHEMA_VERSION,
        "probe_sha256": probe["sha256"],
        "runs": len(samples),
        "threshold_multiplier": spec["timer_floor"]["threshold_multiplier"],
        "clock_reported_resolution_ns": clock_resolution,
        "min_wall_time_ns": min(wall_values),
        "median_wall_time_ns": int(statistics.median(wall_values)),
        "p95_wall_time_ns": p95,
        "max_wall_time_ns": max(wall_values),
        "reliable_single_process_floor_ns": reliable_floor,
        "below_floor_action": "use a larger target or a future reviewed batch condition; do not claim a single-run delta",
        "samples": samples,
    }
    write_json(stage / "timer-floor.json", result)
    return result


def x64lens_extract(path: Path, expected_command: str, expected_tool_version: str) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunnerError(f"x64lens JSON extraction failed: {exc}") from exc
    require(isinstance(report, dict), "x64lens report must be an object")
    require(report.get("schema_version") == "0.2.0", "x64lens report schema must be 0.2.0")
    require(report.get("tool") == "x64lens", "x64lens report tool identity mismatch")
    require(report.get("tool_version") == expected_tool_version, "x64lens report tool version mismatch")
    require(report.get("report_type") == "analysis", "x64lens report type must be analysis")
    require(report.get("command") == expected_command, f"x64lens report command mismatch: expected {expected_command}")

    analysis = report.get("analysis")
    counts = report.get("counts")
    gadgets = report.get("gadgets")
    limitations = report.get("limitations")
    require(isinstance(analysis, dict), "x64lens report analysis must be an object")
    require(isinstance(counts, dict), "x64lens report counts must be an object")
    require(isinstance(gadgets, list), "x64lens report gadgets must be an array")
    require(isinstance(limitations, list) and limitations, "x64lens report limitations must be a nonempty array")

    fields = (
        "raw_candidate_count",
        "exact_pattern_count",
        "semantic_candidate_count",
        "unknown_candidate_count",
        "scored_candidate_count",
    )
    for field in fields:
        value = counts.get(field)
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"x64lens count {field} is invalid")

    candidate_capacity = analysis.get("candidate_capacity")
    candidate_count = analysis.get("candidate_count")
    max_depth = analysis.get("max_depth")
    regions_scanned = analysis.get("regions_scanned")
    regions_total = analysis.get("regions_total")
    for name, value in (
        ("candidate_capacity", candidate_capacity),
        ("candidate_count", candidate_count),
        ("max_depth", max_depth),
        ("regions_scanned", regions_scanned),
        ("regions_total", regions_total),
    ):
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, f"x64lens analysis {name} is invalid")
    require(candidate_capacity > 0 and max_depth > 0, "x64lens capacity and max depth must be positive")
    require(candidate_count <= candidate_capacity, "x64lens candidate capacity relationship is invalid")
    require(candidate_count == counts["raw_candidate_count"] == len(gadgets), "x64lens candidate count mismatch")
    require(counts["raw_candidate_count"] == counts["semantic_candidate_count"] + counts["unknown_candidate_count"], "x64lens semantic partition mismatch")
    require(counts["exact_pattern_count"] <= counts["raw_candidate_count"], "x64lens exact count exceeds raw count")
    require(counts["scored_candidate_count"] <= counts["semantic_candidate_count"], "x64lens scored count exceeds semantic count")
    require(regions_scanned <= regions_total, "x64lens region progress is invalid")
    require(analysis.get("complete") is True, "x64lens diagnostic row requires a complete report")
    require(analysis.get("candidate_truncated") is False, "x64lens diagnostic row cannot be truncated")
    require(analysis.get("candidate_dropped_count_known") is True, "x64lens dropped-count knowledge is invalid")
    require(analysis.get("candidate_dropped_count") == 0, "x64lens diagnostic row cannot drop candidates")
    require(regions_scanned == regions_total, "x64lens complete report must scan every region")

    return {
        "schema_version": report["schema_version"],
        "report_command": report["command"],
        "analysis_complete": analysis["complete"],
        **{field: counts[field] for field in fields},
    }


def render_row_value(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            raise RunnerError(f"cannot write non-finite row value: {value}")
        return f"{value:.12g}"
    return str(value)


def schedule_conditions(conditions: list[dict[str, Any]], rounds: int, policy: str) -> Iterable[tuple[int, int, dict[str, Any]]]:
    for round_number in range(1, rounds + 1):
        ordered = conditions if policy == "listed" or round_number % 2 == 1 else list(reversed(conditions))
        for order_index, condition in enumerate(ordered, start=1):
            yield round_number, order_index, condition


def run_conditions(
    spec: dict[str, Any],
    stage: Path,
    tools: dict[str, dict[str, Any]],
    targets: dict[str, dict[str, Any]],
    timer_floor: dict[str, Any],
    environment: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    outputs_root = stage / "outputs"
    try:
        outputs_root.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise RunnerError("refusing pre-existing campaign outputs directory") from exc
    phases = (("warmup", spec["warmup_runs"]), ("measured", spec["measured_runs"]))
    reliable_floor = timer_floor["reliable_single_process_floor_ns"]
    for phase, rounds in phases:
        for round_number, order_index, condition in schedule_conditions(spec["conditions"], rounds, spec["order_policy"]):
            tool = tools[condition["tool"]]
            target = targets[condition["target"]]
            run_id = f"{phase}-{round_number:03d}-{order_index:02d}-{condition['id']}"
            run_dir = outputs_root / run_id
            run_workdir = run_dir / "work"
            stdout_path = run_dir / "stdout.bin"
            stderr_path = run_dir / "stderr.bin"
            argv = expand_argv(condition["argv"], tool["execution_absolute"], target["execution_absolute"])
            recorded_argv = expand_argv(
                condition["argv"],
                path_from_workdir(tool["snapshot_absolute"], run_workdir),
                path_from_workdir(target["snapshot_absolute"], run_workdir),
            )
            require_snapshot_identity(tool["snapshot_absolute"], tool, f"tool {tool['id']}", 0o555)
            require_snapshot_identity(target["snapshot_absolute"], target, f"target {target['id']}", 0o444)
            require_execution_identity(tool, f"tool {tool['id']}", 0o555)
            require_execution_identity(target, f"target {target['id']}", 0o444)
            result = execute_process(
                argv,
                cwd=run_workdir,
                stdout_path=stdout_path,
                stderr_path=stderr_path,
                timeout_seconds=spec["timeout_seconds"],
                environment=environment,
                maximum_stdout_bytes=spec["capture_limits"]["maximum_stdout_bytes"],
                maximum_stderr_bytes=spec["capture_limits"]["maximum_stderr_bytes"],
                pass_fds=(tool["execution_fd"], target["execution_fd"]),
            )
            require_snapshot_identity(tool["snapshot_absolute"], tool, f"tool {tool['id']}", 0o555)
            require_snapshot_identity(target["snapshot_absolute"], target, f"target {target['id']}", 0o444)
            require_execution_identity(tool, f"tool {tool['id']}", 0o555)
            require_execution_identity(target, f"target {target['id']}", 0o444)
            wall_seconds = result["wall_time_ns"] / 1_000_000_000
            throughput = (target["size_bytes"] / (1024 * 1024)) / wall_seconds if wall_seconds > 0 else None
            timing_class = (
                "below_reliable_single_process_floor"
                if result["wall_time_ns"] < reliable_floor
                else "above_reliable_single_process_floor"
            )
            extracted = {
                "schema_version": None,
                "report_command": None,
                "analysis_complete": None,
                "raw_candidate_count": None,
                "exact_pattern_count": None,
                "semantic_candidate_count": None,
                "unknown_candidate_count": None,
                "scored_candidate_count": None,
            }
            outcome = result["process_outcome"]
            error = ""
            if outcome == "success" and condition["extractor"] == "x64lens_json_0_2":
                try:
                    extracted = x64lens_extract(stdout_path, condition["expected_report_command"], tool["version"])
                except RunnerError as exc:
                    outcome = "extractor_error"
                    error = str(exc)

            included_in_primary = (
                phase == "measured"
                and outcome == "success"
                and timing_class == "above_reliable_single_process_floor"
            )
            if phase == "warmup":
                exclusion_reason = "warmup"
            elif outcome != "success":
                exclusion_reason = outcome
            elif timing_class != "above_reliable_single_process_floor":
                exclusion_reason = "below_timer_floor"
            else:
                exclusion_reason = ""

            row = {
                "runner_schema_version": RUNNER_SCHEMA_VERSION,
                "campaign_id": spec["campaign_id"],
                "evidence_class": EVIDENCE_CLASS,
                "frozen": False,
                "publication_eligible": PUBLICATION_ELIGIBLE,
                "run_id": run_id,
                "phase": phase,
                "round": round_number,
                "order_index": order_index,
                "included_in_primary_summary": included_in_primary,
                "summary_exclusion_reason": exclusion_reason,
                "condition_id": condition["id"],
                "task_scope": condition["task_scope"],
                "profile_id": condition["profile_id"],
                "worker_count": condition["worker_count"],
                "output_scope": condition["output_scope"],
                "tool_id": tool["id"],
                "tool_version": tool["version"],
                "tool_sha256": tool["sha256"],
                "target_id": target["id"],
                "target_sha256": target["sha256"],
                "target_size_bytes": target["size_bytes"],
                "target_license": target["license"],
                "command_json": json.dumps(recorded_argv, separators=(",", ":")),
                "command_cwd": str(run_workdir.relative_to(stage)),
                "stdout_path": str(stdout_path.relative_to(stage)),
                "stderr_path": str(stderr_path.relative_to(stage)),
                **result,
                "throughput_mib_s": throughput,
                "outcome": outcome,
                "timer_floor_ns": reliable_floor,
                "timing_class": timing_class,
                "batch_size": 1,
                "extractor": condition["extractor"],
                **extracted,
                "error": error,
            }
            rows.append(row)
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=ROW_FIELDS, delimiter="\t", lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: render_row_value(row.get(field)) for field in ROW_FIELDS})
    data = buffer.getvalue().encode("utf-8")
    parent_fd = open_directory_nofollow(path.parent, f"rows parent {path.parent}")
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(path.name, flags, 0o600, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise RunnerError(f"refusing pre-existing rows artifact: {path}") from exc
        try:
            write_all(fd, data)
            os.fchmod(fd, 0o444)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def require_campaign_artifact_identities(
    *,
    stage: Path,
    tools: dict[str, dict[str, Any]],
    timer_floor: dict[str, Any],
    rows: list[dict[str, Any]],
) -> None:
    for tool_id, tool in tools.items():
        version = tool["version_result"]
        for stream in ("stdout", "stderr"):
            require_artifact_identity(
                stage / tool[f"version_{stream}_path"],
                expected_size=version[f"{stream}_bytes"],
                expected_sha256=version[f"{stream}_sha256"],
                label=f"tool {tool_id} version {stream}",
            )

    for sample in timer_floor["samples"]:
        for stream in ("stdout", "stderr"):
            require_artifact_identity(
                stage / sample[f"{stream}_path"],
                expected_size=sample[f"{stream}_bytes"],
                expected_sha256=sample[f"{stream}_sha256"],
                label=f"timer floor sample {sample['run']} {stream}",
            )

    encoded_timer_floor = (
        json.dumps(timer_floor, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    require_artifact_identity(
        stage / "timer-floor.json",
        expected_size=len(encoded_timer_floor),
        expected_sha256=sha256_bytes(encoded_timer_floor),
        label="timer floor artifact",
    )

    for row in rows:
        for stream in ("stdout", "stderr"):
            require_artifact_identity(
                stage / row[f"{stream}_path"],
                expected_size=row[f"{stream}_bytes"],
                expected_sha256=row[f"{stream}_sha256"],
                label=f"row {row['run_id']} {stream}",
            )


def strip_runtime_paths(value: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for key in sorted(value):
        record = dict(value[key])
        record.pop("snapshot_absolute", None)
        record.pop("execution_absolute", None)
        record.pop("execution_fd", None)
        output.append(record)
    return output


def build_manifest(
    *,
    spec: dict[str, Any],
    spec_path: Path,
    spec_record: dict[str, Any],
    runner_record: dict[str, Any],
    stage: Path,
    tools: dict[str, dict[str, Any]],
    targets: dict[str, dict[str, Any]],
    probe: dict[str, Any],
    timer_floor: dict[str, Any],
    rows: list[dict[str, Any]],
    environment: dict[str, Any],
) -> dict[str, Any]:
    rows_path = stage / "rows.tsv"
    failures = sum(row["outcome"] != "success" for row in rows)
    measured = sum(row["phase"] == "measured" for row in rows)
    warmups = sum(row["phase"] == "warmup" for row in rows)
    primary = sum(row["included_in_primary_summary"] is True for row in rows)
    probe_record = dict(probe)
    probe_record.pop("snapshot_absolute", None)
    probe_record.pop("execution_absolute", None)
    probe_record.pop("execution_fd", None)
    return {
        "schema_version": RUNNER_SCHEMA_VERSION,
        "campaign_id": spec["campaign_id"],
        "created_utc": utc_now(),
        "evidence_class": EVIDENCE_CLASS,
        "frozen": False,
        "publication_eligible": PUBLICATION_ELIGIBLE,
        "claim_boundary": "development diagnostic evidence only; not preview or publication evidence",
        "runner": {
            **runner_record,
            "python_standard_library_only": True,
            "measurement_api": "time.monotonic_ns + os.wait4",
            "resource_scope": WAIT4_RESOURCE_SCOPE,
            "process_isolation": "new session/process group per run",
            "execution_input_protection": (
                "write-sealed Linux memfd copies bound to the retained tool, target, "
                "and timer-probe snapshot hashes"
            ),
            "transactional_publication": True,
        },
        "spec": {
            **spec_record,
            "source_path": str(spec_path),
            "normalized": spec,
        },
        "policies": {
            "warmup_runs": spec["warmup_runs"],
            "measured_runs": spec["measured_runs"],
            "timeout_seconds": spec["timeout_seconds"],
            "capture_limits": spec["capture_limits"],
            "output_limit_outcome": "output_limit",
            "order_policy": spec["order_policy"],
            "cache_policy": spec["cache_policy"],
            "failed_rows_retained": True,
            "fail_campaign_on_error": spec["fail_campaign_on_error"],
            "retained_artifact_identity_reconciliation": (
                "version, timer-floor, stdout, and stderr bytes are rechecked after the final measured child exits"
            ),
            "child_environment": "fixed C/UTC/PATH plus per-command HOME, TMPDIR, and XDG roots",
            "reserved_environment_keys": sorted(RESERVED_ENVIRONMENT_KEYS),
            "timer_floor_interpretation": "single-process results below the recorded floor require a larger target or future reviewed batching",
        },
        "environment": environment,
        "tools": strip_runtime_paths(tools),
        "targets": strip_runtime_paths(targets),
        "timer_floor_probe": probe_record,
        "timer_floor": {
            key: value for key, value in timer_floor.items() if key != "samples"
        },
        "artifacts": {
            "rows": "rows.tsv",
            "rows_sha256": sha256_file(rows_path),
            "timer_floor": "timer-floor.json",
            "timer_floor_sha256": sha256_file(stage / "timer-floor.json"),
            "outputs_directory": "outputs",
        },
        "outcomes": {
            "row_count": len(rows),
            "warmup_row_count": warmups,
            "measured_row_count": measured,
            "failure_row_count": failures,
            "primary_summary_row_count": primary,
            "all_processes_successful": failures == 0,
        },
    }


def run_campaign(spec_path: Path, output_root: Path, campaign_override: str | None) -> tuple[Path, int]:
    global CREATING_STAGE
    spec_path = spec_path.resolve(strict=True)
    spec, spec_raw, spec_source_identity = parse_spec(spec_path, campaign_override)
    runner_source = Path(__file__).resolve(strict=True)
    runner_source_identity = file_identity(runner_source)
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    output_root = output_root.resolve(strict=True)
    final = output_root / spec["campaign_id"]
    require(not final.exists(), f"campaign result already exists: {final}")
    stage_name = f".{spec['campaign_id']}.staging-{uuid.uuid4().hex}"
    owned_stage: OwnedStage | None = None
    stage_registry: list[OwnedStage] = []
    tools: dict[str, dict[str, Any]] = {}
    targets: dict[str, dict[str, Any]] = {}
    probe: dict[str, Any] | None = None
    manifest: dict[str, Any] | None = None
    exit_code = 0

    try:
        CREATING_STAGE = True
        try:
            previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
            try:
                owned_stage = OwnedStage.create(output_root, stage_name, stage_registry)
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        finally:
            CREATING_STAGE = False
        if INTERRUPTED_BY is not None:
            raise RunnerInterrupted(f"interrupted by {signal.Signals(INTERRUPTED_BY).name}")
        stage = owned_stage.authoritative_path
        spec_snapshot = stage / "inputs" / "spec" / "campaign.json"
        spec_snapshot.parent.mkdir(parents=True, exist_ok=True)
        spec_snapshot.write_bytes(spec_raw)
        os.chmod(spec_snapshot, 0o444)
        require(sha256_file(spec_snapshot) == spec_source_identity["sha256"], "campaign spec snapshot mismatch")
        spec_record = {
            **spec_source_identity,
            "snapshot_path": str(spec_snapshot.relative_to(stage)),
        }

        runner_snapshot = stage / "inputs" / "runner" / "diagnostic-runner.py"
        runner_snapshot_identity = immutable_snapshot(runner_source, runner_snapshot, executable=True)
        require(runner_snapshot_identity["sha256"] == runner_source_identity["sha256"], "runner source changed before snapshot")
        runner_record = {
            **runner_snapshot_identity,
            "source_path": str(runner_source),
            "snapshot_path": str(runner_snapshot.relative_to(stage)),
        }

        subreaper_enabled = enable_subreaper()
        require(not direct_child_pids(), "runner started with unrelated child processes")
        environment = command_environment(spec.get("environment", {}))
        tools, targets, probe = snapshot_inputs(spec, spec_path.parent, stage, environment)
        assert probe is not None
        require_campaign_snapshot_identities(
            spec_snapshot=spec_snapshot,
            spec_record=spec_record,
            runner_snapshot=runner_snapshot,
            runner_record=runner_record,
            tools=tools,
            targets=targets,
            probe=probe,
        )
        floor = timer_floor_campaign(spec, stage, probe, environment)
        require_campaign_snapshot_identities(
            spec_snapshot=spec_snapshot,
            spec_record=spec_record,
            runner_snapshot=runner_snapshot,
            runner_record=runner_record,
            tools=tools,
            targets=targets,
            probe=probe,
        )
        rows = run_conditions(spec, stage, tools, targets, floor, environment)
        write_rows(stage / "rows.tsv", rows)
        require_campaign_artifact_identities(stage=stage, tools=tools, timer_floor=floor, rows=rows)
        require_campaign_snapshot_identities(
            spec_snapshot=spec_snapshot,
            spec_record=spec_record,
            runner_snapshot=runner_snapshot,
            runner_record=runner_record,
            tools=tools,
            targets=targets,
            probe=probe,
        )
        require(file_identity(spec_path)["sha256"] == spec_source_identity["sha256"], "campaign spec changed during execution")
        require(file_identity(runner_source)["sha256"] == runner_source_identity["sha256"], "diagnostic runner source changed during execution")
        manifest = build_manifest(
            spec=spec,
            spec_path=spec_path,
            spec_record=spec_record,
            runner_record=runner_record,
            stage=stage,
            tools=tools,
            targets=targets,
            probe=probe,
            timer_floor=floor,
            rows=rows,
            environment=environment_manifest(subreaper_enabled),
        )
        write_json(stage / "manifest.json", manifest)
        fsync_tree(stage)
        failures = manifest["outcomes"]["failure_row_count"]
        exit_code = 1 if failures and spec["fail_campaign_on_error"] else 0
        _publish_owned_stage(owned_stage, final, "diagnostic campaign staging tree")
        return final, exit_code
    except BaseException as failure:
        if owned_stage is None and stage_registry:
            # Preserve creation-time ownership when a pending signal is raised
            # at the create() return boundary before the local assignment.
            owned_stage = stage_registry[-1]
        if owned_stage is not None and owned_stage.committed:
            # A signal delivered immediately after the authenticated rename may
            # report the already-complete result. Durability or integrity errors
            # after rename remain failures even though the committed tree is
            # preserved for explicit verification.
            if isinstance(failure, RunnerInterrupted):
                return final, exit_code
            raise
        cleanup_failure: BaseException | None = None
        if owned_stage is not None:
            try:
                owned_stage.cleanup("diagnostic campaign staging tree")
            except BaseException as exc:
                cleanup_failure = exc
        if cleanup_failure is not None:
            raise RunnerError(
                f"campaign failed with {type(failure).__name__}; staging cleanup also failed: {cleanup_failure}"
            ) from failure
        raise
    finally:
        CREATING_STAGE = False
        close_execution_inputs(tools, targets, probe)
        if owned_stage is None and stage_registry:
            owned_stage = stage_registry[-1]
        if owned_stage is not None:
            owned_stage.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Sprint 11 diagnostic benchmark campaign")
    parser.add_argument("--platform-check", action="store_true", help="check required Linux runner facilities and exit")
    parser.add_argument("--spec", type=Path, help="diagnostic campaign JSON specification")
    parser.add_argument("--output-root", type=Path, help="directory that receives the campaign tree")
    parser.add_argument("--campaign-id", help="safe unique campaign identifier override")
    args = parser.parse_args(argv)
    if args.platform_check:
        if args.spec is not None or args.output_root is not None or args.campaign_id is not None:
            parser.error("--platform-check cannot be combined with campaign arguments")
    elif args.spec is None or args.output_root is None:
        parser.error("--spec and --output-root are required for a campaign")
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.platform_check:
        try:
            creation_mode = diagnostic_platform_preflight()
        except (OSError, RunnerError, ValueError, subprocess.SubprocessError) as exc:
            print(f"diagnostic-runner-platform-check: error: {exc}", file=sys.stderr)
            return 2
        print(f"diagnostic-runner-platform-check: ok memfd={creation_mode} write_seals=4 noexec_seal=1")
        return 0
    install_signal_handlers()
    try:
        final, exit_code = run_campaign(args.spec, args.output_root, args.campaign_id)
    except RunnerInterrupted as exc:
        ignore_campaign_signals()
        print(f"diagnostic-runner: interrupted: {exc}", file=sys.stderr)
        return 128 + (INTERRUPTED_BY or signal.SIGINT)
    except (OSError, RunnerError, ValueError) as exc:
        print(f"diagnostic-runner: error: {exc}", file=sys.stderr)
        return 2
    print(f"diagnostic-runner: complete result={final} exit={exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
