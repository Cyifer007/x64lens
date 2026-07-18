#!/usr/bin/env python3
"""Validate the exact instruction sequence for the Sprint 10 memory fixture.

GNU objdump is an independent development oracle. It confirms that the source
fixture contains the intended base-plus-zero qword moves and conservative SIB,
displacement, RSP, and 32-bit fallback forms. It does not feed runtime facts.
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
    ("mov", "qwordptr[rdi],rax"), ("ret", ""),
    ("mov", "qwordptr[r8],r9"), ("ret", ""),
    ("mov", "qwordptr[r14],rdx"), ("ret", ""),
    ("mov", "rax,qwordptr[rdi]"), ("ret", ""),
    ("mov", "r9,qwordptr[r8]"), ("ret", ""),
    ("mov", "rdx,qwordptr[r14]"), ("ret", ""),
    ("mov", "qwordptr[rsp],rax"), ("ret", ""),
    ("mov", "qwordptr[rdi+0x8],rax"), ("ret", ""),
    ("mov", "rax,qwordptr[rdi+0x8]"), ("ret", ""),
    ("mov", "qwordptr[rdi],rsp"), ("ret", ""),
    ("mov", "rsp,qwordptr[rdi]"), ("ret", ""),
    ("mov", "eax,dwordptr[rdi]"), ("ret", ""),
]


def normalize_operand(text: str) -> str:
    return re.sub(r"\s+", "", text.strip().lower())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("objdump_output", nargs="?", type=Path)
    args = parser.parse_args()
    if not args.fixture.is_file():
        print(f"validate-sprint10-memory-disassembly: error: missing fixture: {args.fixture}", file=sys.stderr)
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
            print("validate-sprint10-memory-disassembly: error: objdump is required", file=sys.stderr)
            return 127
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr, end="")
            return result.returncode
        text = result.stdout
    else:
        if not args.objdump_output.is_file():
            print(
                "validate-sprint10-memory-disassembly: error: "
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
        print("validate-sprint10-memory-disassembly: error: fixture instruction sequence drifted", file=sys.stderr)
        print(f"expected={EXPECTED!r}", file=sys.stderr)
        print(f"observed={observed!r}", file=sys.stderr)
        return 1

    print(f"validate-sprint10-memory-disassembly: ok instructions={len(observed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
