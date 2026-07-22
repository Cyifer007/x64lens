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
from datetime import datetime, timezone
import errno
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import signal
import statistics
import stat
import subprocess
import sys
import time
from typing import Any, Iterable
import uuid

RUNNER_SCHEMA_VERSION = 1
EVIDENCE_CLASS = "diagnostic"
PUBLICATION_ELIGIBLE = False
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RunnerError(message)


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
    """Delete an exact same-parent staging tree and verify complete removal."""
    parent = expected_parent.resolve(strict=True)
    candidate = Path(os.path.abspath(path))
    require(candidate.parent == parent, f"{label} is outside its expected parent")
    metadata = os.lstat(candidate)
    require(stat.S_ISDIR(metadata.st_mode), f"{label} is not a real directory")
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0))
    try:
        os.chmod(candidate.name, 0o700, dir_fd=parent_fd, follow_symlinks=False)
        directory_fd = os.open(
            candidate.name,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        try:
            observed = os.fstat(directory_fd)
            require(
                (observed.st_dev, observed.st_ino) == (metadata.st_dev, metadata.st_ino),
                f"{label} changed before cleanup",
            )
            _clear_directory_fd(directory_fd, label, metadata.st_dev)
        finally:
            os.close(directory_fd)
        os.rmdir(candidate.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    require(not os.path.lexists(candidate), f"{label} survived cleanup")


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


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o444)
    os.replace(temporary, path)


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
            os.fsync(fd)
        finally:
            os.close(fd)
    fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow | cloexec)
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
    INTERRUPTED_BY = signum
    if ACTIVE_PROCESS_GROUP is not None:
        try:
            os.killpg(ACTIVE_PROCESS_GROUP, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            pass
    elif SPAWNING_PROCESS:
        return
    raise RunnerInterrupted(f"interrupted by {signal.Signals(signum).name}")


def install_signal_handlers() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def direct_child_pids() -> set[int]:
    """Return children currently parented to this Linux subreaper."""
    path = Path(f"/proc/self/task/{os.getpid()}/children")
    try:
        text = path.read_text(encoding="ascii").strip()
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


def execute_process(
    argv: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout_seconds: float,
    environment: dict[str, str],
    pass_fds: tuple[int, ...] = (),
) -> dict[str, Any]:
    global ACTIVE_PROCESS_GROUP, SPAWNING_PROCESS
    require(argv and Path(argv[0]).is_absolute(), "measured executable path must be absolute")
    cwd.mkdir(parents=True, exist_ok=True)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    require(not direct_child_pids(), "runner has unrelated child processes before measurement")
    start_ns = time.monotonic_ns()
    with (
        open(os.devnull, "rb") as stdin_handle,
        stdout_path.open("wb") as stdout_handle,
        stderr_path.open("wb") as stderr_handle,
    ):
        process: subprocess.Popen[bytes] | None = None
        pid: int | None = None
        SPAWNING_PROCESS = True
        try:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=cwd,
                    stdin=stdin_handle,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    env=environment,
                    close_fds=True,
                    pass_fds=pass_fds,
                    start_new_session=True,
                )
            except OSError as exc:
                raise RunnerError(f"cannot start measured command {argv[0]}: {exc}") from exc

            pid = process.pid
            ACTIVE_PROCESS_GROUP = pid
            SPAWNING_PROCESS = False
            if INTERRUPTED_BY is not None:
                raise RunnerInterrupted(f"interrupted by {signal.Signals(INTERRUPTED_BY).name}")
            status, usage, timed_out = wait_for_process(pid, timeout_seconds)
            end_ns = time.monotonic_ns()
            group_cleanup_required, group_descendants_reaped = cleanup_process_group(pid)
            adopted_cleanup_required, adopted_descendants_reaped = cleanup_adopted_descendants()
            cleanup_required = group_cleanup_required or adopted_cleanup_required
            descendants_reaped = group_descendants_reaped + adopted_descendants_reaped
        except BaseException:
            SPAWNING_PROCESS = False
            if pid is not None:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except OSError:
                    pass
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

        assert process is not None
        process.returncode = os.waitstatus_to_exitcode(status)
        stdout_identity = capture_open_artifact_identity(stdout_handle, stdout_path, "measured stdout")
        stderr_identity = capture_open_artifact_identity(stderr_handle, stderr_path, "measured stderr")

    exit_code: int | None = None
    signal_number: int | None = None
    if os.WIFEXITED(status):
        exit_code = os.WEXITSTATUS(status)
    elif os.WIFSIGNALED(status):
        signal_number = os.WTERMSIG(status)

    if timed_out:
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


