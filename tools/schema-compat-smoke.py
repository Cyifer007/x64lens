#!/usr/bin/env python3
"""Exercise x64lens schema 0.1.0 compatibility and 0.2.0 invariants.

Purpose:
    Keep one representative historical report consumable while proving that
    current reports require command identity and internally consistent bounded
    completeness facts. This is a repository validation helper, not a runtime
    dependency or a publication benchmark.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate-json-report.py"
LEGACY = ROOT / "tests" / "expected" / "x64lens-report-0.1.0.json"
CURRENT = ROOT / "tests" / "expected" / "x64lens-report-0.2.0.json"
SCHEMAS = (
    ROOT / "schemas" / "x64lens-report-0.1.0.schema.json",
    ROOT / "schemas" / "x64lens-report.schema.json",
)


def run_validator(path: Path, *args: str, expect_success: bool) -> None:
    command = [sys.executable, str(VALIDATOR), *args, str(path)]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if expect_success and result.returncode != 0:
        raise RuntimeError(
            f"expected validator success for {path.name}: {result.stderr.strip()}"
        )
    if not expect_success and result.returncode == 0:
        raise RuntimeError(f"expected validator rejection for {path.name}")


def write_mutation(directory: Path, name: str, document: dict[str, Any]) -> Path:
    path = directory / name
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    for path in (*SCHEMAS, LEGACY, CURRENT):
        with path.open("r", encoding="utf-8") as stream:
            json.load(stream)

    run_validator(LEGACY, "--require-schema", "0.1.0", expect_success=True)
    run_validator(
        CURRENT,
        "--require-schema",
        "0.2.0",
        "--expected-command",
        "gadgets",
        expect_success=True,
    )

    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="x64lens-schema-compat-") as temp:
        directory = Path(temp)

        mutation = deepcopy(current)
        mutation["analysis"]["candidate_count"] = 1
        run_validator(
            write_mutation(directory, "count-mismatch.json", mutation),
            "--require-schema",
            "0.2.0",
            expect_success=False,
        )

        mutation = deepcopy(current)
        mutation["analysis"]["candidate_truncated"] = True
        run_validator(
            write_mutation(directory, "complete-and-truncated.json", mutation),
            "--require-schema",
            "0.2.0",
            expect_success=False,
        )

        mutation = deepcopy(current)
        mutation["analysis"]["candidate_dropped_count_known"] = False
        run_validator(
            write_mutation(directory, "unknown-dropped-nonnul.json", mutation),
            "--require-schema",
            "0.2.0",
            expect_success=False,
        )

        mutation = deepcopy(current)
        mutation["analysis"]["regions_scanned"] = 1
        run_validator(
            write_mutation(directory, "region-overrun.json", mutation),
            "--require-schema",
            "0.2.0",
            expect_success=False,
        )

        run_validator(
            CURRENT,
            "--require-schema",
            "0.2.0",
            "--expected-command",
            "analyze",
            expect_success=False,
        )

    print("schema-compat-smoke: ok legacy=0.1.0 current=0.2.0 rejection_cases=5")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"schema-compat-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
