#!/usr/bin/env python3
"""Validate bounded whole-batch transaction semantics before timing use.

This is a development oracle, not a benchmark. It deliberately excludes wall
clock values from its retained result identity and never divides a whole-batch
measurement into a claimed single-invocation latency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any

SCRIPT = Path(__file__).resolve()
OUTPUT_LIMIT_TOKEN = b"x" * 4097


class PilotError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PilotError(message)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_authority(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value.get("schema_id") == "sprint12-batch-transaction-pilot-v1", "wrong authority schema")
    require(value.get("evidence_class") == "diagnostic", "authority must remain diagnostic")
    require(value.get("frozen") is False, "authority must remain unfrozen")
    require(value.get("publication_eligible") is False, "authority must remain publication-ineligible")
    require(value.get("divide_batch_elapsed_into_single_run_latency") is False, "divided latency is prohibited")
    families = value.get("case_families")
    require(isinstance(families, dict), "case families missing")
    all_cases = [case for family in families.values() for case in family]
    require(len(all_cases) == 27 and len(set(all_cases)) == 27, "authority must define 27 unique cases")
    acceptance = value.get("acceptance")
    require(isinstance(acceptance, dict), "acceptance missing")
    require(acceptance.get("case_count") == 27, "wrong case count")
    require(acceptance.get("execution_count") == 81, "wrong execution count")
    require(value.get("repeat_count") == 3, "repeat count must be three")
    return value


def child(mode: str) -> int:
    if mode == "success":
        sys.stdout.write("ok\n")
        return 0
    if mode == "nonzero":
        sys.stderr.write("controlled nonzero\n")
        return 17
    if mode == "timeout" or mode == "block":
        time.sleep(30)
        return 0
    if mode == "stdout-limit":
        os.write(1, OUTPUT_LIMIT_TOKEN)
        return 0
    if mode == "stderr-limit":
        os.write(2, OUTPUT_LIMIT_TOKEN)
        return 0
    raise PilotError(f"unknown child mode: {mode}")


def terminate_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def run_member(mode: str, timeout: float, stdout_limit: int, stderr_limit: int) -> tuple[str, int | None]:
    commands = {
        "success": ["/bin/sh", "-c", "printf 'ok\n'"],
        "nonzero": ["/bin/sh", "-c", "printf 'controlled nonzero\n' >&2; exit 17"],
        "timeout": ["/bin/sh", "-c", "sleep 30"],
        "block": ["/bin/sh", "-c", "sleep 30"],
        "stdout-limit": ["/usr/bin/printf", "%s", "x" * 4097],
        "stderr-limit": ["/bin/sh", "-c", "yes x | tr -d '\n' | head -c 4097 >&2"],
    }
    require(mode in commands, f"unknown member mode: {mode}")
    process = subprocess.Popen(
        commands[mode],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_tree(process)
        return "timeout", None
    if len(stdout) > stdout_limit:
        return "stdout_limit", process.returncode
    if len(stderr) > stderr_limit:
        return "stderr_limit", process.returncode
    if process.returncode != 0:
        return "nonzero", process.returncode
    return "success", 0


def parse_normal_case(case: str) -> list[str]:
    if case == "empty":
        return []
    if case == "singleton-success":
        return ["success"]
    for mode, label in (("nonzero", "nonzero"), ("timeout", "timeout"), ("stdout-limit", "stdout-limit"), ("stderr-limit", "stderr-limit")):
        if case == f"singleton-{label}":
            return [mode]
    if case == "three-all-success":
        return ["success"] * 3
    positions = {"first": 0, "middle": 1, "final": 2}
    for label, mode in (("nonzero", "nonzero"), ("timeout", "timeout"), ("stdout-limit", "stdout-limit"), ("stderr-limit", "stderr-limit")):
        for position, index in positions.items():
            if case == f"three-{label}-{position}":
                modes = ["success"] * 3
                modes[index] = mode
                return modes
    raise PilotError(f"unknown normal case: {case}")


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
    failure_index: int | None = None
    try:
        for index, mode in enumerate(modes):
            state, code = run_member(
                mode,
                float(authority["member_timeout_seconds"]),
                int(authority["maximum_stdout_bytes"]),
                int(authority["maximum_stderr_bytes"]),
            )
            states[index] = state
            codes[index] = code
            if state != "success":
                failure_index = index
                break
        successful = failure_index is None
        record = {
            "case": case,
            "member_modes": modes,
            "member_states": states,
            "member_exit_codes": codes,
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
            require(run_member("success", 5.0, 4096, 4096)[0] == "success", "first member failed")
            (sync / "ready").write_text("ready\n")
        elif barrier == "member-active":
            child_process = subprocess.Popen(
                ["/bin/sh", "-c", "sleep 30"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            (sync / "child.pid").write_text(f"{child_process.pid}\n")
            (sync / "ready").write_text("ready\n")
        elif barrier == "after-final":
            for _ in range(3):
                require(run_member("success", 5.0, 4096, 4096)[0] == "success", "member failed")
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
        process.communicate(timeout=10)
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
    for case in cases:
        outputs = []
        for _ in range(repeats):
            output = run_signal_case(case) if case.startswith(("sigint-", "sigterm-")) else normal_transaction(case, authority)
            outputs.append(digest(output))
            stable_hashes += 1
        require(len(set(outputs)) == 1, f"nondeterministic case result: {case}")
    after_fds = fd_count()
    require(after_fds == before_fds, f"file descriptor growth: {before_fds} -> {after_fds}")
    print(
        "sprint12-batch-transaction-smoke: ok "
        f"cases={len(cases)} executions={len(cases) * repeats} stable_hashes={stable_hashes} "
        "failure_positions=13 signals=8 stage_residue=0 survivors=0 fd_growth=0 timing_claims=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PilotError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"sprint12-batch-transaction-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
