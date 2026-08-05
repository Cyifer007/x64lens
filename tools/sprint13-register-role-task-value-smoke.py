#!/usr/bin/env python3
"""Execute the five preregistered P079 register-role task-value strata.

The gate compares two frozen answer profiles under deterministic A/B label
permutation: the current public semantic facts and the additive private role
facets recorded by Patch 078.  Eight development and four untouched
confirmation tasks are evaluated independently for each of five role strata.
A stratum qualifies only when it demonstrates incremental development and
confirmation value without regressions or incorrect promotions.

This is a query-only diagnostic authority.  It changes no classifier, report,
JSON schema, candidate metric, score, or default output byte.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-register-role-task-value-v1.json"
DEFAULT_ROLE_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-register-role-decision-v1.json"
DEFAULT_EXPECTED = ROOT / "tests/expected/sprint13-register-role-task-value.json"
UNKNOWN = "unknown"
STRATA = (
    "generic_control",
    "sysv_call_arguments",
    "linux_syscall_arguments",
    "syscall_number",
    "stack_pivot",
)
REGISTERS = {
    "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
}


class TaskValueError(RuntimeError):
    """Raised when the role-task authority or result is inconsistent."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TaskValueError(message)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
        require(key not in value, f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def exact_int(value: Any, expected: int, label: str) -> None:
    require(type(value) is int and value == expected, f"{label} must be integer {expected}")


def validate_authority(value: dict[str, Any], *, authenticate_sources: bool = True) -> None:
    require(
        isinstance(value, dict)
        and set(value) == {
            "schema", "sprint", "patch", "status", "purpose", "source_authorities",
            "blinding", "acceptance", "strata", "tasks", "public_boundary", "limitations",
        },
        "role-task authority shape changed",
    )
    require(value["schema"] == "x64lens-sprint13-register-role-task-value-v1", "wrong role-task schema")
    exact_int(value["sprint"], 13, "sprint")
    exact_int(value["patch"], 79, "patch")
    require(value["status"] == "preregistered_diagnostic_gate", "role-task status changed")
    require(isinstance(value["purpose"], str) and value["purpose"], "role-task purpose is missing")

    sources = value["source_authorities"]
    require(isinstance(sources, list) and len(sources) == 3, "source authority denominator changed")
    seen_sources: set[str] = set()
    for item in sources:
        require(isinstance(item, dict) and set(item) == {"path", "sha256"}, "source authority shape changed")
        path = item["path"]
        require(isinstance(path, str) and path not in seen_sources, "duplicate source authority")
        seen_sources.add(path)
        require(
            isinstance(item["sha256"], str)
            and len(item["sha256"]) == 64
            and all(char in "0123456789abcdef" for char in item["sha256"]),
            "invalid source digest",
        )
        if authenticate_sources:
            target = ROOT / path
            require(target.is_file() and sha256(target) == item["sha256"], f"source authority changed: {path}")

    blinding = value["blinding"]
    require(
        isinstance(blinding, dict)
        and set(blinding) == {
            "method", "seed_sha256", "labels", "task_authority_omits_profile_label_mapping",
            "human_double_blind_claim", "profile_rules_frozen_before_confirmation",
        },
        "blinding authority shape changed",
    )
    require(blinding["method"] == "deterministic_sha256_label_permutation", "blinding method changed")
    require(
        isinstance(blinding["seed_sha256"], str)
        and len(blinding["seed_sha256"]) == 64
        and all(char in "0123456789abcdef" for char in blinding["seed_sha256"]),
        "invalid blinding seed",
    )
    require(blinding["labels"] == ["A", "B"], "blinded labels changed")
    require(blinding["task_authority_omits_profile_label_mapping"] is True, "task authority exposes profile mapping")
    require(blinding["human_double_blind_claim"] is False, "unsupported human double-blind claim")
    require(blinding["profile_rules_frozen_before_confirmation"] is True, "confirmation profile was not frozen")

    acceptance = value["acceptance"]
    expected_acceptance = {
        "strata_evaluated_independently": True,
        "development_tasks_per_stratum": 8,
        "confirmation_tasks_per_stratum": 4,
        "minimum_incremental_development_gains": 2,
        "maximum_regressions": 0,
        "maximum_incorrect_promotions": 0,
        "required_confirmation_correct": 4,
        "minimum_incremental_confirmation_gains": 1,
        "pooling_across_strata_permitted": False,
    }
    require(isinstance(acceptance, dict) and acceptance == expected_acceptance, "acceptance thresholds changed")

    strata = value["strata"]
    require(isinstance(strata, list) and len(strata) == 5, "role-task stratum denominator changed")
    require([item.get("id") for item in strata] == list(STRATA), "role-task stratum order changed")
    for item in strata:
        require(
            isinstance(item, dict)
            and set(item) == {"id", "label", "development_tasks", "confirmation_tasks"},
            "role-task stratum shape changed",
        )
        require(isinstance(item["label"], str) and item["label"], "role-task stratum label missing")
        exact_int(item["development_tasks"], 8, f"{item['id']}.development_tasks")
        exact_int(item["confirmation_tasks"], 4, f"{item['id']}.confirmation_tasks")

    tasks = value["tasks"]
    require(isinstance(tasks, list) and len(tasks) == 60, "role-task count changed")
    ids: set[str] = set()
    phase_sequences: dict[tuple[str, str], list[int]] = {}
    for task in tasks:
        require(
            isinstance(task, dict)
            and set(task) == {"id", "stratum", "phase", "sequence", "operation", "register", "argument_index", "oracle"},
            "task record shape changed",
        )
        task_id = task["id"]
        require(isinstance(task_id, str) and task_id not in ids, "duplicate task id")
        ids.add(task_id)
        require(task["stratum"] in STRATA, f"unknown task stratum: {task_id}")
        require(task["phase"] in {"development", "confirmation"}, f"unknown task phase: {task_id}")
        require(type(task["sequence"]) is int and 1 <= task["sequence"] <= 8, f"invalid task sequence: {task_id}")
        phase_sequences.setdefault((task["stratum"], task["phase"]), []).append(task["sequence"])
        require(task["operation"] in {"is_role", "select_register"}, f"unknown task operation: {task_id}")
        register = task["register"]
        index = task["argument_index"]
        if task["operation"] == "is_role":
            require(register in REGISTERS and index is None and type(task["oracle"]) is bool, f"invalid Boolean role task: {task_id}")
        else:
            require(register is None and isinstance(task["oracle"], str) and task["oracle"] in REGISTERS,
                    f"invalid register-selection task: {task_id}")
            if task["stratum"] in {"sysv_call_arguments", "linux_syscall_arguments"}:
                require(type(index) is int and 1 <= index <= 6, f"invalid argument index: {task_id}")
            else:
                require(index is None, f"unexpected argument index: {task_id}")
    for stratum in STRATA:
        require(sorted(phase_sequences[(stratum, "development")]) == list(range(1, 9)), f"development task order changed: {stratum}")
        require(sorted(phase_sequences[(stratum, "confirmation")]) == list(range(1, 5)), f"confirmation task order changed: {stratum}")

    boundary = value["public_boundary"]
    require(
        isinstance(boundary, dict)
        and boundary == {
            "runtime_classifier_changed": False,
            "public_fields_added": 0,
            "schema_changed": False,
            "score_changes": 0,
            "default_report_bytes_changed_by_gate": False,
            "passing_stratum_authorizes_public_projection": False,
            "passing_stratum_authorizes_score": False,
            "next_policy_owner": "LC-08B",
        },
        "public/runtime boundary changed",
    )
    limitations = value["limitations"]
    require(isinstance(limitations, list) and len(limitations) == 4 and all(isinstance(item, str) and item for item in limitations),
            "role-task limitations changed")


def role_records(role_authority: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validator = load_module("p079_role_decision_validator", ROOT / "tools/sprint13-register-role-decision-smoke.py")
    validator.validate(role_authority)
    return {item["register"]: item for item in role_authority["register_roles"]}


def current_is_role(stratum: str, record: dict[str, Any]) -> bool | str:
    semantic = record["existing_semantic_class"]
    register = record["register"]
    if stratum == "generic_control":
        if semantic == "unknown_candidate":
            return UNKNOWN
        return semantic in {"arg_control", "syscall_num_control"}
    if stratum == "sysv_call_arguments":
        if semantic == "unknown_candidate":
            return UNKNOWN
        return semantic == "arg_control"
    if stratum == "linux_syscall_arguments":
        if semantic == "unknown_candidate" or register == "rcx":
            return UNKNOWN
        if semantic == "arg_control":
            return record["linux_syscall_argument_index"] is not None
        return False
    if stratum == "syscall_number":
        if semantic == "unknown_candidate":
            return UNKNOWN
        return semantic == "syscall_num_control"
    if stratum == "stack_pivot":
        if semantic == "unknown_candidate":
            return UNKNOWN
        return semantic == "stack_pivot"
    raise TaskValueError(f"unsupported current role stratum: {stratum}")


def additive_is_role(stratum: str, record: dict[str, Any]) -> bool:
    if stratum == "generic_control":
        return bool(record["generic_register_control"])
    if stratum == "sysv_call_arguments":
        return record["sysv_call_argument_index"] is not None
    if stratum == "linux_syscall_arguments":
        return record["linux_syscall_argument_index"] is not None
    if stratum == "syscall_number":
        return bool(record["linux_syscall_number"])
    if stratum == "stack_pivot":
        return bool(record["stack_pivot"])
    raise TaskValueError(f"unsupported additive role stratum: {stratum}")


def answer_profile(task: dict[str, Any], records: dict[str, dict[str, Any]], profile: str) -> Any:
    stratum = task["stratum"]
    if task["operation"] == "is_role":
        record = records[task["register"]]
        return current_is_role(stratum, record) if profile == "current" else additive_is_role(stratum, record)

    # Selection tasks expose one role slot.  The current profile may use only
    # existing public semantic classes; the additive profile may use the frozen
    # private role facets.
    index = task["argument_index"]
    candidates: list[str] = []
    for register, record in records.items():
        if profile == "current":
            if stratum == "sysv_call_arguments":
                match = record["existing_semantic_class"] == "arg_control" and record["sysv_call_argument_index"] == index
            elif stratum == "linux_syscall_arguments":
                match = (
                    record["existing_semantic_class"] == "arg_control"
                    and register != "rcx"
                    and record["linux_syscall_argument_index"] == index
                )
            elif stratum == "syscall_number":
                match = record["existing_semantic_class"] == "syscall_num_control"
            elif stratum == "stack_pivot":
                match = record["existing_semantic_class"] == "stack_pivot"
            else:
                match = False
        else:
            if stratum == "sysv_call_arguments":
                match = record["sysv_call_argument_index"] == index
            elif stratum == "linux_syscall_arguments":
                match = record["linux_syscall_argument_index"] == index
            elif stratum == "syscall_number":
                match = bool(record["linux_syscall_number"])
            elif stratum == "stack_pivot":
                match = bool(record["stack_pivot"])
            else:
                match = False
        if match:
            candidates.append(register)
    if len(candidates) == 1:
        return candidates[0]
    require(len(candidates) <= 1, f"profile {profile} produced multiple register answers: {task['id']}")
    return UNKNOWN


def label_mapping(seed: str, task_id: str) -> dict[str, str]:
    selector = hashlib.sha256((seed + "\0" + task_id).encode("ascii")).digest()[0] & 1
    return {"A": "current", "B": "additive"} if selector == 0 else {"A": "additive", "B": "current"}


def evaluate(authority: dict[str, Any], role_authority: dict[str, Any], *, enforce_clean: bool = True) -> dict[str, Any]:
    records = role_records(role_authority)
    seed = authority["blinding"]["seed_sha256"]
    task_rows: list[dict[str, Any]] = []
    # Generate both profile answers without reading the oracle field.
    for source in authority["tasks"]:
        query = {key: value for key, value in source.items() if key != "oracle"}
        answers = {
            "current": answer_profile(query, records, "current"),
            "additive": answer_profile(query, records, "additive"),
        }
        mapping = label_mapping(seed, source["id"])
        blinded = {label: answers[profile] for label, profile in mapping.items()}
        oracle = source["oracle"]
        current_correct = answers["current"] == oracle
        additive_correct = answers["additive"] == oracle
        incremental = (not current_correct) and additive_correct
        regression = current_correct and not additive_correct
        incorrect_promotion = answers["additive"] != UNKNOWN and not additive_correct
        task_rows.append(
            {
                **query,
                "oracle": oracle,
                "blinded_answers": blinded,
                "unblinding": mapping,
                "current_answer": answers["current"],
                "additive_answer": answers["additive"],
                "current_correct": current_correct,
                "additive_correct": additive_correct,
                "incremental_gain": incremental,
                "regression": regression,
                "incorrect_promotion": incorrect_promotion,
            }
        )

    thresholds = authority["acceptance"]
    summaries: list[dict[str, Any]] = []
    for stratum in STRATA:
        rows = [row for row in task_rows if row["stratum"] == stratum]
        development = [row for row in rows if row["phase"] == "development"]
        confirmation = [row for row in rows if row["phase"] == "confirmation"]
        development_gains = sum(row["incremental_gain"] for row in development)
        confirmation_gains = sum(row["incremental_gain"] for row in confirmation)
        regressions = sum(row["regression"] for row in rows)
        incorrect = sum(row["incorrect_promotion"] for row in rows)
        confirmation_correct = sum(row["additive_correct"] for row in confirmation)
        qualified = (
            development_gains >= thresholds["minimum_incremental_development_gains"]
            and regressions <= thresholds["maximum_regressions"]
            and incorrect <= thresholds["maximum_incorrect_promotions"]
            and confirmation_correct == thresholds["required_confirmation_correct"]
            and confirmation_gains >= thresholds["minimum_incremental_confirmation_gains"]
        )
        summaries.append(
            {
                "stratum": stratum,
                "development_tasks": len(development),
                "development_incremental_gains": development_gains,
                "confirmation_tasks": len(confirmation),
                "confirmation_correct": confirmation_correct,
                "confirmation_incremental_gains": confirmation_gains,
                "regressions": regressions,
                "incorrect_promotions": incorrect,
                "decision": "qualify_private_facet_for_next_policy_gate" if qualified else "retain_existing_semantic_or_unknown",
                "qualified": qualified,
            }
        )

    result = {
        "schema": "x64lens-sprint13-register-role-task-value-result-v1",
        "sprint": 13,
        "patch": 79,
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "authority_sha256": hashlib.sha256(canonical(authority)).hexdigest(),
        "role_authority_sha256": hashlib.sha256(canonical(role_authority)).hexdigest(),
        "blinding": {
            "method": authority["blinding"]["method"],
            "answers_generated_before_oracle_scoring": True,
            "mapping_revealed_after_answer_generation": True,
            "human_double_blind_claim": False,
        },
        "denominators": {
            "strata": 5,
            "tasks": 60,
            "development_tasks": 40,
            "confirmation_tasks": 20,
        },
        "strata": summaries,
        "tasks": task_rows,
        "aggregate": {
            "qualified_strata": sum(item["qualified"] for item in summaries),
            "deferred_strata": sum(not item["qualified"] for item in summaries),
            "incremental_gains": sum(item["development_incremental_gains"] + item["confirmation_incremental_gains"] for item in summaries),
            "regressions": sum(item["regressions"] for item in summaries),
            "incorrect_promotions": sum(item["incorrect_promotions"] for item in summaries),
        },
        "public_boundary": copy.deepcopy(authority["public_boundary"]),
        "next_decision": {
            "owner": "LC-08B",
            "runtime_projection_authorized": False,
            "public_projection_authorized": False,
            "score_change_authorized": False,
            "qualified_private_facets": [item["stratum"] for item in summaries if item["qualified"]],
            "retained_existing_facets": [item["stratum"] for item in summaries if not item["qualified"]],
        },
    }
    if enforce_clean:
        require(
            result["aggregate"]["regressions"] == 0
            and result["aggregate"]["incorrect_promotions"] == 0,
            "role-task evaluation contains a regression or incorrect promotion",
        )
    return result


def negative_oracles(authority: dict[str, Any], role_authority: dict[str, Any]) -> int:
    mutations: list[dict[str, Any]] = []
    value = copy.deepcopy(authority); value["patch"] = False; mutations.append(value)
    value = copy.deepcopy(authority); value["tasks"].append(copy.deepcopy(value["tasks"][0])); mutations.append(value)
    value = copy.deepcopy(authority); value["acceptance"]["pooling_across_strata_permitted"] = True; mutations.append(value)
    value = copy.deepcopy(authority); value["blinding"]["human_double_blind_claim"] = True; mutations.append(value)
    value = copy.deepcopy(authority); value["public_boundary"]["score_changes"] = 1; mutations.append(value)
    value = copy.deepcopy(authority); value["source_authorities"][0]["sha256"] = "0" * 63; mutations.append(value)
    rejected = 0
    for mutation in mutations:
        try:
            validate_authority(mutation, authenticate_sources=False)
        except TaskValueError:
            rejected += 1
        else:
            raise TaskValueError("mutated role-task authority was accepted")

    # A wrong cross-ABI oracle must be visible as an incorrect additive
    # promotion and may not qualify the Linux syscall stratum.
    wrong = copy.deepcopy(authority)
    target = next(item for item in wrong["tasks"] if item["stratum"] == "linux_syscall_arguments" and item["register"] == "rcx")
    target["oracle"] = True
    result = evaluate(wrong, role_authority, enforce_clean=False)
    linux = next(item for item in result["strata"] if item["stratum"] == "linux_syscall_arguments")
    require(linux["incorrect_promotions"] >= 1 and linux["qualified"] is False,
            "cross-ABI oracle corruption did not fail closed")
    return rejected + 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--role-authority", type=Path, default=DEFAULT_ROLE_AUTHORITY)
    parser.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--skip-expected", action="store_true")
    args = parser.parse_args()

    authority = load(args.authority)
    role_authority = load(args.role_authority)
    validate_authority(authority)
    result = evaluate(authority, role_authority)
    negatives = negative_oracles(authority, role_authority)
    if not args.skip_expected:
        expected = load(args.expected)
        require(canonical(expected) == canonical(result), "role-task expected result changed")
    if args.result is not None:
        require(not args.result.exists(), f"result already exists: {args.result}")
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_bytes(json.dumps(result, indent=2, sort_keys=True).encode() + b"\n")

    decisions = {item["stratum"]: item["qualified"] for item in result["strata"]}
    print(
        "sprint13-register-role-task-value-smoke: ok "
        "strata=5 tasks=60 development=40 confirmation=20 "
        f"qualified={result['aggregate']['qualified_strata']} deferred={result['aggregate']['deferred_strata']} "
        f"generic={'qualify' if decisions['generic_control'] else 'defer'} "
        f"sysv={'qualify' if decisions['sysv_call_arguments'] else 'defer'} "
        f"linux_syscall={'qualify' if decisions['linux_syscall_arguments'] else 'defer'} "
        f"syscall_number={'qualify' if decisions['syscall_number'] else 'defer'} "
        f"pivot={'qualify' if decisions['stack_pivot'] else 'defer'} "
        f"incremental_gains={result['aggregate']['incremental_gains']} regressions=0 incorrect_promotions=0 "
        f"negative_oracles={negatives} public_fields_added=0 score_changes=0 schema_changed=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (TaskValueError, OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"sprint13-register-role-task-value-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
