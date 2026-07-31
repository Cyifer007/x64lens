#!/usr/bin/env python3
"""Regress confirmed Patch 068 corpus, held-out, leak, and build defects."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks/corpus/generated/s11-p056-provisional-v1"
ANALYZER = ROOT / "build/x64lens"
PROBE = ROOT / "build/tests/role-property-fact-probe"
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint12-role-property-heldout-v1.json"
SCHEMA = ROOT / "schemas/x64lens-report.schema.json"


class RegressionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def load(name: str, relative: str) -> Any:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module



def remove_owned_tree(path: Path) -> None:
    if not path.exists():
        return
    helper = ROOT / "tools/remove-owned-tree.py"
    identified = subprocess.run(
        [sys.executable, str(helper), "--identify", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10.0,
    )
    require(identified.returncode == 0, f"cannot identify owned result: {identified.stderr!r}")
    removed = subprocess.run(
        [sys.executable, str(helper), "--remove", str(path), "--identity", identified.stdout.decode().strip()],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=20.0,
    )
    require(removed.returncode == 0 and not path.exists(),
            f"cannot remove owned result: {removed.stderr!r}")

def copy_corpus(parent: Path) -> Path:
    require(CORPUS.is_dir(), f"authenticated corpus is missing: {CORPUS}")
    destination = parent / CORPUS.name
    shutil.copytree(CORPUS, destination, copy_function=shutil.copy2)
    return destination


def modes(root: Path) -> dict[str, int]:
    return {".": stat.S_IMODE(root.stat().st_mode)} | {
        path.relative_to(root).as_posix(): stat.S_IMODE(path.lstat().st_mode)
        for path in sorted(root.rglob("*"))
    }


def rewrite_manifest(candidate: Path, publication_eligible: bool) -> None:
    manifest_path = candidate / "corpus-manifest.json"
    checksum_path = candidate / "SHA256SUMS.txt"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["publication_eligible"] = publication_eligible
    data = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    manifest_path.chmod(0o644)
    manifest_path.write_bytes(data)
    manifest_path.chmod(0o444)
    os.utime(manifest_path, ns=(0, 0))
    digest = hashlib.sha256(data).hexdigest()
    lines = [
        f"{digest}  corpus-manifest.json" if line.endswith("  corpus-manifest.json") else line
        for line in checksum_path.read_text(encoding="utf-8").splitlines()
    ]
    checksum_path.chmod(0o644)
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    checksum_path.chmod(0o444)
    os.utime(checksum_path, ns=(0, 0))
    os.utime(candidate, ns=(0, 0))


def retained_semantic_probe(corpus: Any, parent: Path) -> None:
    candidate = copy_corpus(parent)
    valid_manifest = (candidate / "corpus-manifest.json").read_bytes()
    valid_sums = (candidate / "SHA256SUMS.txt").read_bytes()
    rewrite_manifest(candidate, True)
    (candidate / "commands.tsv").chmod(0o600)
    before = modes(candidate)
    original = corpus.verify_retained_corpus_snapshot
    fired = False

    def transient_visible_valid(opened, expected_root_name, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal fired
        if not fired:
            fired = True
            manifest = candidate / "corpus-manifest.json"
            sums = candidate / "SHA256SUMS.txt"
            invalid_manifest = manifest.read_bytes()
            invalid_sums = sums.read_bytes()
            manifest.chmod(0o644); sums.chmod(0o644)
            manifest.write_bytes(valid_manifest); sums.write_bytes(valid_sums)
            manifest.chmod(0o444); sums.chmod(0o444)
            os.utime(manifest, ns=(0, 0)); os.utime(sums, ns=(0, 0)); os.utime(candidate, ns=(0, 0))
            try:
                return original(opened, expected_root_name, **kwargs)
            finally:
                manifest.chmod(0o644); sums.chmod(0o644)
                manifest.write_bytes(invalid_manifest); sums.write_bytes(invalid_sums)
                manifest.chmod(0o444); sums.chmod(0o444)
                os.utime(manifest, ns=(0, 0)); os.utime(sums, ns=(0, 0)); os.utime(candidate, ns=(0, 0))
        return original(opened, expected_root_name, **kwargs)

    corpus.verify_retained_corpus_snapshot = transient_visible_valid
    rejected = False
    try:
        corpus.repair_corpus_modes(candidate)
    except corpus.CorpusError:
        rejected = True
    finally:
        corpus.verify_retained_corpus_snapshot = original
    require(fired and rejected, "transient valid visible path bypassed retained semantic authority")
    require(modes(candidate) == before, "retained semantic rejection changed corpus modes")
    require(json.loads((candidate / "corpus-manifest.json").read_text())["publication_eligible"] is True,
            "visible invalid semantic state was not preserved")


def signal_child(candidate: Path) -> int:
    corpus = load("p069_signal_builder", "benchmarks/scripts/build-provisional-corpus.py")
    original = corpus.os.fchmod
    fired = False

    def terminate(fd: int, mode: int) -> None:
        nonlocal fired
        before = stat.S_IMODE(os.fstat(fd).st_mode)
        original(fd, mode)
        after = stat.S_IMODE(os.fstat(fd).st_mode)
        if not fired and before != after:
            fired = True
            os.kill(os.getpid(), signal.SIGTERM)

    corpus.os.fchmod = terminate
    try:
        corpus.repair_corpus_modes(candidate)
    except corpus.CorpusInterrupted:
        return 0 if fired and stat.S_IMODE((candidate / "commands.tsv").stat().st_mode) == 0o600 else 2
    except corpus.CorpusError:
        return 3
    return 4


def signal_probe(parent: Path) -> None:
    candidate = copy_corpus(parent)
    (candidate / "commands.tsv").chmod(0o600)
    cp = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--signal-child", str(candidate)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=20.0)
    require(cp.returncode == 0,
            f"SIGTERM rollback child failed: exit={cp.returncode} stdout={cp.stdout!r} stderr={cp.stderr!r}")
    require(stat.S_IMODE((candidate / "commands.tsv").stat().st_mode) == 0o600,
            "SIGTERM left a partial corpus mode repair")


def directory_size_probe(corpus: Any, parent: Path, relative: str) -> None:
    candidate = copy_corpus(parent)
    (candidate / "commands.tsv").chmod(0o600)
    before = modes(candidate)
    victim = candidate if relative == "." else candidate / relative
    initial_size = victim.stat().st_size
    original = corpus.verify_retained_corpus_snapshot
    fired = False

    def churn(opened, expected_root_name, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal fired
        result = original(opened, expected_root_name, **kwargs)
        if not fired:
            fired = True
            for index in range(256):
                (victim / f".p069-churn-{index:04d}").write_bytes(b"x")
            for index in range(256):
                (victim / f".p069-churn-{index:04d}").unlink()
            os.utime(victim, ns=(0, 0))
        return result

    corpus.verify_retained_corpus_snapshot = churn
    rejected = False
    try:
        corpus.repair_corpus_modes(candidate)
    except corpus.CorpusError:
        rejected = True
    finally:
        corpus.verify_retained_corpus_snapshot = original
    require(fired and victim.stat().st_size != initial_size and rejected,
            f"directory metadata churn was accepted: {relative}")
    require(modes(candidate) == before, f"directory metadata rejection changed modes: {relative}")


def leak_probe() -> None:
    module = load("p069_leak", "tools/sprint12-role-property-metamorphic-smoke.py")
    for key in ("binaryRole", "gnu-property", "private_role_namespace", "property_note_count"):
        try:
            module.assert_no_private_public_fields({key: 1})
        except RuntimeError:
            continue
        raise RegressionError(f"private JSON key was accepted: {key}")
    for marker in (b"binary_role", b"property_note_count", b"property_overlap_count"):
        try:
            module.assert_no_private_public_text(marker)
        except RuntimeError:
            continue
        raise RegressionError(f"private text marker was accepted: {marker!r}")

    original = module.run
    def synthetic(command, *, expected=0):  # type: ignore[no-untyped-def]
        del expected
        stdout = (json.dumps({"schema_version": "0.2.0", "command": command[1]}).encode()
                  if "--format" in command else b"public output\n")
        return subprocess.CompletedProcess(command, 0, stdout=stdout,
                                           stderr=b"private_role_namespace=1\n")
    module.run = synthetic
    try:
        rejected = False
        try:
            module.validate_public(Path("synthetic-analyzer"), Path("synthetic-target"))
        except RuntimeError:
            rejected = True
    finally:
        module.run = original
    require(rejected, "public command stderr private leak was accepted")


def heldout_authority_probe(parent: Path) -> None:
    require(ANALYZER.is_file() and PROBE.is_file(), "artifact-backed analyzer/fact probe is unavailable")
    result = parent / "heldout"
    command = [
        sys.executable, str(ROOT / "tools/sprint12-role-property-heldout-smoke.py"),
        "--authority", str(AUTHORITY),
        "--analyzer", str(ANALYZER),
        "--schema", str(SCHEMA),
        "--provisional-corpus", str(CORPUS),
        "--fact-probe", str(PROBE),
        "--result-dir", str(result),
    ]
    cp = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        check=False, timeout=60.0)
    require(cp.returncode == 0, f"corrected held-out gate failed: {cp.stdout!r} {cp.stderr!r}")
    manifest = json.loads((result / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["fact_fields"] == list(load("p069_heldout", "tools/sprint12-role-property-heldout-smoke.py").FACT_FIELDS),
            "held-out manifest omitted fact fields")
    require(manifest["expected_vectors_retained"] is True
            and manifest["observed_vectors_retained"] is True
            and manifest["public_command_count"] == 384
            and manifest["provisional_target_count"] == 24,
            "held-out authority inputs or retained vectors are incomplete")
    header = (result / "facts.tsv").read_text(encoding="utf-8").splitlines()[0].split("\t")
    require(sum(name.startswith("expected_") for name in header) == 18
            and sum(name.startswith("observed_") for name in header) == 18,
            "facts.tsv does not retain all expected and observed fields")
    edge = [path for path in (result / "objects").iterdir() if path.name.startswith("metamorphic-edge-")]
    require(len(edge) == 24, "held-out edge-object count changed")

    missing = subprocess.run(command[:-4] + ["--provisional-corpus", str(parent / "missing"),
                                             "--fact-probe", str(PROBE)],
                             cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             check=False, timeout=20.0)
    require(missing.returncode != 0, "held-out gate accepted an absent provisional corpus")
    remove_owned_tree(result)


def make_dependency_probe() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    require("$(BUILD_DIR)/%.o: $(SRC_DIR)/%.asm $(wildcard $(INC_DIR)/*.inc)" in makefile,
            "production assembly objects omit include-file dependencies")
    require("--authority \"$(ROLE_PROPERTY_HELDOUT_AUTHORITY)\"" in makefile
            and "--schema \"$(ROLE_PROPERTY_PUBLIC_SCHEMA)\"" in makefile
            and "--provisional-corpus \"$(PROVISIONAL_CORPUS_PATH)\"" in makefile,
            "held-out Make target omits authenticated authorities")


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--signal-child":
        return signal_child(Path(sys.argv[2]))
    corpus = load("p069_corpus", "benchmarks/scripts/build-provisional-corpus.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p069-corrective-") as raw:
        root = Path(raw)
        retained_semantic_probe(corpus, root / "semantic")
        signal_probe(root / "signal")
        directory_size_probe(corpus, root / "root-size", ".")
        directory_size_probe(corpus, root / "nested-size", "inputs/source")
        heldout_authority_probe(root / "heldout-authority")
    leak_probe()
    make_dependency_probe()
    print(
        "patch068-corrective-regression-smoke: ok "
        "retained_semantics=1 signal_rollback=1 directory_size=2 "
        "authority_inputs=5 private_leaks=8 retained_vectors=36 edge_layouts=24 "
        "include_dependency=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RegressionError, subprocess.SubprocessError) as exc:
        print(f"patch068-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
