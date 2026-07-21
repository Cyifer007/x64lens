#!/usr/bin/env python3
"""Validate the Sprint 11 diagnostic runner's provenance and failure contracts."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks/scripts/diagnostic-runner.py"


class SmokeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(spec: Path, output_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--spec", str(spec), "--output-root", str(output_root)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )


def write_spec(path: Path, *, campaign_id: str, tool: Path, target: Path, conditions: list[dict[str, object]], warmups: int, timeout: float) -> None:
    value = {
        "schema_version": 1,
        "campaign_id": campaign_id,
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "warmup_runs": warmups,
        "measured_runs": 2 if warmups else 1,
        "timeout_seconds": timeout,
        "order_policy": "alternating",
        "cache_policy": "warm" if warmups else "uncontrolled",
        "fail_campaign_on_error": True,
        "environment": {"FAKEBENCH_MARKER": "sprint11"},
        "timer_floor": {
            "probe": "/bin/true",
            "runs": 5,
            "threshold_multiplier": 2,
        },
        "tools": [
            {
                "id": "fakebench",
                "path": str(tool),
                "version": "1.0",
                "version_argv": ["{tool}", "version"],
            }
        ],
        "targets": [
            {
                "id": "fixture",
                "path": str(target),
                "license": "project-generated smoke fixture",
            }
        ],
        "conditions": conditions,
    }
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def assert_wait4_waited_descendant_scope() -> None:
    """Prove the Linux wait4 row includes helpers waited for by its child."""
    read_fd, write_fd = os.pipe()
    direct_pid = os.fork()
    if direct_pid == 0:
        os.close(read_fd)
        helper_pid = os.fork()
        if helper_pid == 0:
            allocation = bytearray(32 * 1024 * 1024)
            for offset in range(0, len(allocation), 4096):
                allocation[offset] = 1
            deadline = time.process_time() + 0.05
            value = 1
            while time.process_time() < deadline:
                value = (value * 1_664_525 + 1_013_904_223) & 0xFFFFFFFF
            os._exit(value & 0)

        waited, status = os.waitpid(helper_pid, 0)
        direct = resource.getrusage(resource.RUSAGE_SELF)
        children = resource.getrusage(resource.RUSAGE_CHILDREN)
        payload = {
            "helper_pid": waited,
            "helper_status": os.waitstatus_to_exitcode(status),
            "direct_cpu_s": direct.ru_utime + direct.ru_stime,
            "direct_maxrss_kb": direct.ru_maxrss,
            "waited_cpu_s": children.ru_utime + children.ru_stime,
            "waited_maxrss_kb": children.ru_maxrss,
        }
        os.write(write_fd, json.dumps(payload, sort_keys=True).encode())
        os.close(write_fd)
        os._exit(0)

    os.close(write_fd)
    waited, status, usage = os.wait4(direct_pid, 0)
    with os.fdopen(read_fd, "rb") as handle:
        payload = json.loads(handle.read())
    require(waited == direct_pid and os.waitstatus_to_exitcode(status) == 0, "wait4 scope probe child failed")
    require(payload["helper_status"] == 0, "wait4 scope probe helper failed")
    require(payload["waited_cpu_s"] >= 0.02, "wait4 scope probe helper CPU was too small")
    require(
        usage.ru_utime + usage.ru_stime >= payload["waited_cpu_s"] * 0.8,
        "wait4 usage omitted the helper CPU that the selected child waited for",
    )
    require(
        usage.ru_maxrss >= payload["waited_maxrss_kb"] > payload["direct_maxrss_kb"],
        "wait4 maximum RSS omitted the larger helper that the selected child waited for",
    )


def assert_spawn_interruption_cleanup(tmp: Path) -> None:
    """Deliver SIGINT after Popen returns but before execute_process registers it."""
    module_spec = importlib.util.spec_from_file_location("diagnostic_runner_spawn_probe", RUNNER)
    require(module_spec is not None and module_spec.loader is not None, "cannot load runner for spawn interruption probe")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    original_popen = module.subprocess.Popen
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)
    spawned: list[int] = []

    def interrupting_popen(*args: object, **kwargs: object) -> subprocess.Popen[bytes]:
        process = original_popen(*args, **kwargs)
        spawned.append(process.pid)
        os.kill(os.getpid(), signal.SIGINT)
        return process

    module.subprocess.Popen = interrupting_popen
    module.install_signal_handlers()
    try:
        try:
            module.execute_process(
                ["/bin/sleep", "30"],
                cwd=tmp / "spawn-interruption" / "work",
                stdout_path=tmp / "spawn-interruption" / "stdout.bin",
                stderr_path=tmp / "spawn-interruption" / "stderr.bin",
                timeout_seconds=31,
                environment={"LANG": "C", "LC_ALL": "C", "TZ": "UTC"},
            )
        except module.RunnerInterrupted:
            pass
        else:
            raise SmokeError("spawn-window SIGINT did not interrupt the measured process")
    finally:
        module.subprocess.Popen = original_popen
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTERM, original_sigterm)

    require(len(spawned) == 1, f"spawn interruption probe launched {len(spawned)} processes")
    require(not Path(f"/proc/{spawned[0]}").exists(), f"spawn-window child survived interruption: {spawned[0]}")


def assert_artifact_hashes(result: Path, rows: list[dict[str, str]]) -> None:
    for row in rows:
        for prefix in ("stdout", "stderr"):
            path = result / row[f"{prefix}_path"]
            require(path.is_file(), f"missing {prefix} artifact for {row['run_id']}")
            require(str(path.stat().st_size) == row[f"{prefix}_bytes"], f"{prefix} size mismatch for {row['run_id']}")
            require(sha256(path) == row[f"{prefix}_sha256"], f"{prefix} hash mismatch for {row['run_id']}")


def main() -> int:
    assert_wait4_waited_descendant_scope()
    platform_check = subprocess.run(
        [sys.executable, str(RUNNER), "--platform-check"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    require(
        platform_check.returncode == 0
        and "diagnostic-runner-platform-check: ok" in platform_check.stdout,
        f"diagnostic runner platform check failed: {platform_check.stderr}",
    )
    with tempfile.TemporaryDirectory(prefix="x64lens-diagnostic-runner-smoke-") as raw:
        tmp = Path(raw)
        assert_spawn_interruption_cleanup(tmp)
        tool = tmp / "fakebench.sh"
        target = tmp / "fixture.bin"
        target.write_bytes(b"controlled diagnostic target\n")
        tool.write_text(
            r"""#!/usr/bin/env python3
