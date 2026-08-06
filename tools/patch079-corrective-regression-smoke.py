#!/usr/bin/env python3
"""Exercise every Patch 079 acceptance blocker promoted into Patch 080.

The regression uses temporary repositories, Git-less source authorities, fake
Docker image inspection, and injected partial effects.  It requires no NASM or
Docker daemon and does not infer analyzer behavior from tooling checks.
"""
from __future__ import annotations

import hashlib
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

ROOT = Path(__file__).resolve().parents[1]


class RegressionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        data: bytes | None = None, expected: int | None = 0) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(argv, cwd=cwd, env=env, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if expected is not None:
        require(cp.returncode == expected, f"command failed ({cp.returncode}, expected {expected}): {' '.join(argv)}\nstdout={cp.stdout[-1000:]!r}\nstderr={cp.stderr[-3000:]!r}")
    return cp


def git(repo: Path, *args: str, data: bytes | None = None) -> str:
    return run(["git", "-C", str(repo), *args], data=data).stdout.decode().strip()


def init_repo(path: Path, files: dict[str, tuple[bytes, int]]) -> tuple[str, str]:
    path.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=path)
    run(["git", "config", "user.email", "p080-regression@example.invalid"], cwd=path)
    run(["git", "config", "user.name", "P080 regression"], cwd=path)
    for raw, (payload, mode) in files.items():
        target = path / raw
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        target.chmod(mode)
    run(["git", "add", "-A"], cwd=path)
    run(["git", "commit", "-q", "-m", "base"], cwd=path)
    return git(path, "rev-parse", "HEAD"), git(path, "rev-parse", "HEAD^{tree}")


def make_patch_repo(tmp: Path) -> tuple[Path, str, str, str, bytes]:
    repo = tmp / "patch-repo"
    base_head, base_tree = init_repo(repo, {"payload.txt": (b"base\n", 0o644), "remove.txt": (b"remove\n", 0o644)})
    (repo / "payload.txt").write_bytes(b"candidate\n")
    (repo / "new.txt").write_bytes(b"new\n")
    (repo / "remove.txt").unlink()
    run(["git", "add", "-A"], cwd=repo)
    candidate_tree = git(repo, "write-tree")
    raw = run(["git", "diff", "--cached", "--binary", "--full-index"], cwd=repo).stdout
    run(["git", "reset", "--hard", "HEAD"], cwd=repo)
    return repo, base_head, base_tree, candidate_tree, raw


def test_partial_patch_recovery(tmp: Path) -> tuple[int, int]:
    helper = module("p080_patch_transaction", ROOT / "tools/git-patch-transaction.py")
    repo, base_head, base_tree, candidate_tree, raw = make_patch_repo(tmp)
    handle = helper.open_repo(repo)
    original = helper.git_apply
    try:
        def worktree_only(repo_handle: Any, patch: bytes, *, reverse: bool, check_only: bool) -> None:
            if check_only:
                original(repo_handle, patch, reverse=reverse, check_only=True)
                return
            argv = ["git", f"--git-dir={repo_handle.git_proc}", f"--work-tree={repo_handle.root_proc}", "apply"]
            if reverse: argv.append("--reverse")
            argv.append("-")
            cp = helper.run(repo_handle, argv, input_bytes=patch)
            require(cp.returncode == 0, "injected worktree-only effect failed")
            raise RuntimeError("injected partial worktree-only effect")

        helper.git_apply = worktree_only
        try:
            helper.apply_patch(handle, raw, branch="main", base_head=base_head, base_tree=base_tree, candidate_tree=candidate_tree)
        except helper.TransactionError as exc:
            require("restored the logical base" in str(exc), "partial apply recovery was not reported")
        else:
            raise RegressionError("partial worktree-only apply was accepted")
        require(helper.exact_tree_state(handle, base_tree), "partial apply left index/worktree residue")

        helper.git_apply = original
        helper.apply_patch(handle, raw, branch="main", base_head=base_head, base_tree=base_tree, candidate_tree=candidate_tree)
        require(helper.exact_tree_state(handle, candidate_tree), "normal apply did not reach candidate")
        helper.git_apply = worktree_only
        try:
            helper.rollback_patch(handle, raw, branch="main", base_head=base_head, base_tree=base_tree, candidate_tree=candidate_tree)
        except helper.TransactionError as exc:
            require("restored the staged candidate" in str(exc), "partial rollback recovery was not reported")
        else:
            raise RegressionError("partial worktree-only rollback was accepted")
        require(helper.exact_tree_state(handle, candidate_tree), "partial rollback lost candidate index/worktree")
    finally:
        helper.git_apply = original
        helper.close_repo(handle)
    return 1, 1


