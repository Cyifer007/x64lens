#!/usr/bin/env python3
"""Run Sprint 10 semantic-family fixtures through one fail-fast validation path."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "tests" / "expected" / "sprint10-fixture-suite.json"


def fail(message: str) -> "NoReturn":
    print(f"sprint10-fixture-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(command: list[str], *, stdout: Path | None = None) -> None:
    if stdout is None:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
        )
    else:
        with stdout.open("wb") as stream:
            result = subprocess.run(
                command,
                cwd=ROOT,
                stdout=stream,
                stderr=subprocess.PIPE,
                check=False,
            )
    if result.returncode != 0:
        sys.stderr.buffer.write(result.stderr)
        fail(f"command exited {result.returncode}: {' '.join(command)}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read JSON {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path} is not a JSON object")
    return value


def validate_spec(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if spec.get("schema_version") != "1.0.0":
        fail("unsupported family-coverage schema")
    families = spec.get("families")
    if not isinstance(families, dict) or not families:
        fail("families must be a non-empty object")
    required = {
        "fixture", "disassembly_validator", "json_mode", "expected_counts",
        "pattern_counts", "text_contains", "false_positive_boundaries", "score_policy",
    }
    for name, entry in families.items():
        if not isinstance(entry, dict):
            fail(f"family {name} must be an object")
        missing = required - set(entry)
        if missing:
            fail(f"family {name} missing fields: {sorted(missing)}")
        notes = entry["false_positive_boundaries"]
        if not isinstance(notes, list) or len(notes) < 2 or not all(isinstance(x, str) and x for x in notes):
            fail(f"family {name} requires at least two false-positive boundary notes")
        if not isinstance(entry["score_policy"], str) or not entry["score_policy"]:
            fail(f"family {name} score policy is empty")
    return families


def validate_report(family: str, entry: dict[str, Any], report: dict[str, Any]) -> None:
    counts = report.get("counts")
    gadgets = report.get("gadgets")
    if not isinstance(counts, dict) or not isinstance(gadgets, list):
        fail(f"family {family} report shape is invalid")
    for key, expected in entry["expected_counts"].items():
        if counts.get(key) != expected:
            fail(f"family {family} {key}: expected {expected}, got {counts.get(key)}")
    observed = Counter(gadget.get("pattern") for gadget in gadgets if isinstance(gadget, dict))
    for pattern, expected in entry["pattern_counts"].items():
        if observed.get(pattern, 0) != expected:
            fail(f"family {family} pattern {pattern!r}: expected {expected}, got {observed.get(pattern, 0)}")


def run_family(binary: Path, family: str, entry: dict[str, Any]) -> None:
    fixture = ROOT / entry["fixture"]
    validator = ROOT / entry["disassembly_validator"]
    if not binary.is_file() or not fixture.is_file() or not validator.is_file():
        fail(f"family {family} is missing binary, fixture, or disassembly validator")

    with tempfile.TemporaryDirectory(prefix=f"x64lens-sprint10-{family}-") as temp:
        out = Path(temp)
        gadgets_json = out / "gadgets.json"
        analyze_json = out / "analyze.json"
        gadgets_text = out / "gadgets.txt"

        run([sys.executable, str(validator), str(fixture)])
        run([str(binary), "gadgets", "--format", "json", "--max-depth", "4", str(fixture)], stdout=gadgets_json)
        run([str(binary), "analyze", "--format", "json", "--max-depth", "4", str(fixture)], stdout=analyze_json)

        common = [
            sys.executable, str(ROOT / "tools" / "validate-json-report.py"),
            "--mode", entry["json_mode"], "--require-schema", "0.2.0",
            "--require-provenance", "--require-sprint10-effects",
            "--require-sprint10-transfer", "--require-sprint10-memory",
            "--require-sprint10-architectural-effects",
        ]
        run(common + ["--expected-command", "gadgets", str(gadgets_json)])
        run(common + ["--expected-command", "analyze", str(analyze_json)])
        run([sys.executable, str(ROOT / "tools" / "validate-report-parity.py"), str(gadgets_json), str(analyze_json)])

        report = load_json(gadgets_json)
        validate_report(family, entry, report)
        run([str(binary), "gadgets", "--max-depth", "4", str(fixture)], stdout=gadgets_text)
        text = gadgets_text.read_text(encoding="utf-8")
        for required in entry["text_contains"]:
            if required not in text:
                fail(f"family {family} text output missing {required!r}")

    counts = entry["expected_counts"]
    print(
        f"sprint10-{family.replace('_', '-')}-smoke: ok "
        f"candidates={counts['raw_candidate_count']} scored={counts['scored_candidate_count']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--family", default="all")
    args = parser.parse_args()

    spec = load_json(args.spec)
    families = validate_spec(spec)
    selected = list(families) if args.family == "all" else [args.family]
    for family in selected:
        if family not in families:
            fail(f"unknown family {family!r}")
        run_family(args.binary.resolve(), family, families[family])
    if args.family == "all":
        print(f"sprint10-family-coverage-smoke: ok families={len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