import json
import hashlib
import os
from pathlib import Path
import signal
import sys
import time

mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode == "version":
    print("fakebench 1.0")
    raise SystemExit(0)
if mode in {"gadgets", "analyze"}:
    with open(sys.argv[2], "rb") as handle:
        handle.read()
    time.sleep(0.01)
    report = {
        "schema_version": "0.2.0",
        "tool": "x64lens",
        "tool_version": "1.0",
        "report_type": "analysis",
        "command": mode,
        "analysis": {
            "complete": True,
            "max_depth": 4,
            "candidate_capacity": 4096,
            "candidate_count": 1,
            "candidate_truncated": False,
            "candidate_dropped_count": 0,
            "candidate_dropped_count_known": True,
            "regions_scanned": 1,
            "regions_total": 1,
        },
        "counts": {
            "raw_candidate_count": 1,
            "exact_pattern_count": 1,
            "semantic_candidate_count": 1,
            "unknown_candidate_count": 0,
            "scored_candidate_count": 1,
        },
        "gadgets": [{}],
        "limitations": ["controlled smoke report"],
    }
    json.dump(report, sys.stdout, separators=(",", ":"))
    print()
    raise SystemExit(0)
if mode == "slow":
    with open(sys.argv[2], "rb") as handle:
        handle.read()
    time.sleep(0.5)
    raise SystemExit(0)
if mode == "symlink":
    os.symlink(sys.argv[2], "unsafe-result-link")
    raise SystemExit(0)
