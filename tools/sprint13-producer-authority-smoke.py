#!/usr/bin/env python3
"""Build and authenticate three independent producer generations for P081 gates.

Patch 081's tuple and score/null authorities were structurally useful but did
not consume the analyzer they purported to govern.  This Patch 082 helper
materializes three independent build roots from one authenticated source tree,
builds the analyzer and fixtures in each root, retains the resulting reports,
and publishes one bounded manifest consumed by the two policy gates.

The helper is development-only.  It adds no runtime dependency and never
executes an analyzed target.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "x64lens-sprint13-producer-authority-v1"
GENERATION_COUNT = 3
EFFECTS_FIXTURE = "tests/bin/gadgets_sprint10_effects"
PAIRS_FIXTURE = "tests/bin/gadgets_sprint13_ordered_pairs"
MAX_REPORT_BYTES = 16 * 1024 * 1024


class ProducerError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProducerError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-producer-authority-smoke: error: {message}", file=sys.stderr)
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
    handle = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            handle.update(chunk)
    return handle.hexdigest()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    log: Path,
    expected: int = 0,
) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )
    with log.open("ab") as handle:
        handle.write(("$ " + " ".join(argv) + "\n").encode())
        handle.write(b"[stdout]\n" + completed.stdout + b"\n[stderr]\n" + completed.stderr + b"\n")
        handle.write(f"[exit] {completed.returncode}\n".encode())
    require(
        completed.returncode == expected,
        f"command failed ({completed.returncode}, expected {expected}): {' '.join(argv)}; see {log}",
    )
    return completed


def source_authority(
    repo: Path, workspace: Path, expected_candidate_tree: str
) -> tuple[Any, Path, dict[str, Any], str]:
    helper = load_module("p082_gitless_source", repo / "tools/gitless-source-manifest.py")
    env_manifest = os.environ.get("X64LENS_SOURCE_MANIFEST")
    env_root = os.environ.get("X64LENS_SOURCE_AUTHORITY_ROOT")
    require(bool(env_manifest) == bool(env_root), "Git-less source manifest and authority root must be supplied as one pair")
    if env_manifest:
        manifest_path = Path(env_manifest).resolve(strict=True)
        root = Path(env_root).resolve(strict=True)
        manifest = helper.load_manifest(manifest_path)
        helper.verify(root, manifest)
        require(
            manifest.get("candidate_tree") == expected_candidate_tree,
            "Git-less producer source is not the required candidate tree",
        )
        return helper, root, manifest, sha256_file(manifest_path)

    source_root = workspace / "authenticated-source"
    manifest_path = workspace / "authenticated-source-manifest.json"
    manifest = helper.create(repo, source_root, manifest_path)
    helper.verify(source_root, manifest)
    require(
        manifest.get("candidate_tree") == expected_candidate_tree,
        "producer source is not the required candidate tree",
    )
    return helper, source_root, manifest, sha256_file(manifest_path)


def copy_authenticated_source(helper: Any, source: Path, manifest: dict[str, Any], destination: Path) -> None:
    require(not destination.exists(), f"generation destination already exists: {destination}")
    destination.mkdir(mode=0o755)
    for record in manifest["directories"]:
        path = destination / record["path"]
        path.mkdir(parents=True, exist_ok=True, mode=int(record["mode"], 8))
        path.chmod(int(record["mode"], 8))
    for record in manifest["files"]:
        relative = record["path"]
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = (source / relative).read_bytes()
        require(sha256_bytes(payload) == record["sha256"], f"source byte identity changed while copying: {relative}")
        target.write_bytes(payload)
        target.chmod(int(record["mode"], 8))
    destination.chmod(int(manifest["root_mode"], 8))
    helper.verify(destination, manifest)


def retain_file(source: Path, destination: Path, mode: int = 0o444) -> dict[str, Any]:
    data = source.read_bytes()
    require(len(data) <= MAX_REPORT_BYTES or source.name == "x64lens", f"retained file exceeds bound: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    destination.chmod(mode)
    return {"path": destination.name, "sha256": sha256_bytes(data), "size_bytes": len(data), "mode": f"{mode:04o}"}


def report_descriptor(path: Path, result_root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    require(len(data) <= MAX_REPORT_BYTES, f"report exceeds bound: {path}")
    value = json.loads(data, object_pairs_hook=strict_pairs)
    return {
        "path": path.relative_to(result_root).as_posix(),
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
        "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}",
        "command": value.get("command"),
        "candidate_count": value.get("counts", {}).get("raw_candidate_count"),
    }


def normalized_effects(report: dict[str, Any]) -> list[dict[str, Any]]:
    gadgets = report.get("gadgets")
    require(isinstance(gadgets, list) and len(gadgets) == 25, "producer effects report must contain 25 candidates")
    return [
        {
            "index": index,
            "pattern": item.get("pattern"),
            "semantic_class": item.get("semantic_class"),
            "score": item.get("score"),
            "stack_pop_order": item.get("stack_pop_order"),
        }
        for index, item in enumerate(gadgets, 1)
    ]


def normalized_pairs(report: dict[str, Any]) -> list[dict[str, Any]]:
    gadgets = report.get("gadgets")
    require(isinstance(gadgets, list) and len(gadgets) == 30, "producer ordered-pair report must contain 30 candidates")
    return [
        {
            "index": index,
            "pattern": item.get("pattern"),
            "semantic_class": item.get("semantic_class"),
            "score": item.get("score"),
            "stack_delta": item.get("stack_delta"),
            "stack_pop_order": item.get("stack_pop_order"),
            "evidence_kind": (item.get("evidence") or {}).get("kind"),
        }
        for index, item in enumerate(gadgets, 1)
    ]


def build_generation(
    *,
    generation: int,
    helper: Any,
    authority_root: Path,
    manifest: dict[str, Any],
    source_manifest_sha256: str,
    workspace: Path,
    result_root: Path,
) -> dict[str, Any]:
    build_root = workspace / f"build-generation-{generation}"
    copy_authenticated_source(helper, authority_root, manifest, build_root)
    retained = result_root / f"generation-{generation}"
    retained.mkdir(mode=0o755)
    log = retained / "build.log"
    env = os.environ.copy()
    for key in ("X64LENS_SOURCE_MANIFEST", "X64LENS_SOURCE_AUTHORITY_ROOT", "MAKEFLAGS", "MAKEOVERRIDES", "MFLAGS", "MAKELEVEL"):
        env.pop(key, None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["TMPDIR"] = os.fspath(workspace / f"tmp-{generation}")
    Path(env["TMPDIR"]).mkdir()
    for command in (["make", "clean"], ["make", "-j1"], ["make", "-j1", "samples"]):
        run(list(command), cwd=build_root, env=env, log=log)

    analyzer = build_root / "build/x64lens"
    effects = build_root / EFFECTS_FIXTURE
    pairs = build_root / PAIRS_FIXTURE
    require(analyzer.is_file() and os.access(analyzer, os.X_OK), "independent analyzer build is missing")
    require(effects.is_file() and pairs.is_file(), "independent fixture build is missing")

    effects_report = retained / "effects.json"
    pairs_report = retained / "ordered-pairs.json"
    for target, output in ((effects, effects_report), (pairs, pairs_report)):
        completed = run(
            [os.fspath(analyzer), "gadgets", "--format", "json", "--max-depth", "8", os.fspath(target)],
            cwd=build_root,
            env=env,
            log=log,
        )
        output.write_bytes(completed.stdout)
        output.chmod(0o444)
        require(not completed.stderr, f"producer emitted unexpected stderr for {target.name}")

    analyzer_copy = retained / "x64lens"
    fixture_effects_copy = retained / "gadgets_sprint10_effects"
    fixture_pairs_copy = retained / "gadgets_sprint13_ordered_pairs"
    analyzer_descriptor = retain_file(analyzer, analyzer_copy, 0o555)
    effects_descriptor = retain_file(effects, fixture_effects_copy, 0o444)
    pairs_descriptor = retain_file(pairs, fixture_pairs_copy, 0o444)
    log.chmod(0o444)

    effects_value = load_json(effects_report)
    pairs_value = load_json(pairs_report)
    effects_facts = normalized_effects(effects_value)
    pair_facts = normalized_pairs(pairs_value)
    facts = {"effects": effects_facts, "ordered_pairs": pair_facts}
    return {
        "generation": generation,
        "build_id": f"p082-independent-build-{generation}",
        "source_candidate_tree": manifest["candidate_tree"],
        "source_manifest_sha256": source_manifest_sha256,
        "build_commands": ["make clean", "make -j1", "make -j1 samples"],
        "analyzer": {**analyzer_descriptor, "path": analyzer_copy.relative_to(result_root).as_posix()},
        "effects_fixture": {**effects_descriptor, "path": fixture_effects_copy.relative_to(result_root).as_posix()},
        "ordered_pairs_fixture": {**pairs_descriptor, "path": fixture_pairs_copy.relative_to(result_root).as_posix()},
        "build_log": {
            "path": log.relative_to(result_root).as_posix(),
            "sha256": sha256_file(log),
            "size_bytes": log.stat().st_size,
            "mode": "0444",
        },
        "effects_report": report_descriptor(effects_report, result_root),
        "ordered_pairs_report": report_descriptor(pairs_report, result_root),
        "normalized_fact_sha256": sha256_bytes(canonical(facts)),
    }


def validate_manifest(path: Path, expected_candidate_tree: str) -> dict[str, Any]:
    value = load_json(path)
    require(isinstance(value, dict), "producer manifest must be an object")
    require(set(value) == {
        "schema", "sprint", "patch", "evidence_class", "publication_eligible",
        "source_candidate_tree", "source_manifest", "source_manifest_sha256", "generation_count",
        "generations", "normalized_fact_sha256", "public_boundary", "limitations",
    }, "producer manifest shape changed")
    require(value["schema"] == SCHEMA and value["sprint"] == 13 and value["patch"] == 82, "producer manifest identity changed")
    require(
        value["source_candidate_tree"] == expected_candidate_tree,
        "producer manifest is not bound to the required candidate tree",
    )
    require(value["evidence_class"] == "diagnostic" and value["publication_eligible"] is False, "producer evidence boundary changed")
    source_manifest = value.get("source_manifest")
    require(isinstance(source_manifest, dict) and set(source_manifest) == {"path", "sha256", "size_bytes", "mode"}, "producer source-manifest descriptor changed")
    relative_manifest = PurePosixPath(source_manifest["path"])
    require(not relative_manifest.is_absolute() and ".." not in relative_manifest.parts, "unsafe producer source-manifest path")
    source_manifest_path = path.parent / relative_manifest
    require(source_manifest_path.is_file() and not source_manifest_path.is_symlink(), "producer source manifest missing")
    require(sha256_file(source_manifest_path) == source_manifest["sha256"] == value["source_manifest_sha256"], "producer source-manifest identity changed")
    require(source_manifest_path.stat().st_size == source_manifest["size_bytes"], "producer source-manifest size changed")
    require(stat.S_IMODE(source_manifest_path.stat().st_mode) == int(source_manifest["mode"], 8) == 0o444,
            "producer source-manifest mode changed")
    retained_source = load_json(source_manifest_path)
    require(retained_source.get("candidate_tree") == value["source_candidate_tree"], "retained producer source tree changed")
    require(value["generation_count"] == GENERATION_COUNT, "producer generation denominator changed")
    generations = value["generations"]
    require(isinstance(generations, list) and len(generations) == GENERATION_COUNT, "producer generations are incomplete")
    ids = [item.get("build_id") for item in generations]
    require(len(set(ids)) == GENERATION_COUNT, "producer build generations are not independent")
    require(all(item.get("source_candidate_tree") == value["source_candidate_tree"] for item in generations), "producer source trees disagree")
    require(all(item.get("source_manifest_sha256") == value["source_manifest_sha256"] for item in generations), "producer source manifests disagree")
    fact_hashes = {item.get("normalized_fact_sha256") for item in generations}
    require(fact_hashes == {value["normalized_fact_sha256"]}, "producer normalized facts disagree")
    root = path.parent
    for item in generations:
        expected_modes = {
            "analyzer": 0o555,
            "effects_fixture": 0o444,
            "ordered_pairs_fixture": 0o444,
            "effects_report": 0o444,
            "ordered_pairs_report": 0o444,
            "build_log": 0o444,
        }
        for key, expected_mode in expected_modes.items():
            record = item.get(key)
            require(isinstance(record, dict) and isinstance(record.get("path"), str), f"producer record missing: {key}")
            relative = PurePosixPath(record["path"])
            require(not relative.is_absolute() and ".." not in relative.parts, f"unsafe producer path: {record['path']}")
            member = root / relative
            require(member.is_file() and not member.is_symlink(), f"producer member missing: {record['path']}")
            require(sha256_file(member) == record["sha256"] and member.stat().st_size == record["size_bytes"], f"producer member identity changed: {record['path']}")
            require(record.get("mode") == f"{expected_mode:04o}", f"producer recorded mode changed: {record['path']}")
            require(stat.S_IMODE(member.stat().st_mode) == expected_mode, f"producer member mode changed: {record['path']}")
    require(value["public_boundary"] == {
        "runtime_records_added": 0,
        "public_fields_added": 0,
        "semantic_changes": 0,
        "score_changes": 0,
        "schema_changed": False,
    }, "producer public boundary changed")
    return value


def execute(repo: Path, result_dir: Path, expected_candidate_tree: str) -> dict[str, Any]:
    require(not result_dir.exists(), f"result directory already exists: {result_dir}")
    result_dir.parent.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(mode=0o755)
    with tempfile.TemporaryDirectory(prefix="x64lens-p082-producer-") as raw:
        workspace = Path(raw)
        helper, authority_root, source_manifest, source_manifest_file_sha = source_authority(
            repo, workspace, expected_candidate_tree
        )
        retained_source_manifest = result_dir / "source-manifest.json"
        retained_source_manifest.write_bytes(canonical(source_manifest))
        retained_source_manifest.chmod(0o444)
        retained_source_manifest_sha = sha256_file(retained_source_manifest)
        require(retained_source_manifest_sha == sha256_bytes(canonical(source_manifest)), "retained producer source-manifest identity changed")
        generations = [
            build_generation(
                generation=index,
                helper=helper,
                authority_root=authority_root,
                manifest=source_manifest,
                source_manifest_sha256=retained_source_manifest_sha,
                workspace=workspace,
                result_root=result_dir,
            )
            for index in range(1, GENERATION_COUNT + 1)
        ]
    fact_hashes = {item["normalized_fact_sha256"] for item in generations}
    require(len(fact_hashes) == 1, "independent producer generations disagree")
    value = {
        "schema": SCHEMA,
        "sprint": 13,
        "patch": 82,
        "evidence_class": "diagnostic",
        "publication_eligible": False,
        "source_candidate_tree": source_manifest["candidate_tree"],
        "source_manifest": {
            "path": retained_source_manifest.name,
            "sha256": retained_source_manifest_sha,
            "size_bytes": retained_source_manifest.stat().st_size,
            "mode": "0444",
        },
        "source_manifest_sha256": generations[0]["source_manifest_sha256"],
        "generation_count": GENERATION_COUNT,
        "generations": generations,
        "normalized_fact_sha256": next(iter(fact_hashes)),
        "public_boundary": {
            "runtime_records_added": 0,
            "public_fields_added": 0,
            "semantic_changes": 0,
            "score_changes": 0,
            "schema_changed": False,
        },
        "limitations": [
            "Independent builds validate current producer output; they do not establish full instruction-sequence validity.",
            "The retained reports are diagnostic and remain outside the Sprint 15-frozen campaign.",
            f"The caller-supplied or generated source-manifest identity before canonical retention was {source_manifest_file_sha}.",
        ],
    }
    manifest = result_dir / "manifest.json"
    manifest.write_bytes(canonical(value))
    manifest.chmod(0o444)
    validate_manifest(manifest, expected_candidate_tree)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--repo", type=Path, default=ROOT)
    run_parser.add_argument("--result-dir", type=Path, required=True)
    run_parser.add_argument("--expected-candidate-tree", required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser.add_argument("--expected-candidate-tree", required=True)
    args = parser.parse_args()
    try:
        if args.action == "run":
            value = execute(
                args.repo.resolve(strict=True),
                args.result_dir.resolve(),
                args.expected_candidate_tree,
            )
            manifest_path = args.result_dir.resolve() / "manifest.json"
        else:
            manifest_path = args.manifest.resolve(strict=True)
            value = validate_manifest(manifest_path, args.expected_candidate_tree)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ProducerError) as exc:
        fail(str(exc))
    print(
        "sprint13-producer-authority-smoke: ok "
        f"generations={value['generation_count']} source_tree={value['source_candidate_tree']} "
        "effects=25 ordered_pairs=30 producer_backed=1 independent_builds=3 "
        "public_fields_added=0 semantic_changes=0 score_changes=0 schema_changed=0 "
        f"manifest={manifest_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
