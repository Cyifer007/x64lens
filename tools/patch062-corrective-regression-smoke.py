#!/usr/bin/env python3
"""Regress Patch 062 review findings in tracked development infrastructure.

The smoke proves four boundaries that were absent from the Patch 062 oracles:

* invalid runner specifications release every retained descriptor;
* final cleanup preserves a foreign file or directory substituted at the atomic
  removal boundary;
* corpus construction remains rooted in the authenticated output directory even
  when the caller-visible pathname is replaced; and
* permission normalization and aggregate corpus readiness remain self-contained.

The private orchestration manager has an equivalent package-local smoke and is
not imported into the public repository validation path.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
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


def probe_runner_fd_lifetime(runner: Any) -> None:
    with tempfile.TemporaryDirectory(prefix="p063-runner-fd-") as raw:
        root = Path(raw)
        bad = root / "bad.json"
        bad.write_text("{}\n", encoding="utf-8")
        before = len(list(Path("/proc/self/fd").iterdir()))
        failures = 0
        for _ in range(20):
            try:
                runner.run_campaign(bad, root / "results", None)
            except runner.RunnerError:
                failures += 1
        after = len(list(Path("/proc/self/fd").iterdir()))
        require(failures == 20, "invalid runner specifications did not all fail")
        require(after == before, f"invalid runner specifications leaked {after - before} descriptors")


def probe_directory_cleanup(module: Any, label: str) -> None:
    with tempfile.TemporaryDirectory(prefix=f"p063-{label}-cleanup-") as raw:
        parent = Path(raw)
        target = parent / "target"
        target.mkdir()
        owned = target.stat()
        parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        original = module._rename_noreplace_between
        fired = False

        def interpose(source_fd: int, source: str, destination_fd: int, destination: str, operation: str) -> None:
            nonlocal fired
            if not fired and source == "target":
                fired = True
                os.rename("target", "target.owned-preserved", src_dir_fd=source_fd, dst_dir_fd=source_fd)
                os.mkdir("target", 0o700, dir_fd=source_fd)
            original(source_fd, source, destination_fd, destination, operation)

        module._rename_noreplace_between = interpose
        rejected = False
        try:
            try:
                module._unlinkat_directory(parent_fd, "target", "probe directory", (owned.st_dev, owned.st_ino))
            except (module.RunnerError if label == "runner" else module.CorpusError):
                rejected = True
        finally:
            module._rename_noreplace_between = original
            os.close(parent_fd)
        require(fired and rejected, f"{label}: cleanup substitution was not rejected")
        require(target.is_dir(), f"{label}: foreign directory was removed")
        require((parent / "target.owned-preserved").is_dir(), f"{label}: owned directory was lost")


def probe_artifact_cleanup(artifact: Any) -> None:
    with tempfile.TemporaryDirectory(prefix="p063-artifact-cleanup-") as raw:
        parent = Path(raw)
        target = parent / "target"
        target.write_bytes(b"owned")
        owned = target.stat()
        parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
        original = artifact._renameat2
        fired = False

        def interpose(directory_fd: int, source: str, destination: str) -> None:
            nonlocal fired
            if not fired and source == "target":
                fired = True
                os.rename("target", "target.owned-preserved", src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
                descriptor = os.open(
                    "target",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                    dir_fd=directory_fd,
                )
                try:
                    os.write(descriptor, b"foreign")
                finally:
                    os.close(descriptor)
            original(directory_fd, source, destination)

        artifact._renameat2 = interpose
        rejected = False
        try:
            try:
                artifact._unlinkat_regular(parent_fd, "target", "probe file", (owned.st_dev, owned.st_ino))
            except artifact.ArtifactError:
                rejected = True
        finally:
            artifact._renameat2 = original
            os.close(parent_fd)
        require(fired and rejected, "artifact cleanup substitution was not rejected")
        require(target.read_bytes() == b"foreign", "artifact foreign replacement was removed")
        require((parent / "target.owned-preserved").read_bytes() == b"owned", "artifact owned file was lost")


def one_target_spec() -> tuple[Path, dict[str, Any]]:
    source = ROOT / "benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json"
    value = json.loads(source.read_text(encoding="utf-8"))
    value["corpus_id"] = f"p063-output-root-{uuid.uuid4().hex}"
    value["toolchains"] = value["toolchains"][:1]
    value["optimization_profiles"] = value["optimization_profiles"][:1]
    value["artifact_profiles"] = value["artifact_profiles"][:1]
    value["hardening_profiles"] = value["hardening_profiles"][:1]
    value["target_count"] = 1
    temporary = ROOT / "benchmarks/corpus/specs" / f".p063-{uuid.uuid4().hex}.json"
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return temporary, value


def probe_corpus_output_root(corpus: Any) -> None:
    spec_path, spec = one_target_spec()
    try:
        with tempfile.TemporaryDirectory(prefix="p063-output-root-") as raw:
            base = Path(raw)
            visible = base / "results"
            preserved = base / "authenticated-root"
            original = corpus.OwnedStage.create
            fired = False

            def swap_then_create(parent: Path, name: str, registry: list[Any] | None = None) -> Any:
                nonlocal fired
                if not fired:
                    fired = True
                    os.rename(visible, preserved)
                    visible.mkdir()
                return original(parent, name, registry)

            corpus.OwnedStage.create = swap_then_create
            try:
                final = corpus.build_corpus(spec_path, visible, ROOT)
            finally:
                corpus.OwnedStage.create = original
            require(fired, "corpus output-root substitution probe did not fire")
            require(final == preserved / spec["corpus_id"], "corpus returned a path outside the authenticated root")
            require(final.is_dir(), "corpus was not published in the authenticated root")
            require(not any(visible.iterdir()), "foreign replacement output root received corpus members")
            corpus.verify_corpus(final)
            retained_spec = final / "inputs" / "spec" / "corpus-spec.json"
            retained_spec.chmod(0o644)
            try:
                corpus.verify_corpus(final)
            except corpus.CorpusError:
                pass
            else:
                raise RuntimeError("mode-drifted corpus was accepted before repair")
            corpus.repair_corpus_modes(final)
            corpus.verify_corpus(final)
    finally:
        spec_path.unlink(missing_ok=True)


def probe_make_contracts() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    require("sprint11-p060-campaign-smoke: provisional-corpus-ready all" in makefile,
            "controlled campaign does not consume the self-contained corpus-ready target")
    require("provisional-corpus-repair-modes" in makefile,
            "authenticated mode-only corpus recovery target is missing")
    require("normalize-tracked-permissions.py --repo ." in makefile,
            "permission normalization is not restricted to authenticated Git-tracked paths")

    probe_root = ROOT / "benchmarks/corpus/generated" / f".p063-mode-{uuid.uuid4().hex}"
    probe_root.mkdir(parents=True)
    probe = probe_root / "retained-input"
    probe.write_bytes(b"mode probe\n")
    probe.chmod(0o444)
    try:
        subprocess.run(["make", "--no-print-directory", "normalize-perms"], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        require(stat.S_IMODE(probe.stat().st_mode) == 0o444,
                "normalize-perms changed an authenticated generated-corpus mode")
    finally:
        shutil.rmtree(probe_root, ignore_errors=True)


def main() -> int:
    runner = load("benchmarks/scripts/diagnostic-runner.py", "p063_runner")
    corpus = load("benchmarks/scripts/build-provisional-corpus.py", "p063_corpus")
    artifact = load("benchmarks/scripts/diagnostic_artifact.py", "p063_artifact")

    probe_runner_fd_lifetime(runner)
    probe_directory_cleanup(runner, "runner")
    probe_directory_cleanup(corpus, "corpus")
    probe_artifact_cleanup(artifact)
    probe_corpus_output_root(corpus)
    probe_make_contracts()

    print(
        "patch062-corrective-regression-smoke: ok "
        "fd_lifetime=20 cleanup_cas=3 output_root_continuity=1 mode_repair=1 "
        "aggregate_readiness=1 authenticated_modes=1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