if mode == "mutate-target":
    os.chmod(sys.argv[2], 0o644)
    with open(sys.argv[2], "wb") as handle:
        handle.write(b"mutated retained target\\n")
    raise SystemExit(0)
if mode == "mutate-retained-restore":
    retained = Path.cwd().parents[2] / "inputs" / "targets" / "fixture"
    original = retained.read_bytes()
    try:
        os.chmod(retained, 0o644)
        retained.write_bytes(b"transient altered target\\n")
        measured = Path(sys.argv[2]).read_bytes()
    finally:
        retained.write_bytes(original)
        os.chmod(retained, 0o444)
    print(hashlib.sha256(measured).hexdigest())
    raise SystemExit(0 if measured == original else 12)
if mode == "mutate-version-artifact":
    artifact = Path.cwd().parents[2] / "inputs" / "versions" / "fakebench" / "stdout.bin"
    os.chmod(artifact, 0o644)
    artifact.write_bytes(b"corrupted version evidence\\n")
    raise SystemExit(0)
if mode == "mutate-timer-artifact":
    artifact = Path.cwd().parents[2] / "timer-floor.json"
    os.chmod(artifact, 0o644)
    artifact.write_text("{}\\n", encoding="utf-8")
    raise SystemExit(0)
if mode == "mutate-prior-output":
    stage = Path.cwd().parents[2]
    current_run = Path.cwd().parent.name
    prior = [
        path for path in sorted((stage / "outputs").glob("*/stdout.bin"))
        if path.parent.name != current_run
    ]
    if not prior:
        raise SystemExit(13)
    os.chmod(prior[0], 0o644)
    prior[0].write_bytes(b"corrupted prior row evidence\\n")
    raise SystemExit(0)
if mode == "replace-own-stdout":
    artifact = Path.cwd().parent / "stdout.bin"
    artifact.unlink()
    artifact.symlink_to("/dev/null")
    raise SystemExit(0)
if mode == "fail":
    print("intentional failure", file=sys.stderr)
    raise SystemExit(7)
if mode == "timeout":
    descendant = os.fork()
    if descendant == 0:
        os.setsid()
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        while True:
            time.sleep(1)
    print(f"descendant_pid={descendant}", file=sys.stderr, flush=True)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(1)
