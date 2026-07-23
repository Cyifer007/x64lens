#!/usr/bin/env python3
"""Normalize one runner-bound baseline output into named diagnostic relations.

The adapter is development infrastructure, not x64lens runtime authority.  It
accepts only a published diagnostic campaign plus one unique row identifier,
authenticates the runner manifest and retained objects, parses the tool-native
text under explicit bounds, preserves duplicates, and emits only relations
named by the Sprint 11 task authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from diagnostic_artifact import (  # noqa: E402
    ArtifactError,
    MAX_JSON_BYTES,
    atomic_publish_bytes,
    canonical_json_bytes,
    directory_member_identity,
    load_authority,
    load_campaign,
    load_member,
    load_regular_path,
    require,
    require_directory_member_identity,
    require_regular_path_identity,
    safe_id,
    sha256_bytes,
)

ADAPTER_SCHEMA_VERSION = 2
ADAPTER_ID = "x64lens-sprint11-baseline-output-adapter-v2"
TASK_AUTHORITY_SCHEMA_VERSION = 3
TASK_AUTHORITY_ID = "sprint11-diagnostic-task-definitions-v3"
SUPPORTED_TOOLS = {"ropgadget", "ropper", "ropr"}
ADDRESS_LINE = re.compile(r"^\s*(0x[0-9A-Fa-f]+)\s*:\s*(.*?)\s*$")
ANSI_ESCAPE = re.compile(rb"\x1b\[[0-?]*[ -/]*[@-~]")
MAX_CAPTURE_BOUND = 256 * 1024 * 1024


class AdapterError(ArtifactError):
    """Raised for an invalid command, native record, or relation artifact."""


def canonical_address(value: str) -> str:
    parsed = int(value, 16)
    require(0 <= parsed <= 0xFFFFFFFFFFFFFFFF, f"address is outside the unsigned x86_64 domain: {value}")
    return f"0x{parsed:016x}"


def normalize_instruction(raw: str) -> str:
    value = " ".join(raw.strip().lower().split())
    value = re.sub(r"\s*,\s*", ", ", value)
    return value


def canonicalize_instruction(instruction: str) -> str:
    if instruction == "retq":
        return "ret"
    match = re.fullmatch(r"retq\s+(.+)", instruction)
    if match:
        return f"ret {match.group(1)}"
    return instruction


def split_sequence(raw: str) -> tuple[list[str], list[str]]:
    native = [normalize_instruction(item) for item in raw.split(";") if item.strip()]
    return native, [canonicalize_instruction(item) for item in native]


def is_return_terminator(instruction: str) -> bool:
    return instruction == "ret" or re.fullmatch(r"ret\s+(?:0x[0-9a-f]+|[0-9]+)", instruction) is not None


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


def raw_lines(data: bytes, maximum_line_bytes: int) -> list[bytes]:
    # splitlines() omits a trailing empty record; that is immaterial because
    # empty native lines are explicitly ignored.  The bound applies before ANSI
    # removal so escape-heavy input cannot shrink below the declared limit.
    lines = data.splitlines()
    for index, line in enumerate(lines, start=1):
        require(len(line) <= maximum_line_bytes, f"native output line {index} exceeds the raw {maximum_line_bytes}-byte bound")
    return lines


def parse_native_output(
    tool: str,
    data: bytes,
    *,
    require_return_terminated: bool,
    maximum_line_bytes: int,
    maximum_record_count: int,
    maximum_instruction_count: int,
) -> tuple[list[dict[str, Any]], int, int]:
    lines = raw_lines(data, maximum_line_bytes)
    ansi_count = sum(len(ANSI_ESCAPE.findall(line)) for line in lines)
    records: list[dict[str, Any]] = []
    ignored = 0
    for line_number, raw_line in enumerate(lines, start=1):
        cleaned = ANSI_ESCAPE.sub(b"", raw_line)
        try:
            line = cleaned.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise AdapterError(f"native output line {line_number} is not valid UTF-8: {exc}") from exc
        if ignored_native_line(tool, line):
            ignored += 1
            continue
        match = ADDRESS_LINE.fullmatch(line)
        require(match is not None, f"uncategorized {tool} native output at line {line_number}: {line!r}")
        address = canonical_address(match.group(1))
        native_instructions, canonical_instructions = split_sequence(match.group(2))
        require(native_instructions, f"empty instruction sequence at line {line_number}")
        require(len(native_instructions) <= maximum_instruction_count, f"native record at line {line_number} exceeds the instruction bound")
        if require_return_terminated:
            require(is_return_terminator(canonical_instructions[-1]), f"native record at line {line_number} is not return-terminated")
        records.append(
            {
                "native_record_index": len(records),
                "source_line": line_number,
                "address": address,
                "native_text": line,
                "native_instructions": native_instructions,
                "canonical_instructions": canonical_instructions,
            }
        )
        require(len(records) <= maximum_record_count, "native record count exceeds the declared bound")
    return records, ansi_count, ignored


def parse_command_json(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdapterError(f"row command JSON is invalid: {exc}") from exc
    require(isinstance(value, list) and value and all(isinstance(item, str) and item and "\x00" not in item for item in value), "row command must be a nonempty string array")
    return value


def resolve_recorded_argument(command_cwd: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = command_cwd / candidate
    return candidate.resolve(strict=True)


def validate_command(
    template: list[str],
    command: list[str],
    command_cwd: Path,
    tool_snapshot: Path,
    target_snapshot: Path,
) -> None:
    require(len(template) == len(command), "row command length does not match task authority")
    for index, (expected, observed) in enumerate(zip(template, command, strict=True)):
        if expected == "<tool>":
            require(resolve_recorded_argument(command_cwd, observed) == tool_snapshot, f"row command tool path mismatch at argument {index}")
        elif expected == "<target>":
            require(resolve_recorded_argument(command_cwd, observed) == target_snapshot, f"row command target path mismatch at argument {index}")
        else:
            require(observed == expected, f"row command differs from task authority at argument {index}: {observed!r}")


def exact_version(
    *,
    baseline: dict[str, Any],
    declared: str,
    retained_stdout: bytes,
) -> str:
    try:
        text = retained_stdout.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AdapterError(f"retained version output is not valid UTF-8: {exc}") from exc
    lines = text.splitlines()
    require(lines, "retained version output is empty")
    observed = lines[0].strip()
    require(observed == declared.strip(), "declared tool version is not the exact retained first line")
    contract = baseline.get("version_contract")
    require(isinstance(contract, dict), "baseline version contract is missing")
    require(contract.get("comparison") == "exact_trimmed_first_line", "unsupported baseline version comparison")
    pattern = contract.get("line_regex")
    require(isinstance(pattern, str) and re.fullmatch(pattern, observed) is not None, "retained tool version does not match the authority pattern")
    return observed


def unique_key_count(records: list[dict[str, Any]]) -> tuple[int, int]:
    keys = [(record["address"], tuple(record["canonical_instructions"])) for record in records]
    unique = len(set(keys))
    return unique, len(keys) - unique


def build_artifact(
    *,
    context: Any,
    row: dict[str, str],
    authority_identity: dict[str, Any],
    adapter_identity: dict[str, Any],
    baseline: dict[str, Any],
    version_identity: dict[str, Any],
    stdout_identity: dict[str, Any],
    stderr_identity: dict[str, Any],
    command_cwd_identity: dict[str, Any],
    records: list[dict[str, Any]],
    ansi_count: int,
    ignored_line_count: int,
) -> dict[str, Any]:
    tool_id = row["tool_id"]
    tool = context.tools[tool_id]
    target = context.targets[row["target_id"]]
    unique_count, duplicate_count = unique_key_count(records)
    return_records = [record for record in records if is_return_terminator(record["canonical_instructions"][-1])]
    exact_records = [
        record
        for record in records
        if record["canonical_instructions"] == ["pop rdi", "ret"]
    ]
    exact_unique = len({(record["address"], tuple(record["canonical_instructions"])) for record in exact_records})
    row_bytes = canonical_json_bytes(row)
    return {
        "schema_version": ADAPTER_SCHEMA_VERSION,
        "artifact_type": "x64lens-sprint11-baseline-normalization",
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "adapter": {
            "id": ADAPTER_ID,
            "schema_version": ADAPTER_SCHEMA_VERSION,
            "path": baseline["adapter"]["path"],
            "size_bytes": adapter_identity["size_bytes"],
            "sha256": adapter_identity["sha256"],
        },
        "campaign_binding": {
            "campaign_id": context.manifest["campaign_id"],
            "campaign_root": str(context.root),
            "manifest_size_bytes": context.manifest_identity["size_bytes"],
            "manifest_sha256": context.manifest_identity["sha256"],
            "rows_path": context.manifest["artifacts"]["rows"],
            "rows_size_bytes": context.rows_identity["size_bytes"],
            "rows_sha256": context.rows_identity["sha256"],
            "run_id": row["run_id"],
            "row_sha256": sha256_bytes(row_bytes),
        },
        "task_authority": {
            "id": TASK_AUTHORITY_ID,
            "schema_version": TASK_AUTHORITY_SCHEMA_VERSION,
            "path": authority_identity["path_resolved"],
            "size_bytes": authority_identity["size_bytes"],
            "sha256": authority_identity["sha256"],
        },
        "tool": {
            "id": tool_id,
            "version": row["tool_version"],
            "snapshot_path": tool["snapshot_path"],
            "size_bytes": tool["size_bytes"],
            "sha256": tool["sha256"],
            "version_stdout_path": tool["version_stdout_path"],
            "version_stdout_size_bytes": version_identity["size_bytes"],
            "version_stdout_sha256": version_identity["sha256"],
        },
        "target": {
            "id": row["target_id"],
            "license": row["target_license"],
            "snapshot_path": target["snapshot_path"],
            "size_bytes": target["size_bytes"],
            "sha256": target["sha256"],
        },
        "execution": {
            "condition_id": row["condition_id"],
            "task_scope": row["task_scope"],
            "run_id": row["run_id"],
            "phase": row["phase"],
            "round": int(row["round"]),
            "order_index": int(row["order_index"]),
            "process_outcome": row["process_outcome"],
            "outcome": row["outcome"],
            "exit_code": int(row["exit_code"]),
            "command": parse_command_json(row["command_json"]),
            "command_cwd": row["command_cwd"],
            "command_cwd_identity": command_cwd_identity,
        },
        "native_output": {
            "stdout_path": row["stdout_path"],
            "stdout_size_bytes": stdout_identity["size_bytes"],
            "stdout_sha256": stdout_identity["sha256"],
            "stderr_path": row["stderr_path"],
            "stderr_size_bytes": stderr_identity["size_bytes"],
            "stderr_sha256": stderr_identity["sha256"],
            "ansi_escape_count": ansi_count,
            "ignored_line_count": ignored_line_count,
            "uncategorized_line_count": 0,
            "native_records": records,
        },
        "parser_limits": {
            "maximum_stdout_bytes": baseline["capture_policy"]["maximum_stdout_bytes"],
            "maximum_stderr_bytes": baseline["capture_policy"]["maximum_stderr_bytes"],
            "maximum_line_bytes": baseline["native_output_contract"]["maximum_line_bytes"],
            "maximum_line_bytes_scope": "raw_bytes_before_ansi_normalization",
            "maximum_record_count": baseline["native_output_contract"]["maximum_record_count"],
            "maximum_instruction_count": baseline["native_output_contract"]["maximum_instruction_count"],
        },
        "normalized_relations": {
            "executable_return_byte_presence": {
                "status": "unavailable",
                "substitution_allowed": False,
                "reason": "baseline native gadget records do not provide the program-header-authoritative raw executable-byte population",
            },
            "tool_reported_return_terminator_records": {
                "status": "observed",
                "record_count": len(return_records),
                "unique_record_count": len({(record["address"], tuple(record["canonical_instructions"])) for record in return_records}),
                "records": return_records,
            },
            "canonical_exact_pop_rdi_ret": {
                "status": "observed" if exact_records else "observed_zero",
                "record_count": len(exact_records),
                "unique_relation_count": exact_unique,
                "records": [
                    {
                        "address": record["address"],
                        "instructions": ["pop rdi", "ret"],
                        "native_record_index": record["native_record_index"],
                    }
                    for record in exact_records
                ],
            },
            "binary_fact_arg_control_rdi_present": {
                "status": "observed",
                "value": bool(exact_records),
            },
        },
        "metrics": {
            "tool_native_record_count": len(records),
            "unique_tool_native_record_count": unique_count,
            "duplicate_tool_native_record_count": duplicate_count,
            "tool_reported_return_terminator_record_count": len(return_records),
            "unique_tool_reported_return_terminator_site_count": len({record["address"] for record in return_records}),
            "canonical_exact_pop_rdi_ret_record_count": len(exact_records),
            "unique_canonical_exact_pop_rdi_ret_relation_count": exact_unique,
            "binary_fact_arg_control_rdi_present": bool(exact_records),
        },
        "limitations": [
            "The artifact is runner-bound diagnostic evidence and not a release or publication result.",
            "The parser represents only address-colon-semicolon text accepted by the named authority contract.",
            "Instruction text is normalized and retq is canonically represented as ret; the native text remains retained.",
            "Displayed baseline addresses require a separate ET_EXEC/ET_DYN coordinate calibration before cross-tool joins.",
            "Tool-native records and duplicates remain tool-specific populations; no generic gadget count is created.",
        ],
    }


def normalize(args: argparse.Namespace) -> tuple[bytes, Any, list[tuple[str, dict[str, Any], int, str]], dict[str, Any], dict[str, Any]]:
    context = load_campaign(args.campaign_result)
    authority, authority_identity, _ = load_authority(
        args.task_authority,
        schema_version=TASK_AUTHORITY_SCHEMA_VERSION,
        authority_id=TASK_AUTHORITY_ID,
    )
    adapter_source = Path(__file__).resolve(strict=True)
    _, adapter_identity = load_regular_path(adapter_source, MAX_JSON_BYTES, "adapter source")
    try:
        row = context.row(args.run_id)
        tool_id = safe_id(row["tool_id"], "tool id")
        require(tool_id in SUPPORTED_TOOLS, f"unsupported baseline tool: {tool_id}")
        require(row["process_outcome"] == "success" and row["outcome"] == "success" and int(row["exit_code"]) == 0, "baseline adapter requires a successful runner row")
        baseline = next((item for item in authority.get("baselines", []) if isinstance(item, dict) and item.get("id") == tool_id), None)
        require(isinstance(baseline, dict) and baseline.get("status") == "implemented", f"task authority does not implement {tool_id}")
        base_condition = baseline.get("condition_id")
        require(baseline.get("condition_id_rule") == "base_or_base--target_id", f"condition-id rule is missing for {tool_id}")
        require(
            row["condition_id"] in {base_condition, f"{base_condition}--{row['target_id']}"},
            f"row condition does not match the authority for {tool_id}",
        )
        adapter = baseline.get("adapter")
        require(isinstance(adapter, dict), f"adapter contract is missing for {tool_id}")
        require(adapter.get("id") == ADAPTER_ID and adapter.get("schema_version") == ADAPTER_SCHEMA_VERSION, f"adapter identity/schema mismatch for {tool_id}")
        repo_root = adapter_source.parents[2]
        expected_adapter = (repo_root / adapter.get("path", "")).resolve(strict=True)
        require(expected_adapter == adapter_source, f"authority-declared adapter path does not identify the running adapter for {tool_id}")
        require(adapter.get("campaign_row_binding_required") is True, f"campaign-row binding is not required for {tool_id}")

        tool = context.tools[tool_id]
        target = context.targets[row["target_id"]]
        command_cwd_identity = directory_member_identity(context.root_fd, context.root, row["command_cwd"], f"row {row['run_id']} command cwd")
        command_cwd = context.root.joinpath(*Path(row["command_cwd"]).parts).resolve(strict=True)
        tool_snapshot = context.root.joinpath(*Path(tool["snapshot_path"]).parts).resolve(strict=True)
        target_snapshot = context.root.joinpath(*Path(target["snapshot_path"]).parts).resolve(strict=True)
        command = parse_command_json(row["command_json"])
        validate_command(baseline["command_template"], command, command_cwd, tool_snapshot, target_snapshot)
        require(int(row["stdout_limit_bytes"]) == baseline["capture_policy"]["maximum_stdout_bytes"], "row stdout limit differs from task authority")
        require(int(row["stderr_limit_bytes"]) == baseline["capture_policy"]["maximum_stderr_bytes"], "row stderr limit differs from task authority")

        version_data, version_identity = load_member(context.root_fd, context.root, tool["version_stdout_path"], baseline["capture_policy"]["maximum_stdout_bytes"], f"tool {tool_id} version stdout")
        observed_version = exact_version(baseline=baseline, declared=row["tool_version"], retained_stdout=version_data)
        require(observed_version == tool["version"] == tool.get("version_observed"), "runner tool-version records disagree")
        stdout_data, stdout_identity = context.load_row_member(row, "stdout")
        _, stderr_identity = context.load_row_member(row, "stderr")
        contract = baseline["native_output_contract"]
        require(contract.get("maximum_line_bytes_scope") == "raw_bytes_before_ansi_normalization", "task authority does not define the raw-line bound")
        records, ansi_count, ignored_count = parse_native_output(
            tool_id,
            stdout_data,
            require_return_terminated=contract.get("require_return_terminated") is True,
            maximum_line_bytes=contract["maximum_line_bytes"],
            maximum_record_count=contract["maximum_record_count"],
            maximum_instruction_count=contract["maximum_instruction_count"],
        )
        relation_ids = baseline.get("normalized_relation_ids")
        require(relation_ids == [
            "tool_reported_return_terminator_records",
            "canonical_exact_pop_rdi_ret",
            "binary_fact_arg_control_rdi_present",
        ], f"unexpected normalized relation set for {tool_id}")
        artifact = build_artifact(
            context=context,
            row=row,
            authority_identity=authority_identity,
            adapter_identity=adapter_identity,
            baseline=baseline,
            version_identity=version_identity,
            stdout_identity=stdout_identity,
            stderr_identity=stderr_identity,
            command_cwd_identity=command_cwd_identity,
            records=records,
            ansi_count=ansi_count,
            ignored_line_count=ignored_count,
        )
        selected = [
            (tool["snapshot_path"], load_member(context.root_fd, context.root, tool["snapshot_path"], MAX_CAPTURE_BOUND, f"tool {tool_id} snapshot")[1], MAX_CAPTURE_BOUND, f"tool {tool_id} snapshot"),
            (target["snapshot_path"], load_member(context.root_fd, context.root, target["snapshot_path"], MAX_CAPTURE_BOUND, f"target {row['target_id']} snapshot")[1], MAX_CAPTURE_BOUND, f"target {row['target_id']} snapshot"),
            (tool["version_stdout_path"], version_identity, baseline["capture_policy"]["maximum_stdout_bytes"], f"tool {tool_id} version stdout"),
            (row["stdout_path"], stdout_identity, baseline["capture_policy"]["maximum_stdout_bytes"], f"row {row['run_id']} stdout"),
            (row["stderr_path"], stderr_identity, baseline["capture_policy"]["maximum_stderr_bytes"], f"row {row['run_id']} stderr"),
        ]
        return canonical_json_bytes(artifact), context, selected, authority_identity, adapter_identity
    except BaseException:
        context.close()
        raise


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-result", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-authority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    data, context, selected, authority_identity, adapter_identity = normalize(args)
    adapter_source = Path(__file__).resolve(strict=True)
    try:
        command_cwd_expected = directory_member_identity(context.root_fd, context.root, context.row(args.run_id)["command_cwd"], "row command cwd")

        def reauthenticate() -> None:
            context.reauthenticate(selected)
            require_directory_member_identity(context.root_fd, context.root, context.row(args.run_id)["command_cwd"], command_cwd_expected, "row command cwd")
            require_regular_path_identity(args.task_authority, authority_identity, MAX_JSON_BYTES, "task authority")
            require_regular_path_identity(adapter_source, adapter_identity, MAX_JSON_BYTES, "adapter source")

        atomic_publish_bytes(args.output, data, reauthenticate=reauthenticate)
        artifact = json.loads(data)
        metrics = artifact["metrics"]
        print(
            "baseline-output-adapter: ok "
            f"tool={artifact['tool']['id']} run_id={artifact['execution']['run_id']} "
            f"records={metrics['tool_native_record_count']} "
            f"return_records={metrics['tool_reported_return_terminator_record_count']} "
            f"pop_rdi_ret={metrics['canonical_exact_pop_rdi_ret_record_count']}"
        )
        return 0
    finally:
        context.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (AdapterError, ArtifactError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"baseline-output-adapter: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
