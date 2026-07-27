#!/usr/bin/env python3
"""Regress confirmed Patch 066 transaction, oracle, and ABI findings.

The gate is standard-library only. It proves that corpus mode repair rechecks
exact membership and caller-visible root identity before mutation, rolls back
mode changes after a late verifier failure, rejects actual private fact keys in
public JSON, and rejects removal of both binary-role stack adjustments.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks/corpus/generated/s11-p056-provisional-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_module(name: str, relative: str) -> Any:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
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


def membership_before_mutation_probe(corpus: Any, root: Path) -> None:
    candidate = copy_corpus(root / "membership")
    drift = candidate / "commands.tsv"
    os.chmod(drift, 0o600)
    addition = candidate / "late-member.txt"
    original = corpus._verify_corpus_bound
    fired = False

    def add_member(bound_root: Path, expected_root_name: str, *, allow_mode_drift: bool = False):
        nonlocal fired
        result = original(bound_root, expected_root_name, allow_mode_drift=allow_mode_drift)
        if allow_mode_drift and not fired:
            fired = True
            addition.write_text("foreign\n", encoding="utf-8")
            os.chmod(addition, 0o600)
            os.utime(addition, ns=(0, 0), follow_symlinks=False)
        return result

    corpus._verify_corpus_bound = add_member
    try:
        try:
            corpus.repair_corpus_modes(candidate)
        except corpus.CorpusError:
            pass
        else:
            raise RuntimeError("post-preflight corpus member addition was accepted")
    finally:
        corpus._verify_corpus_bound = original
    require(fired, "membership probe did not fire")
    require(stat.S_IMODE(drift.stat().st_mode) == 0o600,
            "mode repair changed an authenticated member before rejecting membership drift")
    require(stat.S_IMODE(addition.stat().st_mode) == 0o600,
            "mode repair changed an undeclared late member")


def root_binding_probe(corpus: Any, root: Path) -> None:
    parent = root / "root-binding"
    candidate = copy_corpus(parent)
    drift = candidate / "commands.tsv"
    os.chmod(drift, 0o600)
    displaced = parent / f"{candidate.name}.displaced"
    original = corpus._verify_corpus_bound
    fired = False

    def replace_root(bound_root: Path, expected_root_name: str, *, allow_mode_drift: bool = False):
        nonlocal fired
        result = original(bound_root, expected_root_name, allow_mode_drift=allow_mode_drift)
        if allow_mode_drift and not fired:
            fired = True
            os.rename(candidate, displaced)
            candidate.mkdir(mode=0o700)
            os.utime(candidate, ns=(0, 0), follow_symlinks=False)
        return result

    corpus._verify_corpus_bound = replace_root
    try:
        try:
            corpus.repair_corpus_modes(candidate)
        except corpus.CorpusError:
            pass
        else:
            raise RuntimeError("caller-visible corpus root substitution was accepted")
    finally:
        corpus._verify_corpus_bound = original
    require(fired, "root-binding probe did not fire")
    require(stat.S_IMODE((displaced / "commands.tsv").stat().st_mode) == 0o600,
            "mode repair changed the displaced authenticated corpus")
    require(stat.S_IMODE(candidate.stat().st_mode) == 0o700,
            "mode repair changed the foreign replacement root")


def mode_rollback_probe(corpus: Any, root: Path) -> None:
    candidate = copy_corpus(root / "rollback")
    drift = candidate / "commands.tsv"
    original_root_mode = stat.S_IMODE(candidate.stat().st_mode)
    os.chmod(drift, 0o600)
    original = corpus._verify_corpus_bound
    calls = 0

    def fail_final(bound_root: Path, expected_root_name: str, *, allow_mode_drift: bool = False):
        nonlocal calls
        calls += 1
        if calls >= 2 and not allow_mode_drift:
            raise corpus.CorpusError("injected final verifier failure")
        return original(bound_root, expected_root_name, allow_mode_drift=allow_mode_drift)

    corpus._verify_corpus_bound = fail_final
    try:
        try:
            corpus.repair_corpus_modes(candidate)
        except corpus.CorpusError:
            pass
        else:
            raise RuntimeError("injected late verifier failure was accepted")
    finally:
        corpus._verify_corpus_bound = original
    require(calls >= 2, "mode rollback probe did not reach final verification")
    require(stat.S_IMODE(drift.stat().st_mode) == 0o600,
            "late failure did not restore the original file mode")
    require(stat.S_IMODE(candidate.stat().st_mode) == original_root_mode,
            "late failure did not restore the original root mode")


def private_field_oracle_probe() -> None:
    module = load_module(
        "p067_metamorphic",
        "tools/sprint12-role-property-metamorphic-smoke.py",
    )
    for value in (
        {"role_state": 1},
        {"nested": [{"ibt_state": 2}]},
        {"property_feature_count": 1},
        {"gnu_property_private": True},
    ):
        try:
            module.assert_no_private_public_fields(value)
        except RuntimeError:
            continue
        raise RuntimeError(f"private-field oracle accepted leaked state: {value!r}")
    module.assert_no_private_public_fields(
        {"mitigations": {"pie": True}, "primitive_coverage": {"arg_control": False}}
    )


def abi_oracle_probe() -> None:
    module = load_module(
        "p067_patch065",
        "tools/patch065-corrective-regression-smoke.py",
    )
    source = (ROOT / "tests/internal/binary-role-reconciliation.asm").read_text(encoding="utf-8")
    module.validate_role_harness_shape(source)
    mutated = source.replace("    sub     rsp, 8\n", "", 1)
    mutated = mutated.replace("    add     rsp, 8\n", "", 1)
    try:
        module.validate_role_harness_shape(mutated)
    except RuntimeError:
        return
    raise RuntimeError("binary-role ABI oracle accepted removal of both stack adjustments")


def layout_authority_probe() -> None:
    authority = (ROOT / "tests/internal/role-property-layout-authority.asm").read_text(encoding="utf-8")
    header = (ROOT / "tests/internal/role-property-layout.h").read_text(encoding="utf-8")
    probe = (ROOT / "tests/internal/role-property-fact-probe.c").read_text(encoding="utf-8")
    require("%include \"structs.inc\"" in authority and
            "x64lens_role_property_layout_descriptor" in authority,
            "NASM private-layout authority is missing")
    require("X64LENS_ROLE_PROPERTY_LAYOUT_FIELD_COUNT UINT64_C(21)" in header and
            "x64lens_role_property_layout_validate" in header,
            "independent C private-layout contract is missing")
    require("x64lens_role_property_layout_validate" in probe and
            "PHDR_SUMMARY_RECORD_SIZE = 264" not in probe,
            "fact probe still hardcodes assembly-owned private layout")


def main() -> int:
    corpus = load_module("p067_corpus", "benchmarks/scripts/build-provisional-corpus.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p067-corrective-") as raw:
        root = Path(raw)
        membership_before_mutation_probe(corpus, root)
        root_binding_probe(corpus, root)
        mode_rollback_probe(corpus, root)
    private_field_oracle_probe()
    abi_oracle_probe()
    layout_authority_probe()
    print(
        "patch066-corrective-regression-smoke: ok "
        "membership=1 root_binding=1 mode_rollback=1 private_fields=4 "
        "abi_mutation=1 layout_authority=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"patch066-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
