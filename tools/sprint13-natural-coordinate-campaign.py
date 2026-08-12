#!/usr/bin/env python3
"""Run the outcome-blind P083 natural address-coordinate campaign.

Selection is frozen from installed dpkg package membership and authenticated GNU
readelf role facts before x64lens or any baseline target outcome is inspected.
The campaign retains every selected target, command, native output, normalized
relation, cell disposition, and the complete 108-control oracle.  It is
strictly diagnostic and cannot authorize coverage or performance claims.
"""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY_DEFAULT = ROOT / "benchmarks/task-definitions/sprint13-natural-positive-coordinate-v1.json"
EXPECTED_DEFAULT = ROOT / "tests/expected/sprint13-natural-positive-coordinate-v1.json"
ROLES = ("et_exec", "pie_et_dyn", "shared_et_dyn")
BASELINES = ("ropgadget", "ropper", "ropr")
MAX_PACKAGES = 8192
MAX_PACKAGE_PATHS = 250_000
MAX_ELF_CANDIDATES = 32_768
MAX_POOL_BYTES = 64 * 1024 * 1024
RENAME_NOREPLACE = 1
O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class CampaignError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise CampaignError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-natural-coordinate-campaign: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in items:
        require(key not in value, f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(raw: str) -> str:
    path = PurePosixPath(raw)
    require(raw and not path.is_absolute() and "\\" not in raw and all(p not in {"", ".", ".."} for p in path.parts), f"unsafe path: {raw!r}")
    return raw


def write_regular(path: Path, data: bytes, mode: int = 0o444) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)
    return {
        "path": path.name,
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "mode": f"{mode:04o}",
    }


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == keys, f"{label} shape changed: {sorted(set(value) ^ keys)}")
    return value


def valid_hex40(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(char in "0123456789abcdef" for char in value)
    )


def validate_authority(value: Any) -> dict[str, Any]:
    exact_keys(
        value,
        {
            "schema", "sprint", "patch", "campaign_id", "evidence_class",
            "frozen", "publication_eligible", "relation_id", "selection",
            "execution", "qualification", "claim_boundary",
        },
        "authority",
    )
    require(value["schema"] == "x64lens-sprint13-natural-positive-coordinate-authority-v1", "authority schema changed")
    require(type(value["sprint"]) is int and value["sprint"] == 13, "authority sprint changed")
    require(type(value["patch"]) is int and value["patch"] == 83, "authority patch changed")
    require(value["campaign_id"] == "s13-p083-natural-coordinate-v1", "campaign identity changed")
    require(value["relation_id"] == "canonical_exact_pop_rdi_ret", "relation identity changed")
    require(
        value["evidence_class"] == "diagnostic"
        and value["frozen"] is False
        and value["publication_eligible"] is False,
        "authority evidence boundary changed",
    )

    selection = exact_keys(
        value["selection"],
        {
            "package_universe", "file_universe", "lineage_key", "roles",
            "lineages_per_role", "targets_total", "ordering", "target_rule",
            "outcome_blind", "reroll",
        },
        "selection contract",
    )
    expected_selection = {
        "package_universe": "all installed dpkg packages",
        "file_universe": "regular non-symlink ELF64 little-endian x86_64 package members",
        "lineage_key": "dpkg source package, binary package fallback",
        "roles": list(ROLES),
        "lineages_per_role": 4,
        "targets_total": 12,
        "ordering": "role order, lineage byte order, path byte order",
        "target_rule": "first eligible path in each of the first four distinct lineages",
        "outcome_blind": True,
        "reroll": False,
    }
    require(selection == expected_selection, "selection authority changed")

    execution = exact_keys(
        value["execution"],
        {
            "tools", "executions_per_complete_target",
            "complete_execution_denominator", "x64lens_max_depth",
            "timeout_seconds", "stdout_limit_bytes", "stderr_limit_bytes",
        },
        "execution contract",
    )
    expected_execution = {
        "tools": ["x64lens", *BASELINES],
        "executions_per_complete_target": 4,
        "complete_execution_denominator": 48,
        "x64lens_max_depth": 4,
        "timeout_seconds": 120,
        "stdout_limit_bytes": 16_777_216,
        "stderr_limit_bytes": 4_194_304,
    }
    require(execution == expected_execution, "execution authority changed")

    qualification = exact_keys(
        value["qualification"],
        {
            "cells", "observations_per_cell", "positive_targets_required",
            "distinct_target_hashes_required",
            "consistent_coordinate_class_required", "mismatch_allowed",
            "ambiguous_allowed", "controls_per_cell", "control_total",
            "terminal_states",
        },
        "qualification contract",
    )
    expected_qualification = {
        "cells": 9,
        "observations_per_cell": 4,
        "positive_targets_required": 2,
        "distinct_target_hashes_required": True,
        "consistent_coordinate_class_required": True,
        "mismatch_allowed": False,
        "ambiguous_allowed": False,
        "controls_per_cell": 12,
        "control_total": 108,
        "terminal_states": [
            "qualified", "insufficient", "unavailable", "mismatch",
            "ambiguous",
        ],
    }
    require(qualification == expected_qualification, "qualification authority changed")

    boundary = exact_keys(
        value["claim_boundary"],
        {
            "comparison_qualified", "coverage_claim_authorized",
            "performance_claim_authorized", "publication_claim_authorized",
            "public_fields_added", "semantic_changes", "score_changes",
            "schema_changed",
        },
        "claim boundary",
    )
    require(boundary == {
        "comparison_qualified": False,
        "coverage_claim_authorized": False,
        "performance_claim_authorized": False,
        "publication_claim_authorized": False,
        "public_fields_added": 0,
        "semantic_changes": 0,
        "score_changes": 0,
        "schema_changed": False,
    }, "claim boundary changed")
    return value


