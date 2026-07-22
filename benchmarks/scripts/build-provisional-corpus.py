#!/usr/bin/env python3
"""Build and verify the Sprint 11 provisional diagnostic ELF corpus.

This development-only standard-library tool materializes a project-authored C
source across a bounded GCC/Clang matrix. It records exact tool identity, build
arguments, source and license snapshots, output hashes, and bounded ELF facts.
Targets are never executed. A completed corpus is published transactionally with
Linux renameat2(RENAME_NOREPLACE); an existing corpus is never replaced.
"""
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import pathlib
import platform
import re
import selectors
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

EXIT_ERROR = 2
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
SAFE_ENV = re.compile(r"^[A-Z_][A-Z0-9_]*$")
RESERVED_ENV = {
    "PATH", "HOME", "TMPDIR", "PYTHONPATH", "PYTHONHOME", "LD_PRELOAD",
    "LD_LIBRARY_PATH", "GCC_EXEC_PREFIX", "COMPILER_PATH", "LIBRARY_PATH",
}
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
RENAME_NOREPLACE = 1
AT_FDCWD = -100
FIXED_MTIME = 0
TARGET_MODE = 0o444
INPUT_MODE = 0o444
SCRIPT_MODE = 0o555
TEXT_MODE = 0o444
DIRECTORY_MODE = 0o755
ELF_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
PROGRAM_HEADER = struct.Struct("<IIQQQQQQ")
NOTE_HEADER = struct.Struct("<III")
GNU_PROPERTY_HEADER = struct.Struct("<II")
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
PT_NOTE = 4
PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552
PF_X = 1
PF_W = 2
ET_EXEC = 2
ET_DYN = 3
EM_X86_64 = 62
NT_GNU_PROPERTY_TYPE_0 = 5
GNU_PROPERTY_X86_FEATURE_1_AND = 0xC0000002
GNU_PROPERTY_X86_FEATURE_1_IBT = 1
GNU_PROPERTY_X86_FEATURE_1_SHSTK = 2
MAX_PROFILE_ITEMS = 16
MAX_TARGETS = 256
MAX_FLAGS = 128
MAX_FLAG_BYTES = 4096
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
SIGNALS = {signal.SIGINT, signal.SIGTERM}
COMMAND_FIELDS = (
    "target_id", "compiler_id", "linker_id", "optimization_id", "artifact_id", "hardening_id",
    "cwd", "argv_json", "exit_code", "stdout_path", "stdout_sha256",
    "stderr_path", "stderr_sha256", "output_path", "output_sha256",
)
CANONICAL_DETERMINISM_FLAGS = (
    "-fdebug-prefix-map={stage}=/x64lens/provisional-corpus",
    "-ffile-prefix-map={stage}=/x64lens/provisional-corpus",
    "-fmacro-prefix-map={stage}=/x64lens/provisional-corpus",
)
CANONICAL_LINKER_SEARCH_FLAG = "-B{linker_directory}/"


class CorpusError(RuntimeError):
    """Raised for invalid corpus input, build failure, or integrity failure."""


class CorpusInterrupted(CorpusError):
    """Raised when SIGINT or SIGTERM interrupts corpus construction."""

    def __init__(self, signum: int) -> None:
        super().__init__(f"interrupted by signal {signum}")
        self.signum = signum


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: bytes
    stderr: bytes


_ACTIVE_PROCESS: subprocess.Popen[bytes] | None = None
_SPAWNING_PROCESS = False
_INTERRUPTED_BY: int | None = None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CorpusError(message)


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


def remove_owned_tree(path: pathlib.Path, expected_parent: pathlib.Path, label: str) -> None:
    """Delete an exact same-parent tree and verify complete removal."""
    parent = expected_parent.resolve(strict=True)
    candidate = pathlib.Path(os.path.abspath(path))
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


def require_workspace_members(workspace: pathlib.Path, allowed_file: pathlib.Path | None = None) -> None:
    """Reject every compiler-created member except one named output file."""
    expected = set() if allowed_file is None else {allowed_file.name}
    observed: set[str] = set()
    with os.scandir(workspace) as entries:
        for entry in entries:
            observed.add(entry.name)
            metadata = entry.stat(follow_symlinks=False)
            if allowed_file is not None and entry.name == allowed_file.name:
                require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1, "compiler output is not one regular file")
            else:
                raise CorpusError(f"compiler created an undeclared workspace member: {entry.name}")
    require(observed == expected, "compiler workspace membership changed")


def exact_member_sets(root: pathlib.Path) -> tuple[set[str], set[str]]:
    files: set[str] = set()
    directories: set[str] = set()
    for path in root.rglob("*"):
        metadata = path.lstat()
        relative = path.relative_to(root).as_posix()
        if stat.S_ISDIR(metadata.st_mode):
            directories.add(relative)
        else:
            require(stat.S_ISREG(metadata.st_mode), f"corpus contains a non-regular member: {relative}")
            files.add(relative)
    return files, directories


