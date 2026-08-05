#!/usr/bin/env python3
"""Apply or roll back one authenticated Git patch from pinned bytes and roots.

The patch is opened once with ``O_NOFOLLOW``, authenticated, and retained in
memory.  The repository root and its ``.git`` directory are also opened once
and retained by descriptor.  Every Git command addresses those descriptors
through ``/proc/self/fd`` so a caller-visible repository-path replacement
cannot redirect the mutating operation to another checkout.

The legacy package contract remains supported: apply starts from the exact
clean base commit/tree and produces one exact staged candidate tree; rollback
starts from that candidate and restores the clean base.  Any caller-visible
root or Git-directory substitution is detected before mutation and again after
mutation.  When post-mutation verification fails, the inverse operation is
attempted against the same pinned repository and the same pinned patch bytes.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Sequence

O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
MAX_PATCH_BYTES = 64 * 1024 * 1024


class TransactionError(RuntimeError):
    """Raised when source identity, patch custody, or Git state disagrees."""


@dataclass
class RepoHandle:
    requested: Path
    root_fd: int
    git_fd: int
    root_identity: tuple[int, int, int]
    git_identity: tuple[int, int, int]

    @property
    def root_proc(self) -> str:
        return f"/proc/self/fd/{self.root_fd}"

    @property
    def git_proc(self) -> str:
        return f"/proc/self/fd/{self.git_fd}"

    @property
    def pass_fds(self) -> tuple[int, int]:
        return (self.root_fd, self.git_fd)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TransactionError(message)


def fd_identity(metadata: os.stat_result) -> tuple[int, int, int]:
    return (metadata.st_dev, metadata.st_ino, stat.S_IFMT(metadata.st_mode))


def open_repo(path: Path) -> RepoHandle:
    requested = Path(os.path.abspath(path))
    root_fd = os.open(requested, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW)
    try:
        root_st = os.fstat(root_fd)
        require(stat.S_ISDIR(root_st.st_mode), "repository root is not a directory")
        git_fd = os.open(".git", os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=root_fd)
        try:
            git_st = os.fstat(git_fd)
            require(stat.S_ISDIR(git_st.st_mode), "repository .git is not a directory")
            os.set_inheritable(root_fd, True)
            os.set_inheritable(git_fd, True)
            handle = RepoHandle(
                requested=requested,
                root_fd=root_fd,
                git_fd=git_fd,
                root_identity=fd_identity(root_st),
                git_identity=fd_identity(git_st),
            )
            reauthenticate_repo(handle)
            return handle
        except BaseException:
            os.close(git_fd)
            raise
    except BaseException:
        os.close(root_fd)
        raise


def close_repo(repo: RepoHandle) -> None:
    for fd in (repo.git_fd, repo.root_fd):
        try:
            os.close(fd)
        except OSError:
            pass


def reauthenticate_repo(repo: RepoHandle) -> None:
    """Require the caller-visible root and .git names to retain entry identity."""
    visible_root = os.open(repo.requested, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW)
    try:
        require(fd_identity(os.fstat(visible_root)) == repo.root_identity, "repository root binding changed")
        visible_git = os.open(".git", os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=visible_root)
        try:
            require(fd_identity(os.fstat(visible_git)) == repo.git_identity, "repository .git binding changed")
        finally:
            os.close(visible_git)
    finally:
        os.close(visible_root)


def run(
    repo: RepoHandle,
    argv: Sequence[str],
    *,
    input_bytes: bytes | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(
        list(argv),
        cwd=repo.root_proc,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=repo.pass_fds,
        check=False,
    )
    if check and cp.returncode != 0:
        detail = (cp.stderr or cp.stdout).decode("utf-8", "replace").strip()
        raise TransactionError(f"{' '.join(argv)} failed ({cp.returncode}): {detail}")
    return cp


def git(repo: RepoHandle, *args: str, check: bool = True) -> bytes:
    argv = ["git", f"--git-dir={repo.git_proc}", f"--work-tree={repo.root_proc}", *args]
    return run(repo, argv, check=check).stdout.strip()


def read_authenticated_patch(path: Path, expected_sha256: str) -> bytes:
    require(
        len(expected_sha256) == 64
        and all(char in "0123456789abcdef" for char in expected_sha256),
        "invalid expected patch SHA-256",
    )
    fd = os.open(path, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        require(stat.S_ISREG(opened.st_mode), "patch is not a regular file")
        require(opened.st_nlink == 1, "patch has hard-link aliases")
        require(opened.st_size <= MAX_PATCH_BYTES, "patch exceeds bounded package limit")
        chunks: list[bytes] = []
        total = 0
        digest = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            require(total <= MAX_PATCH_BYTES, "patch exceeds bounded package limit")
            digest.update(chunk)
            chunks.append(chunk)
        final = os.fstat(fd)
        require(
            (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size, opened.st_nlink)
            == (final.st_dev, final.st_ino, final.st_mode, final.st_size, final.st_nlink),
            "patch descriptor changed while hashing",
        )
        require(total == opened.st_size, "patch size changed while hashing")
        observed = digest.hexdigest()
        require(observed == expected_sha256, f"patch SHA-256 mismatch: {observed}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def repository_identity(repo: RepoHandle) -> tuple[str, str, str, str]:
    reauthenticate_repo(repo)
    actual_root = os.fsdecode(git(repo, "rev-parse", "--show-toplevel"))
    require(actual_root in {repo.root_proc, str(repo.requested)}, f"repository root mismatch: {actual_root}")
    branch = os.fsdecode(git(repo, "branch", "--show-current"))
    head = os.fsdecode(git(repo, "rev-parse", "HEAD"))
    head_tree = os.fsdecode(git(repo, "rev-parse", "HEAD^{tree}"))
    index_tree = os.fsdecode(git(repo, "write-tree"))
    return branch, head, head_tree, index_tree


def require_no_unstaged_or_untracked(repo: RepoHandle) -> None:
    require(
        run(repo, ["git", f"--git-dir={repo.git_proc}", f"--work-tree={repo.root_proc}", "diff", "--quiet", "--"]).returncode == 0,
        "unstaged tracked changes are present",
    )
    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    require(untracked == b"", "nonignored untracked files are present")


def logical_base_state(repo: RepoHandle, branch: str, base_head: str, base_tree: str) -> tuple[str, str]:
    """Accept either the reviewed staged base or a later commit of that tree.

    Review bundles may carry a candidate as an exact staged tree while the
    user may commit that tree before applying the next package.  The logical
    base is therefore the authenticated index tree.  The HEAD must either be
    the declared reviewed parent or itself have the logical base tree.
    """
    actual_branch, head, head_tree, index_tree = repository_identity(repo)
    require(actual_branch == branch, f"branch mismatch: {actual_branch}")
    require_no_unstaged_or_untracked(repo)
    require(index_tree == base_tree, f"logical base index tree mismatch: {index_tree}")
    if head == base_head:
        return "reviewed-staged", head
    if head_tree == base_tree:
        return "committed-tree", head
    raise TransactionError(
        f"HEAD {head} is neither declared reviewed parent {base_head} nor a commit of logical base tree {base_tree}"
    )


def candidate_state(
    repo: RepoHandle,
    branch: str,
    base_head: str,
    base_tree: str,
    candidate_tree: str,
) -> tuple[str, str]:
    actual_branch, head, head_tree, index_tree = repository_identity(repo)
    require(actual_branch == branch, f"branch mismatch: {actual_branch}")
    require_no_unstaged_or_untracked(repo)
    require(index_tree == candidate_tree, f"staged candidate tree mismatch: {index_tree}")
    if head == base_head:
        return "reviewed-staged", head
    if head_tree == base_tree:
        return "committed-tree", head
    raise TransactionError(
        f"HEAD {head} is neither declared reviewed parent {base_head} nor a commit of logical base tree {base_tree}"
    )


def invoke_hook(name: str, repo: RepoHandle) -> None:
    command = os.environ.get(name)
    if not command:
        return
    cp = subprocess.run(
        ["bash", "-lc", command],
        cwd=repo.root_proc,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=repo.pass_fds,
        check=False,
    )
    if cp.returncode != 0:
        detail = (cp.stderr or cp.stdout).decode("utf-8", "replace").strip()
        raise TransactionError(f"test hook {name} failed ({cp.returncode}): {detail}")


def git_apply(repo: RepoHandle, raw: bytes, *, reverse: bool, check_only: bool) -> None:
    argv = ["git", f"--git-dir={repo.git_proc}", f"--work-tree={repo.root_proc}", "apply", "--index"]
    if reverse:
        argv.append("--reverse")
    if check_only:
        argv.append("--check")
    argv.append("-")
    cp = run(repo, argv, input_bytes=raw)
    if cp.returncode != 0:
        detail = (cp.stderr or cp.stdout).decode("utf-8", "replace").strip()
        raise TransactionError(f"git apply failed ({cp.returncode}): {detail}")


def restore_with_inverse(repo: RepoHandle, raw: bytes, *, reverse: bool, expected_tree: str) -> str | None:
    """Best-effort exact inverse using the retained repository and patch bytes."""
    try:
        git_apply(repo, raw, reverse=reverse, check_only=True)
        git_apply(repo, raw, reverse=reverse, check_only=False)
        actual = os.fsdecode(git(repo, "write-tree"))
        if actual != expected_tree:
            return f"inverse produced tree {actual}, expected {expected_tree}"
        return None
    except BaseException as exc:
        return str(exc)


def recover_after_effect(
    repo: RepoHandle,
    raw: bytes,
    *,
    desired_tree: str,
    inverse_reverse: bool,
) -> str | None:
    """Restore ``desired_tree`` after a mutating call or hook raises.

    A mutating subprocess or injected test double can perform the Git effect and
    then raise before returning.  The current index tree is therefore inspected
    inside the exception path.  Recovery is skipped only when the desired tree
    is already present; every other state is driven through the retained inverse
    patch bytes and checked exactly.
    """
    try:
        current = os.fsdecode(git(repo, "write-tree"))
    except BaseException as exc:
        return f"could not inspect post-effect tree: {exc}"
    if current == desired_tree:
        return None
    return restore_with_inverse(repo, raw, reverse=inverse_reverse, expected_tree=desired_tree)


def apply_patch(
    repo: RepoHandle,
    raw: bytes,
    *,
    branch: str,
    base_head: str,
    base_tree: str,
    candidate_tree: str,
) -> str:
    mode, original_head = logical_base_state(repo, branch, base_head, base_tree)
    try:
        git_apply(repo, raw, reverse=False, check_only=True)
        invoke_hook("X64LENS_PATCH_TRANSACTION_AFTER_CHECK_HOOK", repo)
        reauthenticate_repo(repo)
        # The mutating call belongs inside the recovery region.  It may complete
        # the Git effect and still raise (for example, interruption or an
        # injected post-effect failure).
        git_apply(repo, raw, reverse=False, check_only=False)
        invoke_hook("X64LENS_PATCH_TRANSACTION_AFTER_APPLY_EFFECT_HOOK", repo)
        observed_mode, current_head = candidate_state(repo, branch, base_head, base_tree, candidate_tree)
        require(current_head == original_head, "HEAD changed during patch application")
        require(observed_mode == mode, "logical base mode changed during patch application")
    except BaseException as exc:
        recovery = recover_after_effect(
            repo,
            raw,
            desired_tree=base_tree,
            inverse_reverse=True,
        )
        suffix = f"; inverse recovery failed: {recovery}" if recovery else "; inverse recovery restored the logical base"
        raise TransactionError(f"patch application failed: {exc}{suffix}") from exc
    return mode


def rollback_patch(
    repo: RepoHandle,
    raw: bytes,
    *,
    branch: str,
    base_head: str,
    base_tree: str,
    candidate_tree: str,
) -> str:
    mode, original_head = candidate_state(repo, branch, base_head, base_tree, candidate_tree)
    try:
        git_apply(repo, raw, reverse=True, check_only=True)
        invoke_hook("X64LENS_PATCH_TRANSACTION_AFTER_REVERSE_CHECK_HOOK", repo)
        reauthenticate_repo(repo)
        git_apply(repo, raw, reverse=True, check_only=False)
        invoke_hook("X64LENS_PATCH_TRANSACTION_AFTER_ROLLBACK_EFFECT_HOOK", repo)
        observed_mode, current_head = logical_base_state(repo, branch, base_head, base_tree)
        require(current_head == original_head, "HEAD changed during patch rollback")
        require(observed_mode == mode, "logical base mode changed during patch rollback")
    except BaseException as exc:
        recovery = recover_after_effect(
            repo,
            raw,
            desired_tree=candidate_tree,
            inverse_reverse=False,
        )
        suffix = f"; forward recovery failed: {recovery}" if recovery else "; forward recovery restored the staged candidate"
        raise TransactionError(f"patch rollback failed: {exc}{suffix}") from exc
    return mode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("apply", "rollback", "verify-applied"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--patch-sha256", required=True)
    parser.add_argument("--branch", default="main")
    parser.add_argument("--base-head", required=True)
    parser.add_argument("--base-tree", required=True)
    parser.add_argument("--candidate-tree", required=True)
    args = parser.parse_args()

    raw = read_authenticated_patch(Path(os.path.abspath(args.patch)), args.patch_sha256)
    repo = open_repo(args.repo)
    try:
        if args.action == "apply":
            mode = apply_patch(
                repo,
                raw,
                branch=args.branch,
                base_head=args.base_head,
                base_tree=args.base_tree,
                candidate_tree=args.candidate_tree,
            )
            print(
                "git-patch-transaction: ok action=apply "
                f"logical_base_tree={args.base_tree} candidate_tree={args.candidate_tree} "
                f"base_mode={mode} pinned_patch=1 pinned_repo=1"
            )
        elif args.action == "rollback":
            mode = rollback_patch(
                repo,
                raw,
                branch=args.branch,
                base_head=args.base_head,
                base_tree=args.base_tree,
                candidate_tree=args.candidate_tree,
            )
            print(
                "git-patch-transaction: ok action=rollback "
                f"logical_base_tree={args.base_tree} candidate_tree={args.candidate_tree} "
                f"base_mode={mode} pinned_patch=1 pinned_repo=1"
            )
        else:
            mode, _head = candidate_state(
                repo, args.branch, args.base_head, args.base_tree, args.candidate_tree
            )
            print(
                "git-patch-transaction: ok action=verify-applied "
                f"logical_base_tree={args.base_tree} candidate_tree={args.candidate_tree} "
                f"base_mode={mode} pinned_patch=1 pinned_repo=1"
            )
    finally:
        close_repo(repo)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, TransactionError, subprocess.SubprocessError) as exc:
        print(f"git-patch-transaction: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
