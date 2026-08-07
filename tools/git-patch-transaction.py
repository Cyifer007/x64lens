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
from pathlib import Path, PurePosixPath
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


@dataclass(frozen=True)
class TreeEntry:
    mode: str
    oid: str


@dataclass(frozen=True)
class PathState:
    exists: bool
    device: int = 0
    inode: int = 0
    file_type: int = 0
    mode: int = 0
    size: int = 0
    oid: str | None = None


class AlreadyState(TransactionError):
    """Raised when the requested exact state is already present."""


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


def tracked_worktree_clean(repo: RepoHandle) -> bool:
    return run(
        repo,
        ["git", f"--git-dir={repo.git_proc}", f"--work-tree={repo.root_proc}", "diff", "--quiet", "--"],
    ).returncode == 0


def nonignored_untracked(repo: RepoHandle) -> bytes:
    return git(repo, "ls-files", "--others", "--exclude-standard", "-z")


def require_no_unstaged_or_untracked(repo: RepoHandle) -> None:
    require(tracked_worktree_clean(repo), "unstaged tracked changes are present")
    require(nonignored_untracked(repo) == b"", "nonignored untracked files are present")


def exact_tree_state(repo: RepoHandle, expected_tree: str) -> bool:
    try:
        return (
            os.fsdecode(git(repo, "write-tree")) == expected_tree
            and tracked_worktree_clean(repo)
            and nonignored_untracked(repo) == b""
        )
    except BaseException:
        return False


def safe_patch_path(raw: str) -> str:
    path = PurePosixPath(raw)
    require(
        raw
        and not path.is_absolute()
        and path.as_posix() == raw
        and "\\" not in raw
        and all(part not in {"", ".", ".."} for part in path.parts),
        f"tree delta contains an unsafe path: {raw!r}",
    )
    return raw


def patch_paths(repo: RepoHandle, raw_patch: bytes) -> list[str]:
    """Derive the authenticated path scope from patch bytes alone.

    A recipient may have the exact base commit without the unreferenced
    candidate-tree object.  Path preflight must therefore not dereference the
    candidate tree before the patch has been applied and ``git write-tree`` has
    materialized it locally.  The package format deliberately rejects rename
    and copy metadata so ``git apply --numstat -z`` yields one literal path per
    changed entry, including additions and deletions.
    """
    for marker in (b"\nrename from ", b"\nrename to ", b"\ncopy from ", b"\ncopy to "):
        require(marker not in raw_patch, "renames and copies are unsupported in guarded package patches")
    argv = [
        "git",
        f"--git-dir={repo.git_proc}",
        f"--work-tree={repo.root_proc}",
        "apply",
        "--numstat",
        "-z",
        "-",
    ]
    cp = run(repo, argv, input_bytes=raw_patch)
    if cp.returncode != 0:
        detail = (cp.stderr or cp.stdout).decode("utf-8", "replace").strip()
        raise TransactionError(f"cannot derive authenticated patch paths ({cp.returncode}): {detail}")
    paths: set[str] = set()
    for record in (item for item in cp.stdout.split(b"\0") if item):
        fields = record.split(b"\t", 2)
        require(len(fields) == 3, "malformed git apply --numstat record")
        added, deleted, encoded_path = fields
        require(
            (added == b"-" and deleted == b"-")
            or (added.isdigit() and deleted.isdigit()),
            "malformed git apply --numstat counts",
        )
        paths.add(safe_patch_path(os.fsdecode(encoded_path)))
    ordered = sorted(paths, key=os.fsencode)
    require(ordered, "authenticated patch path scope is empty")
    return ordered


def changed_paths(repo: RepoHandle, left_tree: str, right_tree: str) -> list[str]:
    # Disable rename folding so every old and new pathname belongs to the
    # authenticated tree delta.  Paths are always passed back to Git through
    # literal, NUL-delimited pathspec input.
    raw = git(repo, "diff", "--no-renames", "--name-only", "-z", left_tree, right_tree)
    paths = sorted(
        {safe_patch_path(os.fsdecode(item)) for item in raw.split(b"\0") if item},
        key=os.fsencode,
    )
    require(paths, "authenticated patch tree delta is empty")
    return paths