def create_gitless(tmp: Path, name: str) -> tuple[Any, Path, Path, Path, dict[str, Any]]:
    helper = module(f"p080_gitless_{name}", ROOT / "tools/gitless-source-manifest.py")
    repo = tmp / f"{name}-repo"
    init_repo(repo, {
        "Makefile": (b"all:\n\t@true\n", 0o644),
        "tools/a.sh": (b"#!/bin/sh\nexit 0\n", 0o755),
        "tools/gitless-source-manifest.py": ((ROOT / "tools/gitless-source-manifest.py").read_bytes(), 0o755),
    })
    source = tmp / f"{name}-source"
    manifest_path = tmp / f"{name}-manifest.json"
    manifest = helper.create(repo, source, manifest_path)
    return helper, repo, source, manifest_path, manifest


def normalizer_env(manifest_path: Path, tree: str) -> dict[str, str]:
    env = os.environ.copy()
    env["X64LENS_SOURCE_MANIFEST"] = str(manifest_path)
    env["X64LENS_CANDIDATE_TREE"] = tree
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def test_gitless_manifest_completeness(tmp: Path) -> int:
    _helper, _repo, source, manifest_path, manifest = create_gitless(tmp, "incomplete")
    bad = json.loads(json.dumps(manifest))
    bad["files"] = [x for x in bad["files"] if x["path"] != "tools/a.sh"]
    bad_path = tmp / "incomplete-bad.json"
    bad_path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
    cp = run([sys.executable, str(ROOT / "tools/normalize-tracked-permissions.py"), "--repo", str(source)], env=normalizer_env(bad_path, manifest["candidate_tree"]), expected=None)
    require(cp.returncode != 0 and b"does not derive its candidate tree" in cp.stderr, "incomplete Git-less manifest was accepted")
    return 1


def test_gitless_root_substitution_rollback(tmp: Path) -> int:
    _helper, _repo, source, manifest_path, manifest = create_gitless(tmp, "root-swap")
    script = source / "tools/a.sh"
    script.chmod(0o644)
    normalizer = module("p080_normalizer_gitless", ROOT / "tools/normalize-tracked-permissions.py")
    detached = tmp / "root-swap-detached"
    replacement = source
    def swap(_repo: Path) -> None:
        source.rename(detached)
        replacement.mkdir()
    normalizer._TEST_GITLESS_AFTER_MUTATION_HOOK = swap
    old_env = os.environ.copy()
    os.environ.update(normalizer_env(manifest_path, manifest["candidate_tree"]))
    try:
        try: normalizer.verify_gitless_source(source, manifest_path)
        except (normalizer.PermissionErrorContract, OSError): pass
        else: raise RegressionError("caller-visible Git-less root substitution was accepted")
        require(stat.S_IMODE((detached / "tools/a.sh").stat().st_mode) == 0o644, "Git-less root-substitution failure bypassed rollback")
    finally:
        normalizer._TEST_GITLESS_AFTER_MUTATION_HOOK = None
        os.environ.clear(); os.environ.update(old_env)
        if replacement.exists(): shutil.rmtree(replacement)
        if detached.exists(): detached.rename(source)
    return 1


def test_final_git_reauth_rollback(tmp: Path) -> int:
    repo = tmp / "git-reauth-repo"
    init_repo(repo, {"tool.sh": (b"#!/bin/sh\nexit 0\n", 0o755)})
    (repo / "tool.sh").chmod(0o644)
    normalizer = module("p080_normalizer_git", ROOT / "tools/normalize-tracked-permissions.py")
    original = normalizer.reauthenticate_repo
    calls = {"count": 0}
    def fail_final(binding: Any) -> None:
        calls["count"] += 1
        original(binding)
        if calls["count"] >= 2:
            raise normalizer.PermissionErrorContract("injected final Git reauthentication failure")
    normalizer.reauthenticate_repo = fail_final
    try:
        try: normalizer.normalize(repo)
        except normalizer.PermissionErrorContract: pass
        else: raise RegressionError("final Git reauthentication failure was accepted")
        require(stat.S_IMODE((repo / "tool.sh").stat().st_mode) == 0o644, "final Git reauthentication failure bypassed rollback")
    finally:
        normalizer.reauthenticate_repo = original
    return 1


def write_fake_docker(path: Path) -> None:
    path.write_text(r'''#!/usr/bin/env python3
import json,os,pathlib,sys
state=pathlib.Path(os.environ["P080_DOCKER_STATE"])
log=pathlib.Path(os.environ["P080_DOCKER_LOG"])
args=sys.argv[1:]
with log.open("a",encoding="utf-8") as h: h.write(json.dumps(args)+"\n")
data=json.loads(state.read_text())
if args[:2]==["image","inspect"]:
 ref=args[2]
 rec=data["refs"].get(ref)
 if rec is None: raise SystemExit(1)
 print(json.dumps([{"Id":rec["id"],"Config":{"Labels":{"org.x64lens.candidate-tree":rec["tree"]}}}]))
 raise SystemExit(0)
raise SystemExit(64)
''', encoding="utf-8")
    path.chmod(0o755)


