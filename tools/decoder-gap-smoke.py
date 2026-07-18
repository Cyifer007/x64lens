#!/usr/bin/env python3
"""Measure x64lens byte-scanner/exact-suffix gaps against GNU objdump.

This is a development/research evidence generator, not a runtime decoder and not
an exploitability oracle. It preserves x64lens JSON, objdump disassembly,
commands, versions, hashes, timing/RSS smoke metrics, and categorized
reconciliation facts under an ignored results directory.
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import math
import os
import platform
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate-json-report.py"
TIME_BIN = Path("/usr/bin/time")
HEX_BYTE_RE = re.compile(r"^[0-9a-fA-F]{2}$")
HEX_ADDRESS_RE = re.compile(r"^[0-9a-fA-F]+$")
OBJDUMP_PREFIXES = {
    "addr16", "addr32", "addr64", "bnd", "cs", "data16", "data32", "data64",
    "ds", "es", "fs", "gs", "lock", "notrack", "rep", "repe", "repne",
    "repnz", "repz", "ss",
}
REX_PREFIX_RE = re.compile(r"^rex(?:\.[wrxb]+)?$")
RETURN_MNEMONICS = {"ret", "retl", "retn", "retq", "retw"}
FAR_RETURN_MNEMONICS = {"lret", "lretl", "lretq", "lretw", "retf", "retfl", "retfq", "retfw"}
SAFE_LABEL_RE = re.compile(r"[^A-Za-z0-9_.-]+")
SUMMARY_FIELDS = [
    "target",
    "target_sha256",
    "target_size",
    "max_depth",
    "x64lens_wall_time_ns",
    "x64lens_max_rss_kib",
    "objdump_wall_time_ns",
    "objdump_max_rss_kib",
    "raw_candidate_count",
    "x64lens_unique_terminator_count",
    "x64lens_duplicate_terminator_count",
    "exact_pattern_count",
    "x64lens_duplicate_exact_evidence_count",
    "semantic_candidate_count",
    "unknown_candidate_count",
    "scored_candidate_count",
    "objdump_instruction_count",
    "objdump_parse_diagnostic_count",
    "objdump_return_terminator_count",
    "objdump_duplicate_return_terminator_count",
    "raw_terminator_intersection_count",
    "x64lens_raw_not_objdump_count",
    "objdump_terminator_not_x64lens_count",
    "x64lens_exact_candidate_count",
    "x64lens_exact_boundary_match_count",
    "x64lens_exact_boundary_disagreement_count",
    "x64lens_candidate_byte_mismatch_count",
    "objdump_canonical_sequence_count",
    "objdump_duplicate_canonical_sequence_count",
    "objdump_supported_sequence_count",
    "objdump_supported_selected_count",
    "objdump_supported_unselected_count",
    "objdump_unsupported_sequence_count",
]


@dataclass(frozen=True)
class Instruction:
    address: int
    raw: bytes
    mnemonic: str
    operands: str
    section: str
    prefixes: tuple[str, ...] = ()

    @property
    def end(self) -> int:
        return self.address + len(self.raw)

    @property
    def text(self) -> str:
        return " ".join((*self.prefixes, self.mnemonic, self.operands)).strip()


@dataclass(frozen=True)
class ObjdumpDiagnostic:
    line_number: int
    reason: str
    line: str


@dataclass(frozen=True)
class TargetSnapshot:
    requested_path: str
    resolved_path: str
    snapshot_path: Path
    sha256: str
    size: int
    source_device: int
    source_inode: int
    source_mtime_ns: int
    source_ctime_ns: int


class CampaignInterrupted(BaseException):
    """Raised by SIGINT/SIGTERM handlers so publication can roll back safely."""

    def __init__(self, signum: int):
        super().__init__(f"campaign interrupted by signal {signum}")
        self.signum = signum


@dataclass(frozen=True)
class CanonicalSequence:
    start: int
    terminator: int
    raw: bytes
    instructions: tuple[str, ...]
    section: str

    @property
    def key(self) -> tuple[int, int, str]:
        return (self.start, self.terminator, self.raw.hex())


@dataclass(frozen=True)
class MeasuredCommand:
    command: list[str]
    command_shell: str
    working_directory: str
    measurement_command: list[str]
    measurement_command_shell: str
    exit_code: int
    wall_time_ns: int
    user_seconds: float | None
    system_seconds: float | None
    max_rss_kib: int | None
    stdout_path: str
    stderr_path: str
    metrics_path: str


def normalize_objdump_token(token: str) -> str:
    """Normalize one GNU objdump mnemonic/prefix token for comparisons."""

    return token.casefold().rstrip(":")


def is_objdump_prefix(token: str) -> bool:
    """Return whether one normalized token is an x86 instruction prefix."""

    normalized = normalize_objdump_token(token)
    if normalized in OBJDUMP_PREFIXES:
        return True
    if not REX_PREFIX_RE.fullmatch(normalized):
        return False
    suffix = normalized.partition(".")[2]
    return not suffix or len(set(suffix)) == len(suffix)


@contextlib.contextmanager
def block_campaign_signals() -> Iterable[None]:
    """Block handled termination signals while rollback or reaping is in progress."""

    if not hasattr(signal, "pthread_sigmask"):
        yield
        return
    blocked = {signal.SIGINT, signal.SIGTERM}
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def kill_and_reap_process_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate a measured process session and reap its direct leader."""

    with block_campaign_signals():
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_target(requested: Path, snapshots_dir: Path, index: int) -> TargetSnapshot:
    """Copy one stable target image and bind all later evidence to that image."""

    resolved = requested.resolve(strict=True)
    if not resolved.is_file():
        raise RuntimeError(f"target is not a regular file: {requested}")
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    basename = SAFE_LABEL_RE.sub("_", resolved.name) or "target"
    destination = snapshots_dir / f"{index:02d}-{basename}.bin"
    digest = hashlib.sha256()

    with resolved.open("rb", buffering=0) as source, destination.open("xb", buffering=0) as output:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"target is not a regular file: {requested}")
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            digest.update(chunk)
        output.flush()
        os.fsync(output.fileno())
        after = os.fstat(source.fileno())
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
            raise RuntimeError(f"target changed while its immutable snapshot was created: {requested}")
        source.seek(0)
        verification = hashlib.sha256()
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            verification.update(chunk)
        if verification.hexdigest() != digest.hexdigest():
            raise RuntimeError(f"target bytes changed while its immutable snapshot was created: {requested}")

    snapshot_digest = sha256_file(destination)
    if snapshot_digest != digest.hexdigest() or destination.stat().st_size != before.st_size:
        raise RuntimeError(f"immutable target snapshot verification failed: {requested}")
    destination.chmod(0o444)
    return TargetSnapshot(
        requested_path=str(requested),
        resolved_path=str(resolved),
        snapshot_path=destination,
        sha256=snapshot_digest,
        size=before.st_size,
        source_device=before.st_dev,
        source_inode=before.st_ino,
        source_mtime_ns=before.st_mtime_ns,
        source_ctime_ns=before.st_ctime_ns,
    )


