#!/usr/bin/env python3
"""Promote the Patch 076 review findings into durable regressions.

The regression is intentionally adversarial and non-documentation-only.  It
covers pinned patch bytes, descriptor-bound source recovery and rollback,
permission rollback after unrelated directory churn, custody quarantine,
Git-less parity source authority, no-replace parity publication, exact external
comparator exits, generalized dynamic-string labels, and deterministic private
search failure-prefix semantics.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
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

ROOT = Path(__file__).resolve().parent.parent


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


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=timeout,
    )


def init_git_repo(root: Path) -> None:
    require(run(["git", "init", "-q"], cwd=root).returncode == 0, "git init failed")
    require(run(["git", "config", "user.email", "test@example.invalid"], cwd=root).returncode == 0,
            "git config failed")
    require(run(["git", "config", "user.name", "test"], cwd=root).returncode == 0,
            "git config failed")


def git_text(repo: Path, *args: str) -> str:
    cp = run(["git", *args], cwd=repo)
    require(cp.returncode == 0, f"git {' '.join(args)} failed: {cp.stderr.decode(errors='replace')}")
    return cp.stdout.decode().strip()


def patch_transaction_tests() -> tuple[int, int, int]:
    helper = ROOT / "tools/git-patch-transaction.py"
    with tempfile.TemporaryDirectory(prefix="x64lens-p076-patch-transaction-") as raw:
        repo = Path(raw) / "repo"
        repo.mkdir()
        init_git_repo(repo)
        target = repo / "value.txt"
        target.write_text("base\n", encoding="utf-8")
        run(["git", "add", "value.txt"], cwd=repo)
        run(["git", "commit", "-qm", "base"], cwd=repo)
        base_head = git_text(repo, "rev-parse", "HEAD")
        base_tree = git_text(repo, "rev-parse", "HEAD^{tree}")

        target.write_text("good\n", encoding="utf-8")
        good = run(["git", "diff", "--binary", "--", "value.txt"], cwd=repo).stdout
        run(["git", "add", "value.txt"], cwd=repo)
        candidate_tree = git_text(repo, "write-tree")
        run(["git", "reset", "--hard", "-q", "HEAD"], cwd=repo)

        target.write_text("evil\n", encoding="utf-8")
        evil = run(["git", "diff", "--binary", "--", "value.txt"], cwd=repo).stdout
        run(["git", "reset", "--hard", "-q", "HEAD"], cwd=repo)

        patch = Path(raw) / "candidate.patch"
        evil_patch = Path(raw) / "evil.patch"
        patch.write_bytes(good)
        evil_patch.write_bytes(evil)
        digest = hashlib.sha256(good).hexdigest()
        common = [
            "--repo", str(repo),
            "--patch", str(patch),
            "--patch-sha256", digest,
            "--branch", "master",
            "--base-head", base_head,
            "--base-tree", base_tree,
            "--candidate-tree", candidate_tree,
        ]
        env = dict(os.environ)
        env["X64LENS_PATCH_TRANSACTION_AFTER_CHECK_HOOK"] = (
            f"cp -- {shlex_quote(evil_patch)} {shlex_quote(patch)}"
        )
        applied = run([sys.executable, str(helper), "apply", *common], cwd=repo, env=env)
        require(applied.returncode == 0, f"pinned apply failed: {applied.stderr.decode(errors='replace')}")
        require(target.read_text() == "good\n" and git_text(repo, "write-tree") == candidate_tree,
                "apply consumed replaced patch pathname")
        apply_ok = 1

        patch.write_bytes(good)
        env = dict(os.environ)
        env["X64LENS_PATCH_TRANSACTION_AFTER_REVERSE_CHECK_HOOK"] = (
            f"cp -- {shlex_quote(evil_patch)} {shlex_quote(patch)}"
        )
        rolled = run([sys.executable, str(helper), "rollback", *common], cwd=repo, env=env)
        require(rolled.returncode == 0, f"pinned rollback failed: {rolled.stderr.decode(errors='replace')}")
        require(target.read_text() == "base\n" and not git_text(repo, "status", "--porcelain=v1", "--untracked-files=all"),
                "rollback consumed replaced patch pathname or left residue")
        rollback_ok = 1

        wrong_digest = list(common)
        digest_index = wrong_digest.index("--patch-sha256") + 1
        wrong_digest[digest_index] = "0" * 64
        rejected = run([sys.executable, str(helper), "apply", *wrong_digest], cwd=repo)
        require(rejected.returncode != 0, "patch transaction accepted the wrong patch digest")
        require(b"patch SHA-256 mismatch" in rejected.stderr,
                f"wrong-digest regression did not reach digest authentication: {rejected.stderr!r}")
        hash_ok = 1
    return apply_ok, rollback_ok, hash_ok


def shlex_quote(path: Path) -> str:
    import shlex
    return shlex.quote(str(path))


def tiny_source_inputs(recovery: Any, root: Path, payload: bytes = b"owned\n") -> tuple[Path, Path]:
    oid = recovery.git_object(b"blob", payload)
    tree_payload = b"100644 a\0" + bytes.fromhex(oid)
    tree = recovery.git_object(b"tree", tree_payload)
    manifest = {
        "schema_id": "x64lens-candidate-source-tree-v1",
        "candidate_tree": tree,
        "directories": [],
        "files": [{
            "path": "a",
            "type": "blob",
            "git_oid": oid,
            "git_mode": "100644",
            "mode": "0644",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }],
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    archive_path = root / "source.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        info = tarfile.TarInfo("a")
        info.size = len(payload)
        info.mode = 0o644
        info.uid = info.gid = info.mtime = 0
        archive.addfile(info, io.BytesIO(payload))
    return archive_path, manifest_path


def recovery_tests() -> tuple[int, int, int, int, int]:
    recovery = load("p077_recovery", ROOT / "tools/recover-candidate-source.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p076-recovery-") as raw:
        root = Path(raw)
        archive, manifest = tiny_source_inputs(recovery, root)

        outside = root / "outside"
        outside.mkdir()
        linked = root / "linked-parent"
        linked.symlink_to(outside, target_is_directory=True)
        symlink_destination = linked / "candidate"
        try:
            recovery.recover(archive, manifest, symlink_destination)
        except (recovery.RecoveryError, OSError):
            pass
        else:
            raise Error("recovery accepted a symlinked destination ancestor")
        require(not (outside / "candidate").exists(), "recovery wrote through symlinked ancestor")
        symlink_ok = 1

        raced_destination = root / "publish-race"
        foreign_marker = root / "foreign-marker-reference"
        def publish_race(parent_fd: int, _stage: str, destination_name: str) -> None:
            os.mkdir(destination_name, 0o700, dir_fd=parent_fd)
            fd = os.open("foreign", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600,
                         dir_fd=os.open(destination_name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent_fd))
            os.write(fd, b"foreign\n")
            os.close(fd)
        recovery._TEST_BEFORE_PUBLISH_HOOK = publish_race
        try:
            try:
                recovery.recover(archive, manifest, raced_destination)
            except (recovery.RecoveryError, OSError):
                pass
            else:
                raise Error("recovery overwrote a raced destination")
        finally:
            recovery._TEST_BEFORE_PUBLISH_HOOK = None
        require((raced_destination / "foreign").read_bytes() == b"foreign\n",
                "recovery publication removed the raced foreign destination")
        publish_ok = 1

        file_destination = root / "file-race"
        file_hook_fired = False
        def file_race(parent_fd: int, stage_name: str, _root_fd: int) -> None:
            nonlocal file_hook_fired
            if file_hook_fired:
                return
            file_hook_fired = True
            stage_path = Path(f"/proc/self/fd/{parent_fd}") / stage_name
            (stage_path / "a").unlink()
            (stage_path / "a").write_bytes(b"foreign\n")
            (stage_path / "a").chmod(0o644)
        recovery._TEST_AFTER_INITIAL_VERIFY_HOOK = file_race
        try:
            try:
                recovery.recover(archive, manifest, file_destination)
            except (recovery.RecoveryError, OSError):
                pass
            else:
                raise Error("recovery accepted a post-verification file replacement")
        finally:
            recovery._TEST_AFTER_INITIAL_VERIFY_HOOK = None
        require(file_hook_fired and not file_destination.exists(), "file replacement was not rejected")
        file_ok = 1

        root_destination = root / "root-race"
        displaced_name = "owned-displaced"
        root_hook_fired = False
        def root_race(parent_fd: int, stage_name: str, _root_fd: int) -> None:
            nonlocal root_hook_fired
            if root_hook_fired:
                return
            root_hook_fired = True
            os.rename(stage_name, displaced_name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            os.mkdir(stage_name, 0o700, dir_fd=parent_fd)
            foreign_fd = os.open(stage_name, os.O_RDONLY | os.O_DIRECTORY, dir_fd=parent_fd)
            try:
                marker = os.open("foreign", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=foreign_fd)
                os.write(marker, b"foreign\n")
                os.close(marker)
            finally:
                os.close(foreign_fd)
        recovery._TEST_AFTER_INITIAL_VERIFY_HOOK = root_race
        try:
            try:
                recovery.recover(archive, manifest, root_destination)
            except (recovery.RecoveryError, OSError):
                pass
            else:
                raise Error("recovery accepted a post-verification root replacement")
        finally:
            recovery._TEST_AFTER_INITIAL_VERIFY_HOOK = None
        quarantines = list(root.glob(".x64lens-recovery-quarantine.*"))
        require(root_hook_fired and (root / displaced_name / "a").read_bytes() == b"owned\n",
                "displaced owned source was not preserved")
        require(any((item / "foreign").is_file() for item in quarantines),
                "foreign replacement was not preserved under quarantine")
        root_ok = 1

        good_destination = root / "success"
        tree, directories, files, published = recovery.recover(archive, manifest, good_destination)
        require(published == good_destination and (good_destination / "a").read_bytes() == b"owned\n",
                "valid descriptor-bound recovery failed")
        require(len(tree) == 40 and directories == 0 and files == 1, "valid recovery identity changed")
        success_ok = 1
    return symlink_ok, publish_ok, file_ok, root_ok, success_ok


def normalizer_rollback_test() -> int:
    module = load("p077_normalizer", ROOT / "tools/normalize-tracked-permissions.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p076-normalizer-") as raw:
        repo = Path(raw)
        init_git_repo(repo)
        (repo / "a").write_text("tracked\n", encoding="utf-8")
        (repo / "a").chmod(0o644)
        run(["git", "add", "a"], cwd=repo)
        repo.chmod(0o700)
        real_fchmod = module.os.fchmod
        fired = False
        def mutate_membership(fd: int, mode: int) -> None:
            nonlocal fired
            real_fchmod(fd, mode)
            if not fired and mode == 0o755:
                fired = True
                os.mkdir("foreign-child", 0o700, dir_fd=fd)
        module.os.fchmod = mutate_membership
        try:
            try:
                module.normalize(repo)
            except module.PermissionErrorContract:
                pass
            else:
                raise Error("normalizer accepted post-preflight directory churn")
        finally:
            module.os.fchmod = real_fchmod
        require(fired and stat.S_IMODE(repo.stat().st_mode) == 0o700,
                "normalizer failed to restore the retained directory mode")
        require((repo / "foreign-child").is_dir(), "normalizer removed unrelated membership")
    return 1


def custody_tests() -> tuple[int, int]:
    module = load("p077_custody", ROOT / "tools/verify-delivery-custody.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p076-custody-") as raw:
        parent = Path(raw) / "parent"
        parent.mkdir()
        root = parent / "tree"
        root.mkdir(mode=0o755)
        (root / "payload").write_text("x", encoding="utf-8")
        (root / "payload").chmod(0o644)
        manifest = root / "manifest.json"
        injected = False
        foreign_name: str | None = None
        def substitute(parent_fd: int, quarantine: str, _fd: int, _label: str) -> None:
            nonlocal injected, foreign_name
            if injected:
                return
            injected = True
            foreign_name = quarantine
            os.unlink(quarantine, dir_fd=parent_fd)
            fd = os.open(quarantine, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
            try:
                os.write(fd, b"foreign\n")
            finally:
                os.close(fd)
            module._TEST_AFTER_UNLINK_QUARANTINE_RENAME_HOOK = None
        module._TEST_AFTER_UNLINK_QUARANTINE_RENAME_HOOK = substitute
        try:
            try:
                module.create(root, manifest, "test")
            except (module.CustodyError, OSError):
                pass
            else:
                raise Error("custody cleanup accepted a quarantine substitution")
        finally:
            module._TEST_AFTER_UNLINK_QUARANTINE_RENAME_HOOK = None
        require(injected and foreign_name is not None and (root / foreign_name).read_bytes() == b"foreign\n",
                "custody cleanup deleted the foreign replacement")
        require(not manifest.exists(), "custody failure left a published manifest")
        substitution_ok = 1

    with tempfile.TemporaryDirectory(prefix="x64lens-p076-custody-ancestor-") as raw:
        grandparent = Path(raw) / "grandparent"
        parent = grandparent / "parent"
        root = parent / "tree"
        root.mkdir(parents=True, mode=0o755)
        (root / "payload").write_text("x", encoding="utf-8")
        (root / "payload").chmod(0o644)
        manifest = root / "manifest.json"
        fired = False
        def churn(_root: Path) -> None:
            nonlocal fired
            if fired:
                return
            fired = True
            (parent / "unrelated-directory").mkdir()
        module._TEST_AFTER_TREE_SCAN_HOOK = churn
        try:
            module.create(root, manifest, "test")
            module.verify(root, manifest)
        finally:
            module._TEST_AFTER_TREE_SCAN_HOOK = None
        require(fired and manifest.is_file(), "unrelated ancestor churn falsely rejected custody")
        ancestor_ok = 1
    return substitution_ok, ancestor_ok


def search_contract_test() -> int:
    module = load("p077_search", ROOT / "tools/sprint12-search-path-matrix-smoke.py")
    module.load_authority(ROOT / "benchmarks/task-definitions/sprint12-search-path-private-evidence-v1.json")
    expected = {
        "missing_strtab": (1, 1, module.UNKNOWN, module.ABSENT, 0, 0),
        "missing_strsz": (1, 1, module.ABSENT, module.UNKNOWN, 0, 0),
        "offset_equal_strsz": (1, 1, module.UNKNOWN, module.ABSENT, 0, 0),
        "unterminated_value": (1, 1, module.ABSENT, module.UNKNOWN, 0, 0),
        "unmapped_strtab": (1, 1, module.UNKNOWN, module.ABSENT, 0, 0),
        "duplicate_strtab": (0, 0, module.UNKNOWN, module.UNKNOWN, 0, 0),
        "duplicate_strsz": (0, 0, module.UNKNOWN, module.UNKNOWN, 0, 0),
        "duplicate_dynamic": (1, 0, module.UNKNOWN, module.UNKNOWN, 0, 0),
        "path_bytes_4097": (1, 1, module.UNKNOWN, module.ABSENT, 0, 0),
        "aggregate_bytes_4097": (2, 1, module.UNKNOWN, module.UNKNOWN, 1, 2048),
        "strtab_scan_cap": (1, 1, module.UNKNOWN, module.ABSENT, 0, 0),
    }
    cases = {case.name: case for case in module.CASES}
    for name, row in expected.items():
        facts = module.expected(cases[name], module.build(cases[name]))
        observed = (
            facts["carrier_count"],
            facts["table_complete"],
            facts["rpath_state"],
            facts["runpath_state"],
            facts["search_record_count"],
            facts["search_bytes_used"],
        )
        require(observed == row, f"private failure-prefix contract changed: {name}: {observed} != {row}")
    return len(expected)


def readelf_exit_tests() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p076-readelf-") as raw:
        wrapper = Path(raw) / "readelf"
        wrapper.write_text("#!/usr/bin/env bash\n/usr/bin/readelf \"$@\"\nexit 17\n", encoding="utf-8")
        wrapper.chmod(0o755)
        search = run([
            sys.executable,
            str(ROOT / "tools/sprint12-search-path-matrix-smoke.py"),
            "--authority", str(ROOT / "benchmarks/task-definitions/sprint12-search-path-private-evidence-v1.json"),
            "--readelf", str(wrapper),
            "--oracle-only",
        ])
        textrel = run([
            sys.executable,
            str(ROOT / "tools/sprint12-textrel-matrix-smoke.py"),
            "--authority", str(ROOT / "benchmarks/task-definitions/sprint12-textrel-private-evidence-v1.json"),
            "--readelf", str(wrapper),
            "--oracle-only",
        ])
        require(search.returncode != 0 and textrel.returncode != 0,
                "external oracles accepted valid-looking output from nonzero readelf")
    return 2


def parity_tests() -> tuple[int, int, int]:
    module = load("p077_dynamic_parity", ROOT / "tools/sprint12-dynamic-metadata-environment-parity-smoke.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p076-parity-source-") as raw:
        repo = Path(raw) / "repo"
        repo.mkdir()
        init_git_repo(repo)
        (repo / ".gitignore").write_text("build/\n", encoding="utf-8")
        script = repo / "tool.sh"
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        script.chmod(0o755)
        run(["git", "add", ".gitignore", "tool.sh"], cwd=repo)
        run(["git", "commit", "-qm", "source"], cwd=repo)
        source_root = Path(raw) / "source"
        manifest, manifest_path = module.create_source_snapshot(repo, source_root)
        module.verify_source(source_root, manifest)
        require((source_root / ".gitignore").is_file() and not (source_root / ".git").exists(),
                "Git-less source authority omitted tracked .gitignore or included .git")
        source_ok = 1

        stage = Path(raw) / "stage"
        destination = Path(raw) / "result"
        stage.mkdir()
        (stage / "owned").write_text("result\n", encoding="utf-8")
        def race(_stage: Path, dest: Path) -> None:
            dest.mkdir(mode=0o700)
            (dest / "foreign").write_text("foreign\n", encoding="utf-8")
        module._TEST_BEFORE_PUBLISH_RENAME_HOOK = race
        try:
            try:
                module.publish(stage, destination)
            except OSError:
                pass
            else:
                raise Error("parity publication overwrote a raced destination")
        finally:
            module._TEST_BEFORE_PUBLISH_RENAME_HOOK = None
        require((destination / "foreign").read_text() == "foreign\n" and (stage / "owned").is_file(),
                "parity no-replace publication damaged foreign or owned data")
        publication_ok = 1

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    script_text = (ROOT / "tools/sprint12-dynamic-metadata-environment-parity-smoke.py").read_text(encoding="utf-8")
    require('-v "$(PWD)":/work' not in makefile.split("docker-test:", 1)[1].split("print-vars:", 1)[0],
            "Docker validation still bind-mounts and overwrites native build artifacts")
    require("live_repository_mounted_into_container\": False" in script_text,
            "dynamic parity does not record live-repository isolation")
    require("/source:ro" in script_text and "/output:rw" in script_text and "/work:rw" not in script_text,
            "dynamic parity mount policy changed")
    isolation_ok = 1
    return source_ok, publication_ok, isolation_ok


def generalized_label_test() -> int:
    source = (ROOT / "src/phdr.asm").read_text(encoding="utf-8")
    require(".dynamic_string_second_pass:" in source and ".dynamic_string_soname_terminator:" in source,
            "generalized dynamic-string labels are missing")
    require(".soname_second_pass:" not in source and ".soname_second_terminator:" not in source,
            "obsolete SONAME-only labels returned")
    return 1


def main() -> int:
    patch_apply, patch_rollback, patch_hash = patch_transaction_tests()
    recovery = recovery_tests()
    normalizer = normalizer_rollback_test()
    custody = custody_tests()
    search = search_contract_test()
    readelf = readelf_exit_tests()
    parity = parity_tests()
    labels = generalized_label_test()
    print(
        "patch076-corrective-regression-smoke: ok "
        f"patch_apply_pinned={patch_apply} patch_rollback_pinned={patch_rollback} patch_hash={patch_hash} "
        f"recovery_symlink={recovery[0]} recovery_publish={recovery[1]} recovery_file={recovery[2]} "
        f"recovery_root={recovery[3]} recovery_success={recovery[4]} normalizer_rollback={normalizer} "
        f"custody_substitution={custody[0]} custody_ancestor_churn={custody[1]} "
        f"search_failure_prefixes={search} readelf_nonzero={readelf} "
        f"parity_gitless_source={parity[0]} parity_no_replace={parity[1]} parity_isolation={parity[2]} "
        f"generalized_labels={labels}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Error, OSError, subprocess.TimeoutExpired, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"patch076-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
