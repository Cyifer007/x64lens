#!/usr/bin/env python3
"""Regress confirmed Patch 065 parser, corpus, harness, and oracle defects.

This gate remains standard-library only. Native GNU-property and public-output
behavior is owned by the focused Sprint 12 harnesses; this script makes the
review-found transaction and source-shape defects durable even on hosts without
NASM.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks/corpus/generated/s11-p056-provisional-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_corpus() -> Any:
    path = ROOT / "benchmarks/scripts/build-provisional-corpus.py"
    spec = importlib.util.spec_from_file_location("p066_corpus", path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def copy_corpus(parent: Path) -> Path:
    require(CORPUS.is_dir(), f"authenticated source corpus is missing: {CORPUS}")
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / CORPUS.name
    shutil.copytree(CORPUS, destination, copy_function=shutil.copy2)
    return destination


def validate_role_harness_shape(role_harness: str) -> None:
    """Require executable ABI instructions, not comment substrings."""

    start = role_harness.find("run_phdr:")
    end = role_harness.find("\nrun_role:", start)
    require(start >= 0 and end > start, "binary-role harness run_phdr block is missing")
    executable: list[str] = []
    for raw in role_harness[start:end].splitlines():
        code = raw.split(";", 1)[0].strip()
        if not code:
            continue
        executable.append(" ".join(code.split()))

    required_in_order = [
        "sub rsp, 8",
        "call assert_callee_entry_alignment",
        "test eax, eax",
        "call x64lens_phdr_analyze",
        ".return:",
        "add rsp, 8",
        "ret",
        "assert_callee_entry_alignment:",
        "cmp eax, 8",
        "mov eax, EXIT_BOUNDS",
    ]
    cursor = 0
    for token in required_in_order:
        try:
            index = executable.index(token, cursor)
        except ValueError as exc:
            raise RuntimeError(f"binary-role harness ABI instruction is missing: {token}") from exc
        cursor = index + 1


def source_shape_probe() -> None:
    gnu = (ROOT / "src/gnu_property.asm").read_text(encoding="utf-8")
    role_harness = (ROOT / "tests/internal/binary-role-reconciliation.asm").read_text(encoding="utf-8")
    oracle = (ROOT / "tools/sprint12-gnu-property-smoke.py").read_text(encoding="utf-8")

    require("sub     rdx, [rsp + 72]" in gnu and "add     rax, rdx" in gnu,
            "GNU property alignment is not descriptor-relative")
    require("jmp     .carrier_malformed" in gnu[gnu.index(".carrier_overlap_check:"):gnu.index(".carrier_find_next:")],
            "partially overlapping property carriers do not fail at registration")
    require("next_prop = desc_start + align(data_end - desc_start, 8)" in oracle,
            "independent GNU-property oracle repeats absolute-offset alignment")
    require("partially overlapping GNU-property carriers" in oracle,
            "independent GNU-property oracle omits partial-overlap rejection")
    validate_role_harness_shape(role_harness)


def copied_readonly_oracle_probe() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "tools/patch064-corrective-regression-smoke.py")],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    require(cp.returncode == 0,
            f"Patch 064 corrective oracle failed on its copied read-only corpus:\n{cp.stdout}\n{cp.stderr}")


def directory_substitution_probe(corpus: Any, root: Path) -> None:
    candidate = copy_corpus(root / "directory-substitution")
    drift = candidate / "commands.tsv"
    os.chmod(drift, 0o600)
    relative = PurePosixPath("inputs/source")
    victim = candidate / relative
    displaced = candidate / "inputs/source.displaced"
    original = corpus._verify_corpus_bound
    fired = False

    def substitute(bound_root: Path, expected_root_name: str, *, allow_mode_drift: bool = False):
        nonlocal fired
        result = original(bound_root, expected_root_name, allow_mode_drift=allow_mode_drift)
        if allow_mode_drift and not fired:
            fired = True
            os.rename(victim, displaced)
            victim.mkdir(mode=0o700)
            os.utime(victim, ns=(0, 0), follow_symlinks=False)
        return result

    corpus._verify_corpus_bound = substitute
    try:
        try:
            corpus.repair_corpus_modes(candidate)
        except corpus.CorpusError:
            pass
        else:
            raise RuntimeError("directory inode substitution was accepted by corpus mode repair")
    finally:
        corpus._verify_corpus_bound = original
    require(fired, "directory substitution probe did not fire")
    require(stat.S_IMODE(victim.stat().st_mode) == 0o700,
            "mode repair chmod changed a substituted foreign directory")
    require(stat.S_IMODE(drift.stat().st_mode) == 0o600,
            "mode repair mutated files after directory substitution")


def post_preflight_byte_mutation_probe(corpus: Any, root: Path) -> None:
    candidate = copy_corpus(root / "byte-mutation")
    relative = PurePosixPath("commands.tsv")
    victim = candidate / relative
    os.chmod(victim, 0o600)
    original_bytes = victim.read_bytes()
    require(original_bytes, "commands.tsv is empty")
    original = corpus._verify_corpus_bound
    fired = False

    def mutate(bound_root: Path, expected_root_name: str, *, allow_mode_drift: bool = False):
        nonlocal fired
        result = original(bound_root, expected_root_name, allow_mode_drift=allow_mode_drift)
        if allow_mode_drift and not fired:
            fired = True
            changed = bytearray(original_bytes)
            changed[0] ^= 1
            victim.write_bytes(changed)
            os.chmod(victim, 0o600)
            os.utime(victim, ns=(0, 0), follow_symlinks=False)
        return result

    corpus._verify_corpus_bound = mutate
    try:
        try:
            corpus.repair_corpus_modes(candidate)
        except corpus.CorpusError:
            pass
        else:
            raise RuntimeError("post-preflight corpus byte mutation was accepted")
    finally:
        corpus._verify_corpus_bound = original
    require(fired, "post-preflight byte mutation probe did not fire")
    require(stat.S_IMODE(victim.stat().st_mode) == 0o600,
            "mode repair mutated a post-preflight-changed file")


def main() -> int:
    source_shape_probe()
    copied_readonly_oracle_probe()
    corpus = load_corpus()
    with tempfile.TemporaryDirectory(prefix="x64lens-p066-corrective-") as raw:
        root = Path(raw)
        directory_substitution_probe(corpus, root)
        post_preflight_byte_mutation_probe(corpus, root)
    print(
        "patch065-corrective-regression-smoke: ok "
        "readonly_fixture=1 descriptor_alignment=1 partial_overlap=1 abi_alignment=1 "
        "directory_identity=1 post_preflight_bytes=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"patch065-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
