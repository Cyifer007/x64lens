#!/usr/bin/env python3
"""Run and verify the bounded P090 reference-workload qualification preflight.

The preflight is deliberately reference-only.  Its 80 executions may decide
whether a fresh paired 160-run phase-attribution matrix is worth running, but
none of these rows may be reused in that later experiment or support a product
performance claim.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import selectors
import signal
import stat
import statistics
import subprocess
import sys
import tempfile
import time
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "x64lens-sprint13-workload-reference-preflight-authority-v1"
RESULT_SCHEMA = "x64lens-sprint13-workload-reference-preflight-result-v1"
MAX_JSON = 8 * 1024 * 1024
CHUNK = 65536


class PreflightError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise PreflightError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-workload-reference-preflight-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def strict(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    raw = path.read_bytes()
    require(len(raw) <= MAX_JSON, f"JSON exceeds bound: {path}")
    return json.loads(raw, object_pairs_hook=strict)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_rel(raw: str) -> str:
    require(isinstance(raw, str) and raw, "empty relative path")
    path = PurePosixPath(raw)
    require(not path.is_absolute() and "\\" not in raw
            and all(part not in {"", ".", ".."} for part in path.parts),
            f"unsafe relative path: {raw!r}")
    require(path.as_posix() == raw, f"noncanonical relative path: {raw!r}")
    return raw


def regular(path: Path, *, executable: bool | None = None) -> dict[str, Any]:
    metadata = os.lstat(path)
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1,
            f"unsafe regular-file authority: {path}")
    if executable is not None:
        require(bool(metadata.st_mode & 0o111) == executable,
                f"unexpected executable state: {path}")
    return {
        "sha256": sha(path),
        "size_bytes": metadata.st_size,
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }


def validate_authority(value: Any, expected: Any) -> dict[str, Any]:
    required = {
        "schema", "sprint", "patch", "experiment_id", "evidence_class",
        "publication_eligible", "purpose", "predecessor_authority", "timer_floor",
        "fixtures", "execution", "qualification", "decision_boundary", "limitations",
    }
    require(isinstance(value, dict) and set(value) == required, "preflight authority shape changed")
    require(value["schema"] == SCHEMA and value["sprint"] == 13 and value["patch"] == 90,
            "preflight authority identity changed")
    require(value["evidence_class"] == "diagnostic" and value["publication_eligible"] is False,
            "preflight evidence boundary changed")
    floor = value["timer_floor"]
    require(floor == {
        "source_campaign": "s13-p089-real-20260816t143543z",
        "timer_floor_ns": 5894690,
        "qualification_multiple": 5,
        "minimum_median_ns": 29473450,
    }, "preflight timer-floor authority changed")
    predecessor = value["predecessor_authority"]
    require(predecessor == {
        "path": "benchmarks/task-definitions/sprint13-workload-phase-attribution-v1.json",
        "sample_reuse_permitted": False,
        "paired_matrix_execution_count": 160,
    }, "preflight predecessor authority changed")
    fixtures = value["fixtures"]
    require(isinstance(fixtures, list) and len(fixtures) == 8, "preflight requires eight fixtures")
    ids: list[str] = []
    paths: list[str] = []
    semantics: list[tuple[str, int | None, str]] = []
    for fixture in fixtures:
        require(isinstance(fixture, dict) and set(fixture) == {
            "id", "command", "max_depth", "target_role", "target_path"
        }, "preflight fixture shape changed")
        require(fixture["command"] in {"gadgets", "analyze", "mitigations"},
                f"unsupported preflight command: {fixture['id']}")
        if fixture["command"] == "mitigations":
            require(fixture["max_depth"] is None, "mitigation fixture max depth must be null")
        else:
            require(type(fixture["max_depth"]) is int and fixture["max_depth"] in {4, 8},
                    "invalid preflight max depth")
        ids.append(fixture["id"])
        paths.append(safe_rel(fixture["target_path"]))
        semantics.append((fixture["command"], fixture["max_depth"], fixture["target_role"]))
    require(len(set(ids)) == 8 and len(set(semantics)) == 8,
            "preflight fixture identities or semantic tuples are not unique")
    require(len(set(paths)) >= 6, "preflight target diversity changed")
    require(value["execution"] == {
        "warmups_per_fixture": 1,
        "measured_runs_per_fixture": 9,
        "fixture_cells": 8,
        "warmup_executions": 8,
        "measured_executions": 72,
        "total_executions": 80,
        "order": "deterministic-rotating-counterbalance",
        "timeout_seconds": 60,
        "stdout_limit_bytes": 16777216,
        "stderr_limit_bytes": 1048576,
        "cache_policy": "warm-uncontrolled-diagnostic",
    }, "preflight execution denominator changed")
    require(value["qualification"] == {
        "minimum_qualified_fixtures": 6,
        "minimum_median_ns": 29473450,
        "maximum_mad_to_median_ratio": 0.1,
        "require_zero_failures": True,
        "require_stable_stdout": True,
        "require_stable_stderr": True,
    }, "preflight qualification policy changed")
    require(value["decision_boundary"] == {
        "proceed_only_to_fresh_paired_160_run_matrix": True,
        "preflight_rows_reusable_in_paired_matrix": False,
        "retire_phase_instrumentation_if_threshold_not_met": True,
        "no_optimization_selected": True,
        "no_performance_claim_authorized": True,
        "no_public_fields_added": True,
        "no_semantic_changes": True,
        "no_score_changes": True,
        "schema_changed": False,
    }, "preflight decision boundary changed")
    require(isinstance(value["limitations"], list) and len(value["limitations"]) >= 4,
            "preflight limitations changed")
    require(expected == {
        "schema": "x64lens-sprint13-workload-reference-preflight-expected-v1",
        "sprint": 13,
        "patch": 90,
        "experiment_id": value["experiment_id"],
        "fixtures": 8,
        "warmup_executions": 8,
        "measured_executions": 72,
        "total_executions": 80,
        "minimum_qualified_fixtures": 6,
        "minimum_median_ns": 29473450,
        "maximum_mad_to_median_ratio": 0.1,
        "executed": False,
        "decision": "authority_frozen_execution_pending",
        "publication_eligible": False,
        "public_fields_added": 0,
        "semantic_changes": 0,
        "score_changes": 0,
        "schema_changed": False,
    }, "preflight expected result changed")
    return value


@dataclass
class BoundedResult:
    exit_code: int | None
    signal: int | None
    timeout: bool
    output_limited: bool
    wall_ns: int
    stdout: bytes
    stderr: bytes


def kill_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def bounded_run(argv: list[str], cwd: Path, timeout_seconds: int,
                stdout_limit: int, stderr_limit: int) -> BoundedResult:
    started = time.monotonic_ns()
    process = subprocess.Popen(
        argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, start_new_session=True,
    )
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ, name)
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": stdout_limit, "stderr": stderr_limit}
    deadline = time.monotonic() + timeout_seconds
    timed_out = False
    limited = False
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                kill_group(process)
                remaining = 0.05
            events = selector.select(min(max(remaining, 0.0), 0.1))
            for key, _mask in events:
                name = key.data
                try:
                    chunk = os.read(key.fileobj.fileno(), CHUNK)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                room = limits[name] + 1 - len(buffers[name])
                if room > 0:
                    buffers[name].extend(chunk[:room])
                if len(buffers[name]) > limits[name]:
                    limited = True
                    kill_group(process)
            if timed_out or limited:
                # Continue draining until both pipes close after group termination.
                continue
        returncode = process.wait(timeout=5)
    except BaseException:
        kill_group(process)
        try:
            process.wait(timeout=5)
        except BaseException:
            pass
        raise
    finally:
        selector.close()
    wall = time.monotonic_ns() - started
    sig = -returncode if returncode < 0 else None
    exit_code = returncode if returncode >= 0 else None
    return BoundedResult(exit_code, sig, timed_out, limited, wall,
                         bytes(buffers["stdout"][:stdout_limit]),
                         bytes(buffers["stderr"][:stderr_limit]))


def command(analyzer: Path, fixture: dict[str, Any], target: Path) -> list[str]:
    argv = [os.fspath(analyzer), fixture["command"]]
    if fixture["command"] in {"gadgets", "analyze"}:
        argv.extend(["--format", "json", "--max-depth", str(fixture["max_depth"])])
    argv.append(os.fspath(target))
    return argv


def ordered_fixtures(fixtures: list[dict[str, Any]], round_index: int) -> list[dict[str, Any]]:
    offset = round_index % len(fixtures)
    rotated = fixtures[offset:] + fixtures[:offset]
    return list(reversed(rotated)) if round_index % 2 else rotated


def summary(authority: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    q = authority["qualification"]
    out: list[dict[str, Any]] = []
    qualified = 0
    for fixture in authority["fixtures"]:
        selected = [row for row in rows if row["fixture_id"] == fixture["id"]]
        require(len(selected) == 10 and sum(row["phase"] == "warmup" for row in selected) == 1,
                f"preflight row denominator changed: {fixture['id']}")
        measured = [row for row in selected if row["phase"] == "measured"]
        values = [row["wall_ns"] for row in measured]
        median = statistics.median(values)
        mad = statistics.median(abs(value - median) for value in values)
        failures = sum(row["exit_code"] != 0 or row["signal"] is not None
                       or row["timeout"] or row["output_limited"] for row in selected)
        stdout_hashes = {row["stdout_sha256"] for row in selected}
        stderr_hashes = {row["stderr_sha256"] for row in selected}
        ok = (failures == 0 and median >= q["minimum_median_ns"]
              and mad / median <= q["maximum_mad_to_median_ratio"]
              and len(stdout_hashes) == 1 and len(stderr_hashes) == 1)
        qualified += int(ok)
        out.append({
            "id": fixture["id"],
            "measured_runs": 9,
            "median_ns": median,
            "mad_ns": mad,
            "mad_to_median_ratio": mad / median,
            "failures": failures,
            "stdout_stable": len(stdout_hashes) == 1,
            "stderr_stable": len(stderr_hashes) == 1,
            "qualified": ok,
        })
    return out, qualified


def checksum_tree(root: Path) -> dict[str, str]:
    actual: dict[str, str] = {}
    for item in root.rglob("*"):
        rel = item.relative_to(root).as_posix()
        metadata = item.lstat()
        require(not stat.S_ISLNK(metadata.st_mode), f"linked preflight evidence rejected: {rel}")
        if stat.S_ISREG(metadata.st_mode):
            require(metadata.st_nlink == 1, f"hard-linked preflight evidence rejected: {rel}")
            if rel != "SHA256SUMS.txt":
                actual[rel] = sha(item)
        elif not stat.S_ISDIR(metadata.st_mode):
            raise PreflightError(f"special preflight evidence rejected: {rel}")
    return actual


def write_checksums(root: Path) -> None:
    rows = [f"{digest}  {path}" for path, digest in sorted(checksum_tree(root).items())]
    output = root / "SHA256SUMS.txt"
    output.write_text("\n".join(rows) + "\n", encoding="utf-8")
    output.chmod(0o444)


def verify_checksums(root: Path) -> int:
    manifest = root / "SHA256SUMS.txt"
    require(manifest.is_file() and not manifest.is_symlink(), "preflight checksum manifest missing")
    declared: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        require(len(line) >= 67 and line[64:66] == "  ", "malformed preflight checksum row")
        digest, rel = line[:64], safe_rel(line[66:])
        require(len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)
                and rel not in declared and rel != "SHA256SUMS.txt",
                "invalid/duplicate preflight checksum row")
        declared[rel] = digest
    actual = checksum_tree(root)
    require(declared == actual, "preflight checksum membership or bytes changed")
    return len(declared)


def validate_result(root: Path, authority: dict[str, Any], expected_tree: str) -> dict[str, Any]:
    verify_checksums(root)
    result = load(root / "manifest.json")
    rows = load(root / "rows.json")
    require(result["schema"] == RESULT_SCHEMA and result["sprint"] == 13 and result["patch"] == 90,
            "preflight result identity changed")
    require(result["source_candidate_tree"] == expected_tree
            and result["experiment_id"] == authority["experiment_id"],
            "preflight source or experiment changed")
    require(result["execution_count"] == 80 and len(rows) == 80,
            "preflight execution denominator changed")
    fixture_summaries, qualified = summary(authority, rows)
    require(result["fixture_results"] == fixture_summaries
            and result["qualified_fixtures"] == qualified,
            "preflight summaries do not match retained rows")
    decision = ("proceed_to_fresh_paired_160_run_matrix" if qualified >= 6
                else "retire_phase_instrumentation_for_current_workloads")
    require(result["decision"] == decision and result["preflight_rows_reusable"] is False,
            "preflight decision changed")
    require(result["public_fields_added"] == 0 and result["semantic_changes"] == 0
            and result["score_changes"] == 0 and result["schema_changed"] is False
            and result["publication_eligible"] is False,
            "preflight public boundary changed")
    return result


def run_preflight(authority: dict[str, Any], authority_path: Path, source_root: Path,
                  source_manifest_path: Path, expected_tree: str, analyzer: Path,
                  analyzer_source_tree: str, target_root: Path, result_dir: Path,
                  evidence_class: str) -> dict[str, Any]:
    require(not result_dir.exists(), f"preflight result already exists: {result_dir}")
    helper_path = ROOT / "tools/gitless-source-manifest.py"
    spec = importlib.util.spec_from_file_location("p090_gitless_source", helper_path)
    require(spec is not None and spec.loader is not None, "cannot load Git-less source helper")
    helper = importlib.util.module_from_spec(spec)
    sys.modules["p090_gitless_source"] = helper
    spec.loader.exec_module(helper)
    source_manifest = helper.load_manifest(source_manifest_path)
    helper.verify(source_root, source_manifest)
    require(source_manifest.get("candidate_tree") == expected_tree,
            "preflight source manifest is not the required candidate tree")
    analyzer = analyzer.resolve(strict=True)
    analyzer_identity = regular(analyzer, executable=True)
    target_root = target_root.resolve(strict=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{result_dir.name}.stage.", dir=result_dir.parent))
    stage.chmod(0o755)
    try:
        (stage / "targets").mkdir(mode=0o755)
        (stage / "canonical-output").mkdir(mode=0o755)
        retained_analyzer = stage / "analyzer"
        retained_analyzer.write_bytes(analyzer.read_bytes())
        retained_analyzer.chmod(0o555)
        retained_source = stage / "source-manifest.json"
        retained_source.write_bytes(source_manifest_path.read_bytes())
        retained_source.chmod(0o444)
        retained_authority = stage / "authority.json"
        retained_authority.write_bytes(authority_path.read_bytes())
        retained_authority.chmod(0o444)
        target_paths: dict[str, Path] = {}
        target_identities: dict[str, dict[str, Any]] = {}
        for fixture in authority["fixtures"]:
            source = target_root / safe_rel(fixture["target_path"])
            identity = regular(source, executable=True)
            destination = stage / "targets" / fixture["id"]
            destination.write_bytes(source.read_bytes())
            destination.chmod(0o444)
            target_paths[fixture["id"]] = destination
            target_identities[fixture["id"]] = {**identity, "retained_path": f"targets/{fixture['id']}"}
        rows: list[dict[str, Any]] = []
        canonical_outputs: dict[str, tuple[str, str]] = {}
        sequence = 0
        execution = authority["execution"]
        for round_index in range(10):
            phase = "warmup" if round_index == 0 else "measured"
            for fixture in ordered_fixtures(authority["fixtures"], round_index):
                sequence += 1
                target = target_paths[fixture["id"]]
                before_analyzer = regular(retained_analyzer, executable=True)
                before_target = regular(target, executable=False)
                observed = bounded_run(
                    command(retained_analyzer, fixture, target), stage,
                    execution["timeout_seconds"], execution["stdout_limit_bytes"],
                    execution["stderr_limit_bytes"],
                )
                require(regular(retained_analyzer, executable=True) == before_analyzer,
                        "preflight analyzer changed during execution")
                require(regular(target, executable=False) == before_target,
                        f"preflight target changed during execution: {fixture['id']}")
                stdout_sha = sha_bytes(observed.stdout)
                stderr_sha = sha_bytes(observed.stderr)
                if fixture["id"] not in canonical_outputs:
                    out_path = stage / "canonical-output" / f"{fixture['id']}.stdout"
                    err_path = stage / "canonical-output" / f"{fixture['id']}.stderr"
                    out_path.write_bytes(observed.stdout); out_path.chmod(0o444)
                    err_path.write_bytes(observed.stderr); err_path.chmod(0o444)
                    canonical_outputs[fixture["id"]] = (stdout_sha, stderr_sha)
                rows.append({
                    "sequence": sequence,
                    "round": round_index,
                    "phase": phase,
                    "fixture_id": fixture["id"],
                    "argv": command(retained_analyzer, fixture, target),
                    "wall_ns": observed.wall_ns,
                    "exit_code": observed.exit_code,
                    "signal": observed.signal,
                    "timeout": observed.timeout,
                    "output_limited": observed.output_limited,
                    "stdout_sha256": stdout_sha,
                    "stdout_size_bytes": len(observed.stdout),
                    "stderr_sha256": stderr_sha,
                    "stderr_size_bytes": len(observed.stderr),
                })
        fixture_results, qualified = summary(authority, rows)
        decision = ("proceed_to_fresh_paired_160_run_matrix" if qualified >= 6
                    else "retire_phase_instrumentation_for_current_workloads")
        result = {
            "schema": RESULT_SCHEMA,
            "sprint": 13,
            "patch": 90,
            "experiment_id": authority["experiment_id"],
            "evidence_class": evidence_class,
            "publication_eligible": False,
            "source_candidate_tree": expected_tree,
            "analyzer_source_tree": analyzer_source_tree,
            "authority_sha256": sha(authority_path),
            "source_manifest_sha256": sha(source_manifest_path),
            "analyzer": analyzer_identity,
            "targets": target_identities,
            "execution_count": 80,
            "fixture_results": fixture_results,
            "qualified_fixtures": qualified,
            "decision": decision,
            "preflight_rows_reusable": False,
            "paired_matrix_execution_count_if_authorized": 160,
            "public_fields_added": 0,
            "semantic_changes": 0,
            "score_changes": 0,
            "schema_changed": False,
            "limitations": authority["limitations"],
        }
        rows_path = stage / "rows.json"
        rows_path.write_bytes(canonical(rows)); rows_path.chmod(0o444)
        manifest = stage / "manifest.json"
        manifest.write_bytes(canonical(result)); manifest.chmod(0o444)
        write_checksums(stage)
        validate_result(stage, authority, expected_tree)
        os.rename(stage, result_dir)
        return validate_result(result_dir, authority, expected_tree)
    except BaseException:
        if stage.exists():
            import shutil
            shutil.rmtree(stage)
        raise


def synthetic_rows(authority: dict[str, Any], qualified: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for round_index in range(10):
        phase = "warmup" if round_index == 0 else "measured"
        for fixture_index, fixture in enumerate(authority["fixtures"]):
            base = authority["qualification"]["minimum_median_ns"] + 1_000_000
            if fixture_index >= qualified:
                base = authority["timer_floor"]["timer_floor_ns"]
            wall = base + (round_index - 5) * 1000
            rows.append({
                "sequence": len(rows) + 1, "round": round_index, "phase": phase,
                "fixture_id": fixture["id"], "argv": ["x64lens", fixture["command"], fixture["target_path"]],
                "wall_ns": wall, "exit_code": 0, "signal": None, "timeout": False,
                "output_limited": False, "stdout_sha256": "0" * 64, "stdout_size_bytes": 0,
                "stderr_sha256": "1" * 64, "stderr_size_bytes": 0,
            })
    return rows


def selftest(authority: dict[str, Any]) -> int:
    mutations = 0
    for qualified, expected_decision in (
        (8, "proceed_to_fresh_paired_160_run_matrix"),
        (5, "retire_phase_instrumentation_for_current_workloads"),
    ):
        rows = synthetic_rows(authority, qualified)
        results, observed = summary(authority, rows)
        require(observed == qualified and len(results) == 8, "synthetic preflight result changed")
        decision = ("proceed_to_fresh_paired_160_run_matrix" if observed >= 6
                    else "retire_phase_instrumentation_for_current_workloads")
        require(decision == expected_decision, "preflight decision threshold changed")
    changed = json.loads(json.dumps(authority))
    changed["fixtures"][1]["command"] = changed["fixtures"][0]["command"]
    changed["fixtures"][1]["max_depth"] = changed["fixtures"][0]["max_depth"]
    changed["fixtures"][1]["target_role"] = changed["fixtures"][0]["target_role"]
    try:
        validate_authority(changed, load(ROOT / "tests/expected/sprint13-workload-reference-preflight-v1.json"))
    except PreflightError:
        mutations += 1
    else:
        raise PreflightError("duplicate semantic workload tuple accepted")
    require(mutations == 1, "preflight mutation denominator changed")
    return mutations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("selftest", "run", "verify"))
    parser.add_argument("--authority", type=Path, default=ROOT / "benchmarks/task-definitions/sprint13-workload-reference-preflight-v1.json")
    parser.add_argument("--expected", type=Path, default=ROOT / "tests/expected/sprint13-workload-reference-preflight-v1.json")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--expected-candidate-tree")
    parser.add_argument("--analyzer", type=Path)
    parser.add_argument("--analyzer-source-tree")
    parser.add_argument("--target-root", type=Path)
    parser.add_argument("--result-dir", type=Path)
    parser.add_argument("--evidence-class", choices=("fresh", "artifact_backed"), default="fresh")
    args = parser.parse_args()
    authority = validate_authority(load(args.authority), load(args.expected))
    if args.action == "selftest":
        mutations = selftest(authority)
        print("sprint13-workload-reference-preflight-smoke: ok mode=selftest fixtures=8 "
              "warmups=8 measured=72 executions=80 minimum_qualified=6 floor_ns=5894690 "
              f"minimum_median_ns=29473450 sample_reuse=0 mutation_rejections={mutations}")
        return 0
    required = (args.expected_candidate_tree, args.result_dir)
    require(all(required), "run/verify requires candidate tree and result directory")
    if args.action == "run":
        require(all((args.source_root, args.source_manifest, args.analyzer,
                     args.analyzer_source_tree, args.target_root)),
                "run requires source, analyzer, analyzer-source-tree, and target authorities")
        result = run_preflight(
            authority, args.authority.resolve(strict=True), args.source_root.resolve(strict=True),
            args.source_manifest.resolve(strict=True), args.expected_candidate_tree,
            args.analyzer.resolve(strict=True), args.analyzer_source_tree,
            args.target_root.resolve(strict=True), args.result_dir.resolve(), args.evidence_class,
        )
    else:
        result = validate_result(args.result_dir.resolve(strict=True), authority, args.expected_candidate_tree)
    print("sprint13-workload-reference-preflight-smoke: ok "
          f"mode={args.action} executions=80 qualified={result['qualified_fixtures']} "
          f"decision={result['decision']} sample_reuse=0 public_fields_added=0 "
          "semantic_changes=0 score_changes=0 schema_changed=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PreflightError, OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        fail(str(exc))
