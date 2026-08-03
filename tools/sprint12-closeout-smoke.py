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


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CloseoutError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must contain an object")
    return value


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

        require(closeout.get("schema_version") == 1, "unsupported closeout schema")
        require(closeout.get("sprint") == 12 and closeout.get("status") == "closed", "Sprint 12 is not closed")
        require(closeout.get("closeout_patch") == 74, "Patch 074 must close Sprint 12")
        patches = closeout.get("completed_patches")
        require(patches == list(range(62, 75)), "Patch sequence must cover 062-074")
        require(closeout.get("next_sprint") == 13, "Sprint 13 must be next")
        require(closeout.get("acceptance_target") == "sprint12-p074-acceptance-smoke", "acceptance target mismatch")

        require(stages.get("completed_sprints") == 12, "completed_sprints must be 12")
        require(stages.get("active_sprint") == 13, "active_sprint must be 13")

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
        require(auth.get("current_authorization") is False, "public-policy authorization must remain false")
        require(auth.get("public_fields_added") == 0, "public role/property fields were added")
        require(disposition.get("public_role_property_fields_added") == 0, "closeout public-field count mismatch")
        require(disposition.get("existing_coarse_pie_field_reinterpreted") is False, "coarse PIE field was reinterpreted")
        require(disposition.get("runtime_cet_enforcement_claimed") is False, "runtime CET enforcement claim is forbidden")

        gap_disposition = gaps.get("patch_074_disposition")
        require(isinstance(gap_disposition, dict), "Patch 074 gap disposition is missing")
        require(gap_disposition.get("runtime_fields_added") == 0, "Patch 074 must add no mitigation field")
        require(gap_disposition.get("deferred_tranches") == closeout.get("deferred_mitigation_tranches"), "deferred mitigation tranches mismatch")

        evidence = closeout.get("diagnostic_evidence_boundary")
        require(evidence == {
            "external_natural_objects": 48,
            "external_natural_eligible_matches": 624,
            "external_natural_eligible_mismatches": 0,
            "external_natural_ambiguous": 48,
            "external_natural_unavailable": 192,
            "publication_eligible": False,
            "performance_claim_authorized": False,
            "positive_coordinate_anchors": 0,
        }, "diagnostic evidence boundary mismatch")

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
        require("Closed by Patch 074" in sprint12, "Sprint 12 plan is not closed by Patch 074")
        require("Active semantic capability completion sprint" in sprint13, "Sprint 13 plan is not active")

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
        "next_sprint=13"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