def test_immutable_docker_authority(tmp: Path) -> int:
    fake = tmp / "docker"
    state = tmp / "docker-state.json"
    log = tmp / "docker.log"
    write_fake_docker(fake)
    tree1, tree2 = "1" * 40, "2" * 40
    id1, id2 = "sha256:" + "a" * 64, "sha256:" + "b" * 64
    state.write_text(json.dumps({"refs": {"x64lens:test": {"id": id1, "tree": tree1}, id1: {"id": id1, "tree": tree1}, id2: {"id": id2, "tree": tree2}}}), encoding="utf-8")
    log.write_text("", encoding="utf-8")
    context = tmp / "context"; context.mkdir()
    (context / "source-manifest.json").write_text("{}\n", encoding="utf-8")
    (context / "context-authority.json").write_text(json.dumps({"candidate_tree": tree1}) + "\n", encoding="utf-8")
    authority = tmp / "image-authority.json"
    env = os.environ.copy(); env["P080_DOCKER_STATE"] = str(state); env["P080_DOCKER_LOG"] = str(log)
    run([sys.executable, str(ROOT / "tools/docker-image-authority.py"), "record", "--path", str(authority), "--docker", str(fake), "--tag", "x64lens:test", "--candidate-tree", tree1, "--context-authority", str(context / "context-authority.json")], env=env)
    data = json.loads(state.read_text()); data["refs"]["x64lens:test"] = {"id": id2, "tree": tree2}; state.write_text(json.dumps(data), encoding="utf-8")
    run([sys.executable, str(ROOT / "tools/docker-image-authority.py"), "verify", "--path", str(authority), "--docker", str(fake)], env=env)
    entries = [json.loads(x) for x in log.read_text().splitlines()]
    require(entries[-1][2] == id1, "Docker authority verification re-resolved mutable tag")
    return 1


def test_parity_exec_build_surface() -> int:
    role = (ROOT / "tools/sprint12-role-property-environment-parity-smoke.py").read_text()
    dynamic = (ROOT / "tools/sprint12-dynamic-metadata-environment-parity-smoke.py").read_text()
    for text, label in ((role, "role/property"), (dynamic, "dynamic metadata")):
        require("/x64lens-build:rw,exec,nosuid,nodev" in text, f"{label} parity lacks executable build tmpfs")
        require("/x64lens-build/repo" in text, f"{label} parity does not build on executable tmpfs")
        require("/tmp/x64lens-role-build" not in text and "/tmp/x64lens-dynamic-build" not in text, f"{label} parity still builds on /tmp")
    return 1


def test_corrected_task_and_policy() -> tuple[int, int, int]:
    task = run([sys.executable, str(ROOT / "tools/sprint13-register-role-task-value-smoke.py")])
    require(b"unique_queries=60" in task.stdout and b"human_blind_claim=0" in task.stdout and b"qualified=3" in task.stdout, "corrected task-value gate did not run")
    policy = run([sys.executable, str(ROOT / "tools/sprint13-role-policy-smoke.py")])
    require(b"cells=9" in policy.stdout and b"private_runtime_accept=3" in policy.stdout, "LC-08B policy gate did not run")
    role = run([sys.executable, str(ROOT / "tools/sprint13-register-role-decision-smoke.py")])
    require(b"negative_oracles=8" in role.stdout, "complete ABI negative oracle was not promoted")
    return 1, 1, 1


def test_make_immutable_id_paths() -> int:
    make = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in ("docker-test:", "docker-validation-smoke:", "sprint12-role-property-environment-parity-smoke:", "sprint12-dynamic-metadata-environment-parity-smoke:"):
        start = make.index(target)
        end = make.find("\n\n", start)
        block = make[start:end if end >= 0 else None]
        require("docker-image-authority.py" in block and "image_id" in block, f"{target} does not consume immutable image authority")
    return 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p079-corrective-") as raw:
        tmp = Path(raw)
        partial_apply, partial_rollback = test_partial_patch_recovery(tmp)
        manifest_complete = test_gitless_manifest_completeness(tmp)
        root_rollback = test_gitless_root_substitution_rollback(tmp)
        git_rollback = test_final_git_reauth_rollback(tmp)
        immutable_image = test_immutable_docker_authority(tmp)
    parity_exec = test_parity_exec_build_surface()
    task_v2, role_policy, abi_oracle = test_corrected_task_and_policy()
    make_ids = test_make_immutable_id_paths()
    print(
        "patch079-corrective-regression-smoke: ok "
        f"partial_apply_recovery={partial_apply} partial_rollback_recovery={partial_rollback} "
        f"gitless_manifest_complete={manifest_complete} gitless_root_rollback={root_rollback} "
        f"final_git_reauth_rollback={git_rollback} docker_immutable_image={immutable_image} "
        f"parity_exec_build={parity_exec} task_value_v2={task_v2} role_policy={role_policy} "
        f"complete_abi_oracle={abi_oracle} make_immutable_id_paths={make_ids}"
    )
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (RegressionError, OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"patch079-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
