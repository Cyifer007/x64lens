#!/usr/bin/env python3
"""Validate the bounded competitive mitigation gap and next-tranche authority."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    args = parser.parse_args()
    value = load(args.authority)
    require(isinstance(value, dict) and set(value) == {
        "authority_id", "evidence_class", "frozen", "publication_eligible", "purpose",
        "current_public_properties", "current_private_or_deferred",
        "prioritized_gap_tranches", "excluded_shortcuts", "patch_073_disposition",
    }, "mitigation gap authority fields changed")
    require(value["authority_id"] == "sprint12-mitigation-competitive-gap-v1",
            "mitigation gap authority id changed")
    require(value["evidence_class"] == "design-decision" and value["frozen"] is False
            and value["publication_eligible"] is False,
            "mitigation gap evidence boundary changed")

    schema = load(ROOT / "schemas/x64lens-report.schema.json")
    observed = sorted(schema["properties"]["mitigations"]["properties"])
    require(observed == sorted(value["current_public_properties"]),
            f"current mitigation property inventory changed: {observed}")

    private = value["current_private_or_deferred"]
    require(isinstance(private, list) and {item["id"] for item in private} == {"binary-role", "ibt-shstk"},
            "private/deferred mitigation inventory changed")
    require(all(item["status"] == "private-policy-deferred" for item in private),
            "a private role/property fact was promoted through the gap register")

    tranches = value["prioritized_gap_tranches"]
    require(isinstance(tranches, list) and [item["priority"] for item in tranches] == [1, 2, 3],
            "mitigation gap priorities changed")
    require([item["id"] for item in tranches] == [
        "text-relocations", "runtime-search-path", "fortify-source-indicator"
    ], "mitigation gap family order changed")
    require(all(isinstance(item["bounded_evidence"], list) and item["bounded_evidence"]
                and isinstance(item["required_work"], list) and item["required_work"]
                for item in tranches), "mitigation gap evidence or work gate is incomplete")
    selected = [item["id"] for item in tranches if item["selected_for_next_bounded_mitigation_tranche"]]
    require(selected == ["text-relocations", "runtime-search-path"],
            "next bounded mitigation tranche changed")

    disposition = value["patch_073_disposition"]
    require(disposition["runtime_fields_added"] == 0,
            "Patch 073 gap authority silently added an unvalidated runtime field")
    require(disposition["next_tranche"] == selected, "Patch 073 next-tranche disposition disagrees")
    shortcuts = value["excluded_shortcuts"]
    require(isinstance(shortcuts, list) and len(shortcuts) == 5 and len(shortcuts) == len(set(shortcuts)),
            "mitigation shortcut exclusions changed")
    print(
        "sprint12-mitigation-competitive-gap-smoke: ok "
        f"current_public={len(observed)} private_deferred={len(private)} "
        f"gap_tranches={len(tranches)} selected_next={','.join(selected)} runtime_fields_added=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GapError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"sprint12-mitigation-competitive-gap-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
