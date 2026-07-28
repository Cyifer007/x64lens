#!/usr/bin/env python3
"""Regress confirmed Patch 067 corpus, Make, and ABI-oracle defects."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
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
    destination = parent / CORPUS.name
    shutil.copytree(CORPUS, destination, copy_function=shutil.copy2)
    return destination


def mode_map(root: Path) -> dict[str, int]:
    return {".": stat.S_IMODE(root.stat().st_mode)} | {
        path.relative_to(root).as_posix(): stat.S_IMODE(path.lstat().st_mode)
        for path in sorted(root.rglob("*"))
    }


def first_fchmod_membership_probe(corpus: Any, parent: Path) -> None:
    candidate = copy_corpus(parent)
    drift = candidate / "commands.tsv"
    drift.chmod(0o600)
    before = mode_map(candidate)
    original = corpus.os.fchmod
    fired = False

    def inject(fd: int, mode: int) -> None:
        nonlocal fired
        result = original(fd, mode)
        if not fired:
            fired = True
            (candidate / "late-member").write_text("foreign\n", encoding="utf-8")
        return result

    corpus.os.fchmod = inject
    rejected = False
    try:
        corpus.repair_corpus_modes(candidate)
    except corpus.CorpusError:
        rejected = True
    finally:
        corpus.os.fchmod = original
    require(fired and rejected, "first-fchmod member insertion was accepted")
    after = mode_map(candidate)
    after.pop("late-member", None)
    require(after == before, "first-fchmod rejection changed an authenticated mode")


def ancestor_chain_probe(corpus: Any, parent: Path) -> None:
    visible = parent / "visible"
    nested = visible / "nested"
    nested.mkdir(parents=True)
    candidate = copy_corpus(nested)
    drift = candidate / "commands.tsv"
    drift.chmod(0o600)
    before = mode_map(candidate)
    displaced = parent / "displaced"
    original = corpus._verify_corpus_bound
    fired = False

    def substitute(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal fired
        result = original(*args, **kwargs)
        if not fired:
            fired = True
            os.rename(visible, displaced)
            foreign = visible / "nested" / candidate.name
            foreign.mkdir(parents=True)
            (foreign / "foreign-marker").write_text("foreign\n", encoding="utf-8")
        return result

    corpus._verify_corpus_bound = substitute
    rejected = False
    try:
        corpus.repair_corpus_modes(candidate)
    except corpus.CorpusError:
        rejected = True
    finally:
        corpus._verify_corpus_bound = original
    require(fired and rejected, "caller-visible ancestor substitution was accepted")
    owned = displaced / "nested" / candidate.name
    require(mode_map(owned) == before, "displaced authenticated corpus was mutated")
    require((visible / "nested" / candidate.name / "foreign-marker").read_text() == "foreign\n",
            "foreign caller-visible replacement was modified")


def rollback_retry_probe(corpus: Any, parent: Path) -> None:
    candidate = copy_corpus(parent)
    drift = candidate / "commands.tsv"
    drift.chmod(0o600)
    before = mode_map(candidate)
    original_fchmod = corpus.os.fchmod
    original_verify = corpus._verify_corpus_bound
    injected_verify = False
    rollback_failed_once = False
    target_inode = drift.stat().st_ino

    def fail_late(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal injected_verify
        result = original_verify(*args, **kwargs)
        if not kwargs.get("allow_mode_drift") and not injected_verify:
            injected_verify = True
            raise corpus.CorpusError("injected post-mutation verifier failure")
        return result

    def transient_rollback_error(fd: int, mode: int) -> None:
        nonlocal rollback_failed_once
        metadata = os.fstat(fd)
        if injected_verify and metadata.st_ino == target_inode and mode == 0o600 and not rollback_failed_once:
            rollback_failed_once = True
            raise OSError(5, "injected transient rollback failure")
        return original_fchmod(fd, mode)

    corpus._verify_corpus_bound = fail_late
    corpus.os.fchmod = transient_rollback_error
    rejected = False
    try:
        corpus.repair_corpus_modes(candidate)
    except corpus.CorpusError as exc:
        rejected = "injected post-mutation" in str(exc)
    finally:
        corpus._verify_corpus_bound = original_verify
        corpus.os.fchmod = original_fchmod
    require(injected_verify and rollback_failed_once and rejected,
            "late failure or rollback retry probe did not execute")
    require(mode_map(candidate) == before, "rollback retry did not restore every original mode")


def stale_patch063_probe() -> None:
    cp = subprocess.run(
        [sys.executable, str(ROOT / "tools/patch063-corrective-regression-smoke.py")],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    require(cp.returncode == 0,
            f"updated Patch 063 corrective oracle failed:\n{cp.stdout}\n{cp.stderr}")


def make_dependency_probe() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    line = next(
        (value for value in makefile.splitlines()
         if value.startswith("$(ROLE_PROPERTY_LAYOUT_AUTHORITY_OBJ):")),
        "",
    )
    require("include/structs.inc" in line,
            "layout-authority object omits include/structs.inc prerequisite")


def abi_comment_probe() -> None:
    module = load("p068_patch065", "tools/patch065-corrective-regression-smoke.py")
    source = (ROOT / "tests/internal/binary-role-reconciliation.asm").read_text(encoding="utf-8")
    module.validate_role_harness_shape(source)
    mutant = source.replace("    sub     rsp, 8\n", "    ; sub     rsp, 8\n", 1)
    mutant = mutant.replace("    add     rsp, 8\n", "    ; add     rsp, 8\n", 1)
    try:
        module.validate_role_harness_shape(mutant)
    except RuntimeError:
        return
    raise RegressionError("ABI oracle accepted comment-only stack-adjustment tokens")


def main() -> int:
    corpus = load("p068_corpus", "benchmarks/scripts/build-provisional-corpus.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p068-corrective-") as raw:
        root = Path(raw)
        first_fchmod_membership_probe(corpus, root / "first-fchmod")
        ancestor_chain_probe(corpus, root / "ancestor")
        rollback_retry_probe(corpus, root / "rollback")
    stale_patch063_probe()
    make_dependency_probe()
    abi_comment_probe()
    print(
        "patch067-corrective-regression-smoke: ok "
        "first_fchmod=1 ancestor_chain=1 rollback_retry=1 stale_oracle=1 "
        "make_dependency=1 abi_comments=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RegressionError, subprocess.SubprocessError) as exc:
        print(f"patch067-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
