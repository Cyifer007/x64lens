#!/usr/bin/env python3
"""Validate the exact instruction sequence for the Sprint 10 stack-adjust fixture.

GNU objdump is an independent development oracle. It confirms source-fixture
shape only and does not feed x64lens runtime facts.
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
    ("add", "rsp,0x8"), ("ret", ""),
    ("add", "rsp,0x20"), ("ret", ""),
    ("add", "rsp,0x0"), ("ret", ""),
    ("add", "rsp,0xfffffffffffffff8"), ("ret", ""),
    ("add", "rsp,0x7"), ("ret", ""),
    ("add", "rax,0x8"), ("ret", ""),
    ("sub", "rsp,0x8"), ("ret", ""),
]


def normalize_operand(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().lower())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument(
        "objdump_output",
        nargs="?",
        type=Path,
        help="optional saved objdump transcript; when omitted, objdump is run",
    )
    args = parser.parse_args()
    if not args.fixture.is_file():
        print(
            f"validate-sprint10-stack-adjust-disassembly: error: missing fixture: {args.fixture}",
            file=sys.stderr,
        )
        return 1

    if args.objdump_output is None:
        try:
            result = subprocess.run(
                ["objdump", "-d", "-w", "-Mintel", str(args.fixture)],
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            print(
                "validate-sprint10-stack-adjust-disassembly: error: objdump is required",
                file=sys.stderr,
            )
            return 127
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr, end="")
            return result.returncode
        text = result.stdout
    else:
        if not args.objdump_output.is_file():
            print(
                "validate-sprint10-stack-adjust-disassembly: error: "
                f"missing transcript: {args.objdump_output}",
                file=sys.stderr,
            )
            return 1
        text = args.objdump_output.read_text(encoding="utf-8")

    observed: list[tuple[str, str]] = []
    for line in text.splitlines():
        match = ROW.match(line)
        if match is None:
            continue
        mnemonic = match.group(1).lower()
        if mnemonic == "retq":
            mnemonic = "ret"
        observed.append((mnemonic, normalize_operand(match.group(2) or "")))
        if len(observed) == len(EXPECTED):
            break

    if observed != EXPECTED:
        print(
            "validate-sprint10-stack-adjust-disassembly: error: fixture instruction sequence drifted",
            file=sys.stderr,
        )
        print(f"expected={EXPECTED!r}", file=sys.stderr)
        print(f"observed={observed!r}", file=sys.stderr)
        return 1

    print(f"validate-sprint10-stack-adjust-disassembly: ok instructions={len(observed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
