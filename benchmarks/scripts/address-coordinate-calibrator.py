#!/usr/bin/env python3
"""Calibrate baseline address coordinates across ELF role-controlled targets.

The calibrator consumes authenticated x64lens and baseline relation artifacts
for one ET_EXEC, one PIE-intended ET_DYN, and one shared ET_DYN corpus target.
It determines whether each baseline displays x64lens virtual-address starts,
file-offset starts, an ambiguous coordinate, or a mismatch. No address is used
for comparative coverage until this calibration succeeds.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from diagnostic_artifact import (  # noqa: E402
    ArtifactError,
    MAX_JSON_BYTES,
    MAX_MEMBER_BYTES,
    atomic_publish_bytes,
    canonical_json_bytes,
    load_authority,
    load_regular_path,
    require,
    require_regular_path_identity,
    safe_id,
)

AUTHORITY_SCHEMA = 3
AUTHORITY_ID = "sprint11-diagnostic-task-definitions-v3"
CALIBRATOR_ID = "x64lens-sprint11-address-coordinate-calibrator-v1"
ARTIFACT_SCHEMA = 1
SPEC_SCHEMA = 1
REQUIRED_TOOLS = ("x64lens", "ropgadget", "ropper", "ropr")
REQUIRED_ROLES = ("et_exec", "pie_et_dyn", "shared_et_dyn")


class CalibrationError(ArtifactError):
    """Raised when address-coordinate evidence is incomplete or inconsistent."""


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-result", type=Path, required=True)
    parser.add_argument("--input-spec", type=Path, required=True)
    parser.add_argument("--task-authority", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def load_builder(repository_root: Path):
    path = repository_root / "benchmarks/scripts/build-provisional-corpus.py"
    module_spec = importlib.util.spec_from_file_location("x64lens_p059_corpus_verifier", path)
    require(module_spec is not None and module_spec.loader is not None, "cannot load provisional corpus verifier")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module, path.resolve(strict=True)


def load_json_file(path: Path, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    data, identity = load_regular_path(path, MAX_JSON_BYTES, label)
    try:
        value = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CalibrationError(f"cannot parse {label}: {exc}") from exc
    require(isinstance(value, dict), f"{label} must be an object")
    return value, identity


def relation_sets(value: dict[str, Any], tool_id: str) -> tuple[set[str], set[str] | None, str, str]:
    if tool_id == "x64lens":
        require(value.get("schema_version") == 1 and value.get("artifact_id") == "x64lens-sprint11-relation-extractor-v1", "invalid x64lens relation artifact")
        relations = value.get("normalized_relations")
        require(isinstance(relations, list), "x64lens normalized relation array is missing")
        virtual = {item["virtual_address_start"] for item in relations if isinstance(item, dict) and item.get("relation_id") == "canonical_exact_pop_rdi_ret"}
        offsets = {item["file_offset_start"] for item in relations if isinstance(item, dict) and item.get("relation_id") == "canonical_exact_pop_rdi_ret"}
        target = value.get("target")
        require(isinstance(target, dict), "x64lens relation target is missing")
        return virtual, offsets, target.get("id"), target.get("sha256")
    require(value.get("schema_version") == 2 and value.get("artifact_type") == "x64lens-sprint11-baseline-normalization", f"invalid {tool_id} normalization artifact")
    tool = value.get("tool")
    target = value.get("target")
    require(isinstance(tool, dict) and tool.get("id") == tool_id, f"normalization artifact tool mismatch: {tool_id}")
    require(isinstance(target, dict), f"normalization target is missing: {tool_id}")
    normalized = value.get("normalized_relations")
    require(isinstance(normalized, dict), f"normalization relations are missing: {tool_id}")
    exact = normalized.get("canonical_exact_pop_rdi_ret")
    require(isinstance(exact, dict) and exact.get("status") in {"observed", "observed_zero"}, f"exact relation state is invalid: {tool_id}")
    records = exact.get("records")
    require(isinstance(records, list), f"exact relation records are missing: {tool_id}")
    addresses = {record["address"] for record in records if isinstance(record, dict)}
    return addresses, None, target.get("id"), target.get("sha256")


def classify(baseline: set[str], virtual: set[str], offsets: set[str]) -> dict[str, Any]:
    if not baseline or not virtual:
        status = "insufficient_relation_evidence"
    else:
        matches_virtual = baseline == virtual
        matches_offset = baseline == offsets
        if matches_virtual and matches_offset:
            status = "ambiguous"
        elif matches_virtual:
            status = "virtual_address"
        elif matches_offset:
            status = "file_offset"
        else:
            status = "mismatch"
    return {
        "status": status,
        "baseline_relation_count": len(baseline),
        "x64lens_virtual_relation_count": len(virtual),
        "x64lens_file_offset_relation_count": len(offsets),
        "virtual_intersection_count": len(baseline & virtual),
        "file_offset_intersection_count": len(baseline & offsets),
    }


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    authority, authority_identity, _ = load_authority(args.task_authority, schema_version=AUTHORITY_SCHEMA, authority_id=AUTHORITY_ID)
    policy = authority.get("address_coordinate_policy")
    require(isinstance(policy, dict), "address-coordinate policy is missing")
    require(policy.get("calibrator_id") == CALIBRATOR_ID and policy.get("artifact_schema_version") == ARTIFACT_SCHEMA, "address-coordinate authority changed")
    repository_root = Path(os.path.abspath(args.task_authority)).parent.parent.parent
    calibrator_path = Path(__file__).resolve(strict=True)
    require(calibrator_path == (repository_root / policy["calibrator_path"]).resolve(strict=True), "running calibrator does not match authority path")
    _calibrator_data, calibrator_identity = load_regular_path(
        calibrator_path, MAX_MEMBER_BYTES, "address-coordinate calibrator"
    )

    spec, spec_identity = load_json_file(args.input_spec, "coordinate calibration input spec")
    require(spec.get("schema_version") == SPEC_SCHEMA, "unsupported coordinate calibration input schema")
    roles = spec.get("roles")
    require(isinstance(roles, list) and len(roles) == len(REQUIRED_ROLES), "coordinate input must contain exactly three roles")
    role_map: dict[str, dict[str, Any]] = {}
    for record in roles:
        require(isinstance(record, dict), "coordinate role record is invalid")
        role_id = safe_id(record.get("id"), "coordinate role id")
        require(role_id not in role_map, f"duplicate coordinate role: {role_id}")
        role_map[role_id] = record
    require(tuple(role_map) == REQUIRED_ROLES, "coordinate roles are missing or out of canonical order")

    builder, builder_path = load_builder(repository_root)
    _builder_data, builder_identity = load_regular_path(builder_path, MAX_MEMBER_BYTES, "corpus verifier")
    corpus_root = Path(os.path.abspath(args.corpus_result))
    corpus_manifest = builder.verify_corpus(corpus_root)
    target_by_id = {item["id"]: item for item in corpus_manifest["targets"]}
    role_policy = {item["id"]: item for item in policy["required_roles"]}

    artifact_inputs: list[tuple[Path, dict[str, Any], str]] = []
    parsed: dict[tuple[str, str], dict[str, Any]] = {}
    role_targets: dict[str, dict[str, Any]] = {}
    for role_id in REQUIRED_ROLES:
        record = role_map[role_id]
        target_id = safe_id(record.get("corpus_target_id"), f"{role_id} corpus target id")
        require(target_id in target_by_id, f"unknown corpus target for role {role_id}")
        target = target_by_id[target_id]
        expected = role_policy[role_id]
        require(target["artifact_id"] == expected["artifact_id"] and target["elf"]["elf_type"] == expected["elf_type"], f"corpus target does not satisfy role {role_id}")
        role_targets[role_id] = target
        artifacts = record.get("artifacts")
        require(isinstance(artifacts, dict) and tuple(artifacts) == REQUIRED_TOOLS, f"role {role_id} must name all tools in canonical order")
        for tool_id in REQUIRED_TOOLS:
            path = Path(artifacts[tool_id])
            value, identity = load_json_file(path, f"{role_id} {tool_id} relation artifact")
            artifact_inputs.append((Path(os.path.abspath(path)), identity, f"{role_id} {tool_id} relation artifact"))
            _addresses, _offsets, artifact_target_id, artifact_target_sha = relation_sets(value, tool_id)
            require(artifact_target_id == target_id and artifact_target_sha == target["sha256"], f"{role_id} {tool_id} target binding mismatch")
            parsed[(role_id, tool_id)] = value

    by_tool: dict[str, Any] = {}
    role_results: list[dict[str, Any]] = []
    for tool_id in REQUIRED_TOOLS[1:]:
        statuses: list[str] = []
        per_role: list[dict[str, Any]] = []
        for role_id in REQUIRED_ROLES:
            x_value = parsed[(role_id, "x64lens")]
            b_value = parsed[(role_id, tool_id)]
            virtual, offsets, _target_id, _target_sha = relation_sets(x_value, "x64lens")
            baseline, _unused, _target_id, _target_sha = relation_sets(b_value, tool_id)
            assert offsets is not None
            result = classify(baseline, virtual, offsets)
            result.update({"role_id": role_id, "corpus_target_id": role_targets[role_id]["id"], "target_sha256": role_targets[role_id]["sha256"]})
            statuses.append(result["status"])
            per_role.append(result)
            role_results.append({"tool_id": tool_id, **result})
        usable = {status for status in statuses if status in {"virtual_address", "file_offset"}}
        if len(usable) == 1 and all(status in usable for status in statuses):
            overall = next(iter(usable))
        elif all(status == "insufficient_relation_evidence" for status in statuses):
            overall = "insufficient_relation_evidence"
        elif "mismatch" in statuses:
            overall = "mismatch"
        else:
            overall = "mixed_or_ambiguous"
        by_tool[tool_id] = {"status": overall, "roles": per_role}

    artifact = {
        "schema_version": ARTIFACT_SCHEMA,
        "artifact_id": CALIBRATOR_ID,
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "calibrator": {"id": CALIBRATOR_ID, "sha256": calibrator_identity["sha256"], "size_bytes": calibrator_identity["size_bytes"]},
        "authority": {"id": AUTHORITY_ID, "sha256": authority_identity["sha256"], "size_bytes": authority_identity["size_bytes"]},
        "corpus": {"corpus_id": corpus_manifest["corpus_id"], "manifest_sha256": builder.sha256_file(corpus_root / "corpus-manifest.json"), "target_count": corpus_manifest["target_count"]},
        "input_spec": {"sha256": spec_identity["sha256"], "size_bytes": spec_identity["size_bytes"]},
        "tools": by_tool,
        "role_results": role_results,
        "claim_boundaries": [
            "Displayed baseline addresses are not compared with x64lens until the same-target coordinate matches across ET_EXEC, PIE-intended ET_DYN, and shared ET_DYN roles.",
            "A mismatch or ambiguity remains explicit and prevents coverage aggregation.",
            "Role labels are bound to the verified provisional corpus manifest; ET_DYN alone is not used to infer PIE versus shared-object identity.",
        ],
    }

    def reauthenticate() -> None:
        builder.verify_corpus(corpus_root)
        require_regular_path_identity(args.task_authority, authority_identity, MAX_JSON_BYTES, "task authority")
        require_regular_path_identity(args.input_spec, spec_identity, MAX_JSON_BYTES, "coordinate calibration input spec")
        require_regular_path_identity(calibrator_path, calibrator_identity, MAX_MEMBER_BYTES, "address-coordinate calibrator")
        for path, identity, label in artifact_inputs:
            require_regular_path_identity(path, identity, MAX_JSON_BYTES, label)
        require_regular_path_identity(builder_path, builder_identity, MAX_MEMBER_BYTES, "corpus verifier")

    atomic_publish_bytes(args.output, canonical_json_bytes(artifact), reauthenticate=reauthenticate)
    calibrated = sum(1 for item in by_tool.values() if item["status"] in {"virtual_address", "file_offset"})
    print(f"address-coordinate-calibrator: ok tools=3 calibrated={calibrated} roles=3")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (ArtifactError, CalibrationError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"address-coordinate-calibrator: error: {exc}", file=sys.stderr)
        raise SystemExit(2)