def first_line(command: list[str], timeout: float) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
    if result.returncode != 0:
        detail = (result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}")
        raise RuntimeError(f"identity command failed: {shlex.join(command)}: {detail}")
    text = result.stdout.strip() or result.stderr.strip()
    if not text:
        raise RuntimeError(f"identity command produced no output: {shlex.join(command)}")
    return text.splitlines()[0]


def parse_time_metrics(path: Path) -> tuple[float | None, float | None, int | None]:
    try:
        fields = path.read_text(encoding="utf-8").strip().split("\t")
        if len(fields) != 3:
            return None, None, None
        user_seconds = float(fields[0])
        system_seconds = float(fields[1])
        max_rss_kib = int(fields[2])
        if (
            not math.isfinite(user_seconds)
            or not math.isfinite(system_seconds)
            or user_seconds < 0
            or system_seconds < 0
            or max_rss_kib < 0
        ):
            return None, None, None
        return user_seconds, system_seconds, max_rss_kib
    except (OSError, ValueError):
        return None, None, None


def run_measured(
    command: list[str],
    stdout_path: Path,
    stderr_path: Path,
    timeout: float,
    artifact_root: Path,
) -> MeasuredCommand:
    metrics_path = stdout_path.with_suffix(stdout_path.suffix + ".time")
    wrapped = [
        str(TIME_BIN),
        "-f",
        "%U\t%S\t%M",
        "-o",
        metrics_path.name,
        "--",
        *command,
    ]
    started = time.monotonic_ns()
    with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
        process = subprocess.Popen(
            wrapped,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
            cwd=artifact_root,
        )
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            kill_and_reap_process_group(process)
            raise RuntimeError(f"command timed out after {timeout}s: {shlex.join(command)}") from exc
        except BaseException:
            kill_and_reap_process_group(process)
            raise
    wall_time_ns = time.monotonic_ns() - started
    user_seconds, system_seconds, max_rss_kib = parse_time_metrics(metrics_path)
    if user_seconds is None or system_seconds is None or max_rss_kib is None:
        raise RuntimeError(f"GNU time did not produce valid metrics: {shlex.join(command)}")
    return MeasuredCommand(
        command=command,
        command_shell=shlex.join(command),
        working_directory=".",
        measurement_command=wrapped,
        measurement_command_shell=shlex.join(wrapped),
        exit_code=exit_code,
        wall_time_ns=wall_time_ns,
        user_seconds=user_seconds,
        system_seconds=system_seconds,
        max_rss_kib=max_rss_kib,
        stdout_path=stdout_path.relative_to(artifact_root).as_posix(),
        stderr_path=stderr_path.relative_to(artifact_root).as_posix(),
        metrics_path=metrics_path.relative_to(artifact_root).as_posix(),
    )


def parse_objdump_with_diagnostics(text: str) -> tuple[list[Instruction], list[ObjdumpDiagnostic]]:
    instructions: list[Instruction] = []
    diagnostics: list[ObjdumpDiagnostic] = []
    section = "unknown"
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("Disassembly of section ") and stripped.endswith(":"):
            section = stripped[len("Disassembly of section ") : -1]
            continue
        if ":" not in line:
            continue
        address_text, remainder = line.split(":", 1)
        address_text = address_text.strip()
        if not HEX_ADDRESS_RE.fullmatch(address_text):
            continue
        tokens = remainder.strip().split()
        byte_tokens: list[str] = []
        while tokens and HEX_BYTE_RE.fullmatch(tokens[0]):
            byte_tokens.append(tokens.pop(0))
        if not byte_tokens:
            if tokens:
                diagnostics.append(ObjdumpDiagnostic(line_number, "address row lacks instruction bytes", line))
            continue
        if not tokens:
            diagnostics.append(ObjdumpDiagnostic(line_number, "byte row lacks a mnemonic", line))
            continue

        prefixes: list[str] = []
        while tokens and is_objdump_prefix(tokens[0]):
            prefixes.append(normalize_objdump_token(tokens.pop(0)))
        if not tokens:
            diagnostics.append(ObjdumpDiagnostic(line_number, "prefix-only byte row lacks a mnemonic", line))
            continue
        mnemonic = normalize_objdump_token(tokens.pop(0))
        operands = " ".join(tokens)
        try:
            raw = bytes.fromhex("".join(byte_tokens))
        except ValueError:
            diagnostics.append(ObjdumpDiagnostic(line_number, "invalid instruction bytes", line))
            continue
        instructions.append(
            Instruction(
                address=int(address_text, 16),
                raw=raw,
                mnemonic=mnemonic,
                operands=operands,
                section=section,
                prefixes=tuple(prefixes),
            )
        )
    return instructions, diagnostics


