#!/usr/bin/env python3
"""Normalize one retained baseline native-output artifact for Sprint 11.

This adapter is diagnostic development infrastructure, not an x64lens runtime
component or analysis authority.  It authenticates one exact baseline command,
preserves the retained native stdout/stderr identities, emits only explicitly
named task relations, rejects uncategorized output, and never creates a generic
cross-tool ``gadget_count`` field.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from typing import Any, Iterable

ADAPTER_SCHEMA_VERSION = 1
ADAPTER_ID = "x64lens-sprint11-baseline-output-adapter-v1"
TASK_AUTHORITY_ID = "sprint11-diagnostic-task-definitions-v2"
SUPPORTED_TOOLS = {"ropgadget", "ropper", "ropr"}
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ADDRESS_LINE = re.compile(r"^\s*(0x[0-9A-Fa-f]+)\s*:\s*(.*?)\s*$")
ANSI_ESCAPE = re.compile(rb"\x1b\[[0-?]*[ -/]*[@-~]")
MAX_AUTHORITY_BYTES = 4 * 1024 * 1024
MAX_CAPTURE_BOUND = 256 * 1024 * 1024


class AdapterError(RuntimeError):
    """Raised for invalid adapter input or unreconciled native evidence."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AdapterError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_fd(fd: int, size: int) -> str:
    digest = hashlib.sha256()
    offset = 0
    while offset < size:
        chunk = os.pread(fd, min(1024 * 1024, size - offset), offset)
        require(chunk, "short read while hashing retained evidence")
        digest.update(chunk)
        offset += len(chunk)
    return digest.hexdigest()


def safe_id(value: str, label: str) -> str:
    require(SAFE_ID.fullmatch(value) is not None, f"unsafe {label}: {value!r}")
    return value


def require_sha256(value: str, label: str) -> str:
    require(HEX_SHA256.fullmatch(value) is not None, f"invalid {label}")
    return value


def open_regular_nofollow(path: Path, maximum_bytes: int, label: str) -> int:
    require(0 <= maximum_bytes <= MAX_CAPTURE_BOUND, f"{label} bound is outside the adapter limit")
    absolute = Path(os.path.abspath(path))
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(absolute, flags)
    except OSError as exc:
        raise AdapterError(f"cannot open {label}: {absolute}: {exc}") from exc
    try:
        metadata = os.fstat(descriptor)
        require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file")
        require(metadata.st_size <= maximum_bytes, f"{label} exceeds the {maximum_bytes}-byte bound")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def load_regular_bounded(path: Path, maximum_bytes: int, label: str) -> tuple[bytes, dict[str, Any]]:
    descriptor = open_regular_nofollow(path, maximum_bytes, label)
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        offset = 0
        while offset < before.st_size:
            chunk = os.pread(descriptor, min(1024 * 1024, before.st_size - offset), offset)
            require(chunk, f"short read while reading {label}")
            chunks.append(chunk)
            offset += len(chunk)
        after = os.fstat(descriptor)
        require(
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
            f"{label} changed while being read",
        )
        data = b"".join(chunks)
        require(len(data) == before.st_size, f"{label} size changed while being read")
        return data, {
            "path_requested": str(path),
            "path_resolved": str(Path(f"/proc/self/fd/{descriptor}").resolve(strict=True)),
            "size_bytes": before.st_size,
            "sha256": sha256_bytes(data),
            "mode": stat.S_IMODE(before.st_mode),
            "device": before.st_dev,
            "inode": before.st_ino,
        }
    finally:
        os.close(descriptor)


def require_regular_identity(path: Path, expected: dict[str, Any], maximum_bytes: int, label: str) -> None:
    descriptor = open_regular_nofollow(path, maximum_bytes, label)
    try:
        metadata = os.fstat(descriptor)
        require(
            (metadata.st_dev, metadata.st_ino) == (expected["device"], expected["inode"]),
            f"{label} path no longer identifies the retained file",
        )
        require(stat.S_IMODE(metadata.st_mode) == expected["mode"], f"{label} mode changed")
        require(metadata.st_size == expected["size_bytes"], f"{label} size changed")
        require(sha256_fd(descriptor, metadata.st_size) == expected["sha256"], f"{label} hash changed")
    finally:
        os.close(descriptor)


