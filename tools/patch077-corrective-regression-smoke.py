#!/usr/bin/env python3
"""Promote every confirmed Patch 077 acceptance blocker into a regression.

The probes cover descriptor-bound patch and permission roots, expected-failure
parity normalization, caller-visible no-replace publication, final cleanup
replacement preservation, discriminating patch-digest authentication, and exact
Git-less/Docker source membership.  Loose-delivery byte identity is verified by
the per-delivery manifest and flat checksum gates because it is an artifact
property rather than a tracked-source behavior.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True


class Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Error(message)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        timeout: int = 180) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=timeout,
    )


def init_repo(root: Path, *, mode: int = 0o644) -> tuple[str, str]:
    root.mkdir()
    require(run(["git", "init", "-q", "-b", "main"], cwd=root).returncode == 0, "git init failed")
    run(["git", "config", "user.name", "test"], cwd=root)
    run(["git", "config", "user.email", "test@example.invalid"], cwd=root)
    target = root / "value.txt"
    target.write_text("base\n", encoding="utf-8")
    target.chmod(mode)
    require(run(["git", "add", "value.txt"], cwd=root).returncode == 0, "git add failed")
    require(run(["git", "commit", "-qm", "base"], cwd=root).returncode == 0, "git commit failed")
    return git(root, "rev-parse", "HEAD"), git(root, "rev-parse", "HEAD^{tree}")


def git(root: Path, *args: str) -> str:
    cp = run(["git", *args], cwd=root)
    require(cp.returncode == 0, f"git {' '.join(args)} failed: {cp.stderr.decode(errors='replace')}")
    return cp.stdout.decode().strip()


def make_patch(repo: Path) -> tuple[bytes, str]:
    target = repo / "value.txt"
    target.write_text("candidate\n", encoding="utf-8")
    patch = run(["git", "diff", "--binary", "--", "value.txt"], cwd=repo).stdout
    run(["git", "add", "value.txt"], cwd=repo)
    tree = git(repo, "write-tree")
    run(["git", "reset", "--hard", "-q", "HEAD"], cwd=repo)
    return patch, tree


def patch_root_binding() -> tuple[int, int]:
    helper = ROOT / "tools/git-patch-transaction.py"
    with tempfile.TemporaryDirectory(prefix="x64lens-p078-patch-root-") as raw:
        area = Path(raw)
        repo = area / "repo"
        base_head, base_tree = init_repo(repo)
        patch_bytes, candidate_tree = make_patch(repo)
        patch = area / "candidate.patch"
        patch.write_bytes(patch_bytes)
        common = [
            "--repo", str(repo), "--patch", str(patch),
            "--patch-sha256", hashlib.sha256(patch_bytes).hexdigest(),
            "--branch", "main", "--base-head", base_head,
            "--base-tree", base_tree, "--candidate-tree", candidate_tree,
        ]

        replacement = area / "replacement"
        require(run(["git", "clone", "-q", str(repo), str(replacement)]).returncode == 0,
                "replacement clone failed")
        displaced = area / "displaced"
        env = dict(os.environ)
        env["X64LENS_PATCH_TRANSACTION_AFTER_CHECK_HOOK"] = (
            f"mv {q(repo)} {q(displaced)} && mv {q(replacement)} {q(repo)}"
        )
        cp = run([sys.executable, str(helper), "apply", *common], cwd=area, env=env)
        require(cp.returncode != 0 and b"repository root binding changed" in cp.stderr,
                f"apply root replacement was not rejected: {cp.stderr!r}")
        require((repo / "value.txt").read_text() == "base\n", "replacement repository was mutated")
        require((displaced / "value.txt").read_text() == "base\n", "selected repository was mutated")
        apply_ok = 1

        # Restore the selected repository, apply normally, and create an exact
        # candidate replacement for the rollback-boundary discriminator.
        shutil.rmtree(repo)
        displaced.rename(repo)
        normal = run([sys.executable, str(helper), "apply", *common], cwd=area)
        require(normal.returncode == 0, f"normal setup apply failed: {normal.stderr!r}")
        replacement2 = area / "replacement2"
        require(run(["git", "clone", "-q", str(repo), str(replacement2)]).returncode == 0,
                "candidate replacement clone failed")
        # clone omits staged state; reproduce the candidate index/worktree.
        require(run(["git", "apply", "--index", str(patch)], cwd=replacement2).returncode == 0,
                "candidate replacement apply failed")
        displaced2 = area / "displaced2"
        env = dict(os.environ)
        env["X64LENS_PATCH_TRANSACTION_AFTER_REVERSE_CHECK_HOOK"] = (
            f"mv {q(repo)} {q(displaced2)} && mv {q(replacement2)} {q(repo)}"
        )
        cp = run([sys.executable, str(helper), "rollback", *common], cwd=area, env=env)
        require(cp.returncode != 0 and b"repository root binding changed" in cp.stderr,
                f"rollback root replacement was not rejected: {cp.stderr!r}")
        require((repo / "value.txt").read_text() == "candidate\n", "replacement candidate was mutated")
        require((displaced2 / "value.txt").read_text() == "candidate\n", "selected candidate was mutated")
        rollback_ok = 1
    return apply_ok, rollback_ok


def q(path: Path) -> str:
    import shlex
    return shlex.quote(str(path))


def normalizer_root_binding() -> int:
    normalizer = load("p078_normalizer", ROOT / "tools/normalize-tracked-permissions.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p078-normalizer-root-") as raw:
        area = Path(raw)
        repo = area / "repo"
        init_repo(repo)
        (repo / "value.txt").chmod(0o600)
        replacement = area / "replacement"
        shutil.copytree(repo, replacement)
        displaced = area / "displaced"

        def swap(_repo: Path) -> None:
            repo.rename(displaced)
            replacement.rename(repo)

        normalizer._TEST_AFTER_ROOT_BIND_BEFORE_INDEX_HOOK = swap
        try:
            try:
                normalizer.normalize(repo)
            except (normalizer.PermissionErrorContract, OSError):
                pass
            else:
                raise Error("permission normalizer accepted a rebound root")
        finally:
            normalizer._TEST_AFTER_ROOT_BIND_BEFORE_INDEX_HOOK = None
        require(stat.S_IMODE((repo / "value.txt").stat().st_mode) == 0o600,
                "replacement root was chmodded")
        require(stat.S_IMODE((displaced / "value.txt").stat().st_mode) == 0o600,
                "selected root was chmodded")
    return 1


def parity_failures_and_publication() -> tuple[int, int]:
    parity = load("p078_dynamic_parity", ROOT / "tools/sprint12-dynamic-metadata-environment-parity-smoke.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p078-parity-") as raw:
        root = Path(raw)
        target = root / "target.elf"
        target.write_bytes(b"x")
        require(parity.normalized_stream("gadgets", b"", target, 6) == b"", "expected failure was not empty")
        try:
            parity.normalized_stream("gadgets", b"", target, 0)
        except (parity.Error, ValueError, UnicodeDecodeError):
            pass
        else:
            raise Error("successful empty JSON was accepted")
        failure_ok = 1

        parent = root / "results"
        parent.mkdir()
        stage = parent / "stage"
        stage.mkdir()
        (stage / "marker").write_text("owned\n")
        detached = root / "detached-results"

        def replace(_source: Path, _destination: Path) -> None:
            parent.rename(detached)
            parent.mkdir()

        parity._TEST_BEFORE_PUBLISH_RENAME_HOOK = replace
        try:
            try:
                parity.rename_noreplace(stage, parent / "final")
            except (parity.Error, OSError):
                pass
            else:
                raise Error("parity publication reported success after parent replacement")
        finally:
            parity._TEST_BEFORE_PUBLISH_RENAME_HOOK = None
        require(not (parent / "final").exists(), "declared result appeared in replacement parent")
        require((detached / "final/marker").read_text() == "owned\n", "authenticated result was lost")
        publication_ok = 1
    return failure_ok, publication_ok


def custody_final_replacement() -> int:
    custody = load("p078_custody", ROOT / "tools/verify-delivery-custody.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p078-custody-final-") as raw:
        root = Path(raw)
        parent_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            (root / "owned").write_text("owned\n")
            owned_fd = os.open("owned", os.O_RDONLY, dir_fd=parent_fd)
            displaced_name: list[str] = []

            def substitute(fd: int, name: str, _owned_fd: int, _label: str) -> None:
                displaced = f"{name}.owned"
                os.rename(name, displaced, src_dir_fd=fd, dst_dir_fd=fd)
                foreign = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=fd)
                os.write(foreign, b"foreign\n")
                os.close(foreign)
                displaced_name.append(displaced)

            custody._TEST_BEFORE_FINAL_UNLINK_HOOK = substitute
            try:
                try:
                    custody._unlink_owned_name(parent_fd, "owned", owned_fd, "test object")
                except (custody.CustodyError, OSError):
                    pass
                else:
                    raise Error("custody cleanup deleted a final foreign replacement")
            finally:
                custody._TEST_BEFORE_FINAL_UNLINK_HOOK = None
                os.close(owned_fd)
            require(displaced_name, "custody final hook did not run")
            require((root / next(name for name in os.listdir(root) if name.endswith('.owned'))).read_text() == "owned\n",
                    "owned custody object was not preserved")
            foreign_names = [name for name in os.listdir(root) if name.startswith('.custody-delete.') and not name.endswith('.owned')]
            require(len(foreign_names) == 1 and (root / foreign_names[0]).read_text() == "foreign\n",
                    "foreign custody replacement was deleted")
        finally:
            os.close(parent_fd)
    return 1


def recovery_final_replacement() -> int:
    recovery = load("p078_recovery", ROOT / "tools/recover-candidate-source.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p078-recovery-final-") as raw:
        root = Path(raw)
        parent_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            (root / "owned").mkdir()
            (root / "owned/marker").write_text("owned\n")
            owned_fd = os.open("owned", os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent_fd)
            expected = recovery.stable(os.fstat(owned_fd))

            def substitute(fd: int, name: str, _root_fd: int) -> None:
                os.rename(name, f"{name}.owned", src_dir_fd=fd, dst_dir_fd=fd)
                os.mkdir(name, 0o700, dir_fd=fd)
                foreign_dir = os.open(name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
                marker = os.open("foreign", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=foreign_dir)
                os.write(marker, b"foreign\n")
                os.close(marker)
                os.close(foreign_dir)

            recovery._TEST_BEFORE_FINAL_RMTREE_HOOK = substitute
            try:
                try:
                    recovery.cleanup_owned_root(parent_fd, "owned", owned_fd, expected)
                except (recovery.RecoveryError, OSError):
                    pass
                else:
                    raise Error("recovery cleanup deleted a final foreign replacement")
            finally:
                recovery._TEST_BEFORE_FINAL_RMTREE_HOOK = None
                os.close(owned_fd)
            names = os.listdir(root)
            owned_names = [name for name in names if name.endswith('.owned')]
            foreign_names = [name for name in names if name.startswith('.x64lens-recovery-delete.') and not name.endswith('.owned')]
            require(len(owned_names) == 1 and (root / owned_names[0] / "marker").read_text() == "owned\n",
                    "owned recovery root was not preserved")
            require(len(foreign_names) == 1 and (root / foreign_names[0] / "foreign").read_text() == "foreign\n",
                    "foreign recovery replacement was deleted")
        finally:
            os.close(parent_fd)
    return 1


def digest_regression() -> int:
    prior = load("p078_patch076", ROOT / "tools/patch076-corrective-regression-smoke.py")
    _apply, _rollback, digest = prior.patch_transaction_tests()
    require(digest == 1, "wrong-digest authentication regression failed")
    return 1


def gitless_and_docker_context() -> tuple[int, int, int]:
    source = load("p078_gitless", ROOT / "tools/gitless-source-manifest.py")
    patch070 = load("p078_patch070", ROOT / "tools/patch070-corrective-regression-smoke.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p078-gitless-") as raw:
        area = Path(raw)
        repo = area / "repo"
        repo.mkdir()
        run(["git", "init", "-q", "-b", "main"], cwd=repo)
        run(["git", "config", "user.name", "test"], cwd=repo)
        run(["git", "config", "user.email", "test@example.invalid"], cwd=repo)
        (repo / "Dockerfile").write_text("FROM scratch\nCOPY source/ /work/\n", encoding="utf-8")
        (repo / "keep").write_text("tracked\n", encoding="utf-8")
        (repo / "tools").mkdir()
        shutil.copy2(ROOT / "tools/gitless-source-manifest.py", repo / "tools/gitless-source-manifest.py")
        run(["git", "add", "."], cwd=repo)
        run(["git", "commit", "-qm", "base"], cwd=repo)
        (repo / "AGENTS.md").write_text("untracked\n")
        (repo / ".env.local").write_text("untracked\n")
        (repo / "tools/__pycache__").mkdir()
        (repo / "tools/__pycache__/ignored.pyc").write_bytes(b"ignored")
        context = area / "context"
        authority = source.create_context(repo, context)
        manifest = source.load_manifest(context / "source-manifest.json")
        source.verify(context / "source", manifest)
        require(authority["ignored_or_untracked_members_copied"] == 0, "context copied ignored files")
        require(not (context / "source/AGENTS.md").exists() and not (context / "source/.env.local").exists(),
                "untracked context members were copied")
        require((context / "Dockerfile.transport").read_bytes() == (context / "source/Dockerfile").read_bytes(),
                "transport Dockerfile differs from staged source")
        context_ok = 1

        # Exercise Patch 070's Git-less branch against the exact source tree.
        old_root = patch070.ROOT
        old_manifest = os.environ.get("X64LENS_SOURCE_MANIFEST")
        old_authority_root = os.environ.get("X64LENS_SOURCE_AUTHORITY_ROOT")
        patch070.ROOT = context / "source"
        os.environ["X64LENS_SOURCE_MANIFEST"] = str(context / "source-manifest.json")
        os.environ["X64LENS_SOURCE_AUTHORITY_ROOT"] = str(context / "source")
        try:
            patch070.source_custody_probe()
        finally:
            patch070.ROOT = old_root
            if old_manifest is None:
                os.environ.pop("X64LENS_SOURCE_MANIFEST", None)
            else:
                os.environ["X64LENS_SOURCE_MANIFEST"] = old_manifest
            if old_authority_root is None:
                os.environ.pop("X64LENS_SOURCE_AUTHORITY_ROOT", None)
            else:
                os.environ["X64LENS_SOURCE_AUTHORITY_ROOT"] = old_authority_root
        gitless_ok = 1

        (context / "source/extra").write_text("extra\n")
        try:
            source.verify(context / "source", manifest)
        except source.SourceError:
            pass
        else:
            raise Error("exact source verifier accepted an undeclared image member")
        membership_ok = 1

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    require("COPY source/ /work/" in dockerfile and "COPY . /work" not in dockerfile,
            "Dockerfile does not use the exact generated source context")
    return gitless_ok, context_ok, membership_ok


def main() -> int:
    apply_root, rollback_root = patch_root_binding()
    normalizer = normalizer_root_binding()
    parity_failure, parity_publication = parity_failures_and_publication()
    custody = custody_final_replacement()
    recovery = recovery_final_replacement()
    digest = digest_regression()
    gitless, context, membership = gitless_and_docker_context()
    print(
        "patch077-corrective-regression-smoke: ok "
        f"patch_apply_root={apply_root} patch_rollback_root={rollback_root} "
        f"normalizer_root={normalizer} parity_expected_failure={parity_failure} "
        f"parity_parent_binding={parity_publication} custody_final={custody} "
        f"recovery_final={recovery} digest_auth={digest} gitless_patch070={gitless} "
        f"docker_exact_context={context} docker_exact_membership={membership} "
        "loose_helper_identity=delivery_gate"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Error, OSError, subprocess.SubprocessError, TimeoutError) as exc:
        print(f"patch077-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
