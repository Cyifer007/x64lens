#!/usr/bin/env python3
"""Validate x64lens JSON reports with only Python standard library.

Purpose:
    Provide a stronger smoke/regression check than `python3 -m json.tool`.
    This validator checks the report contract, metric boundaries, primitive
    coverage shape, gadget record shape, unknown stack-delta encoding, and the
    controlled fixture's exact expected semantic/scoring facts.

The script intentionally does not require jsonschema. It is designed to run in
minimal WSL, Docker, CI, and classroom environments.
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
REQUIRED_COUNTS = {
    "raw_candidate_count",
    "ret_count",
    "ret_imm16_count",
    "exact_pattern_count",
    "semantic_candidate_count",
    "unknown_candidate_count",
    "scored_candidate_count",
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


def validate_common(doc: dict[str, Any]) -> None:
    missing = REQUIRED_TOP - set(doc)
    require(not missing, f"missing top-level fields: {sorted(missing)}")

    require(doc["schema_version"] == "0.1.0", "unexpected schema_version")
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
        require(isinstance(mitigations[key], bool) or mitigations[key] is None, f"mitigations.{key} must be bool or null")
    require("relro" in mitigations, "mitigations.relro is missing")
    require(isinstance(mitigations["relro"], str), "mitigations.relro must be a string")
    require(mitigations["relro"] in {"none", "partial", "full"}, "mitigations.relro must be none, partial, or full")
    require("canary" in mitigations, "mitigations.canary is missing")
    require(isinstance(mitigations["canary"], str), "mitigations.canary must be a string")
    require(mitigations["canary"] in {"unknown", "absent", "present"}, "mitigations.canary must be unknown, absent, or present")
    if "stripped" in mitigations:
        require(isinstance(mitigations["stripped"], str), "mitigations.stripped must be a string")
        require(mitigations["stripped"] in {"unknown", "stripped", "not_stripped"}, "mitigations.stripped must be unknown, stripped, or not_stripped")

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

    coverage = doc["primitive_coverage"]
    require(isinstance(coverage, dict), "primitive_coverage must be an object")
    for key in ["arg_control", "syscall_num_control", "syscall_trigger", "stack_pivot", "alignment"]:
        require(isinstance(coverage.get(key), bool), f"primitive_coverage.{key} must be a boolean")
    registers = coverage.get("registers")
    require(isinstance(registers, list), "primitive_coverage.registers must be an array")
    require(len(registers) == len(set(registers)), "primitive_coverage.registers must not contain duplicates")
    for reg in registers:
        require(reg in ALLOWED_REGS, f"unknown register in primitive coverage: {reg}")

    gadgets = doc["gadgets"]
    require(isinstance(gadgets, list), "gadgets must be an array")
    require(len(gadgets) == counts["raw_candidate_count"], "gadgets length must match raw_candidate_count")

    semantic_seen = 0
    unknown_seen = 0
    scored_seen = 0
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
        require(gadget["terminator"] in ALLOWED_TERMINATORS, f"{prefix}.terminator is invalid")
        require(isinstance(gadget["pattern"], str) and gadget["pattern"], f"{prefix}.pattern must be a non-empty string")
        require(gadget["semantic_class"] in ALLOWED_SEMANTICS, f"{prefix}.semantic_class is invalid")
        require(isinstance(gadget["controls"], list), f"{prefix}.controls must be an array")
        require(len(gadget["controls"]) == len(set(gadget["controls"])), f"{prefix}.controls must not contain duplicates")
        for reg in gadget["controls"]:
            require(reg in ALLOWED_REGS, f"{prefix}.controls contains unknown register {reg}")

        known = gadget["stack_delta_known"]
        require(isinstance(known, bool), f"{prefix}.stack_delta_known must be a boolean")
        if known:
            require_int(gadget["stack_delta"], f"{prefix}.stack_delta")
        else:
            require(gadget["stack_delta"] is None, f"{prefix}.stack_delta must be null when stack_delta_known is false")

        score = gadget["score"]
        if score is None:
            require(gadget["semantic_class"] == "unknown_candidate", f"{prefix}.score may be null only for unknown_candidate in current schema")
        else:
            require_int(score, f"{prefix}.score")
            require(0 <= score <= 100, f"{prefix}.score must be between 0 and 100")
            scored_seen += 1

        if gadget["semantic_class"] == "unknown_candidate":
            unknown_seen += 1
        else:
            semantic_seen += 1

    require(semantic_seen == counts["semantic_candidate_count"], "semantic_candidate_count does not match gadget records")
    require(unknown_seen == counts["unknown_candidate_count"], "unknown_candidate_count does not match gadget records")
    require(scored_seen == counts["scored_candidate_count"], "scored_candidate_count does not match gadget records")

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
    args = parser.parse_args(argv)

    try:
        doc = load_report(args.json_report)
        validate_common(doc)
        if args.mode == "fixture":
            validate_fixture(doc)
    except ValidationError as exc:
        print(f"validate-json-report: error: {exc}", file=sys.stderr)
        return 1

    print(f"validate-json-report: ok ({args.mode}) {args.json_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
