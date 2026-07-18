#!/usr/bin/env python3
"""Validate the Sprint 10 family/effect/fallback coverage contract."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "expected" / "sprint10-family-coverage.json"

REQUIRED_FAMILIES = {
    "ret",
    "ret_imm16",
    "single_pop",
    "syscall_ret",
    "leave_ret",
    "pop_rsp_ret",
    "ordered_multi_pop",
    "register_transfer",
    "stack_adjust",
    "memory_write",
    "memory_read",
}

FAIL_FAST_RECIPES = (
    "json-smoke",
    "sprint10-primitive-smoke",
    "sprint10-register-transfer-smoke",
    "sprint10-stack-adjust-smoke",
    "sprint10-memory-smoke",
    "analyze-smoke",
    "arena-smoke",
)

PATTERN_TO_FAMILY = {
    "pop reg; pop reg; ret": "ordered_multi_pop",
    "mov reg, reg; ret": "register_transfer",
    "add rsp, imm8; ret": "stack_adjust",
    "mov [base], value; ret": "memory_write",
    "mov value, [base]; ret": "memory_read",
}


def fail(message: str) -> None:
    raise ValueError(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        fail(f"{path}: top level must be an object")
    return value


def main() -> int:
    manifest = load(MANIFEST)
    if manifest.get("schema_version") != 1:
        fail("coverage manifest schema_version must be 1")

    profile = manifest.get("reference_profile")
    if not isinstance(profile, dict):
        fail("reference_profile must be an object")
    expected_profile = {
        "tool_version": "0.1.0-dev",
        "report_schema": "0.2.0",
        "candidate_capacity": 4096,
        "gadget_record_bytes": 112,
        "candidate_evidence_record_bytes": 48,
        "memory_effect_record_bytes": 16,
        "candidate_effect_record_bytes": 24,
        "analysis_arena_bytes": 819200,
        "mandatory_decoder": False,
        "mandatory_threads": False,
    }
    if profile != expected_profile:
        fail(f"reference_profile mismatch: {profile!r}")

    families = manifest.get("families")
    if not isinstance(families, list):
        fail("families must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    for index, family in enumerate(families):
        if not isinstance(family, dict):
            fail(f"families[{index}] must be an object")
        family_id = family.get("id")
        if not isinstance(family_id, str) or not family_id:
            fail(f"families[{index}].id must be non-empty")
        if family_id in by_id:
            fail(f"duplicate family id {family_id}")
        by_id[family_id] = family
        for key in (
            "pattern",
            "semantic_class",
            "clobber_policy",
            "score_policy",
            "fixture",
            "validation_target",
            "false_positive_boundary",
        ):
            value = family.get(key)
            if not isinstance(value, str) or not value.strip():
                fail(f"family {family_id}: {key} must be non-empty")
        effects = family.get("effects")
        if not isinstance(effects, list) or not effects or any(not isinstance(x, str) or not x for x in effects):
            fail(f"family {family_id}: effects must be a non-empty string array")
        fixture = ROOT / family["fixture"]
        if not fixture.is_file():
            fail(f"family {family_id}: missing fixture {family['fixture']}")

    if set(by_id) != REQUIRED_FAMILIES:
        fail(
            "family set mismatch: "
            f"missing={sorted(REQUIRED_FAMILIES - set(by_id))} "
            f"extra={sorted(set(by_id) - REQUIRED_FAMILIES)}"
        )

    fixtures = manifest.get("fixture_expectations")
    if not isinstance(fixtures, list) or len(fixtures) != 4:
        fail("fixture_expectations must contain exactly four Sprint 10 reports")

    fixture_count = 0
    cross_family_count = 0
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            fail("fixture expectation must be an object")
        report_path = ROOT / str(fixture.get("report", ""))
        report = load(report_path)
        gadgets = report.get("gadgets")
        counts = report.get("counts")
        if not isinstance(gadgets, list) or not isinstance(counts, dict):
            fail(f"{report_path}: missing gadgets/counts")
        if len(gadgets) != fixture.get("raw_candidates"):
            fail(f"{report_path}: raw candidate array length mismatch")
        if counts.get("raw_candidate_count") != fixture.get("raw_candidates"):
            fail(f"{report_path}: raw_candidate_count mismatch")
        if counts.get("scored_candidate_count") != fixture.get("scored_candidates"):
            fail(f"{report_path}: scored_candidate_count mismatch")
        observed = Counter(gadget.get("pattern") for gadget in gadgets)
        expected_patterns = fixture.get("patterns")
        if not isinstance(expected_patterns, dict) or observed != Counter(expected_patterns):
            fail(f"{report_path}: pattern distribution mismatch: {dict(observed)!r}")

        for gadget in gadgets:
            pattern = gadget.get("pattern")
            family_id = PATTERN_TO_FAMILY.get(pattern)
            if family_id is None:
                continue
            family = by_id[family_id]
            if gadget.get("side_effects") != family["effects"]:
                fail(
                    f"{report_path}: {pattern} effects {gadget.get('side_effects')!r} "
                    f"!= {family['effects']!r}"
                )
            score_policy = family["score_policy"]
            if score_policy == "unscored" and gadget.get("score") is not None:
                fail(f"{report_path}: {pattern} must remain unscored")

        if fixture.get("id") == "register_transfer_cross_family":
            if observed["mov [base], value; ret"] != 1 or observed["mov value, [base]; ret"] != 1:
                fail("transfer fixture must expose both cross-family memory promotions")
            cross_family_count = 2
        fixture_count += 1

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in FAIL_FAST_RECIPES:
        marker = f"{target}:"
        start = makefile.find(marker)
        if start < 0:
            fail(f"missing Make target: {target}")
        recipe_start = makefile.find("\n\t", start)
        if recipe_start < 0 or recipe_start > makefile.find("\n\n", start):
            fail(f"missing recipe for Make target: {target}")
        first_recipe = makefile[recipe_start + 2 : makefile.find("\n", recipe_start + 2)]
        if not first_recipe.startswith("@set -eu;"):
            fail(f"Make target {target} is not fail-fast: {first_recipe!r}")

    print(
        "sprint10-family-coverage-smoke: ok "
        f"families={len(by_id)} fixtures={fixture_count} "
        f"cross_family_promotions={cross_family_count} "
        f"fail_fast_recipes={len(FAIL_FAST_RECIPES)} "
        "scored_policy=explicit false_positive_notes=complete"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"sprint10-family-coverage-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
