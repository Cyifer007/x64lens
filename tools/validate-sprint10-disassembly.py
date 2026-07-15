#!/usr/bin/env python3
"""Validate the emitted instruction sequence for the Sprint 10 fixture.

This check establishes that the host assembler/linker emitted the exact
instruction order expected by the semantic fixture before x64lens output is
interpreted. GNU objdump is a development oracle only; it does not feed runtime
analysis facts.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROW = re.compile(
    r"^\s*[0-9a-fA-F]+:\s+(?:(?:[0-9a-fA-F]{2})\s+)+"
    r"([A-Za-z0-9_.]+)(?:\s+(.*?))?\s*$"
)

EXPECTED = [
    ("pop", "rdi"),
    ("pop", "rsi"),
    ("ret", ""),
    ("pop", "r8"),
    ("pop", "r9"),
    ("ret", ""),
    ("pop", "rdx"),
    ("pop", "rcx"),
    ("ret", ""),
    ("pop", "rdi"),
    ("pop", "rdi"),
    ("ret", ""),
    ("pop", "rbx"),
    ("pop", "rdi"),
    ("ret", ""),
]


def normalize_operand(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().lower())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()

    if not args.fixture.is_file():
        print(f"validate-sprint10-disassembly: error: missing fixture: {args.fixture}", file=sys.stderr)
        return 1

    try:
        result = subprocess.run(
            ["objdump", "-d", "-w", "-Mintel", str(args.fixture)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("validate-sprint10-disassembly: error: objdump is required", file=sys.stderr)
        return 127

    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
        return result.returncode

    observed: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        match = ROW.match(line)
        if match is None:
            continue
        mnemonic = match.group(1).lower()
        operand = normalize_operand(match.group(2) or "")
        if mnemonic == "retq":
            mnemonic = "ret"
        observed.append((mnemonic, operand))
        if len(observed) == len(EXPECTED):
            break

    if observed != EXPECTED:
        print("validate-sprint10-disassembly: error: fixture instruction sequence drifted", file=sys.stderr)
        print(f"expected={EXPECTED!r}", file=sys.stderr)
        print(f"observed={observed!r}", file=sys.stderr)
        return 1

    print(f"validate-sprint10-disassembly: ok instructions={len(observed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
