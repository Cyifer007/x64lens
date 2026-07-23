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
    load_campaign,
    load_regular_path,
    require,
    require_regular_path_identity,
    safe_id,
    sha256_bytes,
)

AUTHORITY_SCHEMA = 3
AUTHORITY_ID = "sprint11-diagnostic-task-definitions-v3"
CALIBRATOR_ID = "x64lens-sprint11-address-coordinate-calibrator-v1"
ARTIFACT_SCHEMA = 1
SPEC_SCHEMA = 2
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




_GENERATOR_MODULES: dict[str, Any] = {}


def generator_module(path: Path, tool_id: str):
    key = str(path)
    if key in _GENERATOR_MODULES:
        return _GENERATOR_MODULES[key]
    module_spec = importlib.util.spec_from_file_location(f"x64lens_coordinate_generator_{tool_id}", path)
    require(module_spec is not None and module_spec.loader is not None, f"cannot load {tool_id} relation generator")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    _GENERATOR_MODULES[key] = module
    return module


def reproduce_relation_artifact(
    *,
    value: dict[str, Any],
    tool_id: str,
    campaign_result: Path,
    run_id: str,
    task_authority: Path,
    generator_path: Path,
) -> None:
    """Rebuild normalized fields from retained native evidence in-process."""
    module = generator_module(generator_path, tool_id)
    if tool_id == "x64lens":
        context = load_campaign(campaign_result)
        try:
            authority, authority_identity, _ = load_authority(
                task_authority, schema_version=AUTHORITY_SCHEMA, authority_id=AUTHORITY_ID
            )
            del authority
            _source, generator_identity = load_regular_path(generator_path, MAX_MEMBER_BYTES, "x64lens relation extractor")
            row = context.row(run_id)
            report_data, report_identity = context.load_row_member(row, "stdout")
            expected = module.build_artifact(
                context=context,
                row=row,
                report=module.parse_report(report_data),
                report_identity=report_identity,
                authority_identity=authority_identity,
                extractor_identity=generator_identity,
            )
            expected_bytes = canonical_json_bytes(expected)
        finally:
            context.close()
    else:
        data, generated_context, _selected, _authority_identity, _adapter_identity = module.normalize(
            argparse.Namespace(
                campaign_result=campaign_result,
                run_id=run_id,
                task_authority=task_authority,
                output=Path("/unused"),
            )
        )
        generated_context.close()
        expected_bytes = data
    require(
        expected_bytes == canonical_json_bytes(value),
        f"{tool_id} relation artifact does not reproduce from retained native evidence",
    )

