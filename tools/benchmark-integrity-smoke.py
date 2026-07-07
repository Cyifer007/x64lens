#!/usr/bin/env python3
"""Regression checks for benchmark TSV summarization integrity.

This is a development-smoke gate. It verifies that the summarizer accepts
finite nonnegative rows and rejects malformed, empty, negative, and non-finite
measurement rows before they can become misleading evidence.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

HEADER = "tool\tcommand\ttarget\trun\twall_s\tmaxrss_kb\texit_code\tnote\n"


def write_tsv(path: Path, *rows: str) -> None:
    path.write_text(HEADER + "".join(rows), encoding="utf-8")


def run_summarizer(script: Path, path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def expect_ok(script: Path, path: Path, label: str) -> None:
    result = run_summarizer(script, path)
    if result.returncode != 0:
        raise SystemExit(
            f"benchmark-integrity-smoke: {label}: expected success, got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def expect_fail(script: Path, path: Path, label: str) -> None:
    result = run_summarizer(script, path)
    if result.returncode == 0:
        raise SystemExit(
            f"benchmark-integrity-smoke: {label}: expected failure, got success\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="validate benchmark summarizer input hygiene")
    parser.add_argument(
        "--summarizer",
        type=Path,
        default=Path("benchmarks/scripts/summarize.py"),
        help="path to summarize.py",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="optional directory to preserve generated smoke TSVs",
    )
    args = parser.parse_args(argv)

    summarizer = args.summarizer
    if not summarizer.is_file():
        raise SystemExit(f"benchmark-integrity-smoke: missing summarizer: {summarizer}")

    if args.results_dir is None:
        with tempfile.TemporaryDirectory(prefix="x64lens-benchmark-integrity.") as tmp:
            run_cases(summarizer, Path(tmp))
    else:
        args.results_dir.mkdir(parents=True, exist_ok=True)
        run_cases(summarizer, args.results_dir)

    print("benchmark-integrity-smoke: ok")
    return 0


def run_cases(summarizer: Path, out_dir: Path) -> None:
    valid = out_dir / "valid.tsv"
    write_tsv(valid, "x64lens\tgadgets\ttarget\t1\t0.001\t100\t0\tok\n")
    expect_ok(summarizer, valid, "valid finite row")

    header_only = out_dir / "header-only.tsv"
    header_only.write_text(HEADER, encoding="utf-8")
    expect_fail(summarizer, header_only, "header-only")

    cases = {
        "negative-wall.tsv": "x64lens\tgadgets\ttarget\t1\t-0.1\t100\t0\tbad\n",
        "nan-wall.tsv": "x64lens\tgadgets\ttarget\t1\tnan\t100\t0\tbad\n",
        "inf-wall.tsv": "x64lens\tgadgets\ttarget\t1\tinf\t100\t0\tbad\n",
        "neg-inf-wall.tsv": "x64lens\tgadgets\ttarget\t1\t-inf\t100\t0\tbad\n",
        "nonnumeric-wall.tsv": "x64lens\tgadgets\ttarget\t1\tCommand\t100\t0\tbad\n",
        "negative-rss.tsv": "x64lens\tgadgets\ttarget\t1\t0.1\t-1\t0\tbad\n",
        "nan-rss.tsv": "x64lens\tgadgets\ttarget\t1\t0.1\tnan\t0\tbad\n",
        "inf-rss.tsv": "x64lens\tgadgets\ttarget\t1\t0.1\tinf\t0\tbad\n",
        "neg-inf-rss.tsv": "x64lens\tgadgets\ttarget\t1\t0.1\t-inf\t0\tbad\n",
        "bad-run.tsv": "x64lens\tgadgets\ttarget\t0\t0.1\t100\t0\tbad\n",
    }
    for filename, row in cases.items():
        path = out_dir / filename
        write_tsv(path, row)
        expect_fail(summarizer, path, filename)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
