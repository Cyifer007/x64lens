#!/usr/bin/env python3
"""Execute the Sprint 12 non-reinterpretive public role/property policy gate.

The gate authenticates the unchanged public mitigation/reporting surface,
preserves the existing coarse ``mitigations.pie`` indicator, and evaluates every
required prerequisite without converting diagnostic private facts into public
PIE/DSO, IBT, SHSTK, or runtime-CET claims.  The current authority deliberately
records a machine-readable deferral.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ID = "x64lens-sprint12-role-property-public-policy-result-v1"


class PolicyError(RuntimeError):
    """Raised when the policy authority or public source surface disagrees."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyError(message)


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def path_identity(path: Path, label: str, display: str) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"{label} is not a regular file: {display}")
    metadata = path.stat()
    data = path.read_bytes()
    post = path.stat()
    require(
        (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)
        == (post.st_dev, post.st_ino, post.st_size, post.st_mtime_ns, post.st_ctime_ns),
        f"{label} changed while hashing: {display}",
    )
    return {
        "path": display,
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }


def file_identity(relative: str) -> dict[str, Any]:
    return path_identity(ROOT / relative, "policy source", relative)


def require_authority(value: Any) -> dict[str, Any]:
    require(isinstance(value, dict), "public-policy authority must be an object")
    require(set(value) == {
        "authority_id", "evidence_class", "frozen", "publication_eligible",
        "policy_style", "schema_version", "decision", "decision_reason",
        "existing_public_surface", "source_identity", "prerequisites",
        "authorization_rule", "deferral_effects",
    }, "public-policy authority fields changed")
    require(value["authority_id"] == "sprint12-role-property-public-policy-v1",
            "public-policy authority id changed")
    require(value["evidence_class"] == "decision" and value["frozen"] is False
            and value["publication_eligible"] is False,
            "public-policy evidence boundary changed")
    require(value["policy_style"] == "non-reinterpretive" and value["schema_version"] == "0.2.0",
            "public-policy compatibility boundary changed")
    require(value["decision"] in {"defer", "authorize"}, "unsupported public-policy decision")

    surface = value["existing_public_surface"]
    require(isinstance(surface, dict) and set(surface) == {
        "coarse_pie_field", "coarse_pie_meaning", "required_direct_mitigation_properties",
        "forbidden_new_direct_mitigation_properties", "forbidden_report_labels",
    }, "public surface authority changed")
    require(surface["coarse_pie_field"] == "mitigations.pie", "existing PIE field identity changed")
    for key in ("required_direct_mitigation_properties", "forbidden_new_direct_mitigation_properties",
                "forbidden_report_labels"):
        require(isinstance(surface[key], list) and all(isinstance(item, str) and item for item in surface[key]),
                f"invalid public surface list: {key}")
        require(len(surface[key]) == len(set(surface[key])), f"duplicate public surface entry: {key}")

    source_identity = value["source_identity"]
    require(isinstance(source_identity, dict) and source_identity, "missing public-policy source identity")
    require(all(isinstance(path, str) and isinstance(digest, str) and len(digest) == 64
                for path, digest in source_identity.items()), "invalid public-policy source identity")

    prereqs = value["prerequisites"]
    require(isinstance(prereqs, list) and prereqs, "public-policy prerequisites are missing")
    ids: set[str] = set()
    for index, item in enumerate(prereqs):
        require(isinstance(item, dict) and set(item) == {
            "id", "required_for_authorization", "status", "evidence"
        }, f"public-policy prerequisite fields changed: {index}")
        require(isinstance(item["id"], str) and item["id"] not in ids, f"duplicate prerequisite id: {item['id']}")
        ids.add(item["id"])
        require(type(item["required_for_authorization"]) is bool, f"invalid prerequisite requirement: {item['id']}")
        require(isinstance(item["status"], str) and item["status"], f"invalid prerequisite status: {item['id']}")
        require(isinstance(item["evidence"], str) and item["evidence"], f"invalid prerequisite evidence: {item['id']}")

    rule = value["authorization_rule"]
    require(isinstance(rule, dict) and set(rule) == {
        "authorize_only_when_all_required_statuses_equal", "current_authorization",
        "open_or_pending_required_prerequisite_count", "public_fields_added",
        "existing_field_reinterpreted",
    }, "authorization rule changed")
    require(rule["authorize_only_when_all_required_statuses_equal"] == "passed",
            "authorization success state changed")
    require(type(rule["current_authorization"]) is bool
            and type(rule["open_or_pending_required_prerequisite_count"]) is int
            and type(rule["public_fields_added"]) is int
            and type(rule["existing_field_reinterpreted"]) is bool,
            "authorization rule types changed")

    effects = value["deferral_effects"]
    require(isinstance(effects, dict) and set(effects) == {
        "preserve_private_role_property_facts", "preserve_existing_coarse_pie_field",
        "add_role_derived_pie_dso_field", "add_public_ibt_field", "add_public_shstk_field",
        "claim_runtime_cet_enforcement", "next_owner",
    }, "deferral effects changed")
    return value


