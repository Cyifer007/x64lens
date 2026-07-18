#!/usr/bin/env python3
"""Prove Sprint 10 score values are enforced by both contract gates."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests" / "expected" / "sprint10-family-coverage.json"
GATES = (
    (ROOT / "tools" / "sprint10-family-coverage-smoke.py", "--manifest"),
    (ROOT / "tools" / "sprint10-contract-reconciliation-smoke.py", "--semantic"),
)
MUTATIONS = (
    ("ordered_multi_pop", "scored:94"),
    ("stack_adjust", "scored:34"),
)


def fail(message: str) -> "NoReturn":
    print(f"sprint10-score-policy-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    families = source.get("families")
    if not isinstance(families, list):
        fail("source manifest has no family array")

    checks = 0
    with tempfile.TemporaryDirectory(prefix="x64lens-score-policy-") as tmp_name:
        tmp = Path(tmp_name)
        for family_id, replacement in MUTATIONS:
            document = copy.deepcopy(source)
            matched = 0
            for family in document["families"]:
                if family.get("id") == family_id:
                    family["score_policy"] = replacement
                    matched += 1
            if matched != 1:
                fail(f"cannot find exactly one family {family_id}")
            manifest = tmp / f"{family_id}.json"
            manifest.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
            for gate, option in GATES:
                result = subprocess.run(
                    [sys.executable, str(gate), option, str(manifest)],
                    cwd=ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                checks += 1
                if result.returncode == 0:
                    fail(f"{gate.name} accepted {family_id} policy {replacement}")

    print(
        "sprint10-score-policy-smoke: ok "
        f"mutations={len(MUTATIONS)} gates={len(GATES)} checks={checks}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