print(f"unsupported mode: {mode}", file=sys.stderr)
raise SystemExit(9)
""",
            encoding="utf-8",
        )
        tool.chmod(0o755)

        success_spec = tmp / "success.json"
        success_root = tmp / "success-results"
        success_conditions = [
            {
                "id": "gadget-json",
                "task_scope": "gadget_report",
                "profile_id": "core-1w",
                "worker_count": 1,
                "tool": "fakebench",
                "target": "fixture",
                "argv": ["{tool}", "gadgets", "{target}"],
                "extractor": "x64lens_json_0_2",
                "expected_report_command": "gadgets",
                "output_scope": "fake schema 0.2 gadget report",
            },
            {
                "id": "analysis-json",
                "task_scope": "integrated_analysis",
                "profile_id": "core-1w",
                "worker_count": 1,
                "tool": "fakebench",
                "target": "fixture",
                "argv": ["{tool}", "analyze", "{target}"],
                "extractor": "x64lens_json_0_2",
                "expected_report_command": "analyze",
                "output_scope": "fake schema 0.2 integrated report",
            },
        ]
        write_spec(
            success_spec,
            campaign_id="diagnostic-success",
            tool=tool,
            target=target,
            conditions=success_conditions,
            warmups=1,
            timeout=2.0,
        )
        accepted = run(success_spec, success_root)
        require(accepted.returncode == 0, f"success campaign failed: {accepted.stderr}")
        result = success_root / "diagnostic-success"
        require(result.is_dir(), "success result was not published")
        manifest = json.loads((result / "manifest.json").read_text(encoding="utf-8"))
        rows = read_rows(result / "rows.tsv")
        require(len(rows) == 6, f"success row count mismatch: {len(rows)}")
        require(manifest["evidence_class"] == "diagnostic", "evidence class mismatch")
        require(manifest["frozen"] is False and manifest["publication_eligible"] is False, "diagnostic claim boundary mismatch")
        require(manifest["runner"]["python_standard_library_only"] is True, "runner dependency contract missing")
        require(
            "write-sealed Linux memfd copies" in manifest["runner"]["execution_input_protection"],
            "runner sealed-input policy missing",
        )
        require(
            "rechecked after the final measured child exits"
            in manifest["policies"]["retained_artifact_identity_reconciliation"],
            "retained-artifact reconciliation policy missing",
        )
        resource_scope = manifest["runner"]["resource_scope"]
        require(
            "including descendants that child waited for" in resource_scope
            and "descendants reaped separately by the runner are excluded" in resource_scope,
            "wait4 resource boundary missing",
        )
        require(manifest["outcomes"]["failure_row_count"] == 0, "success manifest recorded failures")
        require((result / "timer-floor.json").is_file(), "timer floor artifact missing")
        require((result / manifest["runner"]["snapshot_path"]).is_file(), "runner snapshot missing")
        require(sha256(result / manifest["runner"]["snapshot_path"]) == manifest["runner"]["sha256"], "runner snapshot hash mismatch")
        require((result / manifest["spec"]["snapshot_path"]).is_file(), "spec snapshot missing")
        require(sha256(result / manifest["spec"]["snapshot_path"]) == manifest["spec"]["sha256"], "spec snapshot hash mismatch")
        require(len(json.loads((result / "timer-floor.json").read_text(encoding="utf-8"))["samples"]) == 5, "timer floor sample count mismatch")
        require(all(row["outcome"] == "success" for row in rows), "success campaign contains failed rows")
        require(all(row["raw_candidate_count"] == "1" for row in rows), "extractor counts missing")
        measured_order = [row["condition_id"] for row in rows if row["phase"] == "measured"]
        require(measured_order == ["gadget-json", "analysis-json", "analysis-json", "gadget-json"], f"alternating order mismatch: {measured_order}")
        for row in rows:
            included = row["included_in_primary_summary"] == "true"
            if row["phase"] == "warmup":
                require(not included and row["summary_exclusion_reason"] == "warmup", f"warmup summary policy mismatch: {row['run_id']}")
            elif row["timing_class"] == "below_reliable_single_process_floor":
                require(not included and row["summary_exclusion_reason"] == "below_timer_floor", f"timer-floor summary policy mismatch: {row['run_id']}")
            else:
                require(included and row["summary_exclusion_reason"] == "", f"measured summary policy mismatch: {row['run_id']}")
        require(
            manifest["outcomes"]["primary_summary_row_count"]
            == sum(row["included_in_primary_summary"] == "true" for row in rows),
            "primary summary count mismatch",
        )
        assert_artifact_hashes(result, rows)
        require((result / "inputs/tools/fakebench").is_file(), "tool snapshot missing")
        require((result / "inputs/targets/fixture").is_file(), "target snapshot missing")
        require(sha256(result / "inputs/tools/fakebench") == sha256(tool), "tool snapshot hash mismatch")
        require(sha256(result / "inputs/targets/fixture") == sha256(target), "target snapshot hash mismatch")
        execution_records = [*manifest["tools"], *manifest["targets"], manifest["timer_floor_probe"]]
        for record in execution_records:
            require(record["execution_protection"] == "linux_memfd_write_sealed", "sealed execution protection missing")
            require(record["execution_sha256"] == record["sha256"], "sealed execution hash mismatch")
            require(record["execution_size_bytes"] == record["size_bytes"], "sealed execution size mismatch")
            require(
                record["execution_seals"] == ["seal", "shrink", "grow", "write"],
                "sealed execution seal inventory mismatch",
            )
            require("execution_absolute" not in record and "execution_fd" not in record, "runtime execution handle leaked")
        for record in [*manifest["tools"], manifest["timer_floor_probe"]]:
            require(
                record["execution_memfd_creation"] in {"explicit_mfd_exec", "legacy_implicit_exec"},
                "executable memfd creation policy missing",
            )
        require(
            all(record["execution_memfd_creation"] == "nonexecutable" for record in manifest["targets"]),
            "target memfd execution policy mismatch",
        )
        require(not list(success_root.glob(".*.staging-*")), "success staging directory leaked")

        manifest_hash = sha256(result / "manifest.json")
        duplicate = run(success_spec, success_root)
        require(duplicate.returncode == 2, "existing campaign result was overwritten or accepted")
        require(sha256(result / "manifest.json") == manifest_hash, "existing campaign changed after overwrite rejection")

        failure_spec = tmp / "failure.json"
        failure_root = tmp / "failure-results"
        failure_conditions = [
            {
                "id": "nonzero",
                "task_scope": "baseline_gadget_report",
                "profile_id": "core-1w",
                "worker_count": 1,
                "tool": "fakebench",
                "target": "fixture",
                "argv": ["{tool}", "fail", "{target}"],
                "extractor": "none",
                "output_scope": "intentional nonzero process",
            },
            {
                "id": "timeout",
                "task_scope": "baseline_gadget_report",
                "profile_id": "core-1w",
                "worker_count": 1,
                "tool": "fakebench",
                "target": "fixture",
                "argv": ["{tool}", "timeout", "{target}"],
                "extractor": "none",
                "output_scope": "intentional timeout with descendant",
            },
        ]
        write_spec(
            failure_spec,
            campaign_id="diagnostic-failure",
            tool=tool,
            target=target,
            conditions=failure_conditions,
            warmups=0,
            timeout=0.2,
        )
        failed = run(failure_spec, failure_root)
        require(failed.returncode == 1, f"failed campaign did not publish with failure exit: {failed.returncode} {failed.stderr}")
        failed_result = failure_root / "diagnostic-failure"
        require(failed_result.is_dir(), "failed campaign evidence was discarded")
        failed_rows = read_rows(failed_result / "rows.tsv")
        require(len(failed_rows) == 2, f"failed row count mismatch: {len(failed_rows)}")
        outcomes = {row["condition_id"]: row for row in failed_rows}
        require(outcomes["nonzero"]["process_outcome"] == "nonzero_exit", "nonzero process was not retained")
        require(outcomes["nonzero"]["exit_code"] == "7", "nonzero exit code mismatch")
        require(outcomes["timeout"]["process_outcome"] == "timeout", "timeout process was not retained")
        require(outcomes["timeout"]["timed_out"] == "true", "timeout flag missing")
        require(outcomes["timeout"]["descendant_cleanup_required"] == "true", "escaped descendant cleanup was not recorded")
        require(int(outcomes["timeout"]["descendants_reaped"]) >= 1, "escaped descendant was not reaped")
        timeout_stderr = (failed_result / outcomes["timeout"]["stderr_path"]).read_text(encoding="utf-8", errors="replace")
        match = re.search(r"descendant_pid=(\d+)", timeout_stderr)
        require(match is not None, f"timeout descendant identity missing: {timeout_stderr!r}")
        descendant_pid = int(match.group(1))
        require(not Path(f"/proc/{descendant_pid}").exists(), f"timeout descendant survived cleanup: {descendant_pid}")
        failed_manifest = json.loads((failed_result / "manifest.json").read_text(encoding="utf-8"))
        require(failed_manifest["outcomes"]["failure_row_count"] == 2, "failed rows were not counted")
        require(not list(failure_root.glob(".*.staging-*")), "failure staging directory leaked")
        assert_artifact_hashes(failed_result, failed_rows)

        invalid_spec = tmp / "invalid-publication.json"
        invalid_value = json.loads(success_spec.read_text(encoding="utf-8"))
        invalid_value["campaign_id"] = "diagnostic-invalid-publication"
        invalid_value["publication_eligible"] = True
        invalid_spec.write_text(json.dumps(invalid_value, indent=2) + "\n", encoding="utf-8")
        invalid_root = tmp / "invalid-results"
        invalid = run(invalid_spec, invalid_root)
        require(invalid.returncode == 2, "publication-eligible diagnostic spec was accepted")
        require(not (invalid_root / "diagnostic-invalid-publication").exists(), "invalid campaign published evidence")
        require(not list(invalid_root.glob(".*.staging-*")), "invalid campaign leaked staging state")

        omitted_spec = tmp / "invalid-omitted-publication.json"
        omitted_value = json.loads(success_spec.read_text(encoding="utf-8"))
        omitted_value["campaign_id"] = "diagnostic-omitted-publication"
        omitted_value.pop("publication_eligible")
        omitted_spec.write_text(json.dumps(omitted_value, indent=2) + "\n", encoding="utf-8")
        omitted_root = tmp / "omitted-publication-results"
        omitted = run(omitted_spec, omitted_root)
        require(omitted.returncode == 2, "diagnostic spec without publication_eligible was accepted")
        require(
            "must declare publication_eligible=false" in omitted.stderr,
            f"unexpected omitted-publication diagnostic: {omitted.stderr}",
        )
        require(not (omitted_root / "diagnostic-omitted-publication").exists(), "omitted-publication campaign published evidence")
        require(not list(omitted_root.glob(".*.staging-*")), "omitted-publication campaign leaked staging state")

        reserved_spec = tmp / "invalid-reserved-environment.json"
        reserved_value = json.loads(success_spec.read_text(encoding="utf-8"))
        reserved_value["campaign_id"] = "diagnostic-invalid-environment"
        reserved_value["environment"]["HOME"] = "/tmp/not-allowed"
        reserved_spec.write_text(json.dumps(reserved_value, indent=2) + "\n", encoding="utf-8")
        reserved_root = tmp / "reserved-results"
        reserved = run(reserved_spec, reserved_root)
        require(reserved.returncode == 2, "reserved child environment override was accepted")
        require("environment key is reserved" in reserved.stderr, f"unexpected reserved-environment diagnostic: {reserved.stderr}")
        require(not (reserved_root / "diagnostic-invalid-environment").exists(), "reserved-environment campaign was published")

        mutation_spec = tmp / "mutation.json"
        mutation_root = tmp / "mutation-results"
        mutation_conditions = [
            {
                "id": "slow",
                "task_scope": "baseline_gadget_report",
                "profile_id": "core-1w",
                "worker_count": 1,
                "tool": "fakebench",
                "target": "fixture",
                "argv": ["{tool}", "slow", "{target}"],
                "extractor": "none",
                "output_scope": "spec source mutation probe",
            }
        ]
        write_spec(
            mutation_spec,
            campaign_id="diagnostic-spec-mutation",
            tool=tool,
            target=target,
            conditions=mutation_conditions,
            warmups=0,
            timeout=2.0,
        )
        mutation_process = subprocess.Popen(
            [sys.executable, str(RUNNER), "--spec", str(mutation_spec), "--output-root", str(mutation_root)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        snapshot_seen = False
        for _ in range(500):
            if list(mutation_root.glob(".*.staging-*/inputs/spec/campaign.json")):
                snapshot_seen = True
                break
            if mutation_process.poll() is not None:
                break
            time.sleep(0.01)
        require(snapshot_seen, "spec mutation probe did not observe the retained specification")
        mutation_spec.write_text(mutation_spec.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        mutation_stdout, mutation_stderr = mutation_process.communicate(timeout=10)
        require(mutation_process.returncode == 2, f"campaign accepted source spec mutation: {mutation_stdout} {mutation_stderr}")
        require("campaign spec changed during execution" in mutation_stderr, f"unexpected spec mutation diagnostic: {mutation_stderr}")
        require(not (mutation_root / "diagnostic-spec-mutation").exists(), "mutated-spec campaign was published")
        require(not list(mutation_root.glob(".*.staging-*")), "mutated-spec campaign leaked staging state")

        snapshot_spec = tmp / "snapshot-mutation.json"
        snapshot_root = tmp / "snapshot-mutation-results"
        snapshot_conditions = [
            {
                "id": "snapshot-mutation",
                "task_scope": "baseline_gadget_report",
                "profile_id": "core-1w",
                "worker_count": 1,
                "tool": "fakebench",
                "target": "fixture",
                "argv": ["{tool}", "mutate-target", "{target}"],
                "extractor": "none",
                "output_scope": "retained target snapshot mutation probe",
            }
        ]
        write_spec(
            snapshot_spec,
            campaign_id="diagnostic-snapshot-mutation",
            tool=tool,
            target=target,
            conditions=snapshot_conditions,
            warmups=0,
            timeout=2.0,
        )
        snapshot_mutation = run(snapshot_spec, snapshot_root)
        require(snapshot_mutation.returncode == 2, "campaign accepted a retained target snapshot mutation")
        require(
            "target fixture sealed execution copy mode changed during execution" in snapshot_mutation.stderr,
            f"unexpected snapshot-mutation diagnostic: {snapshot_mutation.stderr}",
        )
        require(not (snapshot_root / "diagnostic-snapshot-mutation").exists(), "mutated-snapshot campaign was published")
        require(not list(snapshot_root.glob(".*.staging-*")), "mutated-snapshot campaign leaked staging state")

        transient_spec = tmp / "transient-retained-mutation.json"
        transient_root = tmp / "transient-retained-mutation-results"
        transient_conditions = [
            {
                "id": "transient-retained-mutation",
                "task_scope": "baseline_gadget_report",
                "profile_id": "core-1w",
                "worker_count": 1,
                "tool": "fakebench",
                "target": "fixture",
                "argv": ["{tool}", "mutate-retained-restore", "{target}"],
                "extractor": "none",
                "output_scope": "sealed execution copy transient-mutation probe",
            }
        ]
        write_spec(
            transient_spec,
            campaign_id="diagnostic-transient-retained-mutation",
            tool=tool,
            target=target,
            conditions=transient_conditions,
            warmups=0,
            timeout=2.0,
        )
        transient = run(transient_spec, transient_root)
        require(transient.returncode == 0, f"sealed transient-mutation campaign failed: {transient.stderr}")
        transient_result = transient_root / "diagnostic-transient-retained-mutation"
        transient_rows = read_rows(transient_result / "rows.tsv")
        require(len(transient_rows) == 1 and transient_rows[0]["outcome"] == "success", "sealed transient row failed")
        transient_stdout = (
            transient_result / transient_rows[0]["stdout_path"]
        ).read_text(encoding="utf-8").strip()
        require(transient_stdout == sha256(target), "measured command consumed transient retained-snapshot bytes")
        transient_manifest = json.loads((transient_result / "manifest.json").read_text(encoding="utf-8"))
        retained_target = transient_result / transient_manifest["targets"][0]["snapshot_path"]
        require(
            sha256(retained_target) == transient_manifest["targets"][0]["sha256"] == sha256(target),
            "transient mutation changed the published retained target",
        )
        require(not list(transient_root.glob(".*.staging-*")), "transient-mutation campaign leaked staging state")

        for artifact_mode, campaign_id, expected_error in (
            (
                "mutate-version-artifact",
                "diagnostic-version-artifact-mutation",
                "tool fakebench version stdout changed after capture",
            ),
            (
                "mutate-timer-artifact",
                "diagnostic-timer-artifact-mutation",
                "timer floor artifact changed after capture",
            ),
            (
                "replace-own-stdout",
                "diagnostic-stdout-replacement",
                "measured stdout path is not a regular file",
            ),
        ):
            artifact_spec = tmp / f"{artifact_mode}.json"
            artifact_root = tmp / f"{artifact_mode}-results"
            write_spec(
                artifact_spec,
                campaign_id=campaign_id,
                tool=tool,
                target=target,
                conditions=[
                    {
                        "id": artifact_mode,
                        "task_scope": "baseline_gadget_report",
                        "profile_id": "core-1w",
                        "worker_count": 1,
                        "tool": "fakebench",
                        "target": "fixture",
                        "argv": ["{tool}", artifact_mode, "{target}"],
                        "extractor": "none",
                        "output_scope": "retained artifact mutation probe",
                    }
                ],
                warmups=0,
                timeout=2.0,
            )
            artifact_mutation = run(artifact_spec, artifact_root)
            require(artifact_mutation.returncode == 2, f"{artifact_mode} campaign was accepted")
            require(expected_error in artifact_mutation.stderr, f"unexpected {artifact_mode} diagnostic: {artifact_mutation.stderr}")
            require(not (artifact_root / campaign_id).exists(), f"{artifact_mode} campaign was published")
            require(not list(artifact_root.glob(".*.staging-*")), f"{artifact_mode} campaign leaked staging state")

        prior_output_spec = tmp / "prior-output-mutation.json"
        prior_output_root = tmp / "prior-output-mutation-results"
        write_spec(
            prior_output_spec,
            campaign_id="diagnostic-prior-output-mutation",
            tool=tool,
            target=target,
            conditions=[
                {
                    "id": "prior",
                    "task_scope": "baseline_gadget_report",
                    "profile_id": "core-1w",
                    "worker_count": 1,
                    "tool": "fakebench",
                    "target": "fixture",
                    "argv": ["{tool}", "slow", "{target}"],
                    "extractor": "none",
                    "output_scope": "prior retained output",
                },
                {
                    "id": "mutate-prior",
                    "task_scope": "baseline_gadget_report",
                    "profile_id": "core-1w",
                    "worker_count": 1,
                    "tool": "fakebench",
                    "target": "fixture",
                    "argv": ["{tool}", "mutate-prior-output", "{target}"],
                    "extractor": "none",
                    "output_scope": "prior output mutation probe",
                },
            ],
            warmups=0,
            timeout=2.0,
        )
        prior_output_mutation = run(prior_output_spec, prior_output_root)
        require(prior_output_mutation.returncode == 2, "campaign accepted a mutated prior row artifact")
        require(
            "row measured-001-01-prior stdout changed after capture" in prior_output_mutation.stderr,
            f"unexpected prior-output mutation diagnostic: {prior_output_mutation.stderr}",
        )
        require(
            not (prior_output_root / "diagnostic-prior-output-mutation").exists(),
            "mutated prior-output campaign was published",
        )
        require(not list(prior_output_root.glob(".*.staging-*")), "prior-output mutation leaked staging state")

        unsafe_spec = tmp / "unsafe-artifact.json"
        unsafe_root = tmp / "unsafe-artifact-results"
        unsafe_conditions = [
            {
                "id": "unsafe-artifact",
                "task_scope": "baseline_gadget_report",
                "profile_id": "core-1w",
                "worker_count": 1,
                "tool": "fakebench",
                "target": "fixture",
                "argv": ["{tool}", "symlink", "{target}"],
                "extractor": "none",
                "output_scope": "unsafe staging-artifact probe",
            }
        ]
        write_spec(
            unsafe_spec,
            campaign_id="diagnostic-unsafe-artifact",
            tool=tool,
            target=target,
            conditions=unsafe_conditions,
            warmups=0,
            timeout=2.0,
        )
        unsafe = run(unsafe_spec, unsafe_root)
        require(unsafe.returncode == 2, "campaign with a symlink artifact was accepted")
        require("non-regular artifact" in unsafe.stderr, f"unexpected unsafe-artifact diagnostic: {unsafe.stderr}")
        require(not (unsafe_root / "diagnostic-unsafe-artifact").exists(), "unsafe-artifact campaign was published")
        require(not list(unsafe_root.glob(".*.staging-*")), "unsafe-artifact campaign leaked staging state")

    print("diagnostic-runner-smoke: ok success_rows=6 failure_rows=2 overwrite_rejected=1 descendants_cleaned=1 invalid_specs_rejected=2 source_mutations_rejected=1 unsafe_artifacts_rejected=1")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, SmokeError, subprocess.SubprocessError) as exc:
        print(f"diagnostic-runner-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
