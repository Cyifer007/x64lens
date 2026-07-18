#!/usr/bin/env python3
"""Validate historical compatibility and current x64lens schema semantics.

Purpose:
    Apply the formal Draft 2020-12 schemas to retained reports, then exercise
    the bundled semantic validator for arithmetic and property-to-property
    invariants that JSON Schema cannot express. This is a development and CI
    dependency only; x64lens itself remains dependency-free at runtime.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - exercised by tool checks
    print(
        "schema-compat-smoke: error: Python jsonschema is required "
        "(Ubuntu package: python3-jsonschema)",
        file=sys.stderr,
    )
    raise SystemExit(127) from exc

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_VALIDATOR = ROOT / "tools" / "validate-json-report.py"
LEGACY_SCHEMA_PATH = ROOT / "schemas" / "x64lens-report-0.1.0.schema.json"
CURRENT_SCHEMA_PATH = ROOT / "schemas" / "x64lens-report.schema.json"
LEGACY_REPORT_PATH = ROOT / "tests" / "expected" / "x64lens-report-0.1.0.json"
PATCH040_REPORT_PATH = ROOT / "tests" / "expected" / "x64lens-report-0.2.0-p040.json"
PATCH046_REPORT_PATH = ROOT / "tests" / "expected" / "x64lens-report-0.2.0-p046.json"
CURRENT_REPORT_PATH = ROOT / "tests" / "expected" / "x64lens-report-0.2.0.json"
SPRINT10_REPORT_PATH = ROOT / "tests" / "expected" / "x64lens-report-sprint10-0.2.0.json"
SPRINT10_TRANSFER_REPORT_PATH = ROOT / "tests" / "expected" / "x64lens-report-sprint10-transfer-0.2.0.json"
SPRINT10_STACK_ADJUST_REPORT_PATH = ROOT / "tests" / "expected" / "x64lens-report-sprint10-stack-adjust-0.2.0.json"
SPRINT10_MEMORY_REPORT_PATH = ROOT / "tests" / "expected" / "x64lens-report-sprint10-memory-0.2.0.json"


def load_custom_validator() -> Any:
    spec = importlib.util.spec_from_file_location("x64lens_validate_json_report", CUSTOM_VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import validator from {CUSTOM_VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CUSTOM_VALIDATOR_MODULE = load_custom_validator()


class SmokeError(RuntimeError):
    """Raised when a compatibility or rejection expectation is not met."""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict):
        raise SmokeError(f"{path} must contain a JSON object")
    return document


def formal_validator(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def formal_errors(validator: Draft202012Validator, document: dict[str, Any]) -> list[str]:
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    return [error.message for error in errors]


def require_formal_accept(
    validator: Draft202012Validator,
    name: str,
    document: dict[str, Any],
) -> None:
    errors = formal_errors(validator, document)
    if errors:
        raise SmokeError(f"formal schema unexpectedly rejected {name}: {errors[0]}")


def require_formal_reject(
    validator: Draft202012Validator,
    name: str,
    document: dict[str, Any],
) -> None:
    if not formal_errors(validator, document):
        raise SmokeError(f"formal schema unexpectedly accepted {name}")


def write_document(directory: Path, name: str, document: dict[str, Any]) -> Path:
    path = directory / name
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def run_custom(
    path: Path,
    *args: str,
    expect_success: bool,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        status = CUSTOM_VALIDATOR_MODULE.main([*args, str(path)])
    if expect_success and status != 0:
        raise SmokeError(
            f"custom validator unexpectedly rejected {path.name}: {stderr.getvalue().strip()}"
        )
    if not expect_success and status == 0:
        raise SmokeError(f"custom validator unexpectedly accepted {path.name}")


def main() -> int:
    legacy_schema = formal_validator(LEGACY_SCHEMA_PATH)
    current_schema = formal_validator(CURRENT_SCHEMA_PATH)

    legacy = load_json(LEGACY_REPORT_PATH)
    patch040 = load_json(PATCH040_REPORT_PATH)
    patch046 = load_json(PATCH046_REPORT_PATH)
    current = load_json(CURRENT_REPORT_PATH)
    sprint10 = load_json(SPRINT10_REPORT_PATH)
    sprint10_transfer = load_json(SPRINT10_TRANSFER_REPORT_PATH)
    sprint10_stack_adjust = load_json(SPRINT10_STACK_ADJUST_REPORT_PATH)
    sprint10_memory = load_json(SPRINT10_MEMORY_REPORT_PATH)

    # Historical 0.1.0 reports, Patch 040's initial 0.2.0 shape, and the current
    # provenance-bearing producer shape all remain consumable.
    require_formal_accept(legacy_schema, "legacy-0.1.0", legacy)
    require_formal_accept(current_schema, "patch040-0.2.0", patch040)
    require_formal_accept(current_schema, "patch046-0.2.0", patch046)
    require_formal_accept(current_schema, "current-0.2.0", current)
    require_formal_accept(current_schema, "sprint10-0.2.0", sprint10)
    require_formal_accept(current_schema, "sprint10-transfer-0.2.0", sprint10_transfer)
    require_formal_accept(current_schema, "sprint10-stack-adjust-0.2.0", sprint10_stack_adjust)
    require_formal_accept(current_schema, "sprint10-memory-0.2.0", sprint10_memory)

    run_custom(LEGACY_REPORT_PATH, "--require-schema", "0.1.0", expect_success=True)
    run_custom(
        PATCH040_REPORT_PATH,
        "--require-schema",
        "0.2.0",
        "--expected-command",
        "gadgets",
        expect_success=True,
    )
    run_custom(
        CURRENT_REPORT_PATH,
        "--require-schema",
        "0.2.0",
        "--expected-command",
        "gadgets",
        "--require-provenance",
        "--require-sprint10-effects",
        "--require-sprint10-transfer",
        "--require-sprint10-memory",
        expect_success=True,
    )
    run_custom(
        PATCH046_REPORT_PATH,
        "--require-schema",
        "0.2.0",
        "--expected-command",
        "gadgets",
        "--require-provenance",
        "--require-sprint10-effects",
        expect_success=True,
    )
    run_custom(
        SPRINT10_REPORT_PATH,
        "--mode",
        "sprint10-fixture",
        "--require-schema",
        "0.2.0",
        "--expected-command",
        "gadgets",
        "--require-provenance",
        "--require-sprint10-effects",
        "--require-sprint10-memory",
        expect_success=True,
    )
    run_custom(
        SPRINT10_TRANSFER_REPORT_PATH,
        "--mode",
        "sprint10-transfer-fixture",
        "--require-schema",
        "0.2.0",
        "--expected-command",
        "gadgets",
        "--require-provenance",
        "--require-sprint10-effects",
        "--require-sprint10-transfer",
        "--require-sprint10-memory",
        expect_success=True,
    )
    run_custom(
        SPRINT10_STACK_ADJUST_REPORT_PATH,
        "--mode",
        "sprint10-stack-adjust-fixture",
        "--require-schema",
        "0.2.0",
        "--expected-command",
        "gadgets",
        "--require-provenance",
        "--require-sprint10-effects",
        "--require-sprint10-transfer",
        "--require-sprint10-memory",
        expect_success=True,
    )
    run_custom(
        SPRINT10_MEMORY_REPORT_PATH,
        "--mode",
        "sprint10-memory-fixture",
        "--require-schema",
        "0.2.0",
        "--expected-command",
        "gadgets",
        "--require-provenance",
        "--require-sprint10-effects",
        "--require-sprint10-transfer",
        "--require-sprint10-memory",
        expect_success=True,
    )

    formal_rejections = 0
    semantic_rejections = 0
    with tempfile.TemporaryDirectory(prefix="x64lens-schema-compat-") as temp:
        directory = Path(temp)

        # These mutations are expressible in Draft 2020-12 and must be rejected
        # by the formal current schema.
        formal_cases: list[tuple[str, dict[str, Any]]] = []

        mutation = deepcopy(current)
        mutation["analysis"]["complete"] = False
        formal_cases.append(("incomplete-current-report", mutation))

        mutation = deepcopy(current)
        mutation["analysis"]["candidate_truncated"] = True
        formal_cases.append(("truncated-current-report", mutation))

        mutation = deepcopy(current)
        mutation["mitigations"]["pie"] = None
        formal_cases.append(("current-pie-null", mutation))

        mutation = deepcopy(current)
        del mutation["mitigations"]["dynamic_entry_count"]
        formal_cases.append(("current-dynamic-triplet-missing", mutation))

        mutation = deepcopy(current)
        mutation["limitations"] = []
        formal_cases.append(("empty-limitations", mutation))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["evidence"]["kind"] = "raw_only"
        formal_cases.append(("contradictory-evidence-kind", mutation))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["evidence"]["matched_suffix_length"] = None
        formal_cases.append(("missing-exact-suffix-length", mutation))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["bytes"] = "zz"
        formal_cases.append(("nonhex-candidate-bytes", mutation))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["controls"] = ["rip"]
        formal_cases.append(("unknown-controlled-register", mutation))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["controls"] = ["rdi", "rdi"]
        formal_cases.append(("duplicate-controlled-register", mutation))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["stack_delta_known"] = False
        mutation["gadgets"][0]["stack_delta"] = 8
        formal_cases.append(("unknown-stack-delta-has-number", mutation))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["score"] = 101
        formal_cases.append(("score-above-range", mutation))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["semantic_class"] = "unknown_candidate"
        formal_cases.append(("unknown-candidate-is-scored", mutation))

        mutation = deepcopy(sprint10_transfer)
        mutation["gadgets"][0]["register_transfer"]["source"] = "rip"
        formal_cases.append(("unknown-transfer-register", mutation))

        mutation = deepcopy(sprint10_transfer)
        mutation["gadgets"][0]["side_effects"] = ["memory_execute"]
        formal_cases.append(("unknown-side-effect", mutation))

        mutation = deepcopy(sprint10_memory)
        mutation["gadgets"][0]["memory_access"]["base"] = "rip"
        formal_cases.append(("unknown-memory-base", mutation))

        mutation = deepcopy(sprint10_memory)
        mutation["gadgets"][0]["memory_access"]["scale"] = 3
        formal_cases.append(("invalid-memory-scale", mutation))

        for name, document in formal_cases:
            require_formal_reject(current_schema, name, document)
            formal_rejections += 1

        # These relationships span sibling properties or emitted arrays. The
        # formal schema accepts their individual types; the custom validator is
        # deliberately normative for the combined invariant.
        semantic_cases: list[tuple[str, dict[str, Any], tuple[str, ...]]] = []

        mutation = deepcopy(current)
        mutation["analysis"]["candidate_count"] = 0
        semantic_cases.append(("analysis-count-disagrees", mutation, ("--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(current)
        mutation["analysis"]["regions_scanned"] = 2
        semantic_cases.append(("region-overrun", mutation, ("--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(current)
        mutation["primitive_coverage"]["alignment"] = False
        semantic_cases.append(("coverage-class-disagrees", mutation, ("--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(current)
        mutation["counts"]["exact_pattern_count"] = 0
        semantic_cases.append(("exact-count-disagrees", mutation, ("--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["evidence"]["matched_suffix_offset"] = 1
        semantic_cases.append(("suffix-range-disagrees", mutation, ("--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10)
        mutation["gadgets"][0]["stack_pop_order"] = ["rsi", "rdi"]
        semantic_cases.append(("multi-pop-order-disagrees-with-bytes", mutation, ("--mode", "sprint10-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10)
        mutation["gadgets"][0]["controls"] = ["rdi"]
        semantic_cases.append(("multi-pop-controls-disagree", mutation, ("--mode", "sprint10-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10)
        mutation["gadgets"][0]["side_effects"] = ["stack_read", "syscall"]
        semantic_cases.append(("multi-pop-side-effects-disagree", mutation, ("--mode", "sprint10-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10)
        mutation["gadgets"][0]["score"] = 90
        mutation["counts"]["scored_candidate_count"] = 3
        semantic_cases.append(("multi-pop-premature-score", mutation, ("--mode", "sprint10-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10)
        mutation["gadgets"][0]["clobbers"] = ["rax"]
        semantic_cases.append(("unsupported-clobber-fact", mutation, ("--mode", "sprint10-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-memory",)))

        # Patch 046 review regression: controls and coverage cannot be rewritten
        # independently from an exact single-pop pattern and its ordered fact.
        mutation = deepcopy(current)
        pop = next(g for g in mutation["gadgets"] if g["pattern"] == "ret")
        # The one-record generic fixture cannot exercise the pop relation, so use
        # the retained Sprint 10 fixture's first single-pop fallback instead.
        mutation = deepcopy(sprint10)
        pop = next(g for g in mutation["gadgets"] if g["pattern"] == "pop rdi; ret")
        pop["controls"] = ["rsi"]
        mutation["primitive_coverage"]["registers"] = sorted(
            {reg for gadget in mutation["gadgets"] for reg in gadget["controls"]}
        )
        semantic_cases.append(("single-pop-controls-disagree", mutation, ("--mode", "sprint10-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_transfer)
        mutation["gadgets"][0]["register_transfer"] = {"source": "rax", "destination": "rsi"}
        semantic_cases.append(("transfer-relation-disagrees-with-bytes", mutation, ("--mode", "sprint10-transfer-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_transfer)
        mutation["gadgets"][0]["clobbers"] = ["rsi"]
        semantic_cases.append(("transfer-clobber-disagrees", mutation, ("--mode", "sprint10-transfer-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_transfer)
        mutation["gadgets"][0]["side_effects"] = []
        semantic_cases.append(("transfer-side-effect-missing", mutation, ("--mode", "sprint10-transfer-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_transfer)
        mutation["primitive_coverage"]["reg_transfer"] = False
        semantic_cases.append(("transfer-coverage-disagrees", mutation, ("--mode", "sprint10-transfer-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_transfer)
        mutation["gadgets"][4]["register_transfer"] = {"source": "rax", "destination": "rdi"}
        semantic_cases.append(("non-transfer-carries-transfer-relation", mutation, ("--mode", "sprint10-transfer-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        # Patch 047 review regressions: exact bare-ret facts must agree per
        # candidate even when aggregate counts and register coverage are edited
        # to remain superficially consistent.
        mutation = deepcopy(current)
        mutation["gadgets"][0]["terminator"] = "unknown"
        semantic_cases.append(("ret-terminator-disagrees", mutation, ("--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["controls"] = ["rdi"]
        mutation["primitive_coverage"]["registers"] = ["rdi"]
        semantic_cases.append(("ret-controls-disagree", mutation, ("--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(current)
        mutation["gadgets"][0]["stack_delta"] = 24
        semantic_cases.append(("ret-stack-delta-disagrees", mutation, ("--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_stack_adjust)
        mutation["gadgets"][0]["stack_delta"] = 24
        semantic_cases.append(("stack-adjust-delta-disagrees", mutation, ("--mode", "sprint10-stack-adjust-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_stack_adjust)
        mutation["gadgets"][0]["bytes"] = "4883c407c3"
        semantic_cases.append(("stack-adjust-immediate-disagrees", mutation, ("--mode", "sprint10-stack-adjust-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_stack_adjust)
        mutation["gadgets"][0]["side_effects"] = []
        semantic_cases.append(("stack-adjust-effect-missing", mutation, ("--mode", "sprint10-stack-adjust-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_memory)
        mutation["gadgets"][0]["memory_access"]["direction"] = "read"
        semantic_cases.append(("memory-direction-disagrees", mutation, ("--mode", "sprint10-memory-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_memory)
        mutation["gadgets"][0]["memory_access"]["base"] = "rsi"
        semantic_cases.append(("memory-base-disagrees", mutation, ("--mode", "sprint10-memory-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_memory)
        mutation["gadgets"][3]["memory_access"]["value_register"] = "rdx"
        semantic_cases.append(("memory-value-disagrees", mutation, ("--mode", "sprint10-memory-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_memory)
        mutation["gadgets"][3]["clobbers"] = []
        semantic_cases.append(("memory-read-clobber-missing", mutation, ("--mode", "sprint10-memory-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_memory)
        mutation["primitive_coverage"]["memory_write"] = False
        semantic_cases.append(("memory-coverage-disagrees", mutation, ("--mode", "sprint10-memory-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        mutation = deepcopy(sprint10_memory)
        mutation["gadgets"][6]["memory_access"] = deepcopy(sprint10_memory["gadgets"][0]["memory_access"])
        semantic_cases.append(("non-memory-carries-memory-relation", mutation, ("--mode", "sprint10-memory-fixture", "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",)))

        for name, document, extra_args in semantic_cases:
            require_formal_accept(current_schema, name, document)
            path = write_document(directory, f"{name}.json", document)
            run_custom(
                path,
                "--require-schema",
                "0.2.0",
                *extra_args,
                expect_success=False,
            )
            semantic_rejections += 1

        # The formal schema keeps Patch 040 reports compatible; only the
        # current-producer validation mode requires the new side-car output.
        run_custom(
            PATCH040_REPORT_PATH,
            "--require-schema",
            "0.2.0",
            "--require-provenance", "--require-sprint10-effects", "--require-sprint10-memory",
            expect_success=False,
        )
        semantic_rejections += 1

        # Command is formally valid, but a caller-specific expectation must
        # still be enforced by the semantic validator.
        run_custom(
            CURRENT_REPORT_PATH,
            "--require-schema",
            "0.2.0",
            "--expected-command",
            "analyze",
            "--require-provenance", "--require-sprint10-effects", "--require-sprint10-transfer", "--require-sprint10-memory",
            expect_success=False,
        )
        semantic_rejections += 1

    print(
        "schema-compat-smoke: ok "
        "legacy=0.1.0 patch040=0.2.0 patch046=0.2.0 current=0.2.0 transfer=0.2.0 stack_adjust=0.2.0 memory=0.2.0 "
        f"formal_rejections={formal_rejections} "
        f"semantic_rejections={semantic_rejections}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, SmokeError, ValueError) as exc:
        print(f"schema-compat-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
