#!/usr/bin/env python3
"""Exercise current-producer register-effect relations independently of runtime fixtures.

This validator-only smoke closes the Patch 046 review gap by proving that all
16 exact single-pop patterns have canonical per-candidate controls/order facts.
It also covers mixed legacy/REX ordered two-pop forms, bare-ret relational
invariants found during Patch 047 review, and the bounded Patch 048 stack-adjust
family, and the bounded Patch 049 memory-effect family so aggregate coverage
cannot conceal contradictory candidate facts.
"""

from __future__ import annotations

import argparse
import copy
import json
import importlib.util
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate-json-report.py"
BASE_REPORT = ROOT / "tests" / "expected" / "x64lens-report-0.2.0.json"

REG_ORDER = [
    "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
]
ARG_REGS = {"rdi", "rsi", "rdx", "rcx", "r8", "r9"}
POP_BYTES = {
    "rax": "58", "rcx": "59", "rdx": "5a", "rbx": "5b",
    "rsp": "5c", "rbp": "5d", "rsi": "5e", "rdi": "5f",
    "r8": "4158", "r9": "4159", "r10": "415a", "r11": "415b",
    "r12": "415c", "r13": "415d", "r14": "415e", "r15": "415f",
}


def fail(message: str) -> None:
    print(f"json-effect-consistency-smoke: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_base() -> dict[str, Any]:
    try:
        doc = json.loads(BASE_REPORT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot load {BASE_REPORT}: {exc}")
    if not isinstance(doc, dict):
        fail("base report is not an object")
    return doc


def set_one_candidate_counts(doc: dict[str, Any], *, semantic: bool, scored: bool) -> None:
    doc["analysis"]["candidate_count"] = 1
    doc["counts"].update(
        {
            "raw_candidate_count": 1,
            "ret_count": 1,
            "ret_imm16_count": 0,
            "exact_pattern_count": 1,
            "semantic_candidate_count": 1 if semantic else 0,
            "unknown_candidate_count": 0 if semantic else 1,
            "scored_candidate_count": 1 if scored else 0,
        }
    )


def coverage_for(semantic: str, controls: list[str]) -> dict[str, Any]:
    return {
        "arg_control": semantic == "arg_control",
        "syscall_num_control": semantic == "syscall_num_control",
        "syscall_trigger": False,
        "stack_pivot": semantic == "stack_pivot",
        "alignment": False,
        "reg_transfer": False,
        "memory_write": semantic == "memory_write",
        "memory_read": semantic == "memory_read",
        "registers": [reg for reg in REG_ORDER if reg in controls],
    }


def single_pop_document(base: dict[str, Any], reg: str) -> dict[str, Any]:
    doc = copy.deepcopy(base)
    gadget = doc["gadgets"][0]
    known = reg in ARG_REGS or reg in {"rax", "rsp"}
    scored = known

    if reg in ARG_REGS:
        semantic = "arg_control"
        controls = [reg]
        stack_delta: int | None = 16
        stack_known = True
        effects = ["stack_read"]
        score: int | None = 90
    elif reg == "rax":
        semantic = "syscall_num_control"
        controls = [reg]
        stack_delta = 16
        stack_known = True
        effects = ["stack_read"]
        score = 85
    elif reg == "rsp":
        semantic = "stack_pivot"
        controls = [reg]
        stack_delta = None
        stack_known = False
        effects = ["stack_read", "stack_pivot"]
        score = 70
    else:
        semantic = "unknown_candidate"
        controls = []
        stack_delta = None
        stack_known = False
        effects = []
        score = None

    bytes_hex = f"{POP_BYTES[reg]}c3"
    suffix_len = len(bytes.fromhex(bytes_hex))
    gadget.update(
        {
            "bytes": bytes_hex,
            "pattern": f"pop {reg}; ret",
            "semantic_class": semantic,
            "controls": controls,
            "stack_pop_order": [reg],
            "register_transfer": None,
            "memory_access": None,
            "clobbers": [],
            "side_effects": effects,
            "stack_delta": stack_delta,
            "stack_delta_known": stack_known,
            "score": score,
            "evidence": {
                "kind": "semantic_exact" if known else "exact_suffix",
                "raw_candidate": True,
                "exact_suffix": True,
                "semantic_source": "exact" if known else None,
                "validator": "x64lens-exact-suffix",
                "matched_suffix_offset": 0,
                "matched_suffix_length": suffix_len,
                "full_sequence_valid": None,
            },
        }
    )
    set_one_candidate_counts(doc, semantic=known, scored=scored)
    doc["primitive_coverage"] = coverage_for(semantic, controls)
    doc["target"]["path"] = f"validator-single-pop-{reg}"
    doc["target"]["file_size"] = suffix_len
    return doc


def mixed_multi_pop_document(base: dict[str, Any], first: str, second: str) -> dict[str, Any]:
    doc = copy.deepcopy(base)
    gadget = doc["gadgets"][0]
    bytes_hex = f"{POP_BYTES[first]}{POP_BYTES[second]}c3"
    suffix_len = len(bytes.fromhex(bytes_hex))
    controls = [reg for reg in REG_ORDER if reg in {first, second}]
    gadget.update(
        {
            "bytes": bytes_hex,
            "pattern": "pop reg; pop reg; ret",
            "semantic_class": "arg_control",
            "controls": controls,
            "stack_pop_order": [first, second],
            "register_transfer": None,
            "memory_access": None,
            "clobbers": [],
            "side_effects": ["stack_read"],
            "stack_delta": 24,
            "stack_delta_known": True,
            "score": None,
            "evidence": {
                "kind": "semantic_exact",
                "raw_candidate": True,
                "exact_suffix": True,
                "semantic_source": "exact",
                "validator": "x64lens-exact-suffix",
                "matched_suffix_offset": 0,
                "matched_suffix_length": suffix_len,
                "full_sequence_valid": None,
            },
        }
    )
    set_one_candidate_counts(doc, semantic=True, scored=False)
    doc["primitive_coverage"] = coverage_for("arg_control", controls)
    doc["target"]["path"] = f"validator-mixed-pop-{first}-{second}"
    doc["target"]["file_size"] = suffix_len
    return doc


def stack_adjust_document(base: dict[str, Any], immediate: int) -> dict[str, Any]:
    doc = copy.deepcopy(base)
    gadget = doc["gadgets"][0]
    bytes_hex = f"4883c4{immediate:02x}c3"
    gadget.update(
        {
            "bytes": bytes_hex,
            "pattern": "add rsp, imm8; ret",
            "semantic_class": "alignment",
            "controls": [],
            "stack_pop_order": [],
            "register_transfer": None,
            "memory_access": None,
            "clobbers": [],
            "side_effects": ["stack_adjust", "flags_write"],
            "stack_delta": immediate + 8,
            "stack_delta_known": True,
            "score": None,
            "evidence": {
                "kind": "semantic_exact",
                "raw_candidate": True,
                "exact_suffix": True,
                "semantic_source": "exact",
                "validator": "x64lens-exact-suffix",
                "matched_suffix_offset": 0,
                "matched_suffix_length": 5,
                "full_sequence_valid": None,
            },
        }
    )
    set_one_candidate_counts(doc, semantic=True, scored=False)
    doc["primitive_coverage"] = coverage_for("alignment", [])
    doc["primitive_coverage"]["alignment"] = True
    doc["target"]["path"] = f"validator-stack-adjust-{immediate}"
    doc["target"]["file_size"] = 5
    return doc



def memory_document(base: dict[str, Any], *, direction: str, base_reg: str, value_reg: str) -> dict[str, Any]:
    doc = copy.deepcopy(base)
    gadget = doc["gadgets"][0]
    reg_encoding = {name: index for index, name in enumerate((
        "rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi",
        "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
    ))}
    base_id = reg_encoding[base_reg]
    value_id = reg_encoding[value_reg]
    rex = 0x48 | (0x01 if base_id >= 8 else 0) | (0x04 if value_id >= 8 else 0)
    modrm = ((value_id & 7) << 3) | (base_id & 7)
    opcode = 0x89 if direction == "write" else 0x8B
    bytes_hex = bytes((rex, opcode, modrm, 0xC3)).hex()
    semantic = "memory_write" if direction == "write" else "memory_read"
    pattern = "mov [base], value; ret" if direction == "write" else "mov value, [base]; ret"
    clobbers = [] if direction == "write" else [value_reg]
    effects = ["memory_write"] if direction == "write" else ["register_write", "memory_read"]
    gadget.update(
        {
            "bytes": bytes_hex,
            "pattern": pattern,
            "semantic_class": semantic,
            "controls": [],
            "stack_pop_order": [],
            "register_transfer": None,
            "memory_access": {
                "direction": direction,
                "base": base_reg,
                "index": None,
                "scale": 1,
                "displacement": 0,
                "displacement_known": True,
                "width_bytes": 8,
                "value_register": value_reg,
                "dereference": True,
            },
            "clobbers": clobbers,
            "side_effects": effects,
            "stack_delta": 8,
            "stack_delta_known": True,
            "score": None,
            "evidence": {
                "kind": "semantic_exact",
                "raw_candidate": True,
                "exact_suffix": True,
                "semantic_source": "exact",
                "validator": "x64lens-exact-suffix",
                "matched_suffix_offset": 0,
                "matched_suffix_length": 4,
                "full_sequence_valid": None,
            },
        }
    )
    set_one_candidate_counts(doc, semantic=True, scored=False)
    doc["primitive_coverage"] = coverage_for(semantic, [])
    doc["target"]["path"] = f"validator-memory-{direction}-{base_reg}-{value_reg}"
    doc["target"]["file_size"] = 4
    return doc

def load_validator_module() -> Any:
    spec = importlib.util.spec_from_file_location("x64lens_validate_json_report", VALIDATOR)
    if spec is None or spec.loader is None:
        fail(f"cannot import validator from {VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validator(module: Any, path: Path, *, expect_success: bool) -> None:
    try:
        document = module.load_report(path)
        module.validate_common(
            document,
            required_schema="0.2.0",
            expected_command="gadgets",
            require_provenance=True,
            require_sprint10_effects=True,
            require_sprint10_transfer=True,
            require_sprint10_memory=True,
        )
    except module.ValidationError as exc:
        if expect_success:
            fail(f"positive case {path.name} rejected: {exc}")
        return
    if not expect_success:
        fail(f"negative case {path.name} was accepted")


def write_case(directory: Path, name: str, document: dict[str, Any]) -> Path:
    path = directory / f"{name}.json"
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    base = load_base()
    validator = load_validator_module()
    single_positive = 0
    single_negative = 0
    mixed_positive = 0
    mixed_negative = 0
    bare_ret_negative = 0
    stack_adjust_positive = 0
    stack_adjust_negative = 0
    memory_positive = 0
    memory_negative = 0

    with tempfile.TemporaryDirectory(prefix="x64lens-json-effect-") as temp:
        directory = Path(temp)

        for reg in POP_BYTES:
            document = single_pop_document(base, reg)
            path = write_case(directory, f"single-{reg}-positive", document)
            run_validator(validator, path, expect_success=True)
            single_positive += 1

            mutation = copy.deepcopy(document)
            gadget = mutation["gadgets"][0]
            wrong = "rsi" if reg != "rsi" else "rdi"
            gadget["controls"] = [wrong]
            mutation["primitive_coverage"]["registers"] = [wrong]
            negative = write_case(directory, f"single-{reg}-controls-mismatch", mutation)
            run_validator(validator, negative, expect_success=False)
            single_negative += 1

        mixed_pairs = [("rdi", "r8"), ("r8", "rdi"), ("rsi", "r9"), ("r9", "rdx")]
        for first, second in mixed_pairs:
            document = mixed_multi_pop_document(base, first, second)
            path = write_case(directory, f"mixed-{first}-{second}-positive", document)
            run_validator(validator, path, expect_success=True)
            mixed_positive += 1

            mutation = copy.deepcopy(document)
            mutation["gadgets"][0]["stack_pop_order"] = [second, first]
            negative = write_case(directory, f"mixed-{first}-{second}-order-mismatch", mutation)
            run_validator(validator, negative, expect_success=False)
            mixed_negative += 1

        # Patch 047 review regressions: generic validation must not accept a
        # recognized bare ret with contradictory terminator, controls, or stack
        # delta simply because aggregate counts still reconcile.
        bare_ret = copy.deepcopy(base)
        bare_mutations = []

        mutation = copy.deepcopy(bare_ret)
        mutation["gadgets"][0]["terminator"] = "unknown"
        bare_mutations.append(("bare-ret-unknown-terminator", mutation))

        mutation = copy.deepcopy(bare_ret)
        mutation["gadgets"][0]["controls"] = ["rdi"]
        mutation["primitive_coverage"]["registers"] = ["rdi"]
        bare_mutations.append(("bare-ret-controls", mutation))

        mutation = copy.deepcopy(bare_ret)
        mutation["gadgets"][0]["stack_delta"] = 24
        bare_mutations.append(("bare-ret-stack-delta", mutation))

        for name, mutation in bare_mutations:
            path = write_case(directory, name, mutation)
            run_validator(validator, path, expect_success=False)
            bare_ret_negative += 1

        for immediate in (8, 32):
            document = stack_adjust_document(base, immediate)
            path = write_case(directory, f"stack-adjust-{immediate}-positive", document)
            run_validator(validator, path, expect_success=True)
            stack_adjust_positive += 1

            mutation = copy.deepcopy(document)
            mutation["gadgets"][0]["stack_delta"] += 8
            negative = write_case(directory, f"stack-adjust-{immediate}-delta-mismatch", mutation)
            run_validator(validator, negative, expect_success=False)
            stack_adjust_negative += 1

        mutation = stack_adjust_document(base, 8)
        mutation["gadgets"][0]["bytes"] = "4883c407c3"
        negative = write_case(directory, "stack-adjust-unaligned-immediate", mutation)
        run_validator(validator, negative, expect_success=False)
        stack_adjust_negative += 1

        mutation = stack_adjust_document(base, 8)
        mutation["gadgets"][0]["side_effects"] = []
        negative = write_case(directory, "stack-adjust-missing-effect", mutation)
        run_validator(validator, negative, expect_success=False)
        stack_adjust_negative += 1

        for direction, base_reg, value_reg in (("write", "rdi", "rax"), ("read", "r8", "r9")):
            document = memory_document(base, direction=direction, base_reg=base_reg, value_reg=value_reg)
            path = write_case(directory, f"memory-{direction}-positive", document)
            run_validator(validator, path, expect_success=True)
            memory_positive += 1

            mutations = []
            mutation = copy.deepcopy(document)
            mutation["gadgets"][0]["memory_access"]["direction"] = "read" if direction == "write" else "write"
            mutations.append(("direction", mutation))

            mutation = copy.deepcopy(document)
            mutation["gadgets"][0]["memory_access"]["base"] = "rsi"
            mutations.append(("base", mutation))

            mutation = copy.deepcopy(document)
            mutation["gadgets"][0]["memory_access"]["value_register"] = "rdx"
            mutations.append(("value", mutation))

            mutation = copy.deepcopy(document)
            mutation["gadgets"][0]["memory_access"]["displacement"] = 8
            mutations.append(("displacement", mutation))

            mutation = copy.deepcopy(document)
            mutation["gadgets"][0]["memory_access"] = None
            mutations.append(("missing", mutation))

            mutation = copy.deepcopy(document)
            mutation["gadgets"][0]["side_effects"] = []
            mutations.append(("effects", mutation))

            for suffix, mutation in mutations:
                negative = write_case(directory, f"memory-{direction}-{suffix}-mismatch", mutation)
                run_validator(validator, negative, expect_success=False)
                memory_negative += 1

    print(
        "json-effect-consistency-smoke: ok "
        f"single_pop={single_positive} "
        f"single_pop_rejections={single_negative} "
        f"mixed_multi_pop={mixed_positive} "
        f"mixed_rejections={mixed_negative} "
        f"bare_ret_rejections={bare_ret_negative} "
        f"stack_adjust={stack_adjust_positive} "
        f"stack_adjust_rejections={stack_adjust_negative} "
        f"memory={memory_positive} "
        f"memory_rejections={memory_negative}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
