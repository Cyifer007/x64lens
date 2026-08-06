#!/usr/bin/env python3
"""Validate the Patch 080 Sprint 12 closeout correction and private Sprint 13 role authority."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "tests/expected/sprint12-continuation.json"
STAGES = ROOT / "tests/expected/research-stage-gates.json"


class Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Error(message)


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    require(isinstance(value, dict), f"{path.name} must be an object")
    return value


def exact_int(value: Any, expected: int, label: str) -> None:
    require(type(value) is int and value == expected, f"{label} must be integer {expected}")


def exact_bool(value: Any, expected: bool, label: str) -> None:
    require(type(value) is bool and value is expected, f"{label} must be boolean {expected}")


def main() -> int:
    try:
        authority = load(AUTH)
        stages = load(STAGES)
        exact_int(authority.get("schema_version"), 1, "schema_version")
        exact_int(authority.get("sprint"), 12, "sprint")
        require(
            authority.get("status") == "closeout_correction_and_sprint13_private_role_candidate_pending_acceptance",
            "Sprint 12 must remain pending P080 acceptance",
        )
        exact_int(authority.get("current_patch"), 80, "current_patch")
        exact_int(authority.get("superseded_closeout_patch"), 78, "superseded closeout")
        exact_int(authority.get("prior_corrective_patch"), 79, "prior corrective patch")
        exact_int(authority.get("next_patch"), 81, "next_patch")
        require(
            authority.get("next_patch_tranche") == "ordered-two-pop-role-task-pilot-or-next-measured-semantic-gate",
            "next tranche",
        )
        require(authority.get("acceptance_target") == "sprint13-p080-acceptance-smoke", "acceptance target")
        require(stages.get("completed_sprints") == 11 and stages.get("active_sprint") == 12, "stage chronology")

        reference = authority.get("reference_profile")
        require(isinstance(reference, dict), "reference profile")
        exact_int(reference.get("candidate_capacity"), 4096, "candidate capacity")
        exact_int(reference.get("candidate_role_record_bytes"), 8, "candidate role record")
        exact_int(reference.get("analysis_arena_bytes"), 884736, "analysis arena")
        exact_bool(reference.get("mandatory_decoder"), False, "mandatory decoder")
        exact_bool(reference.get("mandatory_threads"), False, "mandatory threads")
        exact_bool(reference.get("target_execution"), False, "target execution")

        boundary = authority.get("patch080_boundary")
        require(isinstance(boundary, dict), "Patch 080 boundary")
        for key in {
            "complete_patch079_correction",
            "runtime_source_include_change",
            "private_dynamic_metadata_sidecar_preserved",
            "private_register_role_sidecar_added",
            "git_patch_partial_effect_recovery",
            "gitless_complete_manifest_required",
            "gitless_caller_visible_root_reauthenticated",
            "permission_final_git_reauthentication_inside_rollback",
            "docker_immutable_image_id_authority",
            "parity_independent_builds",
            "parity_executable_build_root",
            "task_development_confirmation_queries_disjoint",
            "task_presentation_noncausal",
            "complete_sysv_and_syscall_abi_oracle",
        }:
            exact_bool(boundary.get(key), True, key)
        for key in {
            "runtime_parser_or_report_change",
            "schema_change",
        }:
            exact_bool(boundary.get(key), False, key)
        for key, expected in {
            "private_register_role_record_bytes": 8,
            "private_register_role_arena_bytes": 32768,
            "analysis_arena_bytes": 884736,
            "materializer_calls": 2,
            "reporter_consumers": 0,
            "scoring_consumers": 0,
            "public_fields_added": 0,
            "semantic_classifier_changes": 0,
            "score_changes": 0,
            "candidate_order_changes": 0,
            "candidate_count_changes": 0,
            "candidate_capacity": 4096,
        }.items():
            exact_int(boundary.get(key), expected, key)
        require(boundary.get("candidate_4097") == "exit_6_before_stdout", "capacity boundary")
        require(boundary.get("malformed_parse") == "no_partial_stdout", "malformed boundary")

        entry = authority.get("sprint13_entry_decision")
        require(isinstance(entry, dict), "Sprint 13 entry decision")
        for key, expected in {
            "exact_pop_patterns_accounted": 16,
            "generic_register_control_patterns": 15,
            "sysv_call_argument_patterns": 6,
            "linux_syscall_argument_patterns": 6,
            "new_public_fields": 0,
            "new_scores": 0,
            "task_value_version": 2,
            "task_value_strata": 5,
            "task_value_tasks": 60,
            "task_value_unique_queries": 60,
            "task_value_regressions": 0,
            "task_value_incorrect_promotions": 0,
            "task_value_incremental_gains": 26,
            "lc08b_policy_cells": 9,
        }.items():
            exact_int(entry.get(key), expected, key)
        require(entry.get("linux_syscall_arg4_register") == "r10", "Linux syscall argument 4")
        require(entry.get("sysv_call_arg4_register") == "rcx", "SysV call argument 4")
        require(entry.get("syscall_number_register") == "rax", "syscall number register")
        require(entry.get("stack_pivot_register") == "rsp", "stack pivot register")
        exact_bool(entry.get("task_value_human_blind_claim"), False, "human blind claim")
        exact_bool(entry.get("task_value_presentation_causal"), False, "presentation causal")
        require(
            entry.get("qualified_private_facets") == ["generic_control", "sysv_call_arguments", "linux_syscall_arguments"],
            "qualified private facets",
        )
        require(entry.get("retained_existing_facets") == ["syscall_number", "stack_pivot"], "retained role facets")
        require(entry.get("private_runtime_decision") == "accept_additive_sidecar_pending_exact_acceptance", "private decision")
        require(entry.get("public_projection_decision") == "defer", "public decision")
        require(entry.get("score_decision") == "retain_existing_scores_and_null_new_facets", "score decision")

        preserved = authority.get("preserved_authorities")
        require(isinstance(preserved, dict), "preserved authorities")
        require(preserved.get("executable_mapping") == "PT_LOAD_plus_PF_X_file_backed_ranges", "executable mapping")
        require(preserved.get("section_headers") == "bounded_metadata_and_annotations_only", "section boundary")
        require(preserved.get("candidate_4097") == "exit_6_before_stdout", "candidate capacity")
        require(preserved.get("malformed_parse") == "no_partial_stdout", "malformed boundary")
        require(preserved.get("reference_runtime") == "dependency_free_decoder_free_one_worker", "reference runtime")
        exact_bool(preserved.get("target_execution"), False, "target execution")
        exact_bool(preserved.get("raw_exact_semantic_unknown_scored_separation"), True, "fact separation")
        exact_bool(preserved.get("diagnostic_confirmatory_separation"), True, "campaign separation")

        for relative in authority.get("required_documents", []):
            require((ROOT / relative).is_file(), f"missing {relative}")
        sprint12 = (ROOT / "docs/sprints/sprint-12-plan.md").read_text(encoding="utf-8")
        sprint13 = (ROOT / "docs/sprints/sprint-13-plan.md").read_text(encoding="utf-8")
        require("Patch 080 private register-role closeout candidate" in sprint12, "Sprint 12 marker")
        require("Patch 080 private register-role candidate" in sprint13, "Sprint 13 marker")
    except (OSError, json.JSONDecodeError, Error) as exc:
        print(f"sprint12-continuation-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "sprint12-continuation-smoke: ok sprint=12 status=closeout-correction "
        "patch=80 textrel=private rpath=private runpath=private roles=16 "
        "qualified_private_facets=3 retained_facets=2 role_record_bytes=8 "
        "role_arena_bytes=32768 analysis_arena_bytes=884736 public_fields_added=0 "
        "semantic_changes=0 score_changes=0 next_patch=81"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
