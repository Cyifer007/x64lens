#!/usr/bin/env python3
"""Regression-test patch-bundle hygiene across common archive root layouts."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "check-patch-bundle-hygiene.sh"


def make_zip(path: Path, members: list[str]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member in members:
            archive.writestr(member, "fixture\n")


def run(path: Path, expected_success: bool) -> None:
    result = subprocess.run(
        ["bash", str(CHECKER), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if expected_success and result.returncode != 0:
        raise RuntimeError(f"clean archive rejected: {result.stderr.strip()}")
    if not expected_success and result.returncode == 0:
        raise RuntimeError(f"generated-path archive accepted: {path.name}")


def main() -> int:
    cases = {
        "test-bin": "changed-files/tests/bin/gadgets",
        "test-results": "arbitrary-root/tests/results/result.json",
        "benchmark-results": "changed-files/benchmarks/results/run.tsv",
        "toy-binary": "changed-files/tests/toy-src/gadgets_capacity",
    }
    with tempfile.TemporaryDirectory(prefix="x64lens-bundle-hygiene-") as temp:
        directory = Path(temp)
        clean = directory / "clean.zip"
        make_zip(
            clean,
            [
                "changed-files/src/main.asm",
                "changed-files/benchmarks/results/.gitkeep",
                "PATCH_RUNBOOK.md",
            ],
        )
        run(clean, expected_success=True)

        for name, member in cases.items():
            archive = directory / f"{name}.zip"
            make_zip(archive, ["changed-files/src/main.asm", member])
            run(archive, expected_success=False)

    print(f"patch-bundle-hygiene-smoke: ok layouts={len(cases) + 1}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"patch-bundle-hygiene-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
