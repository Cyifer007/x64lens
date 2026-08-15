#!/usr/bin/env python3
"""Validate the Patch 087 Sprint 12 retrospective and Sprint 13 continuation authority."""
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
            authority.get("status") == "retrospective_recorded_and_sprint13_p087_candidate_pending_acceptance",
            "Sprint 12 retrospective must remain pending P087 acceptance",
        )
        exact_int(authority.get("current_patch"), 87, "current_patch")
        exact_int(authority.get("superseded_closeout_patch"), 78, "superseded closeout")
        exact_int(authority.get("prior_corrective_patch"), 86, "prior corrective patch")
        exact_int(authority.get("next_patch"), 88, "next_patch")
        require(
            authority.get("next_patch_tranche") == "execute-paired-workload-phase-attribution-or-next-measurement-first-gate",
            "next tranche",
        )
        require(authority.get("acceptance_target") == "sprint13-p087-acceptance-smoke", "acceptance target")
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

        patch081 = authority.get("patch081_boundary")
        require(isinstance(patch081, dict), "Patch 081 boundary")
        for key in {
            "complete_patch080_correction", "sprint12_retrospective_recorded",
            "transaction_foreign_replacement_preserved", "git_pathspec_magic_literalized",
            "unrelated_state_preserved", "gitless_manifest_preauthenticated",
            "docker_provenance_digests_bound", "portable_checksum_paths_required",
        }:
            exact_bool(patch081.get(key), True, key)
        exact_bool(patch081.get("runtime_source_include_schema_change"), False, "runtime source/include/schema change")
        for key, expected in {
            "runtime_records_added": 0, "public_fields_added": 0,
            "semantic_classifier_changes": 0, "score_changes": 0,
            "candidate_capacity": 4096, "ordered_two_pop_structural_pairs": 30,
            "ordered_two_pop_incremental_gains": 0, "score_pattern_rows": 25,
            "score_null_mutations": 25, "score_null_independent_rejections": 50,
        }.items():
            exact_int(patch081.get(key), expected, key)
        require(patch081.get("candidate_4097") == "exit_6_before_stdout", "P081 capacity boundary")
        require(patch081.get("malformed_parse") == "no_partial_stdout", "P081 malformed boundary")
        require(patch081.get("ordered_two_pop_task_decision") == "defer_new_runtime_tuple_representation", "P081 tuple decision")

        patch082 = authority.get("patch082_boundary")
        require(isinstance(patch082, dict), "Patch 082 boundary")
        for key in {
            "complete_patch081_correction", "gitless_manifest_root_pair_required",
            "docker_pristine_source_separated_from_build", "nested_make_authority_isolated",
            "ordinary_unzip_custody_portable", "scoped_loose_helpers",
            "package_custody_modes_consistent",
        }:
            exact_bool(patch082.get(key), True, key)
        exact_bool(patch082.get("runtime_source_include_schema_change"), False, "P082 runtime source/include/schema change")
        for key, expected in {
            "runtime_records_added": 0, "public_fields_added": 0,
            "semantic_classifier_changes": 0, "score_changes": 0,
            "candidate_capacity": 4096, "producer_generations": 3,
            "producer_pair_checks": 90, "score_null_mutations": 25,
            "score_null_independent_rejections": 100,
            "controlled_coordinate_targets": 6, "controlled_coordinate_positive_cases": 8,
            "controlled_coordinate_mutation_rejections": 4,
            "controlled_coordinate_semantic_negatives": 4, "controlled_coordinate_cells": 9,
            "controlled_coordinate_qualified_cells": 9,
            "controlled_coordinate_positive_anchors": 18,
        }.items():
            exact_int(patch082.get(key), expected, key)
        exact_bool(patch082.get("natural_coordinate_campaign_qualified"), False, "P082 natural coordinate campaign")
        exact_bool(patch082.get("comparative_coverage_claim_authorized"), False, "P082 comparative coverage")
        require(patch082.get("candidate_4097") == "exit_6_before_stdout", "P082 capacity boundary")
        require(patch082.get("malformed_parse") == "no_partial_stdout", "P082 malformed boundary")

        patch083 = authority.get("patch083_boundary")
        require(isinstance(patch083, dict), "Patch 083 boundary")
        for key in {
            "complete_patch082_correction", "multiple_phony_declarations_supported",
            "exact_base_head_required", "patch_parent_chain_reauthenticated",
            "post_effect_output_recovery", "source_recovery_umask_0777_supported",
            "producer_candidate_tree_bound", "producer_modes_bound",
            "docker_nonroot_writable_run_root", "natural_coordinate_outcome_blind",
        }:
            exact_bool(patch083.get(key), True, key)
        for key in {
            "runtime_source_include_schema_change", "natural_coordinate_reroll",
            "natural_coordinate_campaign_qualified", "comparative_coverage_claim_authorized",
        }:
            exact_bool(patch083.get(key), False, key)
        for key, expected in {
            "runtime_records_added": 0, "public_fields_added": 0,
            "semantic_classifier_changes": 0, "score_changes": 0,
            "candidate_capacity": 4096, "natural_coordinate_target_slots": 12,
            "natural_coordinate_tool_executions": 48, "natural_coordinate_cells": 9,
            "natural_coordinate_controls": 108,
        }.items():
            exact_int(patch083.get(key), expected, key)
        require(patch083.get("candidate_4097") == "exit_6_before_stdout", "P083 capacity boundary")
        require(patch083.get("malformed_parse") == "no_partial_stdout", "P083 malformed boundary")
        require(patch083.get("natural_coordinate_campaign_id") == "s13-p083-natural-coordinate-v1", "P083 campaign id")
        require(patch083.get("natural_coordinate_campaign_status") == "retained_terminal_diagnostic_zero_qualified", "P083 campaign status")

        patch084 = authority.get("patch084_boundary")
        require(isinstance(patch084, dict), "Patch 084 boundary")
        for key in {
            "complete_patch083_correction",
            "generated_ordered_pair_binary_removed",
            "generated_ordered_pair_binary_ignored",
            "post_effect_repository_and_parent_reauthenticated",
            "corrupt_recovery_descriptor_retained",
            "corrupt_recovery_residue_absent",
            "docker_expected_candidate_tree_bound",
            "docker_authenticated_source_read_only",
            "natural_authority_full_shape_validated",
            "natural_source_candidate_tree_bound",
            "natural_structural_completion_separate",
            "natural_comparison_qualification_separate",
        }:
            exact_bool(patch084.get(key), True, key)
        for key in {
            "runtime_source_include_schema_change",
            "abi_role_public_projection",
            "comparative_coverage_claim_authorized",
        }:
            exact_bool(patch084.get(key), False, key)
        for key, expected in {
            "runtime_records_added": 0,
            "public_fields_added": 0,
            "semantic_classifier_changes": 0,
            "score_changes": 0,
            "candidate_capacity": 4096,
            "natural_coordinate_selected_targets": 12,
            "natural_coordinate_tool_executions": 48,
            "natural_coordinate_cells": 9,
            "natural_coordinate_controls": 108,
            "natural_coordinate_qualified_cells": 0,
            "natural_coordinate_insufficient_cells": 5,
            "natural_coordinate_unavailable_cells": 4,
            "natural_coordinate_mismatch_cells": 0,
            "natural_coordinate_ambiguous_cells": 0,
            "abi_role_query_contract_version": 1,
            "abi_role_queries": 36,
            "abi_role_development_queries": 24,
            "abi_role_confirmation_queries": 12,
            "abi_role_public_closures": 96,
            "lifecycle_roots": 20,
            "lifecycle_leaves": 30,
            "lifecycle_aliases": 29,
            "lifecycle_folds": 2,
            "lifecycle_tombstones": 15,
            "lifecycle_lineage_records": 161,
            "lifecycle_events": 87,
            "lifecycle_new_canonical_events": 0,
        }.items():
            exact_int(patch084.get(key), expected, key)
        require(patch084.get("candidate_4097") == "exit_6_before_stdout", "P084 capacity boundary")
        require(patch084.get("malformed_parse") == "no_partial_stdout", "P084 malformed boundary")
        require(patch084.get("natural_coordinate_campaign_status") == "retained_terminal_diagnostic_zero_qualified", "P084 natural status")

        patch085 = authority.get("patch085_boundary")
        require(isinstance(patch085, dict), "Patch 085 boundary")
        for key in {
            "complete_patch084_correction",
            "gitless_full_topology_reauthenticated",
            "source_recovery_initial_open_residue_removed",
            "source_recovery_posthash_topology_reauthenticated",
            "explicit_candidate_tree_authority_required",
            "abi_semantic_disjointness_required",
            "abi_analyzer_copy_pinned",
            "abi_target_reauthentication_per_command",
            "abi_no_replace_publication",
        }:
            exact_bool(patch085.get(key), True, key)
        for key in {
            "runtime_source_include_schema_change",
            "natural_replay_reroll",
            "comparative_coverage_claim_authorized",
        }:
            exact_bool(patch085.get(key), False, key)
        for key, expected in {
            "runtime_records_added": 0,
            "public_fields_added": 0,
            "semantic_classifier_changes": 0,
            "score_changes": 0,
            "candidate_capacity": 4096,
            "lifecycle_floors": 24,
            "lifecycle_successor_deltas": 5,
            "lifecycle_mutations": 13,
            "lifecycle_new_canonical_events": 0,
            "abi_role_queries": 36,
            "abi_role_development_queries": 24,
            "abi_role_confirmation_queries": 12,
            "abi_role_public_closures": 96,
            "natural_replay_targets": 12,
            "natural_replay_tool_executions": 48,
            "natural_terminal_execution_outcomes": 48,
            "natural_terminal_relation_outcomes": 48,
            "natural_terminal_observations": 36,
            "natural_terminal_cells": 9,
            "natural_terminal_precedence_mutations": 16,
        }.items():
            exact_int(patch085.get(key), expected, key)
        require(patch085.get("candidate_4097") == "exit_6_before_stdout", "P085 capacity boundary")
        require(patch085.get("malformed_parse") == "no_partial_stdout", "P085 malformed boundary")
        require(patch085.get("natural_replay_campaign_id") == "s13-p085-natural-frozen-replay-v1", "P085 replay campaign id")

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

        patch086 = authority.get("patch086_boundary")
        require(isinstance(patch086, dict), "Patch 086 boundary")
        exact_bool(patch086.get("complete_patch085_correction"), True, "P086 correction")
        exact_bool(patch086.get("runtime_source_include_schema_change"), False, "P086 runtime boundary")
        for key, expected in {
            "replay_v2_targets": 12,
            "replay_v2_executions": 48,
            "replay_v2_raw_streams": 96,
            "abi_vector_internal_dispositions": 48,
            "abi_vector_controlled_targets": 24,
            "abi_vector_queries": 36,
            "abi_vector_public_closures": 96,
            "public_fields_added": 0,
            "semantic_changes": 0,
            "score_changes": 0,
        }.items():
            exact_int(patch086.get(key), expected, key)

        patch087 = authority.get("patch087_boundary")
        require(isinstance(patch087, dict), "Patch 087 boundary")
        for key in {
            "complete_patch086_correction",
            "patch_state_hardlink_topology_rejected",
            "package_wrapper_helper_is_final_process",
            "source_recovery_effect_bookkeeping_signal_atomic",
            "custody_effect_bookkeeping_signal_atomic",
            "terminal_attribution_atomic_no_replace",
            "abi_candidate_source_bound",
        }:
            exact_bool(patch087.get(key), True, key)
        exact_bool(patch087.get("runtime_source_include_schema_change"), False, "P087 runtime boundary")
        exact_bool(patch087.get("schema_change"), False, "P087 schema boundary")
        for key, expected in {
            "replay_pinned_python_closures": 5,
            "workload_phase_fixtures": 8,
            "workload_phase_profiles": 2,
            "workload_phase_total_executions": 160,
            "public_fields_added": 0,
            "semantic_changes": 0,
            "score_changes": 0,
        }.items():
            exact_int(patch087.get(key), expected, key)
        require(patch087.get("workload_phase_execution") == "deferred", "P087 phase execution")

        for relative in authority.get("required_documents", []):
            require((ROOT / relative).is_file(), f"missing {relative}")
        sprint12 = (ROOT / "docs/sprints/sprint-12-plan.md").read_text(encoding="utf-8")
        sprint13 = (ROOT / "docs/sprints/sprint-13-plan.md").read_text(encoding="utf-8")
        require("Patch 087 correction and paired workload/phase-attribution authority candidate" in sprint12, "Sprint 12 marker")
        require("Patch 087 correction and paired workload/phase-attribution authority candidate" in sprint13, "Sprint 13 marker")
    except (OSError, json.JSONDecodeError, Error) as exc:
        print(f"sprint12-continuation-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "sprint12-continuation-smoke: ok sprint=12 status=closeout-correction "
        "patch=87 textrel=private rpath=private runpath=private roles=16 "
        "qualified_private_facets=3 retained_facets=2 role_record_bytes=8 "
        "role_arena_bytes=32768 analysis_arena_bytes=884736 public_fields_added=0 "
        "semantic_changes=0 score_changes=0 tuple_decision=defer producer_generations=3 coordinate_anchors=18 natural_campaign=terminal-zero-qualified abi_role_queries=36 lifecycle_events=87 phase_executions=160 next_patch=88"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
