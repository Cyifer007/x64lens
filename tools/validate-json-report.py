#!/usr/bin/env python3
"""Validate x64lens JSON reports with only Python standard library.

Purpose:
    Provide a stronger smoke/regression check than `python3 -m json.tool`.
    This validator checks schema-aware report identity, bounded analysis
    completeness, metric boundaries, primitive coverage shape, gadget record
    shape, unknown stack-delta encoding, and controlled fixture facts. It keeps
    representative schema 0.1.0 reports consumable while validating current
    producer output against schema 0.2.0 invariants and candidate provenance.

The script intentionally does not require jsonschema. Formal Draft 2020-12
schema validation is a separate development gate; this validator is normative
for arithmetic and property-to-property relationships JSON Schema cannot
express directly.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HEX64_RE = re.compile(r"^0x[0-9a-fA-F]{16}$")
HEX_BYTES_RE = re.compile(r"^(?:[0-9a-fA-F]{2})*$")

ALLOWED_TERMINATORS = {"ret", "ret imm16", "unknown"}
ALLOWED_SEMANTICS = {
    "unknown_candidate",
    "arg_control",
    "syscall_num_control",
    "syscall_trigger",
    "stack_pivot",
    "memory_write",
    "memory_read",
    "reg_transfer",
    "alignment",
    "clobber_heavy",
}
ALLOWED_REGS = {
    "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
}
SUPPORTED_SCHEMAS = {"0.1.0", "0.2.0"}
ALLOWED_COMMANDS = {"gadgets", "analyze"}
ALLOWED_EVIDENCE_KINDS = {
    "raw_only",
    "exact_suffix",
    "semantic_exact",
    "decoder_validated",
    "semantic_decoded",
}
ALLOWED_EVIDENCE_VALIDATORS = {
    "x64lens-raw-scanner",
    "x64lens-exact-suffix",
    "x64lens-decoder",
}
PATTERN_SUFFIX_LENGTHS = {
    "ret": 1,
    "ret imm16": 3,
    "pop rax; ret": 2,
    "pop rcx; ret": 2,
    "pop rdx; ret": 2,
    "pop rbx; ret": 2,
    "pop rsp; ret": 2,
    "pop rbp; ret": 2,
    "pop rsi; ret": 2,
    "pop rdi; ret": 2,
    "pop r8; ret": 3,
    "pop r9; ret": 3,
    "pop r10; ret": 3,
    "pop r11; ret": 3,
    "pop r12; ret": 3,
    "pop r13; ret": 3,
    "pop r14; ret": 3,
    "pop r15; ret": 3,
    "leave; ret": 2,
    "syscall; ret": 3,
}
COVERAGE_CLASS_MAP = {
    "arg_control": "arg_control",
    "syscall_num_control": "syscall_num_control",
    "syscall_trigger": "syscall_trigger",
    "stack_pivot": "stack_pivot",
    "alignment": "alignment",
}
REQUIRED_TOP = {
    "schema_version",
    "tool",
    "tool_version",
    "target",
    "mitigations",
    "counts",
    "primitive_coverage",
    "gadgets",
    "limitations",
}
REQUIRED_TOP_V2 = {"report_type", "command", "analysis"}
REQUIRED_ANALYSIS_FIELDS = {
    "complete",
    "max_depth",
    "candidate_capacity",
    "candidate_count",
    "candidate_truncated",
    "candidate_dropped_count",
    "candidate_dropped_count_known",
    "regions_scanned",
    "regions_total",
}
REQUIRED_COUNTS = {
    "raw_candidate_count",
    "ret_count",
    "ret_imm16_count",
    "exact_pattern_count",
    "semantic_candidate_count",
    "unknown_candidate_count",
    "scored_candidate_count",
}
REQUIRED_EVIDENCE_FIELDS = {
    "kind",
    "raw_candidate",
    "exact_suffix",
    "semantic_source",
    "validator",
    "matched_suffix_offset",
    "matched_suffix_length",
    "full_sequence_valid",
}
REQUIRED_GADGET_FIELDS = {
    "va",
    "file_offset",
    "bytes",
    "terminator",
    "pattern",
    "semantic_class",
    "controls",
    "stack_delta",
    "stack_delta_known",
    "score",
}


class ValidationError(Exception):
    """Raised when a JSON report violates the x64lens output contract."""


def fail(message: str) -> None:
    raise ValidationError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def require_int(value: Any, name: str, *, min_value: int = 0) -> None:
    require(isinstance(value, int) and not isinstance(value, bool), f"{name} must be an integer")
    require(value >= min_value, f"{name} must be >= {min_value}")


def require_bool(value: Any, name: str) -> None:
    require(isinstance(value, bool), f"{name} must be a boolean")


def require_hex64(value: Any, name: str) -> None:
    require(isinstance(value, str) and HEX64_RE.match(value) is not None, f"{name} must be a 16-digit hex string")


def load_report(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            doc = json.load(f)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON: {exc}")
    require(isinstance(doc, dict), "report root must be an object")
    return doc


def validate_common(
    doc: dict[str, Any],
    *,
    required_schema: str | None = None,
    expected_command: str | None = None,
    require_provenance: bool = False,
) -> None:
    missing = REQUIRED_TOP - set(doc)
    require(not missing, f"missing top-level fields: {sorted(missing)}")

    schema_version = doc.get("schema_version")
    require(
        isinstance(schema_version, str) and schema_version in SUPPORTED_SCHEMAS,
        f"unsupported schema_version: {schema_version!r}",
    )
    if required_schema is not None:
        require(schema_version == required_schema, f"expected schema_version {required_schema}, got {schema_version}")

    if schema_version == "0.2.0":
        missing_v2 = REQUIRED_TOP_V2 - set(doc)
        require(not missing_v2, f"missing schema 0.2.0 fields: {sorted(missing_v2)}")
        require(doc["report_type"] == "analysis", "report_type must be analysis")
        require(
            isinstance(doc["command"], str) and doc["command"] in ALLOWED_COMMANDS,
            "command must be gadgets or analyze",
        )
        if expected_command is not None:
            require(doc["command"] == expected_command, f"expected command {expected_command}, got {doc['command']}")
    else:
        require(expected_command is None, "command identity requires schema 0.2.0")
        require(not require_provenance, "candidate provenance requires schema 0.2.0")

    require(doc["tool"] == "x64lens", "unexpected tool value")
    require(isinstance(doc["tool_version"], str) and doc["tool_version"], "tool_version must be a non-empty string")

    target = doc["target"]
    require(isinstance(target, dict), "target must be an object")
    require(isinstance(target.get("path"), str) and target["path"], "target.path must be a non-empty string")
    require(target.get("format") == "ELF64", "target.format must be ELF64")
    require(target.get("arch") == "x86_64", "target.arch must be x86_64")
    require_int(target.get("file_size"), "target.file_size", min_value=1)
    require_hex64(target.get("entry"), "target.entry")

    mitigations = doc["mitigations"]
    require(isinstance(mitigations, dict), "mitigations must be an object")
    for key in ["nx_stack", "pie", "rwx_load_segment", "dynamic_linking"]:
        require(key in mitigations, f"mitigations.{key} is missing")
        if schema_version == "0.2.0" and key != "nx_stack":
            require_bool(mitigations[key], f"mitigations.{key}")
        else:
            require(
                isinstance(mitigations[key], bool) or mitigations[key] is None,
                f"mitigations.{key} must be bool or null",
            )
    require("relro" in mitigations, "mitigations.relro is missing")
    require(isinstance(mitigations["relro"], str), "mitigations.relro must be a string")
    require(mitigations["relro"] in {"none", "partial", "full"}, "mitigations.relro must be none, partial, or full")
    require("canary" in mitigations, "mitigations.canary is missing")
    require(isinstance(mitigations["canary"], str), "mitigations.canary must be a string")
    require(mitigations["canary"] in {"unknown", "absent", "present"}, "mitigations.canary must be unknown, absent, or present")
    if "stripped" in mitigations:
        require(isinstance(mitigations["stripped"], str), "mitigations.stripped must be a string")
        require(mitigations["stripped"] in {"unknown", "stripped", "not_stripped"}, "mitigations.stripped must be unknown, stripped, or not_stripped")

    if schema_version == "0.2.0":
        for key in ["bind_now", "dynamic_entry_count", "dynamic_terminated"]:
            require(key in mitigations, f"mitigations.{key} is missing for schema 0.2.0")

    if "bind_now" in mitigations:
        require(isinstance(mitigations["bind_now"], bool) or mitigations["bind_now"] is None, "mitigations.bind_now must be bool or null")
    if "dynamic_terminated" in mitigations:
        require(isinstance(mitigations["dynamic_terminated"], bool) or mitigations["dynamic_terminated"] is None, "mitigations.dynamic_terminated must be bool or null")
    if "dynamic_entry_count" in mitigations:
        require_int(mitigations["dynamic_entry_count"], "mitigations.dynamic_entry_count")
    if mitigations.get("dynamic_linking") is False:
        if "bind_now" in mitigations:
            require(mitigations["bind_now"] is None, "mitigations.bind_now must be null when dynamic_linking is false")
        if "dynamic_terminated" in mitigations:
            require(mitigations["dynamic_terminated"] is None, "mitigations.dynamic_terminated must be null when dynamic_linking is false")
        if "dynamic_entry_count" in mitigations:
            require(mitigations["dynamic_entry_count"] == 0, "mitigations.dynamic_entry_count must be 0 when dynamic_linking is false")
    if mitigations.get("relro") == "full":
        require(mitigations.get("dynamic_linking") is True, "mitigations.relro full requires dynamic_linking true")
        require(mitigations.get("bind_now") is True, "mitigations.relro full requires bind_now true")

    counts = doc["counts"]
    require(isinstance(counts, dict), "counts must be an object")
    missing_counts = REQUIRED_COUNTS - set(counts)
    require(not missing_counts, f"missing count fields: {sorted(missing_counts)}")
    for key in REQUIRED_COUNTS:
        require_int(counts[key], f"counts.{key}")

    require(counts["ret_count"] + counts["ret_imm16_count"] == counts["raw_candidate_count"], "ret counts must sum to raw_candidate_count")
    require(counts["exact_pattern_count"] <= counts["raw_candidate_count"], "exact_pattern_count exceeds raw_candidate_count")
    require(counts["semantic_candidate_count"] + counts["unknown_candidate_count"] == counts["raw_candidate_count"], "semantic + unknown counts must equal raw count")
    require(counts["scored_candidate_count"] <= counts["semantic_candidate_count"], "scored_candidate_count exceeds semantic_candidate_count")

    if schema_version == "0.2.0":
        analysis = doc["analysis"]
        require(isinstance(analysis, dict), "analysis must be an object")
        missing_analysis = REQUIRED_ANALYSIS_FIELDS - set(analysis)
        require(not missing_analysis, f"missing analysis fields: {sorted(missing_analysis)}")

        require_bool(analysis["complete"], "analysis.complete")
        require_int(analysis["max_depth"], "analysis.max_depth", min_value=1)
        require(analysis["max_depth"] <= 32, "analysis.max_depth must be <= 32")
        require_int(analysis["candidate_capacity"], "analysis.candidate_capacity", min_value=1)
        require_int(analysis["candidate_count"], "analysis.candidate_count")
        require_bool(analysis["candidate_truncated"], "analysis.candidate_truncated")
        require_bool(analysis["candidate_dropped_count_known"], "analysis.candidate_dropped_count_known")
        require_int(analysis["regions_scanned"], "analysis.regions_scanned")
        require_int(analysis["regions_total"], "analysis.regions_total")

        require(
            analysis["candidate_count"] <= analysis["candidate_capacity"],
            "analysis.candidate_count exceeds candidate_capacity",
        )
        require(
            analysis["candidate_count"] == counts["raw_candidate_count"],
            "analysis.candidate_count must equal counts.raw_candidate_count",
        )
        require(
            analysis["regions_scanned"] <= analysis["regions_total"],
            "analysis.regions_scanned exceeds regions_total",
        )

        if analysis["candidate_dropped_count_known"]:
            require_int(analysis["candidate_dropped_count"], "analysis.candidate_dropped_count")
        else:
            require(
                analysis["candidate_dropped_count"] is None,
                "analysis.candidate_dropped_count must be null when unknown",
            )

        if analysis["candidate_truncated"]:
            require(analysis["complete"] is False, "truncated analysis cannot be complete")
        if analysis["complete"]:
            require(analysis["candidate_truncated"] is False, "complete analysis cannot be truncated")
            require(
                analysis["candidate_dropped_count_known"] is True,
                "complete analysis requires a known dropped count",
            )
            require(
                analysis["candidate_dropped_count"] == 0,
                "complete analysis requires candidate_dropped_count 0",
            )
            require(
                analysis["regions_scanned"] == analysis["regions_total"],
                "complete analysis requires all regions scanned",
            )

        # Schema 0.2.0 currently represents only successfully emitted complete
        # reports. An intentional partial-report mode requires a documented
        # schema transition rather than silently widening this contract.
        require(analysis["complete"] is True, "schema 0.2.0 reports must be complete")
        require(analysis["candidate_truncated"] is False, "schema 0.2.0 reports must not be truncated")
        require(analysis["candidate_dropped_count_known"] is True, "schema 0.2.0 dropped count must be known")
        require(analysis["candidate_dropped_count"] == 0, "schema 0.2.0 dropped count must be 0")

    coverage = doc["primitive_coverage"]
    require(isinstance(coverage, dict), "primitive_coverage must be an object")
    for key in ["arg_control", "syscall_num_control", "syscall_trigger", "stack_pivot", "alignment"]:
        require(isinstance(coverage.get(key), bool), f"primitive_coverage.{key} must be a boolean")
    registers = coverage.get("registers")
    require(isinstance(registers, list), "primitive_coverage.registers must be an array")
    for reg in registers:
        require(
            isinstance(reg, str) and reg in ALLOWED_REGS,
            f"unknown register in primitive coverage: {reg}",
        )
    require(len(registers) == len(set(registers)), "primitive_coverage.registers must not contain duplicates")

    gadgets = doc["gadgets"]
    require(isinstance(gadgets, list), "gadgets must be an array")
    require(len(gadgets) == counts["raw_candidate_count"], "gadgets length must match raw_candidate_count")

    semantic_seen = 0
    unknown_seen = 0
    scored_seen = 0
    exact_seen = 0
    provenance_seen = 0
    controlled_registers_seen: set[str] = set()
    semantic_classes_seen: set[str] = set()
    for idx, gadget in enumerate(gadgets):
        prefix = f"gadgets[{idx}]"
        require(isinstance(gadget, dict), f"{prefix} must be an object")
        missing_gadget = REQUIRED_GADGET_FIELDS - set(gadget)
        require(not missing_gadget, f"{prefix} missing fields: {sorted(missing_gadget)}")

        if "section" in gadget:
            require(gadget["section"] is None or isinstance(gadget["section"], str), f"{prefix}.section must be a string or null")

        require_hex64(gadget["va"], f"{prefix}.va")
        require_hex64(gadget["file_offset"], f"{prefix}.file_offset")
        require(isinstance(gadget["bytes"], str) and HEX_BYTES_RE.match(gadget["bytes"]) is not None and gadget["bytes"], f"{prefix}.bytes must be a non-empty compact hex string")
        require(
            isinstance(gadget["terminator"], str)
            and gadget["terminator"] in ALLOWED_TERMINATORS,
            f"{prefix}.terminator is invalid",
        )
        require(isinstance(gadget["pattern"], str) and gadget["pattern"], f"{prefix}.pattern must be a non-empty string")
        require(
            isinstance(gadget["semantic_class"], str)
            and gadget["semantic_class"] in ALLOWED_SEMANTICS,
            f"{prefix}.semantic_class is invalid",
        )
        semantic_classes_seen.add(gadget["semantic_class"])

        pattern_is_exact = gadget["pattern"] != "unknown"
        if pattern_is_exact:
            exact_seen += 1

        if require_provenance:
            require("evidence" in gadget, f"{prefix}.evidence is required for current-producer validation")
        if "evidence" in gadget:
            provenance_seen += 1
            evidence = gadget["evidence"]
            require(isinstance(evidence, dict), f"{prefix}.evidence must be an object")
            missing_evidence = REQUIRED_EVIDENCE_FIELDS - set(evidence)
            require(not missing_evidence, f"{prefix}.evidence missing fields: {sorted(missing_evidence)}")
            require(
                isinstance(evidence["kind"], str)
                and evidence["kind"] in ALLOWED_EVIDENCE_KINDS,
                f"{prefix}.evidence.kind is invalid",
            )
            require(evidence["raw_candidate"] is True, f"{prefix}.evidence.raw_candidate must be true")
            require_bool(evidence["exact_suffix"], f"{prefix}.evidence.exact_suffix")
            require(
                evidence["semantic_source"] is None
                or (
                    isinstance(evidence["semantic_source"], str)
                    and evidence["semantic_source"] in {"exact", "decoded"}
                ),
                f"{prefix}.evidence.semantic_source is invalid",
            )
            require(
                isinstance(evidence["validator"], str)
                and evidence["validator"] in ALLOWED_EVIDENCE_VALIDATORS,
                f"{prefix}.evidence.validator is invalid",
            )
            require(
                evidence["full_sequence_valid"] is None
                or isinstance(evidence["full_sequence_valid"], bool),
                f"{prefix}.evidence.full_sequence_valid must be bool or null",
            )
            require(
                evidence["exact_suffix"] is pattern_is_exact,
                f"{prefix}.evidence.exact_suffix must agree with pattern identity",
            )

            raw_byte_len = len(gadget["bytes"]) // 2
            if evidence["exact_suffix"]:
                require_int(evidence["matched_suffix_offset"], f"{prefix}.evidence.matched_suffix_offset")
                require_int(
                    evidence["matched_suffix_length"],
                    f"{prefix}.evidence.matched_suffix_length",
                    min_value=1,
                )
                expected_suffix_len = PATTERN_SUFFIX_LENGTHS.get(gadget["pattern"])
                require(expected_suffix_len is not None, f"{prefix}.pattern has no suffix-length contract")
                require(
                    evidence["matched_suffix_length"] == expected_suffix_len,
                    f"{prefix}.evidence.matched_suffix_length disagrees with pattern",
                )
                require(
                    evidence["matched_suffix_offset"] + evidence["matched_suffix_length"] == raw_byte_len,
                    f"{prefix}.evidence suffix must end at the retained candidate terminator",
                )
            else:
                require(
                    evidence["matched_suffix_offset"] is None,
                    f"{prefix}.evidence.matched_suffix_offset must be null without exact suffix",
                )
                require(
                    evidence["matched_suffix_length"] is None,
                    f"{prefix}.evidence.matched_suffix_length must be null without exact suffix",
                )

            semantic_is_known = gadget["semantic_class"] != "unknown_candidate"
            if semantic_is_known:
                require(
                    evidence["semantic_source"] in {"exact", "decoded"},
                    f"{prefix}.evidence.semantic_source must justify a known semantic class",
                )
            else:
                require(
                    evidence["semantic_source"] is None,
                    f"{prefix}.evidence.semantic_source must be null for unknown candidates",
                )

            kind = evidence["kind"]
            if kind == "raw_only":
                require(not evidence["exact_suffix"], f"{prefix}.raw_only cannot carry exact suffix evidence")
                require(evidence["semantic_source"] is None, f"{prefix}.raw_only semantic source must be null")
                require(evidence["validator"] == "x64lens-raw-scanner", f"{prefix}.raw_only validator mismatch")
                require(evidence["full_sequence_valid"] is None, f"{prefix}.raw_only validity must be unknown")
            elif kind == "exact_suffix":
                require(evidence["exact_suffix"], f"{prefix}.exact_suffix kind requires exact evidence")
                require(evidence["semantic_source"] is None, f"{prefix}.exact_suffix semantic source must be null")
                require(evidence["validator"] == "x64lens-exact-suffix", f"{prefix}.exact_suffix validator mismatch")
                require(evidence["full_sequence_valid"] is None, f"{prefix}.exact_suffix validity must be unknown")
            elif kind == "semantic_exact":
                require(evidence["exact_suffix"], f"{prefix}.semantic_exact requires exact evidence")
                require(evidence["semantic_source"] == "exact", f"{prefix}.semantic_exact source mismatch")
                require(evidence["validator"] == "x64lens-exact-suffix", f"{prefix}.semantic_exact validator mismatch")
                require(evidence["full_sequence_valid"] is None, f"{prefix}.semantic_exact validity must be unknown")
            elif kind == "decoder_validated":
                require(evidence["validator"] == "x64lens-decoder", f"{prefix}.decoder_validated validator mismatch")
                require(isinstance(evidence["full_sequence_valid"], bool), f"{prefix}.decoder_validated requires a boolean validity")
            elif kind == "semantic_decoded":
                require(evidence["semantic_source"] == "decoded", f"{prefix}.semantic_decoded source mismatch")
                require(evidence["validator"] == "x64lens-decoder", f"{prefix}.semantic_decoded validator mismatch")
                require(evidence["full_sequence_valid"] is True, f"{prefix}.semantic_decoded requires valid full sequence")

        require(isinstance(gadget["controls"], list), f"{prefix}.controls must be an array")
        for reg in gadget["controls"]:
            require(
                isinstance(reg, str) and reg in ALLOWED_REGS,
                f"{prefix}.controls contains unknown register {reg}",
            )
            controlled_registers_seen.add(reg)
        require(
            len(gadget["controls"]) == len(set(gadget["controls"])),
            f"{prefix}.controls must not contain duplicates",
        )

        known = gadget["stack_delta_known"]
        require(isinstance(known, bool), f"{prefix}.stack_delta_known must be a boolean")
        if known:
            require_int(gadget["stack_delta"], f"{prefix}.stack_delta")
        else:
            require(gadget["stack_delta"] is None, f"{prefix}.stack_delta must be null when stack_delta_known is false")

        score = gadget["score"]
        if score is not None:
            require(
                gadget["semantic_class"] != "unknown_candidate",
                f"{prefix}.unknown_candidate must remain unscored",
            )
            require_int(score, f"{prefix}.score")
            require(0 <= score <= 100, f"{prefix}.score must be between 0 and 100")
            scored_seen += 1

        if gadget["semantic_class"] == "unknown_candidate":
            unknown_seen += 1
        else:
            semantic_seen += 1

    require(exact_seen == counts["exact_pattern_count"], "exact_pattern_count does not match gadget records")
    require(semantic_seen == counts["semantic_candidate_count"], "semantic_candidate_count does not match gadget records")
    require(unknown_seen == counts["unknown_candidate_count"], "unknown_candidate_count does not match gadget records")
    require(scored_seen == counts["scored_candidate_count"], "scored_candidate_count does not match gadget records")
    require(
        set(registers) == controlled_registers_seen,
        "primitive_coverage.registers must equal the union of gadget controls",
    )
    for coverage_key, semantic_class in COVERAGE_CLASS_MAP.items():
        expected = semantic_class in semantic_classes_seen
        require(
            coverage[coverage_key] is expected,
            f"primitive_coverage.{coverage_key} disagrees with gadget semantic classes",
        )
    if provenance_seen:
        require(provenance_seen == len(gadgets), "candidate evidence must be present for all gadgets or none")

    limitations = doc["limitations"]
    require(isinstance(limitations, list) and limitations, "limitations must be a non-empty array")
    for item in limitations:
        require(isinstance(item, str) and item, "limitations entries must be non-empty strings")


def validate_fixture(doc: dict[str, Any]) -> None:
    counts = doc["counts"]
    expected_counts = {
        "raw_candidate_count": 11,
        "ret_count": 10,
        "ret_imm16_count": 1,
        "exact_pattern_count": 11,
        "semantic_candidate_count": 11,
        "unknown_candidate_count": 0,
        "scored_candidate_count": 11,
    }
    for key, value in expected_counts.items():
        require(counts[key] == value, f"fixture {key} expected {value}, got {counts[key]}")

    coverage = doc["primitive_coverage"]
    for key in ["arg_control", "syscall_num_control", "syscall_trigger", "stack_pivot", "alignment"]:
        require(coverage[key] is True, f"fixture primitive coverage {key} must be true")
    for reg in ["rax", "rcx", "rdx", "rsi", "rdi", "rsp", "r8", "r9"]:
        require(reg in coverage["registers"], f"fixture coverage missing register {reg}")

    if all("section" in g for g in doc["gadgets"]):
        for gadget in doc["gadgets"]:
            require(gadget["section"] == ".text", "fixture gadget section labels must be .text when emitted")

    if doc["schema_version"] == "0.2.0":
        analysis = doc["analysis"]
        require(analysis["complete"] is True, "fixture analysis must be complete")
        require(analysis["max_depth"] == 4, "fixture analysis.max_depth must be 4")
        require(analysis["candidate_capacity"] == 4096, "fixture candidate capacity must be 4096")
        require(analysis["candidate_count"] == 11, "fixture analysis candidate count must be 11")
        require(analysis["candidate_truncated"] is False, "fixture analysis must not be truncated")
        require(analysis["candidate_dropped_count"] == 0, "fixture dropped count must be 0")
        require(analysis["candidate_dropped_count_known"] is True, "fixture dropped count must be known")
        require(analysis["regions_scanned"] == analysis["regions_total"], "fixture must scan all regions")
        if all("evidence" in g for g in doc["gadgets"]):
            for idx, gadget in enumerate(doc["gadgets"]):
                evidence = gadget["evidence"]
                require(evidence["kind"] == "semantic_exact", f"fixture gadgets[{idx}] evidence kind must be semantic_exact")
                require(evidence["semantic_source"] == "exact", f"fixture gadgets[{idx}] semantic source must be exact")
                require(evidence["validator"] == "x64lens-exact-suffix", f"fixture gadgets[{idx}] validator mismatch")
                require(evidence["full_sequence_valid"] is None, f"fixture gadgets[{idx}] full-sequence validity must be unknown")

    by_pattern = {g["pattern"]: g for g in doc["gadgets"]}
    required_patterns = [
        "pop rdi; ret",
        "pop rsi; ret",
        "pop rdx; ret",
        "pop rcx; ret",
        "pop r8; ret",
        "pop r9; ret",
        "pop rax; ret",
        "pop rsp; ret",
        "leave; ret",
        "syscall; ret",
        "ret imm16",
    ]
    for pattern in required_patterns:
        require(pattern in by_pattern, f"fixture missing pattern {pattern}")

    for pattern, reg in [
        ("pop rdi; ret", "rdi"),
        ("pop rsi; ret", "rsi"),
        ("pop rdx; ret", "rdx"),
        ("pop rcx; ret", "rcx"),
        ("pop r8; ret", "r8"),
        ("pop r9; ret", "r9"),
    ]:
        g = by_pattern[pattern]
        require(g["semantic_class"] == "arg_control", f"{pattern} semantic class mismatch")
        require(g["controls"] == [reg], f"{pattern} controls mismatch")
        require(g["stack_delta"] == 16 and g["stack_delta_known"] is True, f"{pattern} stack delta mismatch")
        require(g["score"] == 90, f"{pattern} score mismatch")

    g = by_pattern["pop rax; ret"]
    require(g["semantic_class"] == "syscall_num_control", "pop rax semantic class mismatch")
    require(g["controls"] == ["rax"], "pop rax controls mismatch")
    require(g["score"] == 85, "pop rax score mismatch")

    g = by_pattern["pop rsp; ret"]
    require(g["semantic_class"] == "stack_pivot", "pop rsp semantic class mismatch")
    require(g["controls"] == ["rsp"], "pop rsp controls mismatch")
    require(g["stack_delta"] is None and g["stack_delta_known"] is False, "pop rsp stack delta uncertainty mismatch")
    require(g["score"] == 70, "pop rsp score mismatch")

    g = by_pattern["leave; ret"]
    require(g["semantic_class"] == "stack_pivot", "leave semantic class mismatch")
    require(g["controls"] == ["rsp"], "leave controls mismatch")
    require(g["stack_delta"] is None and g["stack_delta_known"] is False, "leave stack delta uncertainty mismatch")
    require(g["score"] == 75, "leave score mismatch")

    g = by_pattern["syscall; ret"]
    require(g["semantic_class"] == "syscall_trigger", "syscall semantic class mismatch")
    require(g["controls"] == [], "syscall controls mismatch")
    require(g["stack_delta"] == 8 and g["stack_delta_known"] is True, "syscall stack delta mismatch")
    require(g["score"] == 85, "syscall score mismatch")

    g = by_pattern["ret imm16"]
    require(g["semantic_class"] == "alignment", "ret imm16 semantic class mismatch")
    require(g["controls"] == [], "ret imm16 controls mismatch")
    require(g["stack_delta"] == 24 and g["stack_delta_known"] is True, "ret imm16 stack delta mismatch")
    require(g["score"] == 40, "ret imm16 score mismatch")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate x64lens JSON report shape and invariants.")
    parser.add_argument("json_report", type=Path)
    parser.add_argument("--mode", choices=["generic", "fixture", "system"], default="generic")
    parser.add_argument("--require-schema", choices=sorted(SUPPORTED_SCHEMAS))
    parser.add_argument("--expected-command", choices=sorted(ALLOWED_COMMANDS))
    parser.add_argument(
        "--require-provenance",
        action="store_true",
        help="require every schema 0.2.0 gadget to carry current-producer evidence",
    )
    args = parser.parse_args(argv)

    try:
        doc = load_report(args.json_report)
        validate_common(
            doc,
            required_schema=args.require_schema,
            expected_command=args.expected_command,
            require_provenance=args.require_provenance,
        )
        if args.mode == "fixture":
            validate_fixture(doc)
    except ValidationError as exc:
        print(f"validate-json-report: error: {exc}", file=sys.stderr)
        return 1

    print(
        f"validate-json-report: ok ({args.mode}, schema={doc['schema_version']}) "
        f"{args.json_report}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
