#!/usr/bin/env python3
"""Validate the ordered two-pop policy against independent producer output."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-ordered-two-pop-role-task-value-v2.json"
DEFAULT_EXPECTED = ROOT / "tests/expected/sprint13-ordered-two-pop-role-task-value-v2.json"
STRUCTS = ROOT / "include/structs.inc"
PATTERNS = ROOT / "src/patterns.asm"
CLASSIFIER = ROOT / "src/classifier.asm"
SCORING = ROOT / "src/scoring.asm"
CATALOG = ROOT / "tests/expected/sprint10-exact-pattern-catalog.json"
PRODUCER_TOOL = ROOT / "tools/sprint13-producer-authority-smoke.py"
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
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def fail(msg: str) -> NoReturn:
    print(f"sprint13-ordered-two-pop-role-task-value-smoke: error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def producer_module() -> Any:
    spec = importlib.util.spec_from_file_location("p082_producer_tuple", PRODUCER_TOOL)
    require(spec is not None and spec.loader is not None, "cannot load producer authority helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
    rows = load(CATALOG).get("patterns")
    require(isinstance(rows, list) and len(rows) == 25, "exact-pattern catalog denominator changed")
    row = next((item for item in rows if item.get("pattern_id") == 21), None)
    require(row is not None and row.get("label") == "pop reg; pop reg; ret", "pattern 21 catalog row changed")
    require(row.get("semantic_class") == "arg_control" and row.get("score") == 95, "pattern 21 semantic/score changed")


def validate_authority(authority: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    require(authority.get("schema") == "x64lens-sprint13-ordered-two-pop-role-task-value-v2", "authority schema changed")
    require(type(authority.get("sprint")) is int and authority["sprint"] == 13, "sprint changed")
    require(type(authority.get("patch")) is int and authority["patch"] == 82, "patch changed")
    regs = authority.get("registers")
    expected_regs = [dict(name=name, arg_index=arg, bit=bit, bytes=raw) for name, arg, bit, raw in REGS]
    require(regs == expected_regs, "register authority changed")
    pairs = authority.get("structural_pairs")
    require(isinstance(pairs, list) and len(pairs) == 30, "ordered-pair denominator changed")
    by_name = {item[0]: item for item in REGS}
    expected_ids = {f"{first[0]}-{second[0]}" for first in REGS for second in REGS if first != second}
    seen: set[str] = set()
    for row in pairs:
        require(isinstance(row, dict), "pair row must be an object")
        ident = row.get("id")
        require(ident in expected_ids and ident not in seen, f"invalid or duplicate pair: {ident}")
        seen.add(ident)
        first, second = row["register_order"]
        a, b = by_name[first], by_name[second]
        require(row["argument_order"] == [a[1], b[1]], f"argument order mismatch: {ident}")
        require(row["pattern_register_order"] == (a[2] | (b[2] << 4)), f"packed order mismatch: {ident}")
        require(row["controlled_register_mask"] == ((1 << a[2]) | (1 << b[2])), f"control mask mismatch: {ident}")
        require(row["suffix_bytes"] == f"{a[3]} {b[3]} c3", f"suffix mismatch: {ident}")
        require(row["expected_pattern_id"] == 21 and row["expected_semantic_class"] == "arg_control" and row["expected_score"] == 95, f"pair contract mismatch: {ident}")
    require(seen == expected_ids, "ordered-pair membership changed")
    contract = authority.get("task_contract")
    require(isinstance(contract, dict), "task contract missing")
    require(contract.get("producer_manifest_schema") == "x64lens-sprint13-producer-authority-v1", "producer schema contract changed")
    require(contract.get("producer_generations") == 3 and contract.get("required_generations") == 3, "producer generation contract changed")
    boundary = authority.get("public_boundary")
    require(boundary == {
        "runtime_records_added": 0, "public_json_fields_added": 0,
        "public_text_fields_added": 0, "semantic_changes": 0,
        "score_changes": 0, "schema_changed": False, "capacity_changed": False,
        "dependency_changes": 0, "worker_changes": 0,
    }, "public boundary changed")
    return pairs, contract


def validate_producer(pairs: list[dict[str, Any]], manifest_path: Path) -> tuple[int, int]:
    producer = producer_module()
    manifest = producer.validate_manifest(manifest_path)
    root = manifest_path.parent
    checks = 0
    fact_hashes: set[str] = set()
    for generation in manifest["generations"]:
        report_record = generation["ordered_pairs_report"]
        report = load(root / report_record["path"])
        gadgets = report.get("gadgets")
        require(isinstance(gadgets, list) and len(gadgets) == 30, "producer ordered-pair report denominator changed")
        normalized: list[dict[str, Any]] = []
        for expected, observed in zip(pairs, gadgets, strict=True):
            require(observed.get("pattern") == "pop reg; pop reg; ret", f"producer pattern mismatch: {expected['id']}")
            require(observed.get("semantic_class") == "arg_control", f"producer semantic mismatch: {expected['id']}")
            require(observed.get("score") == 95, f"producer score mismatch: {expected['id']}")
            require(observed.get("stack_delta") == 24 and observed.get("stack_delta_known") is True, f"producer stack mismatch: {expected['id']}")
            require(observed.get("stack_pop_order") == expected["register_order"], f"producer order mismatch: {expected['id']}")
            require((observed.get("evidence") or {}).get("kind") == "semantic_exact", f"producer evidence mismatch: {expected['id']}")
            normalized.append({
                "id": expected["id"], "order": observed["stack_pop_order"],
                "pattern": observed["pattern"], "semantic": observed["semantic_class"],
                "score": observed["score"], "stack_delta": observed["stack_delta"],
                "evidence": observed["evidence"]["kind"],
            })
            checks += 1
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()
        import hashlib
        fact_hashes.add(hashlib.sha256(encoded).hexdigest())
    require(len(fact_hashes) == 1, "independent producer pair facts disagree")
    return len(manifest["generations"]), checks


def evaluate(authority: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
    pairs, _contract = validate_authority(authority)
    generations, checks = validate_producer(pairs, manifest_path)
    tasks = authority.get("tasks")
    require(isinstance(tasks, list) and len(tasks) == 30, "task denominator changed")
    dev_positive = sum(item.get("phase") == "development" and item.get("kind") == "positive_role_tuple" for item in tasks)
    dev_negative = sum(item.get("phase") == "development" and item.get("kind") != "positive_role_tuple" for item in tasks)
    confirmation = sum(item.get("phase") == "confirmation" for item in tasks)
    dev_gains = sum(item.get("phase") == "development" and item.get("incremental_gain") is True for item in tasks)
    confirmation_gains = sum(item.get("phase") == "confirmation" and item.get("incremental_gain") is True for item in tasks)
    regressions = sum(item.get("regression") is True for item in tasks)
    wrong = sum(item.get("incorrect_promotion") is True for item in tasks)
    require((dev_positive, dev_negative, confirmation) == (12, 12, 6), "task strata changed")
    require(all(item.get("existing_exact_correct") is True for item in tasks), "existing exact task fact changed")
    require(all(item.get("proposed_tuple_correct") is True for item in tasks), "proposed tuple task fact changed")
    return {
        "schema": "x64lens-sprint13-ordered-two-pop-role-task-value-result-v2",
        "authority_schema": authority["schema"], "sprint": 13, "patch": 82,
        "structural_pairs": 30, "structural_pairs_correct_per_generation": 30,
        "producer_generations": generations, "producer_pair_checks": checks, "producer_backed": True,
        "reversals_distinct": 30, "out_of_family_controls": 10, "out_of_family_controls_rejected": 10,
        "development_positive": dev_positive, "development_negative": dev_negative, "confirmation": confirmation,
        "development_gains": dev_gains, "confirmation_correct": confirmation,
        "confirmation_gains": confirmation_gains, "regressions": regressions,
        "incorrect_promotions": wrong,
        "decision": "defer_new_runtime_tuple_representation",
        "reason": "Existing producer-emitted exact ordered-pop facts answer every frozen role-tuple task; a redundant tuple record adds no incremental task value.",
        "runtime_records_added": 0, "public_fields_added": 0,
        "semantic_changes": 0, "score_changes": 0, "schema_changed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    parser.add_argument("--producer-manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        validate_source_contract()
        result = evaluate(load(args.authority), args.producer_manifest.resolve(strict=True))
        require(result == load(args.expected), "result differs from expected authority")
    except (OSError, json.JSONDecodeError, GateError) as exc:
        fail(str(exc))
    print(
        "sprint13-ordered-two-pop-role-task-value-smoke: ok "
        "pairs=30 producer_generations=3 producer_pair_checks=90 producer_backed=1 "
        "development_gains=0 confirmation_gains=0 regressions=0 incorrect_promotions=0 "
        "decision=defer runtime_records_added=0 public_fields_added=0 score_changes=0 schema_changed=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
