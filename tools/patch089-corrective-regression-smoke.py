#!/usr/bin/env python3
"""Exercise the complete Patch 089 corrective boundary for Patch 090."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TREE = "1" * 40


class RegressionError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RegressionError(message)


def module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write(path: Path, data: bytes, mode: int) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)
    return {"path": "", "sha256": sha(path), "size_bytes": len(data), "mode": f"{mode:04o}"}


def expect_failure(function: Callable[[], Any], label: str) -> None:
    try:
        function()
    except Exception:
        return
    raise RegressionError(f"{label} was accepted")


def fake_producer(producer: Any, root: Path) -> tuple[Path, dict[str, Any]]:
    root.mkdir(mode=0o755)
    source = root / "source-manifest.json"
    source.write_bytes(canonical({"candidate_tree": TREE})); source.chmod(0o444)
    generations = []
    fact = "a" * 64
    for generation in range(1, 4):
        prefix = root / f"generation-{generation}"
        prefix.mkdir(mode=0o755)
        records: dict[str, Any] = {}
        for key, name, mode in (
            ("analyzer", "x64lens", 0o555),
            ("effects_fixture", "gadgets_sprint10_effects", 0o444),
            ("ordered_pairs_fixture", "gadgets_sprint13_ordered_pairs", 0o444),
            ("effects_report", "effects.json", 0o444),
            ("ordered_pairs_report", "ordered-pairs.json", 0o444),
            ("build_log", "build.log", 0o444),
        ):
            path = prefix / name
            descriptor = write(path, f"{generation}:{key}\n".encode(), mode)
            descriptor["path"] = path.relative_to(root).as_posix()
            if key.endswith("report"):
                descriptor.update({"command": "gadgets", "candidate_count": 25 if key == "effects_report" else 30})
            records[key] = descriptor
        generations.append({
            "generation": generation,
            "build_id": f"p082-independent-build-{generation}",
            "source_candidate_tree": TREE,
            "source_manifest_sha256": sha(source),
            "build_commands": ["make clean", "make -j1", "make -j1 samples"],
            **records,
            "normalized_fact_sha256": fact,
        })
    value = {
        "schema": producer.SCHEMA,
        "sprint": 13,
        "patch": 82,
        "evidence_class": "diagnostic",
        "publication_eligible": False,
        "source_candidate_tree": TREE,
        "source_manifest": {"path": source.name, "sha256": sha(source),
                            "size_bytes": source.stat().st_size, "mode": "0444"},
        "source_manifest_sha256": sha(source),
        "generation_count": 3,
        "generations": generations,
        "normalized_fact_sha256": fact,
        "public_boundary": {"runtime_records_added": 0, "public_fields_added": 0,
                            "semantic_changes": 0, "score_changes": 0, "schema_changed": False},
        "limitations": ["synthetic regression authority"],
    }
    manifest = root / "manifest.json"
    manifest.write_bytes(canonical(value)); manifest.chmod(0o444)
    producer.validate_manifest(manifest, TREE)
    expected = {**value, "selected": generations[:2],
                "_manifest_sha256": sha(manifest),
                "_source_manifest_sha256": sha(source),
                "_source_manifest_path": source}
    return manifest, expected


def producer_alias_check(producer: Any) -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p090-producer-") as raw:
        root = Path(raw) / "producer"
        manifest, _ = fake_producer(producer, root)
        source = root / "generation-1/x64lens"
        target = root / "generation-2/x64lens"
        target.unlink(); os.link(source, target)
        value = json.loads(manifest.read_text())
        record = value["generations"][1]["analyzer"]
        record["sha256"] = sha(target); record["size_bytes"] = target.stat().st_size
        manifest.chmod(0o644); manifest.write_bytes(canonical(value)); manifest.chmod(0o444)
        expect_failure(lambda: producer.validate_manifest(manifest, TREE), "aliased producer generations")
    return 1


def fake_split(split: Any, producer: Any) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any], tempfile.TemporaryDirectory[str]]:
    holder: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory(prefix="x64lens-p090-split-")
    base = Path(holder.name)
    producer_root = base / "producer-external"
    manifest, producer_expected = fake_producer(producer, producer_root)
    root = base / "result"; root.mkdir(mode=0o755)
    authority = split.load(ROOT / "benchmarks/task-definitions/sprint13-split-debug-packaging-v1.json")
    expected = split.load(ROOT / "tests/expected/sprint13-split-debug-packaging-v1.json")
    retained_producer = root / "producer"; retained_producer.mkdir(mode=0o755)
    (retained_producer / "manifest.json").write_bytes(manifest.read_bytes()); (retained_producer / "manifest.json").chmod(0o444)
    (retained_producer / "source-manifest.json").write_bytes((producer_root / "source-manifest.json").read_bytes()); (retained_producer / "source-manifest.json").chmod(0o444)
    for generation in (1, 2):
        target = retained_producer / f"generation-{generation}"; target.mkdir(mode=0o755)
        target_file = target / "x64lens"
        target_file.write_bytes((producer_root / f"generation-{generation}/x64lens").read_bytes()); target_file.chmod(0o555)
    build_results = []
    known = authority["known_symbols"]
    runtime_payload = b"runtime\n"; companion_payload = b"debug\n"
    for build in (1, 2):
        retained = root / f"build-{build}"; retained.mkdir(mode=0o755)
        runtime = retained / "x64lens"; runtime.write_bytes(runtime_payload); runtime.chmod(0o555)
        companion = retained / "x64lens.debug"; companion.write_bytes(companion_payload); companion.chmod(0o444)
        rows = []
        for profile in authority["behavior_profiles"]:
            args = list(profile["args"])
            if profile["target"] is not None: args.append(profile["target"])
            for variant in ("unstripped", "runtime"):
                raw_root = retained / "raw" / profile["id"]
                stdout = raw_root / f"{variant}.stdout"; stderr = raw_root / f"{variant}.stderr"
                out = write(stdout, b"", 0o444); err = write(stderr, b"", 0o444)
                out["path"] = stdout.relative_to(root).as_posix(); err["path"] = stderr.relative_to(root).as_posix()
                rows.append({"profile": profile["id"], "variant": variant, "args": args,
                             "exit_code": 0, "stdout": out, "stderr": err})
        behavior = retained / "behavior.json"; behavior.write_bytes(canonical(rows)); behavior.chmod(0o444)
        generation = producer_expected["generations"][build - 1]
        build_results.append({
            "build": build, "generation": build, "producer_build_id": generation["build_id"],
            "source_candidate_tree": TREE, "source_manifest_sha256": producer_expected["source_manifest_sha256"],
            "build_commands": ["make clean", "make -j1", "make -j1 samples"],
            "unstripped_sha256": generation["analyzer"]["sha256"],
            "unstripped_size_bytes": generation["analyzer"]["size_bytes"],
            "runtime": {"path": f"build-{build}/x64lens", "sha256": sha(runtime),
                        "size_bytes": runtime.stat().st_size, "mode": "0555"},
            "companion": {"path": f"build-{build}/x64lens.debug", "sha256": sha(companion),
                          "size_bytes": companion.stat().st_size, "mode": "0444"},
            "behavior": {"path": f"build-{build}/behavior.json", "sha256": sha(behavior),
                         "size_bytes": behavior.stat().st_size, "mode": "0444"},
            "runtime_size_reduction": 0.6, "total_transfer_reduction": -0.1,
            "debuglink_crc32": 1, "redacted_local_path_strings": 1,
            "symbol_resolutions": [{"symbol": symbol, "address": f"0x{index + build * 32:016x}",
                                    "location": f"src/{symbol}.asm:1"}
                                   for index, symbol in enumerate(known)],
            "behavior_executions": 30, "behavior_pairs": 15, "build_id_present": False,
        })
    result = {
        "schema": split.RESULT_SCHEMA, "sprint": 13, "patch": 89,
        "experiment_id": authority["experiment_id"], "evidence_class": "diagnostic",
        "publication_eligible": False, "product_adoption_authorized": False,
        "source_candidate_tree": TREE, "producer_manifest_sha256": sha(manifest),
        "producer_source_manifest_sha256": producer_expected["source_manifest_sha256"],
        "tools": {name: {"sha256": str(index + 1) * 64, "size_bytes": index + 1,
                         "mode": "0755", "version_sha256": str(index + 4) * 64}
                  for index, name in enumerate(("objcopy", "nm", "addr2line"))},
        "build_results": build_results,
        "companion_controls": [{"id": item, "passed": True} for item in authority["companion_controls"]],
        "summary": {"builds": 2, "behavior_executions": 60, "behavior_pairs": 30,
                    "companion_controls": 8, "symbol_resolutions": 12,
                    "minimum_runtime_size_reduction": 0.6, "build_id_present": False,
                    "local_path_leaks": 0, "runtime_bytes_equal_between_builds": True,
                    "companion_bytes_equal_between_builds": True, "path_stable_dwarf": False,
                    "post_link_redaction_used": True, "total_transfer_reduction": False},
        "retained_directories": [], "retained_members": [],
        "public_boundary": authority["public_boundary"], "limitations": authority["limitations"],
    }
    result["retained_directories"] = split.directory_authority(root)
    result["retained_members"] = split.retained_authority(root)
    split.validate_result(result, expected, TREE, root, authority, producer_expected)
    return root, result, authority, producer_expected, holder


def split_result_checks(split: Any, producer: Any) -> tuple[int, int, int, int, int]:
    root, result, authority, producer_expected, holder = fake_split(split, producer)
    expected = split.load(ROOT / "tests/expected/sprint13-split-debug-packaging-v1.json")
    try:
        runtime = root / "build-1/x64lens"
        saved = runtime.read_bytes(); runtime.chmod(0o755); runtime.write_bytes(b"substitute\n"); runtime.chmod(0o555)
        changed = copy.deepcopy(result)
        records = {row["path"]: row for row in changed["retained_members"]}
        records["build-1/x64lens"].update({"sha256": sha(runtime), "size_bytes": runtime.stat().st_size})
        expect_failure(lambda: split.validate_result(changed, expected, TREE, root, authority, producer_expected),
                       "runtime/build-result disagreement")
        runtime.chmod(0o755); runtime.write_bytes(saved); runtime.chmod(0o555)

        symbols = copy.deepcopy(result); symbols["build_results"][0]["symbol_resolutions"][0]["symbol"] = "invented"
        expect_failure(lambda: split.validate_result(symbols, expected, TREE, root, authority, producer_expected),
                       "invented split symbol")
        controls = copy.deepcopy(result); controls["companion_controls"][0]["passed"] = False
        expect_failure(lambda: split.validate_result(controls, expected, TREE, root, authority, producer_expected),
                       "failed split control")
        tools = copy.deepcopy(result); tools["tools"] = {}
        expect_failure(lambda: split.validate_result(tools, expected, TREE, root, authority, producer_expected),
                       "empty split tool authority")
        digest = copy.deepcopy(result); digest["producer_manifest_sha256"] = "f" * 64
        expect_failure(lambda: split.validate_result(digest, expected, TREE, root, authority, producer_expected),
                       "invented producer digest")
        return 1, 1, 1, 1, 1
    finally:
        holder.cleanup()


def recovery_checks(recovery: Any) -> tuple[int, int, int]:
    with tempfile.TemporaryDirectory(prefix="x64lens-p090-recovery-") as raw:
        root = Path(raw)
        source = root / "archive.tar"; source.write_bytes(b"payload")
        alias = root / "alias.tar"; os.link(source, alias)
        before = len(os.listdir("/proc/self/fd"))
        expect_failure(lambda: recovery.open_archive(source), "hard-linked archive preflight")
        after = len(os.listdir("/proc/self/fd"))
        require(before == after, "rejected archive preflight leaked a descriptor")
        alias.unlink()
        fd, stream, opened = recovery.open_archive(source)
        try:
            alias = root / "late-alias.tar"; os.link(source, alias)
            expect_failure(lambda: recovery.reauthenticate_archive(source, fd, opened), "late archive hardlink")
            alias.unlink()
        finally:
            stream.close(); os.close(fd)
        fd, stream, opened = recovery.open_archive(source)
        try:
            with source.open("ab") as handle: handle.write(b"drift")
            expect_failure(lambda: recovery.reauthenticate_archive(source, fd, opened), "late archive append")
        finally:
            stream.close(); os.close(fd)
    return 1, 1, 1


def custody_cap(custody: Any) -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p090-custody-") as raw:
        root = Path(raw) / "delivery"; root.mkdir(mode=0o755)
        manifest = root / "DELIVERY_CUSTODY_MANIFEST.json"
        with manifest.open("wb") as handle:
            handle.truncate(custody.MAX_MANIFEST_BYTES + 1)
        manifest.chmod(0o444)
        expect_failure(lambda: custody.verify(root, manifest), "oversized custody manifest")
    return 1


def terminal_argv(terminal: Any) -> int:
    valid = {"argv": ["/opt/x64lens", "gadgets", "--format", "json", "--max-depth", "4", "/x/targets/t1"]}
    terminal.validate_execution_argv("x64lens", "t1", valid)
    invalid = copy.deepcopy(valid); invalid["argv"][4] = "text"
    expect_failure(lambda: terminal.validate_execution_argv("x64lens", "t1", invalid), "fabricated replay argv")
    return 1


def workload_semantics(workload: Any) -> int:
    authority = json.loads(
        (ROOT / "benchmarks/task-definitions/sprint13-workload-phase-attribution-v1.json").read_text()
    )
    authority["fixtures"][1]["command"] = authority["fixtures"][0]["command"]
    authority["fixtures"][1]["max_depth"] = authority["fixtures"][0]["max_depth"]
    authority["fixtures"][1]["target_role"] = authority["fixtures"][0]["target_role"]
    expect_failure(lambda: workload.validate_authority(authority), "duplicate workload semantic tuple")
    return 1


def main() -> int:
    producer = module("p090_producer", ROOT / "tools/sprint13-producer-authority-smoke.py")
    split = module("p090_split", ROOT / "tools/sprint13-split-debug-packaging-smoke.py")
    recovery = module("p090_recovery", ROOT / "tools/recover-candidate-source.py")
    custody = module("p090_custody", ROOT / "tools/verify-delivery-custody.py")
    terminal = module("p090_terminal", ROOT / "tools/sprint13-natural-terminal-attribution-v2-smoke.py")
    workload = module("p090_workload", ROOT / "tools/sprint13-workload-phase-attribution-smoke.py")
    producer_alias = producer_alias_check(producer)
    runtime, symbols, controls, tools, digests = split_result_checks(split, producer)
    fd_leak, archive_hardlink, archive_append = recovery_checks(recovery)
    manifest_cap = custody_cap(custody)
    argv = terminal_argv(terminal)
    workload_tuple = workload_semantics(workload)
    print("patch089-corrective-regression-smoke: ok "
          f"producer_generation_alias={producer_alias} split_runtime_binding={runtime} "
          f"split_symbols={symbols} split_controls={controls} split_tools={tools} "
          f"split_producer_digests={digests} recovery_fd_cleanup={fd_leak} "
          f"recovery_archive_hardlink={archive_hardlink} recovery_archive_append={archive_append} "
          f"custody_manifest_cap={manifest_cap} replay_argv={argv} workload_semantic_tuple={workload_tuple} "
          "split_stage_mode=split_selftest loose_delivery=delivery_gate helper_size_cap=delivery_gate")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"patch089-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