def expected_directories(files: set[str], explicit: set[str] | None = None) -> set[str]:
    directories = set(explicit or set())
    for name in files:
        parent = pathlib.PurePosixPath(name).parent
        while parent != pathlib.PurePosixPath("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return directories


def require_exact_members(root: pathlib.Path, expected_files: set[str], explicit_directories: set[str] | None = None) -> None:
    observed_files, observed_directories = exact_member_sets(root)
    expected_dirs = expected_directories(expected_files, explicit_directories)
    require(
        observed_files == expected_files,
        f"corpus file membership changed: missing={sorted(expected_files - observed_files)} extra={sorted(observed_files - expected_files)}",
    )
    require(
        observed_directories == expected_dirs,
        f"corpus directory membership changed: missing={sorted(expected_dirs - observed_directories)} extra={sorted(observed_directories - expected_dirs)}",
    )


def safe_id(value: Any, name: str) -> str:
    require(isinstance(value, str) and SAFE_ID.fullmatch(value) is not None, f"{name} must be a safe identifier")
    return value


def require_bool(value: Any, name: str) -> bool:
    require(type(value) is bool, f"{name} must be a boolean")
    return value


def require_int(value: Any, name: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    require(type(value) is int and value >= minimum, f"{name} must be an integer >= {minimum}")
    if maximum is not None:
        require(value <= maximum, f"{name} must be <= {maximum}")
    return value


def require_sha256(value: Any, name: str) -> str:
    require(isinstance(value, str) and HEX_SHA256.fullmatch(value) is not None, f"{name} must be a lowercase SHA-256 digest")
    return value


def require_string(value: Any, name: str, *, nonempty: bool = True) -> str:
    require(isinstance(value, str) and "\x00" not in value, f"{name} must be a string without NUL")
    if nonempty:
        require(bool(value), f"{name} must be nonempty")
    return value


def require_flags(value: Any, name: str) -> list[str]:
    require(isinstance(value, list), f"{name} must be an array")
    require(len(value) <= MAX_FLAGS, f"{name} contains too many flags")
    flags: list[str] = []
    total = 0
    for index, raw in enumerate(value):
        flag = require_string(raw, f"{name}[{index}]")
        require("\n" not in flag and "\r" not in flag, f"{name}[{index}] contains a line break")
        total += len(flag.encode("utf-8"))
        require(total <= MAX_FLAG_BYTES, f"{name} is too large")
        flags.append(flag)
    return flags


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def file_identity(path: pathlib.Path) -> dict[str, Any]:
    metadata = path.stat(follow_symlinks=False)
    require(stat.S_ISREG(metadata.st_mode), f"not a regular file: {path}")
    return {
        "size_bytes": metadata.st_size,
        "sha256": sha256_file(path),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        "mtime_ns": metadata.st_mtime_ns,
    }


def write_bytes(path: pathlib.Path, data: bytes, mode: int = TEXT_MODE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, mode)
    os.utime(path, (FIXED_MTIME, FIXED_MTIME), follow_symlinks=False)


def write_text(path: pathlib.Path, text: str, mode: int = TEXT_MODE) -> None:
    write_bytes(path, text.encode("utf-8"), mode)


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def within(root: pathlib.Path, candidate: pathlib.Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_repository_input(repo_root: pathlib.Path, spec_dir: pathlib.Path, raw: Any, name: str) -> pathlib.Path:
    value = require_string(raw, name)
    unresolved = pathlib.Path(value)
    path = unresolved if unresolved.is_absolute() else spec_dir / unresolved
    path = path.resolve(strict=True)
    require(within(repo_root, path), f"{name} resolves outside the repository")
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode), f"{name} is not a regular file")
    return path


def repository_relative(repo_root: pathlib.Path, path: pathlib.Path) -> str:
    return path.resolve(strict=True).relative_to(repo_root).as_posix()


def resolve_tool(command: str, name: str) -> pathlib.Path:
    require_string(command, name)
    found = shutil.which(command)
    require(found is not None, f"required tool is missing: {command}")
    path = pathlib.Path(found).resolve(strict=True)
    metadata = path.stat()
    require(stat.S_ISREG(metadata.st_mode), f"tool is not a regular file: {path}")
    require(os.access(path, os.X_OK), f"tool is not executable: {path}")
    return path


def signal_handler(signum: int, _frame: Any) -> None:
    global _INTERRUPTED_BY
    _INTERRUPTED_BY = signum
    if _ACTIVE_PROCESS is not None:
        try:
            os.killpg(_ACTIVE_PROCESS.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        return
    if _SPAWNING_PROCESS:
        return
    raise CorpusInterrupted(signum)


def install_signal_handlers() -> None:
    for signum in SIGNALS:
        signal.signal(signum, signal_handler)


def enable_subreaper() -> None:
    require(sys.platform.startswith("linux"), "provisional corpus builder requires Linux")
    children_path = pathlib.Path(f"/proc/self/task/{os.getpid()}/children")
    require(children_path.is_file(), "Linux /proc child enumeration is required")
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    prctl.restype = ctypes.c_int
    if prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        code = ctypes.get_errno()
        raise CorpusError(f"cannot enable Linux child subreaper: {os.strerror(code)}")


def process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def direct_child_pids() -> set[int]:
    path = pathlib.Path(f"/proc/self/task/{os.getpid()}/children")
    try:
        text = path.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise CorpusError(f"cannot inspect Linux child process state: {exc}") from exc
    if not text:
        return set()
    try:
        return {int(value) for value in text.split()}
    except ValueError as exc:
        raise CorpusError(f"invalid Linux child process state: {text!r}") from exc


def reap_any_children() -> int:
    reaped = 0
    while True:
        try:
            waited, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            break
        except InterruptedError:
            continue
        if waited <= 0:
            break
        reaped += 1
    return reaped


def cleanup_process_group_members(pgid: int) -> bool:
    if not process_group_exists(pgid):
        return False
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    deadline = time.monotonic() + 0.15
    while time.monotonic() < deadline and process_group_exists(pgid):
        reap_any_children()
        time.sleep(0.005)
    if process_group_exists(pgid):
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and process_group_exists(pgid):
        reap_any_children()
        time.sleep(0.005)
    require(not process_group_exists(pgid), f"build process group {pgid} survived cleanup")
    return True


def cleanup_adopted_descendants() -> bool:
    children = direct_child_pids()
    if not children:
        return False
    for child in children:
        try:
            os.kill(child, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 0.15
    while time.monotonic() < deadline:
        reap_any_children()
        children = direct_child_pids()
        if not children:
            return True
        time.sleep(0.005)
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        children = direct_child_pids()
        for child in children:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
        reap_any_children()
        if not direct_child_pids():
            return True
        time.sleep(0.005)
    raise CorpusError(f"adopted compiler descendants survived cleanup: {sorted(direct_child_pids())}")


def terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=0.15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2.0)
        except subprocess.TimeoutExpired as exc:
            raise CorpusError(f"unable to reap build process {process.pid}") from exc
    cleanup_process_group_members(process.pid)
    cleanup_adopted_descendants()


def capture_bounded_process_output(
    process: subprocess.Popen[bytes],
    timeout_seconds: int,
    maximum_capture_bytes: int,
) -> tuple[bytes, bytes]:
    require(process.stdout is not None and process.stderr is not None, "compiler capture pipes are missing")
    stdout_fd = process.stdout.fileno()
    stderr_fd = process.stderr.fileno()
    streams = {
        stdout_fd: ("command stdout", process.stdout, bytearray()),
        stderr_fd: ("command stderr", process.stderr, bytearray()),
    }
    selector = selectors.DefaultSelector()
    cleanup_after_root_exit = False
    deadline = time.monotonic() + timeout_seconds
    try:
        for descriptor, (_label, stream, _buffer) in streams.items():
            os.set_blocking(descriptor, False)
            selector.register(stream, selectors.EVENT_READ, descriptor)
        while selector.get_map():
            if _INTERRUPTED_BY is not None:
                terminate_process_tree(process)
                raise CorpusInterrupted(_INTERRUPTED_BY)
            if process.poll() is not None and not cleanup_after_root_exit:
                cleanup_process_group_members(process.pid)
                cleanup_adopted_descendants()
                cleanup_after_root_exit = True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                terminate_process_tree(process)
                raise CorpusError(f"command timed out after {timeout_seconds}s: {process.args[0]}")
            for key, _events in selector.select(min(0.05, remaining)):
                descriptor = key.data
                label, stream, buffer = streams[descriptor]
                try:
                    chunk = os.read(descriptor, min(65536, maximum_capture_bytes + 1 - len(buffer)))
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(stream)
                    stream.close()
                    continue
                buffer.extend(chunk)
                if len(buffer) > maximum_capture_bytes:
                    terminate_process_tree(process)
                    raise CorpusError(f"{label} exceeded the {maximum_capture_bytes}-byte capture limit")

        if process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                terminate_process_tree(process)
                raise CorpusError(f"command timed out after {timeout_seconds}s: {process.args[0]}")
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                terminate_process_tree(process)
                raise CorpusError(f"command timed out after {timeout_seconds}s: {process.args[0]}") from exc
        if not cleanup_after_root_exit:
            cleanup_process_group_members(process.pid)
            cleanup_adopted_descendants()
        return bytes(streams[stdout_fd][2]), bytes(streams[stderr_fd][2])
    finally:
        selector.close()
        for _label, stream, _buffer in streams.values():
            if not stream.closed:
                stream.close()


def run_command(
    argv: Sequence[str],
    cwd: pathlib.Path,
    environment: dict[str, str],
    timeout_seconds: int,
    maximum_capture_bytes: int,
) -> CommandResult:
    global _ACTIVE_PROCESS, _SPAWNING_PROCESS
    require(argv, "empty command")
    require(not direct_child_pids(), "corpus builder has unrelated child processes before command launch")
    blocked = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
    process: subprocess.Popen[bytes] | None = None
    spawn_error: BaseException | None = None
    _SPAWNING_PROCESS = True
    try:
        try:
            process = subprocess.Popen(
                list(argv),
                cwd=cwd,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            _ACTIVE_PROCESS = process
        except BaseException as exc:
            spawn_error = exc
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, blocked)
        _SPAWNING_PROCESS = False

    if spawn_error is not None:
        if _INTERRUPTED_BY is not None:
            raise CorpusInterrupted(_INTERRUPTED_BY)
        raise spawn_error
    require(process is not None, "process spawn failed without an exception")
    if _INTERRUPTED_BY is not None:
        terminate_process_tree(process)
        _ACTIVE_PROCESS = None
        raise CorpusInterrupted(_INTERRUPTED_BY)
    try:
        stdout, stderr = capture_bounded_process_output(process, timeout_seconds, maximum_capture_bytes)
        if _INTERRUPTED_BY is not None:
            raise CorpusInterrupted(_INTERRUPTED_BY)
        return CommandResult(tuple(argv), process.returncode, stdout, stderr)
    finally:
        _ACTIVE_PROCESS = None


def fixed_environment(extra: dict[str, str], tools: Iterable[pathlib.Path]) -> dict[str, str]:
    path_entries: list[str] = []
    for tool in tools:
        parent = str(tool.parent)
        if parent not in path_entries:
            path_entries.append(parent)
    for fallback in ("/usr/local/bin", "/usr/bin", "/bin"):
        if pathlib.Path(fallback).is_dir() and fallback not in path_entries:
            path_entries.append(fallback)
    environment = {
        "PATH": os.pathsep.join(path_entries),
        "HOME": "/nonexistent",
        "TMPDIR": "/tmp",
    }
    environment.update(extra)
    return environment


def align_up(value: int, alignment: int) -> int:
    require(alignment > 0 and (alignment & (alignment - 1)) == 0, "invalid alignment")
    return (value + alignment - 1) & ~(alignment - 1)


def checked_range(offset: int, size: int, total: int, label: str) -> tuple[int, int]:
    require(offset >= 0 and size >= 0 and offset <= total and size <= total - offset, f"{label} extends outside the ELF file")
    return offset, offset + size


def parse_gnu_properties(data: bytes, offset: int, size: int) -> tuple[bool, bool, bool]:
    start, end = checked_range(offset, size, len(data), "PT_NOTE")
    cursor = start
    property_note = False
    ibt = False
    shstk = False
    while cursor < end:
        remaining = end - cursor
        if remaining < NOTE_HEADER.size:
            require(all(byte == 0 for byte in data[cursor:end]), "trailing nonzero PT_NOTE bytes")
            break
        namesz, descsz, note_type = NOTE_HEADER.unpack_from(data, cursor)
        cursor += NOTE_HEADER.size
        name_start, name_end = checked_range(cursor, namesz, end, "note name")
        name = data[name_start:name_end]
        cursor = align_up(name_end, 4)
        require(cursor <= end, "note name alignment exceeds PT_NOTE")
        desc_start, desc_end = checked_range(cursor, descsz, end, "note descriptor")
        desc = data[desc_start:desc_end]
        cursor = align_up(desc_end, 4)
        require(cursor <= end, "note descriptor alignment exceeds PT_NOTE")
        if note_type != NT_GNU_PROPERTY_TYPE_0 or name.rstrip(b"\0") != b"GNU":
            continue
        property_note = True
        property_cursor = 0
        while property_cursor < len(desc):
            if len(desc) - property_cursor < GNU_PROPERTY_HEADER.size:
                require(all(byte == 0 for byte in desc[property_cursor:]), "truncated GNU property padding")
                break
            property_type, property_size = GNU_PROPERTY_HEADER.unpack_from(desc, property_cursor)
            property_cursor += GNU_PROPERTY_HEADER.size
            _, property_end = checked_range(property_cursor, property_size, len(desc), "GNU property data")
            property_data = desc[property_cursor:property_end]
            if property_type == GNU_PROPERTY_X86_FEATURE_1_AND:
                require(property_size == 4, "unexpected x86 feature property width")
                feature_bits = struct.unpack_from("<I", property_data, 0)[0]
                ibt = bool(feature_bits & GNU_PROPERTY_X86_FEATURE_1_IBT)
                shstk = bool(feature_bits & GNU_PROPERTY_X86_FEATURE_1_SHSTK)
            property_cursor = align_up(property_end, 8)
            require(property_cursor <= len(desc), "GNU property alignment exceeds descriptor")
    return property_note, ibt, shstk


def parse_elf(path: pathlib.Path) -> dict[str, Any]:
    data = path.read_bytes()
    require(len(data) >= ELF_HEADER.size, f"generated ELF is truncated: {path.name}")
    (
        ident,
        elf_type,
        machine,
        version,
        entry,
        phoff,
        _shoff,
        _flags,
        ehsize,
        phentsize,
        phnum,
        _shentsize,
        _shnum,
        _shstrndx,
    ) = ELF_HEADER.unpack_from(data, 0)
    require(ident[:4] == b"\x7fELF", f"generated output is not ELF: {path.name}")
    require(ident[4] == 2 and ident[5] == 1 and ident[6] == 1, f"generated output is not ELF64 little-endian version 1: {path.name}")
    require(machine == EM_X86_64, f"generated output is not x86_64: {path.name}")
    require(version == 1 and ehsize == ELF_HEADER.size, f"generated ELF header is unsupported: {path.name}")
    require(phnum != 0xFFFF, f"generated ELF uses extended program-header numbering: {path.name}")
    require(phnum > 0 and phentsize == PROGRAM_HEADER.size, f"generated ELF has invalid program-header geometry: {path.name}")
    table_size = phnum * phentsize
    checked_range(phoff, table_size, len(data), "program-header table")

    load_count = 0
    executable_load_count = 0
    rwx_load_count = 0
    dynamic_present = False
    interpreter_present = False
    gnu_stack_present = False
    gnu_stack_executable = False
    gnu_relro_present = False
    note_segments: list[tuple[int, int]] = []

    for index in range(phnum):
        position = phoff + index * phentsize
        p_type, p_flags, p_offset, _vaddr, _paddr, p_filesz, _memsz, _align = PROGRAM_HEADER.unpack_from(data, position)
        checked_range(p_offset, p_filesz, len(data), f"program header {index} file range")
        if p_type == PT_LOAD:
            load_count += 1
            if p_flags & PF_X:
                executable_load_count += 1
                if p_flags & PF_W:
                    rwx_load_count += 1
        elif p_type == PT_DYNAMIC:
            dynamic_present = True
        elif p_type == PT_INTERP:
            interpreter_present = True
        elif p_type == PT_GNU_STACK:
            gnu_stack_present = True
            gnu_stack_executable = bool(p_flags & PF_X)
        elif p_type == PT_GNU_RELRO:
            gnu_relro_present = True
        elif p_type == PT_NOTE:
            note_segments.append((p_offset, p_filesz))

    property_note = False
    ibt = False
    shstk = False
    for note_offset, note_size in note_segments:
        observed_note, observed_ibt, observed_shstk = parse_gnu_properties(data, note_offset, note_size)
        property_note = property_note or observed_note
        ibt = ibt or observed_ibt
        shstk = shstk or observed_shstk

    type_name = {ET_EXEC: "ET_EXEC", ET_DYN: "ET_DYN"}.get(elf_type, f"ET_{elf_type}")
    return {
        "elf_class": "ELF64",
        "endianness": "little",
        "machine": "x86_64",
        "elf_type": type_name,
        "entry": f"0x{entry:016x}",
        "entry_nonzero": entry != 0,
        "program_header_count": phnum,
        "load_count": load_count,
        "executable_load_count": executable_load_count,
        "rwx_load_count": rwx_load_count,
        "dynamic_present": dynamic_present,
        "interpreter_present": interpreter_present,
        "gnu_stack_present": gnu_stack_present,
        "gnu_stack_executable": gnu_stack_executable,
        "gnu_relro_present": gnu_relro_present,
        "gnu_property_note_present": property_note,
        "gnu_property_x86_ibt": ibt,
        "gnu_property_x86_shstk": shstk,
    }


def validate_elf_expectations(
    facts: dict[str, Any], artifact: dict[str, Any], hardening: dict[str, Any], target_id: str
) -> None:
    require(facts["elf_type"] == artifact["expected_elf_type"], f"{target_id}: unexpected ELF type")
    require(facts["dynamic_present"] is artifact["expected_dynamic"], f"{target_id}: unexpected PT_DYNAMIC state")
    require(facts["interpreter_present"] is artifact["expected_interpreter"], f"{target_id}: unexpected PT_INTERP state")
    entry_state = artifact["expected_entry_state"]
    if entry_state == "nonzero":
        require(facts["entry_nonzero"], f"{target_id}: expected nonzero entry point")
    elif entry_state == "zero":
        require(not facts["entry_nonzero"], f"{target_id}: expected zero entry point")
    else:
        require(entry_state == "unconstrained", f"{target_id}: invalid entry expectation")
    require(facts["load_count"] > 0 and facts["executable_load_count"] > 0, f"{target_id}: missing executable PT_LOAD")
    require(facts["rwx_load_count"] == 0, f"{target_id}: generated an RWX PT_LOAD")
    require(facts["gnu_stack_present"], f"{target_id}: missing PT_GNU_STACK")
    require(
        facts["gnu_stack_executable"] is hardening["expected_stack_executable"],
        f"{target_id}: unexpected executable-stack state",
    )
    require(facts["gnu_property_x86_ibt"] is hardening["expected_ibt"], f"{target_id}: unexpected IBT property state")
    require(facts["gnu_property_x86_shstk"] is hardening["expected_shstk"], f"{target_id}: unexpected SHSTK property state")
    expected_relro = bool(facts["dynamic_present"] and hardening["expected_relro_when_dynamic"])
    require(facts["gnu_relro_present"] is expected_relro, f"{target_id}: unexpected GNU_RELRO state")


def parse_profile_list(value: Any, name: str, *, allowed_fields: set[str]) -> list[dict[str, Any]]:
    require(isinstance(value, list) and value, f"{name} must be a nonempty array")
    require(len(value) <= MAX_PROFILE_ITEMS, f"{name} contains too many profiles")
    observed: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        require(isinstance(raw, dict), f"{name}[{index}] must be an object")
        unknown = set(raw) - allowed_fields
        require(not unknown, f"{name}[{index}] has unknown fields: {sorted(unknown)}")
        profile = dict(raw)
        identifier = safe_id(profile.get("id"), f"{name}[{index}].id")
        require(identifier not in observed, f"duplicate {name} id: {identifier}")
        observed.add(identifier)
        if "flags" in profile:
            profile["flags"] = require_flags(profile["flags"], f"{name}[{index}].flags")
        if "compile_flags" in profile:
            profile["compile_flags"] = require_flags(profile["compile_flags"], f"{name}[{index}].compile_flags")
        if "link_flags" in profile:
            profile["link_flags"] = require_flags(profile["link_flags"], f"{name}[{index}].link_flags")
        result.append(profile)
    return result


def parse_spec(spec_path: pathlib.Path, repo_root: pathlib.Path) -> tuple[dict[str, Any], bytes, dict[str, pathlib.Path]]:
    raw = spec_path.read_bytes()
    require(len(raw) <= MAX_MANIFEST_BYTES, "corpus specification is too large")
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CorpusError(f"invalid corpus specification JSON: {exc}") from exc
    require(isinstance(spec, dict), "corpus specification must be an object")
    require(set(spec) == {
        "schema_version", "corpus_id", "evidence_class", "frozen", "publication_eligible",
        "target_count", "source", "toolchains", "linker", "common_compile_flags",
        "common_link_flags", "optimization_profiles", "artifact_profiles",
        "hardening_profiles", "build_environment", "limits",
    }, "corpus specification fields do not match schema version 1")
    require_int(spec["schema_version"], "schema_version", minimum=1, maximum=1)
    spec["corpus_id"] = safe_id(spec["corpus_id"], "corpus_id")
    require(spec["evidence_class"] == "diagnostic", "provisional corpus must use evidence_class=diagnostic")
    require(require_bool(spec["frozen"], "frozen") is False, "provisional corpus must declare frozen=false")
    require(require_bool(spec["publication_eligible"], "publication_eligible") is False, "provisional corpus must declare publication_eligible=false")
    spec["target_count"] = require_int(spec["target_count"], "target_count", minimum=1, maximum=MAX_TARGETS)

    source = spec["source"]
    require(isinstance(source, dict) and set(source) == {
        "id", "path", "sha256", "license", "license_path", "license_sha256", "redistribution"
    }, "source object fields do not match schema version 1")
    source["id"] = safe_id(source["id"], "source.id")
    source["sha256"] = require_sha256(source["sha256"], "source.sha256")
    source["license"] = require_string(source["license"], "source.license")
    source["license_sha256"] = require_sha256(source["license_sha256"], "source.license_sha256")
    source["redistribution"] = require_string(source["redistribution"], "source.redistribution")
    source_path = resolve_repository_input(repo_root, spec_path.parent, source["path"], "source.path")
    license_path = resolve_repository_input(repo_root, spec_path.parent, source["license_path"], "source.license_path")
    require(sha256_file(source_path) == source["sha256"], "source SHA-256 does not match the specification")
    require(sha256_file(license_path) == source["license_sha256"], "license SHA-256 does not match the specification")

    toolchains = parse_profile_list(spec["toolchains"], "toolchains", allowed_fields={"id", "command", "required"})
    for index, toolchain in enumerate(toolchains):
        toolchain["command"] = require_string(toolchain.get("command"), f"toolchains[{index}].command")
        require(require_bool(toolchain.get("required"), f"toolchains[{index}].required"), "all provisional toolchains must be required")
    spec["toolchains"] = toolchains

    linker = spec["linker"]
    require(isinstance(linker, dict) and set(linker) == {"id", "command", "driver_flag"}, "linker object fields do not match schema version 1")
    linker["id"] = safe_id(linker["id"], "linker.id")
    linker["command"] = require_string(linker["command"], "linker.command")
    linker["driver_flag"] = require_string(linker["driver_flag"], "linker.driver_flag")

    spec["common_compile_flags"] = require_flags(spec["common_compile_flags"], "common_compile_flags")
    spec["common_link_flags"] = require_flags(spec["common_link_flags"], "common_link_flags")
    spec["optimization_profiles"] = parse_profile_list(
        spec["optimization_profiles"], "optimization_profiles", allowed_fields={"id", "flags"}
    )
    artifacts = parse_profile_list(
        spec["artifact_profiles"],
        "artifact_profiles",
        allowed_fields={
            "id", "output_suffix", "compile_flags", "link_flags", "expected_elf_type",
            "expected_dynamic", "expected_interpreter", "expected_entry_state",
        },
    )
    for index, artifact in enumerate(artifacts):
        suffix = require_string(artifact["output_suffix"], f"artifact_profiles[{index}].output_suffix")
        require(suffix in {".elf", ".so"}, f"artifact_profiles[{index}].output_suffix is unsupported")
        require(artifact["expected_elf_type"] in {"ET_EXEC", "ET_DYN"}, f"artifact_profiles[{index}].expected_elf_type is unsupported")
        artifact["expected_dynamic"] = require_bool(artifact["expected_dynamic"], f"artifact_profiles[{index}].expected_dynamic")
        artifact["expected_interpreter"] = require_bool(artifact["expected_interpreter"], f"artifact_profiles[{index}].expected_interpreter")
        require(artifact["expected_entry_state"] in {"zero", "nonzero", "unconstrained"}, f"artifact_profiles[{index}].expected_entry_state is unsupported")
    spec["artifact_profiles"] = artifacts

    hardening = parse_profile_list(
        spec["hardening_profiles"],
        "hardening_profiles",
        allowed_fields={
            "id", "compile_flags", "link_flags", "expected_stack_executable",
            "expected_ibt", "expected_shstk", "expected_relro_when_dynamic",
        },
    )
    for index, profile in enumerate(hardening):
        for field in ("expected_stack_executable", "expected_ibt", "expected_shstk", "expected_relro_when_dynamic"):
            profile[field] = require_bool(profile[field], f"hardening_profiles[{index}].{field}")
    spec["hardening_profiles"] = hardening

    environment = spec["build_environment"]
    require(isinstance(environment, dict) and environment, "build_environment must be a nonempty object")
    for key, value in environment.items():
        require(isinstance(key, str) and SAFE_ENV.fullmatch(key) is not None, f"unsafe build environment key: {key!r}")
        require(key not in RESERVED_ENV, f"build_environment may not override reserved key: {key}")
        require_string(value, f"build_environment.{key}", nonempty=False)
    require(environment.get("LC_ALL") == "C" and environment.get("TZ") == "UTC", "build environment must fix C locale and UTC")

    limits = spec["limits"]
    require(
        isinstance(limits, dict)
        and set(limits) == {"timeout_seconds", "maximum_output_bytes", "maximum_log_bytes"},
        "limits fields do not match schema version 1",
    )
    limits["timeout_seconds"] = require_int(limits["timeout_seconds"], "limits.timeout_seconds", minimum=1, maximum=600)
    limits["maximum_output_bytes"] = require_int(limits["maximum_output_bytes"], "limits.maximum_output_bytes", minimum=4096, maximum=256 * 1024 * 1024)
    limits["maximum_log_bytes"] = require_int(
        limits["maximum_log_bytes"], "limits.maximum_log_bytes", minimum=4096, maximum=64 * 1024 * 1024
    )

    product = len(toolchains) * len(spec["optimization_profiles"]) * len(artifacts) * len(hardening)
    require(product == spec["target_count"], f"target_count {spec['target_count']} does not match matrix product {product}")
    return spec, raw, {"source": source_path, "license": license_path}


def tool_identity(path: pathlib.Path, requested: str) -> dict[str, Any]:
    identity = file_identity(path)
    return {
        "requested_command": requested,
        "resolved_path": str(path),
        "size_bytes": identity["size_bytes"],
        "sha256": identity["sha256"],
        "mode": identity["mode"],
        "mtime_ns": identity["mtime_ns"],
    }


def capture_tool_metadata(
    identifier: str,
    requested: str,
    path: pathlib.Path,
    stage: pathlib.Path,
    workspace: pathlib.Path,
    environment: dict[str, str],
    timeout: int,
    maximum_capture_bytes: int,
    *,
    compiler: bool,
) -> dict[str, Any]:
    base = stage / "inputs" / "tool-versions" / identifier
    base.mkdir(parents=True, exist_ok=True)
    require_workspace_members(workspace)
    version = run_command([str(path), "--version"], workspace, environment, timeout, maximum_capture_bytes)
    require_workspace_members(workspace)
    require(version.returncode == 0, f"{identifier} --version failed with exit {version.returncode}")
    write_bytes(base / "version.stdout", version.stdout)
    write_bytes(base / "version.stderr", version.stderr)
    record = tool_identity(path, requested)
    record.update({
        "id": identifier,
        "version_argv": ["{tool}", "--version"],
        "version_stdout_path": (base / "version.stdout").relative_to(stage).as_posix(),
        "version_stdout_sha256": sha256_bytes(version.stdout),
        "version_stdout_size_bytes": len(version.stdout),
        "version_stderr_path": (base / "version.stderr").relative_to(stage).as_posix(),
        "version_stderr_sha256": sha256_bytes(version.stderr),
        "version_stderr_size_bytes": len(version.stderr),
        "version_first_line": version.stdout.decode("utf-8", errors="replace").splitlines()[0] if version.stdout else "",
    })
    if compiler:
        machine = run_command([str(path), "-dumpmachine"], workspace, environment, timeout, maximum_capture_bytes)
        require_workspace_members(workspace)
        require(machine.returncode == 0, f"{identifier} -dumpmachine failed with exit {machine.returncode}")
        write_bytes(base / "target.stdout", machine.stdout)
        write_bytes(base / "target.stderr", machine.stderr)
        record.update({
            "target_argv": ["{tool}", "-dumpmachine"],
            "target_triple": machine.stdout.decode("utf-8", errors="strict").strip(),
            "target_stdout_path": (base / "target.stdout").relative_to(stage).as_posix(),
            "target_stdout_sha256": sha256_bytes(machine.stdout),
            "target_stderr_path": (base / "target.stderr").relative_to(stage).as_posix(),
            "target_stderr_sha256": sha256_bytes(machine.stderr),
        })
        require(record["target_triple"], f"{identifier} returned an empty target triple")
    return record


def snapshot_input(source: pathlib.Path, destination: pathlib.Path, expected_sha: str, mode: int) -> dict[str, Any]:
    before = file_identity(source)
    require(before["sha256"] == expected_sha, f"input hash changed before snapshot: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    os.chmod(destination, mode)
    os.utime(destination, (FIXED_MTIME, FIXED_MTIME), follow_symlinks=False)
    copied = file_identity(destination)
    after = file_identity(source)
    require(before == after, f"input mutated while being snapshotted: {source}")
    require(copied["sha256"] == expected_sha and copied["size_bytes"] == before["size_bytes"], f"snapshot mismatch: {source}")
    return {
        "path": destination.as_posix(),
        "size_bytes": copied["size_bytes"],
        "sha256": copied["sha256"],
        "mode": copied["mode"],
    }


def render_commands_tsv(records: list[dict[str, Any]]) -> str:
    lines = ["\t".join(COMMAND_FIELDS)]
    for record in records:
        values = []
        for field in COMMAND_FIELDS:
            value = record[field]
            if field == "argv_json":
                value = json.dumps(value, separators=(",", ":"), ensure_ascii=True)
            text = str(value).replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")
            values.append(text)
        lines.append("\t".join(values))
    return "\n".join(lines) + "\n"


def fsync_tree(root: pathlib.Path) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
    directories = [root, *(path for path in root.rglob("*") if path.is_dir())]
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def normalize_tree_metadata(root: pathlib.Path) -> None:
    directories = [root, *(path for path in root.rglob("*") if path.is_dir())]
    for directory in directories:
        require(not directory.is_symlink(), f"corpus contains a symlinked directory: {directory.relative_to(root) if directory != root else '.'}")
        os.chmod(directory, DIRECTORY_MODE)
        os.utime(directory, (FIXED_MTIME, FIXED_MTIME), follow_symlinks=False)
    for path in (path for path in root.rglob("*") if path.is_file()):
        os.utime(path, (FIXED_MTIME, FIXED_MTIME), follow_symlinks=False)


def validate_tree_metadata(root: pathlib.Path) -> None:
    for directory in [root, *(path for path in root.rglob("*") if path.is_dir())]:
        metadata = directory.lstat()
        require(stat.S_ISDIR(metadata.st_mode), f"corpus directory metadata changed: {directory}")
        require(stat.S_IMODE(metadata.st_mode) == DIRECTORY_MODE, f"corpus directory mode changed: {directory.relative_to(root) if directory != root else '.'}")
        require(metadata.st_mtime_ns == 0, f"corpus directory mtime changed: {directory.relative_to(root) if directory != root else '.'}")


def validate_regular_tree(root: pathlib.Path) -> list[pathlib.Path]:
    require(root.is_dir() and not root.is_symlink(), "corpus root is not a real directory")
    files: list[pathlib.Path] = []
    for path in sorted(root.rglob("*")):
        metadata = path.lstat()
        if stat.S_ISDIR(metadata.st_mode):
            continue
        require(stat.S_ISREG(metadata.st_mode), f"corpus contains a non-regular member: {path.relative_to(root)}")
        require(metadata.st_nlink == 1, f"corpus contains a multiply linked file: {path.relative_to(root)}")
        files.append(path)
    return files


def write_checksum_manifest(root: pathlib.Path) -> None:
    checksum_path = root / "SHA256SUMS.txt"
    require(not checksum_path.exists(), "checksum manifest already exists")
    lines = []
    for path in validate_regular_tree(root):
        relative = path.relative_to(root).as_posix()
        if relative == "SHA256SUMS.txt":
            continue
        lines.append(f"{sha256_file(path)}  {relative}")
    write_text(checksum_path, "\n".join(lines) + "\n")


def parse_checksum_manifest(root: pathlib.Path) -> dict[str, str]:
    path = root / "SHA256SUMS.txt"
    require(path.is_file() and not path.is_symlink(), "missing SHA256SUMS.txt")
    records: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        require(len(line) >= 67 and line[64:66] == "  ", f"invalid checksum line {line_number}")
        digest = require_sha256(line[:64], f"checksum line {line_number}")
        name = line[66:]
        pure = pathlib.PurePosixPath(name)
        require(name and not pure.is_absolute() and ".." not in pure.parts and "\\" not in name, f"unsafe checksum path: {name!r}")
        require(name not in records and name != "SHA256SUMS.txt", f"duplicate or recursive checksum path: {name}")
        records[name] = digest
    require(records, "checksum manifest is empty")
    return records


def verify_checksum_manifest(root: pathlib.Path) -> dict[str, str]:
    records = parse_checksum_manifest(root)
    files = validate_regular_tree(root)
    actual_names = {path.relative_to(root).as_posix() for path in files}
    expected_names = set(records) | {"SHA256SUMS.txt"}
    require(actual_names == expected_names, f"corpus member set mismatch: missing={sorted(expected_names-actual_names)} extra={sorted(actual_names-expected_names)}")
    for name, digest in records.items():
        path = root / pathlib.PurePosixPath(name)
        require(sha256_file(path) == digest, f"checksum mismatch: {name}")
    return records


def corpus_member(root: pathlib.Path, raw: Any, name: str) -> pathlib.Path:
    value = require_string(raw, name)
    pure = pathlib.PurePosixPath(value)
    require(not pure.is_absolute() and pure.parts and ".." not in pure.parts and "\\" not in value, f"unsafe corpus member path: {value!r}")
    path = root.joinpath(*pure.parts)
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode), f"corpus member is not a regular file: {value}")
    return path


def verify_manifest_identity(root: pathlib.Path, record: Any, name: str, expected_mode: int) -> pathlib.Path:
    require(isinstance(record, dict), f"{name} must be an object")
    path = corpus_member(root, record.get("snapshot_path"), f"{name}.snapshot_path")
    identity = file_identity(path)
    require(identity["size_bytes"] == require_int(record.get("size_bytes"), f"{name}.size_bytes"), f"{name} size mismatch")
    require(identity["sha256"] == require_sha256(record.get("sha256"), f"{name}.sha256"), f"{name} hash mismatch")
    require(identity["mode"] == f"{expected_mode:04o}" and record.get("mode") == f"{expected_mode:04o}", f"{name} mode mismatch")
    return path


def parse_commands_tsv(root: pathlib.Path, raw_path: Any) -> list[dict[str, Any]]:
    path = corpus_member(root, raw_path, "commands_path")
    lines = path.read_text(encoding="utf-8").splitlines()
    require(lines and tuple(lines[0].split("\t")) == COMMAND_FIELDS, "commands.tsv header mismatch")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines[1:], 2):
        fields = line.split("\t")
        require(len(fields) == len(COMMAND_FIELDS), f"commands.tsv row {line_number} has the wrong field count")
        row = dict(zip(COMMAND_FIELDS, fields, strict=True))
        try:
            row["argv_json"] = json.loads(row["argv_json"])
        except json.JSONDecodeError as exc:
            raise CorpusError(f"commands.tsv row {line_number} has invalid argv_json") from exc
        require(isinstance(row["argv_json"], list) and all(isinstance(item, str) for item in row["argv_json"]), f"commands.tsv row {line_number} argv_json is invalid")
        require(row["exit_code"] == "0", f"commands.tsv row {line_number} records a failed command")
        rows.append(row)
    require(rows, "commands.tsv has no command rows")
    return rows


