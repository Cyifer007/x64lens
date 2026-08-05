#!/usr/bin/env python3
"""Validate the Patch 078 Sprint 12 correction and Sprint 13 entry-candidate authority."""
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
            authority.get("status") == "closeout_correction_and_sprint13_entry_candidate_pending_acceptance",
            "Sprint 12 must remain pending P078 acceptance",
        )
        exact_int(authority.get("current_patch"), 78, "current_patch")
        exact_int(authority.get("superseded_closeout_patch"), 77, "superseded closeout")
        exact_int(authority.get("next_patch"), 79, "next_patch")
        require(authority.get("next_patch_tranche") == "blinded-register-role-task-value-after-p078-acceptance", "next tranche")
        require(authority.get("acceptance_target") == "sprint13-p078-acceptance-smoke", "acceptance target")
        require(stages.get("completed_sprints") == 11 and stages.get("active_sprint") == 12, "stage chronology")

        boundary = authority.get("patch078_boundary")
        require(isinstance(boundary, dict), "Patch 078 boundary")
        exact_bool(boundary.get("remaining_patch077_corrections"), True, "remaining corrections")
        exact_bool(boundary.get("runtime_parser_or_report_change"), False, "runtime boundary")
        exact_bool(boundary.get("runtime_source_include_schema_change"), False, "runtime tracked boundary")
        exact_bool(boundary.get("private_dynamic_metadata_sidecar_preserved"), True, "sidecar")
        exact_int(boundary.get("dynamic_metadata_context_bytes"), 9904, "dynamic metadata context")
        exact_int(boundary.get("private_metadata_context_bytes"), 13064, "private metadata context")
        exact_int(boundary.get("mixed_carrier_capacity"), 64, "mixed carrier cap")
        exact_int(boundary.get("search_record_capacity"), 64, "search record cap")
        exact_int(boundary.get("search_value_byte_capacity"), 4096, "search byte cap")
        require(boundary.get("textrel_state") == "private", "textrel state")
        require(boundary.get("rpath_state") == "private_distinct", "RPATH state")
        require(boundary.get("runpath_state") == "private_distinct", "RUNPATH state")
        require(boundary.get("private_failure_snapshot_semantics") == "deterministic_parse_prefix", "private failure semantics")
        exact_bool(boundary.get("path_splitting"), False, "path splitting")
        exact_bool(boundary.get("origin_expansion"), False, "ORIGIN expansion")
        exact_int(boundary.get("target_derived_opens"), 0, "target-derived opens")
        require(boundary.get("gitless_docker_source") == "exact_staged_tree_membership", "Git-less Docker source")
        require(boundary.get("reviewed_base_modes") == ["staged", "committed"], "reviewed base modes")
        exact_int(boundary.get("public_fields_added"), 0, "public fields")
        exact_int(boundary.get("score_changes"), 0, "score changes")
        exact_bool(boundary.get("existing_coarse_pie_field_reinterpreted"), False, "PIE reinterpretation")
        exact_bool(boundary.get("runtime_cet_enforcement_claimed"), False, "runtime CET")
        exact_bool(boundary.get("schema_changed"), False, "schema change")

        entry = authority.get("sprint13_entry_decision")
        require(isinstance(entry, dict), "Sprint 13 entry decision")
        for key, expected in {
            "exact_pop_patterns_accounted": 16,
            "generic_register_control_patterns": 15,
            "sysv_call_argument_patterns": 6,
            "linux_syscall_argument_patterns": 6,
            "new_public_fields": 0,
            "new_scores": 0,
        }.items():
            exact_int(entry.get(key), expected, key)
        require(entry.get("linux_syscall_arg4_register") == "r10", "Linux syscall argument 4")
        require(entry.get("sysv_call_arg4_register") == "rcx", "SysV call argument 4")
        require(entry.get("syscall_number_register") == "rax", "syscall number register")
        require(entry.get("stack_pivot_register") == "rsp", "stack pivot register")
        require(entry.get("next_gate") == "blinded_task_value", "next role gate")

        preserved = authority.get("preserved_authorities")
        require(isinstance(preserved, dict), "preserved authorities")
        require(preserved.get("executable_mapping") == "PT_LOAD_plus_PF_X_file_backed_ranges", "executable mapping")
        require(preserved.get("section_headers") == "bounded_metadata_and_annotations_only", "section boundary")
        require(preserved.get("candidate_4097") == "exit_6_before_stdout", "capacity boundary")
        require(preserved.get("malformed_parse") == "no_partial_stdout", "malformed boundary")
        require(preserved.get("reference_runtime") == "dependency_free_decoder_free_one_worker", "reference runtime")

        for relative in authority.get("required_documents", []):
            require((ROOT / relative).is_file(), f"missing {relative}")
        sprint12 = (ROOT / "docs/sprints/sprint-12-plan.md").read_text(encoding="utf-8")
        sprint13 = (ROOT / "docs/sprints/sprint-13-plan.md").read_text(encoding="utf-8")
        require("Closeout correction and Sprint 13 entry candidate at Patch 078" in sprint12, "Sprint 12 marker")
        require("Entry candidate at Patch 078; activation pending acceptance" in sprint13, "Sprint 13 marker")
    except (OSError, json.JSONDecodeError, Error) as exc:
        print(f"sprint12-continuation-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "sprint12-continuation-smoke: ok sprint=12 status=closeout-correction "
        "patch=78 textrel=private rpath=private runpath=private roles=16 "
        "r10=syscall-arg4 public_fields_added=0 next_patch=79"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
