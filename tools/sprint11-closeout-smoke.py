#!/usr/bin/env python3
"""Reconcile the Sprint 11 diagnostic checkpoint and Sprint 12 handoff."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT = ROOT / "tests/expected/sprint11-closeout.json"
STAGES = ROOT / "tests/expected/research-stage-gates.json"
PLAN = ROOT / "benchmarks/task-definitions/sprint11-p060-campaign-plan.json"
TASKS = ROOT / "benchmarks/task-definitions/sprint11-diagnostic-tasks.json"
CORPUS = ROOT / "benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json"
MAKEFILE = ROOT / "Makefile"


class CloseoutError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CloseoutError(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CloseoutError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must contain an object")
    return value


def contains_exact_key(value: Any, forbidden: str) -> bool:
    if isinstance(value, dict):
        return forbidden in value or any(contains_exact_key(item, forbidden) for item in value.values())
    if isinstance(value, list):
        return any(contains_exact_key(item, forbidden) for item in value)
    return False


def main() -> int:
    try:
        closeout = load(CLOSEOUT)
        stages = load(STAGES)
        plan = load(PLAN)
        tasks = load(TASKS)
        corpus = load(CORPUS)

        require(closeout.get("schema_version") == 1, "unsupported closeout schema")
        require(closeout.get("sprint") == 11 and closeout.get("status") == "closed", "Sprint 11 is not closed")
        require(closeout.get("closeout_patch") == 61, "Patch 061 must close Sprint 11")
        patches = closeout.get("completed_patches")
        require(patches == list(range(55, 62)), "Patch sequence must cover 055-061")
        require(closeout.get("next_sprint") == 12, "Sprint 12 must be next")
        completed_sprints = stages.get("completed_sprints")
        active_sprint = stages.get("active_sprint")
        require(isinstance(completed_sprints, int) and completed_sprints >= 11, "Sprint 11 completion was lost")
        require(active_sprint == completed_sprints + 1, "active sprint must follow completed_sprints")

        profile = closeout.get("reference_profile")
        require(profile == {
            "tool_version": "0.1.0-dev",
            "report_schema": "0.2.0",
            "candidate_capacity": 4096,
            "analysis_arena_bytes": 851968,
            "mandatory_decoder": False,
            "mandatory_threads": False,
        }, "reference profile changed")

        toolchains = corpus.get("toolchains")
        optimizations = corpus.get("optimization_profiles")
        artifacts = corpus.get("artifact_profiles")
        hardening = corpus.get("hardening_profiles")
        require(all(isinstance(value, list) and value for value in (toolchains, optimizations, artifacts, hardening)), "corpus matrix dimensions are missing")
        expected_targets = len(toolchains) * len(optimizations) * len(artifacts) * len(hardening)
        require(corpus.get("target_count") == expected_targets == 24, f"corpus matrix does not produce 24 targets: {expected_targets}")

        selected = plan.get("selection_policy", {}).get("target_ids")
        require(isinstance(selected, list) and len(selected) == 6 and len(set(selected)) == 6, "campaign must select six unique targets")
        require(plan.get("total_condition_count") == 30, "campaign authority must define 30 conditions")

        baselines = tasks.get("baselines")
        require(isinstance(baselines, list) and len(baselines) == 3, "expected three baseline adapters")
        relations = tasks.get("normalized_relations")
        require(isinstance(relations, list) and len(relations) == 4, "expected four relation authorities")
        require(not contains_exact_key(plan, "gadget_count"), "campaign plan contains a recursive generic gadget_count")
        require(not contains_exact_key(tasks, "gadget_count"), "task authority contains a recursive generic gadget_count")

        protocol = plan.get("execution_policy", {}).get("below_floor_protocol")
        require(isinstance(protocol, dict), "below-floor protocol is missing")
        require(protocol.get("whole_batch_sizes") == [2, 4, 8, 16, 32, 64], "batch sizes changed")
        require(protocol.get("minimum_batches") == 9, "minimum batch count changed")
        require(protocol.get("eligibility_floor_multiplier") == 5, "floor multiplier changed")
        require(protocol.get("maximum_mad_over_median") == 0.10, "MAD ratio changed")
        require(protocol.get("same_k_comparisons_only") is True, "same-K comparison rule changed")
        require(protocol.get("divide_batch_time_into_single_run_latency") is False, "divided single-run latency is forbidden")

        checkpoint = closeout.get("diagnostic_checkpoint")
        require(checkpoint == {
            "corpus_targets": 24,
            "selected_targets": 6,
            "planned_conditions": 30,
            "baseline_adapters": 3,
            "relation_authorities": 4,
            "selected_priorities": 3,
            "evidence_class": "diagnostic",
            "frozen": False,
            "publication_eligible": False,
        }, "diagnostic checkpoint summary mismatch")
        require(all(closeout.get("method_gates", {}).values()), "one or more closeout method gates are false")
        boundary = closeout.get("empirical_boundary")
        require(boundary.get("corrected_campaign_rerun_required") is True, "corrected campaign rerun must remain required")
        require(boundary.get("diagnostic_rows_are_publication_evidence") is False, "diagnostic rows cannot become publication evidence")
        require(boundary.get("single_run_x64lens_latency_resolved") is False, "single-run x64lens latency remains unresolved")
        require(boundary.get("generic_cross_tool_count_comparable") is False, "generic cross-tool count remains incomparable")

        for relative in closeout.get("required_closeout_documents", []):
            require((ROOT / relative).is_file(), f"missing closeout document: {relative}")

        sprint11 = (ROOT / "docs/sprints/sprint-11-plan.md").read_text(encoding="utf-8")
        sprint12 = (ROOT / "docs/sprints/sprint-12-plan.md").read_text(encoding="utf-8")
        require("Closed by Patch 061" in sprint11, "Sprint 11 plan is not closed")
        require("Closeout correction and Sprint 13 entry candidate at Patch 078" in sprint12, "Sprint 12 continuation chronology is missing")

        makefile = MAKEFILE.read_text(encoding="utf-8")
        require("sprint11-closeout-smoke:" in makefile, "Sprint 11 closeout Make target is missing")
        validation = next((line for line in makefile.splitlines() if line.startswith("validation-smoke:")), "")
        require("sprint11-closeout-smoke" in validation, "Sprint 11 closeout is not in validation-smoke")
        sprint_closeout = next((line for line in makefile.splitlines() if line.startswith("sprint-closeout-smoke:")), "")
        require("sprint11-closeout-smoke" in sprint_closeout, "Sprint 11 closeout is not in sprint-closeout-smoke")

    except (OSError, CloseoutError) as exc:
        print(f"sprint11-closeout-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "sprint11-closeout-smoke: ok "
        f"sprint=11 patches={len(patches)} corpus_targets={checkpoint['corpus_targets']} "
        f"planned_conditions={checkpoint['planned_conditions']} baseline_adapters={checkpoint['baseline_adapters']} "
        f"relation_authorities={checkpoint['relation_authorities']} selected_priorities={checkpoint['selected_priorities']} "
        "next_sprint=12"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
