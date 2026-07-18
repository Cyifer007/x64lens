#!/usr/bin/env python3
"""Validate the one-per-pattern Sprint 10 architectural-effect fixture.

GNU objdump is an independent development oracle for fixture bytes only. It
does not feed runtime analyzer facts or change program-header scan authority.
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
    ("ret", ""), ("ret", "0x0"),
    ("pop", "rax"), ("ret", ""),
    ("pop", "rcx"), ("ret", ""),
    ("pop", "rdx"), ("ret", ""),
    ("pop", "rbx"), ("ret", ""),
    ("pop", "rsp"), ("ret", ""),
    ("pop", "rbp"), ("ret", ""),
    ("pop", "rsi"), ("ret", ""),
    ("pop", "rdi"), ("ret", ""),
    ("pop", "r8"), ("ret", ""),
    ("pop", "r9"), ("ret", ""),
    ("pop", "r10"), ("ret", ""),
    ("pop", "r11"), ("ret", ""),
    ("pop", "r12"), ("ret", ""),
    ("pop", "r13"), ("ret", ""),
    ("pop", "r14"), ("ret", ""),
    ("pop", "r15"), ("ret", ""),
    ("leave", ""), ("ret", ""),
    ("syscall", ""), ("ret", ""),
    ("pop", "rdi"), ("pop", "rsi"), ("ret", ""),
    ("mov", "rdi,rax"), ("ret", ""),
    ("add", "rsp,0x8"), ("ret", ""),
    ("mov", "qwordptr[rdi],rax"), ("ret", ""),
    ("mov", "rax,qwordptr[rdi]"), ("ret", ""),
]


def normalize_operand(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().lower())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("objdump_output", nargs="?", type=Path)
    args = parser.parse_args()
    if not args.fixture.is_file():
        print(f"validate-sprint10-effects-disassembly: error: missing fixture: {args.fixture}", file=sys.stderr)
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
            print("validate-sprint10-effects-disassembly: error: objdump is required", file=sys.stderr)
            return 127
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr, end="")
            return result.returncode
        text = result.stdout
    else:
        if not args.objdump_output.is_file():
            print(f"validate-sprint10-effects-disassembly: error: missing transcript: {args.objdump_output}", file=sys.stderr)
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
        print("validate-sprint10-effects-disassembly: error: fixture instruction sequence drifted", file=sys.stderr)
        print(f"expected={EXPECTED!r}", file=sys.stderr)
        print(f"observed={observed!r}", file=sys.stderr)
        return 1

    print(f"validate-sprint10-effects-disassembly: ok instructions={len(observed)} patterns=25")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
