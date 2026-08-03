#!/usr/bin/env python3
"""Prove same-byte native/container parity for the private role/property plane.

The 96 authenticated held-out objects, analyzer, fact probe, and public schema
are mounted into both environments as the same bytes.  The completed native
plane is never mounted into the container; the container receives one dedicated
empty write root for its own plane only.  Both planes and their comparison are
retained and recursively sealed.  Each plane records 288 private-probe
executions, 5,184 private field cells, and 384 public command closures.
Comparison uses exact private probe bytes and path-normalized public output
tuples.  This gate does not expose private fields or authorize public PIE/DSO,
IBT, or SHSTK policy.
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
import tempfile
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


class ParityError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ParityError(message)


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


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def identity(path: Path, label: str, *, executable: bool = False) -> dict[str, Any]:
    requested = Path(os.path.abspath(path))
    require(not requested.is_symlink(), f"{label} may not be a symlink: {requested}")
    resolved = requested.resolve(strict=True)
    metadata = resolved.stat()
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file: {resolved}")
    if executable:
        require(os.access(resolved, os.X_OK), f"{label} is not executable: {resolved}")
    data = resolved.read_bytes()
    return {
        "path": str(resolved),
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }


def run(command: list[str], *, timeout: float = 30.0) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
        env={**os.environ, "LC_ALL": "C", "LANG": "C", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1"},
    )


def verify_checksums(root: Path) -> None:
    manifest = root / "SHA256SUMS.txt"
    require(manifest.is_file() and not manifest.is_symlink(), f"checksum manifest missing: {root}")
    listed: set[str] = set()
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        require(len(line) >= 67 and line[64:66] == "  " and re.fullmatch(r"[0-9a-f]{64}", line[:64]),
                f"invalid checksum line {number}: {root}")
        name = line[66:]
        pure = Path(name)
        require(name and not pure.is_absolute() and ".." not in pure.parts and "\\" not in name,
                f"unsafe checksum path: {name!r}")
        require(name not in listed and name != "SHA256SUMS.txt", f"duplicate checksum path: {name}")
        path = root / name
        require(path.is_file() and not path.is_symlink(), f"missing checksummed member: {name}")
        require(sha256_bytes(path.read_bytes()) == line[:64], f"checksum mismatch: {name}")
        listed.add(name)
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.txt"
    }
    require(actual == listed, f"checksum membership mismatch: missing={sorted(listed-actual)} extra={sorted(actual-listed)}")


def write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def seal_tree(root: Path) -> None:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    (root / "SHA256SUMS.txt").write_text(
        "".join(f"{sha256_bytes(path.read_bytes())}  {path.relative_to(root).as_posix()}\n" for path in files),
        encoding="utf-8",
    )
    for path in sorted(root.rglob("*"), reverse=True):
        path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)


def normalize_output(value: bytes, target: Path) -> bytes:
    replacements = {
        os.fsencode(str(target)),
        os.fsencode(str(target.resolve(strict=True))),
    }
    result = value
    for item in sorted(replacements, key=len, reverse=True):
        result = result.replace(item, b"<TARGET>")
    return result


def probe_once(probe: Path, target: Path) -> tuple[subprocess.CompletedProcess[bytes], dict[str, int]]:
    cp = run([str(probe), str(target)], timeout=20.0)
    require(cp.returncode == 0, f"private fact probe returned {cp.returncode}: {target.name}\n{cp.stderr[:500]!r}")
    value = json.loads(cp.stdout, object_pairs_hook=strict_object)
    require(isinstance(value, dict) and tuple(value) == FACT_FIELDS,
            f"private fact probe shape changed: {target.name}")
    require(all(isinstance(value[field], int) for field in FACT_FIELDS),
            f"private fact probe emitted noninteger facts: {target.name}")
    return cp, {field: int(value[field]) for field in FACT_FIELDS}


def plane(args: argparse.Namespace) -> int:
    require(args.execution_stratum in {"native", "container", "logic-only"},
            "execution stratum must be native, container, or logic-only")
    heldout_root = args.heldout_result.resolve(strict=True)
    readelf_mod = load_module("p072_parity_readelf", ROOT / "tools/sprint12-role-property-readelf-smoke.py")
    heldout_mod = load_module("p072_parity_heldout", ROOT / "tools/sprint12-role-property-heldout-smoke.py")
    manifest, source_rows, heldout_identity = readelf_mod.load_heldout(heldout_root)
    require(tuple(heldout_mod.FACT_FIELDS) == FACT_FIELDS, "held-out private fact fields changed")
    harness_identity = identity(Path(__file__), "environment parity harness", executable=True)
    analyzer_identity = identity(args.analyzer, "analyzer", executable=True)
    probe_identity = identity(args.fact_probe, "private fact probe", executable=True)
    schema_identity = identity(args.schema, "public schema")
    schema = load_json(args.schema)
    require(isinstance(schema, dict) and schema.get("$schema"), "public schema is malformed")

    result = Path(os.path.abspath(args.result_dir))
    require(not result.exists(), f"environment plane already exists: {result}")
    result.mkdir(parents=True)
    probe_root = result / "probe"
    public_root = result / "public"
    probe_root.mkdir()
    public_root.mkdir()
    object_rows: list[dict[str, Any]] = []
    probe_rows: list[dict[str, Any]] = []
    private_rows: list[dict[str, Any]] = []
    public_rows: list[dict[str, Any]] = []

    for source_row in source_rows:
        name = source_row["name"]
        target = heldout_root / "objects" / name
        require(target.is_file() and not target.is_symlink(), f"held-out object missing: {name}")
        target_identity = identity(target, f"held-out object {name}")
        expected = {field: int(source_row[f"expected_{field}"]) for field in FACT_FIELDS}
        retained_observed = {field: int(source_row[f"observed_{field}"]) for field in FACT_FIELDS}
        require(expected == retained_observed, f"held-out source result has expected/observed drift: {name}")
        object_rows.append({
            "object": name,
            "sha256": target_identity["sha256"],
            "size_bytes": target_identity["size_bytes"],
            "source_stratum": source_row["stratum"],
            "source_family": source_row["family"],
        })

        target_probe = probe_root / name
        target_probe.mkdir()
        repeat_bytes: list[bytes] = []
        for repeat in range(3):
            cp, observed = probe_once(args.fact_probe, target)
            require(observed == expected, f"private fact mismatch: {args.environment_id}/{name}/repeat-{repeat}")
            repeat_bytes.append(cp.stdout)
            (target_probe / f"repeat-{repeat}.stdout").write_bytes(cp.stdout)
            (target_probe / f"repeat-{repeat}.stderr").write_bytes(cp.stderr)
            probe_rows.append({
                "environment_id": args.environment_id,
                "execution_stratum": args.execution_stratum,
                "object": name,
                "repeat": repeat,
                "exit_code": cp.returncode,
                "stdout_sha256": sha256_bytes(cp.stdout),
                "stderr_sha256": sha256_bytes(cp.stderr),
                "stdout_size": len(cp.stdout),
                "stderr_size": len(cp.stderr),
            })
            for field in FACT_FIELDS:
                private_rows.append({
                    "environment_id": args.environment_id,
                    "object": name,
                    "repeat": repeat,
                    "field": field,
                    "expected": expected[field],
                    "observed": observed[field],
                    "match": int(expected[field] == observed[field]),
                })
        require(repeat_bytes[0] == repeat_bytes[1] == repeat_bytes[2],
                f"private fact probe is nondeterministic: {args.environment_id}/{name}")

        public = heldout_mod.public_commands(args.analyzer, target, expected, schema)
        target_public = public_root / name
        target_public.mkdir()
        for record in public:
            command_id = record["command_id"]
            normalized_stdout = normalize_output(record["stdout"], target)
            normalized_stderr = normalize_output(record["stderr"], target)
            (target_public / f"{command_id}.stdout").write_bytes(record["stdout"])
            (target_public / f"{command_id}.stderr").write_bytes(record["stderr"])
            metadata = {key: value for key, value in record.items() if key not in {"stdout", "stderr"}}
            metadata.update({
                "normalized_stdout_sha256": sha256_bytes(normalized_stdout),
                "normalized_stderr_sha256": sha256_bytes(normalized_stderr),
                "replay_target": f"objects/{name}",
            })
            (target_public / f"{command_id}.json").write_text(
                json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            public_rows.append({
                "environment_id": args.environment_id,
                "execution_stratum": args.execution_stratum,
                "object": name,
                "command_id": command_id,
                "exit_code": record["exit_code"],
                "stdout_sha256": record["stdout_sha256"],
                "stderr_sha256": record["stderr_sha256"],
                "normalized_stdout_sha256": sha256_bytes(normalized_stdout),
                "normalized_stderr_sha256": sha256_bytes(normalized_stderr),
            })

    write_tsv(result / "objects.tsv", object_rows,
              ["object", "sha256", "size_bytes", "source_stratum", "source_family"])
    write_tsv(result / "probe-runs.tsv", probe_rows,
              ["environment_id", "execution_stratum", "object", "repeat", "exit_code",
               "stdout_sha256", "stderr_sha256", "stdout_size", "stderr_size"])
    write_tsv(result / "private-fields.tsv", private_rows,
              ["environment_id", "object", "repeat", "field", "expected", "observed", "match"])
    write_tsv(result / "public-commands.tsv", public_rows,
              ["environment_id", "execution_stratum", "object", "command_id", "exit_code",
               "stdout_sha256", "stderr_sha256", "normalized_stdout_sha256", "normalized_stderr_sha256"])

    require(len(object_rows) == 96, "environment plane object denominator changed")
    require(len(probe_rows) == 288, "environment plane probe denominator changed")
    require(len(private_rows) == 5184 and all(row["match"] == 1 for row in private_rows),
            "environment plane private field denominator or agreement changed")
    require(len(public_rows) == 384, "environment plane public denominator changed")
    end_analyzer_identity = identity(args.analyzer, "analyzer after plane", executable=True)
    end_probe_identity = identity(args.fact_probe, "private fact probe after plane", executable=True)
    end_schema_identity = identity(args.schema, "public schema after plane")
    require(end_analyzer_identity["sha256"] == analyzer_identity["sha256"], "analyzer changed during environment plane")
    require(end_probe_identity["sha256"] == probe_identity["sha256"], "fact probe changed during environment plane")
    require(end_schema_identity["sha256"] == schema_identity["sha256"], "schema changed during environment plane")

    plane_manifest = {
        "format": "x64lens-sprint12-role-property-environment-plane-v1",
        "environment_id": args.environment_id,
        "execution_stratum": args.execution_stratum,
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "object_count": 96,
        "probe_process_count": 288,
        "private_field_count": 5184,
        "public_command_count": 384,
        "private_field_mismatch_count": 0,
        "public_policy_decision_authorized": False,
        "target_execution": False,
        "identities": {
            "heldout_manifest": heldout_identity,
            "heldout_authority_id": manifest["authority_id"],
            "parity_harness": harness_identity,
            "analyzer": analyzer_identity,
            "fact_probe": probe_identity,
            "schema": schema_identity,
            "python_runtime": {"version": sys.version, "executable": sys.executable},
        },
        "objects_sha256": sha256_bytes((result / "objects.tsv").read_bytes()),
        "probe_runs_sha256": sha256_bytes((result / "probe-runs.tsv").read_bytes()),
        "private_fields_sha256": sha256_bytes((result / "private-fields.tsv").read_bytes()),
        "public_commands_sha256": sha256_bytes((result / "public-commands.tsv").read_bytes()),
    }
    (result / "manifest.json").write_text(json.dumps(plane_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seal_tree(result)
    print(
        "sprint12-role-property-environment-plane: ok "
        f"environment={args.environment_id} stratum={args.execution_stratum} objects=96 "
        "probe_processes=288 private_fields=5184 public_commands=384 mismatches=0"
    )
    return 0


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def indexed(rows: list[dict[str, str]], keys: tuple[str, ...], label: str) -> dict[tuple[str, ...], dict[str, str]]:
    result: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = tuple(row[field] for field in keys)
        require(key not in result, f"duplicate {label} key: {key}")
        result[key] = row
    return result


def compare(args: argparse.Namespace) -> int:
    left = args.left.resolve(strict=True)
    right = args.right.resolve(strict=True)
    verify_checksums(left)
    verify_checksums(right)
    lm = load_json(left / "manifest.json")
    rm = load_json(right / "manifest.json")
    require(lm.get("format") == rm.get("format") == "x64lens-sprint12-role-property-environment-plane-v1",
            "environment plane format changed")
    if not args.logic_only:
        require({lm.get("execution_stratum"), rm.get("execution_stratum")} == {"native", "container"},
                "acceptance parity requires one native and one container plane")
    require(lm["environment_id"] != rm["environment_id"], "environment ids must be distinct")
    for key in ("heldout_manifest", "parity_harness", "analyzer", "fact_probe", "schema"):
        require(lm["identities"][key]["sha256"] == rm["identities"][key]["sha256"],
                f"same-byte authority differs across environments: {key}")

    left_objects = indexed(read_tsv(left / "objects.tsv"), ("object",), "object")
    right_objects = indexed(read_tsv(right / "objects.tsv"), ("object",), "object")
    require(left_objects.keys() == right_objects.keys() and len(left_objects) == 96,
            "environment object sets differ")
    for key in left_objects:
        require(left_objects[key]["sha256"] == right_objects[key]["sha256"],
                f"environment target bytes differ: {key}")

    left_probe = indexed(read_tsv(left / "probe-runs.tsv"), ("object", "repeat"), "probe")
    right_probe = indexed(read_tsv(right / "probe-runs.tsv"), ("object", "repeat"), "probe")
    require(left_probe.keys() == right_probe.keys() and len(left_probe) == 288,
            "environment probe process sets differ")
    for key in left_probe:
        require(left_probe[key]["exit_code"] == right_probe[key]["exit_code"] == "0"
                and left_probe[key]["stdout_sha256"] == right_probe[key]["stdout_sha256"]
                and left_probe[key]["stderr_sha256"] == right_probe[key]["stderr_sha256"],
                f"private probe process parity mismatch: {key}")

    left_private = indexed(read_tsv(left / "private-fields.tsv"), ("object", "repeat", "field"), "private field")
    right_private = indexed(read_tsv(right / "private-fields.tsv"), ("object", "repeat", "field"), "private field")
    require(left_private.keys() == right_private.keys() and len(left_private) == 5184,
            "environment private-field sets differ")
    for key in left_private:
        require(left_private[key]["match"] == right_private[key]["match"] == "1"
                and left_private[key]["expected"] == right_private[key]["expected"]
                and left_private[key]["observed"] == right_private[key]["observed"],
                f"private field parity mismatch: {key}")

    left_public = indexed(read_tsv(left / "public-commands.tsv"), ("object", "command_id"), "public command")
    right_public = indexed(read_tsv(right / "public-commands.tsv"), ("object", "command_id"), "public command")
    require(left_public.keys() == right_public.keys() and len(left_public) == 384,
            "environment public-command sets differ")
    for key in left_public:
        require(left_public[key]["exit_code"] == right_public[key]["exit_code"]
                and left_public[key]["normalized_stdout_sha256"] == right_public[key]["normalized_stdout_sha256"]
                and left_public[key]["normalized_stderr_sha256"] == right_public[key]["normalized_stderr_sha256"],
                f"public command parity mismatch: {key}")

    result = Path(os.path.abspath(args.result_dir))
    require(not result.exists(), f"parity result already exists: {result}")
    result.mkdir(parents=True)
    manifest = {
        "format": "x64lens-sprint12-role-property-environment-parity-v1",
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "logic_only": bool(args.logic_only),
        "environment_ids": [lm["environment_id"], rm["environment_id"]],
        "execution_strata": [lm["execution_stratum"], rm["execution_stratum"]],
        "object_count": 96,
        "private_fields_per_environment": 5184,
        "private_fields_combined": 10368,
        "paired_private_field_agreements": 5184,
        "probe_processes_per_environment": 288,
        "paired_probe_process_agreements": 288,
        "public_oracle_closures_combined": 768,
        "paired_public_tuples": 384,
        "private_mismatches": 0,
        "public_mismatches": 0,
        "public_policy_decision_authorized": False,
        "plane_manifest_sha256": {
            lm["environment_id"]: sha256_bytes((left / "manifest.json").read_bytes()),
            rm["environment_id"]: sha256_bytes((right / "manifest.json").read_bytes()),
        },
    }
    (result / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seal_tree(result)
    label = "logic-only" if args.logic_only else "native-container"
    print(
        "sprint12-role-property-environment-parity-smoke: ok "
        f"mode={label} objects=96 private_fields_per_environment=5184 "
        "private_fields_combined=10368 paired_probe_processes=288 "
        "public_oracle_closures=768 paired_public_tuples=384 mismatches=0 public_policy=deferred"
    )
    return 0


def capture_cleanup(path: Path) -> tuple[Any, Any]:
    cleanup = load_module("p073_parity_cleanup", ROOT / "tools/remove-owned-tree.py")
    return cleanup, cleanup.parse_identity(cleanup.identify(path))


def recursive_tree_identity(root: Path) -> dict[str, Any]:
    """Return a mode-aware identity for one sealed retained evidence tree."""
    require(root.is_dir() and not root.is_symlink(), f"retained tree is unavailable: {root}")
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        require(not path.is_symlink(), f"retained parity tree contains a link: {relative}")
        if path.is_dir():
            records.append({"path": relative, "type": "directory", "mode": f"{stat.S_IMODE(metadata.st_mode):04o}"})
        else:
            require(path.is_file(), f"retained parity tree contains a special member: {relative}")
            data = path.read_bytes()
            records.append({
                "path": relative,
                "type": "file",
                "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                "size_bytes": len(data),
                "sha256": sha256_bytes(data),
            })
    encoded = (json.dumps(records, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return {"member_count": len(records), "sha256": sha256_bytes(encoded)}


def build_container_command(
    *,
    docker: str,
    image: str,
    inputs: Path,
    heldout: Path,
    container_write_root: Path,
) -> list[str]:
    """Build the isolated container plane command.

    The native result path is intentionally absent from this interface, making
    cross-plane write access impossible to add accidentally at the call site.
    """
    return [
        docker, "run", "--rm", "--read-only", "--network", "none",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-e", "HOME=/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "LC_ALL=C", "-e", "LANG=C", "-e", "TZ=UTC",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m",
        "-v", f"{ROOT}:/work:ro",
        "-v", f"{inputs}:/inputs:ro",
        "-v", f"{heldout}:/heldout:ro",
        "-v", f"{container_write_root}:/output:rw",
        "-w", "/work",
        image,
        "python3", "/work/tools/sprint12-role-property-environment-parity-smoke.py", "plane",
        "--environment-id", "container", "--execution-stratum", "container",
        "--heldout-result", "/heldout",
        "--analyzer", "/inputs/x64lens",
        "--schema", "/inputs/schema.json",
        "--fact-probe", "/inputs/role-property-fact-probe",
        "--result-dir", "/output/plane",
    ]


def validate_container_mount_policy(
    command: list[str],
    *,
    native_result: Path,
    container_write_root: Path,
) -> dict[str, Any]:
    """Validate that the container can write only its empty private plane root."""
    require(str(native_result) not in "\n".join(command),
            "native parity plane leaked into the container command")
    mounts: list[str] = []
    for index, item in enumerate(command[:-1]):
        if item == "-v":
            mounts.append(command[index + 1])
    writable = [item for item in mounts if item.endswith(":rw")]
    expected = f"{container_write_root}:/output:rw"
    require(writable == [expected], f"container parity writable mounts changed: {writable!r}")
    require(all(item.endswith(":ro") or item == expected for item in mounts),
            f"container parity mount mode is not explicit: {mounts!r}")
    require(container_write_root.is_dir() and not any(container_write_root.iterdir()),
            "container parity write root is not empty before launch")
    return {
        "native_plane_exposed_to_container": False,
        "container_write_scope": "dedicated-empty-container-plane-root-only",
        "writable_mount_count": 1,
        "mount_count": len(mounts),
    }


def run_full(args: argparse.Namespace) -> int:
    docker = shutil.which(args.docker)
    require(docker is not None, "Docker command is unavailable")
    final_result = Path(os.path.abspath(args.result_dir))
    require(not final_result.exists(), f"retained parity result already exists: {final_result}")
    final_result.parent.mkdir(parents=True, exist_ok=True)
    staging = final_result.parent / f".{final_result.name}.staging.{os.getpid()}.{os.urandom(8).hex()}"
    require(not staging.exists(), "parity staging identity collision")
    staging.mkdir(mode=0o700)
    cleanup, cleanup_identity = capture_cleanup(staging)
    completed = False
    try:
        inputs = staging / "inputs"
        heldout = staging / "heldout"
        native_result = staging / "native"
        container_write_root = staging / "container-write-root"
        container_result = staging / "container"
        parity_result = staging / "parity"
        inputs.mkdir()
        container_write_root.mkdir(mode=0o700)
        shutil.copy2(args.analyzer, inputs / "x64lens")
        shutil.copy2(args.fact_probe, inputs / "role-property-fact-probe")
        shutil.copy2(args.schema, inputs / "schema.json")
        (inputs / "x64lens").chmod(0o555)
        (inputs / "role-property-fact-probe").chmod(0o555)
        (inputs / "schema.json").chmod(0o444)
        before = {name: identity(inputs / name, name, executable=name != "schema.json") for name in (
            "x64lens", "role-property-fact-probe", "schema.json"
        )}
        seal_tree(inputs)

        generate = [
            sys.executable,
            str(ROOT / "tools/sprint12-role-property-heldout-smoke.py"),
            "--authority", str(args.heldout_authority),
            "--analyzer", str(inputs / "x64lens"),
            "--schema", str(inputs / "schema.json"),
            "--provisional-corpus", str(args.provisional_corpus),
            "--fact-probe", str(inputs / "role-property-fact-probe"),
            "--result-dir", str(heldout),
        ]
        cp = run(generate, timeout=180.0)
        require(cp.returncode == 0, f"held-out generation failed:\n{cp.stdout[-500:]!r}\n{cp.stderr[-1000:]!r}")
        verify_checksums(heldout)

        native = [
            sys.executable, str(Path(__file__).resolve()), "plane",
            "--environment-id", "native", "--execution-stratum", "native",
            "--heldout-result", str(heldout),
            "--analyzer", str(inputs / "x64lens"),
            "--schema", str(inputs / "schema.json"),
            "--fact-probe", str(inputs / "role-property-fact-probe"),
            "--result-dir", str(native_result),
        ]
        cp = run(native, timeout=180.0)
        require(cp.returncode == 0, f"native environment plane failed:\n{cp.stdout[-500:]!r}\n{cp.stderr[-1000:]!r}")
        verify_checksums(native_result)
        native_before_container = recursive_tree_identity(native_result)

        container_command = build_container_command(
            docker=docker,
            image=args.docker_image,
            inputs=inputs,
            heldout=heldout,
            container_write_root=container_write_root,
        )
        # Exact mount policy: only the dedicated empty container-write root is
        # writable.  The native plane is not present in the command at all.
        mount_policy = validate_container_mount_policy(
            container_command,
            native_result=native_result,
            container_write_root=container_write_root,
        )
        cp = run(container_command, timeout=240.0)
        require(cp.returncode == 0, f"container environment plane failed:\n{cp.stdout[-500:]!r}\n{cp.stderr[-1000:]!r}")
        generated_container = container_write_root / "plane"
        require(generated_container.is_dir(), "container plane did not publish its dedicated result")
        require(set(container_write_root.iterdir()) == {generated_container},
                "container write root contains undeclared members")
        generated_container.rename(container_result)
        container_write_root.rmdir()
        verify_checksums(container_result)
        native_after_container = recursive_tree_identity(native_result)
        require(native_after_container == native_before_container,
                "native parity plane changed during container execution")

        comparison = [
            sys.executable, str(Path(__file__).resolve()), "compare",
            "--left", str(native_result),
            "--right", str(container_result),
            "--result-dir", str(parity_result),
        ]
        cp = run(comparison, timeout=30.0)
        require(cp.returncode == 0, f"environment parity comparison failed:\n{cp.stdout[-500:]!r}\n{cp.stderr[-1000:]!r}")
        verify_checksums(parity_result)
        after = {name: identity(inputs / name, name, executable=name != "schema.json") for name in before}
        require(all(before[name]["sha256"] == after[name]["sha256"] for name in before),
                "same-byte parity inputs changed during execution")

        run_manifest = {
            "format": "x64lens-sprint12-role-property-environment-parity-run-v2",
            "evidence_class": "diagnostic",
            "frozen": False,
            "publication_eligible": False,
            "actual_native_container_parity_executed": True,
            "native_plane_exposed_to_container": mount_policy["native_plane_exposed_to_container"],
            "container_write_scope": mount_policy["container_write_scope"],
            "container_mount_policy": mount_policy,
            "planes_retained_and_sealed": True,
            "public_policy_decision_authorized": False,
            "target_execution": False,
            "input_identities": before,
            "native_plane_identity_before_container": native_before_container,
            "native_plane_identity_after_container": native_after_container,
            "container_plane_identity": recursive_tree_identity(container_result),
            "parity_identity": recursive_tree_identity(parity_result),
            "container_command": container_command,
        }
        (staging / "run-manifest.json").write_text(
            json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        seal_tree(staging)
        os.rename(staging, final_result)
        completed = True
        print(cp.stdout.decode("utf-8", errors="replace").strip())
        print(
            "sprint12-role-property-environment-parity-run: ok "
            f"result={final_result} native_exposed=0 container_write_scope=exclusive "
            "planes_retained=1 public_policy=deferred"
        )
        return 0
    finally:
        if not completed and staging.exists():
            cleanup.remove(staging, cleanup_identity)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plane_parser = sub.add_parser("plane")
    plane_parser.add_argument("--environment-id", required=True)
    plane_parser.add_argument("--execution-stratum", required=True)
    plane_parser.add_argument("--heldout-result", type=Path, required=True)
    plane_parser.add_argument("--analyzer", type=Path, required=True)
    plane_parser.add_argument("--schema", type=Path, required=True)
    plane_parser.add_argument("--fact-probe", type=Path, required=True)
    plane_parser.add_argument("--result-dir", type=Path, required=True)

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--left", type=Path, required=True)
    compare_parser.add_argument("--right", type=Path, required=True)
    compare_parser.add_argument("--result-dir", type=Path, required=True)
    compare_parser.add_argument("--logic-only", action="store_true")

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--heldout-authority", type=Path, required=True)
    run_parser.add_argument("--provisional-corpus", type=Path, required=True)
    run_parser.add_argument("--analyzer", type=Path, required=True)
    run_parser.add_argument("--schema", type=Path, required=True)
    run_parser.add_argument("--fact-probe", type=Path, required=True)
    run_parser.add_argument("--docker-image", required=True)
    run_parser.add_argument("--docker", default="docker")
    run_parser.add_argument("--result-dir", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "plane":
        return plane(args)
    if args.command == "compare":
        return compare(args)
    return run_full(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ParityError, OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"sprint12-role-property-environment-parity-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