def evaluate(authority_path: Path) -> dict[str, Any]:
    authority_path = authority_path.resolve(strict=True)
    authority = require_authority(load_json(authority_path))
    authority_identity = path_identity(authority_path, "public-policy authority", str(authority_path))

    observed_sources: dict[str, dict[str, Any]] = {}
    for relative, expected_sha in sorted(authority["source_identity"].items()):
        observed = file_identity(relative)
        require(observed["sha256"] == expected_sha, f"public-policy source identity changed: {relative}")
        observed_sources[relative] = observed

    schema = load_json(ROOT / "schemas/x64lens-report.schema.json")
    require(isinstance(schema, dict) and schema.get("$schema"), "public schema is malformed")
    mitigations = schema.get("properties", {}).get("mitigations", {})
    direct_properties = mitigations.get("properties", {})
    require(isinstance(direct_properties, dict), "public mitigation schema properties are unavailable")
    observed_property_names = sorted(direct_properties)
    expected_property_names = sorted(authority["existing_public_surface"]["required_direct_mitigation_properties"])
    require(observed_property_names == expected_property_names,
            f"public mitigation property set changed: expected={expected_property_names} observed={observed_property_names}")
    require("pie" in mitigations.get("required", []), "existing coarse PIE field is no longer required")
    forbidden_properties = set(authority["existing_public_surface"]["forbidden_new_direct_mitigation_properties"])
    require(not (forbidden_properties & set(observed_property_names)), "a deferred role/property field is public")

    report_bytes = (ROOT / "src/report_text.asm").read_bytes() + b"\n" + (ROOT / "src/report_json.asm").read_bytes()
    for label in authority["existing_public_surface"]["forbidden_report_labels"]:
        require(label.encode("utf-8") not in report_bytes, f"deferred public report label is present: {label}")

    required = [item for item in authority["prerequisites"] if item["required_for_authorization"]]
    not_passed = [item for item in required if item["status"] != "passed"]
    rule = authority["authorization_rule"]
    require(len(not_passed) == rule["open_or_pending_required_prerequisite_count"],
            "required prerequisite denominator changed")
    authorization_possible = not not_passed
    require(rule["current_authorization"] == (authority["decision"] == "authorize"),
            "decision and authorization flag disagree")
    if authority["decision"] == "authorize":
        require(authorization_possible, "public authorization requested with open prerequisites")
        require(rule["public_fields_added"] > 0, "authorization adds no reviewed public field")
    else:
        require(not authorization_possible, "deferral is inconsistent with all prerequisites passed")
        require(rule["public_fields_added"] == 0 and rule["existing_field_reinterpreted"] is False,
                "deferral changed a public field")
        effects = authority["deferral_effects"]
        require(effects["preserve_private_role_property_facts"] is True
                and effects["preserve_existing_coarse_pie_field"] is True,
                "deferral failed to preserve current facts or PIE surface")
        require(effects["add_role_derived_pie_dso_field"] is False
                and effects["add_public_ibt_field"] is False
                and effects["add_public_shstk_field"] is False
                and effects["claim_runtime_cet_enforcement"] is False,
                "deferral authorized a prohibited projection or runtime claim")

    return {
        "format": SCHEMA_ID,
        "authority_id": authority["authority_id"],
        "authority_sha256": authority_identity["sha256"],
        "evidence_class": "decision",
        "frozen": False,
        "publication_eligible": False,
        "policy_style": "non-reinterpretive",
        "schema_version": authority["schema_version"],
        "decision": authority["decision"],
        "authorization": rule["current_authorization"],
        "public_fields_added": rule["public_fields_added"],
        "existing_field_reinterpreted": rule["existing_field_reinterpreted"],
        "required_prerequisite_count": len(required),
        "open_or_pending_required_prerequisite_count": len(not_passed),
        "open_or_pending_required_prerequisites": [
            {"id": item["id"], "status": item["status"]} for item in not_passed
        ],
        "existing_coarse_pie_preserved": True,
        "observed_direct_mitigation_properties": observed_property_names,
        "deferred_public_properties": sorted(forbidden_properties),
        "runtime_cet_enforcement_claimed": False,
        "source_identities": observed_sources,
    }


def seal_result(result: Path, manifest: dict[str, Any]) -> None:
    require(not result.exists(), f"policy result already exists: {result}")
    result.mkdir(parents=True)
    (result / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = sorted(path for path in result.rglob("*") if path.is_file())
    (result / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256_bytes(path.read_bytes())}  {path.relative_to(result).as_posix()}\n" for path in files),
        encoding="utf-8",
    )
    for path in sorted(result.rglob("*"), reverse=True):
        path.chmod(0o555 if path.is_dir() else 0o444)
    result.chmod(0o555)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path)
    args = parser.parse_args()
    manifest = evaluate(args.authority)
    if args.result_dir is not None:
        seal_result(Path(os.path.abspath(args.result_dir)), manifest)
    print(
        "sprint12-role-property-public-policy-smoke: ok "
        f"decision={manifest['decision']} authorization={int(manifest['authorization'])} "
        f"required={manifest['required_prerequisite_count']} "
        f"open_or_pending={manifest['open_or_pending_required_prerequisite_count']} "
        "public_fields_added=0 existing_pie_preserved=1 runtime_cet_claim=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PolicyError, OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"sprint12-role-property-public-policy-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