def require_patch_scope_matches_trees(
    repo: RepoHandle, raw_patch: bytes, left_tree: str, right_tree: str
) -> list[str]:
    byte_scope = patch_paths(repo, raw_patch)
    tree_scope = changed_paths(repo, left_tree, right_tree)
    require(byte_scope == tree_scope, "patch-byte path scope disagrees with authenticated tree delta")
    return byte_scope


def _git_literal(repo: RepoHandle, args: Sequence[str], *, input_bytes: bytes | None = None) -> bytes:
    argv = [
        "git",
        f"--git-dir={repo.git_proc}",
        f"--work-tree={repo.root_proc}",
        "--literal-pathspecs",
        *args,
    ]
    cp = run(repo, argv, input_bytes=input_bytes)
    if cp.returncode != 0:
        detail = (cp.stderr or cp.stdout).decode("utf-8", "replace").strip()
        raise TransactionError(f"{' '.join(argv)} failed ({cp.returncode}): {detail}")
    return cp.stdout


def _parse_tree_entry(raw: bytes, path: str) -> TreeEntry | None:
    rows = [item for item in raw.split(b"\0") if item]
    if not rows:
        return None
    require(len(rows) == 1, f"ambiguous Git tree entry for {path}")
    header, observed = rows[0].split(b"\t", 1)
    mode_raw, type_raw, oid_raw = header.split()
    require(os.fsdecode(observed) == path, f"Git tree returned the wrong path for {path}")
    require(type_raw == b"blob", f"unsupported Git object type at patch path: {path}")
    mode = mode_raw.decode("ascii")
    require(mode in {"100644", "100755", "120000"}, f"unsupported Git mode {mode}: {path}")
    return TreeEntry(mode=mode, oid=oid_raw.decode("ascii"))


def tree_entry(repo: RepoHandle, tree: str, path: str) -> TreeEntry | None:
    return _parse_tree_entry(
        _git_literal(repo, ["ls-tree", "-z", "--full-tree", tree, "--", safe_patch_path(path)]),
        path,
    )


def index_entry(repo: RepoHandle, path: str) -> TreeEntry | None:
    raw = _git_literal(repo, ["ls-files", "--stage", "-z", "--", safe_patch_path(path)])
    rows = [item for item in raw.split(b"\0") if item]
    if not rows:
        return None
    require(len(rows) == 1, f"unmerged or ambiguous index entry at patch path: {path}")
    header, observed = rows[0].split(b"\t", 1)
    mode_raw, oid_raw, stage_raw = header.split()
    require(os.fsdecode(observed) == path and stage_raw == b"0", f"unexpected index stage at {path}")
    mode = mode_raw.decode("ascii")
    require(mode in {"100644", "100755", "120000"}, f"unsupported index mode {mode}: {path}")
    return TreeEntry(mode=mode, oid=oid_raw.decode("ascii"))


