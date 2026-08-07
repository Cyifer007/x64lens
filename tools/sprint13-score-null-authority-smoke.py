#!/usr/bin/env python3
"""Freeze and mutation-test every release-facing exact-pattern score/null cell."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-score-null-authority-v1.json"
DEFAULT_EXPECTED = ROOT / "tests/expected/sprint13-score-null-authority-v1.json"
CATALOG = ROOT / "tests/expected/sprint10-exact-pattern-catalog.json"
REPORT = ROOT / "tests/expected/x64lens-report-sprint10-effects-0.2.0.json"
ROLE_POLICY = ROOT / "benchmarks/task-definitions/sprint13-register-role-policy-v1.json"

class GateError(RuntimeError): pass

def require(ok: bool, msg: str) -> None:
    if not ok: raise GateError(msg)

def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in items:
        require(k not in out, f"duplicate JSON key: {k}")
        out[k] = v
    return out

def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)

def fail(msg: str) -> NoReturn:
    print(f"sprint13-score-null-authority-smoke: error: {msg}", file=sys.stderr)
    raise SystemExit(1)

def validate_authority(authority: dict[str, Any]) -> list[dict[str, Any]]:
    require(set(authority) == {"schema","sprint","patch","purpose","contract","patterns","private_role_facets"}, "authority shape changed")
    require(authority["schema"] == "x64lens-sprint13-score-null-authority-v1", "authority schema changed")
    require(authority["sprint"] == 13 and authority["patch"] == 81, "authority identity changed")
    contract = authority["contract"]
    require(contract == {
        "pattern_rows":25,"scored_patterns":14,"null_patterns":11,
        "private_null_facets":3,"mutate_every_pattern_cell":True,
        "independent_rejection_gates":2,"score_changes":0,
        "public_fields_added":0,"schema_changed":False,
    }, "score/null contract changed")
    rows = authority["patterns"]
    require(isinstance(rows, list) and len(rows) == 25, "pattern denominator changed")
    ids = [r.get("pattern_id") for r in rows]
    require(ids == list(range(1,26)), "pattern ID order changed")
    require(sum(r.get("score") is not None for r in rows) == 14, "scored denominator changed")
    require(sum(r.get("score") is None for r in rows) == 11, "null denominator changed")
    facets = authority["private_role_facets"]
    require(isinstance(facets,list) and [x.get("facet") for x in facets] == ["generic_control","sysv_call_arguments","linux_syscall_arguments"], "private facet set changed")
    require(all(x.get("score") is None for x in facets), "private role facet gained score")
    return rows

def gate_catalog(authority_rows: list[dict[str, Any]]) -> bool:
    catalog = load(CATALOG)
    rows = catalog.get("patterns")
    if not isinstance(rows,list) or len(rows) != 25: return False
    expected = [(r.get("pattern_id"),r.get("label"),r.get("score")) for r in rows]
    actual = [(r.get("pattern_id"),r.get("label"),r.get("score")) for r in authority_rows]
    return actual == expected

def gate_report(authority_rows: list[dict[str, Any]]) -> bool:
    report = load(REPORT)
    gadgets = report.get("gadgets")
    if not isinstance(gadgets,list) or len(gadgets) != 25: return False
    expected = [(r.get("label"),r.get("score")) for r in authority_rows]
    actual = [(g.get("pattern"),g.get("score")) for g in gadgets]
    return actual == expected

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--authority",type=Path,default=DEFAULT_AUTHORITY)
    parser.add_argument("--expected",type=Path,default=DEFAULT_EXPECTED)
    args=parser.parse_args()
    try:
        authority=load(args.authority)
        rows=validate_authority(authority)
        require(gate_catalog(rows), "authority disagrees with exact-pattern catalog")
        require(gate_report(rows), "authority disagrees with controlled JSON report")
        role=load(ROLE_POLICY)
        cells=role.get("policy_cells")
        require(isinstance(cells,list) and len(cells) == 9, "private role policy cells changed")
        score_cells=[x for x in cells if x.get("surface") == "score"]
        require(len(score_cells) == 3 and all(x.get("decision") == "retain_existing_scores_and_null_new_facets" for x in score_cells), "private role score policy changed")
        cat_rej=rep_rej=0
        for index,row in enumerate(rows):
            mutated=copy.deepcopy(rows)
            mutated[index]["score"] = 1 if row["score"] is None else None
            cat_rej += int(not gate_catalog(mutated))
            rep_rej += int(not gate_report(mutated))
        result={
            "schema":"x64lens-sprint13-score-null-result-v1","sprint":13,"patch":81,
            "pattern_rows":25,"scored_patterns":14,"null_patterns":11,
            "private_null_facets":3,"mutations":25,
            "catalog_policy_rejections":cat_rej,"report_effect_rejections":rep_rej,
            "total_independent_rejections":cat_rej+rep_rej,
            "decision":"retain_existing_scores_and_nulls","score_changes":0,
            "public_fields_added":0,"schema_changed":False,
        }
        require(result == load(args.expected), "result differs from expected authority")
    except (OSError,json.JSONDecodeError,GateError) as exc:
        fail(str(exc))
    print("sprint13-score-null-authority-smoke: ok patterns=25 scored=14 null=11 private_null_facets=3 mutations=25 gates=2 rejections=50 decision=retain score_changes=0 public_fields_added=0 schema_changed=0")
    return 0

if __name__ == "__main__": raise SystemExit(main())
