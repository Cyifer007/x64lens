#!/usr/bin/env python3
"""Validate bounded whole-batch transaction semantics before timing use.

This diagnostic oracle executes a versioned, outcome-complete case authority.
It rejects duplicate JSON keys, authenticates an explicit case order, streams
bounded child output, enforces deadlines after leader exit, reaps same-group and
new-session descendants through Linux subreaper custody, and publishes only a
complete successful batch. Transaction roots are removed through the shared
identity-bound cleanup helper. No wall-clock value is emitted and batch elapsed
time is never divided into a single-invocation latency claim.
"""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import struct
from typing import Any, Sequence
import uuid

SCRIPT = Path(__file__).resolve()
EXPECTED_AUTHORITY_SHA256 = "145be2efdd7c184956c465da647c2050efe5f06c7e11cd235f9bc9c80486b161"

CASE_FAMILIES: dict[str, list[str]] = {
    "empty": ["empty"],
    "singleton": [
        "singleton-success",
        "singleton-nonzero",
        "singleton-timeout",
        "singleton-stdout-limit",
        "singleton-stderr-limit",
    ],
    "three_member": [
        "three-all-success",
        "three-nonzero-first",
        "three-nonzero-middle",
        "three-nonzero-final",
        "three-timeout-first",
        "three-timeout-middle",
        "three-timeout-final",
        "three-stdout-limit-first",
        "three-stdout-limit-middle",
        "three-stdout-limit-final",
        "three-stderr-limit-first",
        "three-stderr-limit-middle",
        "three-stderr-limit-final",
    ],
    "process_tree": [
        "singleton-leader-exit-pipe",
        "singleton-detached-descendant",
    ],
    "signals": [
        "sigint-before-first",
        "sigint-between-members",
        "sigint-member-active",
        "sigint-after-final",
        "sigterm-before-first",
        "sigterm-between-members",
        "sigterm-member-active",
        "sigterm-after-final",
    ],
}
CASE_ORDER = [case for family in CASE_FAMILIES.values() for case in family]


class PilotError(RuntimeError):
    """Raised when the authority, transaction, process, or cleanup contract fails."""


@dataclass(frozen=True)
class MemberResult:
    state: str
    exit_code: int | None
    stdout_bytes: int
    stderr_bytes: int


@dataclass(frozen=True)
class StreamSpec:
    name: str
    limit: int


@dataclass
class OwnedTree:
    path: Path
    identity: Any

    @classmethod
    def capture(cls, path: Path) -> "OwnedTree":
        return cls(path, CLEANUP.parse_identity(CLEANUP.identify(path)))

    @classmethod
    def temporary(cls, prefix: str) -> "OwnedTree":
        path = Path(tempfile.mkdtemp(prefix=prefix))
        return cls.capture(path)

    def cleanup(self) -> None:
        CLEANUP.remove(self.path, self.identity)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PilotError(message)