def directory_identity(path: Path, label: str) -> dict[str, Any]:
    absolute = Path(os.path.abspath(path))
    expected = os.lstat(absolute)
    require(stat.S_ISDIR(expected.st_mode), f"{label} is not a real directory")
    descriptor = os.open(
        absolute,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        observed = os.fstat(descriptor)
        require(
            stat.S_ISDIR(observed.st_mode)
            and (observed.st_dev, observed.st_ino) == (expected.st_dev, expected.st_ino),
            f"{label} changed while being opened",
        )
        return {
            "path": str(Path(f"/proc/self/fd/{descriptor}").resolve(strict=True)),
            "device": observed.st_dev,
            "inode": observed.st_ino,
            "mode": stat.S_IMODE(observed.st_mode),
        }
    finally:
        os.close(descriptor)


def require_directory_identity(path: Path, expected: dict[str, Any], label: str) -> None:
    observed = directory_identity(path, label)
    require(
        (observed["device"], observed["inode"], observed["mode"])
        == (expected["device"], expected["inode"], expected["mode"]),
        f"{label} changed during normalization",
    )


def parse_command_json(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"invalid command JSON: {exc}") from exc
    require(
        isinstance(value, list)
        and value
        and all(isinstance(item, str) and item and "\x00" not in item for item in value),
        "command JSON must be a nonempty string array",
    )
    return value


def normalize_instruction(raw: str) -> str:
    value = " ".join(raw.strip().lower().split())
    value = re.sub(r"\s*,\s*", ", ", value)
    return value


def split_sequence(raw: str) -> list[str]:
    return [normalize_instruction(item) for item in raw.split(";") if item.strip()]


def is_return_terminator(instruction: str) -> bool:
    return instruction in {"ret", "retq"} or re.fullmatch(
        r"ret(?:q)?\s+(?:0x[0-9a-f]+|[0-9]+)", instruction
    ) is not None


def ignored_native_line(tool: str, line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    patterns = {
        "ropgadget": (
            r"^gadgets information$",
            r"^=+$",
            r"^unique gadgets found:\s*\d+$",
            r"^\[\*\].*$",
        ),
        "ropper": (
            r"^\[info\].*$",
            r"^gadgets$",
            r"^=+$",
            r"^\d+ gadgets found$",
            r"^searching for gadgets:.*$",
            r"^loading gadgets.*$",
        ),
        "ropr": (
            r"^rop gadgets.*$",
            r"^=+$",
            r"^==> found \d+ gadgets(?: in .*)?$",
        ),
    }
    lowered = stripped.lower()
    return any(re.fullmatch(pattern, lowered) is not None for pattern in patterns[tool])


def parse_native_output(
    tool: str,
    data: bytes,
    *,
    require_return_terminated: bool,
    maximum_line_bytes: int,
    maximum_record_count: int,
    maximum_instruction_count: int,
) -> tuple[list[dict[str, Any]], int, int]:
    ansi_count = len(ANSI_ESCAPE.findall(data))
    cleaned = ANSI_ESCAPE.sub(b"", data)
    try:
        text = cleaned.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AdapterError(f"native stdout is not valid UTF-8: {exc}") from exc

    records: list[dict[str, Any]] = []
    unknown: list[tuple[int, str]] = []
    ignored_count = 0
    for line_number, line in enumerate(text.splitlines(), 1):
        require(len(line.encode("utf-8")) <= maximum_line_bytes, f"native stdout line {line_number} exceeds the parser bound")
        match = ADDRESS_LINE.fullmatch(line)
        if match is None:
            if ignored_native_line(tool, line):
                ignored_count += 1
            else:
                unknown.append((line_number, line[:160]))
            continue
        address_text, sequence_text = match.groups()
        instructions = split_sequence(sequence_text)
        if not instructions:
            unknown.append((line_number, line[:160]))
            continue
        address = int(address_text, 16)
        require(address <= 0xFFFFFFFFFFFFFFFF, f"native stdout address exceeds the x86_64 domain on line {line_number}")
        require(len(records) < maximum_record_count, "native stdout exceeds the record-count bound")
        require(len(instructions) <= maximum_instruction_count, f"native stdout record exceeds the instruction-count bound on line {line_number}")
        canonical_address = f"0x{address:016x}"
        terminator = instructions[-1]
        return_terminated = is_return_terminator(terminator)
        if require_return_terminated and not return_terminated:
            unknown.append((line_number, line[:160]))
            continue
        records.append(
            {
                "line_number": line_number,
                "address": canonical_address,
                "native_sequence": sequence_text.strip(),
                "instructions": instructions,
                "return_terminated": return_terminated,
                "terminator": terminator if return_terminated else None,
                "canonical_pop_rdi_ret": instructions in (["pop rdi", "ret"], ["pop rdi", "retq"]),
            }
        )

    if unknown:
        rendered = "; ".join(f"line {number}: {value!r}" for number, value in unknown[:5])
        raise AdapterError(
            f"native stdout contains {len(unknown)} uncategorized or out-of-task lines: {rendered}"
        )
    require(records, "native stdout contains no address-bearing records")
    return records, ansi_count, ignored_count


def resolve_command_path(raw: str, cwd: Path) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = cwd / candidate
    return Path(os.path.abspath(candidate))


def same_regular_file(left: Path, right_identity: dict[str, Any], label: str) -> None:
    descriptor = open_regular_nofollow(left, MAX_CAPTURE_BOUND, label)
    try:
        metadata = os.fstat(descriptor)
        require(
            (metadata.st_dev, metadata.st_ino) == (right_identity["device"], right_identity["inode"]),
            f"{label} does not identify the retained file",
        )
        require(sha256_fd(descriptor, metadata.st_size) == right_identity["sha256"], f"{label} hash mismatch")
    finally:
        os.close(descriptor)


def validate_command(
    template: list[str],
    command: list[str],
    command_cwd: Path,
    tool_identity: dict[str, Any],
    target_identity: dict[str, Any],
) -> None:
    require(len(template) == len(command), "command length does not match the task authority")
    tool_placeholders = 0
    target_placeholders = 0
    for index, (expected, observed) in enumerate(zip(template, command, strict=True)):
        if expected == "<tool>":
            tool_placeholders += 1
            same_regular_file(resolve_command_path(observed, command_cwd), tool_identity, f"command[{index}] tool")
        elif expected == "<target>":
            target_placeholders += 1
            same_regular_file(resolve_command_path(observed, command_cwd), target_identity, f"command[{index}] target")
        else:
            require(observed == expected, f"command[{index}] does not match task authority")
    require(tool_placeholders == 1 and target_placeholders == 1, "task command must identify one tool and one target")


def recursively_reject_generic_count(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            require(key != "gadget_count", f"forbidden generic gadget_count at {path}.{key}")
            recursively_reject_generic_count(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            recursively_reject_generic_count(item, f"{path}[{index}]")


def build_artifact(
    *,
    tool: str,
    tool_version: str,
    condition_id: str,
    target_id: str,
    command: list[str],
    command_cwd: Path,
    tool_identity: dict[str, Any],
    target_identity: dict[str, Any],
    version_identity: dict[str, Any],
    stdout_identity: dict[str, Any],
    stderr_identity: dict[str, Any],
    task_authority_identity: dict[str, Any],
    records: list[dict[str, Any]],
    ansi_count: int,
    ignored_line_count: int,
    task_scope: str,
    relation_ids: list[str],
    parser_limits: dict[str, int],
    adapter_data: bytes,
    adapter_identity: dict[str, Any],
) -> dict[str, Any]:
    native_keys = [(record["address"], tuple(record["instructions"])) for record in records]
    unique_native_keys = set(native_keys)
    return_records = [record for record in records if record["return_terminated"]]
    return_sites = {record["address"] for record in return_records}
    exact_records = [record for record in records if record["canonical_pop_rdi_ret"]]
    exact_relations = {(record["address"], tuple(record["instructions"])) for record in exact_records}
    exact_relation_records = [
        {"address": record["address"], "instructions": record["instructions"], "source_line": record["line_number"]}
        for record in exact_records
    ]
    artifact = {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "adapter": {
            "id": ADAPTER_ID,
            "sha256": sha256_bytes(adapter_data),
            "size_bytes": adapter_identity["size_bytes"],
        },
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "claim_boundary": "tool-specific development normalization; not publication evidence or analyzer authority",
        "task_authority": {
            "id": TASK_AUTHORITY_ID,
            "path_requested": task_authority_identity["path_requested"],
            "path_resolved": task_authority_identity["path_resolved"],
            "sha256": task_authority_identity["sha256"],
            "size_bytes": task_authority_identity["size_bytes"],
        },
        "condition": {
            "condition_id": condition_id,
            "task_scope": task_scope,
            "normalized_relation_ids": relation_ids,
        },
        "tool": {
            "id": tool,
            "version": tool_version,
            "executable": {
                key: tool_identity[key]
                for key in ("path_requested", "path_resolved", "size_bytes", "sha256", "mode")
            },
            "version_output": {
                key: version_identity[key]
                for key in ("path_requested", "path_resolved", "size_bytes", "sha256")
            },
            "command": command,
            "command_cwd": str(command_cwd),
        },
        "target": {
            "id": target_id,
            **{
                key: target_identity[key]
                for key in ("path_requested", "path_resolved", "size_bytes", "sha256", "mode")
            },
        },
        "native_output": {
            "stdout": {
                key: stdout_identity[key]
                for key in ("path_requested", "path_resolved", "size_bytes", "sha256")
            },
            "stderr": {
                key: stderr_identity[key]
                for key in ("path_requested", "path_resolved", "size_bytes", "sha256")
            },
            "ansi_sequences_removed_from_stdout": ansi_count,
            "ignored_stdout_line_count": ignored_line_count,
            "uncategorized_stdout_line_count": 0,
            "parser_limits": parser_limits,
        },
        "metrics": {
            "tool_native_record_count": len(records),
            "unique_tool_native_record_count": len(unique_native_keys),
            "duplicate_tool_native_record_count": len(records) - len(unique_native_keys),
            "tool_reported_return_terminator_record_count": len(return_records),
            "unique_tool_reported_return_terminator_site_count": len(return_sites),
            "canonical_exact_pop_rdi_ret_record_count": len(exact_records),
            "unique_canonical_exact_pop_rdi_ret_relation_count": len(exact_relations),
        },
        "normalized_relations": {
            "canonical_exact_pop_rdi_ret": {
                "record_count": len(exact_records),
                "unique_relation_count": len(exact_relations),
                "records": exact_relation_records,
            },
            "binary_fact_arg_control_rdi_present": bool(exact_relations),
        },
        "records": records,
        "limitations": [
            "Addresses and instruction text are normalized from the named baseline's retained native stdout.",
            "A normalized exact relation is not an x64lens raw, semantic-exact, or decoder-backed candidate population.",
            "Tool-native totals remain tool-specific and are not a generic cross-tool gadget count.",
            "The adapter does not select executable regions, decode target bytes, assign x64lens semantics, or score candidates.",
        ],
    }
    recursively_reject_generic_count(artifact)
    return artifact


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def write_exclusive(path: Path, data: bytes) -> None:
    absolute = Path(os.path.abspath(path))
    parent = absolute.parent
    metadata = os.lstat(parent)
    require(stat.S_ISDIR(metadata.st_mode), "output parent is not a real directory")
    parent_fd = os.open(
        parent,
        os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    observed_parent = os.fstat(parent_fd)
    require(
        stat.S_ISDIR(observed_parent.st_mode)
        and (observed_parent.st_dev, observed_parent.st_ino) == (metadata.st_dev, metadata.st_ino),
        "output parent changed while being opened",
    )
    created = False
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(absolute.name, flags, 0o600, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise AdapterError(f"refusing to replace normalized output: {absolute}") from exc
        created = True
        try:
            offset = 0
            while offset < len(data):
                written = os.write(descriptor, data[offset:])
                require(written > 0, "short write while creating normalized output")
                offset += written
            os.fsync(descriptor)
        except BaseException:
            os.close(descriptor)
            descriptor = -1
            try:
                os.unlink(absolute.name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            except OSError:
                pass
            raise
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    require(created, "normalized output was not created")


def normalize(args: argparse.Namespace) -> bytes:
    tool = safe_id(args.tool, "tool id")
    require(tool in SUPPORTED_TOOLS, f"unsupported baseline tool: {tool}")
    condition_id = safe_id(args.condition_id, "condition id")
    target_id = safe_id(args.target_id, "target id")
    require(args.tool_version and "\x00" not in args.tool_version, "tool version must be nonempty")
    target_sha256 = require_sha256(args.target_sha256, "target SHA-256")
    command = parse_command_json(args.command_json)
    command_cwd_requested = Path(os.path.abspath(args.command_cwd))
    command_cwd_identity = directory_identity(command_cwd_requested, "command cwd")
    command_cwd = Path(command_cwd_identity["path"])
    adapter_source = Path(__file__)
    adapter_data, adapter_identity = load_regular_bounded(adapter_source, MAX_CAPTURE_BOUND, "adapter source")

    authority_data, authority_identity = load_regular_bounded(
        args.task_authority, MAX_AUTHORITY_BYTES, "task authority"
    )
    try:
        authority = json.loads(authority_data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError(f"cannot parse task authority: {exc}") from exc
    require(authority.get("schema_version") == 2, "unsupported task authority schema")
    require(authority.get("authority_id") == TASK_AUTHORITY_ID, "unexpected task authority identity")
    baseline = next(
        (
            item
            for item in authority.get("baselines", [])
            if isinstance(item, dict) and item.get("id") == tool
        ),
        None,
    )
    require(baseline is not None and baseline.get("status") == "implemented", f"task authority does not implement baseline {tool}")
    require(baseline.get("condition_id") == condition_id, f"condition id does not match task authority for {tool}")
    require(baseline.get("normalization_required") is True, f"normalization is not required for {tool}")
    require(baseline.get("adapter", {}).get("id") == ADAPTER_ID, f"adapter identity mismatch for {tool}")

    capture = baseline.get("capture_policy")
    require(isinstance(capture, dict), f"missing capture policy for {tool}")
    maximum_stdout = capture.get("maximum_stdout_bytes")
    maximum_stderr = capture.get("maximum_stderr_bytes")
    require(isinstance(maximum_stdout, int) and 4096 <= maximum_stdout <= MAX_CAPTURE_BOUND, f"invalid stdout cap for {tool}")
    require(isinstance(maximum_stderr, int) and 0 <= maximum_stderr <= MAX_CAPTURE_BOUND, f"invalid stderr cap for {tool}")

    tool_data, tool_identity = load_regular_bounded(args.tool_executable, MAX_CAPTURE_BOUND, "tool executable")
    require(tool_identity["mode"] & 0o111, "tool executable is not executable")
    target_data, target_identity = load_regular_bounded(args.target_path, MAX_CAPTURE_BOUND, "target")
    require(target_identity["sha256"] == target_sha256, "declared target SHA-256 does not match retained target")
    version_data, version_identity = load_regular_bounded(args.version_output, maximum_stdout, "version output")
    try:
        version_text = version_data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AdapterError(f"version output is not valid UTF-8: {exc}") from exc
    require(args.tool_version in version_text, "declared tool version is absent from retained version output")
    stdout_data, stdout_identity = load_regular_bounded(args.native_stdout, maximum_stdout, "native stdout")
    _, stderr_identity = load_regular_bounded(args.native_stderr, maximum_stderr, "native stderr")

    command_template = baseline.get("command_template")
    require(
        isinstance(command_template, list)
        and command_template
        and all(isinstance(item, str) and item for item in command_template),
        f"invalid command template for {tool}",
    )
    validate_command(command_template, command, command_cwd, tool_identity, target_identity)

    native_contract = baseline.get("native_output_contract")
    require(isinstance(native_contract, dict), f"missing native output contract for {tool}")
    maximum_line_bytes = native_contract.get("maximum_line_bytes")
    maximum_record_count = native_contract.get("maximum_record_count")
    maximum_instruction_count = native_contract.get("maximum_instruction_count")
    require(isinstance(maximum_line_bytes, int) and 64 <= maximum_line_bytes <= maximum_stdout, f"invalid native line bound for {tool}")
    require(isinstance(maximum_record_count, int) and 1 <= maximum_record_count <= 1_000_000, f"invalid native record bound for {tool}")
    require(isinstance(maximum_instruction_count, int) and 1 <= maximum_instruction_count <= 64, f"invalid native instruction bound for {tool}")
    records, ansi_count, ignored_line_count = parse_native_output(
        tool,
        stdout_data,
        require_return_terminated=native_contract.get("require_return_terminated") is True,
        maximum_line_bytes=maximum_line_bytes,
        maximum_record_count=maximum_record_count,
        maximum_instruction_count=maximum_instruction_count,
    )
    relation_ids = baseline.get("normalized_relation_ids")
    require(
        relation_ids
        == [
            "tool_reported_return_terminator_records",
            "canonical_exact_pop_rdi_ret",
            "binary_fact_arg_control_rdi_present",
        ],
        f"unexpected normalized relation set for {tool}",
    )
    artifact = build_artifact(
        tool=tool,
        tool_version=args.tool_version,
        condition_id=condition_id,
        target_id=target_id,
        command=command,
        command_cwd=command_cwd,
        tool_identity=tool_identity,
        target_identity=target_identity,
        version_identity=version_identity,
        stdout_identity=stdout_identity,
        stderr_identity=stderr_identity,
        task_authority_identity=authority_identity,
        records=records,
        ansi_count=ansi_count,
        ignored_line_count=ignored_line_count,
        task_scope=baseline.get("task_scope"),
        relation_ids=relation_ids,
        parser_limits={
            "maximum_line_bytes": maximum_line_bytes,
            "maximum_record_count": maximum_record_count,
            "maximum_instruction_count": maximum_instruction_count,
        },
        adapter_data=adapter_data,
        adapter_identity=adapter_identity,
    )
    # Reauthenticate every retained input after parsing and artifact construction.
    # This ensures the normalized object remains bound to paths that still name
    # the bytes it records rather than merely to copies read earlier.
    require_regular_identity(adapter_source, adapter_identity, MAX_CAPTURE_BOUND, "adapter source")
    require_regular_identity(args.task_authority, authority_identity, MAX_AUTHORITY_BYTES, "task authority")
    require_regular_identity(args.tool_executable, tool_identity, MAX_CAPTURE_BOUND, "tool executable")
    require_regular_identity(args.target_path, target_identity, MAX_CAPTURE_BOUND, "target")
    require_regular_identity(args.version_output, version_identity, maximum_stdout, "version output")
    require_regular_identity(args.native_stdout, stdout_identity, maximum_stdout, "native stdout")
    require_regular_identity(args.native_stderr, stderr_identity, maximum_stderr, "native stderr")
    require_directory_identity(command_cwd_requested, command_cwd_identity, "command cwd")
    # Keep read bytes live until after every identity and artifact field is built.
    require(sha256_bytes(tool_data) == tool_identity["sha256"], "tool bytes changed during normalization")
    require(sha256_bytes(target_data) == target_identity["sha256"], "target bytes changed during normalization")
    return canonical_bytes(artifact)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", required=True, choices=sorted(SUPPORTED_TOOLS))
    parser.add_argument("--tool-version", required=True)
    parser.add_argument("--tool-executable", type=Path, required=True)
    parser.add_argument("--version-output", type=Path, required=True)
    parser.add_argument("--condition-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--target-path", type=Path, required=True)
    parser.add_argument("--target-sha256", required=True)
    parser.add_argument("--command-json", required=True)
    parser.add_argument("--command-cwd", type=Path, required=True)
    parser.add_argument("--native-stdout", type=Path, required=True)
    parser.add_argument("--native-stderr", type=Path, required=True)
    parser.add_argument("--task-authority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    data = normalize(args)
    write_exclusive(args.output, data)
    artifact = json.loads(data)
    metrics = artifact["metrics"]
    print(
        "baseline-output-adapter: ok "
        f"tool={args.tool} records={metrics['tool_native_record_count']} "
        f"return_records={metrics['tool_reported_return_terminator_record_count']} "
        f"pop_rdi_ret={metrics['canonical_exact_pop_rdi_ret_record_count']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (AdapterError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"baseline-output-adapter: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
