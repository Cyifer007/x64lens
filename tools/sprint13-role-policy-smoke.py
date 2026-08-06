#!/usr/bin/env python3
"""Validate the Patch 080 LC-08B private register-role policy decision.

The policy consumes the corrected v2 task-value result and authorizes only one
additive private candidate-index role-mask side-car for generic register
control, System V call arguments, and Linux syscall arguments.  Public output,
schema, semantic-class, and score projection remain deferred.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-register-role-policy-v1.json"
DEFAULT_EXPECTED = ROOT / "tests/expected/sprint13-register-role-policy.json"
QUALIFIED = ["generic_control", "sysv_call_arguments", "linux_syscall_arguments"]
DEFERRED = ["syscall_number", "stack_pivot"]


class PolicyError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyError(message)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def exact_int(value: Any, expected: int, label: str) -> None:
    require(type(value) is int and value == expected, f"{label} must be integer {expected}")


def validate_authority(authority: dict[str, Any], *, authenticate_sources: bool = True) -> None:
    require(isinstance(authority, dict) and set(authority) == {
        "schema", "sprint", "patch", "status", "purpose", "source_authorities",
        "task_value_input", "private_storage", "policy_cells", "deferred_existing_roles",
        "public_boundary", "acceptance", "limitations",
    }, "role-policy authority shape changed")
    require(authority["schema"] == "x64lens-sprint13-register-role-policy-v1", "role-policy schema")
    exact_int(authority["sprint"], 13, "sprint")
    exact_int(authority["patch"], 80, "patch")
    require(authority["status"] == "private_projection_candidate_pending_acceptance", "role-policy status")

    sources = authority["source_authorities"]
    require(isinstance(sources, list) and len(sources) == 5, "role-policy source denominator")
    seen: set[str] = set()
    for item in sources:
        require(isinstance(item, dict) and set(item) == {"path", "sha256"}, "role-policy source shape")
        path = item["path"]
        require(isinstance(path, str) and path not in seen, "duplicate role-policy source")
        seen.add(path)
        digest = item["sha256"]
        require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "invalid role-policy source digest")
        if authenticate_sources:
            target = ROOT / path
            require(target.is_file() and sha256(target) == digest, f"role-policy source changed: {path}")

    task = authority["task_value_input"]
    require(isinstance(task, dict) and set(task) == {
        "path", "sha256", "schema", "qualified_private_facets", "deferred_facets",
        "development_confirmation_queries_disjoint", "human_blind_claim", "presentation_causal",
    }, "task-value input shape")
    require(task["schema"] == "x64lens-sprint13-register-role-task-value-result-v2", "task-value result schema")
    require(task["qualified_private_facets"] == QUALIFIED and task["deferred_facets"] == DEFERRED, "task-value facet disposition")
    require(task["development_confirmation_queries_disjoint"] is True, "task query overlap")
    require(task["human_blind_claim"] is False and task["presentation_causal"] is False, "unsupported task presentation claim")
    if authenticate_sources:
        result = load(ROOT / task["path"])
        require(sha256(ROOT / task["path"]) == task["sha256"], "task-value result digest changed")
        require(result["next_decision"]["qualified_private_facets"] == QUALIFIED, "task-value result qualified facets changed")
        require(result["next_decision"]["retained_existing_facets"] == DEFERRED, "task-value result deferred facets changed")
        # Confirm every development/confirmation query tuple is unique within a stratum.
        seen_queries: set[tuple[Any, ...]] = set()
        for row in result["tasks"]:
            key = (row["stratum"], row["operation"], row["register"], row["argument_index"])
            require(key not in seen_queries, f"task result query reused: {key}")
            seen_queries.add(key)

    storage = authority["private_storage"]
    require(storage == {
        "record": "candidate_role_record",
        "record_bytes": 8,
        "candidate_capacity": 4096,
        "arena_bytes": 32768,
        "analysis_arena_bytes_before": 851968,
        "analysis_arena_bytes_after": 884736,
        "candidate_index_is_implicit_key": True,
        "scanner_record_unchanged": True,
        "candidate_effect_record_unchanged": True,
    }, "private role storage contract changed")

    cells = authority["policy_cells"]
    require(isinstance(cells, list) and len(cells) == 9, "policy-cell denominator")
    expected = []
    for facet in QUALIFIED:
        expected.extend([
            (facet, "private_runtime", "accept_additive_private_sidecar"),
            (facet, "public_output", "defer"),
            (facet, "score", "retain_existing_scores_and_null_new_facets"),
        ])
    observed: list[tuple[str, str, str]] = []
    for cell in cells:
        require(isinstance(cell, dict) and set(cell) == {"facet", "surface", "decision", "rationale"}, "policy-cell shape")
        require(isinstance(cell["rationale"], str) and cell["rationale"], "policy-cell rationale missing")
        observed.append((cell["facet"], cell["surface"], cell["decision"]))
    require(observed == expected, "policy-cell order or decision changed")

    require(authority["deferred_existing_roles"] == {
        "syscall_number": "retain_existing_syscall_num_control_semantic_and_score",
        "stack_pivot": "retain_existing_stack_pivot_semantics_and_scores",
        "new_private_role_bits": 0,
    }, "deferred existing-role policy changed")
    require(authority["public_boundary"] == {
        "semantic_classifier_changes": 0,
        "public_text_fields_added": 0,
        "public_json_fields_added": 0,
        "schema_changed": False,
        "score_changes": 0,
        "candidate_count_changes": 0,
        "candidate_order_changes": 0,
        "capacity_semantics_changed": False,
        "full_sequence_validity_changed": False,
    }, "public boundary changed")
    require(authority["acceptance"] == {
        "role_masks_exact_for_all_16_single_pops": True,
        "non_pop_role_mask_zero": True,
        "rcx_sysv_arg4_and_not_syscall_arg4": True,
        "r10_syscall_arg4_and_not_sysv_arg4": True,
        "private_sidecar_not_consumed_by_reporters": True,
        "private_sidecar_not_consumed_by_scoring": True,
        "native_and_docker_validation_required": True,
        "lane_a_acceptance_required": True,
    }, "role-policy acceptance contract changed")
    require(isinstance(authority["limitations"], list) and len(authority["limitations"]) == 5, "role-policy limitations")


def source_contract(authority: dict[str, Any]) -> dict[str, Any]:
    structs = (ROOT / "include/structs.inc").read_text(encoding="utf-8")
    role_source = (ROOT / "src/candidate_role.asm").read_text(encoding="utf-8")
    gadgets = (ROOT / "src/gadgets.asm").read_text(encoding="utf-8")
    analyze = (ROOT / "src/analyze.asm").read_text(encoding="utf-8")
    scoring = (ROOT / "src/scoring.asm").read_text(encoding="utf-8")
    report_text = (ROOT / "src/report_text.asm").read_text(encoding="utf-8")
    report_json = (ROOT / "src/report_json.asm").read_text(encoding="utf-8")

    required_defines = {
        "CANDIDATE_ROLE_RECORD_SIZE": "8",
        "CANDIDATE_ROLE_GENERIC_CONTROL": "(1 << 0)",
        "CANDIDATE_ROLE_SYSV_ARG4": "(1 << 11)",
        "CANDIDATE_ROLE_SYSCALL_ARG4": "(1 << 19)",
    }
    for name, expression in required_defines.items():
        require(re.search(rf"^%define\s+{name}\s+{re.escape(expression)}\s*$", structs, re.M) is not None, f"missing role define: {name}")
    require("%define CANDIDATE_ROLE_ARENA_BYTES" in structs and "CANDIDATE_ROLE_ARENA_BYTES" in structs.split("%define ANALYSIS_RECORD_ARENA_BYTES", 1)[1].splitlines()[0], "role arena not included in analysis arena")
    require("global x64lens_candidate_role_from_exact" in role_source, "role materializer symbol missing")
    require(role_source.count("dq CANDIDATE_ROLE_GENERIC_CONTROL") >= 8, "role table lacks generic-control records")
    require("CANDIDATE_ROLE_SYSV_ARG4" in role_source and "CANDIDATE_ROLE_SYSCALL_ARG4" in role_source, "RCX/R10 role distinction missing")
    for source, label in ((gadgets, "gadgets"), (analyze, "analyze")):
        require("call    x64lens_candidate_role_from_exact" in source, f"{label} does not materialize private role facts")
    require("CANDIDATE_ROLE" not in scoring, "scoring consumes private role facts")
    require("CANDIDATE_ROLE" not in report_text and "CANDIDATE_ROLE" not in report_json, "reporter consumes private role facts")
    return {
        "role_record_bytes": 8,
        "role_arena_bytes": 32768,
        "analysis_arena_bytes": 884736,
        "materializer_calls": 2,
        "reporter_consumers": 0,
        "scoring_consumers": 0,
    }


def evaluate(authority: dict[str, Any]) -> dict[str, Any]:
    contract = source_contract(authority)
    cells = copy.deepcopy(authority["policy_cells"])
    return {
        "schema": "x64lens-sprint13-register-role-policy-result-v1",
        "sprint": 13,
        "patch": 80,
        "evidence_class": "implementation_candidate",
        "accepted": False,
        "authority_sha256": hashlib.sha256(canonical(authority)).hexdigest(),
        "qualified_private_facets": QUALIFIED,
        "deferred_existing_facets": DEFERRED,
        "policy_cells": cells,
        "source_contract": contract,
        "public_boundary": copy.deepcopy(authority["public_boundary"]),
        "next_decision": {
            "owner": "S13-P080-Lane-A",
            "condition": "Accept the private side-car only after fresh native and Docker validation; public and score projection remain deferred.",
            "next_patch_after_acceptance": "S13-P081",
        },
    }


def negative_oracles(authority: dict[str, Any]) -> int:
    mutations: list[dict[str, Any]] = []
    value = copy.deepcopy(authority); value["patch"] = False; mutations.append(value)
    value = copy.deepcopy(authority); value["policy_cells"][1]["decision"] = "accept_public_field"; mutations.append(value)
    value = copy.deepcopy(authority); value["policy_cells"][2]["decision"] = "assign_score_90"; mutations.append(value)
    value = copy.deepcopy(authority); value["private_storage"]["record_bytes"] = 16; mutations.append(value)
    value = copy.deepcopy(authority); value["public_boundary"]["semantic_classifier_changes"] = 1; mutations.append(value)
    value = copy.deepcopy(authority); value["source_authorities"][0]["sha256"] = "0" * 63; mutations.append(value)
    rejected = 0
    for mutation in mutations:
        try: validate_authority(mutation, authenticate_sources=False)
        except PolicyError: rejected += 1
        else: raise PolicyError("mutated role-policy authority was accepted")
    return rejected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    args = parser.parse_args()
    authority = load(args.authority)
    validate_authority(authority)
    result = evaluate(authority)
    require(canonical(load(args.expected)) == canonical(result), "role-policy expected result changed")
    negatives = negative_oracles(authority)
    print(
        "sprint13-role-policy-smoke: ok cells=9 private_runtime_accept=3 public_defer=3 score_null=3 "
        "role_record_bytes=8 role_arena_bytes=32768 analysis_arena_bytes=884736 "
        f"negative_oracles={negatives} public_fields_added=0 semantic_changes=0 score_changes=0 schema_changed=0"
    )
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (PolicyError, OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"sprint13-role-policy-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
