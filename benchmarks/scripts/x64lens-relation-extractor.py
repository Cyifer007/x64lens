#!/usr/bin/env python3
"""Extract task-normalized x64lens relations from one authenticated runner row.

This development-only adapter consumes a retained schema 0.2.0 gadget report.
It preserves x64lens raw/exact/semantic facts and emits only the narrowly
reviewed exact ``pop rdi; ret`` relation with both virtual-address and file-
offset coordinates. It never scans target bytes, parses ELF, classifies, scores,
or changes the runtime report.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from diagnostic_artifact import (  # noqa: E402
    ArtifactError,
    MAX_JSON_BYTES,
    MAX_MEMBER_BYTES,
    atomic_publish_bytes,
    canonical_json_bytes,
    load_authority,
    load_campaign,
    load_regular_path,
    require,
    require_regular_path_identity,
    safe_id,
    sha256_bytes,
)

AUTHORITY_SCHEMA = 3
AUTHORITY_ID = "sprint11-diagnostic-task-definitions-v3"
EXTRACTOR_ID = "x64lens-sprint11-relation-extractor-v1"
ARTIFACT_SCHEMA = 1
HEX_ADDRESS = re.compile(r"^0x[0-9a-f]{16}$")
HEX_BYTES = re.compile(r"^[0-9a-f]+$")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-result", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-authority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def parse_hex_address(value: Any, label: str) -> int:
    require(isinstance(value, str) and HEX_ADDRESS.fullmatch(value) is not None, f"invalid {label}")
    return int(value, 16)


def format_address(value: int) -> str:
    require(0 <= value <= 0xFFFF_FFFF_FFFF_FFFF, "derived address is outside x86_64 range")
    return f"0x{value:016x}"


def parse_report(data: bytes) -> dict[str, Any]:
    require(len(data) <= MAX_JSON_BYTES, "x64lens report exceeds the JSON bound")
    try:
        report = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ArtifactError(f"cannot parse x64lens report: {exc}") from exc
    require(isinstance(report, dict), "x64lens report must be an object")
    require(report.get("schema_version") == "0.2.0", "x64lens report schema is not 0.2.0")
    require(report.get("tool") == "x64lens", "report is not an x64lens report")
    require(report.get("report_type") == "analysis", "x64lens report type changed")
    require(report.get("command") == "gadgets", "relation extraction requires a gadgets report")
    analysis = report.get("analysis")
    require(isinstance(analysis, dict) and analysis.get("complete") is True, "x64lens report is not complete")
    gadgets = report.get("gadgets")
    require(isinstance(gadgets, list), "x64lens gadget array is missing")
    return report


def relation_records(report: dict[str, Any]) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    for index, gadget in enumerate(report["gadgets"]):
        require(isinstance(gadget, dict), f"gadgets[{index}] is not an object")
        if gadget.get("pattern") != "pop rdi; ret":
            continue
        require(gadget.get("terminator") == "ret", f"gadgets[{index}] exact relation has a non-ret terminator")
        require(gadget.get("semantic_class") == "arg_control", f"gadgets[{index}] exact relation lost arg_control semantics")
        require(gadget.get("controls") == ["rdi"], f"gadgets[{index}] exact relation controls changed")
        evidence = gadget.get("evidence")
        require(isinstance(evidence, dict), f"gadgets[{index}] evidence is missing")
        require(
            evidence.get("kind") == "semantic_exact"
            and evidence.get("raw_candidate") is True
            and evidence.get("exact_suffix") is True
            and evidence.get("semantic_source") == "exact"
            and evidence.get("validator") == "x64lens-exact-suffix",
            f"gadgets[{index}] is not current semantic-exact suffix evidence",
        )
        suffix_offset = evidence.get("matched_suffix_offset")
        suffix_length = evidence.get("matched_suffix_length")
        require(isinstance(suffix_offset, int) and suffix_offset >= 0, f"gadgets[{index}] suffix offset is invalid")
        require(isinstance(suffix_length, int) and suffix_length == 2, f"gadgets[{index}] suffix length is not two bytes")
        bytes_text = gadget.get("bytes")
        require(isinstance(bytes_text, str) and len(bytes_text) % 2 == 0 and HEX_BYTES.fullmatch(bytes_text) is not None, f"gadgets[{index}] bytes are invalid")
        raw = bytes.fromhex(bytes_text)
        require(suffix_offset + suffix_length == len(raw), f"gadgets[{index}] exact suffix does not end at the candidate terminator")
        require(raw[suffix_offset:] == b"\x5f\xc3", f"gadgets[{index}] exact relation bytes changed")
        terminator_va = parse_hex_address(gadget.get("va"), f"gadgets[{index}].va")
        terminator_offset = parse_hex_address(gadget.get("file_offset"), f"gadgets[{index}].file_offset")
        start_va = terminator_va + 1 - suffix_length
        start_offset = terminator_offset + 1 - suffix_length
        require(start_va >= 0 and start_offset >= 0, f"gadgets[{index}] exact suffix underflowed its coordinates")
        relations.append(
            {
                "candidate_index": index,
                "relation_id": "canonical_exact_pop_rdi_ret",
                "canonical_instructions": ["pop rdi", "ret"],
                "native_pattern": gadget["pattern"],
                "suffix_bytes": "5fc3",
                "virtual_address_start": format_address(start_va),
                "virtual_address_terminator": format_address(terminator_va),
                "file_offset_start": format_address(start_offset),
                "file_offset_terminator": format_address(terminator_offset),
                "evidence_kind": evidence["kind"],
                "semantic_source": evidence["semantic_source"],
                "full_sequence_valid": evidence.get("full_sequence_valid"),
            }
        )
    return relations


def build_artifact(
    *,
    context,
    row: dict[str, str],
    report: dict[str, Any],
    report_identity: dict[str, Any],
    authority_identity: dict[str, Any],
    extractor_identity: dict[str, Any],
) -> dict[str, Any]:
    relations = relation_records(report)
    target = context.targets[row["target_id"]]
    tool = context.tools[row["tool_id"]]
    return {
        "schema_version": ARTIFACT_SCHEMA,
        "artifact_id": EXTRACTOR_ID,
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "campaign": {
            "campaign_id": context.manifest["campaign_id"],
            "manifest_sha256": context.manifest_identity["sha256"],
            "rows_sha256": context.rows_identity["sha256"],
            "run_id": row["run_id"],
            "phase": row["phase"],
            "condition_id": row["condition_id"],
            "task_scope": row["task_scope"],
            "profile_id": row["profile_id"],
            "command_json": row["command_json"],
            "command_cwd": row["command_cwd"],
        },
        "extractor": {
            "id": EXTRACTOR_ID,
            "sha256": extractor_identity["sha256"],
            "size_bytes": extractor_identity["size_bytes"],
        },
        "authority": {
            "id": AUTHORITY_ID,
            "sha256": authority_identity["sha256"],
            "size_bytes": authority_identity["size_bytes"],
        },
        "tool": {
            "id": row["tool_id"],
            "version": row["tool_version"],
            "sha256": tool["sha256"],
            "size_bytes": tool["size_bytes"],
        },
        "target": {
            "id": row["target_id"],
            "sha256": target["sha256"],
            "size_bytes": target["size_bytes"],
            "license": target["license"],
        },
        "native_report": {
            "relative_path": row["stdout_path"],
            "sha256": report_identity["sha256"],
            "size_bytes": report_identity["size_bytes"],
            "schema_version": report["schema_version"],
            "command": report["command"],
            "analysis_complete": report["analysis"]["complete"],
            "raw_candidate_count": report["counts"]["raw_candidate_count"],
            "exact_pattern_count": report["counts"]["exact_pattern_count"],
            "semantic_candidate_count": report["counts"]["semantic_candidate_count"],
            "unknown_candidate_count": report["counts"]["unknown_candidate_count"],
            "scored_candidate_count": report["counts"]["scored_candidate_count"],
        },
        "normalized_relations": relations,
        "metrics": {
            "canonical_exact_pop_rdi_ret_record_count": len(relations),
            "unique_canonical_exact_pop_rdi_ret_relation_count": len(
                {
                    (item["virtual_address_start"], item["virtual_address_terminator"], item["suffix_bytes"])
                    for item in relations
                }
            ),
            "binary_fact_arg_control_rdi_present": bool(relations),
        },
        "claim_boundaries": [
            "This artifact preserves one authenticated x64lens runner row and does not replace the native schema 0.2.0 report.",
            "The relation is semantic-exact suffix evidence; full instruction-sequence validity remains unknown.",
            "Virtual-address and file-offset coordinates are both retained until target-role calibration selects a comparison coordinate.",
            "No generic cross-tool gadget count is produced.",
        ],
    }


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    safe_id(args.run_id, "run id")
    authority, authority_identity, _raw = load_authority(
        args.task_authority,
        schema_version=AUTHORITY_SCHEMA,
        authority_id=AUTHORITY_ID,
    )
    policy = authority.get("x64lens_relation_policy")
    require(isinstance(policy, dict), "x64lens relation policy is missing")
    require(policy.get("extractor_id") == EXTRACTOR_ID, "x64lens relation extractor identity is not authorized")
    require(policy.get("extractor_path") == "benchmarks/scripts/x64lens-relation-extractor.py", "x64lens relation extractor path changed")
    require(policy.get("artifact_schema_version") == ARTIFACT_SCHEMA, "x64lens relation artifact schema changed")
    require(policy.get("runner_extractor") == "x64lens_json_0_2", "x64lens runner extractor authority changed")
    require(policy.get("report_schema_version") == "0.2.0" and policy.get("report_command") == "gadgets", "x64lens report authority changed")
    extractor_path = Path(__file__).resolve(strict=True)
    expected_extractor_path = Path(os.path.abspath(args.task_authority)).parent.parent.parent / policy["extractor_path"]
    # The normal authority is repository-relative. Resolve it from repository root rather than trusting caller cwd.
    repository_root = Path(os.path.abspath(args.task_authority)).parent.parent.parent
    expected_extractor_path = (repository_root / policy["extractor_path"]).resolve(strict=True)
    require(extractor_path == expected_extractor_path, "running x64lens relation extractor does not match authority-declared path")
    _extractor_data, extractor_identity = load_regular_path(extractor_path, MAX_MEMBER_BYTES, "x64lens relation extractor")

    context = load_campaign(args.campaign_result)
    try:
        row = context.row(args.run_id)
        require(row.get("phase") == "measured", "x64lens relation extraction requires a measured runner row")
        require(row.get("extractor") == policy["runner_extractor"], "runner row extractor does not match x64lens relation authority")
        require(row.get("schema_version") == policy["report_schema_version"], "runner row schema does not match x64lens relation authority")
        require(row.get("report_command") == policy["report_command"], "runner row command does not match x64lens relation authority")
        require(row.get("process_outcome") == "success" and row.get("outcome") == "success", "runner row is not successful")
        require(row.get("analysis_complete") == "true", "runner row analysis is not complete")
        report_data, report_identity = context.load_row_member(row, "stdout")
        stderr_data, stderr_identity = context.load_row_member(row, "stderr")
        require(not stderr_data, "successful x64lens relation row retained nonempty stderr")
        report = parse_report(report_data)
        require(report.get("tool_version") == row["tool_version"], "x64lens report version does not match runner row")
        artifact = build_artifact(
            context=context,
            row=row,
            report=report,
            report_identity=report_identity,
            authority_identity=authority_identity,
            extractor_identity=extractor_identity,
        )
        selected = [
            (row["stdout_path"], report_identity, int(row["stdout_limit_bytes"]), f"row {row['run_id']} stdout"),
            (row["stderr_path"], stderr_identity, int(row["stderr_limit_bytes"]), f"row {row['run_id']} stderr"),
        ]

        def reauthenticate() -> None:
            context.reauthenticate(selected)
            require_regular_path_identity(args.task_authority, authority_identity, MAX_JSON_BYTES, "task authority")
            require_regular_path_identity(extractor_path, extractor_identity, MAX_MEMBER_BYTES, "x64lens relation extractor")

        output_bytes = canonical_json_bytes(artifact)
        atomic_publish_bytes(args.output, output_bytes, reauthenticate=reauthenticate)
    finally:
        context.close()
    print(
        "x64lens-relation-extractor: ok "
        f"run={args.run_id} relations={artifact['metrics']['canonical_exact_pop_rdi_ret_record_count']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (ArtifactError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"x64lens-relation-extractor: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