def authenticate_source_authority(
    source_root: Path,
    source_manifest_path: Path,
    expected_candidate_tree: str,
) -> dict[str, Any]:
    require(valid_hex40(expected_candidate_tree), "invalid expected candidate tree")
    source_root = source_root.resolve(strict=True)
    source_manifest_path = source_manifest_path.resolve(strict=True)
    helper = load_module("s13_p084_gitless_source", ROOT / "tools/gitless-source-manifest.py")
    manifest = helper.load_manifest(source_manifest_path)
    helper.verify(source_root, manifest)
    require(
        manifest["candidate_tree"] == expected_candidate_tree,
        f"source authority tree differs from expected candidate tree: {manifest['candidate_tree']}",
    )
    metadata = source_manifest_path.stat()
    require(stat.S_ISREG(metadata.st_mode), "source manifest is not a regular file")
    return {
        "schema": manifest["schema"],
        "candidate_tree": manifest["candidate_tree"],
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "source_manifest_size_bytes": metadata.st_size,
        "source_manifest_mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
        "source_file_count": len(manifest["files"]),
        "source_directory_count": len(manifest["directories"]),
        "source_root_mode": manifest["root_mode"],
    }


@dataclass
class ProcessResult:
    argv: list[str]
    exit_code: int | None
    signal: int | None
    timeout: bool
    output_limited: bool
    stdout: bytes
    stderr: bytes
    wall_ns: int


def run_bounded(argv: list[str], *, cwd: Path, timeout: int, stdout_limit: int, stderr_limit: int) -> ProcessResult:
    started = time.monotonic_ns()
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        close_fds=True,
    )
    require(process.stdout is not None and process.stderr is not None, "capture pipes missing")
    selector = selectors.DefaultSelector()
    for stream, label in ((process.stdout, "stdout"), (process.stderr, "stderr")):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, label)
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": stdout_limit, "stderr": stderr_limit}
    timed_out = False
    limited = False
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map() or process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                break
            for key, _mask in selector.select(min(remaining, 0.2)):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                label = key.data
                room = limits[label] + 1 - len(buffers[label])
                buffers[label].extend(chunk[: max(room, 0)])
                if len(buffers[label]) > limits[label]:
                    limited = True
                    os.killpg(process.pid, signal.SIGKILL)
                    break
            if limited:
                break
        if timed_out or limited:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=10)
        # Drain only the remaining bounded discriminator bytes.
        for stream, label in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            while len(buffers[label]) <= limits[label]:
                try:
                    chunk = os.read(stream.fileno(), min(65536, limits[label] + 1 - len(buffers[label])))
                except BlockingIOError:
                    break
                if not chunk:
                    break
                buffers[label].extend(chunk)
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
    rc = process.returncode
    sig = -rc if rc is not None and rc < 0 else None
    return ProcessResult(
        argv=argv,
        exit_code=None if timed_out or limited or sig is not None else rc,
        signal=sig,
        timeout=timed_out,
        output_limited=limited,
        stdout=bytes(buffers["stdout"][:stdout_limit]),
        stderr=bytes(buffers["stderr"][:stderr_limit]),
        wall_ns=time.monotonic_ns() - started,
    )


