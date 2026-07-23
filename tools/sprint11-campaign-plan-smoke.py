#!/usr/bin/env python3
"""Validate the corrected Sprint 11 provisional diagnostic condition plan.

This is a structural pre-execution oracle.  It prevents baseline-only campaigns,
uncalibrated address comparisons, and generic count summaries from becoming the
Patch 059 method by accident.  It does not execute optional baseline tools.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "benchmarks/task-definitions/sprint11-p059-campaign-plan.json"
CORPUS_PATH = ROOT / "benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json"
TASK_PATH = ROOT / "benchmarks/task-definitions/sprint11-diagnostic-tasks.json"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class PlanError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PlanError(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must contain an object")
    return value


def recursively_reject_generic_count(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            require(key != "gadget_count", f"forbidden generic gadget_count key at {path}.{key}")
            recursively_reject_generic_count(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            recursively_reject_generic_count(item, f"{path}[{index}]")


def expected_target_ids(corpus: dict[str, Any]) -> set[str]:
    dimensions = []
    for key in ("toolchains", "optimization_profiles", "artifact_profiles", "hardening_profiles"):
        records = corpus.get(key)
        require(isinstance(records, list) and records, f"corpus {key} dimension is missing")
        ids = []
        for record in records:
            require(isinstance(record, dict) and SAFE_ID.fullmatch(str(record.get("id", ""))) is not None, f"invalid corpus {key} id")
            ids.append(record["id"])
        require(len(ids) == len(set(ids)), f"duplicate corpus {key} id")
        dimensions.append(ids)
    return {"-".join(parts) for parts in itertools.product(*dimensions)}


def main() -> int:
    try:
        plan = load(PLAN_PATH)
        corpus = load(CORPUS_PATH)
        tasks = load(TASK_PATH)
        require(plan.get("schema_version") == 1, "campaign plan schema mismatch")
        require(plan.get("plan_id") == "sprint11-p059-stage-zero-and-corrected-comparison-plan-v1", "campaign plan identity mismatch")
        require(plan.get("evidence_class") == "diagnostic", "campaign plan must remain diagnostic")
        require(plan.get("frozen") is False and plan.get("publication_eligible") is False, "campaign plan claim boundary mismatch")
        require(plan.get("status") == "pre_execution_authority", "campaign plan status mismatch")
        require(plan.get("corpus_spec") == str(CORPUS_PATH.relative_to(ROOT)), "campaign plan corpus authority mismatch")
        require(plan.get("task_authority") == str(TASK_PATH.relative_to(ROOT)), "campaign plan task authority mismatch")
        require(plan.get("reference_profile") == tasks.get("reference_profile") == "core-1w", "campaign reference profile mismatch")
        require(plan.get("maximum_depth") == 4, "campaign maximum depth mismatch")

        selection = plan.get("selection_policy")
        require(isinstance(selection, dict), "selection policy is missing")
        target_ids = selection.get("target_ids")
        require(isinstance(target_ids, list) and len(target_ids) == selection.get("target_count") == 6, "campaign must select six targets")
        require(len(target_ids) == len(set(target_ids)), "campaign target selection contains duplicates")
        require(set(target_ids) <= expected_target_ids(corpus), "campaign selects a target outside the provisional corpus matrix")
        require(selection.get("roles") == ["et_exec", "pie_et_dyn", "shared_et_dyn"], "campaign role vocabulary mismatch")
        require(selection.get("targets_per_role") == 2, "campaign role balance mismatch")
        role_counts = {
            "et_exec": sum("-exec-nopie-" in item for item in target_ids),
            "pie_et_dyn": sum("-exec-pie-" in item for item in target_ids),
            "shared_et_dyn": sum("-shared-" in item for item in target_ids),
        }
        require(set(role_counts.values()) == {2}, f"campaign role counts mismatch: {role_counts}")
        require({item.split("-", 1)[0] for item in target_ids} == {"gcc", "clang"}, "campaign compiler balance mismatch")
        require({"o0", "o2"} <= {part for item in target_ids for part in item.split("-")}, "campaign optimization balance mismatch")
        require({item.rsplit("-", 1)[1] for item in target_ids} == {"minimal", "hardened"}, "campaign hardening balance mismatch")

        comparative = plan.get("comparative_matrix")
        require(isinstance(comparative, dict), "comparative matrix is missing")
        require(comparative.get("tools") == ["x64lens", "ropgadget", "ropper", "ropr"], "comparative tool set mismatch")
        task_by_id = {item.get("id"): item for item in tasks.get("tasks", []) if isinstance(item, dict)}
        baseline_by_id = {item.get("id"): item for item in tasks.get("baselines", []) if isinstance(item, dict)}
        require(comparative.get("x64lens_condition") == f"{task_by_id['x64lens_gadget_json']['condition_id']}--<target_id>", "x64lens comparative condition does not match task authority")
        require(comparative.get("baseline_conditions") == [
            f"{baseline_by_id['ropgadget']['condition_id']}--<target_id>",
            f"{baseline_by_id['ropper']['condition_id']}--<target_id>",
            f"{baseline_by_id['ropr']['condition_id']}--<target_id>",
        ], "baseline comparative conditions do not match task authority")
        require(comparative.get("condition_count") == 24 == len(target_ids) * len(comparative["tools"]), "comparative condition count mismatch")
        require(comparative.get("required_relation_artifacts_per_condition") == 1, "relation artifact requirement mismatch")
        require(comparative.get("required_runtime_closure_per_tool_identity") == 1, "runtime closure requirement mismatch")

        controls = plan.get("x64lens_control_matrix")
        require(isinstance(controls, dict) and controls.get("condition_count") == 6, "x64lens control count mismatch")
        require(controls.get("condition") == f"{task_by_id['x64lens_integrated_analysis_json']['condition_id']}--<target_id>", "x64lens control condition does not match task authority")
        require(plan.get("total_condition_count") == 30 == comparative["condition_count"] + controls["condition_count"], "total condition count mismatch")

        stage_zero = plan.get("stage_zero_requirements")
        require(isinstance(stage_zero, dict), "stage-zero requirements are missing")
        require(stage_zero.get("matched_x64lens_relation_artifact") is True, "matched x64lens relation artifact is not required")
        coordinate = stage_zero.get("address_coordinate_calibration")
        require(isinstance(coordinate, dict) and coordinate.get("roles") == selection.get("roles"), "coordinate role contract mismatch")
        require(coordinate.get("required_before_cross_tool_address_intersection") is True, "coordinate calibration is not a precondition")
        require(stage_zero.get("runtime_closure_manifest") is True, "runtime closure is not required")
        outcomes = stage_zero.get("explicit_outcome_states")
        require(isinstance(outcomes, list) and len(outcomes) == len(set(outcomes)) == 8, "explicit outcome vocabulary mismatch")
        require({"success", "normalization_failure", "closure_partial", "coordinate_mismatch", "below_timer_floor"} <= set(outcomes), "required outcome states are absent")

        gate = plan.get("summary_gate")
        require(isinstance(gate, dict), "summary gate is missing")
        require(gate.get("requires_all_30_conditions_accounted_for") is True, "summary may omit conditions")
        require(gate.get("requires_native_and_normalized_artifacts") is True, "summary native/normalized boundary is missing")
        require(gate.get("requires_runtime_closure_identity") is True, "summary closure gate is missing")
        require(gate.get("requires_coordinate_calibration") is True, "summary coordinate gate is missing")
        require(gate.get("generic_gadget_count_forbidden") is True, "generic gadget count prohibition is missing")
        require(gate.get("below_floor_performance_claim_forbidden") is True, "below-floor claim prohibition is missing")
        require(gate.get("diagnostic_only") is True, "summary must remain diagnostic")
        recursively_reject_generic_count(plan)
    except PlanError as exc:
        print(f"sprint11-campaign-plan-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "sprint11-campaign-plan-smoke: ok "
        "targets=6 comparative_conditions=24 analyze_controls=6 total_conditions=30 "
        "coordinate_roles=3 closure_tools=4 generic_counts=0 frozen=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
