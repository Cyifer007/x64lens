#!/usr/bin/env python3
"""Discriminate every acceptance blocker promoted from the Patch 081 review."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class RegressionError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RegressionError(message)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, expected: int | None = 0) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=180)
    if expected is not None:
        require(
            completed.returncode == expected,
            f"command failed ({completed.returncode}, expected {expected}): {' '.join(argv)}\nstdout={completed.stdout[-2000:]!r}\nstderr={completed.stderr[-4000:]!r}",
        )
    return completed


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def init_repo(path: Path) -> None:
    path.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=path)
    run(["git", "config", "user.name", "regression"], cwd=path)
    run(["git", "config", "user.email", "regression@example.invalid"], cwd=path)
    (path / "Dockerfile").write_text("FROM scratch\nCOPY source/ /work/\n", encoding="utf-8")
    (path / "keep").write_text("tracked\n", encoding="utf-8")
    (path / "tools").mkdir()
    shutil.copy2(ROOT / "tools/gitless-source-manifest.py", path / "tools/gitless-source-manifest.py")
    run(["git", "add", "."], cwd=path)
    run(["git", "commit", "-qm", "base"], cwd=path)


def source_pairing(tmp: Path) -> tuple[int, int]:
    source = load_module("p082_pair_source", ROOT / "tools/gitless-source-manifest.py")
    patch070 = load_module("p082_pair_patch070", ROOT / "tools/patch070-corrective-regression-smoke.py")
    repo = tmp / "pair-repo"
    init_repo(repo)
    context = tmp / "pair-context"
    source.create_context(repo, context)
    old_manifest = os.environ.get("X64LENS_SOURCE_MANIFEST")
    old_root = os.environ.get("X64LENS_SOURCE_AUTHORITY_ROOT")
    old_patch_root = patch070.ROOT
    old_dont_write = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        patch070.ROOT = context / "source"
        os.environ["X64LENS_SOURCE_MANIFEST"] = str(context / "source-manifest.json")
        os.environ.pop("X64LENS_SOURCE_AUTHORITY_ROOT", None)
        try:
            patch070.source_custody_probe()
        except patch070.RegressionError:
            mismatched_rejected = 1
        else:
            raise RegressionError("manifest-only Git-less source authority was accepted")
        os.environ["X64LENS_SOURCE_AUTHORITY_ROOT"] = str(context / "source")
        patch070.source_custody_probe()
        paired_accepted = 1
    finally:
        patch070.ROOT = old_patch_root
        sys.dont_write_bytecode = old_dont_write
        shutil.rmtree(context / "source/tools/__pycache__", ignore_errors=True)
        if old_manifest is None:
            os.environ.pop("X64LENS_SOURCE_MANIFEST", None)
        else:
            os.environ["X64LENS_SOURCE_MANIFEST"] = old_manifest
        if old_root is None:
            os.environ.pop("X64LENS_SOURCE_AUTHORITY_ROOT", None)
        else:
            os.environ["X64LENS_SOURCE_AUTHORITY_ROOT"] = old_root
    return mismatched_rejected, paired_accepted


def nested_make_authority_isolation(tmp: Path) -> int:
    caller = tmp / "caller-authority.json"
    initial = b'{"caller":"must-survive"}\n'
    caller.write_bytes(initial)
    env = os.environ.copy()
    env.update({"TMPDIR": str(tmp), "TMP": str(tmp), "TEMP": str(tmp), "PYTHONDONTWRITEBYTECODE": "1"})
    completed = run(
        ["make", "--no-print-directory", f"DOCKER_IMAGE_AUTHORITY={caller}", "patch078-corrective-regression-smoke"],
        cwd=ROOT,
        env=env,
    )
    require(b"patch078-corrective-regression-smoke: ok" in completed.stdout, "nested Make regression did not pass")
    require(caller.read_bytes() == initial, "nested Make overwrote caller-selected authority")
    return 1


def ordinary_extraction_custody(tmp: Path) -> int:
    custody = load_module("p082_mode_custody", ROOT / "tools/verify-delivery-custody.py")
    stage = tmp / "mode-stage"
    root = stage / "portable-package"
    root.mkdir(parents=True, mode=0o755)
    root.chmod(0o755)
    payload = root / "payload.txt"
    payload.write_text("portable\n", encoding="utf-8")
    payload.chmod(0o644)
    manifest = root / "DELIVERY_CUSTODY_MANIFEST.json"
    custody.create(root, manifest, "p082-portable-mode-regression")
    custody.verify(root, manifest)
    archive = tmp / "portable-package.zip"
    run(["zip", "-q", "-r", str(archive), root.name], cwd=stage)
    extracted = tmp / "mode-extracted"
    extracted.mkdir()
    run(["unzip", "-q", str(archive), "-d", str(extracted)])
    extracted_root = extracted / root.name
    custody.verify(extracted_root, extracted_root / manifest.name)
    require((extracted_root.stat().st_mode & 0o7777) == 0o755, "ordinary extraction changed the portable root mode")
    return 1


def descriptor(path: Path, root: Path) -> dict[str, Any]:
    return {"path": path.relative_to(root).as_posix(), "sha256": sha(path), "size_bytes": path.stat().st_size}


def create_synthetic_producer(tmp: Path) -> Path:
    result = tmp / "producer"
    result.mkdir()
    source_manifest = result / "source-manifest.json"
    source_manifest.write_bytes(canonical({"candidate_tree": "1" * 40}))
    source_manifest.chmod(0o444)
    source_manifest_sha = sha(source_manifest)
    effects_template = json.loads((ROOT / "tests/expected/x64lens-report-sprint10-effects-0.2.0.json").read_text(encoding="utf-8"))
    pair_authority = json.loads((ROOT / "benchmarks/task-definitions/sprint13-ordered-two-pop-role-task-value-v2.json").read_text(encoding="utf-8"))
    pair_report = {"gadgets": []}
    for row in pair_authority["structural_pairs"]:
        pair_report["gadgets"].append({
            "pattern": "pop reg; pop reg; ret", "semantic_class": "arg_control",
            "score": 95, "stack_delta": 24, "stack_delta_known": True,
            "stack_pop_order": row["register_order"], "evidence": {"kind": "semantic_exact"},
        })
    generations = []
    fact_hash = hashlib.sha256(b"synthetic-producer-facts-v1").hexdigest()
    for number in range(1, 4):
        directory = result / f"generation-{number}"
        directory.mkdir()
        for name, payload, mode in (
            ("x64lens", b"synthetic analyzer\n", 0o555),
            ("gadgets_sprint10_effects", b"effects fixture\n", 0o444),
            ("gadgets_sprint13_ordered_pairs", b"pairs fixture\n", 0o444),
        ):
            path = directory / name
            path.write_bytes(payload)
            path.chmod(mode)
        effects = directory / "effects.json"
        effects.write_bytes(canonical(effects_template)); effects.chmod(0o444)
        pairs = directory / "ordered-pairs.json"
        pairs.write_bytes(canonical(pair_report)); pairs.chmod(0o444)
        generations.append({
            "generation": number, "build_id": f"p082-independent-build-{number}",
            "source_candidate_tree": "1" * 40, "source_manifest_sha256": source_manifest_sha,
            "build_commands": ["make clean", "make -j1", "make -j1 samples"],
            "analyzer": descriptor(directory / "x64lens", result),
            "effects_fixture": descriptor(directory / "gadgets_sprint10_effects", result),
            "ordered_pairs_fixture": descriptor(directory / "gadgets_sprint13_ordered_pairs", result),
            "effects_report": {**descriptor(effects, result), "command": "gadgets", "candidate_count": 25},
            "ordered_pairs_report": {**descriptor(pairs, result), "command": "gadgets", "candidate_count": 30},
            "normalized_fact_sha256": fact_hash,
        })
    manifest_value = {
        "schema": "x64lens-sprint13-producer-authority-v1", "sprint": 13, "patch": 82,
        "evidence_class": "diagnostic", "publication_eligible": False,
        "source_candidate_tree": "1" * 40,
        "source_manifest": descriptor(source_manifest, result),
        "source_manifest_sha256": source_manifest_sha,
        "generation_count": 3, "generations": generations,
        "normalized_fact_sha256": fact_hash,
        "public_boundary": {"runtime_records_added": 0, "public_fields_added": 0, "semantic_changes": 0, "score_changes": 0, "schema_changed": False},
        "limitations": ["synthetic adversarial producer authority"],
    }
    manifest = result / "manifest.json"
    manifest.write_bytes(canonical(manifest_value)); manifest.chmod(0o444)
    return manifest


def update_manifest_identity(manifest_path: Path, *, fact_marker: bytes) -> None:
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    fact_hash = hashlib.sha256(fact_marker).hexdigest()
    for generation in value["generations"]:
        generation["effects_report"].update(descriptor(manifest_path.parent / generation["effects_report"]["path"], manifest_path.parent))
        generation["ordered_pairs_report"].update(descriptor(manifest_path.parent / generation["ordered_pairs_report"]["path"], manifest_path.parent))
        generation["normalized_fact_sha256"] = fact_hash
    value["normalized_fact_sha256"] = fact_hash
    manifest_path.chmod(0o644)
    manifest_path.write_bytes(canonical(value)); manifest_path.chmod(0o444)


def producer_oracle_discrimination(tmp: Path) -> tuple[int, int, int]:
    manifest = create_synthetic_producer(tmp)
    tuple_command = [
        sys.executable, str(ROOT / "tools/sprint13-ordered-two-pop-role-task-value-smoke.py"),
        "--authority", str(ROOT / "benchmarks/task-definitions/sprint13-ordered-two-pop-role-task-value-v2.json"),
        "--expected", str(ROOT / "tests/expected/sprint13-ordered-two-pop-role-task-value-v2.json"),
        "--producer-manifest", str(manifest),
    ]
    score_command = [
        sys.executable, str(ROOT / "tools/sprint13-score-null-authority-smoke.py"),
        "--authority", str(ROOT / "benchmarks/task-definitions/sprint13-score-null-authority-v2.json"),
        "--expected", str(ROOT / "tests/expected/sprint13-score-null-authority-v2.json"),
        "--producer-manifest", str(manifest),
    ]
    run(tuple_command); run(score_command)
    baseline_pass = 1

    # Mutate the emitted score in all three producer generations.  Re-seal the
    # synthetic evidence so rejection must come from producer semantics rather
    # than a stale digest.
    for number in range(1, 4):
        path = manifest.parent / f"generation-{number}/effects.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["gadgets"][20]["score"] = 94
        path.chmod(0o644); path.write_bytes(canonical(value)); path.chmod(0o444)
    update_manifest_identity(manifest, fact_marker=b"score-94")
    require(run(score_command, expected=None).returncode != 0, "producer-backed score gate accepted score 94")
    score_rejected = 1

    # Restore scores, then mutate one ordered pair in all producer generations.
    for number in range(1, 4):
        effects = manifest.parent / f"generation-{number}/effects.json"
        value = json.loads(effects.read_text(encoding="utf-8"))
        value["gadgets"][20]["score"] = 95
        effects.chmod(0o644); effects.write_bytes(canonical(value)); effects.chmod(0o444)
        pairs = manifest.parent / f"generation-{number}/ordered-pairs.json"
        pair_value = json.loads(pairs.read_text(encoding="utf-8"))
        pair_value["gadgets"][0]["stack_pop_order"] = ["rsi", "rdi"]
        pairs.chmod(0o644); pairs.write_bytes(canonical(pair_value)); pairs.chmod(0o444)
    update_manifest_identity(manifest, fact_marker=b"pair-reversed")
    require(run(tuple_command, expected=None).returncode != 0, "producer-backed tuple gate accepted reversed order")
    tuple_rejected = 1
    return baseline_pass, score_rejected, tuple_rejected


def docker_source_build_separation() -> int:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    parity = (ROOT / "tools/native-docker-json-parity-smoke.sh").read_text(encoding="utf-8")
    require(makefile.count("run=/x64lens-run") >= 2, "Docker test/validation recipes lack a separate run tree")
    require("python3 /work/tools/gitless-source-manifest.py verify --root /work" in makefile, "Docker recipes do not reverify pristine source")
    require(makefile.count("X64LENS_SOURCE_MANIFEST=/x64lens-source-manifest.json") >= 2, "Docker mutable recipes do not pass the paired source manifest")
    require(makefile.count("X64LENS_SOURCE_AUTHORITY_ROOT=/work") >= 2, "Docker mutable recipes do not pass the paired source root")
    require("cd /work; make clean; make" not in makefile, "Docker recipe still builds in the source authority root")
    require("run=/x64lens-run" in parity and "cd \"$run\"" in parity, "native/Docker JSON parity still builds in /work")
    require("X64LENS_SOURCE_MANIFEST=/x64lens-source-manifest.json" in parity and "X64LENS_SOURCE_AUTHORITY_ROOT=/work" in parity, "native/Docker JSON parity lacks paired source authority")
    return 1



def producer_cleanup_contract() -> int:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    require('temporary_identity="$$(python3 tools/remove-owned-tree.py --identify "$$temporary_root")"' in makefile, "producer temporary root is not identity-bound")
    require('python3 tools/remove-owned-tree.py --remove "$$temporary_root" --identity "$$temporary_identity"' in makefile, "producer temporary cleanup is not identity-bound")
    require('rm -rf "$$(dirname "$$result_dir")"' not in makefile, "producer temporary cleanup still uses recursive pathname deletion")
    return 1

def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p082-corrective-") as raw:
        tmp = Path(raw)
        pair_rejected, pair_accepted = source_pairing(tmp)
        make_isolation = nested_make_authority_isolation(tmp)
        extraction = ordinary_extraction_custody(tmp)
        producer_pass, score_rejected, tuple_rejected = producer_oracle_discrimination(tmp)
    docker_separation = docker_source_build_separation()
    producer_cleanup = producer_cleanup_contract()
    print(
        "patch081-corrective-regression-smoke: ok "
        f"manifest_root_pair_rejected={pair_rejected} manifest_root_pair_accepted={pair_accepted} "
        f"nested_make_authority_isolated={make_isolation} ordinary_unzip_custody={extraction} "
        f"docker_pristine_source={docker_separation} producer_cleanup_identity={producer_cleanup} producer_baseline={producer_pass} "
        f"producer_score_mutation_rejected={score_rejected} producer_tuple_mutation_rejected={tuple_rejected} "
        "scoped_loose_helpers=delivery_gate package_modes=delivery_gate evidence_rows=delivery_gate"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"patch081-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
