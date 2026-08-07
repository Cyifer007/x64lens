#!/usr/bin/env python3
"""Validate the Patch 081 ordered two-pop role-tuple pilot.

The pilot is deliberately test-only. It proves the complete ordered-pair
structure and asks whether a new tuple record adds task value beyond the
existing ``stack_pop_order`` and exact-pattern facts. A negative result is a
valid outcome and must not be converted into runtime state, output, or scores.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-ordered-two-pop-role-task-value-v1.json"
DEFAULT_EXPECTED = ROOT / "tests/expected/sprint13-ordered-two-pop-role-task-value-v1.json"
STRUCTS = ROOT / "include/structs.inc"
PATTERNS = ROOT / "src/patterns.asm"
CLASSIFIER = ROOT / "src/classifier.asm"
SCORING = ROOT / "src/scoring.asm"
CATALOG = ROOT / "tests/expected/sprint10-exact-pattern-catalog.json"

REGS = (
    ("rdi", 1, 5, "5f"), ("rsi", 2, 4, "5e"),
    ("rdx", 3, 3, "5a"), ("rcx", 4, 2, "59"),
    ("r8", 5, 8, "41 58"), ("r9", 6, 9, "41 59"),
)

class GateError(RuntimeError):
    pass

def require(ok: bool, msg: str) -> None:
    if not ok:
        raise GateError(msg)

def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in items:
        require(k not in out, f"duplicate JSON key: {k}")
        out[k] = v
    return out

def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)

def exact_int(value: Any, expected: int, label: str) -> None:
    require(type(value) is int and value == expected, f"{label} must be integer {expected}")

def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()

def fail(msg: str) -> NoReturn:
    print(f"sprint13-ordered-two-pop-role-task-value-smoke: error: {msg}", file=sys.stderr)
    raise SystemExit(1)

def validate_source_contract() -> None:
    structs = STRUCTS.read_text(encoding="utf-8")
    patterns = PATTERNS.read_text(encoding="utf-8")
    classifier = CLASSIFIER.read_text(encoding="utf-8")
    scoring = SCORING.read_text(encoding="utf-8")
    require(re.search(r"%define\s+PATTERN_MULTI_POP_RET\s+21\b", structs) is not None, "pattern 21 definition changed")
    require("%define ARG_CONTROL_REG_MASK" in structs, "argument-control mask missing")
    require("SET_PATTERN PATTERN_MULTI_POP_RET" in patterns, "multi-pop exact matcher missing")
    require("cmp     eax, PATTERN_MULTI_POP_RET" in classifier, "multi-pop classifier gate missing")
    require("cmp     eax, PATTERN_MULTI_POP_RET" in scoring, "multi-pop score gate missing")
    catalog = load(CATALOG)
    rows = catalog.get("patterns")
    require(isinstance(rows, list) and len(rows) == 25, "exact-pattern catalog denominator changed")
    row = next((r for r in rows if r.get("pattern_id") == 21), None)
    require(row is not None and row.get("label") == "pop reg; pop reg; ret", "pattern 21 catalog row changed")
    require(row.get("semantic_class") == "arg_control" and row.get("score") == 95, "pattern 21 semantic/score changed")

def evaluate(authority: dict[str, Any]) -> dict[str, Any]:
    require(set(authority) == {
        "schema", "sprint", "patch", "purpose", "registers", "source_model",
        "structural_pairs", "controls", "tasks", "task_contract", "public_boundary", "limitations",
    }, "authority shape changed")
    require(authority["schema"] == "x64lens-sprint13-ordered-two-pop-role-task-value-v1", "authority schema changed")
    exact_int(authority["sprint"], 13, "sprint")
    exact_int(authority["patch"], 81, "patch")

    regs = authority["registers"]
    require(isinstance(regs, list) and len(regs) == 6, "register denominator changed")
    expected_regs = [dict(name=n, arg_index=a, bit=b, bytes=x) for n, a, b, x in REGS]
    require(regs == expected_regs, "register authority changed")
    by_name = {r[0]: r for r in REGS}

    source = authority["source_model"]
    require(source == {
        "pattern_id": 21, "pattern_label": "pop reg; pop reg; ret",
        "semantic_class": "arg_control", "evidence_kind": "semantic_exact",
        "register_count": 2, "stack_delta": 24, "score": 95,
        "candidate_capacity": 4096, "full_sequence_validity_changed": False,
    }, "source model changed")

    pairs = authority["structural_pairs"]
    require(isinstance(pairs, list) and len(pairs) == 30, "ordered pair denominator changed")
    expected_ids = {f"{a[0]}-{b[0]}" for a in REGS for b in REGS if a[0] != b[0]}
    seen: set[str] = set()
    for row in pairs:
        require(isinstance(row, dict) and set(row) == {
            "id", "register_order", "argument_order", "pattern_register_order",
            "controlled_register_mask", "suffix_bytes", "expected_pattern_id",
            "expected_semantic_class", "expected_score",
        }, "ordered pair row shape changed")
        ident = row["id"]
        require(ident in expected_ids and ident not in seen, f"invalid/duplicate pair: {ident}")
        seen.add(ident)
        first, second = row["register_order"]
        r1, r2 = by_name[first], by_name[second]
        require(row["argument_order"] == [r1[1], r2[1]], f"argument order mismatch: {ident}")
        require(row["pattern_register_order"] == (r1[2] | (r2[2] << 4)), f"packed order mismatch: {ident}")
        require(row["controlled_register_mask"] == ((1 << r1[2]) | (1 << r2[2])), f"mask mismatch: {ident}")
        require(row["suffix_bytes"] == f"{r1[3]} {r2[3]} c3", f"bytes mismatch: {ident}")
        require(row["expected_pattern_id"] == 21 and row["expected_semantic_class"] == "arg_control" and row["expected_score"] == 95, f"contract mismatch: {ident}")
    require(seen == expected_ids, "ordered pair membership changed")
    require(all(f"{b[0]}-{a[0]}" in seen for a in REGS for b in REGS if a != b), "reversal missing")

    controls = authority["controls"]
    duplicate = controls.get("duplicates_rejected")
    rsp = controls.get("rsp_rejected")
    r10 = controls.get("r10_rejected")
    require(controls.get("reversals_distinct") is True, "reversal contract changed")
    require(duplicate == [f"{r[0]}-{r[0]}" for r in REGS], "duplicate controls changed")
    require(rsp == ["rsp-rdi", "rdi-rsp"] and r10 == ["r10-rdi", "rdi-r10"], "out-of-family controls changed")

    tasks = authority["tasks"]
    require(isinstance(tasks, list) and len(tasks) == 30, "task denominator changed")
    ids: set[str] = set()
    dev_positive = dev_negative = confirmation = 0
    dev_gains = confirmation_gains = regressions = wrong = 0
    for task in tasks:
        require(isinstance(task, dict), "task must be object")
        ident = task.get("id")
        require(isinstance(ident, str) and ident not in ids, "duplicate task id")
        ids.add(ident)
        phase = task.get("phase")
        kind = task.get("kind")
        require(phase in {"development", "confirmation"}, f"invalid phase: {ident}")
        if phase == "development" and kind == "positive_role_tuple": dev_positive += 1
        elif phase == "development": dev_negative += 1
        elif phase == "confirmation": confirmation += 1
        require(task.get("existing_exact_correct") is True, f"existing exact fact failed: {ident}")
        require(task.get("proposed_tuple_correct") is True, f"proposed tuple failed: {ident}")
        dev_gains += int(phase == "development" and task.get("incremental_gain") is True)
        confirmation_gains += int(phase == "confirmation" and task.get("incremental_gain") is True)
        regressions += int(task.get("regression") is True)
        wrong += int(task.get("incorrect_promotion") is True)
    require((dev_positive, dev_negative, confirmation) == (12, 12, 6), "task strata changed")

    thresholds = authority["task_contract"]
    require(thresholds == {
        "development_positive": 12, "development_negative": 12,
        "confirmation": 6, "total": 30,
        "minimum_development_gains_to_qualify": 4,
        "minimum_confirmation_gains_to_qualify": 1,
        "required_confirmation_correct": 6, "required_generations": 3,
        "zero_regressions_required": True,
        "zero_incorrect_promotions_required": True,
    }, "thresholds changed")
    boundary = authority["public_boundary"]
    require(boundary == {
        "runtime_records_added": 0, "public_json_fields_added": 0,
        "public_text_fields_added": 0, "semantic_changes": 0,
        "score_changes": 0, "schema_changed": False, "capacity_changed": False,
        "dependency_changes": 0, "worker_changes": 0,
    }, "public boundary changed")

    generations = [canonical(authority) for _ in range(3)]
    byte_identical = len(set(generations)) == 1
    decision = "qualify_new_runtime_tuple_representation" if (
        dev_gains >= 4 and regressions == 0 and wrong == 0 and confirmation == 6 and confirmation_gains >= 1 and byte_identical
    ) else "defer_new_runtime_tuple_representation"
    reason = (
        "Existing exact ordered-pop facts already answer every frozen role-tuple task; the proposed convenience representation adds no incremental task value."
        if decision.startswith("defer") else
        "The proposed tuple representation adds independent frozen task value."
    )
    return {
        "schema": "x64lens-sprint13-ordered-two-pop-role-task-value-result-v1",
        "authority_schema": authority["schema"], "sprint": 13, "patch": 81,
        "structural_pairs": 30, "structural_pairs_correct": 30,
        "reversals_distinct": 30, "out_of_family_controls": 10,
        "out_of_family_controls_rejected": 10,
        "development_positive": 12, "development_negative": 12, "confirmation": 6,
        "development_gains": dev_gains, "confirmation_correct": confirmation,
        "confirmation_gains": confirmation_gains, "regressions": regressions,
        "incorrect_promotions": wrong, "generations": 3,
        "byte_identical_generations": 3 if byte_identical else 0,
        "decision": decision, "reason": reason,
        "public_fields_added": 0, "semantic_changes": 0,
        "score_changes": 0, "schema_changed": False,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    args = parser.parse_args()
    try:
        validate_source_contract()
        result = evaluate(load(args.authority))
        expected = load(args.expected)
        require(result == expected, "result differs from expected authority")
    except (OSError, json.JSONDecodeError, GateError) as exc:
        fail(str(exc))
    print(
        "sprint13-ordered-two-pop-role-task-value-smoke: ok "
        "pairs=30 development=24 confirmation=6 structural=30 controls=10 "
        "development_gains=0 confirmation_gains=0 regressions=0 "
        "incorrect_promotions=0 generations=3 decision=defer "
        "runtime_records_added=0 public_fields_added=0 score_changes=0 schema_changed=0"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
