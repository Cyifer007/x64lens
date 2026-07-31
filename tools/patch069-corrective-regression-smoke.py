#!/usr/bin/env python3
"""Regress Patch 069 corpus, authority, comparator, cleanup, and Make defects."""
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


def copy_corpus(parent: Path) -> Path:
    require(CORPUS.is_dir(), f"authenticated corpus is missing: {CORPUS}")
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / CORPUS.name
    shutil.copytree(CORPUS, target, copy_function=shutil.copy2)
    return target


def mode_map(root: Path) -> dict[str, int]:
    return {".": stat.S_IMODE(root.stat().st_mode)} | {
        item.relative_to(root).as_posix(): stat.S_IMODE(item.lstat().st_mode)
        for item in sorted(root.rglob("*"))
    }


def invalid_equal_length_semantics(candidate: Path) -> tuple[bytes, bytes]:
    manifest_path = candidate / "corpus-manifest.json"
    sums_path = candidate / "SHA256SUMS.txt"
    valid_manifest = manifest_path.read_bytes()
    valid_sums = sums_path.read_bytes()
    invalid_manifest = valid_manifest.replace(b'"evidence_class": "diagnostic"', b'"evidence_class": "invalidxxx"')
    require(len(invalid_manifest) == len(valid_manifest) and invalid_manifest != valid_manifest,
            "equal-length semantic mutation failed")
    old_digest = hashlib.sha256(valid_manifest).hexdigest().encode()
    new_digest = hashlib.sha256(invalid_manifest).hexdigest().encode()
    invalid_sums = valid_sums.replace(old_digest + b"  corpus-manifest.json",
                                      new_digest + b"  corpus-manifest.json")
    require(len(invalid_sums) == len(valid_sums) and invalid_sums != valid_sums,
            "equal-length checksum mutation failed")
    for path, payload in ((manifest_path, invalid_manifest), (sums_path, invalid_sums)):
        path.chmod(0o644)
        path.write_bytes(payload)
        path.chmod(0o444)
        os.utime(path, ns=(0, 0))
    os.utime(candidate, ns=(0, 0))
    return valid_manifest, valid_sums