def atomic_publish_noreplace(stage: pathlib.Path, final: pathlib.Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    require(renameat2 is not None, "Linux renameat2 is required for no-replace corpus publication")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        AT_FDCWD,
        os.fsencode(stage),
        AT_FDCWD,
        os.fsencode(final),
        RENAME_NOREPLACE,
    )
    if result != 0:
        error = ctypes.get_errno()
        if error == errno.EEXIST:
            raise CorpusError(f"corpus already exists and will not be replaced: {final}")
        raise CorpusError(f"renameat2 publication failed: {os.strerror(error)}")


def platform_check(spec_path: pathlib.Path, repo_root: pathlib.Path) -> str:
    require(sys.platform.startswith("linux"), "provisional corpus builder requires Linux")
    require(platform.machine().lower() in {"x86_64", "amd64"}, "provisional corpus builder requires x86_64")
    libc = ctypes.CDLL(None)
    require(getattr(libc, "renameat2", None) is not None, "renameat2 is unavailable")
    enable_subreaper()
    require(not direct_child_pids(), "platform check started with unrelated child processes")
    spec, _raw, _paths = parse_spec(spec_path, repo_root)
    tools = [resolve_tool(item["command"], f"toolchains.{item['id']}") for item in spec["toolchains"]]
    tools.append(resolve_tool(spec["linker"]["command"], "linker.command"))
    return (
        "provisional-corpus-platform-check: ok "
        f"compilers={len(spec['toolchains'])} linker={spec['linker']['id']} "
        f"tools={len(tools)} subreaper=enabled"
    )


