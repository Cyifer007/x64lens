#!/usr/bin/env python3
"""Exercise current per-candidate semantic and architectural-effect relations."""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "tools" / "validate-json-report.py"
EXPECTED = ROOT / "tests" / "expected"


def fail(message: str) -> "NoReturn":
    print(f"json-effect-consistency-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot load {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path} must contain an object")
    return value


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("x64lens_validate_json_report", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        fail(f"cannot import {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


V = load_validator()


def validate(doc: dict[str, Any]) -> None:
    V.validate_common(
        doc,
        required_schema="0.2.0",
        expected_command="gadgets",
        require_provenance=True,
        require_sprint10_effects=True,
        require_sprint10_transfer=True,
        require_sprint10_memory=True,
        require_sprint10_architectural_effects=True,
    )


def expect_reject(name: str, document: dict[str, Any]) -> None:
    try:
        validate(document)
    except V.ValidationError:
        return
    fail(f"negative case {name} was accepted")


def mutate(base: dict[str, Any], selector: Callable[[dict[str, Any]], bool], change: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    document = copy.deepcopy(base)
    gadget = next((item for item in document["gadgets"] if selector(item)), None)
    if gadget is None:
        fail("mutation selector did not find a candidate")
    change(gadget)
    return document


def main() -> int:
    reports = {
        "current": load(EXPECTED / "x64lens-report-0.2.0.json"),
        "multi": load(EXPECTED / "x64lens-report-sprint10-0.2.0.json"),
        "transfer": load(EXPECTED / "x64lens-report-sprint10-transfer-0.2.0.json"),
        "stack": load(EXPECTED / "x64lens-report-sprint10-stack-adjust-0.2.0.json"),
        "memory": load(EXPECTED / "x64lens-report-sprint10-memory-0.2.0.json"),
        "effects": load(EXPECTED / "x64lens-report-sprint10-effects-0.2.0.json"),
    }
    for name, report in reports.items():
        try:
            validate(report)
        except V.ValidationError as exc:
            fail(f"positive report {name} rejected: {exc}")

    single_pop_rejections = 0
    effects = reports["effects"]
    single_pops = [g for g in effects["gadgets"] if g["pattern"] in V.SINGLE_POP_REG_BY_PATTERN]
    if len(single_pops) != 16:
        fail(f"expected 16 exact single-pop records, got {len(single_pops)}")
    for source in single_pops:
        reg = V.SINGLE_POP_REG_BY_PATTERN[source["pattern"]]
        wrong = "rsi" if reg != "rsi" else "rdi"
        document = copy.deepcopy(effects)
        gadget = next(g for g in document["gadgets"] if g["pattern"] == source["pattern"])
        if gadget["controls"]:
            gadget["controls"] = [wrong]
            document["primitive_coverage"]["registers"] = V.ordered_registers(
                {item for candidate in document["gadgets"] for item in candidate["controls"]}
            )
        else:
            gadget["stack_pop_order"] = [wrong]
        expect_reject(f"single-pop-{reg}", document)
        single_pop_rejections += 1

    multi_rejections = 0
    for index, gadget in enumerate(reports["multi"]["gadgets"]):
        if gadget["pattern"] != V.MULTI_POP_PATTERN:
            continue
        document = copy.deepcopy(reports["multi"])
        document["gadgets"][index]["stack_pop_order"] = list(reversed(gadget["stack_pop_order"]))
        expect_reject(f"multi-order-{index}", document)
        multi_rejections += 1

    ret_rejections = 0
    for field, value in (
        ("terminator", "unknown"),
        ("stack_delta", 24),
        ("side_effects", []),
        ("architectural_effects", None),
    ):
        document = copy.deepcopy(reports["current"])
        document["gadgets"][0][field] = value
        expect_reject(f"ret-{field}", document)
        ret_rejections += 1

    current_family_rejections = 0
    for pattern in ("leave; ret", "syscall; ret", "pop rsp; ret"):
        document = mutate(effects, lambda g, p=pattern: g["pattern"] == p, lambda g: g["side_effects"].remove("control_transfer"))
        expect_reject(f"{pattern}-control-transfer", document)
        current_family_rejections += 1
        document = mutate(effects, lambda g, p=pattern: g["pattern"] == p, lambda g: g["architectural_effects"].update({"model_complete": not g["architectural_effects"]["model_complete"]}))
        expect_reject(f"{pattern}-model-complete", document)
        current_family_rejections += 1

    stack_rejections = 0
    for index, gadget in enumerate(reports["stack"]["gadgets"]):
        if gadget["pattern"] != V.STACK_ADJUST_PATTERN:
            continue
        document = copy.deepcopy(reports["stack"])
        document["gadgets"][index]["stack_delta"] += 8
        expect_reject(f"stack-delta-{index}", document)
        stack_rejections += 1
        document = copy.deepcopy(reports["stack"])
        document["gadgets"][index]["architectural_effects"]["flags_written"] = []
        expect_reject(f"stack-flags-{index}", document)
        stack_rejections += 1

    memory_rejections = 0
    for direction, pattern in (("write", V.MEMORY_WRITE_PATTERN), ("read", V.MEMORY_READ_PATTERN)):
        document = mutate(reports["memory"], lambda g, p=pattern: g["pattern"] == p, lambda g: g["memory_access"].update({"base": "rsi"}))
        expect_reject(f"memory-{direction}-base", document)
        memory_rejections += 1
        document = mutate(reports["memory"], lambda g, p=pattern: g["pattern"] == p, lambda g: g["architectural_effects"].update({"registers_read": ["rsp"]}))
        expect_reject(f"memory-{direction}-architectural-read", document)
        memory_rejections += 1
        document = mutate(reports["memory"], lambda g, p=pattern: g["pattern"] == p, lambda g: g.update({"score": 50}))
        document["counts"]["scored_candidate_count"] += 1
        expect_reject(f"memory-{direction}-score", document)
        memory_rejections += 1

    arch_rejections = 0
    arch_mutations = (
        (0, "registers_read", ["rbx"]),
        (0, "first_stack_read_offset", 8),
        (5, "architectural_effects", None),
        (6, "stack_offsets_known", True),
        (19, "control_flow", ["return"]),
        (20, "stack_read_count", 2),
        (21, "registers_written", ["rsp"]),
        (22, "flags_written", []),
    )
    for index, field, value in arch_mutations:
        document = copy.deepcopy(effects)
        if field == "architectural_effects":
            document["gadgets"][index][field] = value
        else:
            document["gadgets"][index]["architectural_effects"][field] = value
        expect_reject(f"arch-{index}-{field}", document)
        arch_rejections += 1

    print(
        "json-effect-consistency-smoke: ok "
        f"positive_reports={len(reports)} single_pop_rejections={single_pop_rejections} "
        f"multi_rejections={multi_rejections} bare_ret_rejections={ret_rejections} "
        f"current_family_rejections={current_family_rejections} "
        f"stack_adjust_rejections={stack_rejections} memory_rejections={memory_rejections} "
        f"architectural_effect_rejections={arch_rejections}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