def parse_objdump(text: str) -> list[Instruction]:
    return parse_objdump_with_diagnostics(text)[0]


def is_return(instruction: Instruction) -> bool:
    return instruction.mnemonic in RETURN_MNEMONICS


def is_predecessor_barrier(instruction: Instruction) -> bool:
    mnemonic = instruction.mnemonic
    if is_return(instruction) or mnemonic in FAR_RETURN_MNEMONICS:
        return True
    if mnemonic.startswith(("jmp", "call", "loop", "iret")) or mnemonic.startswith("j"):
        return True
    if mnemonic.startswith(".") or mnemonic in {"(bad)", "bad"}:
        return True
    return mnemonic in {
        "int", "int1", "int3", "into", "sysenter", "sysexit", "ud0", "ud1", "ud2",
        "hlt", "rsm", "xbegin", "vmcall", "vmlaunch", "vmresume", "vmrun",
    }


def contiguous_runs(instructions: Iterable[Instruction]) -> list[list[Instruction]]:
    runs: list[list[Instruction]] = []
    current: list[Instruction] = []
    for instruction in instructions:
        if (
            current
            and instruction.section == current[-1].section
            and instruction.address == current[-1].end
        ):
            current.append(instruction)
        else:
            if current:
                runs.append(current)
            current = [instruction]
    if current:
        runs.append(current)
    return runs


def build_canonical_sequences(instructions: list[Instruction], max_depth: int) -> list[CanonicalSequence]:
    sequences: list[CanonicalSequence] = []
    for run in contiguous_runs(instructions):
        for index, terminator in enumerate(run):
            if not is_return(terminator):
                continue
            selected = [terminator]
            sequences.append(
                CanonicalSequence(
                    start=terminator.address,
                    terminator=terminator.address,
                    raw=terminator.raw,
                    instructions=(terminator.text,),
                    section=terminator.section,
                )
            )
            predecessor_bytes = 0
            for predecessor in reversed(run[:index]):
                if is_predecessor_barrier(predecessor):
                    break
                if predecessor_bytes + len(predecessor.raw) > max_depth:
                    break
                predecessor_bytes += len(predecessor.raw)
                selected.insert(0, predecessor)
                sequences.append(
                    CanonicalSequence(
                        start=selected[0].address,
                        terminator=terminator.address,
                        raw=b"".join(item.raw for item in selected),
                        instructions=tuple(item.text for item in selected),
                        section=terminator.section,
                    )
                )
    return sequences


