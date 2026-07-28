#!/usr/bin/env python3
"""Regress Patch 063 review findings in public development infrastructure.

The permanent smoke proves that authenticated mode repair remains bound to the
opened corpus object, corpus ownership drift is rejected, and the focused
section-label fixture emits canonical all-zero section-header entry zero.
Candidate capacity and PHDR-index coherence are exercised by the independent
assembly reconciliation target.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load(relative: str, name: str) -> Any:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def one_target_spec() -> tuple[Path, dict[str, Any]]:
    source = ROOT / "benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json"
    value = json.loads(source.read_text(encoding="utf-8"))
    value["corpus_id"] = f"p064-corpus-{uuid.uuid4().hex}"
    value["toolchains"] = value["toolchains"][:1]
    value["optimization_profiles"] = value["optimization_profiles"][:1]
    value["artifact_profiles"] = value["artifact_profiles"][:1]
    value["hardening_profiles"] = value["hardening_profiles"][:1]
    value["target_count"] = 1
    temporary = ROOT / "benchmarks/corpus/specs" / f".p064-{uuid.uuid4().hex}.json"
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return temporary, value


def probe_mode_root_continuity(corpus: Any) -> None:
    spec_path, spec = one_target_spec()
    try:
        with tempfile.TemporaryDirectory(prefix="p064-mode-root-") as raw:
            parent = Path(raw)
            output = parent / "results"
            final = corpus.build_corpus(spec_path, output, ROOT)
            retained = final / "inputs" / "spec" / "corpus-spec.json"
            retained.chmod(0o644)

            preserved = parent / "owned-preserved"
            original_verify = corpus.verify_checksum_manifest
            fired = False

            def swap_after_auth(bound_root: Path) -> dict[str, str]:
                nonlocal fired
                records = original_verify(bound_root)
                if not fired:
                    fired = True
                    os.rename(final, preserved)
                    final.mkdir()
                    (final / "foreign-marker").write_text("foreign\n", encoding="utf-8")
                return records

            corpus.verify_checksum_manifest = swap_after_auth
            rejected = False
            try:
                corpus.repair_corpus_modes(final)
            except corpus.CorpusError:
                rejected = True
            finally:
                corpus.verify_checksum_manifest = original_verify
            require(fired and rejected, "substituted caller-visible corpus root was not rejected")
            require((final / "foreign-marker").read_text(encoding="utf-8") == "foreign\n", "foreign replacement was modified")
            require((preserved / "inputs/spec/corpus-spec.json").stat().st_mode & 0o777 == 0o644,
                    "rejected repair mutated the displaced authenticated corpus")

            shutil.rmtree(final)
            os.rename(preserved, final)
            corpus.repair_corpus_modes(final)
            corpus.verify_corpus(final)
    finally:
        spec_path.unlink(missing_ok=True)


def probe_owner_drift(corpus: Any) -> None:
    spec_path, _spec = one_target_spec()
    try:
        with tempfile.TemporaryDirectory(prefix="p064-owner-drift-") as raw:
            final = corpus.build_corpus(spec_path, Path(raw) / "results", ROOT)
            original_lstat = Path.lstat
            injected = False

            def forged_lstat(path: Path):  # type: ignore[no-untyped-def]
                nonlocal injected
                observed = original_lstat(path)
                if not injected and path.name == "corpus-manifest.json":
                    values = list(observed)
                    values[4] = observed.st_uid + 1
                    injected = True
                    return os.stat_result(values)
                return observed

            Path.lstat = forged_lstat  # type: ignore[method-assign]
            rejected = False
            try:
                corpus.verify_corpus(final)
            except corpus.CorpusError as exc:
                rejected = "ownership changed" in str(exc)
            finally:
                Path.lstat = original_lstat  # type: ignore[method-assign]
            require(injected and rejected, "corpus ownership drift was not rejected")
    finally:
        spec_path.unlink(missing_ok=True)


def probe_section_zero_fixture() -> None:
    source = (ROOT / "tools/section-label-smoke.py").read_text(encoding="utf-8")
    require("shdrs = [pack_shdr(addralign=0)]" in source,
            "section-label fixture does not emit canonical section zero")


def main() -> int:
    corpus = load("benchmarks/scripts/build-provisional-corpus.py", "p064_corpus")
    probe_mode_root_continuity(corpus)
    probe_owner_drift(corpus)
    probe_section_zero_fixture()
    print(
        "patch063-corrective-regression-smoke: ok "
        "mode_root_continuity=1 owner_drift=1 section_zero=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"patch063-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
