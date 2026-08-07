#!/usr/bin/env python3
"""Exercise acceptance blockers promoted from the Patch 080 review.

This gate is bounded and non-destructive. It creates temporary Git repositories,
uses fake Docker image metadata, and injects failures at exact transaction seams.
It validates tooling and delivery authorities only; it does not make runtime,
performance, coverage, or exploitability claims.
"""
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
    """Raised when a promoted finding is not discriminated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    data: bytes | None = None,
    expected: int | None = 0,
) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if expected is not None:
        require(
            cp.returncode == expected,
            f"command failed ({cp.returncode}, expected {expected}): {' '.join(argv)}\n"
            f"stdout={cp.stdout[-2000:]!r}\nstderr={cp.stderr[-4000:]!r}",
        )
    return cp


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str, data: bytes | None = None) -> str:
    return run(["git", "-C", str(repo), *args], data=data).stdout.decode().strip()


def init_repo(path: Path, files: dict[str, bytes]) -> tuple[str, str]:
    path.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=path)
    run(["git", "config", "user.email", "x64lens-regression@example.invalid"], cwd=path)
    run(["git", "config", "user.name", "x64lens regression"], cwd=path)
    for raw, payload in files.items():
        target = path / raw
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    run(["git", "add", "-A"], cwd=path)
    run(["git", "commit", "-q", "-m", "base"], cwd=path)
    return git(path, "rev-parse", "HEAD"), git(path, "rev-parse", "HEAD^{tree}")


def make_candidate(repo: Path, changes: dict[str, bytes]) -> tuple[str, bytes]:
    for raw, payload in changes.items():
        target = repo / raw
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    run(["git", "add", "-A"], cwd=repo)
    tree = git(repo, "write-tree")
    patch = run(
        ["git", "diff", "--cached", "--binary", "--full-index"], cwd=repo
    ).stdout
    run(["git", "reset", "--hard", "HEAD"], cwd=repo)
    return tree, patch


def test_transaction_foreign_replacement(tmp: Path) -> int:
    helper = load_module("p081_tx_foreign", ROOT / "tools/git-patch-transaction.py")
    repo = tmp / "foreign-repo"
    head, base_tree = init_repo(repo, {"stable.txt": b"stable\n"})
    candidate_tree, patch = make_candidate(repo, {"victim": b"candidate-owned\n"})
    original_hook = helper.invoke_hook

    def replace_then_fail(name: str, binding: Any) -> None:
        if name != "X64LENS_PATCH_TRANSACTION_AFTER_APPLY_EFFECT_HOOK":
            return
        parent_fd, leaf = helper._open_parent(binding, "victim")
        try:
            os.unlink(leaf, dir_fd=parent_fd)
            os.mkdir(leaf, 0o755, dir_fd=parent_fd)
            victim_fd = os.open(
                leaf,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=parent_fd,
            )
            try:
                fd = os.open(
                    "foreign.txt",
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                    0o600,
                    dir_fd=victim_fd,
                )
                try:
                    os.write(fd, b"foreign replacement\n")
                finally:
                    os.close(fd)
            finally:
                os.close(victim_fd)
        finally:
            os.close(parent_fd)
        raise helper.TransactionError("injected foreign replacement")

    helper.invoke_hook = replace_then_fail
    binding = helper.open_repo(repo)
    try:
        try:
            helper.apply_patch(
                binding,
                patch,
                branch="main",
                base_head=head,
                base_tree=base_tree,
                candidate_tree=candidate_tree,
            )
        except helper.TransactionError as exc:
            require("foreign" in str(exc), "foreign replacement failure was not classified")
        else:
            raise RegressionError("foreign replacement was accepted")
    finally:
        helper.close_repo(binding)
        helper.invoke_hook = original_hook
    require((repo / "victim/foreign.txt").read_bytes() == b"foreign replacement\n",
            "transaction recovery deleted a foreign replacement")
    return 1


def test_literal_pathspec_and_unrelated_state(tmp: Path) -> tuple[int, int]:
    helper = load_module("p081_tx_literal", ROOT / "tools/git-patch-transaction.py")
    repo = tmp / "literal-repo"
    head, base_tree = init_repo(
        repo,
        {"stable.txt": b"stable\n", "unrelated.txt": b"original unrelated bytes\n"},
    )
    magic = ":(glob)*.tmp"
    candidate_tree, patch = make_candidate(repo, {magic: b"literal patch path\n"})
    unrelated_untracked = repo / "unrelated-secret.tmp"
    unrelated_untracked.write_bytes(b"preserve me\n")
    binding = helper.open_repo(repo)
    try:
        paths = helper.patch_paths(binding, patch)
        result = helper.restore_exact_tree(
            binding, candidate_tree, base_tree, paths=paths
        )
    finally:
        helper.close_repo(binding)
    require(result is not None and "unrelated" in result, "unrelated untracked state was not reported")
    require(unrelated_untracked.read_bytes() == b"preserve me\n", "literal recovery deleted unrelated untracked data")
    require((repo / magic).read_bytes() == b"literal patch path\n", "literal Git pathspec was not restored exactly")

    run(["git", "reset", "--hard", "HEAD"], cwd=repo)
    unrelated_untracked.unlink()
    original_hook = helper.invoke_hook

    def edit_then_fail(name: str, _binding: Any) -> None:
        if name == "X64LENS_PATCH_TRANSACTION_AFTER_APPLY_EFFECT_HOOK":
            (repo / "unrelated.txt").write_bytes(b"concurrent unrelated edit\n")
            raise helper.TransactionError("injected unrelated edit")

    helper.invoke_hook = edit_then_fail
    binding = helper.open_repo(repo)
    try:
        try:
            helper.apply_patch(
                binding,
                patch,
                branch="main",
                base_head=head,
                base_tree=base_tree,
                candidate_tree=candidate_tree,
            )
        except helper.TransactionError:
            pass
        else:
            raise RegressionError("unrelated tracked edit failure was accepted")
    finally:
        helper.close_repo(binding)
        helper.invoke_hook = original_hook
    require((repo / "unrelated.txt").read_bytes() == b"concurrent unrelated edit\n",
            "transaction recovery erased unrelated tracked work")
    require(not (repo / magic).exists(), "transaction recovery left a patch-owned path")
    return 1, 1


def test_gitless_preauth(tmp: Path) -> int:
    probe = tmp / "gitless-preauth"
    (probe / "tools").mkdir(parents=True)
    sentinel = probe / "preauth-sentinel.txt"
    (probe / "tools/gitless-source-manifest.py").write_text(
        "from pathlib import Path\n"
        "root=Path(__file__).resolve().parents[1]\n"
        "(root/'preauth-sentinel.txt').write_text('executed\\n')\n"
        "raise RuntimeError('unauthenticated helper executed')\n",
        encoding="utf-8",
    )
    (probe / "manifest.json").write_text(
        json.dumps({"schema": "hostile", "candidate_tree": "0" * 40}) + "\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        {
            "X64LENS_SOURCE_MANIFEST": str(probe / "manifest.json"),
            "X64LENS_CANDIDATE_TREE": "0" * 40,
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    cp = run(
        [sys.executable, str(ROOT / "tools/normalize-tracked-permissions.py"), "--repo", str(probe)],
        env=env,
        expected=None,
    )
    require(cp.returncode != 0, "hostile Git-less manifest was accepted")
    require(not sentinel.exists(), "Git-less normalization executed an unauthenticated source helper")
    return 1


def transaction_cli(
    helper: Path,
    repo: Path,
    patch_path: Path,
    patch_sha: str,
    action: str,
    head: str,
    base_tree: str,
    candidate_tree: str,
) -> subprocess.CompletedProcess[bytes]:
    return run(
        [
            sys.executable,
            str(helper),
            action,
            "--repo", str(repo),
            "--patch", str(patch_path),
            "--patch-sha256", patch_sha,
            "--branch", "main",
            "--base-head", head,
            "--base-tree", base_tree,
            "--candidate-tree", candidate_tree,
        ],
        expected=None,
    )


def test_exact_already_state(tmp: Path) -> int:
    repo = tmp / "already-repo"
    head, base_tree = init_repo(repo, {"payload.txt": b"base\n"})
    candidate_tree, patch = make_candidate(repo, {"payload.txt": b"candidate\n"})
    patch_path = tmp / "candidate.patch"
    patch_path.write_bytes(patch)
    patch_sha = hashlib.sha256(patch).hexdigest()
    helper = ROOT / "tools/git-patch-transaction.py"

    require(transaction_cli(helper, repo, patch_path, patch_sha, "apply", head, base_tree, candidate_tree).returncode == 0,
            "initial exact application failed")
    (repo / "foreign-untracked.txt").write_bytes(b"unrelated\n")
    require(transaction_cli(helper, repo, patch_path, patch_sha, "apply", head, base_tree, candidate_tree).returncode == 1,
            "apply already-state ignored nonignored untracked state")
    (repo / "foreign-untracked.txt").unlink()
    require(transaction_cli(helper, repo, patch_path, patch_sha, "apply", head, base_tree, candidate_tree).returncode == 3,
            "exact applied state did not return exit 3")
    run(["git", "switch", "-q", "-c", "wrong-branch"], cwd=repo)
    require(transaction_cli(helper, repo, patch_path, patch_sha, "apply", head, base_tree, candidate_tree).returncode == 1,
            "apply already-state ignored branch identity")
    run(["git", "switch", "-q", "main"], cwd=repo)
    require(transaction_cli(helper, repo, patch_path, patch_sha, "rollback", head, base_tree, candidate_tree).returncode == 0,
            "exact rollback failed")
    (repo / "foreign-untracked.txt").write_bytes(b"unrelated\n")
    require(transaction_cli(helper, repo, patch_path, patch_sha, "rollback", head, base_tree, candidate_tree).returncode == 1,
            "rollback already-state ignored nonignored untracked state")
    (repo / "foreign-untracked.txt").unlink()
    require(transaction_cli(helper, repo, patch_path, patch_sha, "rollback", head, base_tree, candidate_tree).returncode == 3,
            "exact rolled-back state did not return exit 3")
    return 1



def test_fresh_clone_without_candidate_tree(tmp: Path) -> int:
    """Prove application does not require the unreferenced candidate tree object."""
    helper = ROOT / "tools/git-patch-transaction.py"
    source = tmp / "fresh-source"
    head, base_tree = init_repo(source, {"payload.txt": b"base\n"})
    candidate_tree, patch = make_candidate(
        source,
        {
            "payload.txt": b"candidate\n",
            "added.txt": b"new candidate file\n",
        },
    )
    target = tmp / "fresh-clone"
    run(["git", "clone", "-q", "--no-local", str(source), str(target)])
    require(
        run(["git", "-C", str(target), "cat-file", "-e", f"{candidate_tree}^{{tree}}"], expected=None).returncode != 0,
        "fresh clone unexpectedly retained the unreferenced candidate-tree object",
    )
    patch_path = tmp / "fresh-clone.patch"
    patch_path.write_bytes(patch)
    digest = hashlib.sha256(patch).hexdigest()
    applied = transaction_cli(
        helper, target, patch_path, digest, "apply", head, base_tree, candidate_tree
    )
    require(applied.returncode == 0, f"fresh-clone apply failed: {applied.stderr!r}")
    require(git(target, "write-tree") == candidate_tree, "fresh-clone apply produced the wrong tree")
    rolled = transaction_cli(
        helper, target, patch_path, digest, "rollback", head, base_tree, candidate_tree
    )
    require(rolled.returncode == 0, f"fresh-clone rollback failed: {rolled.stderr!r}")
    require(git(target, "write-tree") == base_tree, "fresh-clone rollback did not restore the base")
    return 1

def write_fake_docker(path: Path) -> None:
    path.write_text(
        r'''#!/usr/bin/env python3
import json, os, pathlib, sys
state = pathlib.Path(os.environ["P081_DOCKER_STATE"])
args = sys.argv[1:]
if args[:2] != ["image", "inspect"]:
    raise SystemExit(64)
data = json.loads(state.read_text(encoding="utf-8"))
record = data[args[2]]
print(json.dumps([{"Id": record["id"], "Config": {"Labels": record["labels"]}}]))
''',
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_docker_provenance(tmp: Path) -> int:
    fake = tmp / "fake-docker"
    state = tmp / "docker-state.json"
    context = tmp / "context"
    context.mkdir()
    source_manifest = context / "source-manifest.json"
    context_authority = context / "context-authority.json"
    source_manifest.write_text("{}\n", encoding="utf-8")
    tree = "1" * 40
    context_authority.write_text(json.dumps({"candidate_tree": tree}) + "\n", encoding="utf-8")
    context_sha = hashlib.sha256(context_authority.read_bytes()).hexdigest()
    source_sha = hashlib.sha256(source_manifest.read_bytes()).hexdigest()
    image_id = "sha256:" + "a" * 64
    labels = {
        "org.x64lens.candidate-tree": tree,
        "org.x64lens.context-authority-sha256": context_sha,
        "org.x64lens.source-manifest-sha256": source_sha,
    }
    state.write_text(json.dumps({"x64lens:test": {"id": image_id, "labels": labels}, image_id: {"id": image_id, "labels": labels}}), encoding="utf-8")
    write_fake_docker(fake)
    authority = tmp / "image-authority.json"
    env = os.environ.copy()
    env["P081_DOCKER_STATE"] = str(state)
    tool = ROOT / "tools/docker-image-authority.py"
    run([
        sys.executable, str(tool), "record", "--path", str(authority), "--docker", str(fake),
        "--tag", "x64lens:test", "--candidate-tree", tree,
        "--context-authority", str(context_authority),
    ], env=env)
    run([sys.executable, str(tool), "verify", "--path", str(authority), "--docker", str(fake)], env=env)

    value = json.loads(authority.read_text(encoding="utf-8"))
    value["context_authority_sha256"] = "0" * 64
    authority.chmod(0o644)
    authority.write_text(json.dumps(value) + "\n", encoding="utf-8")
    authority.chmod(0o444)
    require(run([sys.executable, str(tool), "verify", "--path", str(authority), "--docker", str(fake)], env=env, expected=None).returncode == 1,
            "Docker authority ignored stored context provenance")

    value["context_authority_sha256"] = context_sha
    authority.chmod(0o644)
    authority.write_text(json.dumps(value) + "\n", encoding="utf-8")
    authority.chmod(0o444)
    data = json.loads(state.read_text(encoding="utf-8"))
    data[image_id]["labels"]["org.x64lens.source-manifest-sha256"] = "f" * 64
    state.write_text(json.dumps(data), encoding="utf-8")
    require(run([sys.executable, str(tool), "verify", "--path", str(authority), "--docker", str(fake)], env=env, expected=None).returncode == 1,
            "Docker authority ignored immutable image source provenance")
    return 1


def test_portable_checksum_paths(tmp: Path) -> int:
    payload = tmp / "payload.txt"
    payload.write_text("portable evidence\n", encoding="utf-8")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    manifest = tmp / "SHA256SUMS.txt"
    manifest.write_text(f"{digest}  payload.txt\n", encoding="utf-8")
    tool = ROOT / "tools/verify-checksum-manifest.py"
    run([sys.executable, str(tool), str(manifest)])
    manifest.write_text(f"{digest}  {payload}\n", encoding="utf-8")
    require(run([sys.executable, str(tool), str(manifest)], expected=None).returncode != 0,
            "checksum authority accepted a nonportable absolute path")
    return 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p080-corrective-") as raw:
        tmp = Path(raw)
        foreign = test_transaction_foreign_replacement(tmp)
        literal, unrelated = test_literal_pathspec_and_unrelated_state(tmp)
        preauth = test_gitless_preauth(tmp)
        already = test_exact_already_state(tmp)
        fresh_clone = test_fresh_clone_without_candidate_tree(tmp)
        docker = test_docker_provenance(tmp)
        portable = test_portable_checksum_paths(tmp)
    print(
        "patch080-corrective-regression-smoke: ok "
        f"transaction_foreign_preserved={foreign} literal_pathspec={literal} "
        f"unrelated_tracked_preserved={unrelated} gitless_preauth={preauth} "
        f"exact_already_state={already} candidate_tree_absent={fresh_clone} "
        f"docker_provenance={docker} "
        f"portable_checksum_paths={portable}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RegressionError, ValueError, json.JSONDecodeError) as exc:
        print(f"patch080-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
