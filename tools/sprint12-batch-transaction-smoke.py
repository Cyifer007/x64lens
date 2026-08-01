#!/usr/bin/env python3
"""Validate bounded whole-batch transaction semantics before timing use.

This development oracle executes a versioned, outcome-complete case authority.
It streams child output into fixed counters, terminates the whole child process
group as soon as either stream exceeds its cap, compares every result with the
case-specific expected record, and publishes only complete successful batches.
It records no wall-clock value and never divides batch elapsed time into a
single-invocation latency claim.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

SCRIPT = Path(__file__).resolve()
EXPECTED_AUTHORITY_SHA256 = "12730c450a1d0eb8c5a9401143ffcbbd76ad8db265abbb9a4569094a3a09c0e4"

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


class PilotError(RuntimeError):
    """Raised when the authority, transaction, or cleanup contract is violated."""


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PilotError(message)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_normal_case(case: str) -> list[str]:
    if case == "empty":
        return []
    if case == "singleton-success":
        return ["success"]
    for mode in ("nonzero", "timeout", "stdout-limit", "stderr-limit"):
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
    normal = [record for case, record in records.items() if not case.startswith(("sigint-", "sigterm-"))]
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
        "signal_case_count": len(CASE_FAMILIES["signals"]),
        "failure_positions_exact": True,
        "unstarted_members_explicit": True,
        "failed_batches_unpublished": True,
        "successful_batches_complete": True,
        "interrupt_exit_codes": {"SIGINT": 130, "SIGTERM": 143},
        "streaming_output_cap": True,
        "maximum_retained_bytes_per_overflow_stream": 4097,
        "stage_residue": 0,
        "surviving_children": 0,
        "file_descriptor_growth": 0,
        "timing_claims": 0,
    }


def read_authority(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
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
        "case_expectations",
        "acceptance",
    }
    require(set(value) == expected_keys, "authority top-level fields changed")
    require(value["schema_id"] == "sprint12-batch-transaction-pilot-v2", "wrong authority schema")
    require(value["evidence_class"] == "diagnostic", "authority must remain diagnostic")
    require(value["frozen"] is False, "authority must remain unfrozen")
    require(value["publication_eligible"] is False, "authority must remain publication-ineligible")
    require(
        value["purpose"]
        == "Validate exact whole-batch execution, streaming output limits, cleanup, and publication semantics before throughput qualification.",
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
    require(value["case_families"] == CASE_FAMILIES, "case families changed")
    require(value["case_expectations"] == expected_case_records(), "case expectations changed")
    require(value["acceptance"] == expected_acceptance(3), "acceptance semantics changed")
    require(hashlib.sha256(canonical(value)).hexdigest() == EXPECTED_AUTHORITY_SHA256,
            "authority canonical SHA-256 changed")
    return value


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
    raise PilotError(f"unknown child mode: {mode}")


def terminate_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired as exc:
        raise PilotError(f"child process group did not terminate: {process.pid}") from exc


def run_command(
    command: Sequence[str],
    *,
    timeout: float,
    stdout_limit: int,
    stderr_limit: int,
) -> MemberResult:
    """Run one member with streaming limit enforcement and bounded retention."""
    require(timeout > 0, "timeout must be positive")
    require(stdout_limit >= 0 and stderr_limit >= 0, "output limits must be nonnegative")
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
            if process.poll() is None and time.monotonic() >= deadline:
                classification = "timeout"
                terminate_tree(process)
                break
            wait = 0.05
            if process.poll() is None:
                wait = max(0.0, min(wait, deadline - time.monotonic()))
            events = selector.select(wait)
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
        if classification == "timeout":
            return MemberResult("timeout", None, counts["stdout"], counts["stderr"])
        if classification == "stdout_limit":
            return MemberResult("stdout_limit", None, counts["stdout"], counts["stderr"])
        if classification == "stderr_limit":
            return MemberResult("stderr_limit", None, counts["stdout"], counts["stderr"])
        require(process.returncode is not None, "child return code unavailable")
        state = "success" if process.returncode == 0 else "nonzero"
        return MemberResult(state, process.returncode, counts["stdout"], counts["stderr"])
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
        if process.poll() is None:
            terminate_tree(process)


def run_member(mode: str, timeout: float, stdout_limit: int, stderr_limit: int) -> MemberResult:
    commands = {
        "success": ["/bin/sh", "-c", "printf 'ok\n'"],
        "nonzero": ["/bin/sh", "-c", "printf 'controlled nonzero\n' >&2; exit 17"],
        "timeout": ["/bin/sh", "-c", "sleep 30"],
        "block": ["/bin/sh", "-c", "sleep 30"],
        "stdout-limit": ["/usr/bin/printf", "%s", "x" * 4097],
        "stderr-limit": ["/bin/sh", "-c", "yes x | tr -d '\\n' | head -c 4097 >&2"],
    }
    require(mode in commands, f"unknown member mode: {mode}")
    return run_command(
        commands[mode],
        timeout=timeout,
        stdout_limit=stdout_limit,
        stderr_limit=stderr_limit,
    )


def publish_complete(stage: Path, result: Path, record: dict[str, Any]) -> None:
    stage.mkdir(mode=0o700)
    payload = canonical(record)
    (stage / "result.json").write_bytes(payload)
    manifest = {"result.json": hashlib.sha256(payload).hexdigest()}
    (stage / "SHA256SUMS.json").write_bytes(canonical(manifest))
    os.rename(stage, result)
    require(result.is_dir() and not stage.exists(), "publication was not atomic")
    require((result / "result.json").read_bytes() == payload, "published result changed")
    require(json.loads((result / "SHA256SUMS.json").read_text()) == manifest, "published manifest changed")


def normal_transaction(case: str, authority: dict[str, Any]) -> dict[str, Any]:
    modes = parse_normal_case(case)
    root = Path(tempfile.mkdtemp(prefix="x64lens-batch-pilot-"))
    stage = root / "stage"
    result = root / "result"
    states = ["not_started"] * len(modes)
    codes: list[int | None] = [None] * len(modes)
    stdout_bytes = [0] * len(modes)
    stderr_bytes = [0] * len(modes)
    failure_index: int | None = None
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
            "published": successful,
        }
        if successful:
            publish_complete(stage, result, record)
        require(not stage.exists(), "staging residue remained")
        require(result.exists() == successful, "publication state disagrees with outcome")
        return record
    finally:
        shutil.rmtree(root, ignore_errors=False)


def signal_worker(case: str, sync: Path) -> int:
    signame, barrier = case.split("-", 1)
    signum = signal.SIGINT if signame == "sigint" else signal.SIGTERM
    root = sync / "transaction"
    stage = root / "stage"
    result = root / "result"
    child_process: subprocess.Popen[bytes] | None = None
    caught = 0

    def handler(received: int, _frame: object) -> None:
        nonlocal caught
        caught = received

    old = signal.signal(signum, handler)
    try:
        root.mkdir()
        stage.mkdir()
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
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(result, ignore_errors=True)
        shutil.rmtree(root, ignore_errors=True)


def run_signal_case(case: str) -> dict[str, Any]:
    sync = Path(tempfile.mkdtemp(prefix="x64lens-batch-signal-"))
    signame = case.split("-", 1)[0]
    signum = signal.SIGINT if signame == "sigint" else signal.SIGTERM
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), "--signal-worker", case, "--sync", str(sync)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 10
        while not (sync / "ready").exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.005)
        if not (sync / "ready").exists():
            stdout, stderr = process.communicate(timeout=2)
            raise PilotError(
                f"signal worker did not reach barrier: {case}; "
                f"exit={process.returncode} stdout={stdout[:200]!r} stderr={stderr[:400]!r}"
            )
        os.kill(process.pid, signum)
        stdout, stderr = process.communicate(timeout=10)
        require(not stdout and not stderr, f"signal worker emitted output for {case}")
        require(process.returncode == 128 + signum, f"wrong signal exit for {case}: {process.returncode}")
        transaction = sync / "transaction"
        require(not transaction.exists(), f"transaction residue remained for {case}")
        child_pid_file = sync / "child.pid"
        if child_pid_file.exists():
            pid = int(child_pid_file.read_text().strip())
            require(not Path(f"/proc/{pid}").exists(), f"child survived signal case: {pid}")
        return {
            "case": case,
            "signal": signal.Signals(signum).name,
            "exit_code": process.returncode,
            "published": False,
            "stage_residue": 0,
            "surviving_children": 0,
        }
    finally:
        if process.poll() is None:
            terminate_tree(process)
        shutil.rmtree(sync, ignore_errors=False)


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
    authority = read_authority(args.authority)
    cases = [case for family in authority["case_families"].values() for case in family]
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
    normal = [record for case, record in verified_records.items() if not case.startswith(("sigint-", "sigterm-"))]
    failures = [record for record in normal if record["outcome"] == "failed"]
    signals = [record for case, record in verified_records.items() if case.startswith(("sigint-", "sigterm-"))]
    failure_counts = {index: sum(record["failure_index"] == index for record in failures) for index in range(3)}
    stage_residue = sum(record.get("stage_residue", 0) for record in signals)
    survivors = sum(record.get("surviving_children", 0) for record in signals)
    require(stable_hashes == authority["acceptance"]["stable_result_hashes"], "stable hash count changed")
    print(
        "sprint12-batch-transaction-smoke: ok "
        f"cases={len(cases)} executions={len(cases) * repeats} stable_hashes={stable_hashes} "
        f"successful_batches={sum(record['outcome'] == 'success' for record in normal)} "
        f"failed_batches={len(failures)} failure_index_0={failure_counts[0]} "
        f"failure_index_1={failure_counts[1]} failure_index_2={failure_counts[2]} "
        f"signals={len(signals)} stage_residue={stage_residue} survivors={survivors} "
        f"fd_growth={fd_growth} timing_claims=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PilotError, OSError, subprocess.SubprocessError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"sprint12-batch-transaction-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