def build_corpus(spec_path: pathlib.Path, output_root: pathlib.Path, repo_root: pathlib.Path) -> pathlib.Path:
    spec, spec_raw, source_paths = parse_spec(spec_path, repo_root)
    corpus_id = spec["corpus_id"]
    output_root.mkdir(parents=True, exist_ok=True)
    output_root = output_root.resolve(strict=True)
    final = output_root / corpus_id
    require(not final.exists(), f"corpus already exists; verify it or remove it explicitly: {final}")
    stage = output_root / f".{corpus_id}.staging.{uuid.uuid4().hex}"
    require(not stage.exists(), f"staging path already exists: {stage}")
    source_identities = {
        "spec": file_identity(spec_path),
        "source": file_identity(source_paths["source"]),
        "license": file_identity(source_paths["license"]),
        "builder": file_identity(pathlib.Path(__file__).resolve(strict=True)),
    }
    tool_records: list[dict[str, Any]] = []
    tool_paths: dict[str, pathlib.Path] = {}
    command_records: list[dict[str, Any]] = []
    target_records: list[dict[str, Any]] = []
    try:
        stage.mkdir(mode=0o700)
        os.chmod(stage, DIRECTORY_MODE)
        enable_subreaper()
        require(not direct_child_pids(), "corpus builder started with unrelated child processes")
        install_signal_handlers()
        for directory in (
            stage / "inputs" / "spec",
            stage / "inputs" / "source",
            stage / "inputs" / "license",
            stage / "inputs" / "builder",
            stage / "logs",
            stage / "targets",
            stage / "command-workdir",
        ):
            directory.mkdir(parents=True, exist_ok=True)
            os.chmod(directory, DIRECTORY_MODE)

        spec_snapshot = stage / "inputs" / "spec" / "corpus-spec.json"
        write_bytes(spec_snapshot, spec_raw, INPUT_MODE)
        source_snapshot = stage / "inputs" / "source" / source_paths["source"].name
        source_record = snapshot_input(source_paths["source"], source_snapshot, spec["source"]["sha256"], INPUT_MODE)
        license_snapshot = stage / "inputs" / "license" / source_paths["license"].name
        license_record = snapshot_input(source_paths["license"], license_snapshot, spec["source"]["license_sha256"], INPUT_MODE)
        builder_source = pathlib.Path(__file__).resolve(strict=True)
        builder_snapshot = stage / "inputs" / "builder" / builder_source.name
        builder_record = snapshot_input(builder_source, builder_snapshot, source_identities["builder"]["sha256"], SCRIPT_MODE)

        for toolchain in spec["toolchains"]:
            tool_paths[toolchain["id"]] = resolve_tool(toolchain["command"], f"toolchain {toolchain['id']}")
        tool_paths[spec["linker"]["id"]] = resolve_tool(spec["linker"]["command"], "linker")
        environment = fixed_environment(dict(spec["build_environment"]), tool_paths.values())
        timeout = spec["limits"]["timeout_seconds"]
        maximum_log_bytes = spec["limits"]["maximum_log_bytes"]
        for toolchain in spec["toolchains"]:
            tool_path = tool_paths[toolchain["id"]]
            tool_records.append(capture_tool_metadata(
                toolchain["id"], toolchain["command"], tool_path, stage, stage / "command-workdir", environment, timeout,
                maximum_log_bytes, compiler=True
            ))
        linker_path = tool_paths[spec["linker"]["id"]]
        tool_records.append(capture_tool_metadata(
            spec["linker"]["id"], spec["linker"]["command"], linker_path, stage, stage / "command-workdir", environment, timeout,
            maximum_log_bytes, compiler=False
        ))
        tool_before = {record["id"]: file_identity(tool_paths[record["id"]]) for record in tool_records}
        linker_search_flag = f"-B{linker_path.parent}{os.sep}"

        determinism_flags = [
            f"-fdebug-prefix-map={stage}=/x64lens/provisional-corpus",
            f"-ffile-prefix-map={stage}=/x64lens/provisional-corpus",
            f"-fmacro-prefix-map={stage}=/x64lens/provisional-corpus",
        ]

        for toolchain in spec["toolchains"]:
            compiler = tool_paths[toolchain["id"]]
            for optimization in spec["optimization_profiles"]:
                for artifact in spec["artifact_profiles"]:
                    for hardening in spec["hardening_profiles"]:
                        target_id = "-".join((toolchain["id"], optimization["id"], artifact["id"], hardening["id"]))
                        safe_id(target_id, "target id")
                        suffix = artifact["output_suffix"]
                        workdir = stage / "command-workdir"
                        require_workspace_members(workdir)
                        output_work = workdir / f"{target_id}{suffix}"
                        argv = [
                            str(compiler),
                            *spec["common_compile_flags"],
                            *optimization["flags"],
                            *artifact["compile_flags"],
                            *hardening["compile_flags"],
                            *determinism_flags,
                            linker_search_flag,
                            spec["linker"]["driver_flag"],
                            *spec["common_link_flags"],
                            *artifact["link_flags"],
                            *hardening["link_flags"],
                            str(source_snapshot),
                            "-o",
                            str(output_work),
                        ]
                        result = run_command(argv, workdir, environment, timeout, maximum_log_bytes)
                        require_workspace_members(workdir, output_work if result.returncode == 0 else None)
                        log_root = stage / "logs" / target_id
                        log_root.mkdir(parents=True, exist_ok=False)
                        stdout_path = log_root / "compiler.stdout"
                        stderr_path = log_root / "compiler.stderr"
                        write_bytes(stdout_path, result.stdout)
                        write_bytes(stderr_path, result.stderr)
                        require(result.returncode == 0, f"{target_id}: compiler exited {result.returncode}")
                        require(output_work.is_file() and not output_work.is_symlink(), f"{target_id}: compiler did not produce a regular file")
                        output_size = output_work.stat().st_size
                        require(0 < output_size <= spec["limits"]["maximum_output_bytes"], f"{target_id}: output size is outside the configured bound")
                        facts = parse_elf(output_work)
                        validate_elf_expectations(facts, artifact, hardening, target_id)
                        final_target = stage / "targets" / f"{target_id}{suffix}"
                        os.rename(output_work, final_target)
                        require_workspace_members(workdir)
                        os.chmod(final_target, TARGET_MODE)
                        os.utime(final_target, (FIXED_MTIME, FIXED_MTIME), follow_symlinks=False)
                        output_identity = file_identity(final_target)
                        canonical_argv = [
                            "{compiler}",
                            *spec["common_compile_flags"],
                            *optimization["flags"],
                            *artifact["compile_flags"],
                            *hardening["compile_flags"],
                            *CANONICAL_DETERMINISM_FLAGS,
                            CANONICAL_LINKER_SEARCH_FLAG,
                            spec["linker"]["driver_flag"],
                            *spec["common_link_flags"],
                            *artifact["link_flags"],
                            *hardening["link_flags"],
                            "{source_snapshot}",
                            "-o",
                            "{output}",
                        ]
                        command_record = {
                            "target_id": target_id,
                            "compiler_id": toolchain["id"],
                            "linker_id": spec["linker"]["id"],
                            "optimization_id": optimization["id"],
                            "artifact_id": artifact["id"],
                            "hardening_id": hardening["id"],
                            "cwd": "command-workdir",
                            "argv_json": canonical_argv,
                            "exit_code": result.returncode,
                            "stdout_path": stdout_path.relative_to(stage).as_posix(),
                            "stdout_sha256": sha256_bytes(result.stdout),
                            "stderr_path": stderr_path.relative_to(stage).as_posix(),
                            "stderr_sha256": sha256_bytes(result.stderr),
                            "output_path": final_target.relative_to(stage).as_posix(),
                            "output_sha256": output_identity["sha256"],
                        }
                        command_records.append(command_record)
                        target_records.append({
                            "id": target_id,
                            "relative_path": final_target.relative_to(stage).as_posix(),
                            "compiler_id": toolchain["id"],
                            "linker_id": spec["linker"]["id"],
                            "optimization_id": optimization["id"],
                            "artifact_id": artifact["id"],
                            "hardening_id": hardening["id"],
                            "source_id": spec["source"]["id"],
                            "source_sha256": spec["source"]["sha256"],
                            "license": spec["source"]["license"],
                            "redistribution": spec["source"]["redistribution"],
                            "size_bytes": output_identity["size_bytes"],
                            "sha256": output_identity["sha256"],
                            "mode": output_identity["mode"],
                            "target_executed": False,
                            "elf": facts,
                            "command_index": len(command_records) - 1,
                        })

        require(len(target_records) == spec["target_count"], "materialized target count does not match the specification")
        require(len({record["id"] for record in target_records}) == len(target_records), "duplicate target identifiers")
        for record in tool_records:
            require(file_identity(tool_paths[record["id"]]) == tool_before[record["id"]], f"tool changed during corpus build: {record['id']}")
        require(file_identity(spec_path) == source_identities["spec"], "corpus specification changed during build")
        require(file_identity(source_paths["source"]) == source_identities["source"], "corpus source changed during build")
        require(file_identity(source_paths["license"]) == source_identities["license"], "license changed during build")
        require(file_identity(builder_source) == source_identities["builder"], "corpus builder changed during build")

        write_text(stage / "commands.tsv", render_commands_tsv(command_records))
        manifest = {
            "schema_version": 1,
            "corpus_id": corpus_id,
            "evidence_class": "diagnostic",
            "frozen": False,
            "publication_eligible": False,
            "target_count": len(target_records),
            "matrix": {
                "toolchains": len(spec["toolchains"]),
                "optimization_profiles": len(spec["optimization_profiles"]),
                "artifact_profiles": len(spec["artifact_profiles"]),
                "hardening_profiles": len(spec["hardening_profiles"]),
            },
            "inputs": {
                "spec": {
                    "source_path": repository_relative(repo_root, spec_path),
                    "snapshot_path": spec_snapshot.relative_to(stage).as_posix(),
                    "size_bytes": len(spec_raw),
                    "sha256": sha256_bytes(spec_raw),
                    "mode": f"{INPUT_MODE:04o}",
                },
                "source": {
                    "id": spec["source"]["id"],
                    "source_path": repository_relative(repo_root, source_paths["source"]),
                    "snapshot_path": pathlib.Path(source_record["path"]).relative_to(stage).as_posix(),
                    "size_bytes": source_record["size_bytes"],
                    "sha256": source_record["sha256"],
                    "mode": source_record["mode"],
                    "license": spec["source"]["license"],
                    "redistribution": spec["source"]["redistribution"],
                },
                "license": {
                    "source_path": repository_relative(repo_root, source_paths["license"]),
                    "snapshot_path": pathlib.Path(license_record["path"]).relative_to(stage).as_posix(),
                    "size_bytes": license_record["size_bytes"],
                    "sha256": license_record["sha256"],
                    "mode": license_record["mode"],
                },
                "builder": {
                    "source_path": repository_relative(repo_root, builder_source),
                    "snapshot_path": pathlib.Path(builder_record["path"]).relative_to(stage).as_posix(),
                    "size_bytes": builder_record["size_bytes"],
                    "sha256": builder_record["sha256"],
                    "mode": builder_record["mode"],
                },
            },
            "environment": {
                "system": platform.system(),
                "kernel_release": platform.release(),
                "machine": platform.machine(),
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
                "python_executable": str(pathlib.Path(sys.executable).resolve()),
                "build_environment": dict(sorted(spec["build_environment"].items())),
                "effective_environment": dict(sorted(environment.items())),
                "target_execution_policy": "generated targets are never executed and are published mode 0444",
                "publication_policy": "same-parent staging plus renameat2(RENAME_NOREPLACE)",
                "process_cleanup_policy": "new session per compiler command plus Linux subreaper cleanup for escaped descendants",
                "linker_selection_policy": "compiler driver receives the resolved linker directory through -B and the requested -fuse-ld=bfd selector",
            },
            "tools": tool_records,
            "command_count": len(command_records),
            "commands_path": "commands.tsv",
            "targets": target_records,
            "claim_boundaries": [
                "The corpus is mutable diagnostic evidence and is not the Sprint 15-frozen campaign corpus.",
                "Build-role labels describe requested linker modes; they do not replace Sprint 12 loader interpretation.",
                "Byte reproducibility is asserted only for the recorded tool and environment stratum.",
                "Generated targets are static-analysis inputs and are never executed by this workflow.",
                "Compiler drivers and the requested linker are hashed and reauthenticated; auxiliary toolchain programs are not bundled in this provisional corpus.",
                "Compiler and linker paths are reauthenticated before publication; transient mutation by an unrelated same-UID writer remains outside this diagnostic builder's trust boundary.",
            ],
        }
        write_bytes(stage / "corpus-manifest.json", canonical_json(manifest))

        # Reauthenticate every retained input, log, and output after the final compiler exits.
        require(sha256_file(spec_snapshot) == sha256_bytes(spec_raw), "retained spec snapshot changed")
        require(sha256_file(source_snapshot) == spec["source"]["sha256"], "retained source snapshot changed")
        require(sha256_file(license_snapshot) == spec["source"]["license_sha256"], "retained license snapshot changed")
        require(sha256_file(builder_snapshot) == source_identities["builder"]["sha256"], "retained builder snapshot changed")
        for command in command_records:
            require(sha256_file(stage / command["stdout_path"]) == command["stdout_sha256"], f"retained stdout changed: {command['target_id']}")
            require(sha256_file(stage / command["stderr_path"]) == command["stderr_sha256"], f"retained stderr changed: {command['target_id']}")
        for target in target_records:
            target_path = stage / target["relative_path"]
            require(sha256_file(target_path) == target["sha256"], f"retained target changed: {target['id']}")
            require(parse_elf(target_path) == target["elf"], f"retained target ELF facts changed: {target['id']}")

        expected_files = {
            "corpus-manifest.json",
            "commands.tsv",
            spec_snapshot.relative_to(stage).as_posix(),
            source_snapshot.relative_to(stage).as_posix(),
            license_snapshot.relative_to(stage).as_posix(),
            builder_snapshot.relative_to(stage).as_posix(),
        }
        for tool in tool_records:
            for key, value in tool.items():
                if key.endswith("_path") and isinstance(value, str) and value.startswith("inputs/"):
                    expected_files.add(value)
        for command in command_records:
            expected_files.add(command["stdout_path"])
            expected_files.add(command["stderr_path"])
            expected_files.add(command["output_path"])
        require_exact_members(stage, expected_files, {"command-workdir"})

        normalize_tree_metadata(stage)
        write_checksum_manifest(stage)
        expected_files.add("SHA256SUMS.txt")
        require_exact_members(stage, expected_files, {"command-workdir"})
        normalize_tree_metadata(stage)
        verify_checksum_manifest(stage)
        validate_tree_metadata(stage)
        fsync_tree(stage)
        atomic_publish_noreplace(stage, final)
        parent_fd = os.open(output_root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        verify_corpus(final)
        return final
    except BaseException as failure:
        cleanup_failure: BaseException | None = None
        if os.path.lexists(stage):
            try:
                remove_owned_tree(stage, output_root, "provisional corpus staging tree")
            except BaseException as exc:
                cleanup_failure = exc
        if cleanup_failure is not None:
            raise CorpusError(
                f"corpus build failed with {type(failure).__name__}; staging cleanup also failed: {cleanup_failure}"
            ) from failure
        raise


def verify_corpus(root: pathlib.Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    verify_checksum_manifest(root)
    validate_tree_metadata(root)
    manifest_path = root / "corpus-manifest.json"
    require(manifest_path.stat().st_size <= MAX_MANIFEST_BYTES, "corpus manifest is too large")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"invalid corpus manifest JSON: {exc}") from exc
    require(isinstance(manifest, dict), "corpus manifest must be an object")
    require(set(manifest) == {
        "schema_version", "corpus_id", "evidence_class", "frozen", "publication_eligible",
        "target_count", "matrix", "inputs", "environment", "tools", "command_count",
        "commands_path", "targets", "claim_boundaries",
    }, "corpus manifest fields do not match schema version 1")
    require(manifest.get("schema_version") == 1, "unsupported corpus manifest schema")
    corpus_id = safe_id(manifest.get("corpus_id"), "manifest.corpus_id")
    require(root.name == corpus_id, "corpus directory name does not match corpus_id")
    require(manifest.get("evidence_class") == "diagnostic", "corpus evidence class is not diagnostic")
    require(manifest.get("frozen") is False, "provisional corpus must remain frozen=false")
    require(manifest.get("publication_eligible") is False, "provisional corpus must remain publication_eligible=false")

    inputs = manifest.get("inputs")
    require(isinstance(inputs, dict) and set(inputs) == {"spec", "source", "license", "builder"}, "corpus input records are incomplete")
    require(
        isinstance(inputs["spec"], dict)
        and set(inputs["spec"]) == {"source_path", "snapshot_path", "size_bytes", "sha256", "mode"},
        "corpus spec input record is malformed",
    )
    require(
        isinstance(inputs["source"], dict)
        and set(inputs["source"]) == {
            "id", "source_path", "snapshot_path", "size_bytes", "sha256", "mode", "license", "redistribution"
        },
        "corpus source input record is malformed",
    )
    for input_name in ("license", "builder"):
        require(
            isinstance(inputs[input_name], dict)
            and set(inputs[input_name]) == {"source_path", "snapshot_path", "size_bytes", "sha256", "mode"},
            f"corpus {input_name} input record is malformed",
        )
    spec_snapshot = verify_manifest_identity(root, inputs["spec"], "inputs.spec", INPUT_MODE)
    source_snapshot = verify_manifest_identity(root, inputs["source"], "inputs.source", INPUT_MODE)
    license_snapshot = verify_manifest_identity(root, inputs["license"], "inputs.license", INPUT_MODE)
    builder_snapshot = verify_manifest_identity(root, inputs["builder"], "inputs.builder", SCRIPT_MODE)
    try:
        snapshot_spec = json.loads(spec_snapshot.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"retained corpus specification is invalid JSON: {exc}") from exc
    require(isinstance(snapshot_spec, dict), "retained corpus specification must be an object")
    require(set(snapshot_spec) == {
        "schema_version", "corpus_id", "evidence_class", "frozen", "publication_eligible",
        "target_count", "source", "toolchains", "linker", "common_compile_flags",
        "common_link_flags", "optimization_profiles", "artifact_profiles",
        "hardening_profiles", "build_environment", "limits",
    }, "retained corpus specification fields do not match schema version 1")
    require(snapshot_spec.get("schema_version") == 1, "retained corpus specification schema changed")
    require(snapshot_spec.get("corpus_id") == corpus_id, "retained corpus specification id mismatch")
    require(snapshot_spec.get("evidence_class") == "diagnostic", "retained corpus specification evidence class changed")
    require(snapshot_spec.get("frozen") is False and snapshot_spec.get("publication_eligible") is False, "retained corpus specification eligibility changed")
    source_spec = snapshot_spec.get("source")
    require(
        isinstance(source_spec, dict)
        and set(source_spec) == {
            "id", "path", "sha256", "license", "license_path", "license_sha256", "redistribution"
        },
        "retained corpus source specification is missing or malformed",
    )
    source_spec["id"] = safe_id(source_spec.get("id"), "retained source id")
    require_string(source_spec.get("path"), "retained source path")
    require_string(source_spec.get("license_path"), "retained license path")
    source_spec["sha256"] = require_sha256(source_spec.get("sha256"), "retained source sha256")
    source_spec["license_sha256"] = require_sha256(
        source_spec.get("license_sha256"), "retained license sha256"
    )
    source_spec["license"] = require_string(source_spec.get("license"), "retained source license")
    source_spec["redistribution"] = require_string(
        source_spec.get("redistribution"), "retained redistribution policy"
    )
    require(sha256_file(source_snapshot) == require_sha256(source_spec.get("sha256"), "retained source sha256"), "retained source does not match the specification")
    require(sha256_file(license_snapshot) == require_sha256(source_spec.get("license_sha256"), "retained license sha256"), "retained license does not match the specification")
    require(inputs["source"].get("license") == source_spec.get("license"), "retained source license identity mismatch")
    require(inputs["source"].get("redistribution") == source_spec.get("redistribution"), "retained source redistribution policy mismatch")
    require(inputs["source"].get("id") == source_spec.get("id"), "retained source id mismatch")
    require(builder_snapshot.name == pathlib.Path(__file__).name, "retained builder snapshot name changed")

    toolchains = parse_profile_list(
        snapshot_spec.get("toolchains"), "retained toolchains", allowed_fields={"id", "command", "required"}
    )
    for index, toolchain in enumerate(toolchains):
        toolchain["command"] = require_string(
            toolchain.get("command"), f"retained toolchains[{index}].command"
        )
        require(
            require_bool(toolchain.get("required"), f"retained toolchains[{index}].required"),
            "all retained provisional toolchains must be required",
        )
    optimizations = parse_profile_list(
        snapshot_spec.get("optimization_profiles"),
        "retained optimization profiles",
        allowed_fields={"id", "flags"},
    )
    artifacts = parse_profile_list(
        snapshot_spec.get("artifact_profiles"),
        "retained artifact profiles",
        allowed_fields={
            "id", "output_suffix", "compile_flags", "link_flags", "expected_elf_type",
            "expected_dynamic", "expected_interpreter", "expected_entry_state",
        },
    )
    for index, artifact in enumerate(artifacts):
        artifact["output_suffix"] = require_string(
            artifact.get("output_suffix"), f"retained artifact profiles[{index}].output_suffix"
        )
        require(
            artifact["output_suffix"] in {".elf", ".so"},
            f"retained artifact profiles[{index}].output_suffix is unsupported",
        )
        require(
            artifact.get("expected_elf_type") in {"ET_EXEC", "ET_DYN"},
            f"retained artifact profiles[{index}].expected_elf_type is unsupported",
        )
        artifact["expected_dynamic"] = require_bool(
            artifact.get("expected_dynamic"), f"retained artifact profiles[{index}].expected_dynamic"
        )
        artifact["expected_interpreter"] = require_bool(
            artifact.get("expected_interpreter"),
            f"retained artifact profiles[{index}].expected_interpreter",
        )
        require(
            artifact.get("expected_entry_state") in {"zero", "nonzero", "unconstrained"},
            f"retained artifact profiles[{index}].expected_entry_state is unsupported",
        )
    hardening_profiles = parse_profile_list(
        snapshot_spec.get("hardening_profiles"),
        "retained hardening profiles",
        allowed_fields={
            "id", "compile_flags", "link_flags", "expected_stack_executable",
            "expected_ibt", "expected_shstk", "expected_relro_when_dynamic",
        },
    )
    for index, profile in enumerate(hardening_profiles):
        for field in (
            "expected_stack_executable", "expected_ibt", "expected_shstk", "expected_relro_when_dynamic"
        ):
            profile[field] = require_bool(
                profile.get(field), f"retained hardening profiles[{index}].{field}"
            )
    linker = snapshot_spec.get("linker")
    require(
        isinstance(linker, dict) and set(linker) == {"id", "command", "driver_flag"},
        "retained linker specification is missing or malformed",
    )
    linker["id"] = safe_id(linker.get("id"), "retained linker id")
    linker["command"] = require_string(linker.get("command"), "retained linker command")
    linker["driver_flag"] = require_string(linker.get("driver_flag"), "retained linker driver flag")
    common_compile_flags = require_flags(
        snapshot_spec.get("common_compile_flags"), "retained common compile flags"
    )
    common_link_flags = require_flags(
        snapshot_spec.get("common_link_flags"), "retained common link flags"
    )
    retained_environment = snapshot_spec.get("build_environment")
    require(isinstance(retained_environment, dict) and retained_environment, "retained build environment is missing")
    for key, value in retained_environment.items():
        require(isinstance(key, str) and SAFE_ENV.fullmatch(key) is not None, f"unsafe retained environment key: {key!r}")
        require(key not in RESERVED_ENV, f"retained build environment overrides reserved key: {key}")
        require_string(value, f"retained build environment {key}", nonempty=False)
    require(
        retained_environment.get("LC_ALL") == "C" and retained_environment.get("TZ") == "UTC",
        "retained build environment lost C locale or UTC",
    )
    retained_limits = snapshot_spec.get("limits")
    require(
        isinstance(retained_limits, dict)
        and set(retained_limits) == {"timeout_seconds", "maximum_output_bytes", "maximum_log_bytes"},
        "retained limits are missing or malformed",
    )
    require_int(retained_limits.get("timeout_seconds"), "retained timeout_seconds", minimum=1, maximum=600)
    require_int(
        retained_limits.get("maximum_output_bytes"),
        "retained maximum_output_bytes",
        minimum=4096,
        maximum=256 * 1024 * 1024,
    )
    require_int(
        retained_limits.get("maximum_log_bytes"),
        "retained maximum_log_bytes",
        minimum=4096,
        maximum=64 * 1024 * 1024,
    )
    toolchain_ids = [safe_id(item.get("id"), "retained toolchain id") for item in toolchains]
    optimization_ids = [safe_id(item.get("id"), "retained optimization id") for item in optimizations]
    artifact_ids = [safe_id(item.get("id"), "retained artifact id") for item in artifacts]
    hardening_ids = [safe_id(item.get("id"), "retained hardening id") for item in hardening_profiles]
    require(len(set(toolchain_ids)) == len(toolchain_ids), "retained toolchain ids are not unique")
    require(len(set(optimization_ids)) == len(optimization_ids), "retained optimization ids are not unique")
    require(len(set(artifact_ids)) == len(artifact_ids), "retained artifact ids are not unique")
    require(len(set(hardening_ids)) == len(hardening_ids), "retained hardening ids are not unique")
    matrix = manifest.get("matrix")
    require(matrix == {
        "toolchains": len(toolchain_ids),
        "optimization_profiles": len(optimization_ids),
        "artifact_profiles": len(artifact_ids),
        "hardening_profiles": len(hardening_ids),
    }, "corpus matrix dimensions do not match the retained specification")
    expected_ids = [
        "-".join((toolchain, optimization, artifact, hardening))
        for toolchain in toolchain_ids
        for optimization in optimization_ids
        for artifact in artifact_ids
        for hardening in hardening_ids
    ]
    require(snapshot_spec.get("target_count") == len(expected_ids), "retained target_count does not match its matrix")
    require(manifest.get("target_count") == len(expected_ids), "manifest target_count does not match the retained specification")

    tools = manifest.get("tools")
    require(isinstance(tools, list), "corpus tool records are missing")
    expected_tool_ids = set(toolchain_ids) | {linker["id"]}
    require({safe_id(record.get("id"), "tool id") for record in tools if isinstance(record, dict)} == expected_tool_ids, "tool identity set does not match the retained specification")
    expected_commands = {toolchain["id"]: toolchain["command"] for toolchain in toolchains}
    expected_commands[linker["id"]] = linker["command"]
    for index, record in enumerate(tools):
        require(isinstance(record, dict), f"tools[{index}] must be an object")
        tool_id = safe_id(record.get("id"), f"tools[{index}].id")
        common_tool_fields = {
            "requested_command", "resolved_path", "size_bytes", "sha256", "mode", "mtime_ns", "id",
            "version_argv", "version_stdout_path", "version_stdout_sha256", "version_stdout_size_bytes",
            "version_stderr_path", "version_stderr_sha256", "version_stderr_size_bytes", "version_first_line",
        }
        compiler_tool_fields = {
            "target_argv", "target_triple", "target_stdout_path", "target_stdout_sha256",
            "target_stderr_path", "target_stderr_sha256",
        }
        expected_tool_fields = common_tool_fields | (set() if tool_id == linker["id"] else compiler_tool_fields)
        require(set(record) == expected_tool_fields, f"tool record fields changed: {tool_id}")
        require(
            record.get("requested_command") == expected_commands[tool_id],
            f"tool requested command mismatch: {tool_id}",
        )
        require_string(record.get("resolved_path"), f"tools[{index}].resolved_path")
        require_int(record.get("size_bytes"), f"tools[{index}].size_bytes", minimum=1)
        require_sha256(record.get("sha256"), f"tools[{index}].sha256")
        require(
            isinstance(record.get("mode"), str) and re.fullmatch(r"[0-7]{4}", record["mode"]) is not None,
            f"tools[{index}].mode is invalid",
        )
        require_int(record.get("mtime_ns"), f"tools[{index}].mtime_ns")
        require(record.get("version_argv") == ["{tool}", "--version"], f"tool version command changed: {tool_id}")
        for stem in ("version", *(() if tool_id == linker["id"] else ("target",))):
            path = corpus_member(root, record.get(f"{stem}_stdout_path"), f"tools[{index}].{stem}_stdout_path")
            require(sha256_file(path) == require_sha256(record.get(f"{stem}_stdout_sha256"), f"tools[{index}].{stem}_stdout_sha256"), f"tool {stem} stdout hash mismatch")
            stderr_path = corpus_member(root, record.get(f"{stem}_stderr_path"), f"tools[{index}].{stem}_stderr_path")
            require(sha256_file(stderr_path) == require_sha256(record.get(f"{stem}_stderr_sha256"), f"tools[{index}].{stem}_stderr_sha256"), f"tool {stem} stderr hash mismatch")
            if stem == "version":
                require(path.stat().st_size == record.get("version_stdout_size_bytes"), f"tool version stdout size mismatch: {tool_id}")
                require(stderr_path.stat().st_size == record.get("version_stderr_size_bytes"), f"tool version stderr size mismatch: {tool_id}")
                first_line = path.read_text(encoding="utf-8", errors="replace").splitlines()
                require(
                    record.get("version_first_line") == (first_line[0] if first_line else ""),
                    f"tool version first line mismatch: {tool_id}",
                )
            else:
                require(record.get("target_argv") == ["{tool}", "-dumpmachine"], f"tool target command changed: {tool_id}")
                require(
                    record.get("target_triple") == path.read_text(encoding="utf-8", errors="strict").strip()
                    and bool(record.get("target_triple")),
                    f"tool target triple mismatch: {tool_id}",
                )

    environment = manifest.get("environment")
    require(
        isinstance(environment, dict)
        and set(environment) == {
            "system", "kernel_release", "machine", "python_version", "python_implementation",
            "python_executable", "build_environment", "effective_environment", "target_execution_policy",
            "publication_policy", "process_cleanup_policy", "linker_selection_policy",
        },
        "corpus environment record is missing or malformed",
    )
    require(
        environment.get("target_execution_policy")
        == "generated targets are never executed and are published mode 0444",
        "target execution policy changed",
    )
    require(
        environment.get("publication_policy") == "same-parent staging plus renameat2(RENAME_NOREPLACE)",
        "publication policy changed",
    )
    require(
        environment.get("process_cleanup_policy")
        == "new session per compiler command plus Linux subreaper cleanup for escaped descendants",
        "process cleanup policy changed",
    )
    require(
        environment.get("linker_selection_policy")
        == "compiler driver receives the resolved linker directory through -B and the requested -fuse-ld=bfd selector",
        "linker selection policy changed",
    )
    effective = environment.get("effective_environment")
    require(isinstance(effective, dict) and effective.get("HOME") == "/nonexistent" and effective.get("TMPDIR") == "/tmp", "effective build environment is incomplete")
    require(isinstance(effective.get("PATH"), str) and effective["PATH"], "effective build PATH is missing")
    for key, value in snapshot_spec.get("build_environment", {}).items():
        require(effective.get(key) == value, f"effective build environment lost {key}")

    targets = manifest.get("targets")
    require(isinstance(targets, list) and targets, "corpus manifest has no targets")
    require([target.get("id") for target in targets if isinstance(target, dict)] == expected_ids, "target matrix order or membership changed")
    optimization_by_id = {item["id"]: item for item in optimizations}
    artifact_by_id = {item["id"]: item for item in artifacts}
    hardening_by_id = {item["id"]: item for item in hardening_profiles}
    observed: set[str] = set()
    target_by_id: dict[str, dict[str, Any]] = {}
    for index, target in enumerate(targets):
        require(isinstance(target, dict), f"targets[{index}] must be an object")
        require(
            set(target) == {
                "id", "relative_path", "compiler_id", "linker_id", "optimization_id", "artifact_id",
                "hardening_id", "source_id", "source_sha256", "license", "redistribution", "size_bytes",
                "sha256", "mode", "target_executed", "elf", "command_index",
            },
            f"target record fields changed at index {index}",
        )
        target_id = safe_id(target.get("id"), f"targets[{index}].id")
        require(target_id not in observed, f"duplicate target id: {target_id}")
        observed.add(target_id)
        target_by_id[target_id] = target
        require(target.get("compiler_id") in toolchain_ids, f"target compiler id changed: {target_id}")
        require(target.get("linker_id") == linker.get("id"), f"target linker id changed: {target_id}")
        require(target.get("optimization_id") in optimization_ids, f"target optimization id changed: {target_id}")
        require(target.get("artifact_id") in artifact_ids, f"target artifact id changed: {target_id}")
        require(target.get("hardening_id") in hardening_ids, f"target hardening id changed: {target_id}")
        require(target.get("source_id") == source_spec.get("id"), f"target source id changed: {target_id}")
        require(target.get("source_sha256") == source_spec.get("sha256"), f"target source hash changed: {target_id}")
        require(target.get("license") == source_spec.get("license"), f"target license changed: {target_id}")
        require(target.get("redistribution") == source_spec.get("redistribution"), f"target redistribution policy changed: {target_id}")
        path = corpus_member(root, target.get("relative_path"), f"targets[{index}].relative_path")
        require(path.parent == root / "targets", f"target path escaped the targets directory: {target_id}")
        identity = file_identity(path)
        require(identity["mode"] == f"{TARGET_MODE:04o}" and target.get("mode") == f"{TARGET_MODE:04o}", f"target mode changed: {target_id}")
        require(identity["size_bytes"] == target.get("size_bytes"), f"target size mismatch: {target_id}")
        require(identity["sha256"] == target.get("sha256"), f"target hash mismatch: {target_id}")
        require(target.get("target_executed") is False, f"target execution policy changed: {target_id}")
        facts = parse_elf(path)
        require(facts == target.get("elf"), f"target ELF facts mismatch: {target_id}")
        validate_elf_expectations(facts, artifact_by_id[target["artifact_id"]], hardening_by_id[target["hardening_id"]], target_id)
        require(target.get("command_index") == index, f"target command index changed: {target_id}")

    commands = parse_commands_tsv(root, manifest.get("commands_path"))
    require(manifest.get("command_count") == len(commands) == len(targets), "command_count does not match target count")
    require([row["target_id"] for row in commands] == expected_ids, "commands.tsv target order or membership changed")
    for index, row in enumerate(commands):
        target = targets[index]
        target_id = target["id"]
        require(row["compiler_id"] == target["compiler_id"], f"command compiler id mismatch: {target_id}")
        require(row["linker_id"] == target["linker_id"] == linker.get("id"), f"command linker id mismatch: {target_id}")
        require(row["optimization_id"] == target["optimization_id"], f"command optimization id mismatch: {target_id}")
        require(row["artifact_id"] == target["artifact_id"], f"command artifact id mismatch: {target_id}")
        require(row["hardening_id"] == target["hardening_id"], f"command hardening id mismatch: {target_id}")
        require(row["cwd"] == "command-workdir", f"command cwd mismatch: {target_id}")
        artifact = artifact_by_id[target["artifact_id"]]
        hardening = hardening_by_id[target["hardening_id"]]
        optimization = optimization_by_id[target["optimization_id"]]
        expected_argv = [
            "{compiler}",
            *common_compile_flags,
            *optimization["flags"],
            *artifact["compile_flags"],
            *hardening["compile_flags"],
            *CANONICAL_DETERMINISM_FLAGS,
            CANONICAL_LINKER_SEARCH_FLAG,
            linker["driver_flag"],
            *common_link_flags,
            *artifact["link_flags"],
            *hardening["link_flags"],
            "{source_snapshot}",
            "-o",
            "{output}",
        ]
        require(row["argv_json"] == expected_argv, f"canonical command mismatch: {target_id}")
        expected_target_path = f"targets/{target_id}{artifact['output_suffix']}"
        require(target["relative_path"] == expected_target_path, f"target output path mismatch: {target_id}")
        require(row["output_path"] == expected_target_path, f"command output path mismatch: {target_id}")
        require(row["output_sha256"] == target["sha256"], f"command output hash mismatch: {target_id}")
        require(
            row["stdout_path"] == f"logs/{target_id}/compiler.stdout",
            f"command stdout path mismatch: {target_id}",
        )
        require(
            row["stderr_path"] == f"logs/{target_id}/compiler.stderr",
            f"command stderr path mismatch: {target_id}",
        )
        stdout_path = corpus_member(root, row["stdout_path"], f"command stdout path {target_id}")
        stderr_path = corpus_member(root, row["stderr_path"], f"command stderr path {target_id}")
        require(sha256_file(stdout_path) == require_sha256(row["stdout_sha256"], f"command stdout hash {target_id}"), f"command stdout hash mismatch: {target_id}")
        require(sha256_file(stderr_path) == require_sha256(row["stderr_sha256"], f"command stderr hash {target_id}"), f"command stderr hash mismatch: {target_id}")

    expected_files = {
        "SHA256SUMS.txt",
        "corpus-manifest.json",
        manifest["commands_path"],
        inputs["spec"]["snapshot_path"],
        inputs["source"]["snapshot_path"],
        inputs["license"]["snapshot_path"],
        inputs["builder"]["snapshot_path"],
    }
    for tool in tools:
        for key, value in tool.items():
            if key.endswith("_path") and isinstance(value, str) and value.startswith("inputs/"):
                expected_files.add(value)
    for row in commands:
        expected_files.add(row["stdout_path"])
        expected_files.add(row["stderr_path"])
        expected_files.add(row["output_path"])
    require_exact_members(root, expected_files, {"command-workdir"})

    for path in validate_regular_tree(root):
        metadata = path.lstat()
        expected_mode = SCRIPT_MODE if path == builder_snapshot else TEXT_MODE
        require(stat.S_IMODE(metadata.st_mode) == expected_mode, f"corpus file mode changed: {path.relative_to(root)}")
        require(metadata.st_mtime_ns == 0, f"corpus file mtime changed: {path.relative_to(root)}")
    return manifest


def clean_corpus(spec_path: pathlib.Path, output_root: pathlib.Path, repo_root: pathlib.Path) -> pathlib.Path:
    spec, _raw, _paths = parse_spec(spec_path, repo_root)
    output_root.mkdir(parents=True, exist_ok=True)
    output_root = output_root.resolve(strict=True)
    target = output_root / spec["corpus_id"]
    candidate = pathlib.Path(os.path.abspath(target))
    require(candidate.parent == output_root and candidate.name == spec["corpus_id"], "refusing an out-of-scope corpus cleanup path")
    if not os.path.lexists(candidate):
        return candidate
    metadata = os.lstat(candidate)
    require(stat.S_ISDIR(metadata.st_mode), "refusing to clean a non-directory corpus path")
    manifest = verify_corpus(candidate)
    require(
        manifest.get("corpus_id") == spec["corpus_id"]
        and manifest.get("evidence_class") == "diagnostic"
        and manifest.get("frozen") is False
        and manifest.get("publication_eligible") is False,
        "refusing to clean a directory without the expected provisional corpus identity",
    )
    remove_owned_tree(candidate, output_root, "provisional corpus")
    return candidate


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=pathlib.Path, help="corpus specification JSON")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--output-root", type=pathlib.Path, help="parent directory for transactional corpus publication")
    actions.add_argument("--verify", type=pathlib.Path, help="verify an existing generated corpus")
    actions.add_argument("--clean-output-root", type=pathlib.Path, help="safely remove the spec-named generated corpus below this root")
    actions.add_argument("--platform-check", action="store_true", help="validate platform and required tools")
    actions.add_argument("--print-corpus-id", action="store_true", help="print corpus_id from the validated specification")
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    repo_root = pathlib.Path(__file__).resolve(strict=True).parents[2]
    if args.verify is not None:
        manifest = verify_corpus(args.verify)
        matrix = manifest["matrix"]
        print(
            "provisional-corpus-verify: ok "
            f"corpus={manifest['corpus_id']} targets={manifest['target_count']} "
            f"compilers={matrix['toolchains']} optimizations={matrix['optimization_profiles']} "
            f"artifacts={matrix['artifact_profiles']} hardening={matrix['hardening_profiles']}"
        )
        return 0
    require(args.spec is not None, "--spec is required for build, clean, platform check, or corpus-id output")
    spec_path = args.spec.resolve(strict=True)
    if args.clean_output_root is not None:
        target = clean_corpus(spec_path, args.clean_output_root, repo_root)
        print(f"clean-provisional-corpus: ok path={target}")
        return 0
    if args.platform_check:
        print(platform_check(spec_path, repo_root))
        return 0
    spec, _raw, _paths = parse_spec(spec_path, repo_root)
    if args.print_corpus_id:
        print(spec["corpus_id"])
        return 0
    require(args.output_root is not None, "--output-root is required")
    final = build_corpus(spec_path, args.output_root, repo_root)
    matrix = spec
    print(
        "provisional-corpus-build: ok "
        f"corpus={spec['corpus_id']} targets={spec['target_count']} "
        f"compilers={len(matrix['toolchains'])} optimizations={len(matrix['optimization_profiles'])} "
        f"artifacts={len(matrix['artifact_profiles'])} hardening={len(matrix['hardening_profiles'])} "
        f"path={final}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except CorpusInterrupted as exc:
        print(f"provisional-corpus: error: {exc}", file=sys.stderr)
        raise SystemExit(128 + exc.signum)
    except (CorpusError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"provisional-corpus: error: {exc}", file=sys.stderr)
        raise SystemExit(EXIT_ERROR)
