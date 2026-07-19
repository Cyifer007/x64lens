#!/usr/bin/env python3
"""Validate benchmark/capability staging and the twenty-two-sprint roadmap."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "tests/expected/research-stage-gates.json"


class GateError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def load_spec() -> dict:
    try:
        data = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot load {SPEC_PATH.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(data, dict), "top-level specification must be an object")
    return data


def main() -> int:
    try:
        spec = load_spec()
        require(spec.get("version") == 2, "unsupported specification version")
        require(spec.get("completed_sprints") == 10, "completed_sprints must be 10")
        require(spec.get("active_sprint") == 11, "active_sprint must be 11")
        require(spec.get("canonical_roadmap") == "docs/roadmap-22-sprints.md", "canonical roadmap mismatch")

        diagnostic = spec.get("diagnostic_sprint")
        freeze = spec.get("campaign_freeze_sprint")
        preview = spec.get("preview_sprint")
        campaign = spec.get("publication_campaign_sprint")
        release = spec.get("release_sprint")
        require([diagnostic, freeze, preview, campaign, release] == [11, 15, 16, 17, 22], "milestone sprint mismatch")

        stages = spec.get("stages")
        require(isinstance(stages, list) and len(stages) == 7, "expected seven stage records")
        expected_stage_ids = [
            "diagnostic_foundation",
            "capability_hardening",
            "campaign_freeze",
            "preview",
            "comparative_campaign",
            "defensive_value",
            "replication_release",
        ]
        require([stage.get("id") for stage in stages] == expected_stage_ids, "stage order or identity mismatch")

        prior_end = 10
        for stage in stages:
            start = stage.get("start_sprint")
            end = stage.get("end_sprint")
            require(isinstance(start, int) and isinstance(end, int), f"stage {stage.get('id')} needs integer bounds")
            require(start == prior_end + 1, f"stage {stage.get('id')} is not contiguous")
            require(start <= end, f"stage {stage.get('id')} has inverted bounds")
            prior_end = end
        require(prior_end == release, "stage sequence does not end at release sprint")
        require(stages[0].get("frozen") is False, "diagnostic stage must remain mutable")
        require(stages[1].get("frozen") is False, "capability-hardening stage must remain mutable")
        require(all(stage.get("frozen") is True for stage in stages[2:]), "freeze and later stages must be frozen")

        gates = spec.get("capability_gates")
        require(isinstance(gates, list) and len(gates) == 9, "expected nine capability gates")
        gate_ids = [gate.get("id") for gate in gates]
        require(len(gate_ids) == len(set(gate_ids)), "duplicate capability gate")
        gate_deadlines = {"campaign_freeze": freeze, "preview": preview}
        for gate in gates:
            owner = gate.get("owner_sprint")
            deadline_name = gate.get("required_before")
            require(deadline_name in gate_deadlines, f"unknown deadline for {gate.get('id')}")
            require(isinstance(owner, int) and 11 <= owner <= 15, f"invalid owner sprint for {gate.get('id')}")
            require(owner <= gate_deadlines[deadline_name], f"{gate.get('id')} is scheduled after its deadline")
            require(gate.get("status") in {"planned", "implemented", "resolved"}, f"invalid status for {gate.get('id')}")

        profiles = spec.get("conditional_profiles")
        require(isinstance(profiles, list) and len(profiles) == 3, "expected three conditional profiles")
        profile_ids = [profile.get("id") for profile in profiles]
        require(len(profile_ids) == len(set(profile_ids)), "duplicate conditional profile")
        for profile in profiles:
            require(profile.get("default") is False, f"conditional profile {profile.get('id')} cannot be default")
            require(profile.get("preserves_reference_profile") is True, f"conditional profile {profile.get('id')} must preserve reference")
            require(profile.get("decision_sprint") in {13, 14}, f"unexpected decision sprint for {profile.get('id')}")

        roadmap = ROOT / spec["canonical_roadmap"]
        require(roadmap.is_file(), "canonical roadmap is missing")
        roadmap_text = roadmap.read_text(encoding="utf-8")
        for needle in (
            "Diagnostic measurement checkpoint",
            "Campaign freeze",
            "Research preview candidate",
            "First research release",
            "Sprint 22",
        ):
            require(needle in roadmap_text, f"canonical roadmap missing: {needle}")

        for sprint in range(1, release + 1):
            plan = ROOT / f"docs/sprints/sprint-{sprint:02d}-plan.md"
            require(plan.is_file(), f"missing sprint plan: {plan.relative_to(ROOT)}")

        old_roadmap = ROOT / "docs/roadmap-18-sprints.md"
        require(old_roadmap.is_file(), "eighteen-sprint compatibility file is missing")
        old_text = old_roadmap.read_text(encoding="utf-8").lower()
        require("superseded" in old_text and "roadmap-22-sprints.md" in old_text, "eighteen-sprint roadmap is not marked superseded")

    except GateError as exc:
        print(f"research-stage-gates-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "research-stage-gates-smoke: ok "
        f"stages={len(stages)} capability_gates={len(gates)} "
        f"conditional_profiles={len(profiles)} release_sprint={release} "
        "completed_sprints=10 active_sprint=11"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
