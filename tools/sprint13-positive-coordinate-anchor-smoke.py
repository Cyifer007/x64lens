#!/usr/bin/env python3
"""Validate bounded positive coordinate anchors over controlled ELF objects.

The gate exercises the existing address-coordinate classifier with real,
deterministically generated ELF64 bytes whose single executable mapping makes
file offsets and virtual addresses distinct.  It is a controlled diagnostic
preflight, not evidence that a particular external tool emitted the modeled
relations on a natural corpus.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-positive-coordinate-anchor-v1.json"
DEFAULT_EXPECTED = ROOT / "tests/expected/sprint13-positive-coordinate-anchor-v1.json"
CALIBRATOR = ROOT / "benchmarks/scripts/address-coordinate-calibrator.py"
SCHEMA = "x64lens-sprint13-positive-coordinate-anchor-v1"
RESULT_SCHEMA = "x64lens-sprint13-positive-coordinate-anchor-result-v1"
ROLES = ("et_exec", "pie_et_dyn", "shared_et_dyn")
TOOLS = ("ropgadget", "ropper", "ropr")


class AnchorError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise AnchorError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-positive-coordinate-anchor-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_calibrator() -> Any:
    spec = importlib.util.spec_from_file_location("p082_coordinate_calibrator", CALIBRATOR)
    require(spec is not None and spec.loader is not None, "cannot load coordinate calibrator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_elf(record: dict[str, Any]) -> bytes:
    e_type = 2 if record["role"] == "et_exec" else 3
    base = record["p_vaddr"]
    pattern_offset = record["pattern_file_offset"]
    size = 512
    require(128 <= pattern_offset <= size - 2, f"pattern offset out of range: {record['id']}")
    entry = 0 if record["role"] == "shared_et_dyn" else base + pattern_offset
    ident = b"\x7fELF" + bytes([2, 1, 1, 0, 0]) + b"\x00" * 7
    header = struct.pack(
        "<16sHHIQQQIHHHHHH",
        ident, e_type, 62, 1, entry, 64, 0, 0, 64, 56, 1, 64, 0, 0,
    )
    phdr = struct.pack("<IIQQQQQQ", 1, 5, 0, base, base, size, size, 0x1000)
    data = bytearray(size)
    data[: len(header)] = header
    data[64 : 64 + len(phdr)] = phdr
    data[pattern_offset : pattern_offset + 2] = b"\x5f\xc3"
    return bytes(data)


def target_facts(record: dict[str, Any]) -> tuple[bytes, str, str]:
    payload = build_elf(record)
    offset = f"0x{record['pattern_file_offset']:016x}"
    virtual = f"0x{record['p_vaddr'] + record['pattern_file_offset']:016x}"
    require(offset != virtual, f"target does not discriminate coordinates: {record['id']}")
    require(sha256(payload) == record["sha256"], f"target SHA-256 changed: {record['id']}")
    return payload, offset, virtual


def validate_authority(authority: dict[str, Any]) -> dict[str, tuple[bytes, str, str]]:
    require(set(authority) == {
        "schema", "sprint", "patch", "purpose", "evidence_class",
        "publication_eligible", "roles", "tools", "targets",
        "qualification_cells", "oracle_positive_cases", "mutation_cases",
        "semantic_negative_cases", "qualification_contract", "limitations",
    }, "coordinate authority shape changed")
    require(authority["schema"] == SCHEMA and authority["sprint"] == 13 and authority["patch"] == 82, "coordinate authority identity changed")
    require(authority["evidence_class"] == "diagnostic" and authority["publication_eligible"] is False, "coordinate evidence boundary changed")
    require(tuple(authority["roles"]) == ROLES and tuple(authority["tools"]) == TOOLS, "coordinate role/tool set changed")
    targets = authority["targets"]
    require(isinstance(targets, list) and len(targets) == 6, "controlled target denominator changed")
    target_map: dict[str, tuple[bytes, str, str]] = {}
    role_counts = {role: 0 for role in ROLES}
    for record in targets:
        require(isinstance(record, dict) and set(record) == {"id", "role", "p_vaddr", "pattern_file_offset", "sha256"}, "target record shape changed")
        require(record["id"] not in target_map and record["role"] in ROLES, "invalid controlled target identity")
        require(type(record["p_vaddr"]) is int and type(record["pattern_file_offset"]) is int, "target coordinates must be exact integers")
        target_map[record["id"]] = target_facts(record)
        role_counts[record["role"]] += 1
    require(role_counts == {role: 2 for role in ROLES}, "controlled targets must provide two anchors per role")
    return target_map


def evaluate(authority: dict[str, Any], result_dir: Path | None) -> dict[str, Any]:
    calibrator = load_calibrator()
    targets = validate_authority(authority)
    if result_dir is not None:
        require(not result_dir.exists(), f"result directory already exists: {result_dir}")
        result_dir.mkdir(parents=True, mode=0o755)
        target_root = result_dir / "targets"
        target_root.mkdir(mode=0o755)
        for record in authority["targets"]:
            payload, _offset, _virtual = targets[record["id"]]
            path = target_root / f"{record['id']}.elf"
            path.write_bytes(payload)
            path.chmod(0o444)

    positive_cases = authority["oracle_positive_cases"]
    require(isinstance(positive_cases, list) and len(positive_cases) == 8, "positive oracle denominator changed")
    positive_passes = 0
    for case in positive_cases:
        _payload, offset, virtual = targets[case["target_id"]]
        baseline = {virtual} if case["coordinate"] == "virtual_address" else {offset}
        result = calibrator.classify(baseline, {virtual}, {offset})
        require(result["status"] == case["expected_status"] == case["coordinate"], f"positive oracle failed: {case['id']}")
        positive_passes += 1

    mutations = authority["mutation_cases"]
    require(isinstance(mutations, list) and len(mutations) == 4, "mutation denominator changed")
    mutation_rejections = 0
    target_records = {item["id"]: item for item in authority["targets"]}
    for case in mutations:
        base = dict(target_records[case["target_id"]])
        field = case["field"]
        if field == "sha256":
            base[field] = "0" * 64
        elif field == "role":
            base[field] = next(role for role in ROLES if role != base[field])
        elif field == "p_vaddr":
            base[field] += 0x1000
        elif field == "pattern_file_offset":
            base[field] += 1
        else:
            raise AnchorError(f"unknown mutation field: {field}")
        try:
            target_facts(base)
        except AnchorError:
            mutation_rejections += 1
        else:
            raise AnchorError(f"mutation was accepted: {case['id']}")

    negatives = authority["semantic_negative_cases"]
    require(isinstance(negatives, list) and len(negatives) == 4, "semantic-negative denominator changed")
    negative_passes = 0
    for case in negatives:
        result = calibrator.classify(set(case["baseline"]), set(case["virtual"]), set(case["offsets"]))
        require(result["status"] == case["expected_status"], f"semantic negative failed: {case['id']}")
        negative_passes += 1

    cells = authority["qualification_cells"]
    require(isinstance(cells, list) and len(cells) == 9, "qualification-cell denominator changed")
    expected_cells = {(tool, role) for tool in TOOLS for role in ROLES}
    seen: set[tuple[str, str]] = set()
    qualified = 0
    anchors = 0
    cell_results: list[dict[str, Any]] = []
    for cell in cells:
        key = (cell["tool"], cell["role"])
        require(key in expected_cells and key not in seen, f"invalid/duplicate qualification cell: {key}")
        seen.add(key)
        anchor_ids = cell["target_ids"]
        require(isinstance(anchor_ids, list) and len(anchor_ids) == 2 and len(set(anchor_ids)) == 2, f"cell lacks two independent anchors: {key}")
        statuses: list[str] = []
        hashes: set[str] = set()
        for target_id in anchor_ids:
            record = next(item for item in authority["targets"] if item["id"] == target_id)
            require(record["role"] == cell["role"], f"cell role/target mismatch: {key}")
            payload, offset, virtual = targets[target_id]
            hashes.add(sha256(payload))
            result = calibrator.classify({virtual}, {virtual}, {offset})
            statuses.append(result["status"])
            anchors += 1
        require(len(hashes) == 2 and statuses == [cell["expected_status"], cell["expected_status"]], f"cell did not qualify: {key}")
        qualified += 1
        cell_results.append({"tool": key[0], "role": key[1], "status": cell["expected_status"], "anchors": 2})
    require(seen == expected_cells, "qualification cells are incomplete")
    contract = authority["qualification_contract"]
    require(contract == {
        "eligible_cells": 9, "anchors_per_cell": 2, "required_qualified_cells": 9,
        "positive_oracle_cases": 8, "mutation_cases": 4,
        "semantic_negative_cases": 4, "global_interpretation_requires_all_cells": True,
        "natural_campaign_required_before_comparative_claim": True,
    }, "qualification contract changed")

    result = {
        "schema": RESULT_SCHEMA, "sprint": 13, "patch": 82,
        "controlled_targets": 6, "positive_oracle_cases": positive_passes,
        "mutation_rejections": mutation_rejections,
        "semantic_negative_cases": negative_passes,
        "qualification_cells": len(cells), "qualified_cells": qualified,
        "positive_anchors": anchors, "anchors_per_cell": 2,
        "decision": "controlled_coordinate_preflight_qualified",
        "natural_campaign_qualified": False,
        "comparative_coverage_claim_authorized": False,
        "public_fields_added": 0, "semantic_changes": 0,
        "score_changes": 0, "schema_changed": False,
        "cells": cell_results,
    }
    if result_dir is not None:
        (result_dir / "result.json").write_bytes(canonical(result))
        (result_dir / "result.json").chmod(0o444)
        manifest = {
            "schema": "x64lens-sprint13-positive-coordinate-anchor-evidence-v1",
            "authority_sha256": sha256(canonical(authority)),
            "result_sha256": sha256(canonical(result)),
            "controlled_target_sha256": {item["id"]: item["sha256"] for item in authority["targets"]},
            "evidence_class": "diagnostic", "publication_eligible": False,
        }
        (result_dir / "manifest.json").write_bytes(canonical(manifest))
        (result_dir / "manifest.json").chmod(0o444)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    parser.add_argument("--result-dir", type=Path)
    args = parser.parse_args()
    try:
        authority = load(args.authority)
        result = evaluate(authority, args.result_dir.resolve() if args.result_dir else None)
        require(result == load(args.expected), "result differs from expected authority")
    except (OSError, json.JSONDecodeError, AnchorError) as exc:
        fail(str(exc))
    print(
        "sprint13-positive-coordinate-anchor-smoke: ok targets=6 positives=8 "
        "mutations=4 semantic_negatives=4 cells=9 qualified_cells=9 "
        "positive_anchors=18 anchors_per_cell=2 decision=controlled_preflight "
        "natural_campaign_qualified=0 comparative_claims=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