def command_identity(path: Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    metadata = resolved.stat()
    require(stat.S_ISREG(metadata.st_mode), f"tool is not a regular file: {resolved}")
    return {
        "requested": os.fspath(path),
        "resolved": os.fspath(resolved),
        "sha256": sha256_file(resolved),
        "size_bytes": metadata.st_size,
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }


def elf64_x86_64(path: Path) -> bool:
    try:
        with path.open("rb") as stream:
            header = stream.read(20)
    except OSError:
        return False
    return len(header) >= 20 and header[:4] == b"\x7fELF" and header[4:6] == b"\x02\x01" and int.from_bytes(header[18:20], "little") == 62


def readelf_role(path: Path, readelf: Path) -> tuple[str | None, bytes]:
    completed = subprocess.run(
        [os.fspath(readelf), "-hW", "-lW", "-dW", os.fspath(path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    require(len(completed.stdout) <= 8 * 1024 * 1024 and len(completed.stderr) <= 1024 * 1024, "readelf output exceeded bound")
    if completed.returncode != 0:
        return None, completed.stdout + b"\n[stderr]\n" + completed.stderr
    text = completed.stdout.decode("utf-8", "replace")
    elf_type: str | None = None
    for line in text.splitlines():
        if line.lstrip().startswith("Type:"):
            fields = line.split()
            if len(fields) >= 2:
                elf_type = fields[1]
            break
    has_interp = any(line.strip().startswith("INTERP") for line in text.splitlines())
    if elf_type == "EXEC":
        role = "et_exec"
    elif elf_type == "DYN" and has_interp:
        role = "pie_et_dyn"
    elif elf_type == "DYN" and not has_interp:
        role = "shared_et_dyn"
    else:
        role = None
    return role, completed.stdout


def installed_packages(dpkg_query: Path) -> list[tuple[str, str]]:
    cp = subprocess.run(
        [os.fspath(dpkg_query), "-W", "-f=${binary:Package}\t${source:Package}\n"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
        check=False,
    )
    require(cp.returncode == 0, f"dpkg-query package inventory failed: {cp.stderr.decode('utf-8', 'replace')}")
    packages: list[tuple[str, str]] = []
    for raw in cp.stdout.decode("utf-8", "strict").splitlines():
        binary, _sep, source = raw.partition("\t")
        if not binary:
            continue
        lineage = source.split()[0] if source.strip() else binary.split(":", 1)[0]
        packages.append((binary, lineage))
    packages = sorted(set(packages), key=lambda item: (os.fsencode(item[1]), os.fsencode(item[0])))
    require(len(packages) <= MAX_PACKAGES, "installed package capacity exceeded")
    return packages


def package_paths(package: str, dpkg_query: Path) -> list[str]:
    cp = subprocess.run([os.fspath(dpkg_query), "-L", package], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    if cp.returncode != 0:
        return []
    return [line for line in cp.stdout.decode("utf-8", "surrogateescape").splitlines() if line.startswith("/")]


def freeze_pool(
    *, stage: Path, readelf: Path, dpkg_query: Path, campaign_id: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ownership: dict[str, tuple[str, str]] = {}
    total_paths = 0
    for package, lineage in installed_packages(dpkg_query):
        for raw in package_paths(package, dpkg_query):
            total_paths += 1
            require(total_paths <= MAX_PACKAGE_PATHS, "dpkg path capacity exceeded")
            ownership.setdefault(raw, (package, lineage))
    pool: list[dict[str, Any]] = []
    for raw in sorted(ownership, key=os.fsencode):
        path = Path(raw)
        try:
            metadata = path.lstat()
        except OSError:
            continue
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or metadata.st_size > MAX_POOL_BYTES:
            continue
        if not elf64_x86_64(path):
            continue
        role, readelf_output = readelf_role(path, readelf)
        if role is None:
            continue
        package, lineage = ownership[raw]
        pool.append({
            "role": role,
            "lineage": lineage,
            "binary_package": package,
            "source_path": raw,
            "sha256": sha256_file(path),
            "size_bytes": metadata.st_size,
            "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
            "readelf_sha256": sha256_bytes(readelf_output),
        })
        require(len(pool) <= MAX_ELF_CANDIDATES, "eligible ELF pool capacity exceeded")
    pool.sort(key=lambda item: (ROLES.index(item["role"]), os.fsencode(item["lineage"]), os.fsencode(item["source_path"])))
    pool_tsv = "role\tlineage\tbinary_package\tsource_path\tsha256\tsize_bytes\tmode\treadelf_sha256\n" + "".join(
        "\t".join(str(item[key]) for key in ("role", "lineage", "binary_package", "source_path", "sha256", "size_bytes", "mode", "readelf_sha256")) + "\n"
        for item in pool
    )
    pool_path = stage / "eligible-pool.tsv"
    write_regular(pool_path, pool_tsv.encode())
    selected: list[dict[str, Any]] = []
    targets_root = stage / "targets"
    targets_root.mkdir(mode=0o755)
    for role in ROLES:
        by_lineage: dict[str, dict[str, Any]] = {}
        for item in pool:
            if item["role"] == role:
                by_lineage.setdefault(item["lineage"], item)
        for slot, lineage in enumerate(sorted(by_lineage, key=os.fsencode)[:4], start=1):
            item = dict(by_lineage[lineage])
            source = Path(item["source_path"])
            target_id = f"{role}-{slot}-{hashlib.sha256(lineage.encode()).hexdigest()[:12]}"
            snapshot = targets_root / target_id
            payload = source.read_bytes()
            require(sha256_bytes(payload) == item["sha256"], f"selected target changed before freeze: {source}")
            snapshot.write_bytes(payload)
            snapshot.chmod(0o444)
            role_again, selected_readelf = readelf_role(snapshot, readelf)
            require(role_again == role, f"selected role changed before freeze: {source}")
            readelf_path = stage / "readelf" / f"{target_id}.txt"
            write_regular(readelf_path, selected_readelf)
            item.update({
                "target_id": target_id,
                "slot": slot,
                "snapshot_path": snapshot.relative_to(stage).as_posix(),
                "readelf_path": readelf_path.relative_to(stage).as_posix(),
                "snapshot_sha256": sha256_file(snapshot),
            })
            selected.append(item)
    freeze = {
        "schema": "x64lens-sprint13-natural-positive-coordinate-freeze-v1",
        "campaign_id": campaign_id,
        "selection_complete_before_outcomes": True,
        "reroll": False,
        "package_count": len(installed_packages(dpkg_query)),
        "package_path_count": total_paths,
        "eligible_pool_count": len(pool),
        "eligible_pool": {"path": pool_path.name, "sha256": sha256_file(pool_path), "size_bytes": pool_path.stat().st_size},
        "selected_count": len(selected),
        "role_counts": {role: sum(item["role"] == role for item in selected) for role in ROLES},
        "selected_targets": selected,
    }
    freeze_path = stage / "selection-freeze.json"
    write_regular(freeze_path, canonical(freeze))
    return freeze, selected


def relation_sets_x64lens(data: bytes) -> tuple[set[str], set[str]]:
    module = load_module("p083_x64lens_relation", ROOT / "benchmarks/scripts/x64lens-relation-extractor.py")
    report = module.parse_report(data)
    records = module.relation_records(report)
    return (
        {item["virtual_address_start"] for item in records},
        {item["file_offset_start"] for item in records},
    )


def relation_set_baseline(tool: str, data: bytes) -> set[str]:
    module = load_module("p083_baseline_adapter", ROOT / "benchmarks/scripts/baseline-output-adapter.py")
    records, _ansi, _ignored = module.parse_native_output(
        tool,
        data,
        require_return_terminated=True,
        maximum_line_bytes=1024 * 1024,
        maximum_record_count=262_144,
        maximum_instruction_count=64,
    )
    return {
        record["address"]
        for record in records
        if record.get("canonical_instructions") == ["pop rdi", "ret"]
    }


def classify(baseline: set[str], virtual: set[str], offsets: set[str]) -> dict[str, Any]:
    if not baseline or not virtual:
        status = "insufficient_relation_evidence"
    elif baseline == virtual and baseline == offsets:
        status = "ambiguous"
    elif baseline == virtual:
        status = "virtual_address"
    elif baseline == offsets:
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


def controls_for_cell(cell_id: str) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    for slot in range(1, 5):
        for kind, baseline, virtual, offsets, expected in (
            ("empty", set(), {"0x0000000000001000"}, {"0x0000000000000100"}, "insufficient_relation_evidence"),
            ("ambiguous", {"0x0000000000001000"}, {"0x0000000000001000"}, {"0x0000000000001000"}, "ambiguous"),
            ("mismatch", {"0x0000000000003000"}, {"0x0000000000001000"}, {"0x0000000000000100"}, "mismatch"),
        ):
            observed = classify(baseline, virtual, offsets)
            require(observed["status"] == expected, f"control classifier failed: {cell_id}/{slot}/{kind}")
            controls.append({"id": f"{cell_id}-t{slot}-{kind}", "kind": kind, "expected": expected, "observed": observed["status"]})
    return controls


def cell_result(tool: str, role: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
    positives = [item for item in observations if item.get("status") in {"virtual_address", "file_offset"}]
    selected: list[dict[str, Any]] = []
    for coordinate in ("virtual_address", "file_offset"):
        candidates = [item for item in positives if item["status"] == coordinate]
        hashes: set[str] = set()
        for item in candidates:
            if item["target_sha256"] not in hashes:
                selected.append(item)
                hashes.add(item["target_sha256"])
            if len(selected) == 2:
                break
        if len(selected) == 2:
            break
        selected = []
    statuses = {item.get("status") for item in observations}
    if "mismatch" in statuses:
        terminal = "mismatch"
    elif "ambiguous" in statuses:
        terminal = "ambiguous"
    elif len(selected) == 2 and selected[0]["status"] == selected[1]["status"]:
        terminal = "qualified"
    elif statuses == {"unavailable"}:
        terminal = "unavailable"
    else:
        terminal = "insufficient"
    controls = controls_for_cell(f"{tool}-{role}")
    return {
        "cell_id": f"{tool}-{role}",
        "tool": tool,
        "role": role,
        "terminal_state": terminal,
        "selected_positive_target_ids": [item["target_id"] for item in selected],
        "coordinate_class": selected[0]["status"] if len(selected) == 2 else None,
        "observations": observations,
        "controls": controls,
    }


def tool_commands(tool: str, executable: Path, target: Path, max_depth: int) -> list[str]:
    if tool == "x64lens":
        return [os.fspath(executable), "gadgets", "--format", "json", "--max-depth", str(max_depth), os.fspath(target)]
    if tool == "ropgadget":
        return [os.fspath(executable), "--binary", os.fspath(target), "--depth", "5", "--only", "pop|ret", "--nojop", "--nosys"]
    if tool == "ropper":
        return [os.fspath(executable), "--file", os.fspath(target), "--nocolor", "--single", "--type", "rop", "--inst-count", "5"]
    return [os.fspath(executable), "--colour", "false", "--max-instr", "5", "--nojop", "--nosys", os.fspath(target)]


def execute_campaign(args: argparse.Namespace, authority: dict[str, Any]) -> dict[str, Any]:
    result_dir = Path(os.path.abspath(args.result_dir))
    require(not result_dir.exists(), f"result directory already exists: {result_dir}")
    result_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{result_dir.name}.stage.", dir=result_dir.parent))
    tools = {
        "x64lens": args.x64lens.resolve(strict=True),
        "ropgadget": args.ropgadget.resolve(strict=True),
        "ropper": args.ropper.resolve(strict=True),
        "ropr": args.ropr.resolve(strict=True),
    }
    readelf = args.readelf.resolve(strict=True)
    dpkg_query = args.dpkg_query.resolve(strict=True)
    source_authority = authenticate_source_authority(
        args.source_root, args.source_manifest, args.expected_candidate_tree
    )
    try:
        tool_records = {name: command_identity(path) for name, path in tools.items()}
        tool_records["readelf"] = command_identity(readelf)
        tool_records["dpkg_query"] = command_identity(dpkg_query)
        freeze, selected = freeze_pool(
            stage=stage, readelf=readelf, dpkg_query=dpkg_query,
            campaign_id=authority["campaign_id"],
        )
        # No target outcome is inspected before selection-freeze.json exists.
        require((stage / "selection-freeze.json").is_file(), "selection freeze was not published before outcomes")
        outcomes: dict[str, dict[str, Any]] = {}
        execution_count = 0
        execution = authority["execution"]
        for target_record in selected:
            target = stage / target_record["snapshot_path"]
            target_outcomes: dict[str, Any] = {}
            x_sets: tuple[set[str], set[str]] | None = None
            for tool in ("x64lens", *BASELINES):
                argv = tool_commands(tool, tools[tool], target, execution["x64lens_max_depth"])
                result = run_bounded(
                    argv,
                    cwd=ROOT,
                    timeout=execution["timeout_seconds"],
                    stdout_limit=execution["stdout_limit_bytes"],
                    stderr_limit=execution["stderr_limit_bytes"],
                )
                execution_count += 1
                member_dir = stage / "runs" / target_record["target_id"] / tool
                stdout_path = member_dir / "stdout"
                stderr_path = member_dir / "stderr"
                stdout_desc = write_regular(stdout_path, result.stdout)
                stderr_desc = write_regular(stderr_path, result.stderr)
                record: dict[str, Any] = {
                    "argv": argv,
                    "exit_code": result.exit_code,
                    "signal": result.signal,
                    "timeout": result.timeout,
                    "output_limited": result.output_limited,
                    "wall_ns": result.wall_ns,
                    "stdout": {**stdout_desc, "path": stdout_path.relative_to(stage).as_posix()},
                    "stderr": {**stderr_desc, "path": stderr_path.relative_to(stage).as_posix()},
                    "relation_status": "unavailable",
                    "relation_addresses": [],
                }
                if result.exit_code == 0 and not result.timeout and not result.output_limited:
                    try:
                        if tool == "x64lens":
                            x_sets = relation_sets_x64lens(result.stdout)
                            record["relation_status"] = "observed" if x_sets[0] else "observed_zero"
                            record["virtual_addresses"] = sorted(x_sets[0])
                            record["file_offsets"] = sorted(x_sets[1])
                        else:
                            addresses = relation_set_baseline(tool, result.stdout)
                            record["relation_status"] = "observed" if addresses else "observed_zero"
                            record["relation_addresses"] = sorted(addresses)
                    except BaseException as exc:
                        record["relation_status"] = "parse_error"
                        record["parse_error"] = str(exc)
                target_outcomes[tool] = record
            outcomes[target_record["target_id"]] = {"target": target_record, "tools": target_outcomes}
        cells: list[dict[str, Any]] = []
        for baseline in BASELINES:
            for role in ROLES:
                observations: list[dict[str, Any]] = []
                for target_record in [item for item in selected if item["role"] == role]:
                    target_outcome = outcomes[target_record["target_id"]]["tools"]
                    x = target_outcome["x64lens"]
                    b = target_outcome[baseline]
                    observation = {
                        "target_id": target_record["target_id"],
                        "target_sha256": target_record["sha256"],
                    }
                    if x["relation_status"] not in {"observed", "observed_zero"} or b["relation_status"] not in {"observed", "observed_zero"}:
                        observation["status"] = "unavailable"
                    else:
                        observation.update(classify(set(b["relation_addresses"]), set(x["virtual_addresses"]), set(x["file_offsets"])))
                    observations.append(observation)
                cells.append(cell_result(baseline, role, observations))
        manifest = {
            "schema": "x64lens-sprint13-natural-positive-coordinate-result-v1",
            "sprint": 13,
            "patch": 83,
            "campaign_id": authority["campaign_id"],
            "evidence_class": "diagnostic",
            "frozen": False,
            "publication_eligible": False,
            "authority_sha256": sha256_file(args.authority),
            "source_authority": source_authority,
            "tool_identities": tool_records,
            "selection_freeze": {
                "path": "selection-freeze.json",
                "sha256": sha256_file(stage / "selection-freeze.json"),
                "selected_count": freeze["selected_count"],
                "role_counts": freeze["role_counts"],
            },
            "execution_count": execution_count,
            "complete_execution_denominator": 48,
            "outcomes": outcomes,
            "cells": cells,
            "cell_counts": {state: sum(item["terminal_state"] == state for item in cells) for state in ("qualified", "insufficient", "unavailable", "mismatch", "ambiguous")},
            "control_count": sum(len(item["controls"]) for item in cells),
            "claim_boundary": authority["claim_boundary"],
            "limitations": [
                "This is mutable diagnostic evidence and is not part of the Sprint 15-frozen campaign.",
                "Unavailable packages or tools are terminal states; target selection is never rerolled after outcomes.",
                "Coordinate qualification does not establish cross-tool coverage equivalence or performance superiority.",
            ],
        }
        require(
            authenticate_source_authority(
                args.source_root, args.source_manifest, args.expected_candidate_tree
            ) == source_authority,
            "source authority changed during campaign",
        )
        manifest_path = stage / "manifest.json"
        write_regular(manifest_path, canonical(manifest))
        # Complete recursive checksums before no-replace publication.
        lines: list[str] = []
        for path in sorted((item for item in stage.rglob("*") if item.is_file()), key=lambda item: os.fsencode(item.relative_to(stage).as_posix())):
            if path.name == "SHA256SUMS.txt":
                continue
            lines.append(f"{sha256_file(path)}  {path.relative_to(stage).as_posix()}\n")
        write_regular(stage / "SHA256SUMS.txt", "".join(lines).encode())
        libc = ctypes.CDLL(None, use_errno=True)
        syscall = libc.syscall
        syscall.restype = ctypes.c_long
        SYS_RENAMEAT2 = 316
        rc = syscall(SYS_RENAMEAT2, -100, os.fsencode(stage), -100, os.fsencode(result_dir), RENAME_NOREPLACE)
        if rc != 0:
            err = ctypes.get_errno()
            raise CampaignError(f"no-replace result publication failed: {os.strerror(err)}")
        stage = result_dir
        return manifest
    finally:
        if stage.exists() and stage != result_dir:
            import shutil
            shutil.rmtree(stage, ignore_errors=True)


def require_structural_complete(result: dict[str, Any]) -> None:
    require(result["selection_freeze"]["selected_count"] == 12, "structural completion requires 12 selected targets")
    require(
        result["selection_freeze"]["role_counts"] == {role: 4 for role in ROLES},
        "structural completion requires four targets in every role",
    )
    require(result["execution_count"] == 48, "structural completion requires 48 tool executions")
    require(result["complete_execution_denominator"] == 48, "execution denominator changed")
    require(len(result["cells"]) == 9, "structural completion requires nine cells")
    require(sum(result["cell_counts"].values()) == 9, "terminal cell accounting changed")
    require(result["control_count"] == 108, "structural completion requires 108 controls")
    require(
        all(
            len(cell["observations"]) == 4
            and len(cell["controls"]) == 12
            and all(control["expected"] == control["observed"] for control in cell["controls"])
            for cell in result["cells"]
        ),
        "natural campaign observation/control closure changed",
    )


def require_acceptance_complete(result: dict[str, Any]) -> None:
    require_structural_complete(result)
    require(
        result["cell_counts"]
        == {
            "qualified": 9,
            "insufficient": 0,
            "unavailable": 0,
            "mismatch": 0,
            "ambiguous": 0,
        },
        "acceptance completion requires all nine cells qualified",
    )


def selftest(authority: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    observations = 0
    cells: list[dict[str, Any]] = []
    for baseline_index, baseline in enumerate(BASELINES):
        for role_index, role in enumerate(ROLES):
            rows: list[dict[str, Any]] = []
            coordinate = "virtual_address" if (baseline_index + role_index) % 2 == 0 else "file_offset"
            for slot in range(1, 5):
                rows.append({
                    "target_id": f"{role}-{slot}",
                    "target_sha256": hashlib.sha256(f"{role}-{slot}".encode()).hexdigest(),
                    "status": coordinate,
                })
                observations += 1
            cells.append(cell_result(baseline, role, rows))
    result = {
        "schema": "x64lens-sprint13-natural-positive-coordinate-selftest-result-v1",
        "sprint": 13,
        "patch": 83,
        "roles": len(ROLES),
        "baselines": len(BASELINES),
        "cells": len(cells),
        "observations": observations,
        "qualified_cells": sum(item["terminal_state"] == "qualified" for item in cells),
        "controls": sum(len(item["controls"]) for item in cells),
        "control_terminal_states": sum(all(control["expected"] == control["observed"] for control in item["controls"]) * len(item["controls"]) for item in cells),
        "outcome_blind_selection": authority["selection"]["outcome_blind"],
        "reroll": authority["selection"]["reroll"],
        "public_fields_added": 0,
        "semantic_changes": 0,
        "score_changes": 0,
        "schema_changed": False,
    }
    require(result == expected, "natural-coordinate selftest differs from expected authority")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("selftest", "run"))
    parser.add_argument("--authority", type=Path, default=AUTHORITY_DEFAULT)
    parser.add_argument("--expected", type=Path, default=EXPECTED_DEFAULT)
    parser.add_argument("--result-dir", type=Path)
    parser.add_argument("--x64lens", type=Path)
    parser.add_argument("--ropgadget", type=Path)
    parser.add_argument("--ropper", type=Path)
    parser.add_argument("--ropr", type=Path)
    parser.add_argument("--readelf", type=Path, default=Path("/usr/bin/readelf"))
    parser.add_argument("--dpkg-query", type=Path, default=Path("/usr/bin/dpkg-query"))
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--expected-candidate-tree")
    parser.add_argument(
        "--require-structural-complete",
        action="store_true",
        help="fail after retaining the result unless all targets, executions, cells, and controls are accounted for",
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="fail after retaining the result unless all nine baseline-by-role cells qualify for acceptance",
    )
    args = parser.parse_args()
    try:
        authority = validate_authority(load_json(args.authority.resolve(strict=True)))
        if args.action == "selftest":
            result = selftest(authority, load_json(args.expected.resolve(strict=True)))
            print(
                "sprint13-natural-coordinate-campaign-smoke: ok roles=3 baselines=3 "
                "cells=9 observations=36 qualified=9 controls=108 terminal_controls=108 "
                "outcome_blind=1 reroll=0 public_fields_added=0 semantic_changes=0 score_changes=0 schema_changed=0"
            )
        else:
            for name in (
                "result_dir", "x64lens", "ropgadget", "ropper", "ropr",
                "source_root", "source_manifest", "expected_candidate_tree",
            ):
                require(getattr(args, name) is not None, f"--{name.replace('_', '-')} is required for run")
            result = execute_campaign(args, authority)
            if args.require_structural_complete or args.require_complete:
                require_structural_complete(result)
            if args.require_complete:
                require_acceptance_complete(result)
            print(
                "sprint13-natural-coordinate-campaign: ok "
                f"selected={result['selection_freeze']['selected_count']} executions={result['execution_count']}/48 "
                f"cells=9 controls={result['control_count']}/108 qualified={result['cell_counts']['qualified']} "
                "diagnostic=1 publication_eligible=0 reroll=0"
            )
        del result
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, CampaignError) as exc:
        fail(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
