#!/usr/bin/env python3
"""Reconcile the Sprint 12 closeout authority and Sprint 13 handoff."""

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
GAPS = ROOT / "benchmarks/task-definitions/sprint12-mitigation-competitive-gap-v1.json"
OVERLAP = ROOT / "benchmarks/task-definitions/sprint12-overlap-normalization-decision.json"
CONSTANTS = ROOT / "include/constants.inc"
STRUCTS = ROOT / "include/structs.inc"
MAKEFILE = ROOT / "Makefile"


class CloseoutError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CloseoutError(message)


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
        )
    except (OSError, json.JSONDecodeError) as exc:
        label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        raise CloseoutError(f"cannot load {label}: {exc}") from exc
    label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    require(isinstance(value, dict), f"{label} must contain an object")
    return value




def exact_int(value: Any, expected: int, label: str) -> None:
    require(type(value) is int and value == expected, f"{label} must be integer {expected}")


def exact_bool(value: Any, expected: bool, label: str) -> None:
    require(type(value) is bool and value is expected, f"{label} must be boolean {expected}")

def define(path: Path, name: str) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^%define\s+{re.escape(name)}\s+(.+?)\s*(?:;.*)?$", text, re.MULTILINE)
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
        gaps = load(GAPS)
        overlap = load(OVERLAP)

        exact_int(closeout.get("schema_version"), 1, "closeout.schema_version")
        exact_int(closeout.get("sprint"), 12, "closeout.sprint")
        require(closeout.get("status") == "superseded_closeout_candidate", "Patch 074 closeout authority is not marked superseded")
        exact_int(closeout.get("superseded_by_patch"), 75, "closeout.superseded_by_patch")
        require(closeout.get("current_authority") == "tests/expected/sprint12-continuation.json", "current continuation authority mismatch")
        exact_int(closeout.get("closeout_patch"), 74, "closeout.closeout_patch")
        patches = closeout.get("completed_patches")
        require(patches == list(range(62, 75)), "Patch sequence must cover 062-074")
        require(closeout.get("next_sprint") == 13, "Sprint 13 must be next")
        require(closeout.get("acceptance_target") == "sprint12-p074-acceptance-smoke", "acceptance target mismatch")

        exact_int(stages.get("completed_sprints"), 11, "stages.completed_sprints")
        exact_int(stages.get("active_sprint"), 12, "stages.active_sprint")

        profile = closeout.get("reference_profile")
        require(isinstance(profile, dict), "reference_profile must be an object")
        require(profile.get("tool_version") == string_define(CONSTANTS, "X64LENS_VERSION") == "0.1.0-dev", "tool version mismatch")
        require(profile.get("report_schema") == string_define(CONSTANTS, "X64LENS_SCHEMA") == "0.2.0", "schema version mismatch")
        require(profile.get("candidate_capacity") == integer_define(STRUCTS, "GADGET_RECORD_MAX") == 4096, "candidate capacity mismatch")
        expected_arena = (
            integer_define(STRUCTS, "GADGET_RECORD_SIZE")
            + integer_define(STRUCTS, "CANDIDATE_EVIDENCE_RECORD_SIZE")
            + integer_define(STRUCTS, "MEMORY_EFFECT_RECORD_SIZE")
            + integer_define(STRUCTS, "CANDIDATE_EFFECT_RECORD_SIZE")
        ) * profile["candidate_capacity"]
        require(profile.get("analysis_arena_bytes") == expected_arena == 851968, "analysis arena mismatch")
        require(profile.get("phdr_summary_bytes") == integer_define(STRUCTS, "PHDR_SUMMARY_RECORD_SIZE") == 264, "PHDR summary mismatch")
        require(profile.get("gnu_property_context_bytes") == 3160, "GNU-property context mismatch")
        require(profile.get("mandatory_decoder") is False and profile.get("mandatory_threads") is False, "reference profile changed")
        require(profile.get("target_mapping") == "read_only" and profile.get("target_execution") is False, "target safety boundary changed")

        disposition = closeout.get("loader_and_mitigation_disposition")
        require(isinstance(disposition, dict), "loader_and_mitigation_disposition must be an object")
        require(disposition.get("program_header_executable_authority") == "PT_LOAD_plus_PF_X_file_backed_ranges", "loader authority changed")
        require(disposition.get("overlap_normalization") == "deferred_under_measured_reopen_threshold", "overlap disposition changed")
        require(overlap.get("decision") == "defer_normalization_preserve_provenance", "overlap authority no longer defers")
        require(disposition.get("public_role_property_policy") == policy.get("decision") == "defer", "public-policy decision changed")
        auth = policy.get("authorization_rule")
        require(isinstance(auth, dict), "policy authorization_rule must be an object")
        exact_bool(auth.get("current_authorization"), False, "policy.current_authorization")
        exact_int(auth.get("public_fields_added"), 0, "policy.public_fields_added")
        exact_int(disposition.get("public_role_property_fields_added"), 0, "closeout.public_role_property_fields_added")
        exact_bool(disposition.get("existing_coarse_pie_field_reinterpreted"), False, "closeout.existing_coarse_pie_field_reinterpreted")
        exact_bool(disposition.get("runtime_cet_enforcement_claimed"), False, "closeout.runtime_cet_enforcement_claimed")

        gap_disposition = gaps.get("patch_074_disposition")
        require(isinstance(gap_disposition, dict), "Patch 074 gap disposition is missing")
        exact_int(gap_disposition.get("runtime_fields_added"), 0, "gap.runtime_fields_added")
        require(gap_disposition.get("deferred_tranches") == closeout.get("deferred_mitigation_tranches"), "deferred mitigation tranches mismatch")

        evidence = closeout.get("diagnostic_evidence_boundary")
        require(isinstance(evidence, dict) and set(evidence) == {
            "external_natural_objects", "external_natural_eligible_matches",
            "external_natural_eligible_mismatches", "external_natural_ambiguous",
            "external_natural_unavailable", "publication_eligible",
            "performance_claim_authorized", "positive_coordinate_anchors",
        }, "diagnostic evidence boundary shape mismatch")
        for key, expected in {
            "external_natural_objects": 48,
            "external_natural_eligible_matches": 624,
            "external_natural_eligible_mismatches": 0,
            "external_natural_ambiguous": 48,
            "external_natural_unavailable": 192,
            "positive_coordinate_anchors": 0,
        }.items():
            exact_int(evidence.get(key), expected, f"diagnostic_evidence_boundary.{key}")
        exact_bool(evidence.get("publication_eligible"), False,
                   "diagnostic_evidence_boundary.publication_eligible")
        exact_bool(evidence.get("performance_claim_authorized"), False,
                   "diagnostic_evidence_boundary.performance_claim_authorized")

        custody = closeout.get("corrective_custody_boundary")
        require(isinstance(custody, dict) and all(value is True for key, value in custody.items() if key != "delivery_custody_schema"), "one or more custody corrections are false")
        require(custody.get("delivery_custody_schema") == "x64lens-delivery-custody-v3", "delivery custody schema mismatch")

        handoff = closeout.get("sprint13_handoff")
        require(isinstance(handoff, dict), "Sprint 13 handoff missing")
        require(handoff.get("generic_exact_pop_semantic_decision") == "open", "generic pop decision must remain open")
        require(handoff.get("linux_syscall_r10_role_decision") == "open", "r10 decision must remain open")
        require(handoff.get("score_null_policy_freeze") == "open", "score/null policy must remain open")
        require(handoff.get("diagnostic_restart_on_task_change") is True, "task changes must restart affected diagnostics")

        for relative in closeout.get("required_closeout_documents", []):
            require((ROOT / relative).is_file(), f"missing closeout document: {relative}")

        sprint12 = (ROOT / "docs/sprints/sprint-12-plan.md").read_text(encoding="utf-8")
        sprint13 = (ROOT / "docs/sprints/sprint-13-plan.md").read_text(encoding="utf-8")
        require("Active at Patch 076" in sprint12, "Sprint 12 continuation chronology is missing")
        require("Planned semantic capability completion sprint" in sprint13, "Sprint 13 plan is not planned")

        makefile = MAKEFILE.read_text(encoding="utf-8")
        require("sprint12-closeout-smoke:" in makefile, "Sprint 12 closeout target is missing")
        validation = next((line for line in makefile.splitlines() if line.startswith("validation-smoke:")), "")
        require("sprint12-closeout-smoke" in validation, "Sprint 12 closeout is not in validation-smoke")
        sprint_closeout = next((line for line in makefile.splitlines() if line.startswith("sprint-closeout-smoke:")), "")
        require("sprint12-closeout-smoke" in sprint_closeout, "Sprint 12 closeout is not in sprint-closeout-smoke")

    except (OSError, CloseoutError) as exc:
        print(f"sprint12-closeout-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "sprint12-closeout-smoke: ok "
        f"sprint=12 patches={len(patches)} decision=defer public_fields=0 "
        f"external_natural_objects={evidence['external_natural_objects']} "
        f"eligible_matches={evidence['external_natural_eligible_matches']} "
        "superseded_by_patch=75 current_sprint=12"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
