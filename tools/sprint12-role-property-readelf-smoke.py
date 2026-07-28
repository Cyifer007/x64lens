#!/usr/bin/env python3
"""Reconcile retained private role/property facts with GNU readelf evidence.

The comparator is a development oracle, not runtime authority.  Every held-out
object receives four authenticated readelf invocations.  Directly represented
or reproducibly derived fields must agree; ambiguous and unavailable fields stay
explicit rather than being coerced into agreement or a public policy decision.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FACT_FIELDS = (
    "status", "phnum", "role_state", "role_evidence", "interp_count",
    "flags1_count", "soname_count", "property_view_count",
    "property_contributor_count", "property_note_count",
    "property_feature_count", "property_feature_and", "property_feature_or",
    "property_unknown_count", "property_conflict_count",
    "property_overlap_count", "ibt_state", "shstk_state",
)
ROLE_UNKNOWN = 0
ROLE_EXECUTABLE = 1
ROLE_SHARED = 2
ROLE_AMBIGUOUS = 3
ROLE_CONTRADICTORY = 4
PROPERTY_UNKNOWN = 0
PROPERTY_ABSENT = 1
PROPERTY_PRESENT = 2
PROPERTY_CONTRADICTORY = 3
ROLE_ET_EXEC = 1 << 0
ROLE_ET_DYN = 1 << 1
ROLE_ENTRY = 1 << 2
ROLE_INTERP = 1 << 3
ROLE_DF1_PIE = 1 << 4
ROLE_SONAME = 1 << 5
ROLE_DUP_INTERP = 1 << 6
ROLE_DUP_FLAGS1 = 1 << 7
ROLE_DUP_SONAME = 1 << 8
ROLE_CONFLICT_FLAGS1 = 1 << 9
ROLE_CONFLICT_SONAME = 1 << 10
IBT = 1
SHSTK = 2


class ReconciliationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconciliationError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def identity(
    path: Path,
    label: str,
    *,
    executable: bool = False,
    allow_command_symlink: bool = False,
) -> dict[str, Any]:
    requested = Path(os.path.abspath(path))
    if not allow_command_symlink:
        require(not requested.is_symlink(), f"{label} may not be a symlink: {requested}")
    absolute = requested.resolve(strict=True)
    metadata = absolute.lstat()
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file: {absolute}")
    if executable:
        require(os.access(absolute, os.X_OK), f"{label} is not executable: {absolute}")
    data = absolute.read_bytes()
    return {
        "requested_path": str(requested),
        "path": str(absolute),
        "size_bytes": len(data),
        "sha256": sha256_bytes(data),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }


def load_authority(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    ident = identity(path, "readelf reconciliation authority")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "readelf authority must be an object")
    require(value.get("authority_id") == "sprint12-role-property-readelf-v1",
            "readelf authority id changed")
    require(value.get("evidence_class") == "diagnostic"
            and value.get("frozen") is False
            and value.get("publication_eligible") is False,
            "readelf authority evidence boundary changed")
    require(value.get("source_authority_id") == "sprint12-role-property-heldout-v1",
            "readelf source authority changed")
    require(value.get("object_count") == 96, "readelf authority object count changed")
    require(value.get("readelf_commands") == ["-hW", "-lW", "-dW", "-nW"],
            "readelf command authority changed")
    eligibility = value.get("field_eligibility")
    require(isinstance(eligibility, dict) and tuple(eligibility) == FACT_FIELDS,
            "readelf field eligibility is incomplete or reordered")
    require(all(isinstance(eligibility[field], dict)
                and eligibility[field].get("class") in {"direct", "derived", "ambiguous", "unavailable"}
                for field in FACT_FIELDS), "readelf field eligibility class is invalid")
    acceptance = value.get("acceptance")
    require(isinstance(acceptance, dict)
            and acceptance.get("accounted_objects") == 96
            and acceptance.get("readelf_processes") == 384
            and acceptance.get("eligible_unexplained_mismatches") == 0
            and acceptance.get("raw_outputs_retained") is True
            and acceptance.get("all_field_dispositions_retained") is True
            and acceptance.get("public_policy_decision_authorized") is False,
            "readelf acceptance authority changed")
    return value, ident


def verify_checksums(root: Path) -> None:
    path = root / "SHA256SUMS.txt"
    require(path.is_file() and not path.is_symlink(), "held-out checksum manifest is missing")
    listed: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        require(len(line) >= 67 and line[64:66] == "  ",
                f"invalid held-out checksum line {line_number}")
        digest, name = line[:64], line[66:]
        require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
                f"invalid held-out digest at line {line_number}")
        pure = Path(name)
        require(name and not pure.is_absolute() and ".." not in pure.parts and "\\" not in name,
                f"unsafe held-out checksum path: {name!r}")
        require(name not in listed and name != "SHA256SUMS.txt",
                f"duplicate held-out checksum path: {name}")
        member = root / name
        require(member.is_file() and not member.is_symlink(), f"missing held-out member: {name}")
        require(sha256_bytes(member.read_bytes()) == digest, f"held-out checksum mismatch: {name}")
        listed.add(name)
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    }
    require(actual == listed,
            f"held-out result member mismatch: missing={sorted(listed-actual)} extra={sorted(actual-listed)}")


def load_heldout(root: Path) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    require(root.is_dir() and not root.is_symlink(), "held-out result is unavailable")
    verify_checksums(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    require(isinstance(manifest, dict)
            and manifest.get("format") == "x64lens-sprint12-role-property-heldout-v2"
            and manifest.get("authority_id") == "sprint12-role-property-heldout-v1"
            and manifest.get("object_count") == 96
            and manifest.get("probe_run_count") == 288
            and manifest.get("public_command_count") == 384
            and manifest.get("fact_fields") == list(FACT_FIELDS)
            and manifest.get("expected_vectors_retained") is True
            and manifest.get("observed_vectors_retained") is True,
            "held-out result manifest is not the corrected v2 authority")
    with (root / "facts.tsv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    require(len(rows) == 96 and len({row["name"] for row in rows}) == 96,
            "held-out fact rows are incomplete or duplicated")
    for row in rows:
        require(all(f"observed_{field}" in row and f"expected_{field}" in row for field in FACT_FIELDS),
                f"held-out row omits fact vectors: {row.get('name')}")
    return manifest, rows, identity(root / "manifest.json", "held-out result manifest")


def run_readelf(readelf: Path, target: Path, option: str) -> dict[str, Any]:
    command = [str(readelf), option, str(target)]
    cp = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        check=False, timeout=10.0)
    return {
        "command": command,
        "option": option,
        "exit_code": cp.returncode,
        "stdout": cp.stdout,
        "stderr": cp.stderr,
        "stdout_sha256": sha256_bytes(cp.stdout),
        "stderr_sha256": sha256_bytes(cp.stderr),
    }


def first_match(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, re.MULTILINE)
    require(match is not None, f"readelf output omitted {label}")
    return match.group(1)


def parse_readelf(records: dict[str, dict[str, Any]]) -> tuple[dict[str, int], set[str], dict[str, str]]:
    header = records["-hW"]["stdout"].decode("utf-8", errors="replace")
    program = records["-lW"]["stdout"].decode("utf-8", errors="replace")
    dynamic = records["-dW"]["stdout"].decode("utf-8", errors="replace")
    notes = records["-nW"]["stdout"].decode("utf-8", errors="replace")
    note_stderr = records["-nW"]["stderr"].decode("utf-8", errors="replace")

    phnum = int(first_match(r"Number of program headers:\s*(\d+)", header, "PHNUM"))
    etype_text = first_match(r"^\s*Type:\s+(\S+)", header, "ELF type")
    entry = int(first_match(r"Entry point address:\s*(0x[0-9a-fA-F]+)", header, "entrypoint"), 16)
    interp_count = len(re.findall(r"^\s*INTERP\s", program, re.MULTILINE))
    flags_lines = re.findall(r"^.*\(FLAGS_1\).*?Flags:\s*(.*)$", dynamic, re.MULTILINE)
    soname_lines = re.findall(r"^.*\(SONAME\).*?\[(.*?)\]\s*$", dynamic, re.MULTILINE)

    evidence = 0
    if etype_text == "EXEC":
        evidence |= ROLE_ET_EXEC
    elif etype_text == "DYN":
        evidence |= ROLE_ET_DYN
    if entry:
        evidence |= ROLE_ENTRY
    if interp_count:
        evidence |= ROLE_INTERP
    if interp_count > 1:
        evidence |= ROLE_DUP_INTERP
    if len(flags_lines) > 1:
        evidence |= ROLE_DUP_FLAGS1
    if any(re.search(r"\bPIE\b", line) for line in flags_lines):
        evidence |= ROLE_DF1_PIE
    if len(set(flags_lines)) > 1:
        evidence |= ROLE_CONFLICT_FLAGS1
    if soname_lines:
        evidence |= ROLE_SONAME
    if len(soname_lines) > 1:
        evidence |= ROLE_DUP_SONAME
    if len(set(soname_lines)) > 1:
        evidence |= ROLE_CONFLICT_SONAME

    contradiction = evidence & (
        ROLE_DUP_INTERP | ROLE_DUP_FLAGS1 | ROLE_DUP_SONAME |
        ROLE_CONFLICT_FLAGS1 | ROLE_CONFLICT_SONAME
    )
    if contradiction:
        role_state = ROLE_CONTRADICTORY
    elif etype_text == "EXEC":
        role_state = ROLE_CONTRADICTORY if evidence & (ROLE_DF1_PIE | ROLE_SONAME) else ROLE_EXECUTABLE
    elif etype_text == "DYN":
        executable = bool(evidence & (ROLE_INTERP | ROLE_DF1_PIE))
        shared = bool(evidence & ROLE_SONAME)
        if executable and shared:
            role_state = ROLE_CONTRADICTORY
        elif executable:
            role_state = ROLE_EXECUTABLE
        elif shared and not entry:
            role_state = ROLE_SHARED
        elif entry:
            role_state = ROLE_AMBIGUOUS
        else:
            role_state = ROLE_UNKNOWN
    else:
        role_state = ROLE_UNKNOWN

    note_count = len(re.findall(r"NT_GNU_PROPERTY_TYPE_0", notes))
    feature_texts = [
        value.strip()
        for value in re.findall(
            r"x86 feature:\s*(.*?)(?=,\s*x86 feature:|\n|\r|$)",
            notes,
            re.DOTALL,
        )
    ]
    values: list[int] = []
    property_corrupt = bool(re.search(r"corrupt|truncated|invalid", notes + "\n" + note_stderr, re.I))
    for value_text in feature_texts:
        value = 0
        if re.search(r"\bIBT\b", value_text):
            value |= IBT
        if re.search(r"\bSHSTK\b", value_text):
            value |= SHSTK
        for unknown in re.findall(r"<unknown:\s*([0-9a-fA-F]+)>", value_text):
            value |= int(unknown, 16)
        values.append(value)

    facts = {
        "phnum": phnum,
        "role_state": role_state,
        "role_evidence": evidence,
        "interp_count": interp_count,
        "flags1_count": len(flags_lines),
        "soname_count": len(soname_lines),
        "property_view_count": note_count,
        "property_note_count": note_count,
        "property_feature_count": len(values),
    }
    if values:
        and_value = values[0]
        or_value = values[0]
        for value in values[1:]:
            and_value &= value
            or_value |= value
        facts["property_feature_and"] = and_value
        facts["property_feature_or"] = or_value
        facts["property_conflict_count"] = int(and_value != or_value)
        facts["ibt_state"] = PROPERTY_PRESENT if and_value & IBT else (
            PROPERTY_CONTRADICTORY if or_value & IBT else PROPERTY_ABSENT
        )
        facts["shstk_state"] = PROPERTY_PRESENT if and_value & SHSTK else (
            PROPERTY_CONTRADICTORY if or_value & SHSTK else PROPERTY_ABSENT
        )
    elif note_count:
        facts.update(
            property_feature_and=0,
            property_feature_or=0,
            property_conflict_count=0,
            ibt_state=PROPERTY_UNKNOWN,
            shstk_state=PROPERTY_UNKNOWN,
        )
    else:
        facts.update(
            property_feature_and=0,
            property_feature_or=0,
            property_conflict_count=0,
            ibt_state=PROPERTY_UNKNOWN,
            shstk_state=PROPERTY_UNKNOWN,
        )

    eligible = {
        "phnum", "role_state", "role_evidence", "interp_count", "flags1_count", "soname_count"
    }
    if not property_corrupt:
        eligible |= {
            "property_view_count", "property_note_count", "property_feature_count",
            "property_feature_and", "property_feature_or", "property_conflict_count",
            "ibt_state", "shstk_state",
        }
    notes_meta = {
        "etype_text": etype_text,
        "entry": f"0x{entry:x}",
        "property_corrupt": str(int(property_corrupt)),
        "feature_texts_json": json.dumps(feature_texts, sort_keys=True),
    }
    return facts, eligible, notes_meta


def field_disposition(
    field: str,
    eligibility: dict[str, Any],
    expected: int,
    readelf_facts: dict[str, int],
    eligible_fields: set[str],
    object_status: int,
) -> tuple[str, str, str]:
    category = eligibility[field]["class"]
    if category in {"ambiguous", "unavailable"}:
        return category, "", eligibility[field].get("reason", category)
    if field not in eligible_fields:
        return "not_eligible", "", "readelf representation was corrupt, truncated, or unavailable"
    if field in {"role_state", "role_evidence"} and object_status != 0:
        return "not_eligible", "", "x64lens stopped before private role classification"
    if field.startswith("property_") or field in {"ibt_state", "shstk_state"}:
        if object_status != 0:
            return "not_eligible", "", "x64lens rejected the property representation before private fact publication"
    observed = readelf_facts.get(field)
    require(observed is not None, f"eligible readelf fact is absent: {field}")
    if observed == expected:
        return "match", str(observed), eligibility[field].get("source", category)
    return "mismatch", str(observed), eligibility[field].get("source", category)


def write_result(
    result_dir: Path,
    rows: list[dict[str, str]],
    raw: dict[str, dict[str, dict[str, Any]]],
    manifest: dict[str, Any],
) -> None:
    require(not result_dir.exists(), f"readelf result already exists: {result_dir}")
    result_dir.mkdir(parents=True)
    raw_root = result_dir / "raw"
    raw_root.mkdir()
    for name, command_records in raw.items():
        target = raw_root / name
        target.mkdir()
        for option, record in command_records.items():
            stem = {"-hW": "header", "-lW": "program", "-dW": "dynamic", "-nW": "notes"}[option]
            (target / f"{stem}.stdout").write_bytes(record["stdout"])
            (target / f"{stem}.stderr").write_bytes(record["stderr"])
            retained = {key: value for key, value in record.items() if key not in {"stdout", "stderr"}}
            (target / f"{stem}.json").write_text(
                json.dumps(retained, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
    fields = ["object", "field", "authority_class", "expected", "readelf_value", "disposition", "source_or_reason"]
    with (result_dir / "crosswalk.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest["crosswalk_sha256"] = sha256_bytes((result_dir / "crosswalk.tsv").read_bytes())
    (result_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = sorted(path for path in result_dir.rglob("*") if path.is_file())
    (result_dir / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256_bytes(path.read_bytes())}  {path.relative_to(result_dir).as_posix()}\n" for path in files),
        encoding="utf-8",
    )
    for path in sorted(result_dir.rglob("*"), reverse=True):
        path.chmod(0o555 if path.is_dir() else 0o444)
    result_dir.chmod(0o555)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--heldout-result", type=Path, required=True)
    parser.add_argument("--readelf", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path)
    args = parser.parse_args()

    authority, authority_identity = load_authority(args.authority)
    heldout_manifest, heldout_rows, heldout_identity = load_heldout(args.heldout_result)
    require(heldout_manifest.get("authority_id") == authority["source_authority_id"],
            "held-out result and readelf authority disagree")
    readelf_identity = identity(args.readelf, "GNU readelf", executable=True, allow_command_symlink=True)
    version = subprocess.run([str(args.readelf), "--version"], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, check=False, timeout=5.0)
    require(version.returncode == 0 and version.stdout, "readelf --version failed")

    crosswalk: list[dict[str, str]] = []
    raw: dict[str, dict[str, dict[str, Any]]] = {}
    mismatches = 0
    matches = 0
    disposition_counts: dict[str, int] = {}
    for heldout in heldout_rows:
        name = heldout["name"]
        target = args.heldout_result / "objects" / name
        require(target.is_file() and not target.is_symlink(), f"held-out object is missing: {name}")
        command_records = {option: run_readelf(args.readelf, target, option)
                           for option in authority["readelf_commands"]}
        raw[name] = command_records
        facts, eligible_fields, _metadata = parse_readelf(command_records)
        object_status = int(heldout["observed_status"])
        for field in FACT_FIELDS:
            expected = int(heldout[f"observed_{field}"])
            disposition, observed, reason = field_disposition(
                field, authority["field_eligibility"], expected, facts, eligible_fields, object_status
            )
            disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1
            if disposition == "mismatch":
                mismatches += 1
            elif disposition == "match":
                matches += 1
            crosswalk.append({
                "object": name,
                "field": field,
                "authority_class": authority["field_eligibility"][field]["class"],
                "expected": str(expected),
                "readelf_value": observed,
                "disposition": disposition,
                "source_or_reason": reason,
            })

    require(len(raw) == 96 and sum(len(records) for records in raw.values()) == 384,
            "readelf process accounting changed")
    require(len(crosswalk) == 96 * len(FACT_FIELDS), "readelf field accounting changed")
    require(mismatches == 0, f"eligible readelf facts contain {mismatches} unexplained mismatches")
    manifest = {
        "format": "x64lens-sprint12-role-property-readelf-v1",
        "authority_id": authority["authority_id"],
        "source_authority_id": authority["source_authority_id"],
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "public_policy_decision_authorized": False,
        "object_count": 96,
        "readelf_process_count": 384,
        "field_record_count": len(crosswalk),
        "eligible_match_count": matches,
        "eligible_mismatch_count": mismatches,
        "disposition_counts": disposition_counts,
        "identities": {
            "authority": authority_identity,
            "heldout_result_manifest": heldout_identity,
            "readelf": readelf_identity,
            "readelf_version_stdout_sha256": sha256_bytes(version.stdout),
            "readelf_version_stderr_sha256": sha256_bytes(version.stderr),
            "readelf_version_first_line": version.stdout.decode("utf-8", errors="replace").splitlines()[0],
        },
    }
    if args.result_dir is not None:
        write_result(args.result_dir, crosswalk, raw, manifest)

    print(
        "sprint12-role-property-readelf-smoke: ok "
        f"objects=96 commands=384 fields={len(crosswalk)} eligible_matches={matches} "
        f"eligible_mismatches=0 ambiguous={disposition_counts.get('ambiguous', 0)} "
        f"unavailable={disposition_counts.get('unavailable', 0)} "
        f"not_eligible={disposition_counts.get('not_eligible', 0)} public_policy=deferred"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ReconciliationError, ValueError, json.JSONDecodeError,
            subprocess.SubprocessError) as exc:
        print(f"sprint12-role-property-readelf-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
