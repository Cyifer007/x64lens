#!/usr/bin/env python3
"""Regression checks for benchmark TSV summarization integrity.

This development-smoke gate verifies that the summarizer accepts finite
nonnegative rows, rejects malformed measurement evidence, and never merges rows
whose tool or report-schema identities differ.
"""
from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
import tempfile
from pathlib import Path

HEADER = (
    "tool\ttool_version\tschema_version\tcommand\ttarget\trun\t"
    "wall_s\tmaxrss_kb\texit_code\tnote\n"
)


def row(
    *,
    tool_version: str = "0.1.0-dev",
    schema_version: str = "0.2.0",
    run: str = "1",
    wall: str = "0.001",
    rss: str = "100",
    exit_code: str = "0",
    note: str = "ok",
) -> str:
    return (
        f"x64lens\t{tool_version}\t{schema_version}\tgadgets\ttarget\t{run}\t"
        f"{wall}\t{rss}\t{exit_code}\t{note}\n"
    )


def write_tsv(path: Path, *rows: str) -> None:
    path.write_text(HEADER + "".join(rows), encoding="utf-8")


def run_summarizer(
    script: Path,
    path: Path,
    *,
    output_format: str = "markdown",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--format", output_format, str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def expect_ok(script: Path, path: Path, label: str) -> subprocess.CompletedProcess[str]:
    result = run_summarizer(script, path)
    if result.returncode != 0:
        raise SystemExit(
            f"benchmark-integrity-smoke: {label}: expected success, got {result.returncode}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def expect_fail(script: Path, path: Path, label: str) -> None:
    result = run_summarizer(script, path)
    if result.returncode == 0:
        raise SystemExit(
            f"benchmark-integrity-smoke: {label}: expected failure, got success\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def require_identity_stratification(script: Path, path: Path) -> None:
    result = run_summarizer(script, path, output_format="csv")
    if result.returncode != 0:
        raise SystemExit(
            "benchmark-integrity-smoke: mixed identity summary failed\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    rows = list(csv.DictReader(io.StringIO(result.stdout)))
    if len(rows) != 3:
        raise SystemExit(
            "benchmark-integrity-smoke: mixed tool/schema identities were merged "
            f"into {len(rows)} summary row(s)"
        )
    identities = {(item["tool_version"], item["schema_version"], item["runs"]) for item in rows}
    expected = {
        ("0.1.0-dev", "0.1.0", "1"),
        ("0.1.0-dev", "0.2.0", "1"),
        ("0.1.1-dev", "0.2.0", "1"),
    }
    if identities != expected:
        raise SystemExit(
            "benchmark-integrity-smoke: unexpected identity groups: "
            f"{sorted(identities)}"
        )


def run_cases(summarizer: Path, out_dir: Path) -> None:
    valid = out_dir / "valid.tsv"
    write_tsv(valid, row())
    expect_ok(summarizer, valid, "valid finite row")

    mixed = out_dir / "mixed-schema.tsv"
    write_tsv(
        mixed,
        row(tool_version="0.1.0-dev", schema_version="0.1.0", run="1"),
        row(tool_version="0.1.0-dev", schema_version="0.2.0", run="2"),
        row(tool_version="0.1.1-dev", schema_version="0.2.0", run="3"),
    )
    require_identity_stratification(summarizer, mixed)

    header_only = out_dir / "header-only.tsv"
    header_only.write_text(HEADER, encoding="utf-8")
    expect_fail(summarizer, header_only, "header-only")

    cases = {
        "negative-wall.tsv": row(wall="-0.1", note="bad"),
        "nan-wall.tsv": row(wall="nan", note="bad"),
        "inf-wall.tsv": row(wall="inf", note="bad"),
        "neg-inf-wall.tsv": row(wall="-inf", note="bad"),
        "nonnumeric-wall.tsv": row(wall="Command", note="bad"),
        "negative-rss.tsv": row(rss="-1", note="bad"),
        "nan-rss.tsv": row(rss="nan", note="bad"),
        "inf-rss.tsv": row(rss="inf", note="bad"),
        "neg-inf-rss.tsv": row(rss="-inf", note="bad"),
        "bad-run.tsv": row(run="0", note="bad"),
    }
    for filename, value in cases.items():
        path = out_dir / filename
        write_tsv(path, value)
        expect_fail(summarizer, path, filename)


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

    if not args.summarizer.is_file():
        raise SystemExit(f"benchmark-integrity-smoke: missing summarizer: {args.summarizer}")

    if args.results_dir is None:
        with tempfile.TemporaryDirectory(prefix="x64lens-benchmark-integrity.") as tmp:
            run_cases(args.summarizer, Path(tmp))
    else:
        args.results_dir.mkdir(parents=True, exist_ok=True)
        run_cases(args.summarizer, args.results_dir)

    print("benchmark-integrity-smoke: ok identity_groups=3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
