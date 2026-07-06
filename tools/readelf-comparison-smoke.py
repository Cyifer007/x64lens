#!/usr/bin/env python3
"""Automated readelf comparison smoke for x64lens metadata and loader facts.

The goal is not to make readelf an oracle for every x64lens policy decision.
This script compares stable, mechanical fields where x64lens and binutils use
compatible meanings: ELF header identity, table offsets/sizes/counts, file
size, loader-visible LOAD/DYNAMIC/GNU_STACK/GNU_RELRO presence, and executable
LOAD region counts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HEX_RE = re.compile(r"0x[0-9a-fA-F]+")
LOAD_RE = re.compile(
    r"^\s*LOAD\s+"
    r"(?P<offset>0x[0-9a-fA-F]+)\s+"
    r"(?P<vaddr>0x[0-9a-fA-F]+)\s+"
    r"(?P<paddr>0x[0-9a-fA-F]+)\s+"
    r"(?P<filesz>0x[0-9a-fA-F]+)\s+"
    r"(?P<memsz>0x[0-9a-fA-F]+)\s+"
    r"(?P<flags>[RWE ]+?)\s+"
    r"(?P<align>0x[0-9a-fA-F]+)\s*$"
)
STACK_RE = re.compile(
    r"^\s*GNU_STACK\s+"
    r"(?P<offset>0x[0-9a-fA-F]+)\s+"
    r"(?P<vaddr>0x[0-9a-fA-F]+)\s+"
    r"(?P<paddr>0x[0-9a-fA-F]+)\s+"
    r"(?P<filesz>0x[0-9a-fA-F]+)\s+"
    r"(?P<memsz>0x[0-9a-fA-F]+)\s+"
    r"(?P<flags>[RWE ]+?)\s+"
    r"(?P<align>0x[0-9a-fA-F]+)\s*$"
)


def run(cmd: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def parse_int(value: str) -> int:
    value = value.strip()
    match = HEX_RE.search(value)
    if match:
        return int(match.group(0), 16)
    number = re.search(r"\b\d+\b", value)
    if not number:
        raise ValueError(f"no integer found in {value!r}")
    return int(number.group(0), 10)


def parse_x64lens_info(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Type:"):
            fields["class"] = line.split(":", 1)[1].strip()
        elif line.startswith("Endian:"):
            fields["endian"] = line.split(":", 1)[1].strip()
        elif line.startswith("Machine:"):
            fields["machine"] = line.split(":", 1)[1].strip()
        elif line.startswith("ELF Type:"):
            fields["elf_type"] = line.split(":", 1)[1].strip()
        elif line.startswith("Entry:"):
            fields["entry"] = parse_int(line)
        elif line.startswith("Program header offset:"):
            fields["phoff"] = parse_int(line)
        elif line.startswith("Program header entry size:"):
            fields["phentsize"] = parse_int(line)
        elif line.startswith("Program header count:"):
            fields["phnum"] = parse_int(line)
        elif line.startswith("Section header offset:"):
            fields["shoff"] = parse_int(line)
        elif line.startswith("Section header entry size:"):
            fields["shentsize"] = parse_int(line)
        elif line.startswith("Section header count:"):
            fields["shnum"] = parse_int(line)
        elif line.startswith("File size:"):
            fields["file_size"] = parse_int(line)
    return fields


def parse_x64lens_mitigations(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("PIE:"):
            fields["pie"] = line.split(":", 1)[1].strip()
        elif line.startswith("NX stack:"):
            fields["nx_stack"] = line.split(":", 1)[1].strip()
        elif line.startswith("RELRO:"):
            fields["relro"] = line.split(":", 1)[1].strip()
        elif line.startswith("RWX load segment:"):
            fields["rwx_load"] = line.split(":", 1)[1].strip()
        elif line.startswith("Dynamic linking:"):
            fields["dynamic"] = line.split(":", 1)[1].strip()
        elif line.startswith("Program header count:"):
            fields["phnum"] = parse_int(line)
        elif line.startswith("LOAD segments:"):
            fields["load_count"] = parse_int(line)
        elif line.startswith("Executable LOAD regions:"):
            fields["exec_load_count"] = parse_int(line)
    return fields


def parse_readelf_header(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Class:"):
            fields["class"] = line.split(":", 1)[1].strip()
        elif line.startswith("Data:"):
            data = line.split(":", 1)[1].strip().lower()
            fields["endian"] = "little" if "little" in data else "big" if "big" in data else data
        elif line.startswith("Type:"):
            token = line.split(":", 1)[1].strip().split()[0]
            fields["elf_type"] = f"ET_{token}"
        elif line.startswith("Machine:"):
            machine = line.split(":", 1)[1].strip()
            fields["machine"] = "x86_64" if "x86-64" in machine.lower() else machine
        elif line.startswith("Entry point address:"):
            fields["entry"] = parse_int(line)
        elif line.startswith("Start of program headers:"):
            fields["phoff"] = parse_int(line)
        elif line.startswith("Start of section headers:"):
            fields["shoff"] = parse_int(line)
        elif line.startswith("Size of program headers:"):
            fields["phentsize"] = parse_int(line)
        elif line.startswith("Number of program headers:"):
            fields["phnum"] = parse_int(line)
        elif line.startswith("Size of section headers:"):
            fields["shentsize"] = parse_int(line)
        elif line.startswith("Number of section headers:"):
            fields["shnum"] = parse_int(line)
    return fields


def parse_readelf_program_headers(text: str) -> dict[str, Any]:
    loads: list[dict[str, Any]] = []
    has_dynamic = False
    has_relro = False
    stack_flags: str | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("DYNAMIC"):
            has_dynamic = True
        elif stripped.startswith("GNU_RELRO"):
            has_relro = True
        load = LOAD_RE.match(raw)
        if load:
            flags = load.group("flags").replace(" ", "")
            loads.append({"flags": flags})
            continue
        stack = STACK_RE.match(raw)
        if stack:
            stack_flags = stack.group("flags").replace(" ", "")
    return {
        "load_count": len(loads),
        "exec_load_count": sum(1 for item in loads if "E" in item["flags"]),
        "rwx_load": any(all(bit in item["flags"] for bit in "RWE") for item in loads),
        "dynamic": has_dynamic,
        "relro_present": has_relro,
        "gnu_stack_flags": stack_flags,
    }


def assert_equal(case: str, mismatches: list[str], left: Any, right: Any, field: str) -> None:
    if left != right:
        mismatches.append(f"{case}: {field}: x64lens={left!r} readelf={right!r}")


def compare_target(binary: Path, target: Path, timeout: float) -> dict[str, Any]:
    case = str(target)
    result: dict[str, Any] = {"target": case, "ok": False, "mismatches": []}

    x_info = run([str(binary), "info", str(target)], timeout)
    x_mit = run([str(binary), "mitigations", str(target)], timeout)
    r_hdr = run(["readelf", "-h", str(target)], timeout)
    r_phdr = run(["readelf", "-W", "-l", str(target)], timeout)

    for name, proc in [("x64lens info", x_info), ("x64lens mitigations", x_mit), ("readelf -h", r_hdr), ("readelf -W -l", r_phdr)]:
        if proc.returncode != 0:
            result["mismatches"].append(f"{case}: {name} exited {proc.returncode}: {proc.stderr.strip()}")
            return result

    xh = parse_x64lens_info(x_info.stdout)
    xm = parse_x64lens_mitigations(x_mit.stdout)
    rh = parse_readelf_header(r_hdr.stdout)
    rp = parse_readelf_program_headers(r_phdr.stdout)
    result["x64lens_info"] = xh
    result["x64lens_mitigations"] = xm
    result["readelf_header"] = rh
    result["readelf_program_headers"] = rp

    mismatches: list[str] = result["mismatches"]
    for field in ["class", "endian", "machine", "elf_type", "entry", "phoff", "phentsize", "phnum", "shoff", "shentsize", "shnum"]:
        assert_equal(case, mismatches, xh.get(field), rh.get(field), field)
    assert_equal(case, mismatches, xh.get("file_size"), os.path.getsize(target), "file_size")
    assert_equal(case, mismatches, xm.get("phnum"), rh.get("phnum"), "mitigation phnum")
    assert_equal(case, mismatches, xm.get("load_count"), rp.get("load_count"), "LOAD count")
    assert_equal(case, mismatches, xm.get("exec_load_count"), rp.get("exec_load_count"), "executable LOAD count")

    expected_pie = "enabled" if rh.get("elf_type") == "ET_DYN" else "disabled"
    assert_equal(case, mismatches, xm.get("pie"), expected_pie, "PIE from ELF type")

    expected_dynamic = "yes" if rp.get("dynamic") else "no"
    assert_equal(case, mismatches, xm.get("dynamic"), expected_dynamic, "PT_DYNAMIC presence")

    expected_rwx = "yes" if rp.get("rwx_load") else "no"
    assert_equal(case, mismatches, xm.get("rwx_load"), expected_rwx, "RWX LOAD presence")

    stack_flags = rp.get("gnu_stack_flags")
    if stack_flags is None:
        expected_nx = "unknown"
    elif "E" in stack_flags:
        expected_nx = "disabled"
    else:
        expected_nx = "enabled"
    assert_equal(case, mismatches, xm.get("nx_stack"), expected_nx, "GNU_STACK NX state")

    relro = str(xm.get("relro", "")).lower()
    if rp.get("relro_present"):
        if relro in {"not found", "no", "none", "absent"}:
            mismatches.append(f"{case}: RELRO: readelf has GNU_RELRO but x64lens reported {xm.get('relro')!r}")
    else:
        if relro not in {"not found", "no", "none", "absent"}:
            mismatches.append(f"{case}: RELRO: readelf has no GNU_RELRO but x64lens reported {xm.get('relro')!r}")

    result["ok"] = not mismatches
    return result


def default_targets(root: Path) -> list[Path]:
    candidates = [
        root / "tests/bin/minimal_nopie",
        root / "tests/bin/minimal_pie_canary",
        root / "tests/bin/minimal_execstack",
        root / "tests/bin/gadgets",
        Path("/bin/ls"),
    ]
    return [path for path in candidates if path.exists() and path.is_file()]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="compare x64lens metadata and mitigation facts against readelf")
    parser.add_argument("--binary", type=Path, default=Path("./build/x64lens"))
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--results-dir", type=Path, default=Path("./tests/results/readelf-comparison"))
    parser.add_argument("targets", nargs="*", type=Path)
    args = parser.parse_args(argv)

    if not args.binary.is_file() or not os.access(args.binary, os.X_OK):
        print(f"readelf-comparison-smoke: error: binary is not executable: {args.binary}", file=sys.stderr)
        return 1
    if run(["readelf", "--version"], args.timeout).returncode != 0:
        print("readelf-comparison-smoke: error: readelf is not available", file=sys.stderr)
        return 127

    root = Path.cwd()
    targets = args.targets or default_targets(root)
    if not targets:
        print("readelf-comparison-smoke: error: no targets found", file=sys.stderr)
        return 1

    args.results_dir.mkdir(parents=True, exist_ok=True)
    results = [compare_target(args.binary, target, args.timeout) for target in targets]
    out = args.results_dir / "readelf-comparison-latest.json"
    out.write_text(json.dumps({"cases": results}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failures = [case for case in results if not case["ok"]]
    if failures:
        for case in failures:
            for mismatch in case["mismatches"]:
                print(f"readelf-comparison-smoke: error: {mismatch}", file=sys.stderr)
        print(f"readelf-comparison-smoke: failed cases={len(failures)} results={out}", file=sys.stderr)
        return 1

    print(f"readelf-comparison-smoke: ok cases={len(results)} results={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
