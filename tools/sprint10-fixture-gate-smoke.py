#!/usr/bin/env python3
"""Prove the Sprint 10 family runner stops before later steps after a failed gate."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "sprint10-fixture-smoke.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-sprint10-gate-") as temp:
        root = Path(temp)
        fixture = root / "fixture.bin"
        fixture.write_bytes(b"fixture")
        validator_marker = root / "validator.marker"
        binary_marker = root / "binary.marker"

        validator = root / "fail-validator.py"
        validator.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            f"Path({str(validator_marker)!r}).write_text('called\\n')\n"
            "raise SystemExit(7)\n",
            encoding="utf-8",
        )
        validator.chmod(0o755)

        binary = root / "must-not-run.py"
        binary.write_text(
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            f"Path({str(binary_marker)!r}).write_text('called\\n')\n"
            "raise SystemExit(0)\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)

        spec = root / "spec.json"
        spec.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "purpose": "fail-fast regression",
                    "families": {
                        "gate": {
                            "fixture": str(fixture),
                            "disassembly_validator": str(validator),
                            "json_mode": "generic",
                            "expected_counts": {
                                "raw_candidate_count": 0,
                                "exact_pattern_count": 0,
                                "semantic_candidate_count": 0,
                                "unknown_candidate_count": 0,
                                "scored_candidate_count": 0,
                            },
                            "pattern_counts": {},
                            "text_contains": [],
                            "false_positive_boundaries": ["synthetic one", "synthetic two"],
                            "score_policy": "synthetic",
                        }
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--binary",
                str(binary),
                "--spec",
                str(spec),
                "--family",
                "gate",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if result.returncode == 0:
            print("sprint10-fixture-gate-smoke: runner false-passed a failed validator", file=sys.stderr)
            return 1
        if not validator_marker.is_file():
            print("sprint10-fixture-gate-smoke: failing validator did not execute", file=sys.stderr)
            return 1
        if binary_marker.exists():
            print("sprint10-fixture-gate-smoke: later analyzer step executed after failure", file=sys.stderr)
            return 1

    print("sprint10-fixture-gate-smoke: ok failed_validator=7 later_steps=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
