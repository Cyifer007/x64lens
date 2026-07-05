#!/usr/bin/env python3
"""Summarize x64lens benchmark TSV files.

The benchmark harness preserves raw TSV rows. This helper computes development
summary tables without replacing the raw evidence. It intentionally uses only
Python standard-library modules so the repository remains dependency-light.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable


NUMERIC_NA = {"", "NA", "null", "None"}


def as_float(value: str) -> float | None:
    if value in NUMERIC_NA:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def require_nonnegative_number(row: dict[str, str], field: str, source: Path, row_number: int) -> None:
    value = row.get(field, "")
    parsed = as_float(value)
    if parsed is None:
        raise ValueError(f"{source}:{row_number}: {field} must be numeric, got {value!r}")
    if parsed < 0:
        raise ValueError(f"{source}:{row_number}: {field} must be non-negative, got {value!r}")


def require_nonnegative_int(row: dict[str, str], field: str, source: Path, row_number: int) -> None:
    value = row.get(field, "")
    if not value.isdigit():
        raise ValueError(f"{source}:{row_number}: {field} must be a non-negative integer, got {value!r}")


def validate_row(row: dict[str, str], source: Path, row_number: int) -> None:
    require_nonnegative_number(row, "wall_s", source, row_number)
    require_nonnegative_int(row, "maxrss_kb", source, row_number)
    require_nonnegative_int(row, "exit_code", source, row_number)
    if "run" in row:
        require_nonnegative_int(row, "run", source, row_number)
        if int(row["run"]) < 1:
            raise ValueError(f"{source}:{row_number}: run must be >= 1, got {row['run']!r}")


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    frac = rank - lo
    return ordered[lo] + (ordered[hi] - ordered[lo]) * frac


def fmt(value: float | None) -> str:
    if value is None:
        return "NA"
    return f"{value:.6g}"


def load_rows(paths: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            print(f"warning: benchmark file not found: {path}", file=sys.stderr)
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if not reader.fieldnames:
                print(f"warning: benchmark file has no header: {path}", file=sys.stderr)
                continue
            for row_number, row in enumerate(reader, start=2):
                validate_row(row, path, row_number)
                row["source_file"] = str(path)
                rows.append(row)
    return rows


def summarize(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (
            row.get("tool", "unknown"),
            row.get("command", "unknown"),
            row.get("target", "unknown"),
        )
        groups[key].append(row)

    summary: list[dict[str, str]] = []
    for (tool, command, target), group in sorted(groups.items()):
        wall_values = [v for v in (as_float(row.get("wall_s", "")) for row in group) if v is not None]
        rss_values = [v for v in (as_float(row.get("maxrss_kb", "")) for row in group) if v is not None]
        exit_codes = sorted({row.get("exit_code", "NA") for row in group})
        notes = sorted({row.get("note", "NA") for row in group})

        summary.append(
            {
                "tool": tool,
                "command": command,
                "target": target,
                "runs": str(len(group)),
                "median_wall_s": fmt(statistics.median(wall_values) if wall_values else None),
                "p95_wall_s": fmt(percentile(wall_values, 0.95)),
                "max_rss_kb": fmt(max(rss_values) if rss_values else None),
                "exit_codes": ",".join(exit_codes),
                "notes": ",".join(notes),
            }
        )
    return summary


def emit_markdown(rows: list[dict[str, str]]) -> None:
    headers = [
        "tool",
        "command",
        "target",
        "runs",
        "median_wall_s",
        "p95_wall_s",
        "max_rss_kb",
        "exit_codes",
        "notes",
    ]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        print("| " + " | ".join(row.get(header, "") for header in headers) + " |")


def emit_csv(rows: list[dict[str, str]]) -> None:
    headers = [
        "tool",
        "command",
        "target",
        "runs",
        "median_wall_s",
        "p95_wall_s",
        "max_rss_kb",
        "exit_codes",
        "notes",
    ]
    writer = csv.DictWriter(sys.stdout, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Summarize x64lens benchmark TSV rows")
    parser.add_argument("paths", nargs="+", type=Path, help="benchmark TSV files")
    parser.add_argument("--format", choices=("markdown", "csv"), default="markdown")
    args = parser.parse_args(argv)

    try:
        rows = load_rows(args.paths)
    except ValueError as exc:
        print(f"error: invalid benchmark row: {exc}", file=sys.stderr)
        return 1
    if not rows:
        print("error: no benchmark rows found", file=sys.stderr)
        return 1

    summary = summarize(rows)
    if args.format == "csv":
        emit_csv(summary)
    else:
        emit_markdown(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