LOW_REGS = ["rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi"]
HIGH_REGS = ["r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]


def supported_pattern(raw: bytes) -> str | None:
    if raw == b"\xc3":
        return "ret"
    if len(raw) == 3 and raw[0] == 0xC2:
        return "ret imm16"
    if len(raw) == 2 and 0x58 <= raw[0] <= 0x5F and raw[1] == 0xC3:
        return f"pop {LOW_REGS[raw[0] - 0x58]}; ret"
    if len(raw) == 3 and raw[0] == 0x41 and 0x58 <= raw[1] <= 0x5F and raw[2] == 0xC3:
        return f"pop {HIGH_REGS[raw[1] - 0x58]}; ret"
    if raw == b"\xc9\xc3":
        return "leave; ret"
    if raw == b"\x0f\x05\xc3":
        return "syscall; ret"
    return None


def int_hex(value: Any, field: str) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise RuntimeError(f"{field} must be a hexadecimal string")
    try:
        return int(value, 16)
    except ValueError as exc:
        raise RuntimeError(f"{field} is not hexadecimal: {value!r}") from exc


def target_label(target: Path, digest: str, index: int) -> str:
    basename = SAFE_LABEL_RE.sub("_", target.name) or "target"
    return f"{index:02d}-{basename}-{digest[:12]}"


def sample_sequence(sequence: CanonicalSequence) -> dict[str, Any]:
    return {
        "start": f"0x{sequence.start:016x}",
        "terminator": f"0x{sequence.terminator:016x}",
        "bytes": sequence.raw.hex(),
        "instructions": list(sequence.instructions),
        "section": sequence.section,
        "supported_pattern": supported_pattern(sequence.raw),
    }


def compare_target(
    *,
    binary: Path,
    objdump_binary: Path,
    source_target: Path,
    analyzed_target: Path,
    target_identity: dict[str, Any],
    target_dir: Path,
    max_depth: int,
    timeout: float,
    sample_limit: int,
    fixture_mode: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    target_bytes = analyzed_target.read_bytes()
    target_digest = hashlib.sha256(target_bytes).hexdigest()
    if target_digest != target_identity["sha256"] or len(target_bytes) != target_identity["size"]:
        raise RuntimeError(f"immutable target snapshot identity mismatch: {source_target}")
    analyzed_argument = os.path.relpath(analyzed_target, target_dir)

    report_path = target_dir / "x64lens.json"
    x_stderr = target_dir / "x64lens.stderr"
    x_measurement = run_measured(
        [str(binary), "gadgets", "--format", "json", "--max-depth", str(max_depth), analyzed_argument],
        report_path,
        x_stderr,
        timeout,
        target_dir,
    )
    if x_measurement.exit_code != 0:
        raise RuntimeError(
            f"x64lens failed for {source_target} with exit {x_measurement.exit_code}: "
            f"{x_stderr.read_text(encoding='utf-8', errors='replace').strip()}"
        )

    validator_command = [
        sys.executable,
        str(VALIDATOR),
        "--mode",
        "fixture" if fixture_mode else "system",
        "--require-schema",
        "0.2.0",
        "--expected-command",
        "gadgets",
        "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory", "--require-sprint10-architectural-effects",
        report_path.name,
    ]
    validator = subprocess.run(
        validator_command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        cwd=target_dir,
    )
    validator_stdout = target_dir / "validator.stdout"
    validator_stderr = target_dir / "validator.stderr"
    validator_stdout.write_text(validator.stdout, encoding="utf-8")
    validator_stderr.write_text(validator.stderr, encoding="utf-8")
    if validator.returncode != 0:
        raise RuntimeError(f"x64lens report validation failed for {source_target}: {validator.stderr.strip()}")

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot parse x64lens report for {source_target}: {exc}") from exc

    objdump_path = target_dir / "objdump.txt"
    objdump_stderr = target_dir / "objdump.stderr"
    objdump_measurement = run_measured(
        [str(objdump_binary), "-d", "-w", "-Mintel", analyzed_argument],
        objdump_path,
        objdump_stderr,
        timeout,
        target_dir,
    )
    if objdump_measurement.exit_code != 0:
        raise RuntimeError(
            f"objdump failed for {source_target} with exit {objdump_measurement.exit_code}: "
            f"{objdump_stderr.read_text(encoding='utf-8', errors='replace').strip()}"
        )

    instructions, parse_diagnostics = parse_objdump_with_diagnostics(
        objdump_path.read_text(encoding="utf-8", errors="replace")
    )
    sequences = build_canonical_sequences(instructions, max_depth)
    sequence_by_key = {sequence.key: sequence for sequence in sequences}
    duplicate_canonical_sequences = len(sequences) - len(sequence_by_key)
    sequences_by_pair: dict[tuple[int, int], list[CanonicalSequence]] = {}
    for sequence in sequences:
        sequences_by_pair.setdefault((sequence.start, sequence.terminator), []).append(sequence)

    return_instructions = [instruction for instruction in instructions if is_return(instruction)]
    canonical_terminators = {instruction.address for instruction in return_instructions}
    duplicate_return_terminators = len(return_instructions) - len(canonical_terminators)
    gadgets = report.get("gadgets")
    if not isinstance(gadgets, list):
        raise RuntimeError("x64lens report gadgets field is not an array")

    x_terminator_occurrences: list[int] = []
    selected_exact_keys: set[tuple[int, int, str]] = set()
    duplicate_exact_evidence = 0
    exact_matches: list[dict[str, Any]] = []
    exact_disagreements: list[dict[str, Any]] = []
    byte_mismatches: list[dict[str, Any]] = []

    for index, gadget in enumerate(gadgets):
        if not isinstance(gadget, dict):
            raise RuntimeError(f"gadgets[{index}] is not an object")
        raw_hex = gadget.get("bytes")
        if not isinstance(raw_hex, str) or len(raw_hex) % 2:
            raise RuntimeError(f"gadgets[{index}].bytes is not an even-length hex string")
        try:
            raw = bytes.fromhex(raw_hex)
        except ValueError as exc:
            raise RuntimeError(f"gadgets[{index}].bytes is not hexadecimal") from exc

        terminator = gadget.get("terminator")
        terminator_length = 1 if terminator == "ret" else 3 if terminator == "ret imm16" else None
        if terminator_length is None:
            raise RuntimeError(f"gadgets[{index}].terminator is unsupported: {terminator!r}")
        term_va = int_hex(gadget.get("va"), f"gadgets[{index}].va")
        term_offset = int_hex(gadget.get("file_offset"), f"gadgets[{index}].file_offset")
        x_terminator_occurrences.append(term_va)

        candidate_start_offset = term_offset - (len(raw) - terminator_length)
        candidate_start_va = term_va - (len(raw) - terminator_length)
        if candidate_start_offset < 0:
            raise RuntimeError(f"gadgets[{index}] candidate start underflows")
        observed = target_bytes[candidate_start_offset : candidate_start_offset + len(raw)]
        if observed != raw:
            byte_mismatches.append(
                {
                    "index": index,
                    "candidate_start_offset": f"0x{candidate_start_offset:016x}",
                    "expected": raw.hex(),
                    "observed": observed.hex(),
                }
            )

        evidence = gadget.get("evidence")
        if not isinstance(evidence, dict) or not evidence.get("exact_suffix"):
            continue
        suffix_offset = evidence.get("matched_suffix_offset")
        suffix_length = evidence.get("matched_suffix_length")
        if not isinstance(suffix_offset, int) or not isinstance(suffix_length, int):
            raise RuntimeError(f"gadgets[{index}] exact evidence lacks numeric suffix range")
        if suffix_offset < 0 or suffix_length <= 0 or suffix_offset + suffix_length > len(raw):
            raise RuntimeError(f"gadgets[{index}] exact suffix range is out of bounds")
        if suffix_offset + suffix_length != len(raw):
            raise RuntimeError(f"gadgets[{index}] exact suffix does not end at the terminator")
        suffix = raw[suffix_offset : suffix_offset + suffix_length]
        suffix_start = candidate_start_va + suffix_offset
        key = (suffix_start, term_va, suffix.hex())
        derived_pattern = supported_pattern(suffix)
        if derived_pattern != gadget.get("pattern"):
            raise RuntimeError(
                f"gadgets[{index}] pattern catalog mismatch: report={gadget.get('pattern')!r} "
                f"derived={derived_pattern!r} bytes={suffix.hex()}"
            )
        selected_exact = {
            "index": index,
            "start": f"0x{suffix_start:016x}",
            "terminator": f"0x{term_va:016x}",
            "bytes": suffix.hex(),
            "pattern": gadget.get("pattern"),
            "semantic_class": gadget.get("semantic_class"),
        }
        if key in selected_exact_keys:
            duplicate_exact_evidence += 1
        selected_exact_keys.add(key)
        if key in sequence_by_key:
            exact_matches.append(selected_exact)
        else:
            pair_sequences = sequences_by_pair.get((suffix_start, term_va), [])
            exact_disagreements.append(
                {
                    **selected_exact,
                    "objdump_sequences_same_boundary": [sample_sequence(item) for item in pair_sequences[:sample_limit]],
                }
            )

    supported_sequences = {sequence.key: sequence for sequence in sequences if supported_pattern(sequence.raw)}
    selected_keys = selected_exact_keys
    supported_selected = set(supported_sequences) & selected_keys
    supported_unselected = [
        supported_sequences[key] for key in sorted(set(supported_sequences) - selected_keys)
    ]
    unsupported_sequences = [sequence for sequence in sequences if supported_pattern(sequence.raw) is None]

    x_terminators = set(x_terminator_occurrences)
    duplicate_x_terminators = len(x_terminator_occurrences) - len(x_terminators)
    x_raw_not_objdump = sorted(x_terminators - canonical_terminators)
    objdump_not_x_raw = sorted(canonical_terminators - x_terminators)
    counts = report.get("counts", {})
    expected_report_counts = {
        "raw_candidate_count": len(gadgets),
        "exact_pattern_count": len(exact_matches) + len(exact_disagreements),
    }
    for field, expected_value in expected_report_counts.items():
        if counts.get(field) != expected_value:
            raise RuntimeError(
                f"x64lens report {field} disagrees with candidate records: "
                f"report={counts.get(field)!r} records={expected_value}"
            )
    metrics: dict[str, Any] = {
        "target": str(source_target),
        "target_sha256": target_digest,
        "target_size": len(target_bytes),
        "max_depth": max_depth,
        "x64lens_wall_time_ns": x_measurement.wall_time_ns,
        "x64lens_max_rss_kib": x_measurement.max_rss_kib,
        "objdump_wall_time_ns": objdump_measurement.wall_time_ns,
        "objdump_max_rss_kib": objdump_measurement.max_rss_kib,
        "raw_candidate_count": counts.get("raw_candidate_count"),
        "x64lens_unique_terminator_count": len(x_terminators),
        "x64lens_duplicate_terminator_count": duplicate_x_terminators,
        "exact_pattern_count": counts.get("exact_pattern_count"),
        "x64lens_duplicate_exact_evidence_count": duplicate_exact_evidence,
        "semantic_candidate_count": counts.get("semantic_candidate_count"),
        "unknown_candidate_count": counts.get("unknown_candidate_count"),
        "scored_candidate_count": counts.get("scored_candidate_count"),
        "objdump_instruction_count": len(instructions),
        "objdump_parse_diagnostic_count": len(parse_diagnostics),
        "objdump_return_terminator_count": len(canonical_terminators),
        "objdump_duplicate_return_terminator_count": duplicate_return_terminators,
        "raw_terminator_intersection_count": len(x_terminators & canonical_terminators),
        "x64lens_raw_not_objdump_count": len(x_raw_not_objdump),
        "objdump_terminator_not_x64lens_count": len(objdump_not_x_raw),
        "x64lens_exact_candidate_count": len(exact_matches) + len(exact_disagreements),
        "x64lens_exact_boundary_match_count": len(exact_matches),
        "x64lens_exact_boundary_disagreement_count": len(exact_disagreements),
        "x64lens_candidate_byte_mismatch_count": len(byte_mismatches),
        "objdump_canonical_sequence_count": len(sequences),
        "objdump_duplicate_canonical_sequence_count": duplicate_canonical_sequences,
        "objdump_supported_sequence_count": len(supported_sequences),
        "objdump_supported_selected_count": len(supported_selected),
        "objdump_supported_unselected_count": len(supported_unselected),
        "objdump_unsupported_sequence_count": len(unsupported_sequences),
    }

    if sha256_file(analyzed_target) != target_digest:
        raise RuntimeError(f"immutable target snapshot changed during decoder-gap measurement: {source_target}")

    comparison = {
        "comparison_model": "x64lens-decoder-gap-v2",
        "target_identity": target_identity,
        "interpretation": {
            "objdump_role": "external canonical-disassembly evidence, not loader authority",
            "x64lens_raw_not_objdump": "byte-oriented terminators absent from objdump's canonical instruction boundaries",
            "objdump_terminator_not_x64lens": "canonical return terminators absent from x64lens raw candidates",
            "exact_boundary_disagreement": "exact suffix start/bytes not reproduced by objdump's canonical boundary sequence",
            "supported_unselected": "supported canonical suffix alternatives not selected by the one-record-per-terminator report model",
            "unsupported_sequence": "canonical return-ending sequence outside the current exact pattern catalog",
            "duplicate_candidate": "additional records sharing one terminator address; preserved separately from unique-boundary coverage",
            "duplicate_canonical_sequence": "canonical sequences sharing the same start, terminator, and bytes after external disassembly normalization",
        },
        "metrics": metrics,
        "commands": {
            "x64lens": asdict(x_measurement),
            "validator": {
                "command": validator_command,
                "command_shell": shlex.join(validator_command),
                "working_directory": ".",
                "exit_code": validator.returncode,
                "stdout_path": validator_stdout.name,
                "stderr_path": validator_stderr.name,
            },
            "objdump": asdict(objdump_measurement),
        },
        "objdump_parse_diagnostics": [asdict(item) for item in parse_diagnostics],
        "samples": {
            "x64lens_raw_not_objdump": [f"0x{value:016x}" for value in x_raw_not_objdump[:sample_limit]],
            "objdump_terminator_not_x64lens": [f"0x{value:016x}" for value in objdump_not_x_raw[:sample_limit]],
            "x64lens_exact_boundary_disagreement": exact_disagreements[:sample_limit],
            "x64lens_candidate_byte_mismatch": byte_mismatches[:sample_limit],
            "objdump_supported_unselected": [sample_sequence(item) for item in supported_unselected[:sample_limit]],
            "objdump_unsupported_sequence": [sample_sequence(item) for item in unsupported_sequences[:sample_limit]],
        },
    }
    return metrics, comparison


def load_controlled_spec(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot load controlled decoder-gap spec {path}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("expected"), dict):
        raise RuntimeError(f"controlled decoder-gap spec is malformed: {path}")
    if not isinstance(value.get("target"), str) or not value["target"]:
        raise RuntimeError(f"controlled decoder-gap spec lacks a target path: {path}")
    if (
        not isinstance(value.get("max_depth"), int)
        or isinstance(value.get("max_depth"), bool)
        or not 1 <= value["max_depth"] <= 32
    ):
        raise RuntimeError(f"controlled decoder-gap spec has an invalid max_depth: {path}")
    return value


def verify_controlled(metrics: dict[str, Any], spec: dict[str, Any]) -> None:
    expected = spec["expected"]
    for field, expected_value in expected.items():
        actual = metrics.get(field)
        if actual != expected_value:
            raise RuntimeError(
                f"controlled decoder-gap mismatch for {field}: expected {expected_value!r}, observed {actual!r}"
            )


def default_system_targets() -> list[Path]:
    candidates = [Path("/bin/ls"), Path("/bin/cat"), Path("/bin/sh"), Path("/usr/bin/env"), Path("/usr/bin/printf")]
    result: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        if resolved.is_file() and resolved not in seen:
            result.append(candidate)
            seen.add(resolved)
    return result


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in SUMMARY_FIELDS})