def isolated_child_environment(base: dict[str, str], workdir: Path) -> dict[str, str]:
    """Create per-command home, cache, config, data, and temporary roots."""
    environment_root = workdir / "environment"
    paths = {
        "HOME": environment_root / "home",
        "TMPDIR": environment_root / "tmp",
        "XDG_CACHE_HOME": environment_root / "cache",
        "XDG_CONFIG_HOME": environment_root / "config",
        "XDG_DATA_HOME": environment_root / "data",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    environment = dict(base)
    environment.update({key: str(path) for key, path in paths.items()})
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

        for tool_id, tool in tools.items():
            version_dir = stage / "inputs" / "versions" / tool_id
            version_workdir = version_dir / "work"
            require_snapshot_identity(tool["snapshot_absolute"], tool, f"tool {tool_id}", 0o555)
            require_execution_identity(tool, f"tool {tool_id}", 0o555)
            result = execute_process(
                expand_argv(tool["version_argv"], tool["execution_absolute"]),
                cwd=version_workdir,
                stdout_path=version_dir / "stdout.bin",
                stderr_path=version_dir / "stderr.bin",
                timeout_seconds=min(5.0, spec["timeout_seconds"]),
                environment=isolated_child_environment(environment, version_workdir),
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
    for index in range(1, spec["timer_floor"]["runs"] + 1):
        sample_dir = stage / "timer-floor" / f"probe-{index:03d}"
        require_snapshot_identity(probe["snapshot_absolute"], probe, "timer floor probe", 0o555)
        require_execution_identity(probe, "timer floor probe", 0o555)
        result = execute_process(
            [str(probe["execution_absolute"])],
            cwd=sample_dir / "work",
            stdout_path=sample_dir / "stdout.bin",
            stderr_path=sample_dir / "stderr.bin",
            timeout_seconds=min(5.0, spec["timeout_seconds"]),
            environment=isolated_child_environment(environment, sample_dir / "work"),
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
        "schema_version": 1,
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
    phases = (("warmup", spec["warmup_runs"]), ("measured", spec["measured_runs"]))
    reliable_floor = timer_floor["reliable_single_process_floor_ns"]
    for phase, rounds in phases:
        for round_number, order_index, condition in schedule_conditions(spec["conditions"], rounds, spec["order_policy"]):
            tool = tools[condition["tool"]]
            target = targets[condition["target"]]
            run_id = f"{phase}-{round_number:03d}-{order_index:02d}-{condition['id']}"
            run_dir = stage / "outputs" / run_id
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
                environment=isolated_child_environment(environment, run_workdir),
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
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ROW_FIELDS, delimiter="\t", lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: render_row_value(row.get(field)) for field in ROW_FIELDS})


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
    spec_path = spec_path.resolve(strict=True)
    spec, spec_raw, spec_source_identity = parse_spec(spec_path, campaign_override)
    runner_source = Path(__file__).resolve(strict=True)
    runner_source_identity = file_identity(runner_source)
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    final = output_root / spec["campaign_id"]
    require(not final.exists(), f"campaign result already exists: {final}")
    stage = output_root / f".{spec['campaign_id']}.staging-{uuid.uuid4().hex}"
    require(not stage.exists(), f"staging path already exists: {stage}")
    tools: dict[str, dict[str, Any]] = {}
    targets: dict[str, dict[str, Any]] = {}
    probe: dict[str, Any] | None = None

    try:
        stage.mkdir(mode=0o700)
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
        require_campaign_artifact_identities(
            stage=stage,
            tools=tools,
            timer_floor=floor,
            rows=rows,
        )
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
        atomic_publish_noreplace(stage, final)
        failures = manifest["outcomes"]["failure_row_count"]
        exit_code = 1 if failures and spec["fail_campaign_on_error"] else 0
        return final, exit_code
    except BaseException as failure:
        cleanup_failure: BaseException | None = None
        if os.path.lexists(stage):
            try:
                remove_staging_tree(stage, output_root, "diagnostic campaign staging tree")
            except BaseException as exc:
                cleanup_failure = exc
        if cleanup_failure is not None:
            raise RunnerError(
                f"campaign failed with {type(failure).__name__}; staging cleanup also failed: {cleanup_failure}"
            ) from failure
        raise
    finally:
        close_execution_inputs(tools, targets, probe)


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
        print(f"diagnostic-runner: interrupted: {exc}", file=sys.stderr)
        return 128 + (INTERRUPTED_BY or signal.SIGINT)
    except (OSError, RunnerError, ValueError) as exc:
        print(f"diagnostic-runner: error: {exc}", file=sys.stderr)
        return 2
    print(f"diagnostic-runner: complete result={final} exit={exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
