#!/usr/bin/env python3
"""Permanent regressions for confirmed Patch 061 evidence-integrity defects."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def owned_cleanup_substitution(module: ModuleType, label: str) -> None:
    original = module._unlinkat_directory
    with tempfile.TemporaryDirectory(prefix=f"p062-{label}-") as temporary:
        parent = Path(temporary)
        owned = module.OwnedStage.create(parent, "stage")
        owned_identity = (owned.device, owned.inode)
        fired = False

        def swap_then_remove(parent_fd: int, name: str, remove_label: str, expected: tuple[int, int]) -> None:
            nonlocal fired
            if not fired and name == "stage":
                fired = True
                os.rename("stage", "owned-preserved", src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                os.mkdir("stage", 0o700, dir_fd=parent_fd)
            original(parent_fd, name, remove_label, expected)

        module._unlinkat_directory = swap_then_remove
        rejected = False
        try:
            try:
                owned.cleanup(f"{label} cleanup")
            except module.RunnerError if label == "runner" else module.CorpusError:
                rejected = True
        finally:
            module._unlinkat_directory = original

        foreign = parent / "stage"
        preserved = parent / "owned-preserved"
        require(fired and rejected, f"{label}: substituted cleanup was not rejected")
        require(foreign.is_dir(), f"{label}: foreign replacement was removed")
        metadata = preserved.stat()
        require((metadata.st_dev, metadata.st_ino) == owned_identity, f"{label}: owned directory was not preserved")
        foreign.rmdir()
        preserved.rename(parent / "stage")
        owned.cleanup(f"{label} cleanup recovery")
        owned.close()


def runner_spec_continuity(runner: ModuleType) -> None:
    with tempfile.TemporaryDirectory(prefix="p062-spec-") as temporary:
        root = Path(temporary)
        source = ROOT / "benchmarks/specs/sprint11-reference-diagnostic.json"
        original = root / "campaign.json"
        replacement = root / "replacement.json"
        shutil.copyfile(source, original)
        first = json.loads(source.read_text(encoding="utf-8"))
        second = dict(first)
        second["campaign_id"] = f"{first['campaign_id']}-substituted"
        replacement.write_text(json.dumps(second) + "\n", encoding="utf-8")

        authenticated = runner.authenticate_regular_path_nofollow(original, "campaign spec")
        try:
            os.replace(replacement, original)
            try:
                parsed, _raw, _identity = runner.parse_spec(authenticated, None)
            except runner.RunnerError:
                parsed = None
            require(parsed is None, "campaign spec pathname substitution was not rejected")
        finally:
            authenticated.close()


def corpus_output_root_nofollow() -> None:
    with tempfile.TemporaryDirectory(prefix="p062-corpus-root-") as temporary:
        root = Path(temporary)
        victim = root / "victim"
        victim.mkdir()
        alias = root / "alias"
        alias.symlink_to(victim, target_is_directory=True)
        requested = alias / "must-not-exist" / "nested"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "benchmarks/scripts/build-provisional-corpus.py"),
                "--spec",
                str(ROOT / "benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json"),
                "--output-root",
                str(requested),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        require(result.returncode == 2, f"symlinked output root returned {result.returncode}")
        require(not (victim / "must-not-exist").exists(), "builder modified a symlink-ancestor victim")


def artifact_post_commit_substitution(artifact: ModuleType) -> None:
    original = artifact._unlinkat_regular
    with tempfile.TemporaryDirectory(prefix="p062-artifact-") as temporary:
        root = Path(temporary)
        output = root / "result.json"
        calls = 0
        fired = False

        def reauthenticate() -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise artifact.ArtifactError("forced post-commit failure")

        def swap_then_remove(parent_fd: int, name: str, label: str, expected: tuple[int, int]) -> None:
            nonlocal fired
            if not fired and name == output.name:
                fired = True
                os.rename(name, "owned-preserved", src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
                try:
                    os.write(fd, b"foreign")
                finally:
                    os.close(fd)
            original(parent_fd, name, label, expected)

        artifact._unlinkat_regular = swap_then_remove
        rejected = False
        try:
            try:
                artifact.atomic_publish_bytes(output, b"owned", reauthenticate=reauthenticate)
            except artifact.ArtifactError:
                rejected = True
        finally:
            artifact._unlinkat_regular = original
        require(fired and rejected and calls == 2, "post-commit substitution probe did not reach the removal boundary")
        require(output.read_bytes() == b"foreign", "foreign published-path replacement was removed")
        require((root / "owned-preserved").read_bytes() == b"owned", "transaction-owned output was not preserved")


def main() -> int:
    runner = load_module(ROOT / "benchmarks/scripts/diagnostic-runner.py", "p062_runner")
    corpus = load_module(ROOT / "benchmarks/scripts/build-provisional-corpus.py", "p062_corpus")
    artifact = load_module(ROOT / "benchmarks/scripts/diagnostic_artifact.py", "p062_artifact")

    owned_cleanup_substitution(runner, "runner")
    owned_cleanup_substitution(corpus, "corpus")
    runner_spec_continuity(runner)
    corpus_output_root_nofollow()
    artifact_post_commit_substitution(artifact)
    print(
        "patch061-corrective-regression-smoke: ok "
        "owned_cleanup=2 spec_continuity=1 output_root_nofollow=1 artifact_cleanup=1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
