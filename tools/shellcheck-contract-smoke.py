#!/usr/bin/env python3
"""Validate strict and advisory missing-ShellCheck behavior."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSING = "/nonexistent/x64lens-shellcheck"


def run(strict: bool) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if strict:
        env["SHELLCHECK_STRICT"] = "1"
    else:
        env.pop("SHELLCHECK_STRICT", None)
    return subprocess.run(
        ["make", "--no-print-directory", "shellcheck-smoke", f"SHELLCHECK={MISSING}"],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    strict = run(True)
    strict_text = strict.stdout + strict.stderr
    if strict.returncode == 0 or "SHELLCHECK_STRICT=1 requires" not in strict_text:
        print("shellcheck-contract-smoke: error: strict missing-tool path did not fail clearly", file=sys.stderr)
        return 1

    advisory = run(False)
    advisory_text = advisory.stdout + advisory.stderr
    if advisory.returncode != 0 or "shellcheck-smoke: skipped" not in advisory_text:
        print("shellcheck-contract-smoke: error: advisory missing-tool path did not skip cleanly", file=sys.stderr)
        return 1

    print("shellcheck-contract-smoke: ok strict_missing=reject advisory_missing=skip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