def _open_parent(repo: RepoHandle, path: str) -> tuple[int, str]:
    parts = PurePosixPath(safe_patch_path(path)).parts
    fd = os.dup(repo.root_fd)
    try:
        for component in parts[:-1]:
            child = os.open(component, os.O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def _blob_oid_from_fd(fd: int, size: int) -> str:
    digest = hashlib.sha1(b"blob " + str(size).encode("ascii") + b"\0")
    os.lseek(fd, 0, os.SEEK_SET)
    total = 0
    while True:
        chunk = os.read(fd, 1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
        total += len(chunk)
    require(total == size, "patch-path file size changed while hashing")
    return digest.hexdigest()


def path_state(repo: RepoHandle, path: str) -> PathState:
    parent_fd, name = _open_parent(repo, path)
    try:
        try:
            initial = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return PathState(False)
        file_type = stat.S_IFMT(initial.st_mode)
        oid: str | None = None
        if stat.S_ISREG(initial.st_mode):
            fd = os.open(name, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
            try:
                opened = os.fstat(fd)
                require(fd_identity(opened) == fd_identity(initial), f"patch path changed before hashing: {path}")
                oid = _blob_oid_from_fd(fd, opened.st_size)
                final = os.fstat(fd)
                require(
                    (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size, opened.st_nlink)
                    == (final.st_dev, final.st_ino, final.st_mode, final.st_size, final.st_nlink),
                    f"patch path changed while hashing: {path}",
                )
                initial = final
            finally:
                os.close(fd)
        elif stat.S_ISLNK(initial.st_mode):
            payload = os.fsencode(os.readlink(name, dir_fd=parent_fd))
            oid = hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()
            final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            require(fd_identity(final) == fd_identity(initial), f"patch symlink changed while reading: {path}")
            initial = final
        return PathState(
            True,
            initial.st_dev,
            initial.st_ino,
            file_type,
            stat.S_IMODE(initial.st_mode),
            initial.st_size,
            oid,
        )
    finally:
        os.close(parent_fd)


def state_matches_entry(state: PathState, entry: TreeEntry | None) -> bool:
    if entry is None:
        return not state.exists
    if not state.exists or state.oid != entry.oid:
        return False
    if entry.mode == "120000":
        return state.file_type == stat.S_IFLNK
    if state.file_type != stat.S_IFREG:
        return False
    expected_exec = entry.mode == "100755"
    return bool(state.mode & stat.S_IXUSR) == expected_exec


def state_identity_equal(left: PathState, right: PathState) -> bool:
    if left.exists != right.exists:
        return False
    if not left.exists:
        return True
    return (
        left.device, left.inode, left.file_type, left.mode, left.size, left.oid
    ) == (
        right.device, right.inode, right.file_type, right.mode, right.size, right.oid
    )


def capture_scope(repo: RepoHandle, paths: Sequence[str]) -> dict[str, PathState]:
    return {path: path_state(repo, path) for path in paths}


def scope_matches_tree(repo: RepoHandle, tree: str, paths: Sequence[str]) -> bool:
    for path in paths:
        expected = tree_entry(repo, tree, path)
        if index_entry(repo, path) != expected or not state_matches_entry(path_state(repo, path), expected):
            return False
    return True


def _unlink_bound_path(repo: RepoHandle, path: str, expected: PathState) -> None:
    require(expected.exists and expected.file_type in {stat.S_IFREG, stat.S_IFLNK},
            f"cannot remove unsupported patch residue: {path}")
    parent_fd, name = _open_parent(repo, path)
    held_fd = -1
    try:
        if expected.file_type == stat.S_IFREG:
            held_fd = os.open(name, os.O_RDONLY | O_CLOEXEC | O_NOFOLLOW, dir_fd=parent_fd)
            observed = path_state(repo, path)
            require(state_identity_equal(observed, expected), f"foreign replacement preserved before unlink: {path}")
        else:
            observed = path_state(repo, path)
            require(state_identity_equal(observed, expected), f"foreign replacement preserved before unlink: {path}")
        final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(
            (final.st_dev, final.st_ino, stat.S_IFMT(final.st_mode))
            == (expected.device, expected.inode, expected.file_type),
            f"foreign replacement preserved at final unlink: {path}",
        )
        os.unlink(name, dir_fd=parent_fd)
        if held_fd >= 0:
            require(os.fstat(held_fd).st_nlink == 0, f"patch residue was not unlinked: {path}")
    finally:
        if held_fd >= 0:
            os.close(held_fd)
        os.close(parent_fd)


def _remove_index_entry(repo: RepoHandle, path: str) -> None:
    _git_literal(repo, ["update-index", "--force-remove", "--", safe_patch_path(path)])


def _scope_safe_for_recovery(
    repo: RepoHandle,
    paths: Sequence[str],
    *,
    desired_tree: str,
    alternate_tree: str,
    before: dict[str, PathState] | None,
    effect: dict[str, PathState] | None,
) -> None:
    for path in paths:
        current = path_state(repo, path)
        if effect is not None:
            require(state_identity_equal(current, effect[path]), f"foreign replacement preserved at patch path: {path}")
        elif before is not None and state_identity_equal(current, before[path]):
            pass
        else:
            alternate = tree_entry(repo, alternate_tree, path)
            desired = tree_entry(repo, desired_tree, path)
            require(
                state_matches_entry(current, alternate) or state_matches_entry(current, desired),
                f"foreign or ambiguous object preserved at patch path: {path}",
            )
        current_index = index_entry(repo, path)
        require(
            current_index in {tree_entry(repo, desired_tree, path), tree_entry(repo, alternate_tree, path)},
            f"foreign index divergence preserved at patch path: {path}",
        )


def restore_exact_tree(
    repo: RepoHandle,
    desired_tree: str,
    alternate_tree: str,
    *,
    paths: Sequence[str],
    before: dict[str, PathState] | None = None,
    effect: dict[str, PathState] | None = None,
) -> str | None:
    """Restore only authenticated patch paths and preserve unrelated state.

    No repository-wide reset or path-based clean is used.  Every path is passed
    through Git's literal NUL-delimited pathspec interface.  A late foreign
    replacement or unrelated tracked/untracked divergence is preserved and
    causes fail-closed recovery rather than deletion.
    """
    try:
        _scope_safe_for_recovery(
            repo, paths, desired_tree=desired_tree, alternate_tree=alternate_tree, before=before, effect=effect
        )
        present_paths = [path for path in paths if tree_entry(repo, desired_tree, path) is not None]
        absent_paths = [path for path in paths if tree_entry(repo, desired_tree, path) is None]
        if present_paths:
            payload = b"\0".join(os.fsencode(path) for path in present_paths) + b"\0"
            _git_literal(
                repo,
                [
                    "restore",
                    f"--source={desired_tree}",
                    "--staged",
                    "--worktree",
                    "--pathspec-from-file=-",
                    "--pathspec-file-nul",
                ],
                input_bytes=payload,
            )
        for path in absent_paths:
            current = path_state(repo, path)
            if current.exists:
                _unlink_bound_path(repo, path, current)
            _remove_index_entry(repo, path)
        reauthenticate_repo(repo)
        require(scope_matches_tree(repo, desired_tree, paths), f"patch-scope recovery did not restore {desired_tree}")
        if exact_tree_state(repo, desired_tree):
            return None
        return "patch paths restored; unrelated tracked or untracked divergence was preserved"
    except BaseException as exc:
        return str(exc)



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


def restore_with_inverse(
    repo: RepoHandle,
    raw: bytes,
    *,
    reverse: bool,
    expected_tree: str,
    alternate_tree: str,
    paths: Sequence[str],
    before: dict[str, PathState] | None,
    effect: dict[str, PathState] | None,
) -> str | None:
    """Apply the exact inverse only while patch-path identities remain bound."""
    try:
        _scope_safe_for_recovery(
            repo, paths, desired_tree=expected_tree, alternate_tree=alternate_tree, before=before, effect=effect
        )
        git_apply(repo, raw, reverse=reverse, check_only=True)
        git_apply(repo, raw, reverse=reverse, check_only=False)
        reauthenticate_repo(repo)
        require(scope_matches_tree(repo, expected_tree, paths), f"inverse did not restore patch scope {expected_tree}")
        if exact_tree_state(repo, expected_tree):
            return None
        return "inverse restored patch paths; unrelated tracked or untracked divergence was preserved"
    except BaseException as exc:
        return str(exc)


def recover_after_effect(
    repo: RepoHandle,
    raw: bytes,
    *,
    desired_tree: str,
    alternate_tree: str,
    inverse_reverse: bool,
    paths: Sequence[str],
    before: dict[str, PathState],
    effect: dict[str, PathState] | None,
) -> str | None:
    """Recover only authenticated patch effects after a failed mutation."""
    if exact_tree_state(repo, desired_tree):
        return None
    try:
        current = os.fsdecode(git(repo, "write-tree"))
    except BaseException as exc:
        return f"could not inspect post-effect tree: {exc}"
    if current == alternate_tree:
        inverse = restore_with_inverse(
            repo,
            raw,
            reverse=inverse_reverse,
            expected_tree=desired_tree,
            alternate_tree=alternate_tree,
            paths=paths,
            before=before,
            effect=effect,
        )
        if inverse is None:
            return None
        # An inverse that preserved unrelated state is already the safest result.
        if "unrelated" in inverse or "foreign" in inverse:
            return inverse
    return restore_exact_tree(
        repo, desired_tree, alternate_tree, paths=paths, before=before, effect=effect
    )



def apply_patch(
    repo: RepoHandle,
    raw: bytes,
    *,
    branch: str,
    base_head: str,
    base_tree: str,
    candidate_tree: str,
) -> str:
    try:
        mode, original_head = logical_base_state(repo, branch, base_head, base_tree)
    except TransactionError as original:
        try:
            candidate_state(repo, branch, base_head, base_tree, candidate_tree)
        except TransactionError:
            raise original
        raise AlreadyState("patch is already applied at the exact candidate state")
    paths = patch_paths(repo, raw)
    before = capture_scope(repo, paths)
    effect: dict[str, PathState] | None = None
    try:
        git_apply(repo, raw, reverse=False, check_only=True)
        invoke_hook("X64LENS_PATCH_TRANSACTION_AFTER_CHECK_HOOK", repo)
        reauthenticate_repo(repo)
        # The mutating call belongs inside the recovery region.  It may complete
        # the Git effect and still raise (for example, interruption or an
        # injected post-effect failure).
        git_apply(repo, raw, reverse=False, check_only=False)
        effect = capture_scope(repo, paths)
        invoke_hook("X64LENS_PATCH_TRANSACTION_AFTER_APPLY_EFFECT_HOOK", repo)
        observed_mode, current_head = candidate_state(repo, branch, base_head, base_tree, candidate_tree)
        require(current_head == original_head, "HEAD changed during patch application")
        require(observed_mode == mode, "logical base mode changed during patch application")
        require_patch_scope_matches_trees(repo, raw, base_tree, candidate_tree)
    except BaseException as exc:
        recovery = recover_after_effect(
            repo,
            raw,
            desired_tree=base_tree,
            alternate_tree=candidate_tree,
            inverse_reverse=True,
            paths=paths,
            before=before,
            effect=effect,
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
    try:
        mode, original_head = candidate_state(repo, branch, base_head, base_tree, candidate_tree)
    except TransactionError as original:
        try:
            logical_base_state(repo, branch, base_head, base_tree)
        except TransactionError:
            raise original
        raise AlreadyState("patch is already rolled back at the exact logical base")
    paths = patch_paths(repo, raw)
    before = capture_scope(repo, paths)
    effect: dict[str, PathState] | None = None
    try:
        git_apply(repo, raw, reverse=True, check_only=True)
        invoke_hook("X64LENS_PATCH_TRANSACTION_AFTER_REVERSE_CHECK_HOOK", repo)
        reauthenticate_repo(repo)
        git_apply(repo, raw, reverse=True, check_only=False)
        effect = capture_scope(repo, paths)
        invoke_hook("X64LENS_PATCH_TRANSACTION_AFTER_ROLLBACK_EFFECT_HOOK", repo)
        observed_mode, current_head = logical_base_state(repo, branch, base_head, base_tree)
        require(current_head == original_head, "HEAD changed during patch rollback")
        require(observed_mode == mode, "logical base mode changed during patch rollback")
        require_patch_scope_matches_trees(repo, raw, base_tree, candidate_tree)
    except BaseException as exc:
        recovery = recover_after_effect(
            repo,
            raw,
            desired_tree=candidate_tree,
            alternate_tree=base_tree,
            inverse_reverse=False,
            paths=paths,
            before=before,
            effect=effect,
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
    except AlreadyState as exc:
        print(f"git-patch-transaction: already-state: {exc}", file=sys.stderr)
        raise SystemExit(3)
    except (OSError, TransactionError, subprocess.SubprocessError) as exc:
        print(f"git-patch-transaction: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
