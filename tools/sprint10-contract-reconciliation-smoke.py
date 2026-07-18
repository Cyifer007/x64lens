#!/usr/bin/env python3
"""Reconcile Sprint 10 semantic families, exact patterns, and fixture suites."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEMANTIC = ROOT / "tests" / "expected" / "sprint10-family-coverage.json"
DEFAULT_EXACT = ROOT / "tests" / "expected" / "sprint10-exact-pattern-catalog.json"
DEFAULT_SUITE = ROOT / "tests" / "expected" / "sprint10-fixture-suite.json"
DEFAULT_REPORT = ROOT / "tests" / "expected" / "x64lens-report-sprint10-effects-0.2.0.json"


def fail(message: str) -> "NoReturn":
    print(f"sprint10-contract-reconciliation-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot load {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


SINGLE_POP_LABELS = {
    "pop rax; ret", "pop rcx; ret", "pop rdx; ret", "pop rbx; ret",
    "pop rsp; ret", "pop rbp; ret", "pop rsi; ret", "pop rdi; ret",
    "pop r8; ret", "pop r9; ret", "pop r10; ret", "pop r11; ret",
    "pop r12; ret", "pop r13; ret", "pop r14; ret", "pop r15; ret",
}

LABEL_TO_FAMILY = {
    "ret": "ret",
    "ret imm16": "ret_imm16",
    "syscall; ret": "syscall_ret",
    "leave; ret": "leave_ret",
    "pop rsp; ret": "pop_rsp_ret",
    "pop reg; pop reg; ret": "ordered_multi_pop",
    "mov reg, reg; ret": "register_transfer",
    "add rsp, imm8; ret": "stack_adjust",
    "mov [base], value; ret": "memory_write",
    "mov value, [base]; ret": "memory_read",
}


def parse_score_policy(policy: Any, family_id: str) -> int | None | str:
    if policy == "unscored":
        return None
    if policy == "family-specific existing scores":
        if family_id != "single_pop":
            fail(f"family {family_id}: family-specific score policy is invalid")
        return "family-specific"
    if not isinstance(policy, str):
        fail(f"family {family_id}: score policy must be a string")
    match = re.fullmatch(r"scored:(0|[1-9][0-9]*)", policy)
    if match is None:
        fail(f"family {family_id}: invalid score policy {policy!r}")
    value = int(match.group(1))
    if not 0 <= value <= 100:
        fail(f"family {family_id}: score policy is outside 0..100")
    return value


def family_for_label(label: str) -> str:
    if label in SINGLE_POP_LABELS:
        return "single_pop"
    family_id = LABEL_TO_FAMILY.get(label)
    if family_id is None:
        fail(f"no semantic family maps exact pattern {label!r}")
    return family_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--semantic", type=Path, default=DEFAULT_SEMANTIC)
    parser.add_argument("--exact", type=Path, default=DEFAULT_EXACT)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    semantic = load(args.semantic.resolve())
    exact = load(args.exact.resolve())
    suite = load(args.suite.resolve())
    report = load(args.report.resolve())

    families = semantic.get("families")
    patterns = exact.get("patterns")
    fixtures = suite.get("families")
    gadgets = report.get("gadgets")
    if not isinstance(families, list) or len(families) != 11:
        fail("semantic family contract must contain 11 families")
    if not isinstance(patterns, list) or len(patterns) != 25:
        fail("exact pattern catalog must contain 25 patterns")
    if not isinstance(fixtures, dict) or len(fixtures) != 5:
        fail("fixture suite must contain 5 groups")
    if not isinstance(gadgets, list) or len(gadgets) != 25:
        fail("one-per-pattern expected report must contain 25 candidates")

    profile = exact.get("reference_profile")
    expected_profile = {
        "tool_version": "0.1.0-dev",
        "report_schema": "0.2.0",
        "pattern_count": 25,
        "gadget_record_bytes": 112,
        "candidate_evidence_record_bytes": 48,
        "memory_effect_record_bytes": 16,
        "candidate_effect_record_bytes": 24,
        "candidate_capacity": 4096,
        "analysis_arena_bytes": 819200,
    }
    if profile != expected_profile:
        fail(f"exact catalog reference profile mismatch: {profile!r}")
    semantic_profile = semantic.get("reference_profile", {})
    for key in (
        "tool_version", "report_schema", "candidate_capacity",
        "gadget_record_bytes", "candidate_evidence_record_bytes",
        "memory_effect_record_bytes", "candidate_effect_record_bytes",
        "analysis_arena_bytes",
    ):
        if semantic_profile.get(key) != expected_profile.get(key):
            fail(f"semantic/exact reference profile disagreement for {key}")

    ids = [entry.get("pattern_id") for entry in patterns]
    if ids != list(range(1, 26)):
        fail(f"pattern IDs must be the contiguous range 1..25: {ids!r}")
    labels = [entry.get("label") for entry in patterns]
    report_labels = [gadget.get("pattern") for gadget in gadgets]
    if labels != report_labels:
        fail("exact catalog labels disagree with one-per-pattern report order")

    family_entries = {entry.get("id"): entry for entry in families if isinstance(entry, dict)}
    if set(family_entries) != {
        "ret", "ret_imm16", "single_pop", "syscall_ret", "leave_ret",
        "pop_rsp_ret", "ordered_multi_pop", "register_transfer",
        "stack_adjust", "memory_write", "memory_read",
    }:
        fail("semantic family identifiers are incomplete or duplicated")
    parsed_policies = {
        family_id: parse_score_policy(entry.get("score_policy"), family_id)
        for family_id, entry in family_entries.items()
    }

    exact_only = 0
    partial = 0
    scored = 0
    for entry, gadget in zip(patterns, gadgets):
        for key in ("label", "semantic_class", "evidence_kind", "effect_model_complete", "score"):
            report_key = {
                "label": "pattern",
                "semantic_class": "semantic_class",
                "evidence_kind": None,
                "effect_model_complete": None,
                "score": "score",
            }[key]
            if key == "evidence_kind":
                observed = gadget.get("evidence", {}).get("kind")
            elif key == "effect_model_complete":
                observed = gadget.get("architectural_effects", {}).get("model_complete")
            else:
                observed = gadget.get(report_key)
            if entry.get(key) != observed:
                fail(f"pattern {entry.get('pattern_id')} field {key} disagrees with expected report")
        if entry["semantic_class"] == "unknown_candidate":
            exact_only += 1
        if entry["effect_model_complete"] is False:
            partial += 1
        if entry["score"] is not None:
            scored += 1
        family_id = family_for_label(str(entry["label"]))
        score_policy = parsed_policies[family_id]
        if score_policy != "family-specific" and entry["score"] != score_policy:
            fail(
                f"pattern {entry['pattern_id']} score {entry['score']!r} "
                f"disagrees with family {family_id} policy {score_policy!r}"
            )
        for path_key in ("fixture",):
            if not (ROOT / entry[path_key]).is_file():
                fail(f"pattern {entry['pattern_id']} missing fixture {entry[path_key]}")
        if not isinstance(entry.get("false_positive_boundary"), str) or not entry["false_positive_boundary"].strip():
            fail(f"pattern {entry['pattern_id']} lacks a false-positive boundary")

    if (exact_only, partial, scored) != (8, 2, 14):
        fail(f"catalog population mismatch: exact_only={exact_only} partial={partial} scored={scored}")
    partial_labels = {entry["label"] for entry in patterns if not entry["effect_model_complete"]}
    if partial_labels != {"pop rsp; ret", "syscall; ret"}:
        fail(f"partial effect-model set mismatch: {sorted(partial_labels)}")

    for fixture_id, fixture in fixtures.items():
        fixture_path = ROOT / str(fixture.get("fixture", ""))
        validator_path = ROOT / str(fixture.get("disassembly_validator", ""))
        if not fixture_path.is_file():
            source_fallback = ROOT / "tests" / "toy-src" / f"{fixture_path.name}.S"
            if not source_fallback.is_file():
                fail(f"fixture group {fixture_id} has no generated binary or source fixture")
        if not validator_path.is_file():
            fail(f"fixture group {fixture_id} is missing its disassembly validator")
        boundaries = fixture.get("false_positive_boundaries")
        if not isinstance(boundaries, list) or len(boundaries) < 2:
            fail(f"fixture group {fixture_id} lacks false-positive boundaries")
        if not isinstance(fixture.get("score_policy"), str) or not fixture["score_policy"].strip():
            fail(f"fixture group {fixture_id} lacks score policy")

    print(
        "sprint10-contract-reconciliation-smoke: ok "
        "semantic_families=11 exact_patterns=25 fixture_groups=5 "
        "semantic=17 exact_only=8 scored=14 model_complete=23 model_partial=2"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