def authenticate_relation_artifact(
    *,
    value: dict[str, Any],
    tool_id: str,
    campaign_result: Path,
    authority: dict[str, Any],
    authority_identity: dict[str, Any],
    repository_root: Path,
    reproduce: bool = True,
) -> tuple[str, str]:
    """Bind one relation artifact back to its exact authenticated runner row."""
    context = load_campaign(campaign_result)
    try:
        require(value.get("evidence_class") == "diagnostic", f"{tool_id} relation artifact is not diagnostic evidence")
        require(value.get("frozen") is False and value.get("publication_eligible") is False, f"{tool_id} relation artifact claim boundary mismatch")
        if tool_id == "x64lens":
            binding = value.get("campaign")
            require(isinstance(binding, dict), "x64lens relation campaign binding is missing")
            require(binding.get("campaign_id") == context.manifest["campaign_id"], "x64lens relation campaign id mismatch")
            require(binding.get("manifest_sha256") == context.manifest_identity["sha256"], "x64lens relation manifest hash mismatch")
            require(binding.get("rows_sha256") == context.rows_identity["sha256"], "x64lens relation rows hash mismatch")
            run_id = safe_id(binding.get("run_id"), "x64lens relation run id")
            row = context.row(run_id)
            require(binding.get("phase") == row["phase"] == "measured", "x64lens relation phase mismatch")
            for key in ("condition_id", "task_scope", "profile_id", "command_json", "command_cwd"):
                require(binding.get(key) == row[key], f"x64lens relation {key} mismatch")
            auth = value.get("authority")
            require(isinstance(auth, dict) and auth.get("id") == AUTHORITY_ID, "x64lens relation authority id mismatch")
            require(auth.get("sha256") == authority_identity["sha256"] and auth.get("size_bytes") == authority_identity["size_bytes"], "x64lens relation authority identity mismatch")
            policy = authority["x64lens_relation_policy"]
            extractor = value.get("extractor")
            require(isinstance(extractor, dict) and extractor.get("id") == policy["extractor_id"], "x64lens relation extractor id mismatch")
            extractor_path = (repository_root / policy["extractor_path"]).resolve(strict=True)
            generator_path = extractor_path
            _data, extractor_identity = load_regular_path(extractor_path, MAX_MEMBER_BYTES, "x64lens relation extractor")
            require(extractor.get("sha256") == extractor_identity["sha256"] and extractor.get("size_bytes") == extractor_identity["size_bytes"], "x64lens relation extractor identity mismatch")
            native = value.get("native_report")
            require(isinstance(native, dict), "x64lens native report binding is missing")
            stdout_data, stdout_identity = context.load_row_member(row, "stdout")
            del stdout_data
            require(native.get("relative_path") == row["stdout_path"], "x64lens native report path mismatch")
            require(native.get("sha256") == stdout_identity["sha256"] and native.get("size_bytes") == stdout_identity["size_bytes"], "x64lens native report identity mismatch")
        else:
            binding = value.get("campaign_binding")
            require(isinstance(binding, dict), f"{tool_id} campaign binding is missing")
            require(binding.get("campaign_id") == context.manifest["campaign_id"], f"{tool_id} campaign id mismatch")
            require(binding.get("manifest_sha256") == context.manifest_identity["sha256"], f"{tool_id} manifest hash mismatch")
            require(binding.get("rows_sha256") == context.rows_identity["sha256"], f"{tool_id} rows hash mismatch")
            run_id = safe_id(binding.get("run_id"), f"{tool_id} relation run id")
            row = context.row(run_id)
            require(binding.get("row_sha256") == sha256_bytes(canonical_json_bytes(row)), f"{tool_id} runner row hash mismatch")
            auth = value.get("task_authority")
            require(isinstance(auth, dict) and auth.get("id") == AUTHORITY_ID, f"{tool_id} task authority id mismatch")
            require(auth.get("sha256") == authority_identity["sha256"] and auth.get("size_bytes") == authority_identity["size_bytes"], f"{tool_id} task authority identity mismatch")
            baseline = next(item for item in authority["baselines"] if item["id"] == tool_id)
            adapter = value.get("adapter")
            require(isinstance(adapter, dict) and adapter.get("id") == baseline["adapter"]["id"], f"{tool_id} adapter id mismatch")
            adapter_path = (repository_root / baseline["adapter"]["path"]).resolve(strict=True)
            generator_path = adapter_path
            _data, adapter_identity = load_regular_path(adapter_path, MAX_MEMBER_BYTES, f"{tool_id} adapter")
            require(adapter.get("sha256") == adapter_identity["sha256"] and adapter.get("size_bytes") == adapter_identity["size_bytes"], f"{tool_id} adapter identity mismatch")
            execution = value.get("execution")
            require(isinstance(execution, dict), f"{tool_id} execution binding is missing")
            for key in ("condition_id", "task_scope", "run_id", "phase", "process_outcome", "outcome"):
                require(str(execution.get(key)) == row[key], f"{tool_id} execution {key} mismatch")
            native = value.get("native_output")
            require(isinstance(native, dict), f"{tool_id} native output binding is missing")
            for stream in ("stdout", "stderr"):
                _data, identity = context.load_row_member(row, stream)
                require(native.get(f"{stream}_path") == row[f"{stream}_path"], f"{tool_id} native {stream} path mismatch")
                require(native.get(f"{stream}_sha256") == identity["sha256"] and native.get(f"{stream}_size_bytes") == identity["size_bytes"], f"{tool_id} native {stream} identity mismatch")
        require(row["tool_id"] == tool_id, f"{tool_id} runner row tool mismatch")
        if reproduce:
            reproduce_relation_artifact(
                value=value,
                tool_id=tool_id,
                campaign_result=campaign_result,
                run_id=run_id,
                task_authority=Path(authority_identity["path_resolved"]),
                generator_path=generator_path,
            )
        target = value.get("target")
        require(isinstance(target, dict) and target.get("id") == row["target_id"] and target.get("sha256") == row["target_sha256"], f"{tool_id} target binding mismatch")
        require(row["process_outcome"] == "success" and row["outcome"] == "success", f"{tool_id} relation is not bound to a successful row")
        return row["target_id"], row["target_sha256"]
    finally:
        context.close()


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
    artifact_bindings: list[tuple[dict[str, Any], str, Path]] = []
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
            descriptor = artifacts[tool_id]
            require(isinstance(descriptor, dict) and set(descriptor) == {"path", "campaign_result"}, f"{role_id} {tool_id} artifact descriptor is invalid")
            path = Path(descriptor["path"])
            campaign_result = Path(descriptor["campaign_result"])
            value, identity = load_json_file(path, f"{role_id} {tool_id} relation artifact")
            artifact_inputs.append((Path(os.path.abspath(path)), identity, f"{role_id} {tool_id} relation artifact"))
            authenticated_target_id, authenticated_target_sha = authenticate_relation_artifact(
                value=value,
                tool_id=tool_id,
                campaign_result=campaign_result,
                authority=authority,
                authority_identity=authority_identity,
                repository_root=repository_root,
            )
            _addresses, _offsets, artifact_target_id, artifact_target_sha = relation_sets(value, tool_id)
            require(artifact_target_id == authenticated_target_id and artifact_target_sha == authenticated_target_sha, f"{role_id} {tool_id} relation/campaign binding mismatch")
            require(artifact_target_id == target_id and artifact_target_sha == target["sha256"], f"{role_id} {tool_id} target binding mismatch")
            artifact_bindings.append((value, tool_id, campaign_result))
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
        for value, tool_id, campaign_result in artifact_bindings:
            authenticate_relation_artifact(
                value=value,
                tool_id=tool_id,
                campaign_result=campaign_result,
                authority=authority,
                authority_identity=authority_identity,
                repository_root=repository_root,
                reproduce=False,
            )
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
