#!/usr/bin/env python3
"""Deterministic hostile-input smoke runner for x64lens.

The runner derives a bounded set of mutated ELF64 files from a controlled seed,
executes the command path that reaches each mutated field, and records the
result without retaining generated binaries by default. It is a regression
smoke test, not coverage-guided fuzzing and not a memory-safety proof.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import struct
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Sequence

SCRIPT_VERSION = "0.1.1"
ELF64_EHDR_SIZE = 64
ELF64_PHDR_SIZE = 56
ELF64_SHDR_SIZE = 64
PT_LOAD = 1
PF_X = 1
ROOT = Path(__file__).resolve().parents[1]
REPORT_VALIDATOR = ROOT / "tools" / "validate-json-report.py"


class HarnessError(RuntimeError):
    """Raised for invalid harness configuration or an unusable seed."""


@dataclass(frozen=True)
class MutationCase:
    case_id: str
    description: str
    command: tuple[str, ...]
    expected_exit: tuple[int, ...]
    mutate: Callable[[bytearray, "ElfSeed"], bytearray]
    input_class: str = "malformed"


@dataclass(frozen=True)
class ElfSeed:
    path: Path
    data: bytes
    sha256: str
    phoff: int
    phentsize: int
    phnum: int
    shoff: int
    shentsize: int
    shnum: int
    first_load_offset: int
    executable_load_offset: int


def u16(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def u64(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def put_u16(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", data, offset, value & 0xFFFF)


def put_u32(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<I", data, offset, value & 0xFFFFFFFF)


def put_u64(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<Q", data, offset, value & 0xFFFFFFFFFFFFFFFF)


def load_seed(path: Path) -> ElfSeed:
    data = path.read_bytes()
    if len(data) < ELF64_EHDR_SIZE:
        raise HarnessError(f"seed is smaller than an ELF64 header: {path}")
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise HarnessError(f"seed is not ELF64 little-endian: {path}")

    phoff = u64(data, 0x20)
    shoff = u64(data, 0x28)
    phentsize = u16(data, 0x36)
    phnum = u16(data, 0x38)
    shentsize = u16(data, 0x3A)
    shnum = u16(data, 0x3C)

    if phnum == 0 or phentsize != ELF64_PHDR_SIZE:
        raise HarnessError("seed must contain standard ELF64 program headers")
    if phoff > len(data) or phnum * phentsize > len(data) - phoff:
        raise HarnessError("seed program-header table is out of range")

    first_load = -1
    executable_load = -1
    for index in range(phnum):
        entry = phoff + index * phentsize
        if u32(data, entry) != PT_LOAD:
            continue
        if first_load < 0:
            first_load = entry
        if u32(data, entry + 4) & PF_X:
            executable_load = entry
            break

    if first_load < 0 or executable_load < 0:
        raise HarnessError("seed must contain an executable PT_LOAD segment")

    return ElfSeed(
        path=path,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        phoff=phoff,
        phentsize=phentsize,
        phnum=phnum,
        shoff=shoff,
        shentsize=shentsize,
        shnum=shnum,
        first_load_offset=first_load,
        executable_load_offset=executable_load,
    )


def copied(seed: ElfSeed) -> bytearray:
    return bytearray(seed.data)


def cases() -> list[MutationCase]:
    def truncate(length: int) -> Callable[[bytearray, ElfSeed], bytearray]:
        return lambda data, _seed: data[:length]

    def byte_at(offset: int, value: int) -> Callable[[bytearray, ElfSeed], bytearray]:
        def apply(data: bytearray, _seed: ElfSeed) -> bytearray:
            data[offset] = value
            return data
        return apply

    def word_at(offset: int, value: int) -> Callable[[bytearray, ElfSeed], bytearray]:
        def apply(data: bytearray, _seed: ElfSeed) -> bytearray:
            put_u16(data, offset, value)
            return data
        return apply

    def dword_at(offset: int, value: int) -> Callable[[bytearray, ElfSeed], bytearray]:
        def apply(data: bytearray, _seed: ElfSeed) -> bytearray:
            put_u32(data, offset, value)
            return data
        return apply

    def qword_at(offset: int, value: int) -> Callable[[bytearray, ElfSeed], bytearray]:
        def apply(data: bytearray, _seed: ElfSeed) -> bytearray:
            put_u64(data, offset, value)
            return data
        return apply

    def phdr_qword(relative: int, value: int) -> Callable[[bytearray, ElfSeed], bytearray]:
        def apply(data: bytearray, seed: ElfSeed) -> bytearray:
            put_u64(data, seed.executable_load_offset + relative, value)
            return data
        return apply

    def load_filesz_gt_memsz(data: bytearray, seed: ElfSeed) -> bytearray:
        put_u64(data, seed.executable_load_offset + 0x20, 0x1000)
        put_u64(data, seed.executable_load_offset + 0x28, 1)
        return data

    def load_range_past_eof(data: bytearray, seed: ElfSeed) -> bytearray:
        put_u64(data, seed.executable_load_offset + 0x08, len(data))
        put_u64(data, seed.executable_load_offset + 0x20, 1)
        put_u64(data, seed.executable_load_offset + 0x28, 1)
        return data

    def trailing_ret_imm_boundary(data: bytearray, seed: ElfSeed) -> bytearray:
        file_offset = u64(data, seed.executable_load_offset + 0x08)
        file_size = u64(data, seed.executable_load_offset + 0x20)
        if file_size == 0 or file_offset + file_size > len(data):
            raise HarnessError("executable PT_LOAD range is not file-backed")
        data[file_offset + file_size - 1] = 0xC2
        return data

    return [
        MutationCase("control_info", "unmodified seed metadata", ("info",), (0,), lambda d, _s: d, "valid_control"),
        MutationCase("control_analyze_json", "unmodified integrated JSON path", ("analyze", "--format", "json", "--max-depth", "4"), (0,), lambda d, _s: d, "valid_control"),
        MutationCase("truncated_1", "one-byte file", ("info",), (5,), truncate(1)),
        MutationCase("truncated_3", "ELF magic truncated before four bytes", ("info",), (5,), truncate(3)),
        MutationCase("truncated_8", "ELF identity present but header truncated", ("info",), (5,), truncate(8)),
        MutationCase("truncated_63", "one byte short of ELF64 header", ("info",), (5,), truncate(63)),
        MutationCase("bad_magic", "first ELF magic byte cleared", ("info",), (4,), byte_at(0, 0)),
        MutationCase("wrong_class", "ELF class changed to ELF32", ("info",), (4,), byte_at(4, 1)),
        MutationCase("wrong_endian", "ELF data encoding changed to big-endian", ("info",), (4,), byte_at(5, 2)),
        MutationCase("bad_ident_version", "e_ident version cleared", ("info",), (5,), byte_at(6, 0)),
        MutationCase("wrong_machine", "machine changed away from x86_64", ("info",), (4,), word_at(0x12, 0)),
        MutationCase("bad_header_version", "ELF header version cleared", ("info",), (5,), dword_at(0x14, 0)),
        MutationCase("bad_ehsize", "ELF header size cleared", ("info",), (5,), word_at(0x34, 0)),
        MutationCase("phoff_zero", "program-header offset cleared while count remains nonzero", ("info",), (5,), qword_at(0x20, 0)),
        MutationCase("phoff_past_eof", "program-header table starts beyond EOF", ("info",), (5,), lambda d, _s: qword_at(0x20, len(d) + 0x1000)(d, _s)),
        MutationCase("phoff_end_wrap", "program-header table end overflows uint64", ("info",), (5,), qword_at(0x20, 0xFFFFFFFFFFFFFFF0)),
        MutationCase("phentsize_zero", "program-header entry size cleared", ("info",), (5,), word_at(0x36, 0)),
        MutationCase("phentsize_short", "program-header entry size is one byte short", ("info",), (5,), word_at(0x36, ELF64_PHDR_SIZE - 1)),
        MutationCase("phnum_oversized", "program-header count expands table beyond EOF", ("info",), (5,), word_at(0x38, 0xFFFF)),
        MutationCase("shoff_zero", "section-header offset cleared while count remains nonzero", ("info",), (5,), qword_at(0x28, 0)),
        MutationCase("shoff_past_eof", "section-header table starts beyond EOF", ("info",), (5,), lambda d, _s: qword_at(0x28, len(d) + 0x1000)(d, _s)),
        MutationCase("shoff_end_wrap", "section-header table end overflows uint64", ("info",), (5,), qword_at(0x28, 0xFFFFFFFFFFFFFFF0)),
        MutationCase("shentsize_zero", "section-header entry size cleared", ("info",), (5,), word_at(0x3A, 0)),
        MutationCase("shentsize_short", "section-header entry size is one byte short", ("info",), (5,), word_at(0x3A, ELF64_SHDR_SIZE - 1)),
        MutationCase("shentsize_long", "section-header entry size is one byte long", ("info",), (5,), word_at(0x3A, ELF64_SHDR_SIZE + 1)),
        MutationCase("shnum_oversized", "section-header count expands table beyond EOF", ("info",), (5,), word_at(0x3C, 0xFFFF)),
        MutationCase("load_filesz_gt_memsz", "executable PT_LOAD file size exceeds memory size", ("analyze", "--format", "json", "--max-depth", "4"), (5,), load_filesz_gt_memsz),
        MutationCase("load_offset_max", "executable PT_LOAD file offset is UINT64_MAX", ("analyze", "--format", "json", "--max-depth", "4"), (5,), phdr_qword(0x08, 0xFFFFFFFFFFFFFFFF)),
        MutationCase("load_filesz_max", "executable PT_LOAD file size is UINT64_MAX", ("analyze", "--format", "json", "--max-depth", "4"), (5,), phdr_qword(0x20, 0xFFFFFFFFFFFFFFFF)),
        MutationCase("load_range_past_eof", "one-byte executable PT_LOAD starts at EOF", ("analyze", "--format", "json", "--max-depth", "4"), (5,), load_range_past_eof),
        MutationCase("trailing_ret_imm_boundary", "0xc2 terminator byte at final executable-region byte", ("analyze", "--format", "json", "--max-depth", "4"), (0,), trailing_ret_imm_boundary, "valid_boundary"),
    ]


def signal_name(returncode: int) -> str:
    if returncode >= 0:
        return "none"
    number = -returncode
    try:
        return signal.Signals(number).name
    except ValueError:
        return f"SIG{number}"


def validate_successful_json(stdout: bytes, command: str, case_id: str) -> None:
    """Require successful JSON controls to satisfy the current report contract."""
    with tempfile.TemporaryDirectory(prefix=f"x64lens-malformed-{case_id}-") as temp:
        report_path = Path(temp) / f"{command}.json"
        report_path.write_bytes(stdout)
        result = subprocess.run(
            [
                sys.executable,
                str(REPORT_VALIDATOR),
                "--mode",
                "system",
                "--require-schema",
                "0.2.0",
                "--expected-command",
                command,
                "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",
                str(report_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if result.returncode != 0:
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
        raise HarnessError(
            f"{case_id}: successful {command} JSON failed canonical validation: {diagnostic}"
        )


def run_case(
    binary: Path,
    case: MutationCase,
    input_path: Path,
    timeout_seconds: float,
) -> dict[str, object]:
    command = [str(binary), *case.command, str(input_path)]
    started = time.perf_counter_ns()
    timed_out = False
    stdout = b""
    stderr = b""
    returncode = 124

    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            start_new_session=True,
        )
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""

    elapsed_ns = time.perf_counter_ns() - started
    signaled = returncode < 0
    if (
        not timed_out
        and not signaled
        and returncode == 0
        and "--format" in case.command
        and "json" in case.command
    ):
        validate_successful_json(stdout, case.command[0], case.case_id)
    stdout_policy_ok = case.input_class != "malformed" or len(stdout) == 0
    expected = (
        (not timed_out)
        and (not signaled)
        and returncode in case.expected_exit
        and stdout_policy_ok
    )

    return {
        "case_id": case.case_id,
        "input_class": case.input_class,
        "mutation_description": case.description,
        "command": " ".join([binary.name, *case.command, f"<{case.case_id}>"]),
        "expected_exit": ",".join(str(value) for value in case.expected_exit),
        "exit_code": returncode if returncode >= 0 else 128 + (-returncode),
        "signal": signal_name(returncode),
        "timeout": "yes" if timed_out else "no",
        "wall_time_ns": elapsed_ns,
        "stdout_size": len(stdout),
        "stderr_size": len(stderr),
        "result": "ok" if expected else "fail",
        "stderr_preview": stderr.decode("utf-8", errors="replace").replace("\n", " ")[:160],
    }


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default="./build/x64lens", type=Path)
    parser.add_argument("--seed", default="./tests/bin/minimal_nopie", type=Path)
    parser.add_argument("--timeout", default=2.0, type=float)
    parser.add_argument("--results-dir", default="./tests/results/malformed", type=Path)
    parser.add_argument("--keep-mutations", action="store_true")
    parser.add_argument("--work-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    binary = args.binary.resolve()
    seed_path = args.seed.resolve()
    results_dir = args.results_dir.resolve()

    if args.timeout <= 0:
        raise HarnessError("timeout must be greater than zero")
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise HarnessError(f"x64lens executable not found or not executable: {binary}")
    if not seed_path.is_file():
        raise HarnessError(f"seed not found: {seed_path}")

    seed = load_seed(seed_path)
    results_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    tsv_path = results_dir / f"malformed-smoke-{stamp}.tsv"
    meta_path = results_dir / f"malformed-smoke-{stamp}.meta"

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if args.work_dir is not None:
        work_dir = args.work_dir.resolve()
        work_dir.mkdir(parents=True, exist_ok=True)
    elif args.keep_mutations:
        work_dir = (results_dir / f"malformed-smoke-{stamp}-cases").resolve()
        work_dir.mkdir(parents=True, exist_ok=True)
    else:
        temporary = tempfile.TemporaryDirectory(prefix="x64lens-malformed-smoke.")
        work_dir = Path(temporary.name)

    rows: list[dict[str, object]] = []
    try:
        for case in cases():
            data = case.mutate(copied(seed), seed)
            input_path = work_dir / f"{case.case_id}.elf"
            input_path.write_bytes(data)
            rows.append(run_case(binary, case, input_path, args.timeout))
    finally:
        if temporary is not None:
            temporary.cleanup()

    fieldnames = [
        "case_id",
        "input_class",
        "seed_hash",
        "mutation_description",
        "command",
        "expected_exit",
        "exit_code",
        "signal",
        "timeout",
        "wall_time_ns",
        "stdout_size",
        "stderr_size",
        "result",
        "stderr_preview",
    ]
    with tsv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "seed_hash": seed.sha256})

    version = subprocess.run(
        [str(binary), "version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
        timeout=args.timeout,
    ).stdout.strip()
    metadata = {
        "schema_version": "0.1.0",
        "harness": "x64lens deterministic malformed-input smoke",
        "harness_version": SCRIPT_VERSION,
        "timestamp_utc": stamp,
        "binary": str(binary),
        "tool_version_output": version,
        "seed": str(seed_path),
        "seed_sha256": seed.sha256,
        "timeout_seconds": args.timeout,
        "case_count": len(rows),
        "host": platform.platform(),
        "python": platform.python_version(),
        "mutations_retained": bool(args.keep_mutations or args.work_dir),
    }
    meta_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failures = [row for row in rows if row["result"] != "ok"]
    if failures:
        print(f"malformed-smoke: failed cases={len(failures)} total={len(rows)}", file=sys.stderr)
        for row in failures:
            print(
                "  "
                f"{row['case_id']}: expected={row['expected_exit']} "
                f"exit={row['exit_code']} signal={row['signal']} "
                f"timeout={row['timeout']} stderr={row['stderr_preview']}",
                file=sys.stderr,
            )
        print(f"  results: {tsv_path}", file=sys.stderr)
        print(f"  metadata: {meta_path}", file=sys.stderr)
        return 1

    malformed_count = sum(1 for row in rows if row["input_class"] == "malformed")
    print("malformed-smoke: ok")
    print(f"  seed: {seed_path}")
    print(f"  seed_sha256: {seed.sha256}")
    print(f"  cases: {len(rows)}")
    print(f"  malformed cases: {malformed_count}")
    print(f"  timeout_seconds: {args.timeout:g}")
    print(f"  results: {tsv_path}")
    print(f"  metadata: {meta_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except HarnessError as exc:
        print(f"malformed-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
