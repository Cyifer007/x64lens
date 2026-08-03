#!/usr/bin/env python3
"""Acquire outcome-blind external-natural role/property evidence.

Selection is frozen from installed dpkg source lineage and path evidence before
x64lens, the private fact probe, or GNU readelf inspect a selected target.  The
result preserves object and execution denominators, raw public/comparator
outputs, ambiguous and unavailable cells, and the private/public separation.
It does not authorize a public PIE/DSO, IBT, or SHSTK field.
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
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[1]
FACT_FIELDS = (
    "status", "phnum", "role_state", "role_evidence", "interp_count",
    "flags1_count", "soname_count", "property_view_count",
    "property_contributor_count", "property_note_count",
    "property_feature_count", "property_feature_and", "property_feature_or",
    "property_unknown_count", "property_conflict_count",
    "property_overlap_count", "ibt_state", "shstk_state",
)
ROLE_NAMES = {
    0: "unknown",
    1: "executable-like",
    2: "shared-object-like",
    3: "ambiguous",
    4: "contradictory",
}
PROPERTY_NAMES = {
    0: "unknown",
    1: "absent",
    2: "present",
    3: "contradictory",
}
PUBLIC_COMMANDS = (
    ("info", ("info",)),
    ("mitigations", ("mitigations",)),
    ("gadgets", ("gadgets", "--format", "json", "--max-depth", "4")),
    ("analyze", ("analyze", "--format", "json", "--max-depth", "4")),
)
READELF_OPTIONS = ("-hW", "-lW", "-dW", "-nW")


class AcquisitionError(RuntimeError):
    pass


# Test-only hook used by the corrective regression to mutate a frozen
# selection before any analyzer outcome is inspected.
_TEST_AFTER_SELECTION_FREEZE_HOOK: Callable[[Path], None] | None = None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcquisitionError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_module(name: str, relative: str) -> Any:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(command: list[str], *, timeout: float = 30.0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
        env={**os.environ, "LC_ALL": "C", "LANG": "C", "TZ": "UTC"},
    )


def identity(path: Path, label: str, *, executable: bool = False, allow_symlink: bool = False) -> dict[str, Any]:
    requested = Path(os.path.abspath(path))
    if not allow_symlink:
        require(not requested.is_symlink(), f"{label} may not be a symlink: {requested}")
    resolved = requested.resolve(strict=True)
    metadata = resolved.stat()
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file: {resolved}")
    if executable:
        require(os.access(resolved, os.X_OK), f"{label} is not executable: {resolved}")
    data = resolved.read_bytes()
    return {
        "requested_path": str(requested),
        "resolved_path": str(resolved),
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }


def retained_identity(path: Path, label: str) -> dict[str, Any]:
    """Return the exact retained-file identity used by the selection freeze."""
    require(path.is_file() and not path.is_symlink(), f"{label} is not a retained regular file")
    metadata = path.stat()
    data = path.read_bytes()
    post = path.stat()
    require(
        (metadata.st_dev, metadata.st_ino, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)
        == (post.st_dev, post.st_ino, post.st_size, post.st_mtime_ns, post.st_ctime_ns),
        f"{label} changed while hashing",
    )
    return {
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }


def assert_selection_freeze(
    staging: Path,
    frozen: dict[str, Any],
    frozen_manifest_sha256: str,
    *,
    checkpoint: str,
) -> dict[str, Any]:
    """Reauthenticate selection authorities and acquired object identities."""
    candidates = retained_identity(staging / "selection-candidates.tsv", "selection candidate authority")
    selection = retained_identity(staging / "selection.tsv", "selection authority")
    freeze_path = staging / "selection-freeze.json"
    freeze_identity = retained_identity(freeze_path, "selection freeze")
    require(candidates["sha256"] == frozen["selection_candidates_sha256"],
            f"selection candidates changed after freeze: {checkpoint}")
    require(selection["sha256"] == frozen["selection_sha256"],
            f"selection changed after freeze: {checkpoint}")
    require(freeze_identity["sha256"] == frozen_manifest_sha256,
            f"selection-freeze manifest changed: {checkpoint}")
    require(load_json(freeze_path) == frozen, f"selection-freeze semantics changed: {checkpoint}")
    require(candidates["mode"] == "0444" and selection["mode"] == "0444"
            and freeze_identity["mode"] == "0444",
            f"selection authority mode changed: {checkpoint}")
    observed_objects: dict[str, dict[str, Any]] = {}
    for name, expected in sorted(frozen["selected_objects"].items()):
        observed = retained_identity(staging / "objects" / name, f"selected object {name}")
        require(observed == expected, f"selected object changed after freeze: {name}: {checkpoint}")
        observed_objects[name] = observed
    return {
        "checkpoint": checkpoint,
        "selection_candidates": candidates,
        "selection": selection,
        "selection_freeze": freeze_identity,
        "selected_objects": observed_objects,
    }


def require_exact_authority(value: Any) -> dict[str, Any]:
    require(isinstance(value, dict), "external-natural authority must be an object")
    require(set(value) == {
        "authority_id", "evidence_class", "frozen", "publication_eligible",
        "purpose", "selection", "acquisition_custody", "fact_plane", "acceptance",
    }, "external-natural authority fields changed")
    require(value["authority_id"] == "sprint12-external-natural-acquisition-v1",
            "external-natural authority id changed")
    require(value["evidence_class"] == "diagnostic"
            and value["frozen"] is False
            and value["publication_eligible"] is False,
            "external-natural evidence boundary changed")
    selection = value["selection"]
    require(selection == {
        "package_manager": "dpkg-query",
        "source_lineages": ["binutils", "glibc", "systemd", "util-linux"],
        "objects_per_lineage": 12,
        "buckets_per_lineage": {"executable_path": 7, "shared_library_path": 5},
        "ordering": "bytewise lexical absolute path within each source lineage and bucket",
        "eligibility": [
            "installed binary package declares the exact source lineage",
            "dpkg-query lists the absolute path",
            "path is a regular non-symlink file",
            "ELF identity is 64-bit little-endian x86_64",
            "executable_path is below /usr/bin or /usr/sbin and has an execute bit",
            "shared_library_path is below /lib or /usr/lib and its basename contains .so",
            "SHA-256 identity is unique across the selected 48 objects",
        ],
        "selection_must_precede_analyzer_outcomes": True,
        "lineage_maximum_fraction": "0.25",
    }, "external-natural selection authority changed")
    require(value["acquisition_custody"] == {
        "retain_binary_package_names_and_versions": True,
        "retain_source_package_names_and_versions": True,
        "retain_requested_and_resolved_paths": True,
        "retain_target_sha256_size_mode": True,
        "retain_package_file_list_sha256": True,
        "retain_copyright_file_sha256": True,
        "retain_dpkg_query_identity_and_version": True,
        "targets_are_copied_read_only_and_never_executed": True,
    }, "external-natural custody authority changed")
    require(value["fact_plane"] == {
        "private_fact_fields": 18,
        "probe_repeats_per_object": 3,
        "public_commands_per_object": 4,
        "readelf_commands_per_object": ["-hW", "-lW", "-dW", "-nW"],
        "states_retained": [
            "unknown", "executable-like", "shared-object-like", "ambiguous",
            "contradictory", "malformed", "unsupported", "unavailable", "inapplicable",
        ],
        "public_schema_version": "0.2.0",
        "public_policy_decision_authorized": False,
        "readelf_field_eligibility": {
            "status": {"class": "unavailable", "reason": "readelf exit status is not the x64lens parser contract"},
            "phnum": {"class": "direct", "source": "readelf -hW"},
            "role_state": {"class": "derived", "source": "readelf -hW/-lW/-dW"},
            "role_evidence": {"class": "derived", "source": "readelf -hW/-lW/-dW"},
            "interp_count": {"class": "direct", "source": "readelf -lW"},
            "flags1_count": {"class": "direct", "source": "readelf -dW"},
            "soname_count": {"class": "direct", "source": "readelf -dW"},
            "property_view_count": {"class": "unavailable", "reason": "readelf -nW collapses canonical physical carrier views and does not retain x64lens view multiplicity"},
            "property_contributor_count": {"class": "unavailable", "reason": "readelf does not retain original PHDR contributor multiplicity"},
            "property_note_count": {"class": "direct", "source": "readelf -nW"},
            "property_feature_count": {"class": "direct", "source": "readelf -nW"},
            "property_feature_and": {"class": "derived", "source": "readelf -nW represented x86 feature records"},
            "property_feature_or": {"class": "derived", "source": "readelf -nW represented x86 feature records"},
            "property_unknown_count": {"class": "ambiguous", "reason": "readelf textual unknown-property and unknown-bit categories are not isomorphic to the private count"},
            "property_conflict_count": {"class": "derived", "source": "readelf -nW represented feature intersection/union"},
            "property_overlap_count": {"class": "unavailable", "reason": "readelf output does not expose x64lens carrier-overlap accounting"},
            "ibt_state": {"class": "derived", "source": "readelf -nW represented x86 feature records"},
            "shstk_state": {"class": "derived", "source": "readelf -nW represented x86 feature records"},
        },
    }, "external-natural fact-plane authority changed")
    require(value["acceptance"] == {
        "lineage_count": 4,
        "object_count": 48,
        "executable_path_count": 28,
        "shared_library_path_count": 20,
        "probe_run_count": 144,
        "private_run_field_count": 2592,
        "object_field_summary_count": 864,
        "public_command_count": 192,
        "readelf_process_count": 192,
        "readelf_field_disposition_count": 864,
        "eligible_readelf_mismatch_count": 0,
        "all_selection_records_retained": True,
        "all_raw_outputs_retained": True,
        "native_container_parity_is_separate": True,
        "public_policy_is_deferred": True,
    }, "external-natural acceptance authority changed")
    return value


def parse_package_inventory(raw: bytes, lineages: list[str]) -> dict[str, list[dict[str, str]]]:
    result = {lineage: [] for lineage in lineages}
    for line in raw.decode("utf-8", errors="strict").splitlines():
        parts = line.split("\t")
        require(len(parts) == 5, f"unexpected dpkg-query inventory row: {line!r}")
        binary, source, source_version, binary_version, architecture = parts
        if source in result:
            result[source].append({
                "binary_package": binary,
                "source_package": source,
                "source_version": source_version,
                "binary_version": binary_version,
                "architecture": architecture,
            })
    for lineage, packages in result.items():
        require(packages, f"no installed binary packages for source lineage {lineage}")
        source_versions = {row["source_version"] for row in packages}
        require(len(source_versions) == 1, f"source lineage {lineage} spans versions: {sorted(source_versions)}")
        packages.sort(key=lambda row: os.fsencode(row["binary_package"]))
    return result


def elf64_x86_64(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            header = handle.read(20)
    except OSError:
        return False
    return (len(header) >= 20 and header[:7] == b"\x7fELF\x02\x01\x01"
            and int.from_bytes(header[18:20], "little") == 62)


def path_bucket(path: str, mode: int) -> str | None:
    if (path.startswith("/usr/bin/") or path.startswith("/usr/sbin/")) and mode & 0o111:
        return "executable_path"
    name = Path(path).name
    if (path.startswith("/lib/") or path.startswith("/usr/lib/")) and ".so" in name:
        return "shared_library_path"
    return None


def discover(
    authority: dict[str, Any],
    dpkg_query: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, bytes], dict[str, bytes]]:
    lineages = authority["selection"]["source_lineages"]
    format_arg = "-f=${binary:Package}\\t${source:Package}\\t${source:Version}\\t${Version}\\t${Architecture}\\n"
    inventory_cp = run([str(dpkg_query), "-W", format_arg])
    require(inventory_cp.returncode == 0 and inventory_cp.stdout,
            f"dpkg-query inventory failed: {inventory_cp.stderr[:500]!r}")
    packages = parse_package_inventory(inventory_cp.stdout, lineages)
    package_outputs: dict[str, bytes] = {}
    copyright_outputs: dict[str, bytes] = {}
    providers: dict[str, dict[str, set[str]]] = {lineage: {} for lineage in lineages}
    package_records: list[dict[str, Any]] = []

    for lineage in lineages:
        for package in packages[lineage]:
            binary = package["binary_package"]
            cp = run([str(dpkg_query), "-L", binary])
            require(cp.returncode == 0, f"dpkg-query -L failed for {binary}: {cp.stderr[:300]!r}")
            package_outputs[binary] = cp.stdout
            paths = [line for line in cp.stdout.decode("utf-8", errors="strict").splitlines() if line.startswith("/")]
            for path in paths:
                providers[lineage].setdefault(path, set()).add(binary)
            copyright_records: list[dict[str, Any]] = []
            for path_text in paths:
                if not path_text.endswith("/copyright") or "/usr/share/doc/" not in path_text:
                    continue
                requested = Path(path_text)
                try:
                    resolved = requested.resolve(strict=True)
                    metadata = resolved.stat()
                except OSError:
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    continue
                data = resolved.read_bytes()
                key = sha256_bytes(os.fsencode(binary + "\0" + path_text))[:16]
                copyright_outputs[f"{key}-{resolved.name}"] = data
                copyright_records.append({
                    "requested_path": path_text,
                    "resolved_path": str(resolved),
                    "sha256": sha256_bytes(data),
                    "size_bytes": len(data),
                })
            package_records.append({
                **package,
                "file_list_sha256": sha256_bytes(cp.stdout),
                "file_list_entry_count": len(paths),
                "copyright_files": copyright_records,
            })
        require(any(record["source_package"] == lineage and record["copyright_files"] for record in package_records),
                f"source lineage {lineage} has no retained copyright file")

    candidates: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    selected_hashes: set[str] = set()
    quotas = authority["selection"]["buckets_per_lineage"]
    for lineage in lineages:
        lineage_rows: list[dict[str, Any]] = []
        for path_text in sorted(providers[lineage], key=os.fsencode):
            if not (path_text.startswith("/usr/bin/") or path_text.startswith("/usr/sbin/")
                    or path_text.startswith("/lib/") or path_text.startswith("/usr/lib/")):
                continue
            path = Path(path_text)
            row: dict[str, Any] = {
                "source_lineage": lineage,
                "requested_path": path_text,
                "providers": sorted(providers[lineage][path_text], key=os.fsencode),
                "eligible": False,
                "selected": False,
                "bucket": "",
                "reason": "",
            }
            try:
                metadata = path.lstat()
            except OSError as exc:
                row["reason"] = f"lstat:{exc.errno}"
                lineage_rows.append(row)
                continue
            if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
                row["reason"] = "not_regular_nonsymlink"
                lineage_rows.append(row)
                continue
            bucket = path_bucket(path_text, metadata.st_mode)
            if bucket is None:
                row["reason"] = "outside_selected_bucket"
                lineage_rows.append(row)
                continue
            if not elf64_x86_64(path):
                row["reason"] = "not_elf64_little_x86_64"
                lineage_rows.append(row)
                continue
            data = path.read_bytes()
            digest = sha256_bytes(data)
            row.update({
                "eligible": True,
                "bucket": bucket,
                "reason": "eligible",
                "resolved_path": str(path.resolve(strict=True)),
                "sha256": digest,
                "size_bytes": len(data),
                "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
            })
            lineage_rows.append(row)
        candidates.extend(lineage_rows)
        for bucket in ("executable_path", "shared_library_path"):
            eligible = [row for row in lineage_rows if row["eligible"] and row["bucket"] == bucket]
            count = 0
            for row in eligible:
                if row["sha256"] in selected_hashes:
                    row["reason"] = "duplicate_selected_sha256"
                    continue
                row["selected"] = True
                selected_hashes.add(row["sha256"])
                selected.append(row)
                count += 1
                if count == quotas[bucket]:
                    break
            require(count == quotas[bucket],
                    f"lineage {lineage} has {count} unique {bucket} objects, expected {quotas[bucket]}")

    require(len(selected) == 48 and len(selected_hashes) == 48, "external-natural selection did not produce 48 unique objects")
    for ordinal, row in enumerate(selected, 1):
        safe_lineage = re.sub(r"[^A-Za-z0-9_.-]", "_", row["source_lineage"])
        safe_bucket = "exe" if row["bucket"] == "executable_path" else "lib"
        row["object_name"] = f"{ordinal:02d}-{safe_lineage}-{safe_bucket}.elf"
        row["selection_ordinal"] = ordinal
    lineage_counts = {
        lineage: sum(row["source_lineage"] == lineage for row in selected)
        for lineage in lineages
    }
    require(set(lineage_counts.values()) == {12}, f"source-lineage denominator changed: {lineage_counts}")
    selection_meta = {
        "inventory_sha256": sha256_bytes(inventory_cp.stdout),
        "inventory_stderr_sha256": sha256_bytes(inventory_cp.stderr),
        "package_records": package_records,
        "lineage_counts": lineage_counts,
        "candidate_record_count": len(candidates),
        "selected_object_count": len(selected),
    }
    return candidates, selected, selection_meta, package_outputs, copyright_outputs


def write_tsv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            flattened = dict(row)
            if isinstance(flattened.get("providers"), list):
                flattened["providers"] = ",".join(flattened["providers"])
            writer.writerow(flattened)


def public_records(
    analyzer: Path,
    target: Path,
    replay_target: str,
    expected: dict[str, int],
    schema: dict[str, Any],
    heldout: Any,
    public_boundary: Any,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for command_id, prefix in PUBLIC_COMMANDS:
        argv = [str(analyzer), *prefix, str(target)]
        replay_argv = [str(analyzer), *prefix, replay_target]
        cp = run(argv, timeout=20.0)
        public_boundary.assert_no_private_public_text(cp.stdout)
        public_boundary.assert_no_private_public_text(cp.stderr)
        if expected["status"] == 5 and command_id != "info":
            allowed = {5}
        elif command_id in {"gadgets", "analyze"}:
            allowed = {0, 6}
        else:
            allowed = {0}
        require(cp.returncode in allowed,
                f"public command {command_id} returned {cp.returncode}, allowed={sorted(allowed)}: {target.name}")
        if cp.returncode == 0:
            require(cp.stdout, f"public command emitted empty stdout: {command_id}/{target.name}")
        else:
            require(not cp.stdout, f"failed public command emitted partial stdout: {command_id}/{target.name}")
        if command_id in {"gadgets", "analyze"} and cp.returncode == 0:
            report = json.loads(cp.stdout, object_pairs_hook=strict_object)
            require(report.get("schema_version") == "0.2.0" and report.get("command") == command_id,
                    f"public JSON identity changed: {target.name}/{command_id}")
            public_boundary.assert_no_private_public_fields(report)
            heldout.validate_formal_schema(schema, report, f"{target.name}/{command_id}")
        records.append({
            "command_id": command_id,
            "executed_argv": argv,
            "replay_argv": replay_argv,
            "exit_code": cp.returncode,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
            "stdout_sha256": sha256_bytes(cp.stdout),
            "stderr_sha256": sha256_bytes(cp.stderr),
        })
    return records


def write_command_records(root: Path, records: list[dict[str, Any]]) -> None:
    root.mkdir()
    for record in records:
        command_id = record.get("command_id") or record.get("option", "command").lstrip("-")
        stem = str(command_id).replace("/", "_")
        (root / f"{stem}.stdout").write_bytes(record["stdout"])
        (root / f"{stem}.stderr").write_bytes(record["stderr"])
        metadata = {key: value for key, value in record.items() if key not in {"stdout", "stderr"}}
        (root / f"{stem}.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def seal_tree(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    sums = root / "SHA256SUMS.txt"
    sums.write_text(
        "".join(f"{sha256_bytes(path.read_bytes())}  {path.relative_to(root).as_posix()}\n" for path in files),
        encoding="utf-8",
    )
    for path in sorted(root.rglob("*"), reverse=True):
        path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)


def perform(args: argparse.Namespace, staging: Path) -> dict[str, Any]:
    authority_path = args.authority.resolve(strict=True)
    authority = require_exact_authority(load_json(authority_path))
    authority_identity = identity(authority_path, "external-natural authority")
    harness_identity = identity(Path(__file__), "external-natural acquisition harness", executable=True)
    cleanup_identity = identity(ROOT / "tools/remove-owned-tree.py", "identity-bound cleanup helper", executable=True)
    dpkg_query_path = Path(shutil.which(str(args.dpkg_query)) or str(args.dpkg_query))
    dpkg_identity = identity(dpkg_query_path, "dpkg-query", executable=True, allow_symlink=True)
    dpkg_version = run([str(dpkg_query_path), "--version"])
    require(dpkg_version.returncode == 0 and dpkg_version.stdout, "dpkg-query --version failed")

    candidates, selected, selection_meta, package_outputs, copyright_outputs = discover(authority, dpkg_query_path)
    require(staging.is_dir(), "external-natural staging directory is unavailable")
    objects_root = staging / "objects"
    package_root = staging / "package-evidence"
    objects_root.mkdir()
    package_root.mkdir()
    (package_root / "file-lists").mkdir()
    (package_root / "copyright").mkdir()
    for package, data in package_outputs.items():
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", package)
        (package_root / "file-lists" / f"{safe}.txt").write_bytes(data)
    for name, data in copyright_outputs.items():
        (package_root / "copyright" / name).write_bytes(data)

    selected_by_name: dict[str, dict[str, Any]] = {}
    for row in selected:
        source = Path(row["requested_path"])
        target = objects_root / row["object_name"]
        data = source.read_bytes()
        require(sha256_bytes(data) == row["sha256"] and len(data) == row["size_bytes"],
                f"selected object changed before acquisition: {source}")
        target.write_bytes(data)
        target.chmod(0o444)
        selected_by_name[row["object_name"]] = row

    candidate_fields = [
        "source_lineage", "requested_path", "resolved_path", "providers", "bucket",
        "eligible", "selected", "reason", "sha256", "size_bytes", "mode",
        "selection_ordinal", "object_name",
    ]
    write_tsv(staging / "selection-candidates.tsv", candidates, candidate_fields)
    write_tsv(staging / "selection.tsv", selected, candidate_fields)
    selection_freeze = {
        "authority_id": authority["authority_id"],
        "authority_identity": authority_identity,
        "acquisition_harness_identity": harness_identity,
        "selection_rule": authority["selection"],
        "selection_metadata": selection_meta,
        "selection_candidates_sha256": sha256_bytes((staging / "selection-candidates.tsv").read_bytes()),
        "selection_sha256": sha256_bytes((staging / "selection.tsv").read_bytes()),
        "selected_objects": {
            row["object_name"]: retained_identity(objects_root / row["object_name"], f"selected object {row['object_name']}")
            for row in selected
        },
        "outcomes_inspected": False,
    }
    freeze_path = staging / "selection-freeze.json"
    freeze_path.write_text(
        json.dumps(selection_freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for frozen_path in (staging / "selection-candidates.tsv", staging / "selection.tsv", freeze_path):
        frozen_path.chmod(0o444)
    selection_freeze_sha = sha256_bytes(freeze_path.read_bytes())
    freeze_checkpoints: list[dict[str, Any]] = []
    hook = _TEST_AFTER_SELECTION_FREEZE_HOOK
    if hook is not None:
        hook(staging)
    freeze_checkpoints.append(assert_selection_freeze(
        staging, selection_freeze, selection_freeze_sha, checkpoint="before-outcome-authorities"
    ))

    # Analysis authorities are authenticated only after the target set is frozen.
    analyzer_identity = identity(args.analyzer, "analyzer", executable=True)
    schema_identity = identity(args.schema, "public schema")
    probe_identity = identity(args.fact_probe, "private fact probe", executable=True)
    readelf_identity = identity(args.readelf, "GNU readelf", executable=True, allow_symlink=True)
    readelf_version = run([str(args.readelf), "--version"])
    require(readelf_version.returncode == 0 and readelf_version.stdout, "readelf --version failed")
    schema = load_json(args.schema)
    require(isinstance(schema, dict) and schema.get("$schema"), "public schema is malformed")

    heldout_path = ROOT / "tools/sprint12-role-property-heldout-smoke.py"
    readelf_module_path = ROOT / "tools/sprint12-role-property-readelf-smoke.py"
    public_boundary_path = ROOT / "tools/sprint12-role-property-metamorphic-smoke.py"
    heldout_module_identity = identity(heldout_path, "independent private-fact author", executable=True)
    readelf_module_identity = identity(readelf_module_path, "readelf reconciliation adapter", executable=True)
    public_boundary_identity = identity(public_boundary_path, "public boundary oracle", executable=True)
    heldout = load_module("p072_external_heldout", "tools/sprint12-role-property-heldout-smoke.py")
    readelf_mod = load_module("p072_external_readelf", "tools/sprint12-role-property-readelf-smoke.py")
    public_boundary = load_module("p072_external_public_boundary", "tools/sprint12-role-property-metamorphic-smoke.py")
    require(tuple(heldout.FACT_FIELDS) == FACT_FIELDS and tuple(readelf_mod.FACT_FIELDS) == FACT_FIELDS,
            "private fact field authorities disagree")

    facts_root = staging / "facts"
    public_root = staging / "public"
    readelf_root = staging / "readelf"
    facts_root.mkdir()
    public_root.mkdir()
    readelf_root.mkdir()
    fact_rows: list[dict[str, Any]] = []
    crosswalk_rows: list[dict[str, Any]] = []
    disposition_counts: dict[str, int] = {}
    public_exit_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    ibt_counts: dict[str, int] = {}
    shstk_counts: dict[str, int] = {}
    eligible_mismatches = 0
    probe_runs = 0
    public_commands_count = 0
    readelf_processes = 0

    for row in selected:
        name = row["object_name"]
        freeze_checkpoints.append(assert_selection_freeze(
            staging, selection_freeze, selection_freeze_sha, checkpoint=f"before-outcomes:{name}"
        ))
        target = objects_root / name
        blob = target.read_bytes()
        require(sha256_bytes(blob) == row["sha256"], f"acquired object identity changed: {name}")
        expected = heldout.independent_vector(blob)
        repeats = [heldout.probe_fact(args.fact_probe, target) for _ in range(3)]
        probe_runs += len(repeats)
        require(repeats[0][0] == repeats[1][0] == repeats[2][0], f"nondeterministic private probe: {name}")
        observed = repeats[0][1]
        require(observed == expected, f"private fact mismatch for {name}: expected={expected} observed={observed}")
        public = public_records(
            args.analyzer,
            target,
            f"objects/{name}",
            expected,
            schema,
            heldout,
            public_boundary,
        )
        public_commands_count += len(public)
        for record in public:
            key = f"{record['command_id']}:{record['exit_code']}"
            public_exit_counts[key] = public_exit_counts.get(key, 0) + 1
        write_command_records(public_root / name, public)

        readelf_records: dict[str, dict[str, Any]] = {}
        for option in READELF_OPTIONS:
            record = readelf_mod.run_readelf(args.readelf, target, option)
            require(record["exit_code"] == 0,
                    f"readelf {option} returned {record['exit_code']} for {name}: {record['stderr'][:300]!r}")
            record["replay_argv"] = [str(args.readelf), option, f"objects/{name}"]
            readelf_records[option] = record
            readelf_processes += 1
        write_command_records(readelf_root / name, list(readelf_records.values()))
        readelf_facts, eligible_fields, notes_meta = readelf_mod.parse_readelf(readelf_records)
        for field in FACT_FIELDS:
            disposition, readelf_value, source_or_reason = readelf_mod.field_disposition(
                field,
                authority["fact_plane"]["readelf_field_eligibility"],
                expected[field],
                readelf_facts,
                eligible_fields,
                expected["status"],
            )
            disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1
            eligible_mismatches += int(disposition == "mismatch")
            crosswalk_rows.append({
                "object": name,
                "source_lineage": row["source_lineage"],
                "bucket": row["bucket"],
                "field": field,
                "authority_class": authority["fact_plane"]["readelf_field_eligibility"][field]["class"],
                "expected": expected[field],
                "readelf_value": readelf_value,
                "disposition": disposition,
                "source_or_reason": source_or_reason,
            })

        facts_path = facts_root / name
        facts_path.mkdir()
        (facts_path / "expected.json").write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (facts_path / "observed.json").write_text(json.dumps(observed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (facts_path / "readelf-derived.json").write_text(json.dumps(readelf_facts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (facts_path / "readelf-notes.json").write_text(json.dumps(notes_meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (facts_path / "probe-repeat-sha256.json").write_text(
            json.dumps([sha256_bytes(item[0]) for item in repeats], indent=2) + "\n", encoding="utf-8"
        )
        fact_row: dict[str, Any] = {
            "object": name,
            "source_lineage": row["source_lineage"],
            "bucket": row["bucket"],
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
            "role_state_name": ROLE_NAMES.get(expected["role_state"], f"value-{expected['role_state']}"),
            "ibt_state_name": PROPERTY_NAMES.get(expected["ibt_state"], f"value-{expected['ibt_state']}"),
            "shstk_state_name": PROPERTY_NAMES.get(expected["shstk_state"], f"value-{expected['shstk_state']}"),
            "probe_repeat_sha256": sha256_bytes(repeats[0][0]),
        }
        fact_row.update({f"expected_{field}": expected[field] for field in FACT_FIELDS})
        fact_row.update({f"observed_{field}": observed[field] for field in FACT_FIELDS})
        fact_rows.append(fact_row)
        role_counts[fact_row["role_state_name"]] = role_counts.get(fact_row["role_state_name"], 0) + 1
        ibt_counts[fact_row["ibt_state_name"]] = ibt_counts.get(fact_row["ibt_state_name"], 0) + 1
        shstk_counts[fact_row["shstk_state_name"]] = shstk_counts.get(fact_row["shstk_state_name"], 0) + 1

    fact_fields = [
        "object", "source_lineage", "bucket", "sha256", "size_bytes",
        "role_state_name", "ibt_state_name", "shstk_state_name", "probe_repeat_sha256",
    ] + [f"expected_{field}" for field in FACT_FIELDS] + [f"observed_{field}" for field in FACT_FIELDS]
    write_tsv(staging / "facts.tsv", fact_rows, fact_fields)
    crosswalk_fields = [
        "object", "source_lineage", "bucket", "field", "authority_class", "expected",
        "readelf_value", "disposition", "source_or_reason",
    ]
    write_tsv(staging / "readelf-crosswalk.tsv", crosswalk_rows, crosswalk_fields)

    acceptance = authority["acceptance"]
    require(probe_runs == acceptance["probe_run_count"], "external-natural probe denominator changed")
    require(len(fact_rows) * len(FACT_FIELDS) * 3 == acceptance["private_run_field_count"],
            "external-natural private run-field denominator changed")
    require(len(fact_rows) * len(FACT_FIELDS) == acceptance["object_field_summary_count"],
            "external-natural object-field denominator changed")
    require(public_commands_count == acceptance["public_command_count"], "public command denominator changed")
    require(readelf_processes == acceptance["readelf_process_count"], "readelf process denominator changed")
    require(len(crosswalk_rows) == acceptance["readelf_field_disposition_count"],
            "readelf field denominator changed")
    require(eligible_mismatches == acceptance["eligible_readelf_mismatch_count"],
            f"eligible readelf mismatches: {eligible_mismatches}")

    freeze_checkpoints.append(assert_selection_freeze(
        staging, selection_freeze, selection_freeze_sha, checkpoint="after-all-outcomes"
    ))
    final_selection_candidates = retained_identity(staging / "selection-candidates.tsv", "final selection candidates")
    final_selection = retained_identity(staging / "selection.tsv", "final selection")

    manifest = {
        "format": "x64lens-sprint12-external-natural-acquisition-v2",
        "authority_id": authority["authority_id"],
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "selection_frozen_before_outcomes": True,
        "selection_freeze_verified_through_outcomes": True,
        "selection_freeze_checkpoint_count": len(freeze_checkpoints),
        "selection_freeze_sha256": selection_freeze_sha,
        "object_count": len(fact_rows),
        "lineage_count": len(authority["selection"]["source_lineages"]),
        "lineage_counts": selection_meta["lineage_counts"],
        "bucket_counts": {
            bucket: sum(row["bucket"] == bucket for row in selected)
            for bucket in ("executable_path", "shared_library_path")
        },
        "probe_run_count": probe_runs,
        "private_run_field_count": probe_runs * len(FACT_FIELDS),
        "object_field_summary_count": len(fact_rows) * len(FACT_FIELDS),
        "public_command_count": public_commands_count,
        "public_exit_counts": public_exit_counts,
        "readelf_process_count": readelf_processes,
        "readelf_field_disposition_count": len(crosswalk_rows),
        "readelf_disposition_counts": disposition_counts,
        "eligible_readelf_mismatch_count": eligible_mismatches,
        "role_state_counts": role_counts,
        "ibt_state_counts": ibt_counts,
        "shstk_state_counts": shstk_counts,
        "fact_fields": list(FACT_FIELDS),
        "environment_build_origin_separation": {
            "this_result": "external natural installed-package source/build-origin stratum",
            "same_byte_native_container_parity": "separate gate; not inferred from this result",
        },
        "public_policy_decision_authorized": False,
        "target_execution": False,
        "identities": {
            "authority": authority_identity,
            "acquisition_harness": harness_identity,
            "cleanup_helper": cleanup_identity,
            "independent_private_fact_author": heldout_module_identity,
            "readelf_reconciliation_adapter": readelf_module_identity,
            "public_boundary_oracle": public_boundary_identity,
            "analyzer": analyzer_identity,
            "schema": schema_identity,
            "fact_probe": probe_identity,
            "readelf": readelf_identity,
            "readelf_version_stdout_sha256": sha256_bytes(readelf_version.stdout),
            "dpkg_query": dpkg_identity,
            "dpkg_query_version_stdout_sha256": sha256_bytes(dpkg_version.stdout),
            "python": {"version": sys.version, "executable": sys.executable},
        },
        "selection_candidates_sha256": final_selection_candidates["sha256"],
        "selection_sha256": final_selection["sha256"],
        "selection_candidates_final_identity": final_selection_candidates,
        "selection_final_identity": final_selection,
        "facts_sha256": sha256_bytes((staging / "facts.tsv").read_bytes()),
        "readelf_crosswalk_sha256": sha256_bytes((staging / "readelf-crosswalk.tsv").read_bytes()),
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seal_tree(staging)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--analyzer", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--fact-probe", type=Path, required=True)
    parser.add_argument("--readelf", type=Path, required=True)
    parser.add_argument("--dpkg-query", type=Path, default=Path("dpkg-query"))
    parser.add_argument("--result-dir", type=Path, required=True)
    args = parser.parse_args()

    cleanup_mod = load_module("sprint12_external_natural_cleanup", "tools/remove-owned-tree.py")
    final_result = Path(os.path.abspath(args.result_dir))
    require(not final_result.exists(), f"external-natural result already exists: {final_result}")
    final_result.parent.mkdir(parents=True, exist_ok=True)
    staging = final_result.parent / f".{final_result.name}.staging.{os.getpid()}.{os.urandom(8).hex()}"
    require(not staging.exists(), "external-natural staging identity collision")
    staging.mkdir(mode=0o700)
    staging_identity = cleanup_mod.identify(staging)
    try:
        manifest = perform(args, staging)
        os.rename(staging, final_result)
        print(
            "sprint12-external-natural-acquisition-smoke: ok "
            f"objects={manifest['object_count']} lineages={manifest['lineage_count']} "
            f"probe_runs={manifest['probe_run_count']} public_commands={manifest['public_command_count']} "
            f"readelf_processes={manifest['readelf_process_count']} "
            f"eligible_mismatches={manifest['eligible_readelf_mismatch_count']} "
            f"selection_sha256={manifest['selection_sha256']} public_policy=deferred"
        )
        return 0
    finally:
        if staging.exists():
            cleanup_mod.remove(staging, cleanup_mod.parse_identity(staging_identity))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AcquisitionError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"sprint12-external-natural-acquisition-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