def validate_results_destination(path: Path) -> Path:
    """Return an absolute safe destination and refuse destructive ambiguity."""

    resolved = path.expanduser().resolve(strict=False)
    protected = {Path("/"), Path.home().resolve(), ROOT.resolve()}
    if resolved in protected or ROOT.resolve().is_relative_to(resolved):
        raise RuntimeError(f"refusing unsafe results directory: {resolved}")
    if path.is_symlink() or resolved.is_symlink():
        raise RuntimeError(f"results directory must not be a symbolic link: {path}")
    if resolved.exists():
        if not resolved.is_dir():
            raise RuntimeError(f"results destination is not a directory: {resolved}")
        marker = resolved / "manifest.json"
        try:
            manifest = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"refusing to replace an unrecognized existing results directory: {resolved}"
            ) from exc
        if manifest.get("format") not in {
            "x64lens-decoder-gap-manifest-v1",
            "x64lens-decoder-gap-manifest-v2",
        }:
            raise RuntimeError(
                f"refusing to replace an unrecognized existing results directory: {resolved}"
            )
    return resolved


def publish_results(
    staging: Path,
    results_dir: Path,
    hook: Callable[[str], None] | None = None,
) -> None:
    """Publish one complete result tree without losing a recognized prior tree."""

    callback = hook or (lambda _stage: None)
    backup: Path | None = None
    try:
        callback("before_backup")
        if results_dir.exists():
            backup = Path(tempfile.mkdtemp(prefix=".decoder-gap-backup-", dir=results_dir.parent))
            backup.rmdir()
            results_dir.replace(backup)
            callback("after_backup")

        callback("before_publish")
        staging.replace(results_dir)
        callback("after_publish")
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
    except BaseException:
        # Rename is atomic but Python signal delivery can occur between the
        # syscall and the next bytecode. Recover from the observable filesystem
        # state instead of relying on an assignment that may not have run.
        with block_campaign_signals():
            backup_visible = backup is not None and backup.exists()
            destination_visible = results_dir.exists()
            staging_visible = staging.exists()

            if not destination_visible and backup_visible:
                backup.replace(results_dir)
            elif destination_visible and not staging_visible:
                # The complete new result is already visible. The prior tree is
                # now only a backup and may be removed.
                if backup_visible:
                    shutil.rmtree(backup, ignore_errors=True)
            elif destination_visible and staging_visible and backup_visible:
                # Publication did not consume staging. Preserve the recognized
                # destination and discard only an empty/duplicate private backup.
                shutil.rmtree(backup, ignore_errors=True)
        raise


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="measure x64lens exact/decoder boundary gaps with objdump")
    parser.add_argument("--binary", type=Path, default=Path("./build/x64lens"))
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--results-dir", type=Path, default=Path("./tests/results/decoder-gap"))
    parser.add_argument(
        "--controlled-spec",
        type=Path,
        default=Path("./tests/expected/decoder-gap-controlled.json"),
    )
    parser.add_argument("--controlled-only", action="store_true")
    parser.add_argument("--sample-limit", type=int, default=25)
    parser.add_argument("targets", nargs="*", type=Path)
    args = parser.parse_args(argv)

    if args.max_depth < 1 or args.max_depth > 32:
        print("decoder-gap-smoke: error: --max-depth must be between 1 and 32", file=sys.stderr)
        return 2
    if args.timeout <= 0 or args.sample_limit < 1:
        print("decoder-gap-smoke: error: timeout and sample limit must be positive", file=sys.stderr)
        return 2
    if not args.binary.is_file() or not os.access(args.binary, os.X_OK):
        print(f"decoder-gap-smoke: error: binary is not executable: {args.binary}", file=sys.stderr)
        return 1
    if not TIME_BIN.is_file() or not os.access(TIME_BIN, os.X_OK):
        print("decoder-gap-smoke: error: /usr/bin/time is required", file=sys.stderr)
        return 127
    objdump_name = shutil.which("objdump")
    if objdump_name is None:
        print("decoder-gap-smoke: error: objdump is required", file=sys.stderr)
        return 127

    old_handlers: dict[int, Any] = {}

    def interrupt_handler(signum: int, _frame: Any) -> None:
        raise CampaignInterrupted(signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        old_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, interrupt_handler)

    try:
        controlled_spec = load_controlled_spec(args.controlled_spec)
        results_dir = validate_results_destination(args.results_dir)
        campaign_path = Path(__file__).resolve(strict=True)
        controlled_spec_path = args.controlled_spec.resolve(strict=True)
        objdump_binary = Path(objdump_name).resolve(strict=True)
        python_binary = Path(sys.executable).resolve(strict=True)
        time_binary = TIME_BIN.resolve(strict=True)
        controlled_target = (ROOT / controlled_spec["target"]).resolve()
        if args.targets:
            targets = args.targets
        elif args.controlled_only:
            targets = [controlled_target]
        else:
            targets = [controlled_target, *default_system_targets()]

        unique_targets: list[Path] = []
        seen_targets: set[Path] = set()
        for target in targets:
            resolved = target.resolve(strict=True)
            if not resolved.is_file():
                raise RuntimeError(f"target is not a file: {target}")
            if resolved not in seen_targets:
                unique_targets.append(target)
                seen_targets.add(resolved)
        if not unique_targets:
            raise RuntimeError("no decoder-gap targets were selected")

        parent = results_dir.parent
        parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".decoder-gap-", dir=parent))
        rows: list[dict[str, Any]] = []
        comparisons: list[dict[str, Any]] = []
        try:
            binary_path = args.binary.resolve(strict=True)
            binary_hash = sha256_file(binary_path)
            campaign_hash = sha256_file(campaign_path)
            controlled_spec_hash = sha256_file(controlled_spec_path)
            objdump_hash = sha256_file(objdump_binary)
            objdump_version = first_line([str(objdump_binary), "--version"], args.timeout)
            binary_version = first_line([str(binary_path), "version"], args.timeout)
            validator_hash = sha256_file(VALIDATOR)
            python_hash = sha256_file(python_binary)
            time_hash = sha256_file(time_binary)
            time_version = first_line([str(time_binary), "--version"], args.timeout)

            snapshots_dir = staging / "inputs"
            snapshots = [
                snapshot_target(target, snapshots_dir, index)
                for index, target in enumerate(unique_targets)
            ]
            target_inventory: list[dict[str, Any]] = []
            for snapshot in snapshots:
                target_inventory.append(
                    {
                        "requested_path": snapshot.requested_path,
                        "resolved_path": snapshot.resolved_path,
                        "snapshot_path": snapshot.snapshot_path.relative_to(staging).as_posix(),
                        "sha256": snapshot.sha256,
                        "size": snapshot.size,
                        "source_device": snapshot.source_device,
                        "source_inode": snapshot.source_inode,
                        "source_mtime_ns": snapshot.source_mtime_ns,
                        "source_ctime_ns": snapshot.source_ctime_ns,
                    }
                )

            run_identity = hashlib.sha256(
                json.dumps(
                    {
                        "binary_sha256": binary_hash,
                        "campaign_path": str(campaign_path),
                        "campaign_sha256": campaign_hash,
                        "campaign_argv": [sys.executable, str(campaign_path), *argv],
                        "controlled_spec_path": str(controlled_spec_path),
                        "controlled_spec_sha256": controlled_spec_hash,
                        "validator_sha256": validator_hash,
                        "python_path": str(python_binary),
                        "python_sha256": python_hash,
                        "python_version": sys.version.split()[0],
                        "objdump_path": str(objdump_binary),
                        "objdump_sha256": objdump_hash,
                        "objdump_version": objdump_version,
                        "time_path": str(time_binary),
                        "time_sha256": time_hash,
                        "time_version": time_version,
                        "max_depth": args.max_depth,
                        "timeout_seconds": args.timeout,
                        "sample_limit": args.sample_limit,
                        "controlled_only": args.controlled_only,
                        "targets": target_inventory,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()

            for index, (target, snapshot, identity) in enumerate(
                zip(unique_targets, snapshots, target_inventory, strict=True)
            ):
                directory = staging / target_label(target, snapshot.sha256, index)
                directory.mkdir(parents=True)
                is_controlled = Path(snapshot.resolved_path) == controlled_target
                metrics, comparison = compare_target(
                    binary=binary_path,
                    objdump_binary=objdump_binary,
                    source_target=Path(snapshot.resolved_path),
                    analyzed_target=snapshot.snapshot_path,
                    target_identity=identity,
                    target_dir=directory,
                    max_depth=args.max_depth,
                    timeout=args.timeout,
                    sample_limit=args.sample_limit,
                    fixture_mode=is_controlled,
                )
                if is_controlled:
                    if controlled_spec.get("max_depth") != args.max_depth:
                        raise RuntimeError(
                            f"controlled spec requires max_depth={controlled_spec.get('max_depth')}, "
                            f"observed {args.max_depth}"
                        )
                    verify_controlled(metrics, controlled_spec)
                (directory / "comparison.json").write_text(
                    json.dumps(comparison, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                rows.append(metrics)
                comparisons.append(
                    {
                        "target": snapshot.resolved_path,
                        "snapshot": identity,
                        "directory": directory.name,
                        "metrics": metrics,
                    }
                )

            for snapshot in snapshots:
                if sha256_file(snapshot.snapshot_path) != snapshot.sha256:
                    raise RuntimeError(
                        f"immutable target snapshot changed before publication: {snapshot.resolved_path}"
                    )

            write_tsv(staging / "decoder-gap-summary.tsv", rows)
            aggregate = {
                "format": "x64lens-decoder-gap-summary-v2",
                "run_id": run_identity,
                "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "max_depth": args.max_depth,
                "binary": {"path": str(binary_path), "sha256": binary_hash, "version": binary_version},
                "campaign": {
                    "path": str(campaign_path),
                    "sha256": campaign_hash,
                    "argv": [sys.executable, str(campaign_path), *argv],
                    "argv_shell": shlex.join([sys.executable, str(campaign_path), *argv]),
                    "timeout_seconds": args.timeout,
                    "sample_limit": args.sample_limit,
                    "controlled_only": args.controlled_only,
                },
                "validator": {
                    "path": str(VALIDATOR.resolve()),
                    "sha256": validator_hash,
                    "python_path": str(python_binary),
                    "python_sha256": python_hash,
                    "python_version": sys.version.split()[0],
                },
                "objdump": {"path": str(objdump_binary), "sha256": objdump_hash, "version": objdump_version},
                "time": {"path": str(time_binary), "sha256": time_hash, "version": time_version},
                "host": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "machine": platform.machine(),
                },
                "controlled_spec": {"path": str(controlled_spec_path), "sha256": controlled_spec_hash},
                "targets": comparisons,
                "decision_policy": "facts only; apply docs/design/decoder-gap-decision-gate.md after review",
            }
            (staging / "decoder-gap-summary.json").write_text(
                json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            (staging / "manifest.json").write_text(
                json.dumps(
                    {
                        "format": "x64lens-decoder-gap-manifest-v2",
                        "run_id": run_identity,
                        "binary_sha256": binary_hash,
                        "campaign_path": str(campaign_path),
                        "campaign_sha256": campaign_hash,
                        "campaign_argv": [sys.executable, str(campaign_path), *argv],
                        "controlled_spec_path": str(controlled_spec_path),
                        "controlled_spec_sha256": controlled_spec_hash,
                        "validator_sha256": validator_hash,
                        "python_path": str(python_binary),
                        "python_sha256": python_hash,
                        "python_version": sys.version.split()[0],
                        "objdump_path": str(objdump_binary),
                        "objdump_sha256": objdump_hash,
                        "objdump_version": objdump_version,
                        "time_path": str(time_binary),
                        "time_sha256": time_hash,
                        "time_version": time_version,
                        "max_depth": args.max_depth,
                        "timeout_seconds": args.timeout,
                        "sample_limit": args.sample_limit,
                        "controlled_only": args.controlled_only,
                        "targets": target_inventory,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            stable_files = [
                (binary_path, binary_hash, "x64lens analyzer"),
                (campaign_path, campaign_hash, "decoder-gap campaign implementation"),
                (controlled_spec_path, controlled_spec_hash, "controlled decoder-gap expectation"),
                (VALIDATOR, validator_hash, "canonical JSON validator"),
                (objdump_binary, objdump_hash, "objdump executable"),
                (python_binary, python_hash, "Python executable"),
                (time_binary, time_hash, "GNU time executable"),
            ]
            for stable_path, expected_hash, label in stable_files:
                if sha256_file(stable_path) != expected_hash:
                    raise RuntimeError(f"{label} changed during decoder-gap measurement")

            publish_results(staging, results_dir)
        except BaseException:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise

        total_boundary_disagreements = sum(row["x64lens_exact_boundary_disagreement_count"] for row in rows)
        total_canonical_only = sum(row["objdump_terminator_not_x64lens_count"] for row in rows)
        print(
            "decoder-gap-smoke: ok "
            f"targets={len(rows)} exact_boundary_disagreements={total_boundary_disagreements} "
            f"canonical_only_terminators={total_canonical_only} results={results_dir}"
        )
        return 0
    except CampaignInterrupted as exc:
        print(f"decoder-gap-smoke: interrupted by signal {exc.signum}", file=sys.stderr)
        return 128 + exc.signum
    except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"decoder-gap-smoke: error: {exc}", file=sys.stderr)
        return 1
    finally:
        for signum, previous in old_handlers.items():
            signal.signal(signum, previous)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