def load_cleanup() -> Any:
    path = SCRIPT.with_name("remove-owned-tree.py")
    spec = importlib.util.spec_from_file_location("x64lens_owned_tree_cleanup", path)
    require(spec is not None and spec.loader is not None, f"cannot load cleanup helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CLEANUP = load_cleanup()
_SUBREAPER_ENABLED = False

IN_CREATE = 0x00000100
IN_MOVED_TO = 0x00000080
IN_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
IN_NONBLOCK = getattr(os, "O_NONBLOCK", 0)
INOTIFY_EVENT = struct.Struct("iIII")


class PublicationObserver:
    """Retain every result-name creation or move after an explicit handshake."""

    def __init__(self, transaction: Path) -> None:
        require(sys.platform.startswith("linux"), "publication transition observation requires Linux")
        libc = ctypes.CDLL(None, use_errno=True)
        init = libc.inotify_init1
        add = libc.inotify_add_watch
        init.argtypes = [ctypes.c_int]
        init.restype = ctypes.c_int
        add.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        add.restype = ctypes.c_int
        self.fd = init(IN_CLOEXEC | IN_NONBLOCK)
        if self.fd < 0:
            code = ctypes.get_errno()
            raise PilotError(f"cannot initialize publication observer: {os.strerror(code)}")
        self.transitions = 0
        self.closed = False
        try:
            self.watch = add(self.fd, os.fsencode(transaction), IN_CREATE | IN_MOVED_TO)
            if self.watch < 0:
                code = ctypes.get_errno()
                raise PilotError(f"cannot watch transaction publication: {os.strerror(code)}")
            require(not (transaction / "result").exists(), "result existed before publication observer handshake")
        except BaseException:
            os.close(self.fd)
            self.closed = True
            raise

    def poll(self) -> int:
        if self.closed:
            return self.transitions
        while True:
            try:
                data = os.read(self.fd, 65536)
            except BlockingIOError:
                return self.transitions
            if not data:
                return self.transitions
            offset = 0
            while offset < len(data):
                require(len(data) - offset >= INOTIFY_EVENT.size, "truncated inotify publication event")
                _watch, mask, _cookie, length = INOTIFY_EVENT.unpack_from(data, offset)
                offset += INOTIFY_EVENT.size
                require(length <= len(data) - offset, "invalid inotify publication event length")
                raw_name = data[offset:offset + length]
                offset += length
                name = raw_name.split(b"\0", 1)[0]
                if name == b"result" and mask & (IN_CREATE | IN_MOVED_TO):
                    self.transitions += 1

    def close(self) -> None:
        if not self.closed:
            os.close(self.fd)
            self.closed = True


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PilotError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json_loads(raw: str) -> Any:
    return json.loads(raw, object_pairs_hook=reject_duplicate_pairs)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_normal_case(case: str) -> list[str]:
    if case == "empty":
        return []
    if case == "singleton-success":
        return ["success"]
    for mode in (
        "nonzero",
        "timeout",
        "stdout-limit",
        "stderr-limit",
        "leader-exit-pipe",
        "detached-descendant",
    ):
        if case == f"singleton-{mode}":
            return [mode]
    if case == "three-all-success":
        return ["success"] * 3
    positions = {"first": 0, "middle": 1, "final": 2}
    for mode in ("nonzero", "timeout", "stdout-limit", "stderr-limit"):
        for position, index in positions.items():
            if case == f"three-{mode}-{position}":
                modes = ["success"] * 3
                modes[index] = mode
                return modes
    raise PilotError(f"unknown normal case: {case}")


def expected_member(mode: str) -> MemberResult:
    values = {
        "success": MemberResult("success", 0, 3, 0),
        "nonzero": MemberResult("nonzero", 17, 0, 19),
        "timeout": MemberResult("timeout", None, 0, 0),
        "stdout-limit": MemberResult("stdout_limit", None, 4097, 0),
        "stderr-limit": MemberResult("stderr_limit", None, 0, 4097),
        "leader-exit-pipe": MemberResult("timeout", None, 0, 0),
        "detached-descendant": MemberResult("descendant", None, 0, 0),
    }
    require(mode in values, f"unknown expected member mode: {mode}")
    return values[mode]


def expected_normal_record(case: str) -> dict[str, Any]:
    modes = parse_normal_case(case)
    states = ["not_started"] * len(modes)
    codes: list[int | None] = [None] * len(modes)
    stdout_bytes = [0] * len(modes)
    stderr_bytes = [0] * len(modes)
    failure_index: int | None = None
    for index, mode in enumerate(modes):
        result = expected_member(mode)
        states[index] = result.state
        codes[index] = result.exit_code
        stdout_bytes[index] = result.stdout_bytes
        stderr_bytes[index] = result.stderr_bytes
        if result.state != "success":
            failure_index = index
            break
    successful = failure_index is None
    return {
        "case": case,
        "member_modes": modes,
        "member_states": states,
        "member_exit_codes": codes,
        "member_stdout_bytes": stdout_bytes,
        "member_stderr_bytes": stderr_bytes,
        "failure_index": failure_index,
        "outcome": "success" if successful else "failed",
        "published": successful,
        "publication_transitions": 1 if successful else 0,
    }


def expected_signal_record(case: str) -> dict[str, Any]:
    signame = case.split("-", 1)[0]
    signal_name = "SIGINT" if signame == "sigint" else "SIGTERM"
    exit_code = 130 if signal_name == "SIGINT" else 143
    return {
        "case": case,
        "signal": signal_name,
        "exit_code": exit_code,
        "published": False,
        "publication_transitions": 0,
        "stage_residue": 0,
        "surviving_children": 0,
    }


def expected_case_records() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for family, cases in CASE_FAMILIES.items():
        for case in cases:
            records[case] = expected_signal_record(case) if family == "signals" else expected_normal_record(case)
    return records


def expected_acceptance(repeats: int) -> dict[str, Any]:
    records = expected_case_records()
    normal = [records[case] for case in CASE_ORDER if not case.startswith(("sigint-", "sigterm-"))]
    failures = [record for record in normal if record["outcome"] == "failed"]
    failure_counts = {
        str(index): sum(record["failure_index"] == index for record in failures)
        for index in range(3)
    }
    return {
        "case_count": len(records),
        "execution_count": len(records) * repeats,
        "stable_result_hashes": len(records) * repeats,
        "normal_case_count": len(normal),
        "successful_batch_count": sum(record["outcome"] == "success" for record in normal),
        "failed_batch_count": len(failures),
        "failure_index_counts_per_case": failure_counts,
        "unstarted_member_count_per_case_set": sum(
            state == "not_started" for record in normal for state in record["member_states"]
        ),
        "process_tree_case_count": len(CASE_FAMILIES["process_tree"]),
        "descendant_failure_count": sum("descendant" in record["member_states"] for record in normal),
        "signal_case_count": len(CASE_FAMILIES["signals"]),
        "failure_positions_exact": True,
        "unstarted_members_explicit": True,
        "failed_batches_unpublished": True,
        "successful_batches_complete": True,
        "publication_transitions_exact": True,
        "interrupt_exit_codes": {"SIGINT": 130, "SIGTERM": 143},
        "streaming_output_cap": True,
        "deadline_survives_leader_exit": True,
        "adopted_descendants_reaped": True,
        "maximum_retained_bytes_per_overflow_stream": 4097,
        "stage_residue": 0,
        "surviving_children": 0,
        "file_descriptor_growth": 0,
        "timing_claims": 0,
    }


def read_authority(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = strict_json_loads(raw.decode("utf-8"))
    expected_keys = {
        "schema_id",
        "evidence_class",
        "frozen",
        "publication_eligible",
        "purpose",
        "repeat_count",
        "member_timeout_seconds",
        "maximum_stdout_bytes",
        "maximum_stderr_bytes",
        "publish_only_complete_success",
        "divide_batch_elapsed_into_single_run_latency",
        "case_families",
        "case_order",
        "case_expectations",
        "acceptance",
    }
    require(isinstance(value, dict) and set(value) == expected_keys, "authority top-level fields changed")
    require(value["schema_id"] == "sprint12-batch-transaction-pilot-v3", "wrong authority schema")
    require(value["evidence_class"] == "diagnostic", "authority must remain diagnostic")
    require(value["frozen"] is False, "authority must remain unfrozen")
    require(value["publication_eligible"] is False, "authority must remain publication-ineligible")
    require(
        value["purpose"]
        == "Validate exact whole-batch execution, streaming limits, process-tree cleanup, identity-bound cleanup, and publication transitions before throughput qualification.",
        "authority purpose changed",
    )
    require(type(value["repeat_count"]) is int and value["repeat_count"] == 3, "repeat count must be three")
    require(type(value["member_timeout_seconds"]) in {int, float} and value["member_timeout_seconds"] == 0.2,
            "member timeout changed")
    require(type(value["maximum_stdout_bytes"]) is int and value["maximum_stdout_bytes"] == 4096,
            "stdout limit changed")
    require(type(value["maximum_stderr_bytes"]) is int and value["maximum_stderr_bytes"] == 4096,
            "stderr limit changed")
    require(value["publish_only_complete_success"] is True, "failed publication policy changed")
    require(value["divide_batch_elapsed_into_single_run_latency"] is False, "divided latency is prohibited")
    require(isinstance(value["case_families"], dict), "case families must be an object")
    require(value["case_families"] == CASE_FAMILIES, "case families changed")
    require(value["case_order"] == CASE_ORDER, "explicit case order changed")
    require(value["case_expectations"] == expected_case_records(), "case expectations changed")
    require(value["acceptance"] == expected_acceptance(3), "acceptance semantics changed")
    require(hashlib.sha256(canonical(value)).hexdigest() == EXPECTED_AUTHORITY_SHA256,
            "authority canonical SHA-256 changed")
    return value


def ensure_subreaper() -> None:
    global _SUBREAPER_ENABLED
    if _SUBREAPER_ENABLED:
        return
    require(sys.platform.startswith("linux"), "batch process-tree custody requires Linux")
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    prctl.restype = ctypes.c_int
    if prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        code = ctypes.get_errno()
        raise PilotError(f"cannot enable Linux child subreaper: {os.strerror(code)}")
    _SUBREAPER_ENABLED = True


def direct_child_pids() -> set[int]:
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
            for line in status_text.splitlines():
                if line.startswith("PPid:"):
                    try:
                        ppid = int(line.split(":", 1)[1].strip())
                    except ValueError as exc:
                        raise PilotError(f"invalid PPid in {candidate}/status") from exc
                    if ppid == parent_pid:
                        children.add(int(candidate.name))
                    break
        return children
    except OSError as exc:
        raise PilotError(f"cannot inspect Linux child process state: {exc}") from exc
    if not text:
        return set()
    try:
        return {int(value) for value in text.split()}
    except ValueError as exc:
        raise PilotError(f"invalid Linux child process state: {text!r}") from exc


def process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def reap_children() -> int:
    count = 0
    while True:
        try:
            waited, _status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return count
        except InterruptedError:
            continue
        if waited <= 0:
            return count
        count += 1


def cleanup_adopted_descendants() -> tuple[bool, int]:
    children = direct_child_pids()
    if not children:
        return False, 0
    reaped = 0
    for signum, duration in ((signal.SIGTERM, 0.15), (signal.SIGKILL, 1.5)):
        deadline = time.monotonic() + duration
        while children and time.monotonic() < deadline:
            for pid in children:
                try:
                    os.kill(pid, signum)
                except ProcessLookupError:
                    pass
            reaped += reap_children()
            time.sleep(0.005)
            children = direct_child_pids()
    reaped += reap_children()
    require(not direct_child_pids(), f"adopted descendants survived cleanup: {sorted(direct_child_pids())}")
    return True, reaped


def terminate_tree(process: subprocess.Popen[bytes]) -> tuple[bool, int]:
    """Terminate the launch process group and every subreaper-adopted escape."""
    pgid = process.pid
    required = process.poll() is None or process_group_exists(pgid)
    if process_group_exists(pgid):
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 0.15
        while process_group_exists(pgid) and time.monotonic() < deadline:
            time.sleep(0.005)
        if process_group_exists(pgid):
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    if process.poll() is None:
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired as exc:
            raise PilotError(f"child process leader did not terminate: {process.pid}") from exc
    adopted_required, reaped = cleanup_adopted_descendants()
    deadline = time.monotonic() + 0.5
    while process_group_exists(pgid) and time.monotonic() < deadline:
        try:
            os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            break
        reap_children()
        time.sleep(0.005)
    require(not process_group_exists(pgid), f"child process group survived cleanup: {pgid}")
    return required or adopted_required, reaped


def child(mode: str) -> int:
    if mode == "success":
        os.write(1, b"ok\n")
        return 0
    if mode == "nonzero":
        os.write(2, b"controlled nonzero\n")
        return 17
    if mode in {"timeout", "block"}:
        time.sleep(30)
        return 0
    if mode == "stdout-limit":
        os.write(1, b"x" * 4097)
        return 0
    if mode == "stderr-limit":
        os.write(2, b"x" * 4097)
        return 0
    if mode == "leader-exit-pipe":
        pid = os.fork()
        if pid == 0:
            time.sleep(30)
            os._exit(0)
        return 0
    if mode == "detached-descendant":
        pid = os.fork()
        if pid == 0:
            os.setsid()
            devnull = os.open("/dev/null", os.O_RDWR)
            for fd in (0, 1, 2):
                os.dup2(devnull, fd)
            if devnull > 2:
                os.close(devnull)
            try:
                os.closerange(3, 1024)
            except OSError:
                pass
            time.sleep(30)
            os._exit(0)
        return 0
    raise PilotError(f"unknown child mode: {mode}")


def run_command(
    command: Sequence[str],
    *,
    timeout: float,
    stdout_limit: int,
    stderr_limit: int,
) -> MemberResult:
    """Run one member with bounded streams, deadline, and process-tree custody."""
    require(timeout > 0, "timeout must be positive")
    require(stdout_limit >= 0 and stderr_limit >= 0, "output limits must be nonnegative")
    ensure_subreaper()
    require(not direct_child_pids(), "batch runner has unrelated child processes before launch")
    process = subprocess.Popen(
        list(command),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    require(process.stdout is not None and process.stderr is not None, "child pipes unavailable")
    selector = selectors.DefaultSelector()
    counts = {"stdout": 0, "stderr": 0}
    limits = {"stdout": stdout_limit, "stderr": stderr_limit}
    pipes = {"stdout": process.stdout, "stderr": process.stderr}
    for name, pipe in pipes.items():
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe.fileno(), selectors.EVENT_READ, data=StreamSpec(name, limits[name]))
    deadline = time.monotonic() + timeout
    classification: str | None = None
    try:
        while selector.get_map():
            if time.monotonic() >= deadline:
                classification = "timeout"
                terminate_tree(process)
                break
            events = selector.select(max(0.0, min(0.05, deadline - time.monotonic())))
            if not events:
                continue
            for key, _mask in events:
                spec: StreamSpec = key.data
                remaining = spec.limit + 1 - counts[spec.name]
                read_size = max(1, min(65536, remaining))
                try:
                    chunk = os.read(key.fd, read_size)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fd)
                    continue
                counts[spec.name] += len(chunk)
                if counts[spec.name] > spec.limit:
                    classification = f"{spec.name}_limit"
                    terminate_tree(process)
                    break
            if classification is not None:
                break
        if classification is None:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                classification = "timeout"
                terminate_tree(process)
        if classification is None:
            lingering_group = process_group_exists(process.pid)
            adopted = bool(direct_child_pids())
            if lingering_group or adopted:
                terminate_tree(process)
                classification = "descendant"
        if classification == "timeout":
            return MemberResult("timeout", None, counts["stdout"], counts["stderr"])
        if classification == "stdout_limit":
            return MemberResult("stdout_limit", None, counts["stdout"], counts["stderr"])
        if classification == "stderr_limit":
            return MemberResult("stderr_limit", None, counts["stdout"], counts["stderr"])
        if classification == "descendant":
            return MemberResult("descendant", None, counts["stdout"], counts["stderr"])
        require(process.returncode is not None, "child return code unavailable")
        state = "success" if process.returncode == 0 else "nonzero"
        return MemberResult(state, process.returncode, counts["stdout"], counts["stderr"])
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
        if process.poll() is None or process_group_exists(process.pid) or direct_child_pids():
            terminate_tree(process)


def run_member(mode: str, timeout: float, stdout_limit: int, stderr_limit: int) -> MemberResult:
    commands = {
        "success": ["/bin/sh", "-c", "printf 'ok\\n'"],
        "nonzero": ["/bin/sh", "-c", "printf 'controlled nonzero\\n' >&2; exit 17"],
        "timeout": ["/bin/sh", "-c", "sleep 30"],
        "block": ["/bin/sh", "-c", "sleep 30"],
        "stdout-limit": ["/usr/bin/printf", "%s", "x" * 4097],
        "stderr-limit": ["/bin/sh", "-c", "yes x | tr -d '\\n' | head -c 4097 >&2"],
        "leader-exit-pipe": ["/bin/sh", "-c", "sleep 30 & exit 0"],
        "detached-descendant": ["/bin/sh", "-c", "setsid /bin/sleep 30 </dev/null >/dev/null 2>&1 & exit 0"],
    }
    require(mode in commands, f"unknown member mode: {mode}")
    return run_command(
        commands[mode],
        timeout=timeout,
        stdout_limit=stdout_limit,
        stderr_limit=stderr_limit,
    )


def write_json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def publish_complete(stage: Path, result: Path, record: dict[str, Any]) -> None:
    stage.mkdir(mode=0o700)
    payload = canonical(record)
    (stage / "result.json").write_bytes(payload)
    manifest = {"result.json": hashlib.sha256(payload).hexdigest()}
    (stage / "SHA256SUMS.json").write_bytes(canonical(manifest))
    os.rename(stage, result)
    require(result.is_dir() and not stage.exists(), "publication was not atomic")
    require((result / "result.json").read_bytes() == payload, "published result changed")
    require(strict_json_loads((result / "SHA256SUMS.json").read_text()) == manifest,
            "published manifest changed")


def normal_transaction(case: str, authority: dict[str, Any]) -> dict[str, Any]:
    modes = parse_normal_case(case)
    owned = OwnedTree.temporary("x64lens-batch-pilot-")
    root = owned.path
    stage = root / "stage"
    result = root / "result"
    states = ["not_started"] * len(modes)
    codes: list[int | None] = [None] * len(modes)
    stdout_bytes = [0] * len(modes)
    stderr_bytes = [0] * len(modes)
    failure_index: int | None = None
    transitions = 0
    try:
        for index, mode in enumerate(modes):
            member = run_member(
                mode,
                float(authority["member_timeout_seconds"]),
                int(authority["maximum_stdout_bytes"]),
                int(authority["maximum_stderr_bytes"]),
            )
            states[index] = member.state
            codes[index] = member.exit_code
            stdout_bytes[index] = member.stdout_bytes
            stderr_bytes[index] = member.stderr_bytes
            if member.state != "success":
                failure_index = index
                break
        successful = failure_index is None
        record = {
            "case": case,
            "member_modes": modes,
            "member_states": states,
            "member_exit_codes": codes,
            "member_stdout_bytes": stdout_bytes,
            "member_stderr_bytes": stderr_bytes,
            "failure_index": failure_index,
            "outcome": "success" if successful else "failed",
            "published": False,
            "publication_transitions": 0,
        }
        if successful:
            publication_record = dict(record)
            publication_record["published"] = True
            publication_record["publication_transitions"] = 1
            publish_complete(stage, result, publication_record)
            transitions = 1
        record["published"] = result.exists()
        record["publication_transitions"] = transitions
        require(not stage.exists(), "staging residue remained")
        require(record["published"] == successful, "publication state disagrees with outcome")
        require(transitions == (1 if successful else 0), "publication transition count disagrees with outcome")
        return record
    finally:
        owned.cleanup()


def signal_state_path(sync: Path) -> Path:
    return sync / "publication-state.json"


def signal_worker(case: str, sync: Path) -> int:
    ensure_subreaper()
    signame, barrier = case.split("-", 1)
    signum = signal.SIGINT if signame == "sigint" else signal.SIGTERM
    root = sync / "transaction"
    root.mkdir()
    owned = OwnedTree.capture(root)
    child_process: subprocess.Popen[bytes] | None = None
    caught = 0
    write_json_atomic(signal_state_path(sync), {"case": case, "state": "not_published", "transitions": 0})
    (sync / "worker-ready").write_text("worker-ready\n")
    observer_deadline = time.monotonic() + 10
    while not (sync / "observer-ready").exists() and time.monotonic() < observer_deadline:
        time.sleep(0.005)
    require((sync / "observer-ready").exists(), "publication observer did not complete handshake")

    def handler(received: int, _frame: object) -> None:
        nonlocal caught
        caught = received

    old = signal.signal(signum, handler)
    try:
        (root / "stage").mkdir()
        if barrier == "before-first":
            (sync / "ready").write_text("ready\n")
        elif barrier == "between-members":
            require(run_member("success", 5.0, 4096, 4096).state == "success", "first member failed")
            (sync / "ready").write_text("ready\n")
        elif barrier == "member-active":
            child_process = subprocess.Popen(
                [sys.executable, str(SCRIPT), "--child", "block"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            (sync / "child.pid").write_text(f"{child_process.pid}\n")
            (sync / "ready").write_text("ready\n")
        elif barrier == "after-final":
            for _ in range(3):
                require(run_member("success", 5.0, 4096, 4096).state == "success", "member failed")
            (sync / "ready").write_text("ready\n")
        else:
            raise PilotError(f"unknown signal barrier: {barrier}")
        deadline = time.monotonic() + 10
        while not caught and time.monotonic() < deadline:
            time.sleep(0.005)
        require(caught == signum, "expected signal was not received")
        return 128 + signum
    finally:
        signal.signal(signum, old)
        if child_process is not None:
            terminate_tree(child_process)
            if child_process.stdout is not None:
                child_process.stdout.close()
            if child_process.stderr is not None:
                child_process.stderr.close()
        owned.cleanup()


def run_signal_case(case: str) -> dict[str, Any]:
    ensure_subreaper()
    require(not direct_child_pids(), "batch runner has unrelated children before signal case")
    sync_owned = OwnedTree.temporary("x64lens-batch-signal-")
    sync = sync_owned.path
    signame = case.split("-", 1)[0]
    signum = signal.SIGINT if signame == "sigint" else signal.SIGTERM
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--signal-worker", case, "--sync", str(sync)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    observer: PublicationObserver | None = None
    try:
        handshake_deadline = time.monotonic() + 10
        while not (sync / "worker-ready").exists() and process.poll() is None and time.monotonic() < handshake_deadline:
            time.sleep(0.005)
        if not (sync / "worker-ready").exists():
            stdout, stderr = process.communicate(timeout=2)
            raise PilotError(
                f"signal worker did not create transaction: {case}; "
                f"exit={process.returncode} stdout={stdout[:200]!r} stderr={stderr[:400]!r}"
            )
        transaction = sync / "transaction"
        require(transaction.is_dir(), f"signal transaction was not created: {case}")
        observer = PublicationObserver(transaction)
        (sync / "observer-ready").write_text("observer-ready\n")

        deadline = time.monotonic() + 10
        while not (sync / "ready").exists() and process.poll() is None and time.monotonic() < deadline:
            observer.poll()
            time.sleep(0.005)
        if not (sync / "ready").exists():
            stdout, stderr = process.communicate(timeout=2)
            observer.poll()
            raise PilotError(
                f"signal worker did not reach barrier: {case}; "
                f"exit={process.returncode} stdout={stdout[:200]!r} stderr={stderr[:400]!r}"
            )
        observer.poll()
        os.kill(process.pid, signum)
        stdout, stderr = process.communicate(timeout=10)
        observer.poll()
        require(not stdout and not stderr, f"signal worker emitted output for {case}: {stderr[:400]!r}")
        require(process.returncode == 128 + signum, f"wrong signal exit for {case}: {process.returncode}")
        require(observer.transitions == 0, f"transient publication observed for {case}: {observer.transitions}")
        if process_group_exists(process.pid) or direct_child_pids():
            terminate_tree(process)
        require(not transaction.exists(), f"transaction residue remained for {case}")
        child_pid_file = sync / "child.pid"
        if child_pid_file.exists():
            pid = int(child_pid_file.read_text().strip())
            require(not Path(f"/proc/{pid}").exists(), f"child survived signal case: {pid}")
        state = strict_json_loads(signal_state_path(sync).read_text(encoding="utf-8"))
        require(
            state == {"case": case, "state": "not_published", "transitions": 0},
            f"signal publication transition disagrees with contract: {state!r}",
        )
        return {
            "case": case,
            "signal": signal.Signals(signum).name,
            "exit_code": process.returncode,
            "published": False,
            "publication_transitions": 0,
            "stage_residue": 0,
            "surviving_children": 0,
        }
    finally:
        if observer is not None:
            observer.close()
        if process.poll() is None or process_group_exists(process.pid) or direct_child_pids():
            terminate_tree(process)
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
        sync_owned.cleanup()


def verify_case_record(case: str, record: dict[str, Any], authority: dict[str, Any]) -> None:
    expected = authority["case_expectations"].get(case)
    require(expected is not None, f"case has no expected record: {case}")
    require(record == expected, f"case result mismatch: {case}: expected={expected!r} observed={record!r}")


def fd_count() -> int:
    path = Path("/proc/self/fd")
    return len(list(path.iterdir())) if path.is_dir() else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path)
    parser.add_argument("--child")
    parser.add_argument("--signal-worker")
    parser.add_argument("--sync", type=Path)
    args = parser.parse_args()
    if args.child:
        return child(args.child)
    if args.signal_worker:
        require(args.sync is not None, "--sync is required")
        return signal_worker(args.signal_worker, args.sync)
    require(args.authority is not None, "--authority is required")
    ensure_subreaper()
    require(not direct_child_pids(), "batch runner started with unrelated child processes")
    authority = read_authority(args.authority)
    cases = list(authority["case_order"])
    repeats = int(authority["repeat_count"])
    before_fds = fd_count()
    stable_hashes = 0
    verified_records: dict[str, dict[str, Any]] = {}
    for case in cases:
        outputs: list[str] = []
        for _ in range(repeats):
            output = run_signal_case(case) if case.startswith(("sigint-", "sigterm-")) else normal_transaction(case, authority)
            verify_case_record(case, output, authority)
            verified_records[case] = output
            outputs.append(digest(output))
            stable_hashes += 1
        require(len(set(outputs)) == 1, f"nondeterministic case result: {case}")
    after_fds = fd_count()
    fd_growth = after_fds - before_fds
    require(fd_growth == authority["acceptance"]["file_descriptor_growth"],
            f"file descriptor growth: {before_fds} -> {after_fds}")
    normal = [verified_records[case] for case in cases if not case.startswith(("sigint-", "sigterm-"))]
    failures = [record for record in normal if record["outcome"] == "failed"]
    signals = [verified_records[case] for case in cases if case.startswith(("sigint-", "sigterm-"))]
    failure_counts = {index: sum(record["failure_index"] == index for record in failures) for index in range(3)}
    stage_residue = sum(record.get("stage_residue", 0) for record in signals)
    survivors = sum(record.get("surviving_children", 0) for record in signals)
    descendants = sum("descendant" in record.get("member_states", []) for record in normal)
    require(stable_hashes == authority["acceptance"]["stable_result_hashes"], "stable hash count changed")
    print(
        "sprint12-batch-transaction-smoke: ok "
        f"cases={len(cases)} executions={len(cases) * repeats} stable_hashes={stable_hashes} "
        f"successful_batches={sum(record['outcome'] == 'success' for record in normal)} "
        f"failed_batches={len(failures)} failure_index_0={failure_counts[0]} "
        f"failure_index_1={failure_counts[1]} failure_index_2={failure_counts[2]} "
        f"process_tree_cases={len(CASE_FAMILIES['process_tree'])} descendant_failures={descendants} "
        f"signals={len(signals)} stage_residue={stage_residue} survivors={survivors} "
        f"fd_growth={fd_growth} timing_claims=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PilotError, CLEANUP.CleanupError, OSError, subprocess.SubprocessError,
            json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"sprint12-batch-transaction-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
