#!/usr/bin/env python3
"""Validate the Sprint 13 exact-pop multi-role decision authority.

Patch 078 deliberately queries existing exact-pattern and architectural-effect
facts instead of allocating duplicate runtime role state.  The authority keeps
generic register control, SysV call arguments, Linux syscall arguments, syscall
number control, and stack pivoting as additive facets.  It authorizes no public
field or score change before the corrected task-value and policy gates.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-register-role-decision-v1.json"


class DecisionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DecisionError(message)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    require(isinstance(value, dict), f"{path.name} must contain an object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_int(value: Any, expected: int, label: str) -> None:
    require(type(value) is int and value == expected, f"{label} must be integer {expected}")


def exact_bool(value: Any, expected: bool, label: str) -> None:
    require(type(value) is bool and value is expected, f"{label} must be boolean {expected}")


def validate(authority: dict[str, Any], *, authenticate_sources: bool = True) -> dict[str, int]:
    require(set(authority) == {
        "schema", "sprint", "patch", "status", "purpose", "source_authorities",
        "decision_contract", "register_roles", "qualification_queries", "next_gate", "limitations",
    }, "authority shape changed")
    require(authority["schema"] == "x64lens-sprint13-register-role-decision-v1", "authority schema")
    exact_int(authority["sprint"], 13, "sprint")
    exact_int(authority["patch"], 78, "patch")
    require(authority["status"] == "entry_candidate_pending_acceptance", "authority status")

    sources = authority["source_authorities"]
    require(isinstance(sources, list) and len(sources) == 3, "source authority count")
    source_paths: set[str] = set()
    for item in sources:
        require(isinstance(item, dict) and set(item) == {"path", "sha256"}, "source authority shape")
        path = item["path"]
        require(isinstance(path, str) and path not in source_paths, "duplicate source authority")
        source_paths.add(path)
        require(isinstance(item["sha256"], str) and len(item["sha256"]) == 64, "source SHA-256")
        if authenticate_sources:
            full = ROOT / path
            require(full.is_file() and sha256(full) == item["sha256"], f"source authority changed: {path}")

    catalog = load(ROOT / "tests/expected/sprint10-exact-pattern-catalog.json") if authenticate_sources else None
    catalog_by_id = {item["pattern_id"]: item for item in catalog["patterns"]} if catalog else {}

    contract = authority["decision_contract"]
    require(isinstance(contract, dict), "decision contract")
    for key in (
        "role_facets_are_additive", "generic_register_control_is_not_argument_control",
        "sysv_call_and_linux_syscall_roles_are_distinct", "diagnostic_restart_required_after_public_task_change",
    ):
        exact_bool(contract.get(key), True, key)
    require(contract.get("linux_syscall_argument_4_register") == "r10", "Linux syscall argument four")
    require(contract.get("sysv_call_argument_4_register") == "rcx", "SysV call argument four")
    require(contract.get("syscall_number_register") == "rax", "syscall number register")
    require(contract.get("stack_pivot_register") == "rsp", "stack pivot register")
    for key, expected in {
        "all_exact_single_pop_patterns_accounted": 16,
        "generic_register_control_patterns": 15,
        "sysv_call_argument_patterns": 6,
        "linux_syscall_argument_patterns": 6,
        "new_public_fields": 0,
        "score_changes": 0,
    }.items():
        exact_int(contract.get(key), expected, key)
    exact_bool(contract.get("schema_changed"), False, "schema_changed")
    require(contract.get("task_value_gate") in {"pending_blinded_role_queries", "pending_corrected_role_queries"}, "task-value gate")

    roles = authority["register_roles"]
    require(isinstance(roles, list) and len(roles) == 16, "register-role count")
    required_fields = {
        "register", "pattern_id", "pattern_label", "existing_semantic_class", "existing_evidence_kind",
        "effect_model_complete", "generic_register_control", "sysv_call_argument_index",
        "linux_syscall_argument_index", "linux_syscall_number", "stack_pivot", "role_decision",
        "new_public_projection", "score_decision", "score",
    }
    records: dict[str, dict[str, Any]] = {}
    ids: set[int] = set()
    allowed_registers = {"rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"}
    for item in roles:
        require(isinstance(item, dict) and set(item) == required_fields, "register-role record shape")
        register = item["register"]
        require(register in allowed_registers and register not in records, f"duplicate or unknown register: {register}")
        records[register] = item
        require(type(item["pattern_id"]) is int and item["pattern_id"] not in ids, f"invalid pattern ID: {register}")
        ids.add(item["pattern_id"])
        require(item["pattern_label"] == f"pop {register}; ret", f"pattern label mismatch: {register}")
        for key in ("effect_model_complete", "generic_register_control", "linux_syscall_number", "stack_pivot", "new_public_projection"):
            require(type(item[key]) is bool, f"{register}.{key} must be Boolean")
        exact_bool(item["new_public_projection"], False, f"{register}.new_public_projection")
        for key in ("sysv_call_argument_index", "linux_syscall_argument_index"):
            require(item[key] is None or (type(item[key]) is int and 1 <= item[key] <= 6), f"invalid {register}.{key}")
        require(item["score"] is None or (type(item["score"]) is int and 0 <= item["score"] <= 100), f"invalid score: {register}")
        if catalog:
            source = catalog_by_id.get(item["pattern_id"])
            require(source is not None and source["label"] == item["pattern_label"], f"catalog identity mismatch: {register}")
            for key in ("semantic_class", "evidence_kind", "effect_model_complete", "score"):
                authority_key = {
                    "semantic_class": "existing_semantic_class",
                    "evidence_kind": "existing_evidence_kind",
                    "effect_model_complete": "effect_model_complete",
                    "score": "score",
                }[key]
                require(source[key] == item[authority_key], f"catalog field mismatch: {register}.{key}")

    require(set(records) == allowed_registers, "register role membership changed")
    require(sum(item["generic_register_control"] for item in roles) == 15, "generic-control denominator")
    require(sum(item["sysv_call_argument_index"] is not None for item in roles) == 6, "call-argument denominator")
    require(sum(item["linux_syscall_argument_index"] is not None for item in roles) == 6, "syscall-argument denominator")
    expected_sysv = {"rdi": 1, "rsi": 2, "rdx": 3, "rcx": 4, "r8": 5, "r9": 6}
    expected_syscall = {"rdi": 1, "rsi": 2, "rdx": 3, "r10": 4, "r8": 5, "r9": 6}
    actual_sysv = {register: item["sysv_call_argument_index"] for register, item in records.items() if item["sysv_call_argument_index"] is not None}
    actual_syscall = {register: item["linux_syscall_argument_index"] for register, item in records.items() if item["linux_syscall_argument_index"] is not None}
    require(actual_sysv == expected_sysv, "complete SysV ABI argument map changed")
    require(actual_syscall == expected_syscall, "complete Linux syscall ABI argument map changed")
    require(records["rcx"]["sysv_call_argument_index"] == 4 and records["rcx"]["linux_syscall_argument_index"] is None,
            "RCX call/syscall distinction collapsed")
    require(records["r10"]["sysv_call_argument_index"] is None and records["r10"]["linux_syscall_argument_index"] == 4,
            "R10 call/syscall distinction collapsed")
    require(records["rax"]["linux_syscall_number"] is True, "RAX syscall-number role")
    require(records["rsp"]["stack_pivot"] is True and records["rsp"]["generic_register_control"] is False,
            "RSP pivot distinction")
    pending = [item for item in roles if item["role_decision"] == "private_qualified_pending_task_value"]
    require(len(pending) == 8, "pending exact-only role denominator")
    require(all(item["existing_semantic_class"] == "unknown_candidate" and item["score"] is None and item["score_decision"] == "null_pending_task_value" for item in pending),
            "pending roles changed public semantics or score")

    queries = authority["qualification_queries"]
    require(isinstance(queries, list) and len(queries) == 12, "qualification query count")
    query_ids: set[str] = set()
    for query in queries:
        require(isinstance(query, dict) and set(query) == {"id", "register", "facet", "expected"}, "query shape")
        require(query["id"] not in query_ids, "duplicate query ID")
        query_ids.add(query["id"])
        register = query["register"]
        facet = query["facet"]
        require(register in records and facet in records[register], f"unknown query target: {query}")
        require(records[register][facet] == query["expected"], f"query expectation mismatch: {query['id']}")

    gate = authority["next_gate"]
    require(isinstance(gate, dict) and set(gate) == {"id", "condition", "public_projection_before_gate"}, "next gate shape")
    require(gate["id"] == "S13-P079-role-task-value", "next gate ID")
    exact_bool(gate["public_projection_before_gate"], False, "public projection before task-value gate")
    limitations = authority["limitations"]
    require(isinstance(limitations, list) and len(limitations) == 4 and all(isinstance(item, str) and item for item in limitations), "limitations")
    return {"roles": len(roles), "pending": len(pending), "queries": len(queries)}


def negative_oracles(authority: dict[str, Any]) -> int:
    mutations: list[dict[str, Any]] = []
    value = copy.deepcopy(authority); value["patch"] = False; mutations.append(value)
    value = copy.deepcopy(authority); value["register_roles"].append(copy.deepcopy(value["register_roles"][0])); mutations.append(value)
    value = copy.deepcopy(authority); next(item for item in value["register_roles"] if item["register"] == "r10")["sysv_call_argument_index"] = 4; mutations.append(value)
    value = copy.deepcopy(authority); next(item for item in value["register_roles"] if item["register"] == "rcx")["linux_syscall_argument_index"] = 4; mutations.append(value)
    value = copy.deepcopy(authority); next(item for item in value["register_roles"] if item["register"] == "r10")["score"] = 90; mutations.append(value)
    value = copy.deepcopy(authority); next(item for item in value["register_roles"] if item["register"] == "rdx")["sysv_call_argument_index"] = None; next(item for item in value["register_roles"] if item["register"] == "r13")["sysv_call_argument_index"] = 3; mutations.append(value)
    value = copy.deepcopy(authority); next(item for item in value["register_roles"] if item["register"] == "rdx")["linux_syscall_argument_index"] = None; next(item for item in value["register_roles"] if item["register"] == "r13")["linux_syscall_argument_index"] = 3; mutations.append(value)
    value = copy.deepcopy(authority); value["decision_contract"]["new_public_fields"] = 1; mutations.append(value)
    rejected = 0
    for mutation in mutations:
        try:
            validate(mutation, authenticate_sources=False)
        except DecisionError:
            rejected += 1
        else:
            raise DecisionError("mutated role authority was accepted")
    return rejected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    args = parser.parse_args()
    authority = load(args.authority)
    counts = validate(authority)
    negatives = negative_oracles(authority)
    print(
        "sprint13-register-role-decision-smoke: ok "
        f"roles={counts['roles']} generic_control=15 call_args=6 syscall_args=6 "
        f"r10_syscall_arg4=1 rcx_call_arg4=1 pending_private={counts['pending']} "
        f"qualification_queries={counts['queries']} negative_oracles={negatives} "
        "public_fields_added=0 score_changes=0 schema_changed=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, DecisionError) as exc:
        print(f"sprint13-register-role-decision-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
