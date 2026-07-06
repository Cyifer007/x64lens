#!/usr/bin/env python3
"""Run optional mitigation/metadata comparison helpers when installed.

This script intentionally does not treat checksec or rabin2 as authoritative
oracles. It confirms that optional comparator workflows can execute against the
controlled corpus and preserves their version/output metadata for local review.
Missing optional tools are recorded as skipped, not as validation failures.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def run(cmd: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def first_line(text: str) -> str:
    return text.splitlines()[0] if text.splitlines() else ""


def tool_version(tool: str, timeout: float) -> str:
    if tool == "checksec":
        proc = run([tool, "--version"], timeout)
    elif tool == "rabin2":
        proc = run([tool, "-v"], timeout)
    else:
        proc = run([tool, "--version"], timeout)
    return first_line((proc.stdout or proc.stderr).strip()) or "unknown"


def default_targets(root: Path) -> list[Path]:
    candidates = [
        root / "tests/bin/minimal_nopie",
        root / "tests/bin/minimal_pie_canary",
        root / "tests/bin/minimal_execstack",
        root / "tests/bin/gadgets",
    ]
    return [path for path in candidates if path.exists() and path.is_file()]


def run_checksec(target: Path, timeout: float) -> dict[str, Any]:
    proc = run(["checksec", f"--file={target}"], timeout)
    return {
        "command": ["checksec", f"--file={str(target)}"],
        "exit_code": proc.returncode,
        "stdout_head": proc.stdout.splitlines()[:20],
        "stderr_head": proc.stderr.splitlines()[:20],
        "ok": proc.returncode == 0,
    }


def run_rabin2(target: Path, timeout: float) -> dict[str, Any]:
    proc = run(["rabin2", "-I", str(target)], timeout)
    return {
        "command": ["rabin2", "-I", str(target)],
        "exit_code": proc.returncode,
        "stdout_head": proc.stdout.splitlines()[:40],
        "stderr_head": proc.stderr.splitlines()[:20],
        "ok": proc.returncode == 0,
    }


def run_x64lens(binary: Path, target: Path, timeout: float) -> dict[str, Any]:
    proc = run([str(binary), "mitigations", str(target)], timeout)
    return {
        "command": [str(binary), "mitigations", str(target)],
        "exit_code": proc.returncode,
        "stdout_head": proc.stdout.splitlines()[:40],
        "stderr_head": proc.stderr.splitlines()[:20],
        "ok": proc.returncode == 0,
    }


def run_compare_helper(script: Path, binary: Path, target: Path, timeout: float, order: str) -> dict[str, Any]:
    if order == "target-tool":
        command = ["bash", str(script), str(target), str(binary)]
    elif order == "tool-target":
        command = ["bash", str(script), str(binary), str(target)]
    else:
        raise ValueError(f"unknown helper order: {order}")

    proc = run(command, timeout)
    lines = proc.stdout.splitlines()
    identity = lines[0] if lines else ""
    identity_ok = f"tool={binary}" in identity and f"target={target}" in identity
    return {
        "command": command,
        "exit_code": proc.returncode,
        "identity_line": identity,
        "stdout_head": lines[:30],
        "stderr_head": proc.stderr.splitlines()[:20],
        "ok": proc.returncode == 0 and identity_ok,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="run optional checksec/rabin2 comparison helpers")
    parser.add_argument("--binary", type=Path, default=Path("./build/x64lens"))
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--results-dir", type=Path, default=Path("./tests/results/optional-tool-comparison"))
    parser.add_argument("targets", nargs="*", type=Path)
    args = parser.parse_args(argv)

    if not args.binary.is_file() or not os.access(args.binary, os.X_OK):
        print(f"optional-tool-comparison-smoke: error: binary is not executable: {args.binary}", file=sys.stderr)
        return 1

    targets = args.targets or default_targets(Path.cwd())
    if not targets:
        print("optional-tool-comparison-smoke: error: no targets found", file=sys.stderr)
        return 1

    tools = {
        "checksec": shutil.which("checksec"),
        "rabin2": shutil.which("rabin2"),
    }
    inventory = {
        name: {
            "path": path,
            "available": path is not None,
            "version": tool_version(name, args.timeout) if path else "missing",
        }
        for name, path in tools.items()
    }

    cases: list[dict[str, Any]] = []
    failures: list[str] = []
    for target in targets:
        case: dict[str, Any] = {
            "target": str(target),
            "x64lens": run_x64lens(args.binary, target, args.timeout),
            "checksec": "skipped-missing",
            "rabin2": "skipped-missing",
            "compare_helpers": {},
        }
        if not case["x64lens"]["ok"]:
            failures.append(f"x64lens mitigations failed for {target}")
        if inventory["checksec"]["available"]:
            case["checksec"] = run_checksec(target, args.timeout)
            if not case["checksec"]["ok"]:
                failures.append(f"checksec failed for {target}")
            helper_script = Path("tools/compare-checksec.sh")
            case["compare_helpers"]["checksec_target_tool"] = run_compare_helper(
                helper_script, args.binary, target, args.timeout, "target-tool"
            )
            case["compare_helpers"]["checksec_tool_target"] = run_compare_helper(
                helper_script, args.binary, target, args.timeout, "tool-target"
            )
            for helper_name in ("checksec_target_tool", "checksec_tool_target"):
                if not case["compare_helpers"][helper_name]["ok"]:
                    failures.append(f"{helper_name} helper failed target identity for {target}")
        if inventory["rabin2"]["available"]:
            case["rabin2"] = run_rabin2(target, args.timeout)
            if not case["rabin2"]["ok"]:
                failures.append(f"rabin2 -I failed for {target}")
            helper_script = Path("tools/compare-rabin2.sh")
            case["compare_helpers"]["rabin2_target_tool"] = run_compare_helper(
                helper_script, args.binary, target, args.timeout, "target-tool"
            )
            case["compare_helpers"]["rabin2_tool_target"] = run_compare_helper(
                helper_script, args.binary, target, args.timeout, "tool-target"
            )
            for helper_name in ("rabin2_target_tool", "rabin2_tool_target"):
                if not case["compare_helpers"][helper_name]["ok"]:
                    failures.append(f"{helper_name} helper failed target identity for {target}")
        cases.append(case)

    args.results_dir.mkdir(parents=True, exist_ok=True)
    out = args.results_dir / "optional-tool-comparison-latest.json"
    out.write_text(
        json.dumps({"inventory": inventory, "cases": cases}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if failures:
        for failure in failures:
            print(f"optional-tool-comparison-smoke: error: {failure}", file=sys.stderr)
        print(f"optional-tool-comparison-smoke: failed results={out}", file=sys.stderr)
        return 1

    present = [name for name, info in inventory.items() if info["available"]]
    print(
        f"optional-tool-comparison-smoke: ok cases={len(cases)} "
        f"optional_tools={','.join(present) if present else 'none'} results={out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
