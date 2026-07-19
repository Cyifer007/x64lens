#!/usr/bin/env python3
"""Reconcile Sprint 10 closeout state with maintained machine authorities."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT = ROOT / "tests/expected/sprint10-closeout.json"
CATALOG = ROOT / "tests/expected/sprint10-exact-pattern-catalog.json"
FAMILY = ROOT / "tests/expected/sprint10-family-coverage.json"
FIXTURES = ROOT / "tests/expected/sprint10-fixture-suite.json"
STAGES = ROOT / "tests/expected/research-stage-gates.json"


class CloseoutError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CloseoutError(message)


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CloseoutError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must contain an object")
    return value


def main() -> int:
    try:
        closeout = load(CLOSEOUT)
        catalog = load(CATALOG)
        family = load(FAMILY)
        fixtures = load(FIXTURES)
        stages = load(STAGES)

        require(closeout.get("schema_version") == 1, "unsupported closeout schema")
        require(closeout.get("sprint") == 10 and closeout.get("status") == "closed", "Sprint 10 is not closed")
        require(closeout.get("closeout_patch") == 54, "Patch 054 must close Sprint 10")
        require(closeout.get("completed_patches") == list(range(46, 55)), "Patch sequence must cover 046-054")
        require(closeout.get("next_sprint") == 11, "Sprint 11 must be next")

        expected_profile = {
            "tool_version": "0.1.0-dev",
            "report_schema": "0.2.0",
            "gadget_record_bytes": 112,
            "candidate_evidence_record_bytes": 48,
            "memory_effect_record_bytes": 16,
            "candidate_effect_record_bytes": 24,
            "candidate_capacity": 4096,
            "analysis_arena_bytes": 819200,
            "mandatory_decoder": False,
            "mandatory_threads": False,
        }
        require(closeout.get("reference_profile") == expected_profile, "reference profile mismatch")

        patterns = catalog.get("patterns")
        require(isinstance(patterns, list) and len(patterns) == 25, "exact-pattern catalog must contain 25 patterns")
        semantic = sum(item.get("semantic_class") != "unknown_candidate" for item in patterns)
        exact_only = sum(item.get("semantic_class") == "unknown_candidate" for item in patterns)
        scored = sum(item.get("score") is not None for item in patterns)
        complete = sum(item.get("effect_model_complete") is True for item in patterns)
        partial = sum(item.get("effect_model_complete") is False for item in patterns)

        families = family.get("families")
        groups = fixtures.get("families")
        require(isinstance(families, list) and len(families) == 11, "family contract count mismatch")
        require(isinstance(groups, dict) and len(groups) == 5, "fixture group count mismatch")

        observed_counts = {
            "semantic_family_contracts": len(families),
            "exact_patterns": len(patterns),
            "semantic_patterns": semantic,
            "exact_only_patterns": exact_only,
            "scored_patterns": scored,
            "complete_effect_models": complete,
            "partial_effect_models": partial,
            "fixture_groups": len(groups),
        }
        require(closeout.get("contract_counts") == observed_counts, f"contract counts mismatch: {observed_counts!r}")

        transition = closeout.get("research_transition")
        expected_transition = {
            "diagnostic_sprint": stages.get("diagnostic_sprint"),
            "campaign_freeze_sprint": stages.get("campaign_freeze_sprint"),
            "preview_sprint": stages.get("preview_sprint"),
            "publication_campaign_sprint": stages.get("publication_campaign_sprint"),
            "release_sprint": stages.get("release_sprint"),
        }
        require(transition == expected_transition == {
            "diagnostic_sprint": 11,
            "campaign_freeze_sprint": 15,
            "preview_sprint": 16,
            "publication_campaign_sprint": 17,
            "release_sprint": 22,
        }, "research transition mismatch")
        require(stages.get("completed_sprints") == 10 and stages.get("active_sprint") == 11, "stage status mismatch")

        for relative in closeout.get("required_closeout_documents", []):
            require((ROOT / relative).is_file(), f"missing closeout document: {relative}")

        sprint10 = (ROOT / "docs/sprints/sprint-10-plan.md").read_text(encoding="utf-8")
        sprint11 = (ROOT / "docs/sprints/sprint-11-plan.md").read_text(encoding="utf-8")
        require("Closed by Patch 054" in sprint10, "Sprint 10 plan is not closed")
        require("Active diagnostic measurement sprint" in sprint11, "Sprint 11 plan is not active")

        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        require("sprint10-closeout-smoke:" in makefile, "Make target is missing")
        validation_line = next((line for line in makefile.splitlines() if line.startswith("validation-smoke:")), "")
        require("sprint10-closeout-smoke" in validation_line, "closeout smoke is not part of validation-smoke")
        require("research-roadmap-consistency-smoke" in validation_line, "roadmap consistency is not part of validation-smoke")

    except (OSError, CloseoutError) as exc:
        print(f"sprint10-closeout-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "sprint10-closeout-smoke: ok "
        "sprint=10 patches=9 families=11 exact_patterns=25 semantic=17 exact_only=8 "
        "scored=14 model_complete=23 model_partial=2 fixture_groups=5 next_sprint=11"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
