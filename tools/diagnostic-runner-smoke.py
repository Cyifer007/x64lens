#!/usr/bin/env python3
"""Validate the Sprint 11 diagnostic runner's provenance and failure contracts."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
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


def assert_artifact_hashes(result: Path, rows: list[dict[str, str]]) -> None:
    for row in rows:
        for prefix in ("stdout", "stderr"):
            path = result / row[f"{prefix}_path"]
            require(path.is_file(), f"missing {prefix} artifact for {row['run_id']}")
            require(str(path.stat().st_size) == row[f"{prefix}_bytes"], f"{prefix} size mismatch for {row['run_id']}")
            require(sha256(path) == row[f"{prefix}_sha256"], f"{prefix} hash mismatch for {row['run_id']}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-diagnostic-runner-smoke-") as raw:
        tmp = Path(raw)
        tool = tmp / "fakebench.sh"
        target = tmp / "fixture.bin"
        target.write_bytes(b"controlled diagnostic target\n")
        tool.write_text(
            r"""#!/usr/bin/env python3
import json
import os
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
        require("direct measured child" in manifest["runner"]["resource_scope"], "direct-child resource boundary missing")
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
