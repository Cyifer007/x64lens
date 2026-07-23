#!/usr/bin/env python3
"""Execute and summarize the Sprint 11 Patch 060 provisional campaign.

The orchestrator accounts for the complete 30-condition authority, executes only
available authenticated tools through the high-resolution runner, preserves all
native rows, derives task-scoped relation and runtime-closure artifacts, performs
address-coordinate calibration when evidence is complete, and generates
reproducible diagnostic summaries plus an engineering gap register.

This is development infrastructure. It does not alter x64lens runtime facts and
never promotes Sprint 11 rows into the Sprint 15-frozen campaign.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import stat
import statistics
import subprocess
import sys
from typing import Any, Iterable
import uuid

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from diagnostic_artifact import (  # noqa: E402
    ArtifactError,
    MAX_JSON_BYTES,
    MAX_MEMBER_BYTES,
    canonical_json_bytes,
    load_campaign,
    load_regular_path,
    open_real_directory,
    require,
    require_regular_path_identity,
    safe_id,
    sha256_bytes,
)

SCHEMA_VERSION = 1
PLAN_SCHEMA_VERSION = 2
PLAN_ID = "sprint11-p060-authenticated-provisional-campaign-v1"
AUTHORITY_SCHEMA_VERSION = 3
AUTHORITY_ID = "sprint11-diagnostic-task-definitions-v3"
EVIDENCE_CLASS = "diagnostic"
TOOLS = ("x64lens", "ropgadget", "ropper", "ropr")
BASELINES = TOOLS[1:]
RELATION_TOOLS = TOOLS
MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_SUBPROCESS_OUTPUT = 4 * 1024 * 1024

RUNNER = ROOT / "benchmarks/scripts/diagnostic-runner.py"
CORPUS_BUILDER = ROOT / "benchmarks/scripts/build-provisional-corpus.py"
X_RELATION = ROOT / "benchmarks/scripts/x64lens-relation-extractor.py"
BASELINE_ADAPTER = ROOT / "benchmarks/scripts/baseline-output-adapter.py"
CLOSURE = ROOT / "benchmarks/scripts/runtime-closure-manifest.py"
CALIBRATOR = ROOT / "benchmarks/scripts/address-coordinate-calibrator.py"


class CampaignError(RuntimeError):
    """Raised for an invalid authority, execution, or derived artifact."""


def fail(message: str) -> None:
    raise CampaignError(message)


def read_json(path: Path, label: str, maximum: int = MAX_JSON_BYTES) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    data, identity = load_regular_path(path, maximum, label)
    try:
        value = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CampaignError(f"cannot parse {label}: {exc}") from exc
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value, identity, data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def identity(path: Path) -> dict[str, Any]:
    data, record = load_regular_path(path, MAX_MEMBER_BYTES, f"file {path}")
    del data
    return record


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int,
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            pass_fds=pass_fds,
            env={
                "HOME": os.environ.get("HOME", "/nonexistent"),
                "LANG": "C",
                "LC_ALL": "C",
                "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                "TZ": "UTC",
            },
        )
    except subprocess.TimeoutExpired as exc:
        raise CampaignError(f"orchestrator helper timed out: {argv[0]}") from exc
    require(len(result.stdout) <= MAX_SUBPROCESS_OUTPUT, f"helper stdout exceeded {MAX_SUBPROCESS_OUTPUT} bytes")
    require(len(result.stderr) <= MAX_SUBPROCESS_OUTPUT, f"helper stderr exceeded {MAX_SUBPROCESS_OUTPUT} bytes")
    return result


def write_file(path: Path, data: bytes, mode: int = 0o444) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        offset = 0
        while offset < len(data):
            offset += os.write(fd, data[offset:])
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path: Path, value: Any) -> None:
    write_file(path, canonical_json_bytes(value))


def write_text(path: Path, text: str) -> None:
    write_file(path, text.encode("utf-8"))


def tsv_bytes(fields: list[str], rows: Iterable[dict[str, Any]]) -> bytes:
    from io import StringIO
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    for row in rows:
        rendered: dict[str, str] = {}
        for field in fields:
            value = row.get(field)
            if value is None:
                rendered[field] = "NA"
            elif isinstance(value, bool):
                rendered[field] = "true" if value else "false"
            elif isinstance(value, (dict, list)):
                rendered[field] = json.dumps(value, sort_keys=True, separators=(",", ":"))
            else:
                rendered[field] = str(value)
        writer.writerow(rendered)
    return buffer.getvalue().encode("utf-8")


def load_runner_support():
    return load_module(RUNNER, "x64lens_p060_runner_support")


def load_corpus_builder():
    return load_module(CORPUS_BUILDER, "x64lens_p060_corpus_builder")


def validate_plan(plan: dict[str, Any]) -> None:
    require(plan.get("schema_version") == PLAN_SCHEMA_VERSION, "unsupported Patch 060 campaign-plan schema")
    require(plan.get("plan_id") == PLAN_ID, "unexpected Patch 060 campaign-plan identity")
    require(plan.get("evidence_class") == EVIDENCE_CLASS, "campaign plan is not diagnostic")
    require(plan.get("frozen") is False and plan.get("publication_eligible") is False, "campaign plan claim boundary changed")
    require(plan.get("status") == "executable_provisional_campaign_authority", "campaign plan is not executable authority")
    require(plan.get("total_condition_count") == 30, "campaign plan no longer accounts for 30 conditions")
    selection = plan.get("selection_policy")
    require(isinstance(selection, dict), "campaign target selection is missing")
    target_ids = selection.get("target_ids")
    require(isinstance(target_ids, list) and len(target_ids) == 6 and len(set(target_ids)) == 6, "campaign must select six unique targets")
    comparative = plan.get("comparative_matrix")
    controls = plan.get("x64lens_control_matrix")
    require(isinstance(comparative, dict) and comparative.get("condition_count") == 24, "comparative matrix must contain 24 conditions")
    require(isinstance(controls, dict) and controls.get("condition_count") == 6, "control matrix must contain six conditions")
    summary = plan.get("summary_contract")
    require(isinstance(summary, dict) and summary.get("generic_gadget_count_forbidden") is True, "generic count prohibition is missing")


def validate_authority(authority: dict[str, Any]) -> None:
    require(authority.get("schema_version") == AUTHORITY_SCHEMA_VERSION, "unsupported task authority schema")
    require(authority.get("authority_id") == AUTHORITY_ID, "unexpected task authority identity")
    require(authority.get("evidence_class") == EVIDENCE_CLASS, "task authority is not diagnostic")
    require(authority.get("frozen") is False and authority.get("publication_eligible") is False, "task authority claim boundary changed")
    baseline_ids = [item.get("id") for item in authority.get("baselines", []) if isinstance(item, dict)]
    require(tuple(baseline_ids) == BASELINES, "task authority baseline order changed")


def resolve_tool(raw: str | None, required: bool, tool_id: str) -> Path | None:
    if raw is None:
        require(not required, f"required tool path is missing: {tool_id}")
        return None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        found = shutil.which(raw)
        require(found is not None, f"cannot resolve tool {tool_id}: {raw}")
        path = Path(found)
    path = path.resolve(strict=True)
    metadata = os.stat(path, follow_symlinks=False)
    require(stat.S_ISREG(metadata.st_mode), f"tool is not a regular file: {tool_id}")
    require(os.access(path, os.X_OK), f"tool is not executable: {tool_id}")
    return path


def task_maps(authority: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    tasks = {item["id"]: item for item in authority["tasks"] if item.get("status") == "implemented"}
    baselines = {item["id"]: item for item in authority["baselines"]}
    return tasks, baselines


def command_from_template(template: list[str]) -> list[str]:
    result = ["{target}" if item == "<target>" else item for item in template]
    require(result, "empty command template")
    if result[0] in {"<tool>", "x64lens"}:
        result[0] = "{tool}"
    return result


def planned_conditions(plan: dict[str, Any], authority: dict[str, Any]) -> list[dict[str, Any]]:
    tasks, baselines = task_maps(authority)
    target_ids = plan["selection_policy"]["target_ids"]
    conditions: list[dict[str, Any]] = []
    for target_id in target_ids:
        gadget = tasks["x64lens_gadget_json"]
        conditions.append({
            "id": f"{gadget['condition_id']}--{target_id}",
            "tool_id": "x64lens",
            "target_id": target_id,
            "task_scope": gadget["task_scope"],
            "profile_id": plan["reference_profile"],
            "worker_count": 1,
            "argv": command_from_template(gadget["command_template"]),
            "extractor": gadget["extractor"],
            "expected_report_command": "gadgets",
            "output_scope": gadget["work_scope_note"],
            "relation_required": True,
            "control": False,
        })
        for tool_id in BASELINES:
            baseline = baselines[tool_id]
            conditions.append({
                "id": f"{baseline['condition_id']}--{target_id}",
                "tool_id": tool_id,
                "target_id": target_id,
                "task_scope": baseline["task_scope"],
                "profile_id": "baseline-native",
                "worker_count": 1,
                "argv": command_from_template(baseline["command_template"]),
                "extractor": "none",
                "expected_report_command": None,
                "output_scope": baseline["work_scope_note"],
                "relation_required": True,
                "control": False,
            })
        analyze = tasks["x64lens_integrated_analysis_json"]
        conditions.append({
            "id": f"{analyze['condition_id']}--{target_id}",
            "tool_id": "x64lens",
            "target_id": target_id,
            "task_scope": analyze["task_scope"],
            "profile_id": plan["reference_profile"],
            "worker_count": 1,
            "argv": command_from_template(analyze["command_template"]),
            "extractor": analyze["extractor"],
            "expected_report_command": "analyze",
            "output_scope": analyze["work_scope_note"],
            "relation_required": False,
            "control": True,
        })
    require(len(conditions) == 30 and len({item["id"] for item in conditions}) == 30, "derived condition authority is not 30 unique conditions")
    return conditions


def runner_spec(
    *,
    campaign_id: str,
    plan: dict[str, Any],
    authority: dict[str, Any],
    corpus_root: Path,
    corpus_manifest: dict[str, Any],
    tool_paths: dict[str, Path | None],
    conditions: list[dict[str, Any]],
    warmups: int,
    measured: int,
) -> dict[str, Any]:
    target_by_id = {item["id"]: item for item in corpus_manifest["targets"]}
    target_records: list[dict[str, Any]] = []
    for target_id in plan["selection_policy"]["target_ids"]:
        require(target_id in target_by_id, f"selected target is absent from corpus: {target_id}")
        record = target_by_id[target_id]
        target_records.append({
            "id": target_id,
            "path": str(corpus_root / record["relative_path"]),
            "license": record["license"],
        })
    tool_authority = {item["id"]: item for item in plan["tool_authority"]}
    tools: list[dict[str, Any]] = []
    for tool_id in TOOLS:
        path = tool_paths[tool_id]
        if path is None:
            continue
        record = tool_authority[tool_id]
        tools.append({
            "id": tool_id,
            "path": str(path),
            "version": record["expected_version"],
            "version_argv": record["version_argv"],
        })
    available = {item["id"] for item in tools}
    runner_conditions: list[dict[str, Any]] = []
    for condition in conditions:
        if condition["tool_id"] not in available:
            continue
        row = {
            "id": condition["id"],
            "task_scope": condition["task_scope"],
            "profile_id": condition["profile_id"],
            "worker_count": condition["worker_count"],
            "tool": condition["tool_id"],
            "target": condition["target_id"],
            "argv": condition["argv"],
            "extractor": condition["extractor"],
            "output_scope": condition["output_scope"],
        }
        if condition["expected_report_command"] is not None:
            row["expected_report_command"] = condition["expected_report_command"]
        runner_conditions.append(row)
    policy = plan["execution_policy"]
    return {
        "schema_version": 2,
        "campaign_id": f"{campaign_id}-native",
        "evidence_class": EVIDENCE_CLASS,
        "frozen": False,
        "publication_eligible": False,
        "warmup_runs": warmups,
        "measured_runs": measured,
        "timeout_seconds": policy["timeout_seconds"],
        "order_policy": policy["order_policy"],
        "cache_policy": policy["cache_policy"] if warmups else "uncontrolled",
        "fail_campaign_on_error": False,
        "capture_limits": {"maximum_stdout_bytes": 16777216, "maximum_stderr_bytes": 1048576},
        "environment": {"X64LENS_DIAGNOSTIC_PROFILE": plan["reference_profile"]},
        "timer_floor": {
            "probe": "/bin/true",
            "runs": policy["timer_floor_runs"],
            "threshold_multiplier": policy["timer_floor_threshold_multiplier"],
        },
        "tools": tools,
        "targets": target_records,
        "conditions": runner_conditions,
    }


def row_success(row: dict[str, str]) -> bool:
    return row.get("phase") == "measured" and row.get("process_outcome") == "success" and row.get("outcome") == "success"


def choose_success(rows: list[dict[str, str]]) -> dict[str, str] | None:
    candidates = [row for row in rows if row_success(row)]
    candidates.sort(key=lambda row: (int(row["round"]), int(row["order_index"]), row["run_id"]))
    return candidates[0] if candidates else None


def invoke_derived(
    *,
    script: Path,
    argv: list[str],
    log_root: Path,
    label: str,
    stage_fd: int,
    timeout: int = 300,
) -> tuple[bool, str]:
    log_root.mkdir(parents=True, exist_ok=True)
    result = run_command([sys.executable, str(script), *argv], cwd=ROOT, timeout=timeout, pass_fds=(stage_fd,))
    write_file(log_root / f"{label}.stdout", result.stdout)
    write_file(log_root / f"{label}.stderr", result.stderr)
    return result.returncode == 0, result.stderr.decode("utf-8", errors="replace")[:1000]


def int_field(row: dict[str, str], name: str) -> int:
    value = row.get(name, "")
    require(value not in {"", "NA"}, f"row {row.get('run_id')} lacks {name}")
    return int(value)


def p95(values: list[int]) -> int:
    require(values, "cannot compute p95 of an empty sample")
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def timing_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    measured = [row for row in rows if row.get("phase") == "measured"]
    successful = [row for row in measured if row.get("process_outcome") == "success" and row.get("outcome") == "success"]
    included = [row for row in successful if row.get("included_in_primary_summary") == "true"]
    result: dict[str, Any] = {
        "measured_row_count": len(measured),
        "successful_measured_row_count": len(successful),
        "failed_measured_row_count": len(measured) - len(successful),
        "primary_summary_row_count": len(included),
        "below_floor_success_row_count": sum(row.get("summary_exclusion_reason") == "below_reliable_timer_floor" for row in successful),
        "wall_time_ns": None,
        "user_time_ns": None,
        "system_time_ns": None,
        "max_rss_kb": None,
        "output_bytes": None,
    }
    if included:
        walls = [int_field(row, "wall_time_ns") for row in included]
        users = [int_field(row, "user_time_ns") for row in included]
        systems = [int_field(row, "system_time_ns") for row in included]
        rss = [int_field(row, "max_rss_kb") for row in included]
        outputs = [int_field(row, "stdout_bytes") + int_field(row, "stderr_bytes") for row in included]
        result.update({
            "wall_time_ns": {"median": int(statistics.median(walls)), "p95": p95(walls), "min": min(walls), "max": max(walls)},
            "user_time_ns": {"median": int(statistics.median(users)), "p95": p95(users)},
            "system_time_ns": {"median": int(statistics.median(systems)), "p95": p95(systems)},
            "max_rss_kb": {"median": int(statistics.median(rss)), "p95": p95(rss), "min": min(rss), "max": max(rss)},
            "output_bytes": {"median": int(statistics.median(outputs)), "p95": p95(outputs)},
        })
    return result


def classify_condition(
    *,
    available: bool,
    rows: list[dict[str, str]],
    relation_status: str,
) -> tuple[str, str]:
    if not available:
        return "unavailable_tool", "pinned tool was not supplied on this host"
    measured = [row for row in rows if row.get("phase") == "measured"]
    success = [row for row in measured if row_success(row)]
    if not success:
        outcomes = {row.get("process_outcome") for row in measured} | {row.get("outcome") for row in measured}
        if "output_limit" in outcomes:
            return "output_limit", "every measured row exceeded an authenticated capture limit"
        if "timeout" in outcomes:
            return "timeout", "every measured row timed out"
        return "tool_failure", "no measured row completed successfully"
    if relation_status == "failed":
        return "normalization_failure", "native execution succeeded but the required normalized artifact failed"
    if all(row.get("included_in_primary_summary") != "true" for row in success):
        return "below_timer_floor", "successful rows were retained but all were below the reliable single-process floor"
    return "success", "at least one successful measured row is eligible for diagnostic summary"


def relation_metrics(path: Path) -> dict[str, Any]:
    value, _identity, _data = read_json(path, "normalized relation artifact")
    metrics = value.get("metrics")
    require(isinstance(metrics, dict), "relation artifact metrics are missing")
    require("gadget_count" not in metrics, "relation artifact contains a generic gadget count")
    return metrics


def x64_report_observation(context, row: dict[str, str], role: str) -> dict[str, Any]:
    data, _identity = context.load_row_member(row, "stdout")
    try:
        report = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CampaignError(f"cannot parse retained x64lens report for gap analysis: {exc}") from exc
    mitigations = report.get("mitigations")
    gadgets = report.get("gadgets")
    require(isinstance(mitigations, dict) and isinstance(gadgets, list), "x64lens report lacks mitigation or gadget facts")
    exact_unknown_patterns: dict[str, int] = {}
    for gadget in gadgets:
        if not isinstance(gadget, dict):
            continue
        pattern = gadget.get("pattern")
        if gadget.get("semantic_class") == "unknown_candidate" and isinstance(pattern, str) and pattern != "unknown":
            exact_unknown_patterns[pattern] = exact_unknown_patterns.get(pattern, 0) + 1
    return {
        "role": role,
        "target_id": row["target_id"],
        "run_id": row["run_id"],
        "pie_indicator": mitigations.get("pie"),
        "mitigation_fields": sorted(mitigations),
        "exact_unknown_patterns": exact_unknown_patterns,
        "counts": {
            key: int(row[key]) for key in (
                "raw_candidate_count", "exact_pattern_count", "semantic_candidate_count", "unknown_candidate_count", "scored_candidate_count"
            )
        },
    }


def build_gap_register(
    *,
    campaign_id: str,
    plan: dict[str, Any],
    accounting: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    calibration: dict[str, Any],
    closure_records: list[dict[str, Any]],
) -> dict[str, Any]:
    gaps: list[dict[str, Any]] = []
    unavailable = sorted({item["tool_id"] for item in accounting if item["status"] == "unavailable_tool"})
    for tool_id in unavailable:
        gaps.append({
            "id": f"P060-ENV-{tool_id.upper()}-UNAVAILABLE",
            "category": "environment",
            "roadmap_sprint": None,
            "disposition": "measurement_required",
            "evidence": {"tool_id": tool_id, "condition_count": sum(item["tool_id"] == tool_id for item in accounting)},
            "decision": "Install and authenticate the pinned baseline before drawing comparative conclusions.",
            "claim_boundary": "Missing optional tooling is environment evidence, not an x64lens product defect.",
        })

    role_pie: dict[str, set[Any]] = {}
    exact_unknown: dict[str, int] = {}
    for item in observations:
        role_pie.setdefault(item["role"], set()).add(item["pie_indicator"])
        for pattern, count in item["exact_unknown_patterns"].items():
            exact_unknown[pattern] = exact_unknown.get(pattern, 0) + count
    if role_pie.get("pie_et_dyn") and role_pie.get("shared_et_dyn") and role_pie["pie_et_dyn"] == role_pie["shared_et_dyn"]:
        gaps.append({
            "id": "P060-S12-PIE-DSO-IDENTITY",
            "category": "loader_identity",
            "roadmap_sprint": 12,
            "disposition": "selected_priority",
            "evidence": {"role_indicator_values": {key: sorted(value, key=lambda x: str(x)) for key, value in sorted(role_pie.items())}},
            "decision": "Retain Sprint 12 bounded PIE-executable versus shared-object evidence as a release-facing priority.",
            "claim_boundary": "The current PIE indicator is static ET_DYN evidence and cannot distinguish these roles.",
        })
    hardened_observations = [item for item in observations if "hardened" in item["target_id"]]
    if hardened_observations and all("ibt" not in {name.lower() for name in item["mitigation_fields"]} and "shstk" not in {name.lower() for name in item["mitigation_fields"]} for item in hardened_observations):
        gaps.append({
            "id": "P060-S12-CET-PROPERTY-EVIDENCE",
            "category": "mitigation_evidence",
            "roadmap_sprint": 12,
            "disposition": "selected_priority",
            "evidence": {"hardened_targets": [item["target_id"] for item in hardened_observations], "reported_fields": sorted({name for item in hardened_observations for name in item["mitigation_fields"]})},
            "decision": "Retain bounded GNU-property IBT/SHSTK parsing and hostile fixtures in Sprint 12.",
            "claim_boundary": "Compiler hardening intent is corpus provenance, not proof of runtime CET state until x64lens parses bounded note evidence.",
        })
    if exact_unknown:
        gaps.append({
            "id": "P060-S13-EXACT-ONLY-SEMANTIC-GAPS",
            "category": "semantic_coverage",
            "roadmap_sprint": 13,
            "disposition": "selected_priority",
            "evidence": {"exact_unknown_pattern_counts": dict(sorted(exact_unknown.items()))},
            "decision": "Use the observed exact-only patterns to drive the bounded Sprint 13 generic-pop and role decision; add only families with complete represented effects.",
            "claim_boundary": "Exact suffix presence is not decoded validity and does not justify a score by itself.",
        })
    else:
        gaps.append({
            "id": "P060-S13-NO-OBSERVED-EXACT-ONLY-GAP",
            "category": "semantic_coverage",
            "roadmap_sprint": 13,
            "disposition": "measurement_required",
            "evidence": {"observed_x64lens_targets": len(observations)},
            "decision": "Do not broaden semantic families from this selected-target screen without a named observed gap or controlled oracle.",
            "claim_boundary": "Absence in six selected targets is not evidence of universal completeness.",
        })

    calibration_status = calibration.get("status", "unknown")
    if calibration_status != "complete":
        gaps.append({
            "id": "P060-METHOD-COORDINATE-CALIBRATION",
            "category": "methodology",
            "roadmap_sprint": None,
            "disposition": "measurement_required",
            "evidence": calibration,
            "decision": "Block cross-tool address intersections until every baseline has role-controlled authenticated calibration.",
            "claim_boundary": "Uncalibrated displayed addresses are not comparable coordinates.",
        })
    partial_closures = [item for item in closure_records if item.get("status") == "partial"]
    if partial_closures:
        gaps.append({
            "id": "P060-METHOD-RUNTIME-CLOSURE-PARTIAL",
            "category": "provenance",
            "roadmap_sprint": None,
            "disposition": "measurement_required",
            "evidence": {"partial_closures": [{"tool_id": item["tool_id"], "task_scope": item["task_scope"]} for item in partial_closures]},
            "decision": "Resolve or explicitly retain each unresolved task-path dependency before campaign freeze.",
            "claim_boundary": "A partial observed closure is not a complete dependency inventory.",
        })
    below_floor = [item["condition_id"] for item in accounting if item["status"] == "below_timer_floor"]
    if below_floor:
        gaps.append({
            "id": "P060-METHOD-BELOW-FLOOR",
            "category": "measurement_resolution",
            "roadmap_sprint": None,
            "disposition": "measurement_required",
            "evidence": {"condition_ids": below_floor, "batch_sizes": plan["execution_policy"]["below_floor_batch_sizes"]},
            "decision": "Apply the preregistered larger-target or whole-batch protocol; do not infer single-run latency from these rows.",
            "claim_boundary": "Below-floor rows cannot select a performance optimization.",
        })
    gaps.extend([
        {
            "id": "P060-S14-DECODER-ABLATION",
            "category": "optional_profile",
            "roadmap_sprint": 14,
            "disposition": "deferred",
            "evidence": {"normalized_relation": "canonical_exact_pop_rdi_ret", "decoder_validated_population": "unmeasured"},
            "decision": "Do not make a decoder mandatory from this exact-relation screen; retain candidate-scoped validation as a separate Sprint 14 ablation only if a material task gap is later quantified.",
            "claim_boundary": "Count or relation disagreement alone is insufficient decoder evidence.",
        },
        {
            "id": "P060-S14-CONCURRENCY-ABLATION",
            "category": "optional_profile",
            "roadmap_sprint": 14,
            "disposition": "deferred",
            "evidence": {"measured_profile": plan["reference_profile"], "worker_profiles": "unmeasured"},
            "decision": "Preserve the one-worker reference; evaluate target-level or candidate-validation concurrency only as separately identified profiles.",
            "claim_boundary": "No parallel speedup or RSS tradeoff was measured by this campaign.",
        },
    ])
    selected = [item["id"] for item in gaps if item["disposition"] == "selected_priority"]
    return {
        "schema_version": 1,
        "register_id": f"{campaign_id}-engineering-gap-register",
        "evidence_class": EVIDENCE_CLASS,
        "frozen": False,
        "publication_eligible": False,
        "selected_priorities": selected,
        "entries": gaps,
        "claim_boundaries": [
            "The register is generated from mutable diagnostic evidence and may change after capability or method revisions.",
            "Only entries with source evidence may select Sprint 12-14 work.",
            "Environment and methodology gaps are not x64lens product defects.",
            "No generic cross-tool count or release-facing superiority claim is produced.",
        ],
    }


def render_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Sprint 11 Patch 060 Diagnostic Summary",
        "",
        "This generated summary is mutable diagnostic evidence. It is not publication or release evidence.",
        "",
        "## Condition accounting",
        "",
        f"- Planned conditions: {summary['condition_totals']['planned']}",
        f"- Executed conditions: {summary['condition_totals']['executed']}",
        f"- Successful: {summary['condition_totals']['success']}",
        f"- Unavailable tool: {summary['condition_totals']['unavailable_tool']}",
        f"- Failed or non-summarizable: {summary['condition_totals']['other']}",
        "",
        "## Task-scoped results",
        "",
        "| Condition | Tool | Target | Status | Primary rows | Median wall ns | Median RSS KiB | Relation records |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for item in summary["conditions"]:
        timing = item["timing"]
        wall = timing["wall_time_ns"]["median"] if timing["wall_time_ns"] else "NA"
        rss = timing["max_rss_kb"]["median"] if timing["max_rss_kb"] else "NA"
        relation = item.get("relation_metrics") or {}
        relation_count = relation.get("canonical_exact_pop_rdi_ret_record_count", "NA")
        lines.append(f"| `{item['condition_id']}` | {item['tool_id']} | `{item['target_id']}` | {item['status']} | {timing['primary_summary_row_count']} | {wall} | {rss} | {relation_count} |")
    lines.extend([
        "",
        "## Interpretation boundaries",
        "",
        "- Native tool records, normalized exact relations, and x64lens raw/exact/semantic/unknown/scored populations remain separate.",
        "- Missing or failed conditions remain in the accounting table.",
        "- Below-floor rows remain retained but do not support single-run latency interpretation.",
        "- The selected six-target screen does not independently identify compiler, optimization, linkage, or hardening effects.",
        "- Sprint 15 remains the confirmatory campaign freeze.",
        "",
    ])
    return "\n".join(lines)


def render_gap_markdown(register: dict[str, Any]) -> str:
    lines = [
        "# Sprint 11 Patch 060 Engineering Gap Register",
        "",
        "Generated from authenticated provisional campaign evidence. This register is diagnostic and unfrozen.",
        "",
        "| ID | Category | Sprint | Disposition | Decision |",
        "|---|---|---:|---|---|",
    ]
    for item in register["entries"]:
        sprint = item["roadmap_sprint"] if item["roadmap_sprint"] is not None else "-"
        lines.append(f"| `{item['id']}` | {item['category']} | {sprint} | {item['disposition']} | {item['decision']} |")
    lines.extend(["", "Selected priorities: " + (", ".join(f"`{item}`" for item in register["selected_priorities"]) or "none"), ""])
    return "\n".join(lines)


def exact_tree_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        metadata = path.lstat()
        require(stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode), f"campaign result contains a non-regular member: {path.relative_to(root)}")
        if stat.S_ISREG(metadata.st_mode):
            require(metadata.st_nlink == 1, f"campaign result contains a multiply linked file: {path.relative_to(root)}")
            files.append(path)
    return files


def checksum_manifest(root: Path) -> bytes:
    lines: list[str] = []
    for path in exact_tree_files(root):
        relative = path.relative_to(root).as_posix()
        if relative == "SHA256SUMS.txt":
            continue
        lines.append(f"{sha256_file(path)}  {relative}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--task-authority", type=Path, required=True)
    parser.add_argument("--corpus-result", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--campaign-id", required=True)
    parser.add_argument("--x64lens", required=True)
    parser.add_argument("--ropgadget")
    parser.add_argument("--ropper")
    parser.add_argument("--ropr")
    parser.add_argument("--warmup-runs", type=int)
    parser.add_argument("--measured-runs", type=int)
    return parser.parse_args(argv)


def execute(args: argparse.Namespace) -> Path:
    campaign_id = safe_id(args.campaign_id, "campaign id")
    plan, plan_identity, plan_bytes = read_json(args.plan, "Patch 060 campaign plan")
    authority, authority_identity, authority_bytes = read_json(args.task_authority, "Sprint 11 task authority")
    validate_plan(plan)
    validate_authority(authority)
    plan_required = Path(plan["task_authority"])
    require((ROOT / plan_required).resolve(strict=True) == args.task_authority.resolve(strict=True), "campaign plan points to a different task authority")

    builder = load_corpus_builder()
    corpus_root = args.corpus_result.resolve(strict=True)
    corpus_manifest = builder.verify_corpus(corpus_root)
    require(corpus_manifest["evidence_class"] == EVIDENCE_CLASS and corpus_manifest["frozen"] is False, "corpus is not provisional diagnostic evidence")
    corpus_manifest_path = corpus_root / "corpus-manifest.json"
    corpus_manifest_identity = identity(corpus_manifest_path)

    tool_paths = {
        "x64lens": resolve_tool(args.x64lens, True, "x64lens"),
        "ropgadget": resolve_tool(args.ropgadget, False, "ropgadget"),
        "ropper": resolve_tool(args.ropper, False, "ropper"),
        "ropr": resolve_tool(args.ropr, False, "ropr"),
    }
    tool_source_identities = {tool_id: identity(path) for tool_id, path in tool_paths.items() if path is not None}
    conditions = planned_conditions(plan, authority)
    warmups = plan["execution_policy"]["warmup_runs"] if args.warmup_runs is None else args.warmup_runs
    measured = plan["execution_policy"]["measured_runs"] if args.measured_runs is None else args.measured_runs
    require(isinstance(warmups, int) and 0 <= warmups <= 20, "warmup runs are outside the diagnostic bound")
    require(isinstance(measured, int) and 1 <= measured <= 100, "measured runs are outside the diagnostic bound")

    output_root = args.output_root.resolve(strict=True) if args.output_root.exists() else Path(os.path.abspath(args.output_root))
    output_root.mkdir(parents=True, exist_ok=True)
    output_root = output_root.resolve(strict=True)
    final = output_root / campaign_id
    require(not final.exists(), f"campaign result already exists: {final}")
    support = load_runner_support()
    stage_registry: list[Any] = []
    owned = support.OwnedStage.create(output_root, f".{campaign_id}.staging.{uuid.uuid4().hex}", stage_registry)
    stage = owned.authoritative_path
    try:
        for directory in (
            stage / "inputs",
            stage / "runner-results",
            stage / "relations",
            stage / "runtime-closures",
            stage / "coordinate",
            stage / "summaries",
            stage / "derivation-logs",
        ):
            directory.mkdir(parents=True, exist_ok=True)
        write_file(stage / "inputs" / "campaign-plan.json", plan_bytes)
        write_file(stage / "inputs" / "task-authority.json", authority_bytes)
        write_file(stage / "inputs" / "corpus-manifest.json", (corpus_manifest_path.read_bytes()))

        spec_value = runner_spec(
            campaign_id=campaign_id,
            plan=plan,
            authority=authority,
            corpus_root=corpus_root,
            corpus_manifest=corpus_manifest,
            tool_paths=tool_paths,
            conditions=conditions,
            warmups=warmups,
            measured=measured,
        )
        spec_path = stage / "inputs" / "runner-spec.json"
        write_json(spec_path, spec_value)
        runner_result_root = stage / "runner-results"
        runner_id = spec_value["campaign_id"]
        runner_result = runner_result_root / runner_id
        runner_cmd = [sys.executable, str(RUNNER), "--spec", str(spec_path), "--output-root", str(runner_result_root)]
        runner_run = run_command(runner_cmd, cwd=ROOT, timeout=max(600, len(spec_value["conditions"]) * measured * 30), pass_fds=(owned.directory_fd,))
        write_file(stage / "derivation-logs" / "runner.stdout", runner_run.stdout)
        write_file(stage / "derivation-logs" / "runner.stderr", runner_run.stderr)
        require(runner_run.returncode in {0, 1}, f"diagnostic runner infrastructure failed with exit {runner_run.returncode}: {runner_run.stderr.decode('utf-8', errors='replace')[:2000]}")
        require(runner_result.is_dir(), "diagnostic runner did not publish its native result")

        context = load_campaign(runner_result)
        try:
            rows_by_condition: dict[str, list[dict[str, str]]] = {item["id"]: [] for item in conditions}
            for row in context.rows:
                condition_id = row["condition_id"]
                require(condition_id in rows_by_condition, f"runner produced an undeclared condition: {condition_id}")
                rows_by_condition[condition_id].append(row)

            relation_paths: dict[str, Path] = {}
            relation_states: dict[str, str] = {}
            relation_errors: dict[str, str] = {}
            for condition in conditions:
                if not condition["relation_required"] or tool_paths[condition["tool_id"]] is None:
                    continue
                selected = choose_success(rows_by_condition[condition["id"]])
                if selected is None:
                    relation_states[condition["id"]] = "not_attempted"
                    continue
                output = stage / "relations" / f"{condition['id']}.json"
                script = X_RELATION if condition["tool_id"] == "x64lens" else BASELINE_ADAPTER
                ok, error = invoke_derived(
                    script=script,
                    argv=["--campaign-result", str(runner_result), "--run-id", selected["run_id"], "--task-authority", str(args.task_authority), "--output", str(output)],
                    log_root=stage / "derivation-logs",
                    label=f"relation-{condition['id']}",
                    stage_fd=owned.directory_fd,
                )
                relation_states[condition["id"]] = "success" if ok else "failed"
                if ok:
                    relation_paths[condition["id"]] = output
                else:
                    relation_errors[condition["id"]] = error

            closure_records: list[dict[str, Any]] = []
            closure_keys: dict[tuple[str, str], dict[str, str]] = {}
            for condition in conditions:
                if tool_paths[condition["tool_id"]] is None:
                    continue
                selected = choose_success(rows_by_condition[condition["id"]])
                if selected is not None:
                    closure_keys.setdefault((condition["tool_id"], condition["task_scope"]), selected)
            for (tool_id, task_scope), selected in sorted(closure_keys.items()):
                output = stage / "runtime-closures" / f"{tool_id}--{task_scope}.json"
                ok, error = invoke_derived(
                    script=CLOSURE,
                    argv=["--campaign-result", str(runner_result), "--run-id", selected["run_id"], "--task-authority", str(args.task_authority), "--output", str(output)],
                    log_root=stage / "derivation-logs",
                    label=f"closure-{tool_id}--{task_scope}",
                    stage_fd=owned.directory_fd,
                )
                if ok:
                    value, _id, _data = read_json(output, f"runtime closure {tool_id}/{task_scope}")
                    closure_records.append({
                        "tool_id": tool_id,
                        "task_scope": task_scope,
                        "run_id": selected["run_id"],
                        "status": value.get("status"),
                        "path": output.relative_to(stage).as_posix(),
                        "sha256": sha256_file(output),
                    })
                else:
                    closure_records.append({"tool_id": tool_id, "task_scope": task_scope, "run_id": selected["run_id"], "status": "failed", "error": error})

            role_targets = plan["selection_policy"]["role_targets"]
            calibration_roles: list[dict[str, Any]] = []
            missing_calibration: list[str] = []
            for role in ("et_exec", "pie_et_dyn", "shared_et_dyn"):
                target_id = role_targets[role][0]
                artifacts: dict[str, Any] = {}
                for tool_id in RELATION_TOOLS:
                    base = "x64lens-gadget-json" if tool_id == "x64lens" else next(item["condition_id"] for item in authority["baselines"] if item["id"] == tool_id)
                    condition_id = f"{base}--{target_id}"
                    path = relation_paths.get(condition_id)
                    if path is None:
                        missing_calibration.append(condition_id)
                    else:
                        artifacts[tool_id] = {"path": str(path), "campaign_result": str(runner_result)}
                calibration_roles.append({"id": role, "corpus_target_id": target_id, "artifacts": artifacts})
            if missing_calibration:
                calibration = {
                    "schema_version": 1,
                    "status": "unavailable",
                    "missing_relation_conditions": sorted(missing_calibration),
                    "claim_boundary": "Cross-tool address intersections remain blocked.",
                }
                write_json(stage / "coordinate" / "status.json", calibration)
            else:
                calibration_input = stage / "coordinate" / "input.json"
                write_json(calibration_input, {"schema_version": 2, "roles": calibration_roles})
                calibration_output = stage / "coordinate" / "address-calibration.json"
                ok, error = invoke_derived(
                    script=CALIBRATOR,
                    argv=["--corpus-result", str(corpus_root), "--input-spec", str(calibration_input), "--task-authority", str(args.task_authority), "--output", str(calibration_output)],
                    log_root=stage / "derivation-logs",
                    label="address-calibration",
                    stage_fd=owned.directory_fd,
                )
                if ok:
                    calibration, _id, _data = read_json(calibration_output, "address coordinate calibration")
                    calibration = {"status": "complete", "artifact": calibration_output.relative_to(stage).as_posix(), "tools": calibration.get("tools", {})}
                else:
                    calibration = {"schema_version": 1, "status": "failed", "error": error, "claim_boundary": "Cross-tool address intersections remain blocked."}
                    write_json(stage / "coordinate" / "failure.json", calibration)

            target_roles = {
                target_id: role
                for role, target_ids in role_targets.items()
                for target_id in target_ids
            }
            observations: list[dict[str, Any]] = []
            accounting: list[dict[str, Any]] = []
            condition_summaries: list[dict[str, Any]] = []
            for condition in conditions:
                available = tool_paths[condition["tool_id"]] is not None
                condition_rows = rows_by_condition[condition["id"]]
                relation_state = relation_states.get(condition["id"], "not_required" if not condition["relation_required"] else "not_attempted")
                status, reason = classify_condition(available=available, rows=condition_rows, relation_status=relation_state)
                selected = choose_success(condition_rows)
                metrics = relation_metrics(relation_paths[condition["id"]]) if condition["id"] in relation_paths else None
                timing = timing_summary(condition_rows)
                record = {
                    "condition_id": condition["id"],
                    "tool_id": condition["tool_id"],
                    "target_id": condition["target_id"],
                    "target_role": target_roles[condition["target_id"]],
                    "task_scope": condition["task_scope"],
                    "profile_id": condition["profile_id"],
                    "control": condition["control"],
                    "tool_available": available,
                    "status": status,
                    "reason": reason,
                    "native_row_count": len(condition_rows),
                    "warmup_row_count": sum(row.get("phase") == "warmup" for row in condition_rows),
                    "measured_row_count": sum(row.get("phase") == "measured" for row in condition_rows),
                    "successful_measured_row_count": timing["successful_measured_row_count"],
                    "failed_measured_row_count": timing["failed_measured_row_count"],
                    "primary_summary_row_count": timing["primary_summary_row_count"],
                    "relation_status": relation_state,
                    "relation_artifact": relation_paths[condition["id"]].relative_to(stage).as_posix() if condition["id"] in relation_paths else None,
                    "relation_error": relation_errors.get(condition["id"]),
                    "selected_run_id": selected["run_id"] if selected else None,
                    "run_ids": [row["run_id"] for row in condition_rows],
                }
                accounting.append(record)
                condition_summaries.append({**record, "timing": timing, "relation_metrics": metrics})
                if condition["tool_id"] == "x64lens" and condition["task_scope"] == "gadget_report" and selected is not None:
                    observations.append(x64_report_observation(context, selected, target_roles[condition["target_id"]]))

            require(len(accounting) == 30 and len({item["condition_id"] for item in accounting}) == 30, "condition accounting is not complete")
            accounting_fields = [
                "condition_id", "tool_id", "target_id", "target_role", "task_scope", "profile_id", "control",
                "tool_available", "status", "reason", "native_row_count", "warmup_row_count", "measured_row_count",
                "successful_measured_row_count", "failed_measured_row_count", "primary_summary_row_count",
                "relation_status", "relation_artifact", "selected_run_id", "run_ids",
            ]
            write_file(stage / "condition-accounting.tsv", tsv_bytes(accounting_fields, accounting))
            write_json(stage / "condition-accounting.json", {"schema_version": 1, "campaign_id": campaign_id, "conditions": accounting})

            status_counts = {state: sum(item["status"] == state for item in accounting) for state in plan["accounting_states"]}
            summary = {
                "schema_version": 1,
                "summary_id": f"{campaign_id}-task-scoped-summary",
                "evidence_class": EVIDENCE_CLASS,
                "frozen": False,
                "publication_eligible": False,
                "condition_totals": {
                    "planned": 30,
                    "executed": sum(item["tool_available"] for item in accounting),
                    "success": status_counts.get("success", 0),
                    "unavailable_tool": status_counts.get("unavailable_tool", 0),
                    "other": 30 - status_counts.get("success", 0) - status_counts.get("unavailable_tool", 0),
                    "by_status": status_counts,
                },
                "runner": {
                    "campaign_id": context.manifest["campaign_id"],
                    "manifest_sha256": context.manifest_identity["sha256"],
                    "rows_sha256": context.rows_identity["sha256"],
                    "native_row_count": len(context.rows),
                    "timer_floor_ns": context.manifest["timer_floor"]["reliable_single_process_floor_ns"],
                    "wait4_resource_scope": context.manifest["runner"]["resource_scope"],
                },
                "conditions": condition_summaries,
                "coordinate_calibration": calibration,
                "runtime_closures": closure_records,
                "x64lens_role_observations": observations,
                "factor_attribution": {
                    "status": "not_identifiable_from_selected_screen",
                    "reason": "The six selected targets intentionally balance but do not independently cross every compiler, optimization, linkage, and hardening factor.",
                    "full_factor_target_count": corpus_manifest["target_count"],
                },
                "claim_boundaries": plan["claim_boundaries"],
            }
            require("gadget_count" not in json.dumps(summary), "generated summary contains a generic gadget count")
            write_json(stage / "summaries" / "task-summary.json", summary)
            write_text(stage / "summaries" / "task-summary.md", render_summary_markdown(summary))
            summary_fields = [
                "condition_id", "tool_id", "target_id", "task_scope", "status", "primary_summary_row_count",
                "median_wall_time_ns", "p95_wall_time_ns", "median_max_rss_kb", "relation_record_count",
            ]
            summary_rows = []
            for item in condition_summaries:
                wall = item["timing"]["wall_time_ns"]
                rss = item["timing"]["max_rss_kb"]
                relation = item.get("relation_metrics") or {}
                summary_rows.append({
                    "condition_id": item["condition_id"],
                    "tool_id": item["tool_id"],
                    "target_id": item["target_id"],
                    "task_scope": item["task_scope"],
                    "status": item["status"],
                    "primary_summary_row_count": item["timing"]["primary_summary_row_count"],
                    "median_wall_time_ns": wall["median"] if wall else None,
                    "p95_wall_time_ns": wall["p95"] if wall else None,
                    "median_max_rss_kb": rss["median"] if rss else None,
                    "relation_record_count": relation.get("canonical_exact_pop_rdi_ret_record_count"),
                })
            write_file(stage / "summaries" / "task-summary.tsv", tsv_bytes(summary_fields, summary_rows))

            gap_register = build_gap_register(
                campaign_id=campaign_id,
                plan=plan,
                accounting=accounting,
                observations=observations,
                calibration=calibration,
                closure_records=closure_records,
            )
            require("gadget_count" not in json.dumps(gap_register), "gap register contains a generic gadget count")
            write_json(stage / "engineering-gap-register.json", gap_register)
            write_text(stage / "engineering-gap-register.md", render_gap_markdown(gap_register))

            generator_paths = [RUNNER, CORPUS_BUILDER, X_RELATION, BASELINE_ADAPTER, CLOSURE, CALIBRATOR, Path(__file__).resolve(strict=True)]
            generator_records = []
            for path in generator_paths:
                record = identity(path)
                generator_records.append({"path": path.relative_to(ROOT).as_posix(), "sha256": record["sha256"], "size_bytes": record["size_bytes"], "mode": f"{record['mode']:04o}"})
            manifest = {
                "schema_version": SCHEMA_VERSION,
                "campaign_id": campaign_id,
                "evidence_class": EVIDENCE_CLASS,
                "frozen": False,
                "publication_eligible": False,
                "status": "complete_condition_accounting",
                "authority": {
                    "plan_id": PLAN_ID,
                    "plan_sha256": plan_identity["sha256"],
                    "task_authority_id": AUTHORITY_ID,
                    "task_authority_sha256": authority_identity["sha256"],
                },
                "corpus": {
                    "corpus_id": corpus_manifest["corpus_id"],
                    "manifest_sha256": corpus_manifest_identity["sha256"],
                    "target_count": corpus_manifest["target_count"],
                    "selected_target_ids": plan["selection_policy"]["target_ids"],
                },
                "source_tools": {
                    tool_id: {
                        "available": tool_paths[tool_id] is not None,
                        "source_path": str(tool_paths[tool_id]) if tool_paths[tool_id] else None,
                        "sha256": tool_source_identities.get(tool_id, {}).get("sha256"),
                        "size_bytes": tool_source_identities.get(tool_id, {}).get("size_bytes"),
                    }
                    for tool_id in TOOLS
                },
                "generators": generator_records,
                "artifacts": {
                    "native_runner_result": runner_result.relative_to(stage).as_posix(),
                    "condition_accounting_tsv": "condition-accounting.tsv",
                    "condition_accounting_json": "condition-accounting.json",
                    "task_summary_tsv": "summaries/task-summary.tsv",
                    "task_summary_json": "summaries/task-summary.json",
                    "task_summary_markdown": "summaries/task-summary.md",
                    "engineering_gap_register_json": "engineering-gap-register.json",
                    "engineering_gap_register_markdown": "engineering-gap-register.md",
                    "relation_artifact_count": len(relation_paths),
                    "runtime_closure_count": len(closure_records),
                    "coordinate_status": calibration.get("status"),
                },
                "condition_totals": summary["condition_totals"],
                "selected_priorities": gap_register["selected_priorities"],
                "claim_boundaries": plan["claim_boundaries"],
            }
            write_json(stage / "manifest.json", manifest)

            # Reauthenticate all mutable source authorities before finalizing the tree.
            require_regular_path_identity(args.plan, plan_identity, MAX_JSON_BYTES, "Patch 060 campaign plan")
            require_regular_path_identity(args.task_authority, authority_identity, MAX_JSON_BYTES, "Sprint 11 task authority")
            require_regular_path_identity(corpus_manifest_path, corpus_manifest_identity, MAX_JSON_BYTES, "provisional corpus manifest")
            builder.verify_corpus(corpus_root)
            for tool_id, path in tool_paths.items():
                if path is not None:
                    require_regular_path_identity(path, tool_source_identities[tool_id], MAX_MEMBER_BYTES, f"source tool {tool_id}")
            # Reauthenticate runner and every derived relation through their own validators.
            verify_context = load_campaign(runner_result)
            verify_context.close()
            write_file(stage / "SHA256SUMS.txt", checksum_manifest(stage))
            # Verify the final checksum set before publication.
            checksum_lines = (stage / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
            expected = {line[66:]: line[:64] for line in checksum_lines}
            actual_files = {path.relative_to(stage).as_posix(): path for path in exact_tree_files(stage) if path.relative_to(stage).as_posix() != "SHA256SUMS.txt"}
            require(set(expected) == set(actual_files), "campaign checksum membership mismatch")
            for name, digest in expected.items():
                require(sha256_file(actual_files[name]) == digest, f"campaign checksum mismatch: {name}")
        finally:
            context.close()

        support.fsync_tree(stage)
        support._publish_owned_stage(owned, final, "Patch 060 campaign staging tree")
        return final
    except BaseException:
        if not owned.committed:
            owned.cleanup("Patch 060 campaign staging tree")
        raise
    finally:
        owned.close()


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        final = execute(args)
    except (CampaignError, ArtifactError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"sprint11-provisional-campaign: error: {exc}", file=sys.stderr)
        return 2
    print(f"sprint11-provisional-campaign: ok result={final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
