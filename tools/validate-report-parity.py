#!/usr/bin/env python3
"""Validate shared-fact parity between gadgets and analyze JSON reports.

Purpose:
    Prove that the two commands use one schema-backed analysis result while
    preserving distinct top-level command identity. The helper compares parsed
    JSON objects, not textual serialization order.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class ParityError(Exception):
    """Raised when report identity or shared facts disagree."""


def load(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ParityError(f"cannot read {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ParityError(f"report root is not an object: {path}")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate gadgets/analyze JSON parity except command identity."
    )
    parser.add_argument("gadgets_report", type=Path)
    parser.add_argument("analyze_report", type=Path)
    args = parser.parse_args()

    gadgets = load(args.gadgets_report)
    analyze = load(args.analyze_report)

    for name, document, expected_command in (
        ("gadgets", gadgets, "gadgets"),
        ("analyze", analyze, "analyze"),
    ):
        if document.get("schema_version") != "0.2.0":
            raise ParityError(f"{name} report is not schema 0.2.0")
        if document.get("report_type") != "analysis":
            raise ParityError(f"{name} report_type is not analysis")
        if document.get("command") != expected_command:
            raise ParityError(
                f"{name} command identity is {document.get('command')!r}, "
                f"expected {expected_command!r}"
            )

    normalized_gadgets = dict(gadgets)
    normalized_analyze = dict(analyze)
    normalized_gadgets.pop("command", None)
    normalized_analyze.pop("command", None)
    if normalized_gadgets != normalized_analyze:
        differing = sorted(
            key
            for key in set(normalized_gadgets) | set(normalized_analyze)
            if normalized_gadgets.get(key) != normalized_analyze.get(key)
        )
        raise ParityError(
            "reports differ outside command identity: " + ", ".join(differing)
        )

    print("validate-report-parity: ok schema=0.2.0 commands=gadgets,analyze")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ParityError as exc:
        print(f"validate-report-parity: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
