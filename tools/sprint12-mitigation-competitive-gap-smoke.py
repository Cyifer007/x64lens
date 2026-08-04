#!/usr/bin/env python3
"""Validate the bounded competitive mitigation gap and next-tranche authority.

The register is a design authority, not a runtime-field implementation.  Every
collection and scalar is type-checked exactly so JSON booleans cannot satisfy
integer fields, duplicate records cannot inflate denominators, and a string
cannot silently replace a list-valued selection policy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PUBLIC = [
    "bind_now", "canary", "dynamic_entry_count", "dynamic_linking",
    "dynamic_terminated", "nx_stack", "pie", "relro", "rwx_load_segment", "stripped",
]
EXPECTED_PRIVATE = ["binary-role", "ibt-shstk"]
EXPECTED_TRANCHES = ["text-relocations", "runtime-search-path", "fortify-source-indicator"]
EXPECTED_SELECTED: list[str] = []


class GapError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GapError(message)


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)


def string_list(value: Any, label: str, *, exact_count: int | None = None) -> list[str]:
    require(isinstance(value, list), f"{label} must be an array")
    require(all(isinstance(item, str) and item for item in value), f"{label} contains a non-string or empty item")
    require(len(value) == len(set(value)), f"{label} contains duplicate items")
    if exact_count is not None:
        require(len(value) == exact_count, f"{label} count changed")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    args = parser.parse_args()
    value = load(args.authority)
    require(isinstance(value, dict) and set(value) == {
        "authority_id", "evidence_class", "frozen", "publication_eligible", "purpose",
        "current_public_properties", "current_private_or_deferred",
        "prioritized_gap_tranches", "excluded_shortcuts", "patch_073_disposition", "patch_074_disposition",
        "patch_075_disposition", "patch_076_disposition",
    }, "mitigation gap authority fields changed")
    require(value["authority_id"] == "sprint12-mitigation-competitive-gap-v1",
            "mitigation gap authority id changed")
    require(value["evidence_class"] == "design-decision"
            and type(value["frozen"]) is bool and value["frozen"] is False
            and type(value["publication_eligible"]) is bool and value["publication_eligible"] is False,
            "mitigation gap evidence boundary changed")
    require(isinstance(value["purpose"], str) and value["purpose"], "mitigation gap purpose is invalid")

    current = string_list(value["current_public_properties"], "current public properties", exact_count=10)
    require(current == EXPECTED_PUBLIC, "current public mitigation authority order or membership changed")
    schema = load(ROOT / "schemas/x64lens-report.schema.json")
    observed = sorted(schema["properties"]["mitigations"]["properties"])
    require(observed == sorted(current), f"current mitigation property inventory changed: {observed}")

    private = value["current_private_or_deferred"]
    require(isinstance(private, list) and len(private) == 2, "private/deferred mitigation inventory changed")
    private_ids: list[str] = []
    for index, item in enumerate(private):
        require(isinstance(item, dict) and set(item) == {"id", "status", "reason"},
                f"private/deferred record fields changed: {index}")
        require(isinstance(item["id"], str) and item["id"], f"invalid private record id: {index}")
        require(isinstance(item["status"], str) and item["status"] == "private-policy-deferred",
                f"private role/property fact was promoted: {item['id']}")
        require(isinstance(item["reason"], str) and item["reason"], f"private record reason is invalid: {item['id']}")
        private_ids.append(item["id"])
    require(private_ids == EXPECTED_PRIVATE and len(private_ids) == len(set(private_ids)),
            "private/deferred mitigation inventory order, membership, or uniqueness changed")

    tranches = value["prioritized_gap_tranches"]
    require(isinstance(tranches, list) and len(tranches) == 3, "mitigation gap tranche count changed")
    tranche_ids: list[str] = []
    priorities: list[int] = []
    selected: list[str] = []
    for index, item in enumerate(tranches):
        require(isinstance(item, dict) and set(item) == {
            "priority", "id", "candidate_public_state", "bounded_evidence", "required_work",
            "selected_for_next_bounded_mitigation_tranche",
        }, f"mitigation tranche fields changed: {index}")
        require(type(item["priority"]) is int and item["priority"] > 0,
                f"mitigation tranche priority type/value changed: {index}")
        require(isinstance(item["id"], str) and item["id"], f"invalid mitigation tranche id: {index}")
        require(isinstance(item["candidate_public_state"], str) and item["candidate_public_state"],
                f"invalid candidate public state: {item['id']}")
        string_list(item["bounded_evidence"], f"bounded evidence for {item['id']}")
        string_list(item["required_work"], f"required work for {item['id']}")
        require(type(item["selected_for_next_bounded_mitigation_tranche"]) is bool,
                f"mitigation tranche selection type changed: {item['id']}")
        priorities.append(item["priority"])
        tranche_ids.append(item["id"])
        if item["selected_for_next_bounded_mitigation_tranche"]:
            selected.append(item["id"])
    require(priorities == [1, 2, 3], "mitigation gap priorities changed")
    require(tranche_ids == EXPECTED_TRANCHES and len(tranche_ids) == len(set(tranche_ids)),
            "mitigation gap family order, membership, or uniqueness changed")
    require(selected == EXPECTED_SELECTED, "next bounded mitigation tranche changed")

    shortcuts = string_list(value["excluded_shortcuts"], "excluded shortcuts", exact_count=5)
    require(len(shortcuts) == 5, "mitigation shortcut exclusions changed")

    disposition = value["patch_073_disposition"]
    require(isinstance(disposition, dict) and set(disposition) == {"runtime_fields_added", "reason", "next_tranche"},
            "Patch 073 gap disposition fields changed")
    require(type(disposition["runtime_fields_added"]) is int and disposition["runtime_fields_added"] == 0,
            "Patch 073 gap authority silently added an unvalidated runtime field")
    require(isinstance(disposition["reason"], str) and disposition["reason"],
            "Patch 073 gap disposition reason is invalid")
    next_tranche = string_list(disposition["next_tranche"], "Patch 073 next tranche", exact_count=2)
    require(next_tranche == ["text-relocations", "runtime-search-path"], "Patch 073 historical next-tranche disposition changed")

    closeout = value["patch_074_disposition"]
    require(isinstance(closeout, dict) and set(closeout) == {"runtime_fields_added", "reason", "deferred_tranches"},
            "Patch 074 gap disposition fields changed")
    require(type(closeout["runtime_fields_added"]) is int and closeout["runtime_fields_added"] == 0,
            "Patch 074 silently added an unvalidated runtime field")
    require(isinstance(closeout["reason"], str) and closeout["reason"],
            "Patch 074 gap disposition reason is invalid")
    deferred = string_list(closeout["deferred_tranches"], "Patch 074 deferred tranches", exact_count=2)
    require(deferred == ["text-relocations", "runtime-search-path"], "Patch 074 historical deferred-tranche disposition changed")

    current = value["patch_075_disposition"]
    require(isinstance(current, dict) and set(current) == {
        "runtime_fields_added", "private_facts_added", "public_projection",
        "next_implementation_tranche", "reason",
    }, "Patch 075 gap disposition fields changed")
    require(type(current["runtime_fields_added"]) is int and current["runtime_fields_added"] == 0,
            "Patch 075 silently added a public runtime field")
    private_facts = string_list(current["private_facts_added"], "Patch 075 private facts", exact_count=3)
    require(private_facts == [
        "DT_TEXTREL carrier provenance",
        "DT_FLAGS and DF_TEXTREL carrier provenance",
        "private unknown-absent-present-contradictory text-relocation state",
    ], "Patch 075 private text-relocation facts changed")
    require(current["public_projection"] == "deferred_pending_schema_and_consumer_value_gate",
            "Patch 075 public projection boundary changed")
    require(string_list(current["next_implementation_tranche"],
                        "Patch 075 next implementation tranche", exact_count=1)
            == ["runtime-search-path"],
            "Patch 076 implementation handoff changed")
    require(isinstance(current["reason"], str) and current["reason"],
            "Patch 075 gap disposition reason is invalid")

    p076 = value["patch_076_disposition"]
    require(isinstance(p076, dict) and set(p076) == {
        "runtime_fields_added", "private_facts_added", "public_projection",
        "next_implementation_tranche", "next_gate", "reason",
    }, "Patch 076 gap disposition fields changed")
    require(type(p076["runtime_fields_added"]) is int and p076["runtime_fields_added"] == 0,
            "Patch 076 silently added a public runtime field")
    p076_private = string_list(p076["private_facts_added"], "Patch 076 private facts", exact_count=3)
    require(p076_private == [
        "DT_RPATH carrier and exact byte provenance",
        "DT_RUNPATH carrier and exact byte provenance",
        "separate private unknown-absent-present-contradictory RPATH and RUNPATH states",
    ], "Patch 076 private search-path facts changed")
    require(p076["public_projection"] ==
            "deferred_pending_acceptance_parity_schema_and_consumer_value_gate",
            "Patch 076 public projection boundary changed")
    require(string_list(p076["next_implementation_tranche"],
                        "Patch 076 next implementation tranche", exact_count=0) == [],
            "Patch 076 selected an unreviewed implementation tranche")
    require(p076["next_gate"] == "Patch 077 Sprint 12 acceptance and closeout reconciliation",
            "Patch 077 closeout handoff changed")
    require(isinstance(p076["reason"], str) and p076["reason"],
            "Patch 076 gap disposition reason is invalid")

    print(
        "sprint12-mitigation-competitive-gap-smoke: ok "
        f"current_public={len(observed)} private_deferred={len(private)} "
        f"gap_tranches={len(tranches)} selected_next={','.join(selected) if selected else 'none'} "
        f"runtime_fields_added={disposition['runtime_fields_added']} "
        f"closeout_fields_added={closeout['runtime_fields_added']} "
        f"patch075_private_textrel={len(private_facts)} patch075_public_fields={current['runtime_fields_added']} "
        f"patch076_private_search_path={len(p076_private)} patch076_public_fields={p076['runtime_fields_added']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GapError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"sprint12-mitigation-competitive-gap-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
