#!/usr/bin/env python3
"""Validate the controlled Sprint 11 diagnostic campaign and command parity."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "benchmarks/scripts/diagnostic-runner.py"
SPEC = ROOT / "benchmarks/specs/sprint11-reference-diagnostic.json"
ANALYZER = ROOT / "build/x64lens"
TARGET = ROOT / "tests/bin/gadgets"
CAMPAIGN_ID = "s11-p055-reference-smoke"


class SmokeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_report(result: Path, row: dict[str, str]) -> dict[str, Any]:
    path = result / row["stdout_path"]
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SmokeError(f"cannot read report for {row['run_id']}: {exc}") from exc
    require(isinstance(report, dict), f"report is not an object: {row['run_id']}")
    return report


def normalized_report(report: dict[str, Any]) -> dict[str, Any]:
    value = dict(report)
    value.pop("command", None)
    return value


def main() -> int:
    require(RUNNER.is_file(), "diagnostic runner is missing")
    require(SPEC.is_file(), "reference diagnostic spec is missing")
    require(ANALYZER.is_file() and ANALYZER.stat().st_mode & 0o111, "built x64lens executable is missing")
    require(TARGET.is_file(), "controlled gadget fixture is missing")

    with tempfile.TemporaryDirectory(prefix="x64lens-s11-reference-smoke-") as raw:
        output_root = Path(raw) / "results"
        completed = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--spec",
                str(SPEC),
                "--output-root",
                str(output_root),
                "--campaign-id",
                CAMPAIGN_ID,
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=45,
        )
        require(completed.returncode == 0, f"reference campaign failed: {completed.stderr}")

        result = output_root / CAMPAIGN_ID
        require(result.is_dir(), "reference campaign was not published")
        manifest = json.loads((result / "manifest.json").read_text(encoding="utf-8"))
        rows = read_rows(result / "rows.tsv")
        require(len(rows) == 8, f"reference row count mismatch: {len(rows)}")
        require(sum(row["phase"] == "warmup" for row in rows) == 2, "warmup row count mismatch")
        require(sum(row["phase"] == "measured" for row in rows) == 6, "measured row count mismatch")
        require(all(row["outcome"] == "success" for row in rows), "reference campaign contains a failed row")
        require(all(row["analysis_complete"] == "true" for row in rows), "reference report is incomplete")
        require(all(row["raw_candidate_count"] == "11" for row in rows), "controlled raw count mismatch")
        require(all(row["exact_pattern_count"] == "11" for row in rows), "controlled exact count mismatch")
        require(all(row["semantic_candidate_count"] == "11" for row in rows), "controlled semantic count mismatch")
        require(all(row["unknown_candidate_count"] == "0" for row in rows), "controlled unknown count mismatch")
        require(all(row["scored_candidate_count"] == "11" for row in rows), "controlled score count mismatch")
        require(manifest["outcomes"]["row_count"] == 8, "manifest row count mismatch")
        require(manifest["outcomes"]["failure_row_count"] == 0, "manifest recorded a reference failure")
        resource_scope = manifest["runner"]["resource_scope"]
        require(
            "including descendants that child waited for" in resource_scope
            and "descendants reaped separately by the runner are excluded" in resource_scope,
            "wait4 resource boundary missing",
        )
        require(
            "write-sealed Linux memfd copies" in manifest["runner"]["execution_input_protection"],
            "sealed execution-input policy missing",
        )
        require(
            "rechecked after the final measured child exits"
            in manifest["policies"]["retained_artifact_identity_reconciliation"],
            "retained-artifact reconciliation policy missing",
        )
        require(sha256(result / manifest["runner"]["snapshot_path"]) == manifest["runner"]["sha256"], "runner snapshot identity mismatch")
        require(sha256(result / manifest["spec"]["snapshot_path"]) == manifest["spec"]["sha256"], "spec snapshot identity mismatch")

        tools = {item["id"]: item for item in manifest["tools"]}
        targets = {item["id"]: item for item in manifest["targets"]}
        execution_records = [*tools.values(), *targets.values(), manifest["timer_floor_probe"]]
        for record in execution_records:
            require(record["execution_sha256"] == record["sha256"], "sealed execution hash mismatch")
            require(record["execution_size_bytes"] == record["size_bytes"], "sealed execution size mismatch")
            require("execution_absolute" not in record and "execution_fd" not in record, "runtime execution handle leaked")
        for record in [*tools.values(), manifest["timer_floor_probe"]]:
            require(record["execution_protection"] == "linux_memfd_write_sealed", "executable sealed protection missing")
            require(record["execution_seals"] == ["seal", "shrink", "grow", "write"], "executable seal inventory mismatch")
            require(
                record["execution_memfd_creation"] in {"explicit_mfd_exec", "legacy_implicit_exec"},
                "executable memfd creation policy missing",
            )
        for record in targets.values():
            require(record["execution_protection"] == "linux_memfd_noexec_write_sealed", "target no-exec protection missing")
            require(record["execution_seals"] == ["seal", "shrink", "grow", "write", "exec"], "target seal inventory mismatch")
            require(record["execution_memfd_creation"] == "explicit_mfd_noexec_seal", "target memfd execution policy mismatch")
        require(tools["x64lens"]["sha256"] == sha256(ANALYZER), "analyzer snapshot hash mismatch")
        require(targets["controlled-gadgets"]["sha256"] == sha256(TARGET), "target snapshot hash mismatch")
        version_command = tools["x64lens"]["version_command"]
        version_cwd = result / tools["x64lens"]["version_command_cwd"]
        require(isinstance(version_command, list) and version_command, "version command is missing")
        require(version_cwd.is_dir(), "version command cwd is missing")
        require((version_cwd / version_command[0]).resolve() == (result / "inputs/tools/x64lens").resolve(), "version command does not resolve after publication")

        pairs: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
        for row in rows:
            command = json.loads(row["command_json"])
            require(isinstance(command, list) and command, f"invalid recorded command: {row['run_id']}")
            require(not Path(command[0]).is_absolute() and not Path(command[-1]).is_absolute(), f"recorded command is not relative: {command!r}")
            command_cwd = result / row["command_cwd"]
            require(command_cwd.is_dir(), f"recorded command cwd is missing: {row['run_id']}")
            require((command_cwd / command[0]).resolve() == (result / "inputs/tools/x64lens").resolve(), f"tool command does not resolve after publication: {command!r}")
            require((command_cwd / command[-1]).resolve() == (result / "inputs/targets/controlled-gadgets").resolve(), f"target command does not resolve after publication: {command!r}")
            require(".staging-" not in row["command_json"] and ".staging-" not in row["command_cwd"], f"staging path leaked into command: {row['run_id']}")
            included = row["included_in_primary_summary"] == "true"
            if row["phase"] == "warmup":
                require(not included and row["summary_exclusion_reason"] == "warmup", f"warmup inclusion mismatch: {row['run_id']}")
            elif row["timing_class"] == "below_reliable_single_process_floor":
                require(not included and row["summary_exclusion_reason"] == "below_timer_floor", f"floor inclusion mismatch: {row['run_id']}")
            else:
                require(included and row["summary_exclusion_reason"] == "", f"measured inclusion mismatch: {row['run_id']}")
            key = (row["phase"], row["round"])
            pairs.setdefault(key, {})[row["report_command"]] = row

        require(len(pairs) == 4, f"parity pair count mismatch: {len(pairs)}")
        for key, pair in pairs.items():
            require(set(pair) == {"gadgets", "analyze"}, f"missing command parity member for {key}: {sorted(pair)}")
            gadgets = read_report(result, pair["gadgets"])
            analyze = read_report(result, pair["analyze"])
            require(gadgets.get("command") == "gadgets", f"gadgets command identity mismatch for {key}")
            require(analyze.get("command") == "analyze", f"analyze command identity mismatch for {key}")
            require(normalized_report(gadgets) == normalized_report(analyze), f"command-only report parity mismatch for {key}")

        require(
            manifest["outcomes"]["primary_summary_row_count"]
            == sum(row["included_in_primary_summary"] == "true" for row in rows),
            "manifest primary-summary count mismatch",
        )
        require(not list(output_root.glob(".*.staging-*")), "reference staging directory leaked")

    print("sprint11-diagnostic-reference-smoke: ok rows=8 warmup=2 measured=6 parity_pairs=4")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, SmokeError, subprocess.SubprocessError) as exc:
        print(f"sprint11-diagnostic-reference-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