def retained_semantic_probe(corpus: Any, parent: Path) -> None:
    candidate = copy_corpus(parent)
    valid_manifest, valid_sums = invalid_equal_length_semantics(candidate)
    (candidate / "commands.tsv").chmod(0o600)
    before = mode_map(candidate)
    original = corpus.verify_retained_corpus_snapshot
    swaps = 0

    def transient(opened, expected_root_name, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal swaps
        manifest = candidate / "corpus-manifest.json"
        sums = candidate / "SHA256SUMS.txt"
        invalid_manifest = manifest.read_bytes()
        invalid_sums = sums.read_bytes()
        manifest.chmod(0o644); sums.chmod(0o644)
        manifest.write_bytes(valid_manifest); sums.write_bytes(valid_sums)
        manifest.chmod(0o444); sums.chmod(0o444)
        os.utime(manifest, ns=(0, 0)); os.utime(sums, ns=(0, 0)); os.utime(candidate, ns=(0, 0))
        swaps += 1
        try:
            return original(opened, expected_root_name, **kwargs)
        finally:
            manifest.chmod(0o644); sums.chmod(0o644)
            manifest.write_bytes(invalid_manifest); sums.write_bytes(invalid_sums)
            manifest.chmod(0o444); sums.chmod(0o444)
            os.utime(manifest, ns=(0, 0)); os.utime(sums, ns=(0, 0)); os.utime(candidate, ns=(0, 0))

    corpus.verify_retained_corpus_snapshot = transient
    rejected = False
    try:
        corpus.repair_corpus_modes(candidate)
    except corpus.CorpusError:
        rejected = True
    finally:
        corpus.verify_retained_corpus_snapshot = original
    require(swaps >= 1 and rejected, "equal-length transient retained semantics were accepted")
    require(mode_map(candidate) == before, "semantic rejection changed corpus modes")
    require(b'"evidence_class": "invalidxxx"' in (candidate / "corpus-manifest.json").read_bytes(),
            "invalid visible semantics were not preserved")


def post_mutation_root_size_probe(corpus: Any, parent: Path) -> None:
    candidate = copy_corpus(parent)
    (candidate / "commands.tsv").chmod(0o600)
    before = mode_map(candidate)
    original = corpus.os.fchmod
    fired = False

    def churn(fd: int, mode: int) -> None:
        nonlocal fired
        old_mode = stat.S_IMODE(os.fstat(fd).st_mode)
        original(fd, mode)
        if not fired and old_mode != mode:
            fired = True
            for index in range(128):
                (candidate / f".p070-root-churn-{index:03d}").write_bytes(b"x")
            for index in range(128):
                (candidate / f".p070-root-churn-{index:03d}").unlink()
            os.utime(candidate, ns=(0, 0))

    corpus.os.fchmod = churn
    rejected = False
    try:
        corpus.repair_corpus_modes(candidate)
    except corpus.CorpusError:
        rejected = True
    finally:
        corpus.os.fchmod = original
    require(fired and rejected, "post-mutation root directory churn was accepted")
    require(mode_map(candidate) == before, "root-size rejection did not restore all modes")


def transient_root_probe(corpus: Any, parent: Path) -> None:
    candidate = copy_corpus(parent)
    (candidate / "commands.tsv").chmod(0o600)
    before = mode_map(candidate)
    original = corpus.verify_retained_corpus_snapshot
    fired = False

    def replace_and_restore(opened, expected_root_name, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal fired
        result = original(opened, expected_root_name, **kwargs)
        if not fired:
            fired = True
            displaced = candidate.with_name(candidate.name + ".displaced")
            os.rename(candidate, displaced)
            candidate.mkdir()
            candidate.rmdir()
            os.rename(displaced, candidate)
        return result

    corpus.verify_retained_corpus_snapshot = replace_and_restore
    rejected = False
    try:
        corpus.repair_corpus_modes(candidate)
    except corpus.CorpusError:
        rejected = True
    finally:
        corpus.verify_retained_corpus_snapshot = original
    require(fired and rejected, "transient caller-visible root replacement was accepted")
    require(mode_map(candidate) == before, "root replacement rejection changed corpus modes")


def early_open_handler_probe(corpus: Any, parent: Path) -> None:
    def sentinel(_signum: int, _frame: object) -> None:
        return None
    old_int = signal.signal(signal.SIGINT, sentinel)
    old_term = signal.signal(signal.SIGTERM, sentinel)
    try:
        rejected = False
        try:
            corpus.repair_corpus_modes(parent / "missing-corpus")
        except (corpus.CorpusError, OSError):
            rejected = True
        require(rejected, "missing root did not fail")
        require(signal.getsignal(signal.SIGINT) is sentinel and signal.getsignal(signal.SIGTERM) is sentinel,
                "early root-open failure leaked signal handlers")
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)


def cleanup_probe(parent: Path) -> None:
    helper = ROOT / "tools/remove-owned-tree.py"
    owned = parent / "sealed"
    owned.mkdir(parents=True)
    (owned / "value").write_text("sealed\n")
    (owned / "value").chmod(0o444)
    owned.chmod(0o555)
    ident = subprocess.run([sys.executable, str(helper), "--identify", str(owned)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=5.0)
    require(ident.returncode == 0, f"cleanup identity failed: {ident.stderr!r}")
    identity = ident.stdout.decode().strip()
    removed = subprocess.run([sys.executable, str(helper), "--remove", str(owned), "--identity", identity],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10.0)
    require(removed.returncode == 0 and not owned.exists(), f"sealed cleanup failed: {removed.stderr!r}")

    owned.mkdir()
    (owned / "value").write_text("owned\n")
    ident = subprocess.run([sys.executable, str(helper), "--identify", str(owned)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=5.0)
    identity = ident.stdout.decode().strip()
    displaced = owned.with_name("displaced")
    os.rename(owned, displaced)
    owned.mkdir()
    (owned / "foreign").write_text("foreign\n")
    rejected = subprocess.run([sys.executable, str(helper), "--remove", str(owned), "--identity", identity],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10.0)
    require(rejected.returncode != 0 and (owned / "foreign").read_text() == "foreign\n",
            "cleanup removed a foreign replacement")
    shutil.rmtree(owned)
    shutil.rmtree(displaced)


def make_prerequisite_probe() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    require(
        "patch068-corrective-regression-smoke: corpus-tools-check provisional-corpus-ready all $(ROLE_PROPERTY_FACT_PROBE_BIN)" in makefile,
        "Patch 068 corrective target omits analyzer, fact-probe, or corpus prerequisites",
    )
    require("tools/remove-owned-tree.py --remove" in makefile,
            "readelf target still uses unowned recursive cleanup")


def leak_probe() -> None:
    module = load("p070_leak", "tools/sprint12-role-property-metamorphic-smoke.py")
    commands = ("info", "mitigations", "gadgets", "analyze")
    for command_id in commands:
        for channel in ("stdout", "stderr"):
            original = module.run
            def synthetic(command, *, expected=0, command_id=command_id, channel=channel):  # type: ignore[no-untyped-def]
                del expected
                current = command[1]
                is_json = "--format" in command
                stdout = (json.dumps({"schema_version": "0.2.0", "command": current}).encode()
                          if is_json else b"public output\n")
                stderr = b""
                if current == command_id:
                    if channel == "stderr":
                        stderr = b"gnu-property private state\n"
                    elif is_json:
                        stdout = json.dumps({"schema_version": "0.2.0", "command": current,
                                             "x64lensGnuProperty": 1}).encode()
                    else:
                        stdout = b"x64lensGnuProperty=1\n"
                return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=stderr)
            module.run = synthetic
            rejected = False
            try:
                module.validate_public(Path("synthetic-analyzer"), Path("synthetic-target"))
            except RuntimeError:
                rejected = True
            finally:
                module.run = original
            require(rejected, f"private leak accepted: command={command_id} channel={channel}")


def authority_and_overlap_probe(parent: Path) -> None:
    parent.mkdir(parents=True, exist_ok=True)
    heldout = load("p070_heldout", "tools/sprint12-role-property-heldout-smoke.py")
    readelf = load("p070_readelf", "tools/sprint12-role-property-readelf-smoke.py")

    original_heldout = json.loads((ROOT / "benchmarks/task-definitions/sprint12-role-property-heldout-v1.json").read_text())
    minimal = dict(original_heldout)
    minimal["natural_stratum"] = {"object_count": 48}
    path = parent / "minimal-heldout.json"
    path.write_text(json.dumps(minimal))
    rejected = False
    try:
        heldout.load_authority(path)
    except RuntimeError:
        rejected = True
    require(rejected, "semantically incomplete held-out authority was accepted")

    original_readelf = json.loads((ROOT / "benchmarks/task-definitions/sprint12-role-property-readelf-v1.json").read_text())
    unavailable = json.loads(json.dumps(original_readelf))
    for field in unavailable["field_eligibility"]:
        unavailable["field_eligibility"][field] = {"class": "unavailable", "reason": "mutation"}
    path = parent / "all-unavailable-readelf.json"
    path.write_text(json.dumps(unavailable))
    rejected = False
    try:
        readelf.load_authority(path)
    except RuntimeError:
        rejected = True
    require(rejected, "all-unavailable readelf authority was accepted")

    source = (ROOT / "tools/sprint12-role-property-readelf-smoke.py").read_text()
    require('require(record["exit_code"] == 0' in source,
            "readelf comparator exits are not required to succeed")

    edge_root = parent / "edges"
    edge_root.mkdir()
    objects = heldout.metamorphic_objects(edge_root)
    positives = 0
    for name, blob, _metadata in objects:
        vector = heldout.independent_vector(blob)
        if vector["property_overlap_count"] > 0:
            positives += 1
            require(name == "metamorphic-edge-bad-feature-width-v3.elf",
                    f"unexpected positive overlap anchor: {name}")
    require(positives == 1, f"positive overlap anchor count is {positives}, expected one")


def main() -> int:
    corpus = load("p070_corpus", "benchmarks/scripts/build-provisional-corpus.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p070-corrective-") as raw:
        root = Path(raw)
        retained_semantic_probe(corpus, root / "semantic")
        post_mutation_root_size_probe(corpus, root / "root-size")
        transient_root_probe(corpus, root / "root-replacement")
        early_open_handler_probe(corpus, root / "handlers")
        cleanup_probe(root / "cleanup")
        authority_and_overlap_probe(root / "authority")
    make_prerequisite_probe()
    leak_probe()
    print(
        "patch069-corrective-regression-smoke: ok "
        "retained_semantics=1 root_size=1 root_replacement=1 handlers=1 cleanup=2 "
        "make_prerequisites=4 private_leaks=8 authorities=2 readelf_exits=1 overlap_anchor=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"patch069-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
