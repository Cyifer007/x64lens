#!/usr/bin/env python3
"""Exercise every acceptance blocker promoted from the Patch 078 review.

The regression is intentionally bounded and non-destructive.  It uses temporary
Git repositories, staged Git-object source authorities, fake Docker transport,
and injected post-effect failures to distinguish the reviewed defects without
requiring a Docker daemon or NASM.  Product/runtime behavior is not inferred
from this tooling gate.
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
import tarfile
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class RegressionError(RuntimeError):
    """Raised when a promoted Patch 078 finding is not discriminated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    expected: int | None = 0,
) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        input=input_bytes,
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


def git(repo: Path, *args: str, input_bytes: bytes | None = None) -> str:
    return run(["git", "-C", str(repo), *args], input_bytes=input_bytes).stdout.decode().strip()


def init_repo(path: Path, files: dict[str, tuple[bytes, int]]) -> tuple[str, str]:
    path.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=path)
    run(["git", "config", "user.email", "x64lens-regression@example.invalid"], cwd=path)
    run(["git", "config", "user.name", "x64lens regression"], cwd=path)
    for raw, (payload, mode) in files.items():
        target = path / raw
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        target.chmod(mode)
    run(["git", "add", "-A"], cwd=path)
    run(["git", "commit", "-q", "-m", "base"], cwd=path)
    return git(path, "rev-parse", "HEAD"), git(path, "rev-parse", "HEAD^{tree}")


