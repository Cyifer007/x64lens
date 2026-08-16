#!/usr/bin/env python3
"""Validate the Patch 088 Sprint 12 retrospective and Sprint 13 continuation authority."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT = ROOT / "tests/expected/sprint12-closeout.json"
STAGES = ROOT / "tests/expected/research-stage-gates.json"
POLICY = ROOT / "benchmarks/task-definitions/sprint12-role-property-public-policy-v1.json"
OVERLAP = ROOT / "benchmarks/task-definitions/sprint12-overlap-normalization-decision.json"
ROLE = ROOT / "benchmarks/task-definitions/sprint13-register-role-decision-v1.json"
STRUCTS = ROOT / "include/structs.inc"
CONSTANTS = ROOT / "include/constants.inc"
MAKEFILE = ROOT / "Makefile"


class CloseoutError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CloseoutError(message)


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    require(isinstance(value, dict), f"{path.name} must contain an object")
    return value


def exact_int(value: Any, expected: int, label: str) -> None:
    require(type(value) is int and value == expected, f"{label} must be integer {expected}")


def exact_bool(value: Any, expected: bool, label: str) -> None:
    require(type(value) is bool and value is expected, f"{label} must be boolean {expected}")


def define(path: Path, name: str) -> str:
    match = re.search(
        rf"^%define\s+{re.escape(name)}\s+(.+?)\s*(?:;.*)?$",
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    require(match is not None, f"missing NASM definition {name}")
    return match.group(1).strip()


def integer_define(path: Path, name: str) -> int:
    value = define(path, name)
    require(re.fullmatch(r"[0-9]+", value) is not None, f"{name} must be a direct integer")
    return int(value)


def string_define(path: Path, name: str) -> str:
    value = define(path, name)
    require(len(value) >= 2 and value[0] == value[-1] == '"', f"{name} must be a string")
    return value[1:-1]


def main() -> int:
    try:
        closeout = load(CLOSEOUT)
        stages = load(STAGES)
        policy = load(POLICY)
        overlap = load(OVERLAP)
        role = load(ROLE)

        exact_int(closeout.get("schema_version"), 1, "closeout.schema_version")
        exact_int(closeout.get("sprint"), 12, "closeout.sprint")
        require(
            closeout.get("status") == "retrospective_recorded_and_sprint13_p088_candidate_pending_acceptance",
            "closeout status",
        )
        exact_int(closeout.get("closeout_patch"), 88, "closeout.closeout_patch")
        require(closeout.get("candidate_patches") == list(range(62, 89)), "Patch sequence must cover 062-088")
        exact_int(closeout.get("next_sprint"), 13, "next sprint")
        require(closeout.get("acceptance_target") == "sprint13-p088-acceptance-smoke", "acceptance target")
        exact_int(stages.get("completed_sprints"), 11, "stages.completed_sprints")
        exact_int(stages.get("active_sprint"), 12, "stages.active_sprint")

        profile = closeout.get("reference_profile")
        require(isinstance(profile, dict), "reference_profile")
        require(profile.get("tool_version") == string_define(CONSTANTS, "X64LENS_VERSION") == "0.1.0-dev", "tool version")
        require(profile.get("report_schema") == string_define(CONSTANTS, "X64LENS_SCHEMA") == "0.2.0", "schema version")
        require(profile.get("candidate_capacity") == integer_define(STRUCTS, "GADGET_RECORD_MAX") == 4096, "candidate capacity")
        arena = (
            integer_define(STRUCTS, "GADGET_RECORD_SIZE")
            + integer_define(STRUCTS, "CANDIDATE_EVIDENCE_RECORD_SIZE")
            + integer_define(STRUCTS, "MEMORY_EFFECT_RECORD_SIZE")
            + integer_define(STRUCTS, "CANDIDATE_EFFECT_RECORD_SIZE")
            + integer_define(STRUCTS, "CANDIDATE_ROLE_RECORD_SIZE")
        ) * 4096
        require(profile.get("candidate_role_record_bytes") == integer_define(STRUCTS, "CANDIDATE_ROLE_RECORD_SIZE") == 8, "candidate role record")
        require(profile.get("analysis_arena_bytes") == arena == 884736, "analysis arena")
        require(profile.get("phdr_summary_bytes") == integer_define(STRUCTS, "PHDR_SUMMARY_RECORD_SIZE") == 264, "PHDR summary")
        exact_int(profile.get("gnu_property_context_bytes"), 3160, "GNU property context")
        exact_int(profile.get("dynamic_metadata_context_bytes"), 9904, "dynamic context")
        exact_int(profile.get("private_metadata_context_bytes"), 13064, "private context")
        exact_bool(profile.get("mandatory_decoder"), False, "mandatory decoder")
        exact_bool(profile.get("mandatory_threads"), False, "mandatory threads")
        require(profile.get("target_mapping") == "read_only" and profile.get("target_execution") is False, "target safety")

        disposition = closeout.get("loader_and_mitigation_disposition")
        require(isinstance(disposition, dict), "loader disposition")
        require(disposition.get("program_header_executable_authority") == "PT_LOAD_plus_PF_X_file_backed_ranges", "loader authority")
        require(disposition.get("overlap_normalization") == "deferred_under_measured_reopen_threshold", "overlap disposition")
        require(overlap.get("decision") == "defer_normalization_preserve_provenance", "overlap authority")
        for key, expected in {
            "textrel": "retained_private_static_only",
            "rpath": "retained_private_distinct_static_only",
            "runpath": "retained_private_distinct_static_only",
        }.items():
            require(disposition.get(key) == expected, key)
        require(disposition.get("private_failure_snapshot_semantics") == "deterministic_parse_prefix", "private failure semantics")
        require(disposition.get("public_role_property_policy") == policy.get("decision") == "defer", "public policy")
        exact_int(disposition.get("public_fields_added"), 0, "public fields")
        exact_bool(disposition.get("existing_coarse_pie_field_reinterpreted"), False, "PIE reinterpretation")
        exact_bool(disposition.get("runtime_cet_enforcement_claimed"), False, "runtime CET")

        evidence = closeout.get("diagnostic_evidence_boundary")
        require(isinstance(evidence, dict), "diagnostic evidence")
        for key, expected in {
            "external_natural_objects": 48,
            "external_natural_eligible_matches": 624,
            "external_natural_eligible_mismatches": 0,
            "external_natural_ambiguous": 48,
            "external_natural_unavailable": 192,
            "positive_coordinate_anchors": 18,
        }.items():
            exact_int(evidence.get(key), expected, key)
        exact_bool(evidence.get("publication_eligible"), False, "publication eligible")
        exact_bool(evidence.get("performance_claim_authorized"), False, "performance claim")

        transaction = closeout.get("corrective_transaction_boundary")
        require(isinstance(transaction, dict), "transaction boundary")
        for key, value in transaction.items():
            if key == "delivery_custody_schema":
                require(value == "x64lens-delivery-custody-v3", "custody schema")
            else:
                exact_bool(value, True, key)
        for required_key in (
            "docker_source_and_transport_single_snapshot",
            "gitless_root_directory_file_descriptor_custody",
            "gitless_permission_normalization_tracked_only",
            "docker_build_failure_transparent",
            "role_property_parity_independent_builds",
            "role_property_parity_immutable_image_identity",
            "patch_post_effect_exception_recovery",
            "source_recovery_foreign_descendant_preserved",
        ):
            exact_bool(transaction.get(required_key), True, required_key)

        require(
            closeout.get("deferred_loader_and_mitigation_work")
            == [
                "public-pie-dso-ibt-shstk-projection",
                "public-textrel-rpath-runpath-projection",
                "executable-overlap-normalization",
                "bounded-fortify-relocation-symbol-join",
            ],
            "deferred work",
        )

        handoff = closeout.get("sprint13_handoff")
        require(isinstance(handoff, dict), "Sprint 13 handoff")
        require(handoff.get("generic_exact_pop_semantic_decision") == "private_additive_role_sidecar_candidate", "generic pop decision")
        require(handoff.get("linux_syscall_r10_role_decision") == "private_additive_linux_syscall_arg4_sidecar_candidate", "r10 decision")
        require(handoff.get("score_null_policy_freeze") == "existing_scores_retained_new_private_facets_unscored", "score/null decision")
        require(handoff.get("public_projection") == "deferred", "public projection")
        exact_int(handoff.get("next_patch"), 89, "Sprint 13 next patch")
        require(handoff.get("next_patch_tranche") == "reconcile-split-debug-and-execute-workload-phase-or-next-measurement-first-gate", "Sprint 13 next tranche")
        require(handoff.get("replay_v2_campaign_id") == "s13-p087-natural-frozen-replay-v2", "P087 replay campaign")
        exact_int(handoff.get("replay_v2_targets"), 12, "P087 replay targets")
        exact_int(handoff.get("replay_v2_executions"), 48, "P087 replay executions")
        exact_int(handoff.get("replay_v2_raw_streams"), 96, "P087 replay raw streams")
        exact_int(handoff.get("replay_v2_pinned_python_closures"), 5, "P087 pinned Python closures")
        exact_int(handoff.get("workload_phase_authority_version"), 1, "phase authority version")
        exact_int(handoff.get("workload_phase_fixtures"), 8, "phase fixtures")
        exact_int(handoff.get("workload_phase_profiles"), 2, "phase profiles")
        exact_int(handoff.get("workload_phase_cells"), 16, "phase cells")
        exact_int(handoff.get("workload_phase_warmups"), 16, "phase warmups")
        exact_int(handoff.get("workload_phase_measured_executions"), 144, "phase measured executions")
        exact_int(handoff.get("workload_phase_total_executions"), 160, "phase total executions")
        exact_int(handoff.get("workload_phase_required_qualified_fixtures"), 6, "phase qualified fixtures")
        exact_int(handoff.get("workload_phase_minimum_floor_multiple"), 5, "phase floor multiple")
        require(handoff.get("workload_phase_maximum_mad_ratio") == 0.1, "phase MAD ratio")
        require(handoff.get("workload_phase_maximum_residual_ratio") == 0.05, "phase residual ratio")
        require(handoff.get("workload_phase_maximum_overhead_ratio") == 1.03, "phase overhead ratio")
        exact_int(handoff.get("workload_phase_private_bytes_max"), 65536, "phase private bytes")
        require(handoff.get("workload_phase_execution") == "deferred", "phase execution state")
        exact_bool(handoff.get("workload_phase_performance_claim_authorized"), False, "phase performance claim")
        exact_int(handoff.get("split_debug_authority_version"), 1, "split-debug authority version")
        exact_int(handoff.get("split_debug_builds"), 2, "split-debug builds")
        exact_int(handoff.get("split_debug_behavior_executions"), 60, "split-debug executions")
        exact_int(handoff.get("split_debug_behavior_pairs"), 30, "split-debug pairs")
        exact_int(handoff.get("split_debug_companion_controls"), 8, "split-debug controls")
        exact_int(handoff.get("split_debug_symbol_resolutions"), 12, "split-debug symbols")
        require(handoff.get("split_debug_minimum_runtime_reduction") == 0.5, "split-debug reduction")
        exact_bool(handoff.get("split_debug_product_adoption"), False, "split-debug product adoption")
        exact_bool(handoff.get("diagnostic_restart_on_task_change"), True, "diagnostic restart")
        exact_int(handoff.get("task_value_strata"), 5, "task-value strata")
        exact_int(handoff.get("task_value_tasks"), 60, "task-value tasks")
        require(handoff.get("qualified_private_facets") == ["generic_control", "sysv_call_arguments", "linux_syscall_arguments"], "qualified private facets")
        require(handoff.get("retained_existing_facets") == ["syscall_number", "stack_pivot"], "retained existing facets")
        exact_int(handoff.get("task_value_regressions"), 0, "task-value regressions")
        exact_int(handoff.get("task_value_incorrect_promotions"), 0, "task-value incorrect promotions")
        exact_int(handoff.get("task_value_incremental_gains"), 26, "task-value gains")
        exact_int(handoff.get("task_value_unique_queries"), 60, "unique task queries")
        exact_bool(handoff.get("task_value_human_blind_claim"), False, "human blind claim")
        exact_bool(handoff.get("task_value_presentation_causal"), False, "presentation causal")
        exact_int(handoff.get("lc08b_policy_cells"), 9, "LC-08B policy cells")
        exact_int(handoff.get("private_role_record_bytes"), 8, "private role record bytes")
        exact_int(handoff.get("private_role_arena_bytes"), 32768, "private role arena bytes")
        exact_int(handoff.get("ordered_two_pop_structural_pairs"), 30, "ordered two-pop pairs")
        require(handoff.get("ordered_two_pop_task_decision") == "defer_new_runtime_tuple_representation", "ordered two-pop decision")
        exact_int(handoff.get("ordered_two_pop_incremental_gains"), 0, "ordered two-pop gains")
        exact_int(handoff.get("score_pattern_rows"), 25, "score pattern rows")
        exact_int(handoff.get("scored_pattern_rows"), 14, "scored pattern rows")
        exact_int(handoff.get("null_pattern_rows"), 11, "null pattern rows")
        exact_int(handoff.get("score_null_mutations"), 25, "score/null mutations")
        exact_int(handoff.get("score_null_independent_rejections"), 100, "score/null rejections")
        exact_int(handoff.get("ordered_two_pop_producer_generations"), 3, "producer generations")
        exact_int(handoff.get("ordered_two_pop_producer_pair_checks"), 90, "producer pair checks")
        exact_int(handoff.get("score_null_producer_generations"), 3, "score producer generations")
        exact_int(handoff.get("controlled_coordinate_targets"), 6, "coordinate targets")
        exact_int(handoff.get("controlled_coordinate_positive_cases"), 8, "coordinate positives")
        exact_int(handoff.get("controlled_coordinate_mutation_rejections"), 4, "coordinate mutations")
        exact_int(handoff.get("controlled_coordinate_semantic_negatives"), 4, "coordinate negatives")
        exact_int(handoff.get("controlled_coordinate_cells"), 9, "coordinate cells")
        exact_int(handoff.get("controlled_coordinate_qualified_cells"), 9, "qualified coordinate cells")
        exact_int(handoff.get("controlled_coordinate_positive_anchors"), 18, "coordinate anchors")
        exact_bool(handoff.get("natural_coordinate_campaign_qualified"), False, "natural coordinate campaign")
        exact_bool(handoff.get("comparative_coverage_claim_authorized"), False, "comparative coverage claim")
        require(handoff.get("natural_coordinate_campaign_id") == "s13-p083-natural-coordinate-v1", "natural campaign id")
        require(handoff.get("natural_coordinate_campaign_status") == "frozen_replay_and_layered_terminal_attribution_candidate", "natural campaign status")
        exact_int(handoff.get("natural_coordinate_planned_targets"), 12, "natural campaign targets")
        exact_int(handoff.get("natural_coordinate_planned_executions"), 48, "natural campaign executions")
        exact_int(handoff.get("natural_coordinate_cells"), 9, "natural campaign cells")
        exact_int(handoff.get("natural_coordinate_controls"), 108, "natural campaign controls")
        exact_bool(handoff.get("natural_coordinate_outcome_blind"), True, "natural campaign outcome blind")
        exact_bool(handoff.get("natural_coordinate_reroll"), False, "natural campaign reroll")
        for key, expected in {
            "natural_coordinate_selected_targets": 12,
            "natural_coordinate_completed_executions": 48,
            "natural_coordinate_completed_controls": 108,
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
        }.items():
            exact_int(handoff.get(key), expected, key)
        exact_bool(handoff.get("abi_role_public_projection"), False, "ABI role public projection")

        require(role.get("patch") == 78 and role.get("sprint") == 13, "role authority identity")
        contract = role.get("decision_contract")
        require(isinstance(contract, dict), "role decision contract")
        exact_int(contract.get("all_exact_single_pop_patterns_accounted"), 16, "role count")
        exact_int(contract.get("generic_register_control_patterns"), 15, "generic role count")
        exact_int(contract.get("sysv_call_argument_patterns"), 6, "call role count")
        exact_int(contract.get("linux_syscall_argument_patterns"), 6, "syscall role count")
        require(contract.get("linux_syscall_argument_4_register") == "r10", "Linux syscall argument 4")
        require(contract.get("sysv_call_argument_4_register") == "rcx", "SysV call argument 4")
        exact_int(contract.get("new_public_fields"), 0, "role public fields")
        exact_int(contract.get("score_changes"), 0, "role score changes")

        exact_int(evidence.get("natural_coordinate_frozen_replay_targets"), 12, "frozen replay targets")
        exact_int(evidence.get("natural_coordinate_frozen_replay_executions"), 48, "frozen replay executions")
        exact_int(evidence.get("natural_coordinate_terminal_execution_outcomes"), 48, "terminal executions")
        exact_int(evidence.get("natural_coordinate_terminal_relation_outcomes"), 48, "terminal relations")
        exact_int(evidence.get("natural_coordinate_terminal_observations"), 36, "terminal observations")
        exact_int(evidence.get("natural_coordinate_terminal_cells"), 9, "terminal cells")
        exact_int(evidence.get("natural_coordinate_terminal_precedence_mutations"), 16, "terminal precedence mutations")
        require(evidence.get("natural_coordinate_frozen_replay_id") == "s13-p085-natural-frozen-replay-v1", "frozen replay id")

        for required_key in (
            "gitless_full_topology_reauthenticated",
            "source_recovery_initial_open_residue_removed",
            "source_recovery_posthash_topology_reauthenticated",
            "abi_development_confirmation_semantically_disjoint",
            "abi_analyzer_copy_pinned_and_reauthenticated",
            "abi_targets_reauthenticated_per_command",
            "abi_evidence_no_replace_publication",
            "natural_targets_reauthenticated_per_tool",
            "natural_structure_recomputed_from_membership",
            "explicit_candidate_tree_authority_required",
            "frozen_natural_target_reroll_prohibited",
            "terminal_attribution_layered",
        ):
            exact_bool(transaction.get(required_key), True, required_key)

        exact_int(handoff.get("natural_coordinate_frozen_replay_targets"), 12, "handoff replay targets")
        exact_int(handoff.get("natural_coordinate_frozen_replay_executions"), 48, "handoff replay executions")
        exact_int(handoff.get("natural_coordinate_terminal_execution_outcomes"), 48, "handoff terminal executions")
        exact_int(handoff.get("natural_coordinate_terminal_relation_outcomes"), 48, "handoff terminal relations")
        exact_int(handoff.get("natural_coordinate_terminal_observations"), 36, "handoff terminal observations")
        exact_int(handoff.get("natural_coordinate_terminal_cells"), 9, "handoff terminal cells")
        exact_int(handoff.get("natural_coordinate_terminal_precedence_mutations"), 16, "handoff terminal precedence")

        for relative in closeout.get("required_closeout_documents", []):
            require((ROOT / relative).is_file(), f"missing closeout document: {relative}")
        sprint12 = (ROOT / "docs/sprints/sprint-12-plan.md").read_text(encoding="utf-8")
        sprint13 = (ROOT / "docs/sprints/sprint-13-plan.md").read_text(encoding="utf-8")
        require("Patch 088 correction and split-debug packaging experiment candidate" in sprint12, "Sprint 12 marker")
        require("Patch 088 correction and split-debug packaging experiment candidate" in sprint13, "Sprint 13 marker")
        makefile = MAKEFILE.read_text(encoding="utf-8")
        require("sprint13-p088-acceptance-smoke:" in makefile, "P087 acceptance target")
        validation = next((line for line in makefile.splitlines() if line.startswith("validation-smoke:")), "")
        require("patch079-corrective-regression-smoke" in validation, "P079 corrective integration")
        require("sprint13-register-role-decision-smoke" in validation, "Sprint 13 role integration")
        require("sprint13-register-role-task-value-smoke" in validation, "Sprint 13 task-value integration")
        require("sprint13-role-facet-smoke" in validation, "Sprint 13 role-facet integration")
        require("sprint13-role-policy-smoke" in validation, "Sprint 13 role-policy integration")
        require("sprint13-ordered-two-pop-role-task-value-smoke" in validation, "ordered two-pop integration")
        require("sprint13-score-null-authority-smoke" in validation, "score/null integration")
        require("sprint13-positive-coordinate-anchor-smoke" in validation, "coordinate preflight integration")
        require("patch081-corrective-regression-smoke" in validation, "Patch 081 corrective integration")
        require("patch082-corrective-regression-smoke" in validation, "Patch 082 corrective integration")
        require("patch083-corrective-regression-smoke" in validation, "Patch 083 corrective integration")
        require("sprint13-natural-coordinate-campaign-smoke" in validation, "natural coordinate selftest integration")
        require("sprint13-abi-role-query-contract-smoke" in validation, "ABI role contract integration")
        require("sprint13-lifecycle-denominator-smoke" in validation, "lifecycle denominator integration")
        require("patch087-corrective-regression-smoke" in validation, "Patch 087 corrective integration")
        require("sprint13-workload-phase-attribution-smoke" in validation, "P087 phase authority integration")
        require("sprint13-split-debug-packaging-contract-smoke" in validation, "P088 split-debug contract integration")
        require("sprint12-closeout-smoke" in validation, "closeout integration")
    except (OSError, json.JSONDecodeError, CloseoutError) as exc:
        print(f"sprint12-closeout-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "sprint12-closeout-smoke: ok sprint=12 patches=27 "
        "status=retrospective-recorded-and-sprint13-p088-candidate decision=defer "
        "public_fields=0 roles=16 r10=syscall-arg4 qualified_private_facets=3 "
        "deferred_facets=2 tuple_decision=defer score_changes=0 producer_generations=3 coordinate_anchors=18 natural_campaign=terminal-zero-qualified abi_role_queries=36 lifecycle_events=87 phase_executions=160 split_debug_builds=2 split_debug_executions=60 product_adoption=0 next_patch=89"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
