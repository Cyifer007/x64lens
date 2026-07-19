#!/usr/bin/env python3
"""Reconcile Sprint 10 closeout state with independent maintained authorities."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT = ROOT / "tests/expected/sprint10-closeout.json"
CATALOG = ROOT / "tests/expected/sprint10-exact-pattern-catalog.json"
FAMILY = ROOT / "tests/expected/sprint10-family-coverage.json"
FIXTURES = ROOT / "tests/expected/sprint10-fixture-suite.json"
STAGES = ROOT / "tests/expected/research-stage-gates.json"
CANONICAL_REPORT = ROOT / "tests/expected/x64lens-report-sprint10-effects-0.2.0.json"
CONSTANTS = ROOT / "include/constants.inc"
STRUCTS = ROOT / "include/structs.inc"
MAKEFILE = ROOT / "Makefile"


class CloseoutError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CloseoutError(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CloseoutError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must contain an object")
    return value


def load_nasm_defines(path: Path) -> dict[str, str]:
    definitions: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CloseoutError(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc
    for line in text.splitlines():
        match = re.match(r"^\s*%define\s+([A-Za-z_][A-Za-z0-9_]*)\s+(.+?)\s*(?:;.*)?$", line)
        if match:
            definitions[match.group(1)] = match.group(2).strip()
    return definitions


def eval_nasm_define(name: str, definitions: dict[str, str], stack: tuple[str, ...] = ()) -> int | str:
    require(name in definitions, f"missing NASM definition: {name}")
    require(name not in stack, f"cyclic NASM definition: {' -> '.join((*stack, name))}")
    expression = definitions[name]
    if len(expression) >= 2 and expression[0] == expression[-1] == '"':
        return expression[1:-1]

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise CloseoutError(f"unsupported NASM expression for {name}: {expression!r}") from exc

    def visit(node: ast.AST) -> int:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.Name):
            value = eval_nasm_define(node.id, definitions, (*stack, name))
            require(isinstance(value, int), f"integer expression {name} references string {node.id}")
            return value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            left = visit(node.left)
            right = visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            return left * right
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise CloseoutError(f"unsupported NASM expression node for {name}: {ast.dump(node)}")

    return visit(tree)


def make_assignment(name: str, text: str) -> str:
    match = re.search(rf"^\s*{re.escape(name)}\s*:?=\s*(\S+)\s*$", text, re.MULTILINE)
    require(match is not None, f"missing Makefile assignment: {name}")
    return match.group(1)


def source_reference_profile(stages: dict[str, Any]) -> dict[str, Any]:
    constants = load_nasm_defines(CONSTANTS)
    structs = load_nasm_defines(STRUCTS)
    try:
        makefile_text = MAKEFILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise CloseoutError(f"cannot read Makefile: {exc}") from exc

    tool_version = eval_nasm_define("X64LENS_VERSION", constants)
    report_schema = eval_nasm_define("X64LENS_SCHEMA", constants)
    require(isinstance(tool_version, str) and isinstance(report_schema, str), "version definitions must be strings")
    require(make_assignment("VERSION", makefile_text) == tool_version, "Makefile/tool version mismatch")
    require(make_assignment("SCHEMA", makefile_text) == report_schema, "Makefile/schema version mismatch")

    conditional = stages.get("conditional_profiles")
    require(isinstance(conditional, list), "conditional_profiles must be a list")
    defaults = {
        item.get("id"): item.get("default")
        for item in conditional
        if isinstance(item, dict)
    }
    require(defaults.get("candidate_scoped_decoder") is False, "decoder must remain an optional profile")
    require(defaults.get("deterministic_concurrency") is False, "concurrency must remain an optional profile")

    def integer(name: str) -> int:
        value = eval_nasm_define(name, structs)
        require(isinstance(value, int), f"{name} must resolve to an integer")
        return value

    return {
        "tool_version": tool_version,
        "report_schema": report_schema,
        "gadget_record_bytes": integer("GADGET_RECORD_SIZE"),
        "candidate_evidence_record_bytes": integer("CANDIDATE_EVIDENCE_RECORD_SIZE"),
        "memory_effect_record_bytes": integer("MEMORY_EFFECT_RECORD_SIZE"),
        "candidate_effect_record_bytes": integer("CANDIDATE_EFFECT_RECORD_SIZE"),
        "candidate_capacity": integer("GADGET_RECORD_MAX"),
        "analysis_arena_bytes": integer("ANALYSIS_RECORD_ARENA_BYTES"),
        "mandatory_decoder": defaults["candidate_scoped_decoder"],
        "mandatory_threads": defaults["deterministic_concurrency"],
    }


def pattern_counts(patterns: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "exact_patterns": len(patterns),
        "semantic_patterns": sum(item.get("semantic_class") != "unknown_candidate" for item in patterns),
        "exact_only_patterns": sum(item.get("semantic_class") == "unknown_candidate" for item in patterns),
        "scored_patterns": sum(item.get("score") is not None for item in patterns),
        "complete_effect_models": sum(item.get("effect_model_complete") is True for item in patterns),
        "partial_effect_models": sum(item.get("effect_model_complete") is False for item in patterns),
    }


def report_counts(report: dict[str, Any]) -> dict[str, int]:
    gadgets = report.get("gadgets")
    require(isinstance(gadgets, list), "canonical report gadgets must be a list")
    counts = report.get("counts")
    require(isinstance(counts, dict), "canonical report counts must be an object")
    derived = {
        "exact_patterns": len(gadgets),
        "semantic_patterns": sum(item.get("semantic_class") != "unknown_candidate" for item in gadgets),
        "exact_only_patterns": sum(item.get("semantic_class") == "unknown_candidate" for item in gadgets),
        "scored_patterns": sum(item.get("score") is not None for item in gadgets),
        "complete_effect_models": sum(
            isinstance(item.get("architectural_effects"), dict)
            and item["architectural_effects"].get("model_complete") is True
            for item in gadgets
        ),
        "partial_effect_models": sum(
            isinstance(item.get("architectural_effects"), dict)
            and item["architectural_effects"].get("model_complete") is False
            for item in gadgets
        ),
    }
    require(counts.get("raw_candidate_count") == len(gadgets), "canonical raw candidate count mismatch")
    require(counts.get("exact_pattern_count") == derived["exact_patterns"], "canonical exact count mismatch")
    require(counts.get("semantic_candidate_count") == derived["semantic_patterns"], "canonical semantic count mismatch")
    require(counts.get("unknown_candidate_count") == derived["exact_only_patterns"], "canonical unknown count mismatch")
    require(counts.get("scored_candidate_count") == derived["scored_patterns"], "canonical scored count mismatch")
    return derived


def format_success_banner(counts: dict[str, int], *, patch_count: int, next_sprint: int) -> str:
    return (
        "sprint10-closeout-smoke: ok "
        f"sprint=10 patches={patch_count} families={counts['semantic_family_contracts']} "
        f"exact_patterns={counts['exact_patterns']} semantic={counts['semantic_patterns']} "
        f"exact_only={counts['exact_only_patterns']} scored={counts['scored_patterns']} "
        f"model_complete={counts['complete_effect_models']} model_partial={counts['partial_effect_models']} "
        f"fixture_groups={counts['fixture_groups']} next_sprint={next_sprint}"
    )


def main() -> int:
    try:
        closeout = load(CLOSEOUT)
        catalog = load(CATALOG)
        family = load(FAMILY)
        fixtures = load(FIXTURES)
        stages = load(STAGES)
        report = load(CANONICAL_REPORT)

        require(closeout.get("schema_version") == 1, "unsupported closeout schema")
        require(closeout.get("sprint") == 10 and closeout.get("status") == "closed", "Sprint 10 is not closed")
        require(closeout.get("closeout_patch") == 54, "Patch 054 must close Sprint 10")
        completed_patches = closeout.get("completed_patches")
        require(completed_patches == list(range(46, 55)), "Patch sequence must cover 046-054")
        next_sprint = closeout.get("next_sprint")
        require(next_sprint == 11, "Sprint 11 must be next")

        expected_profile = source_reference_profile(stages)
        require(closeout.get("reference_profile") == expected_profile, "closeout reference profile/source mismatch")
        require(family.get("reference_profile") == expected_profile, "family reference profile/source mismatch")
        expected_catalog_profile = dict(expected_profile)
        expected_catalog_profile.pop("mandatory_decoder")
        expected_catalog_profile.pop("mandatory_threads")

        patterns = catalog.get("patterns")
        require(isinstance(patterns, list), "exact-pattern catalog patterns must be a list")
        expected_catalog_profile["pattern_count"] = len(patterns)
        require(catalog.get("reference_profile") == expected_catalog_profile, "catalog reference profile/source mismatch")

        families = family.get("families")
        groups = fixtures.get("families")
        require(isinstance(families, list), "family contracts must be a list")
        require(isinstance(groups, dict), "fixture groups must be an object")

        observed_counts = {
            "semantic_family_contracts": len(families),
            **pattern_counts(patterns),
            "fixture_groups": len(groups),
        }
        independent_counts = report_counts(report)
        require(
            {key: observed_counts[key] for key in independent_counts} == independent_counts,
            f"catalog/canonical report count mismatch: catalog={observed_counts!r} report={independent_counts!r}",
        )
        require(closeout.get("contract_counts") == observed_counts, f"closeout contract counts mismatch: {observed_counts!r}")

        require(report.get("tool_version") == expected_profile["tool_version"], "canonical report tool version mismatch")
        require(report.get("schema_version") == expected_profile["report_schema"], "canonical report schema mismatch")
        analysis = report.get("analysis")
        require(isinstance(analysis, dict), "canonical report analysis must be an object")
        require(analysis.get("candidate_capacity") == expected_profile["candidate_capacity"], "canonical report capacity mismatch")

        transition = closeout.get("research_transition")
        expected_transition = {
            "diagnostic_sprint": stages.get("diagnostic_sprint"),
            "campaign_freeze_sprint": stages.get("campaign_freeze_sprint"),
            "preview_sprint": stages.get("preview_sprint"),
            "publication_campaign_sprint": stages.get("publication_campaign_sprint"),
            "release_sprint": stages.get("release_sprint"),
        }
        require(transition == expected_transition == {
            "diagnostic_sprint": 11,
            "campaign_freeze_sprint": 15,
            "preview_sprint": 16,
            "publication_campaign_sprint": 17,
            "release_sprint": 22,
        }, "research transition mismatch")
        require(stages.get("completed_sprints") == 10 and stages.get("active_sprint") == 11, "stage status mismatch")

        for relative in closeout.get("required_closeout_documents", []):
            require((ROOT / relative).is_file(), f"missing closeout document: {relative}")

        sprint10 = (ROOT / "docs/sprints/sprint-10-plan.md").read_text(encoding="utf-8")
        sprint11 = (ROOT / "docs/sprints/sprint-11-plan.md").read_text(encoding="utf-8")
        require("Closed by Patch 054" in sprint10, "Sprint 10 plan is not closed")
        require("Active diagnostic measurement sprint" in sprint11, "Sprint 11 plan is not active")

        makefile = MAKEFILE.read_text(encoding="utf-8")
        require("sprint10-closeout-smoke:" in makefile, "Make target is missing")
        validation_line = next((line for line in makefile.splitlines() if line.startswith("validation-smoke:")), "")
        require("sprint10-closeout-smoke" in validation_line, "closeout smoke is not part of validation-smoke")
        require("research-roadmap-consistency-smoke" in validation_line, "roadmap consistency is not part of validation-smoke")

    except (OSError, CloseoutError) as exc:
        print(f"sprint10-closeout-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(format_success_banner(observed_counts, patch_count=len(completed_patches), next_sprint=next_sprint))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
