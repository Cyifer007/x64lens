#!/usr/bin/env python3
"""Freeze every score/null cell against independently built producer output."""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-score-null-authority-v2.json"
DEFAULT_EXPECTED = ROOT / "tests/expected/sprint13-score-null-authority-v2.json"
CATALOG = ROOT / "tests/expected/sprint10-exact-pattern-catalog.json"
ROLE_POLICY = ROOT / "benchmarks/task-definitions/sprint13-register-role-policy-v1.json"
PRODUCER_TOOL = ROOT / "tools/sprint13-producer-authority-smoke.py"


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
    print(f"sprint13-score-null-authority-smoke: error: {msg}", file=sys.stderr)
    raise SystemExit(1)


def producer_module() -> Any:
    spec = importlib.util.spec_from_file_location("p082_producer_score", PRODUCER_TOOL)
    require(spec is not None and spec.loader is not None, "cannot load producer authority helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_authority(authority: dict[str, Any]) -> list[dict[str, Any]]:
    require(authority.get("schema") == "x64lens-sprint13-score-null-authority-v2", "authority schema changed")
    require(authority.get("sprint") == 13 and authority.get("patch") == 82, "authority identity changed")
    contract = authority.get("contract")
    require(contract == {
        "pattern_rows": 25, "scored_patterns": 14, "null_patterns": 11,
        "private_null_facets": 3, "mutate_every_pattern_cell": True,
        "catalog_rejection_gate": True,
        "producer_manifest_schema": "x64lens-sprint13-producer-authority-v1",
        "producer_generations": 3, "score_changes": 0,
        "public_fields_added": 0, "schema_changed": False,
    }, "score/null contract changed")
    rows = authority.get("patterns")
    require(isinstance(rows, list) and len(rows) == 25, "pattern denominator changed")
    require([item.get("pattern_id") for item in rows] == list(range(1, 26)), "pattern order changed")
    require(sum(item.get("score") is not None for item in rows) == 14, "scored denominator changed")
    require(sum(item.get("score") is None for item in rows) == 11, "null denominator changed")
    facets = authority.get("private_role_facets")
    require(isinstance(facets, list) and [item.get("facet") for item in facets] == ["generic_control", "sysv_call_arguments", "linux_syscall_arguments"], "private facet set changed")
    require(all(item.get("score") is None for item in facets), "private role facet gained a score")
    return rows


def gate_catalog(authority_rows: list[dict[str, Any]]) -> bool:
    rows = load(CATALOG).get("patterns")
    if not isinstance(rows, list) or len(rows) != 25:
        return False
    expected = [(item.get("pattern_id"), item.get("label"), item.get("score")) for item in rows]
    actual = [(item.get("pattern_id"), item.get("label"), item.get("score")) for item in authority_rows]
    return actual == expected


def producer_rows(manifest_path: Path) -> list[list[tuple[str, Any]]]:
    producer = producer_module()
    manifest = producer.validate_manifest(manifest_path)
    root = manifest_path.parent
    rows: list[list[tuple[str, Any]]] = []
    for generation in manifest["generations"]:
        report = load(root / generation["effects_report"]["path"])
        gadgets = report.get("gadgets")
        require(isinstance(gadgets, list) and len(gadgets) == 25, "producer effects denominator changed")
        rows.append([(item.get("pattern"), item.get("score")) for item in gadgets])
    require(len(rows) == 3 and rows[0] == rows[1] == rows[2], "independent producer score facts disagree")
    return rows


def gate_producer(authority_rows: list[dict[str, Any]], generations: list[list[tuple[str, Any]]]) -> bool:
    expected = [(item.get("label"), item.get("score")) for item in authority_rows]
    return all(observed == expected for observed in generations)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    parser.add_argument("--producer-manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        authority = load(args.authority)
        rows = validate_authority(authority)
        generations = producer_rows(args.producer_manifest.resolve(strict=True))
        require(gate_catalog(rows), "authority disagrees with exact-pattern catalog")
        require(gate_producer(rows, generations), "authority disagrees with independent producer output")
        role = load(ROLE_POLICY)
        score_cells = [item for item in role.get("policy_cells", []) if item.get("surface") == "score"]
        require(len(score_cells) == 3 and all(item.get("decision") == "retain_existing_scores_and_null_new_facets" for item in score_cells), "private role score policy changed")
        catalog_rejections = producer_rejections = 0
        for index, row in enumerate(rows):
            mutated = copy.deepcopy(rows)
            mutated[index]["score"] = 1 if row["score"] is None else None
            catalog_rejections += int(not gate_catalog(mutated))
            producer_rejections += sum(1 for generation in generations if not gate_producer(mutated, [generation]))
        result = {
            "schema": "x64lens-sprint13-score-null-result-v2", "sprint": 13, "patch": 82,
            "pattern_rows": 25, "scored_patterns": 14, "null_patterns": 11,
            "private_null_facets": 3, "mutations": 25,
            "catalog_policy_rejections": catalog_rejections,
            "producer_generations": 3, "producer_effect_rejections": producer_rejections,
            "total_rejections": catalog_rejections + producer_rejections,
            "producer_backed": True, "decision": "retain_existing_scores_and_nulls",
            "score_changes": 0, "public_fields_added": 0, "schema_changed": False,
        }
        require(result == load(args.expected), "result differs from expected authority")
    except (OSError, json.JSONDecodeError, GateError) as exc:
        fail(str(exc))
    print(
        "sprint13-score-null-authority-smoke: ok patterns=25 scored=14 null=11 "
        "private_null_facets=3 mutations=25 catalog_rejections=25 "
        "producer_generations=3 producer_rejections=75 total_rejections=100 "
        "producer_backed=1 decision=retain score_changes=0 public_fields_added=0 schema_changed=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
