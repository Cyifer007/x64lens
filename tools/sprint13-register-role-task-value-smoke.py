#!/usr/bin/env python3
"""Execute the corrected five-stratum Sprint 13 register-role task gate.

Patch 080 supersedes the P079 v1 oracle.  Development and confirmation query
identities are disjoint within each stratum, the complete SysV and Linux syscall
ABI maps are validated, and deterministic answer presentation is explicitly
non-causal.  The gate compares the current semantic profile with additive
private role facets.  It does not claim human blinding and cannot authorize
public fields or scores.
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
DEFAULT_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-register-role-task-value-v2.json"
DEFAULT_ROLE_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-register-role-decision-v1.json"
DEFAULT_EXPECTED = ROOT / "tests/expected/sprint13-register-role-task-value-v2.json"
UNKNOWN = "unknown"
STRATA = (
    "generic_control", "sysv_call_arguments", "linux_syscall_arguments",
    "syscall_number", "stack_pivot",
)
REGISTERS = {
    "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp",
    "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
}


class TaskValueError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TaskValueError(message)


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
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
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


def query_key(task: dict[str, Any]) -> tuple[Any, ...]:
    return (task["operation"], task["register"], task["argument_index"])


def validate_authority(value: dict[str, Any], *, authenticate_sources: bool = True) -> None:
    require(isinstance(value, dict) and set(value) == {
        "schema", "sprint", "patch", "status", "purpose", "source_authorities",
        "presentation", "acceptance", "strata", "tasks", "public_boundary", "limitations",
    }, "role-task authority shape changed")
    require(value["schema"] == "x64lens-sprint13-register-role-task-value-v2", "wrong role-task schema")
    exact_int(value["sprint"], 13, "sprint")
    exact_int(value["patch"], 80, "patch")
    require(value["status"] == "corrected_diagnostic_gate_pending_acceptance", "role-task status changed")
    require(isinstance(value["purpose"], str) and value["purpose"], "role-task purpose missing")

    sources = value["source_authorities"]
    require(isinstance(sources, list) and len(sources) == 3, "source authority denominator changed")
    seen: set[str] = set()
    for item in sources:
        require(isinstance(item, dict) and set(item) == {"path", "sha256"}, "source authority shape changed")
        path = item["path"]
        digest = item["sha256"]
        require(isinstance(path, str) and path not in seen, "duplicate source authority")
        seen.add(path)
        require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "invalid source digest")
        if authenticate_sources:
            target = ROOT / path
            require(target.is_file() and sha256(target) == digest, f"source authority changed: {path}")

    presentation = value["presentation"]
    require(isinstance(presentation, dict) and presentation == {
        "method": "deterministic_sha256_profile_order",
        "seed_sha256": presentation.get("seed_sha256"),
        "profiles": ["current", "additive_private"],
        "human_blind_claim": False,
        "causal_to_scoring_or_decision": False,
        "profile_order_is_only_a_reproducibility_control": True,
    }, "presentation authority changed")
    seed = presentation["seed_sha256"]
    require(isinstance(seed, str) and len(seed) == 64 and all(c in "0123456789abcdef" for c in seed), "invalid presentation seed")

    expected_acceptance = {
        "strata_evaluated_independently": True,
        "development_tasks_per_stratum": 8,
        "confirmation_tasks_per_stratum": 4,
        "minimum_incremental_development_gains": 2,
        "maximum_regressions": 0,
        "maximum_incorrect_promotions": 0,
        "required_confirmation_correct": 4,
        "minimum_incremental_confirmation_gains": 1,
        "development_confirmation_queries_disjoint": True,
        "pooling_across_strata_permitted": False,
    }
    require(value["acceptance"] == expected_acceptance, "acceptance thresholds changed")

    strata = value["strata"]
    require(isinstance(strata, list) and len(strata) == 5, "stratum denominator changed")
    require([item.get("id") for item in strata] == list(STRATA), "stratum order changed")
    for item in strata:
        require(isinstance(item, dict) and set(item) == {"id", "label", "development_tasks", "confirmation_tasks"}, "stratum shape changed")
        exact_int(item["development_tasks"], 8, f"{item['id']}.development_tasks")
        exact_int(item["confirmation_tasks"], 4, f"{item['id']}.confirmation_tasks")

    tasks = value["tasks"]
    require(isinstance(tasks, list) and len(tasks) == 60, "task denominator changed")
    ids: set[str] = set()
    phase_sequences: dict[tuple[str, str], list[int]] = {}
    phase_queries: dict[tuple[str, str], set[tuple[Any, ...]]] = {}
    for task in tasks:
        require(isinstance(task, dict) and set(task) == {
            "id", "stratum", "phase", "sequence", "operation", "register", "argument_index", "oracle",
        }, "task shape changed")
        task_id = task["id"]
        require(isinstance(task_id, str) and task_id not in ids, "duplicate task id")
        ids.add(task_id)
        stratum = task["stratum"]
        phase = task["phase"]
        require(stratum in STRATA and phase in {"development", "confirmation"}, f"invalid task identity: {task_id}")
        limit = 8 if phase == "development" else 4
        require(type(task["sequence"]) is int and 1 <= task["sequence"] <= limit, f"invalid sequence: {task_id}")
        phase_sequences.setdefault((stratum, phase), []).append(task["sequence"])
        operation = task["operation"]
        require(operation in {"is_role", "select_register"}, f"invalid operation: {task_id}")
        if operation == "is_role":
            require(task["register"] in REGISTERS and task["argument_index"] is None and type(task["oracle"]) is bool, f"invalid role query: {task_id}")
        else:
            require(task["register"] is None and task["oracle"] in REGISTERS, f"invalid selection query: {task_id}")
            if stratum in {"sysv_call_arguments", "linux_syscall_arguments"}:
                require(type(task["argument_index"]) is int and 1 <= task["argument_index"] <= 6, f"invalid argument index: {task_id}")
            else:
                require(task["argument_index"] is None, f"unexpected argument index: {task_id}")
        key = query_key(task)
        bucket = phase_queries.setdefault((stratum, phase), set())
        require(key not in bucket, f"duplicate query in phase: {task_id}")
        bucket.add(key)

    for stratum in STRATA:
        require(sorted(phase_sequences[(stratum, "development")]) == list(range(1, 9)), f"development order changed: {stratum}")
        require(sorted(phase_sequences[(stratum, "confirmation")]) == list(range(1, 5)), f"confirmation order changed: {stratum}")
        require(phase_queries[(stratum, "development")].isdisjoint(phase_queries[(stratum, "confirmation")]), f"development/confirmation query reuse: {stratum}")

    require(value["public_boundary"] == {
        "runtime_classifier_changed_by_gate": False,
        "private_role_sidecar_changed_by_gate": False,
        "public_fields_added": 0,
        "schema_changed": False,
        "score_changes": 0,
        "passing_stratum_authorizes_public_projection": False,
        "passing_stratum_authorizes_score": False,
        "next_policy_owner": "S13-P080-LC-08B",
    }, "public/runtime boundary changed")
    limitations = value["limitations"]
    require(isinstance(limitations, list) and len(limitations) == 5 and all(isinstance(x, str) and x for x in limitations), "limitations changed")


def role_records(role_authority: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validator = load_module("p080_role_decision_validator", ROOT / "tools/sprint13-register-role-decision-smoke.py")
    validator.validate(role_authority)
    return {item["register"]: item for item in role_authority["register_roles"]}


def current_is_role(stratum: str, record: dict[str, Any]) -> bool | str:
    semantic = record["existing_semantic_class"]
    register = record["register"]
    if stratum == "generic_control":
        if semantic == "unknown_candidate": return UNKNOWN
        return semantic in {"arg_control", "syscall_num_control"}
    if stratum == "sysv_call_arguments":
        if semantic == "unknown_candidate": return UNKNOWN
        return semantic == "arg_control"
    if stratum == "linux_syscall_arguments":
        if semantic == "unknown_candidate" or register == "rcx": return UNKNOWN
        if semantic == "arg_control": return record["linux_syscall_argument_index"] is not None
        return False
    if stratum == "syscall_number":
        if semantic == "unknown_candidate": return UNKNOWN
        return semantic == "syscall_num_control"
    if stratum == "stack_pivot":
        if semantic == "unknown_candidate": return UNKNOWN
        return semantic == "stack_pivot"
    raise TaskValueError(f"unsupported stratum: {stratum}")


def additive_is_role(stratum: str, record: dict[str, Any]) -> bool:
    if stratum == "generic_control": return bool(record["generic_register_control"])
    if stratum == "sysv_call_arguments": return record["sysv_call_argument_index"] is not None
    if stratum == "linux_syscall_arguments": return record["linux_syscall_argument_index"] is not None
    if stratum == "syscall_number": return bool(record["linux_syscall_number"])
    if stratum == "stack_pivot": return bool(record["stack_pivot"])
    raise TaskValueError(f"unsupported stratum: {stratum}")


def answer_profile(task: dict[str, Any], records: dict[str, dict[str, Any]], profile: str) -> Any:
    stratum = task["stratum"]
    if task["operation"] == "is_role":
        record = records[task["register"]]
        return current_is_role(stratum, record) if profile == "current" else additive_is_role(stratum, record)
    index = task["argument_index"]
    candidates: list[str] = []
    for register, record in records.items():
        if profile == "current":
            if stratum == "sysv_call_arguments":
                match = record["existing_semantic_class"] == "arg_control" and record["sysv_call_argument_index"] == index
            elif stratum == "linux_syscall_arguments":
                match = record["existing_semantic_class"] == "arg_control" and register != "rcx" and record["linux_syscall_argument_index"] == index
            elif stratum == "syscall_number": match = record["existing_semantic_class"] == "syscall_num_control"
            elif stratum == "stack_pivot": match = record["existing_semantic_class"] == "stack_pivot"
            else: match = False
        else:
            if stratum == "sysv_call_arguments": match = record["sysv_call_argument_index"] == index
            elif stratum == "linux_syscall_arguments": match = record["linux_syscall_argument_index"] == index
            elif stratum == "syscall_number": match = bool(record["linux_syscall_number"])
            elif stratum == "stack_pivot": match = bool(record["stack_pivot"])
            else: match = False
        if match: candidates.append(register)
    require(len(candidates) <= 1, f"multiple register answers: {task['id']}")
    return candidates[0] if candidates else UNKNOWN


def presentation_order(seed: str, task_id: str) -> list[str]:
    return ["current", "additive_private"] if hashlib.sha256((seed + "\0" + task_id).encode()).digest()[0] & 1 == 0 else ["additive_private", "current"]


def evaluate(authority: dict[str, Any], role_authority: dict[str, Any], *, enforce_clean: bool = True) -> dict[str, Any]:
    records = role_records(role_authority)
    seed = authority["presentation"]["seed_sha256"]
    rows: list[dict[str, Any]] = []
    for source in authority["tasks"]:
        query = {k: v for k, v in source.items() if k != "oracle"}
        answers = {
            "current": answer_profile(query, records, "current"),
            "additive_private": answer_profile(query, records, "additive"),
        }
        oracle = source["oracle"]
        current_correct = answers["current"] == oracle
        additive_correct = answers["additive_private"] == oracle
        rows.append({
            **query, "oracle": oracle, "profile_answers": answers,
            "presentation_order": presentation_order(seed, source["id"]),
            "current_correct": current_correct, "additive_correct": additive_correct,
            "incremental_gain": (not current_correct) and additive_correct,
            "regression": current_correct and not additive_correct,
            "incorrect_promotion": answers["additive_private"] != UNKNOWN and not additive_correct,
        })

    thresholds = authority["acceptance"]
    summaries: list[dict[str, Any]] = []
    for stratum in STRATA:
        selected = [row for row in rows if row["stratum"] == stratum]
        dev = [row for row in selected if row["phase"] == "development"]
        conf = [row for row in selected if row["phase"] == "confirmation"]
        dev_gains = sum(row["incremental_gain"] for row in dev)
        conf_gains = sum(row["incremental_gain"] for row in conf)
        regressions = sum(row["regression"] for row in selected)
        incorrect = sum(row["incorrect_promotion"] for row in selected)
        conf_correct = sum(row["additive_correct"] for row in conf)
        qualified = (
            dev_gains >= thresholds["minimum_incremental_development_gains"]
            and regressions <= thresholds["maximum_regressions"]
            and incorrect <= thresholds["maximum_incorrect_promotions"]
            and conf_correct == thresholds["required_confirmation_correct"]
            and conf_gains >= thresholds["minimum_incremental_confirmation_gains"]
        )
        summaries.append({
            "stratum": stratum, "development_tasks": len(dev),
            "development_incremental_gains": dev_gains, "confirmation_tasks": len(conf),
            "confirmation_correct": conf_correct, "confirmation_incremental_gains": conf_gains,
            "regressions": regressions, "incorrect_promotions": incorrect,
            "decision": "qualify_private_facet_for_policy_gate" if qualified else "retain_existing_semantic_or_unknown",
            "qualified": qualified,
        })

    result = {
        "schema": "x64lens-sprint13-register-role-task-value-result-v2",
        "sprint": 13, "patch": 80, "evidence_class": "diagnostic",
        "frozen": False, "publication_eligible": False,
        "authority_sha256": hashlib.sha256(canonical(authority)).hexdigest(),
        "role_authority_sha256": hashlib.sha256(canonical(role_authority)).hexdigest(),
        "presentation": {
            "method": authority["presentation"]["method"],
            "causal_to_scoring_or_decision": False,
            "human_blind_claim": False,
            "all_profile_answers_generated_before_oracle_scoring": True,
        },
        "denominators": {"strata": 5, "tasks": 60, "development_tasks": 40, "confirmation_tasks": 20, "unique_query_tuples": 60},
        "strata": summaries, "tasks": rows,
        "aggregate": {
            "qualified_strata": sum(item["qualified"] for item in summaries),
            "deferred_strata": sum(not item["qualified"] for item in summaries),
            "incremental_gains": sum(item["development_incremental_gains"] + item["confirmation_incremental_gains"] for item in summaries),
            "regressions": sum(item["regressions"] for item in summaries),
            "incorrect_promotions": sum(item["incorrect_promotions"] for item in summaries),
        },
        "public_boundary": copy.deepcopy(authority["public_boundary"]),
        "next_decision": {
            "owner": "S13-P080-LC-08B", "runtime_private_projection_authorized": False,
            "public_projection_authorized": False, "score_change_authorized": False,
            "qualified_private_facets": [item["stratum"] for item in summaries if item["qualified"]],
            "retained_existing_facets": [item["stratum"] for item in summaries if not item["qualified"]],
        },
    }
    if enforce_clean:
        require(result["aggregate"]["regressions"] == 0 and result["aggregate"]["incorrect_promotions"] == 0, "evaluation contains regression or incorrect promotion")
    return result


def negative_oracles(authority: dict[str, Any], role_authority: dict[str, Any]) -> int:
    mutations: list[dict[str, Any]] = []
    value = copy.deepcopy(authority); value["patch"] = False; mutations.append(value)
    value = copy.deepcopy(authority); value["tasks"].append(copy.deepcopy(value["tasks"][0])); mutations.append(value)
    value = copy.deepcopy(authority); value["acceptance"]["pooling_across_strata_permitted"] = True; mutations.append(value)
    value = copy.deepcopy(authority); value["presentation"]["human_blind_claim"] = True; mutations.append(value)
    value = copy.deepcopy(authority); value["presentation"]["causal_to_scoring_or_decision"] = True; mutations.append(value)
    value = copy.deepcopy(authority); value["public_boundary"]["score_changes"] = 1; mutations.append(value)
    value = copy.deepcopy(authority); value["source_authorities"][0]["sha256"] = "0" * 63; mutations.append(value)
    # Reuse one development query as confirmation under a new ID.
    value = copy.deepcopy(authority)
    dev = next(x for x in value["tasks"] if x["stratum"] == "generic_control" and x["phase"] == "development")
    conf = next(x for x in value["tasks"] if x["stratum"] == "generic_control" and x["phase"] == "confirmation")
    for key in ("operation", "register", "argument_index", "oracle"):
        conf[key] = dev[key]
    mutations.append(value)
    rejected = 0
    for mutation in mutations:
        try: validate_authority(mutation, authenticate_sources=False)
        except TaskValueError: rejected += 1
        else: raise TaskValueError("mutated role-task authority was accepted")

    # Full ABI misbinding must fail in the role-decision validator.
    wrong_role = copy.deepcopy(role_authority)
    next(x for x in wrong_role["register_roles"] if x["register"] == "rdx")["sysv_call_argument_index"] = None
    next(x for x in wrong_role["register_roles"] if x["register"] == "r13")["sysv_call_argument_index"] = 3
    try: role_records(wrong_role)
    except Exception: rejected += 1
    else: raise TaskValueError("wrong SysV argument-three map was accepted")

    # Presentation is non-causal: changing the seed may reorder display only.
    changed = copy.deepcopy(authority)
    changed["presentation"]["seed_sha256"] = "f" * 64
    result_a = evaluate(authority, role_authority)
    result_b = evaluate(changed, role_authority)
    require(result_a["strata"] == result_b["strata"] and result_a["aggregate"] == result_b["aggregate"], "presentation order changed decisions")
    rejected += 1
    return rejected


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
        require(canonical(load(args.expected)) == canonical(result), "role-task expected result changed")
    if args.result is not None:
        require(not args.result.exists(), f"result already exists: {args.result}")
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    decisions = {item["stratum"]: item["qualified"] for item in result["strata"]}
    print(
        "sprint13-register-role-task-value-smoke: ok version=2 strata=5 tasks=60 unique_queries=60 "
        f"qualified={result['aggregate']['qualified_strata']} deferred={result['aggregate']['deferred_strata']} "
        f"generic={'qualify' if decisions['generic_control'] else 'defer'} "
        f"sysv={'qualify' if decisions['sysv_call_arguments'] else 'defer'} "
        f"linux_syscall={'qualify' if decisions['linux_syscall_arguments'] else 'defer'} "
        f"syscall_number={'qualify' if decisions['syscall_number'] else 'defer'} "
        f"pivot={'qualify' if decisions['stack_pivot'] else 'defer'} "
        f"incremental_gains={result['aggregate']['incremental_gains']} regressions=0 incorrect_promotions=0 "
        f"negative_oracles={negatives} human_blind_claim=0 presentation_causal=0 public_fields_added=0 score_changes=0 schema_changed=0"
    )
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (TaskValueError, OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"sprint13-register-role-task-value-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