def git_object(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def make_recovery_authority(root: Path) -> tuple[Path, Path]:
    payload = b"all:\n\t@echo recovery fixture\n"
    oid = git_object(payload)
    tree_payload = b"100644 Makefile\0" + bytes.fromhex(oid)
    tree = hashlib.sha1(b"tree " + str(len(tree_payload)).encode("ascii") + b"\0" + tree_payload).hexdigest()
    manifest = {
        "schema_id": "x64lens-candidate-source-tree-v1",
        "candidate_tree": tree,
        "directories": [],
        "files": [
            {
                "path": "Makefile",
                "type": "blob",
                "git_oid": oid,
                "git_mode": "100644",
                "mode": "0644",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        ],
    }
    manifest_path = root / "source-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o444)
    archive_path = root / "source.tar"
    source = root / "Makefile"
    source.write_bytes(payload)
    source.chmod(0o644)
    with tarfile.open(archive_path, "w", format=tarfile.PAX_FORMAT) as archive:
        info = archive.gettarinfo(str(source), arcname="Makefile")
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mtime = 0
        info.mode = 0o644
        with source.open("rb") as handle:
            archive.addfile(info, handle)
    archive_path.chmod(0o444)
    source.unlink()
    return archive_path, manifest_path


def test_gitless_custody_and_snapshot(tmp: Path) -> tuple[int, int, int, int]:
    helper = load_module("p079_gitless_regression", ROOT / "tools/gitless-source-manifest.py")
    repo = tmp / "gitless-repo"
    init_repo(
        repo,
        {
            "Dockerfile": (b"FROM scratch\nCOPY source/ /work/\n", 0o644),
            "Makefile": (b"all:\n\t@true\n", 0o644),
            "nested/tool.sh": (b"#!/bin/sh\nexit 0\n", 0o755),
        },
    )
    source = tmp / "gitless-source"
    manifest_path = tmp / "gitless-source-manifest.json"
    manifest = helper.create(repo, source, manifest_path)
    helper.verify(source, manifest)
    require(stat.S_IMODE(source.stat().st_mode) == 0o755, "Git-less root mode is not canonical")
    require(stat.S_IMODE((source / "nested").stat().st_mode) == 0o755, "Git-less directory mode is not canonical")

    (source / "nested").chmod(0o700)
    try:
        helper.verify(source, manifest)
    except helper.SourceError:
        directory_mode_rejected = 1
    else:
        raise RegressionError("Git-less directory mode drift was accepted")
    (source / "nested").chmod(0o755)

    moved = tmp / "gitless-source-real"
    source.rename(moved)
    source.symlink_to(moved, target_is_directory=True)
    try:
        helper.verify(source, manifest)
    except (helper.SourceError, OSError):
        symlink_root_rejected = 1
    else:
        raise RegressionError("Git-less symlink root was accepted")
    source.unlink()
    moved.rename(source)

    alias = tmp / "source-hardlink-alias"
    os.link(source / "Makefile", alias)
    try:
        helper.verify(source, manifest)
    except helper.SourceError:
        hardlink_rejected = 1
    else:
        raise RegressionError("Git-less hard-link topology was accepted")
    alias.unlink()
    helper.verify(source, manifest)

    # Freeze source from one index snapshot, mutate the index, then require the
    # transport Dockerfile to remain byte-identical to the already materialized
    # source snapshot.
    split_repo = tmp / "split-repo"
    init_repo(
        split_repo,
        {
            "Dockerfile": (b"FROM scratch\nCOPY source/ /work/\n", 0o644),
            "Makefile": (b"all:\n\t@true\n", 0o644),
        },
    )
    frozen_tree = git(split_repo, "write-tree")
    original_create = helper.create

    def create_then_mutate(repo_path: Path, source_root: Path, source_manifest: Path) -> dict[str, Any]:
        value = original_create(repo_path, source_root, source_manifest)
        mutated = b"FROM scratch\n# post-freeze index mutation\n"
        oid = git(split_repo, "hash-object", "-w", "--stdin", input_bytes=mutated)
        git(split_repo, "update-index", "--cacheinfo", "100644", oid, "Dockerfile")
        return value

    helper.create = create_then_mutate
    context = tmp / "split-context"
    authority = helper.create_context(split_repo, context)
    helper.create = original_create
    require(authority["candidate_tree"] == frozen_tree, "Docker source snapshot was not frozen")
    require(
        (context / "source/Dockerfile").read_bytes() == (context / "Dockerfile.transport").read_bytes(),
        "Docker transport file came from a second index snapshot",
    )
    return directory_mode_rejected, symlink_root_rejected, hardlink_rejected, 1


def test_gitless_normalizer(tmp: Path) -> int:
    helper = load_module("p079_gitless_normalizer_source", ROOT / "tools/gitless-source-manifest.py")
    repo = tmp / "normalize-repo"
    init_repo(
        repo,
        {
            "Dockerfile": (b"FROM scratch\nCOPY source/ /work/\n", 0o644),
            "Makefile": (b"all:\n\t@true\n", 0o644),
            "tools/example.sh": (b"#!/bin/sh\nexit 0\n", 0o755),
            "tools/gitless-source-manifest.py": (
                (ROOT / "tools/gitless-source-manifest.py").read_bytes(),
                0o755,
            ),
        },
    )
    source = tmp / "normalize-source"
    manifest_path = tmp / "normalize-manifest.json"
    manifest = helper.create(repo, source, manifest_path)
    (source / "Makefile").chmod(0o600)
    generated = source / "generated-untracked.tmp"
    generated.write_text("must remain untouched\n", encoding="utf-8")
    generated.chmod(0o600)
    env = os.environ.copy()
    env["X64LENS_SOURCE_MANIFEST"] = str(manifest_path)
    env["X64LENS_CANDIDATE_TREE"] = manifest["candidate_tree"]
    cp = run(
        [sys.executable, str(ROOT / "tools/normalize-tracked-permissions.py"), "--repo", str(source)],
        env=env,
    )
    require(b"gitless_verified=1" in cp.stdout, "Git-less permission path did not run")
    require(stat.S_IMODE((source / "Makefile").stat().st_mode) == 0o644, "tracked Git-less mode was not normalized")
    require(generated.read_text(encoding="utf-8") == "must remain untouched\n", "generated member was modified")
    require(stat.S_IMODE(generated.stat().st_mode) == 0o600, "generated member mode was modified")
    return 1


def test_patch_effect_recovery(tmp: Path) -> tuple[int, int]:
    helper = load_module("p079_patch_transaction_regression", ROOT / "tools/git-patch-transaction.py")
    repo = tmp / "patch-repo"
    base_head, base_tree = init_repo(repo, {"payload.txt": (b"base\n", 0o644)})
    (repo / "payload.txt").write_bytes(b"candidate\n")
    run(["git", "add", "payload.txt"], cwd=repo)
    candidate_tree = git(repo, "write-tree")
    patch = run(["git", "diff", "--cached", "--binary", "--full-index"], cwd=repo).stdout
    run(["git", "reset", "--hard", "HEAD"], cwd=repo)
    raw = patch
    handle = helper.open_repo(repo)
    original_git_apply = helper.git_apply
    try:
        def forward_effect_then_raise(repo_handle: Any, patch_bytes: bytes, *, reverse: bool, check_only: bool) -> None:
            original_git_apply(repo_handle, patch_bytes, reverse=reverse, check_only=check_only)
            if not check_only and not reverse:
                raise RuntimeError("injected forward post-effect failure")

        helper.git_apply = forward_effect_then_raise
        try:
            helper.apply_patch(
                handle,
                raw,
                branch="main",
                base_head=base_head,
                base_tree=base_tree,
                candidate_tree=candidate_tree,
            )
        except helper.TransactionError as exc:
            require("inverse recovery restored" in str(exc), "forward post-effect recovery was not reported")
        else:
            raise RegressionError("forward post-effect failure was accepted")
        require(git(repo, "write-tree") == base_tree, "forward post-effect failure left the patch applied")

        helper.git_apply = original_git_apply
        helper.apply_patch(
            handle,
            raw,
            branch="main",
            base_head=base_head,
            base_tree=base_tree,
            candidate_tree=candidate_tree,
        )
        require(git(repo, "write-tree") == candidate_tree, "normal patch application did not reach candidate")

        def reverse_effect_then_raise(repo_handle: Any, patch_bytes: bytes, *, reverse: bool, check_only: bool) -> None:
            original_git_apply(repo_handle, patch_bytes, reverse=reverse, check_only=check_only)
            if not check_only and reverse:
                raise RuntimeError("injected reverse post-effect failure")

        helper.git_apply = reverse_effect_then_raise
        try:
            helper.rollback_patch(
                handle,
                raw,
                branch="main",
                base_head=base_head,
                base_tree=base_tree,
                candidate_tree=candidate_tree,
            )
        except helper.TransactionError as exc:
            require("forward recovery restored" in str(exc), "reverse post-effect recovery was not reported")
        else:
            raise RegressionError("reverse post-effect failure was accepted")
        require(git(repo, "write-tree") == candidate_tree, "reverse post-effect failure lost the candidate")
    finally:
        helper.git_apply = original_git_apply
        helper.close_repo(handle)
    return 1, 1


def test_recovery_foreign_descendant(tmp: Path) -> int:
    helper = load_module("p079_recovery_regression", ROOT / "tools/recover-candidate-source.py")
    authority_root = tmp / "recovery-authority"
    authority_root.mkdir()
    archive, manifest = make_recovery_authority(authority_root)
    destination = tmp / "recovered-source"
    held: dict[str, int] = {"fd": -1}

    def replace_descendant(_parent_fd: int, _name: str, root_fd: int) -> None:
        os.unlink("Makefile", dir_fd=root_fd)
        fd = os.open(
            "Makefile",
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC,
            0o644,
            dir_fd=root_fd,
        )
        os.write(fd, b"foreign descendant must survive failed recovery\n")
        os.fsync(fd)
        held["fd"] = fd

    helper._TEST_AFTER_PUBLISH_HOOK = replace_descendant
    try:
        try:
            helper.recover(archive, manifest, destination)
        except (helper.RecoveryError, OSError):
            pass
        else:
            raise RegressionError("recovery accepted a foreign descendant replacement")
        require(held["fd"] >= 0, "foreign descendant hook did not run")
        metadata = os.fstat(held["fd"])
        require(metadata.st_nlink == 1, "recovery cleanup deleted the foreign descendant")
        os.lseek(held["fd"], 0, os.SEEK_SET)
        require(b"foreign descendant" in os.read(held["fd"], 4096), "foreign descendant bytes changed")
        residues = [item for item in tmp.iterdir() if item.name.startswith(".x64lens-recovery-")]
        require(residues, "foreign recovery residue was not preserved for inspection")
    finally:
        helper._TEST_AFTER_PUBLISH_HOOK = None
        if held["fd"] >= 0:
            os.close(held["fd"])
    return 1


def test_parity_independent_build_and_mounts(tmp: Path) -> tuple[int, int]:
    parity = load_module("p079_role_parity_regression", ROOT / "tools/sprint12-role-property-environment-parity-smoke.py")
    heldout = tmp / "heldout"
    output = tmp / "container-output"
    native = tmp / "native-plane"
    heldout.mkdir()
    output.mkdir()
    native.mkdir()
    tree = "1" * 40
    image_id = "sha256:" + "2" * 64
    command = parity.build_container_command(
        docker="docker",
        image_id=image_id,
        candidate_tree=tree,
        heldout=heldout,
        container_write_root=output,
    )
    policy = parity.validate_container_mount_policy(
        command,
        native_result=native,
        heldout=heldout,
        container_write_root=output,
    )
    joined = "\n".join(command)
    require(policy["mount_count"] == 2 and policy["writable_mount_count"] == 1, "parity mount denominator changed")
    require(str(native) not in joined and "/inputs" not in joined and "/source" not in joined, "parity command exposes host source/native inputs")
    require(image_id in command and "container-image-build" in joined, "parity command lacks immutable image/build origin")
    require("make clean; make; make build/tests/role-property-fact-probe" in joined, "container plane does not build independently")
    return 1, 1


def write_fake_docker(path: Path) -> None:
    script = """#!/usr/bin/env python3
import json
import os
import pathlib
import subprocess
import sys

state_path = pathlib.Path(os.environ["FAKE_DOCKER_STATE"])
log_path = pathlib.Path(os.environ["FAKE_DOCKER_LOG"])
log_path.parent.mkdir(parents=True, exist_ok=True)
with log_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\\n")
args = sys.argv[1:]
if args and args[0] == "info":
    raise SystemExit(0)
if args and args[0] == "build":
    if os.environ.get("FAKE_DOCKER_BUILD_FAIL") == "1":
        raise SystemExit(42)
    context = pathlib.Path(args[-1])
    authority = json.loads((context / "context-authority.json").read_text())
    labels = {}
    for index, item in enumerate(args):
        if item == "--label" and index + 1 < len(args):
            key, value = args[index + 1].split("=", 1)
            labels[key] = value
    state = {
        "tree": authority["candidate_tree"],
        "context": str(context),
        "image_id": "sha256:" + "7" * 64,
        "labels": labels,
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    raise SystemExit(0)
if len(args) >= 2 and args[:2] == ["image", "inspect"]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    labels = state.get("labels", {})
    labels.setdefault("org.x64lens.candidate-tree", state["tree"])
    print(json.dumps([{"Id": state["image_id"], "Config": {"Labels": labels}}]))
    raise SystemExit(0)
if args and args[0] == "run":
    state = json.loads(state_path.read_text(encoding="utf-8"))
    context = pathlib.Path(state["context"])
    cp = subprocess.run([
        sys.executable,
        str(context / "source/tools/gitless-source-manifest.py"),
        "verify",
        "--root",
        str(context / "source"),
        "--manifest",
        str(context / "source-manifest.json"),
    ])
    raise SystemExit(cp.returncode)
raise SystemExit(64)
"""
    path.write_text(script, encoding="utf-8")
    path.chmod(0o755)


def materialize_regression_repo(source: Path, destination: Path) -> None:
    """Create an isolated Git authority even when the caller is Git-less."""
    ignored = shutil.ignore_patterns(
        ".git", ".local", ".env.local", "build", "tests/bin", "tests/results",
        "__pycache__", "*.pyc", "*.o", "*.zip", "*.tar", "*.tar.gz",
    )
    shutil.copytree(source, destination, ignore=ignored, symlinks=False)
    for cache in destination.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    run(["git", "init", "-q", "-b", "main"], cwd=destination)
    run(["git", "config", "user.email", "x64lens-regression@example.invalid"], cwd=destination)
    run(["git", "config", "user.name", "x64lens regression"], cwd=destination)
    run(["git", "add", "-A"], cwd=destination)
    run(["git", "commit", "-q", "-m", "exact source"], cwd=destination)


def test_make_level_docker_caller(tmp: Path) -> tuple[int, int]:
    fake = tmp / "fake-docker"
    state = tmp / "fake-state.json"
    log = tmp / "fake-docker.log"
    authority_path = tmp / "isolated-docker-image-authority.json"
    source_repo = tmp / "isolated-source-repo"
    materialize_regression_repo(ROOT, source_repo)
    write_fake_docker(fake)

    default_authority = ROOT / ".local/docker-image-authority.json"
    before_default = default_authority.read_bytes() if default_authority.is_file() else None
    env = os.environ.copy()
    env.update(
        {
            "DOCKER": str(fake),
            "DOCKER_IMAGE": "x64lens:p079-regression",
            "DOCKER_IMAGE_AUTHORITY": str(authority_path),
            "FAKE_DOCKER_STATE": str(state),
            "FAKE_DOCKER_LOG": str(log),
            "TMPDIR": str(tmp),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    cp = run(["make", "--no-print-directory", "docker-build"], cwd=source_repo, env=env)
    require(b"docker-build: ok" in cp.stdout, "Make-level Docker build did not complete")
    require(authority_path.is_file(), "isolated Docker authority was not published")
    entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    require(any(item and item[0] == "build" for item in entries), "fake Docker did not receive build")
    require(any(item and item[0] == "run" for item in entries), "fake Docker did not receive source verification")
    labels = json.loads(state.read_text(encoding="utf-8"))["labels"]
    require(
        set(labels) >= {
            "org.x64lens.candidate-tree",
            "org.x64lens.context-authority-sha256",
            "org.x64lens.source-manifest-sha256",
        },
        "Make-level Docker build omitted immutable provenance labels",
    )

    after_default = default_authority.read_bytes() if default_authority.is_file() else None
    require(after_default == before_default, "regression overwrote the caller's Docker image authority")

    log.write_text("", encoding="utf-8")
    fail_env = env.copy()
    fail_env["FAKE_DOCKER_BUILD_FAIL"] = "1"
    failed = run(["make", "--no-print-directory", "docker-build"], cwd=source_repo, env=fail_env, expected=None)
    require(failed.returncode != 0, "Make-level Docker build masked the injected build failure")
    failed_entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    build_index = next(index for index, item in enumerate(failed_entries) if item and item[0] == "build")
    require(
        not any(item and item[0] in {"run", "image"} for item in failed_entries[build_index + 1 :]),
        "Make-level Docker recipe continued to a stale image after build failure",
    )
    require(
        (default_authority.read_bytes() if default_authority.is_file() else None) == before_default,
        "failed regression run overwrote the caller's Docker image authority",
    )
    return 1, 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p078-corrective-") as raw:
        tmp = Path(raw)
        gitless_directory, gitless_root, gitless_hardlink, split_snapshot = test_gitless_custody_and_snapshot(tmp)
        gitless_normalizer = test_gitless_normalizer(tmp)
        patch_apply, patch_rollback = test_patch_effect_recovery(tmp)
        recovery_foreign = test_recovery_foreign_descendant(tmp)
        parity_build, parity_mounts = test_parity_independent_build_and_mounts(tmp)
        make_context, make_failfast = test_make_level_docker_caller(tmp)
    print(
        "patch078-corrective-regression-smoke: ok "
        f"docker_make_context={make_context} docker_failfast={make_failfast} "
        f"gitless_directory_modes={gitless_directory} gitless_root_symlink={gitless_root} "
        f"gitless_hardlinks={gitless_hardlink} gitless_normalizer={gitless_normalizer} "
        f"docker_single_snapshot={split_snapshot} parity_independent_build={parity_build} "
        f"parity_mount_isolation={parity_mounts} patch_apply_recovery={patch_apply} "
        f"patch_rollback_recovery={patch_rollback} recovery_foreign_descendant={recovery_foreign}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"patch078-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
