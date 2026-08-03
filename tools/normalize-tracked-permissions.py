#!/usr/bin/env python3
"""Normalize only Git-tracked repository modes with preflight and rollback.

The old broad ``find | chmod`` recipe could touch ignored or untracked files and
leave a partially mutated worktree when a later chmod failed.  This helper reads
Git's index modes, validates every tracked pathname before mutation, touches no
ignored/untracked object, rolls back every changed mode on failure, and verifies
the final tracked modes.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from typing import NamedTuple


class PermissionErrorContract(RuntimeError):
    pass


class Record(NamedTuple):
    path: str
    expected_mode: int
    file_type: int


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionErrorContract(message)


def run_git(repo: Path, *args: str) -> bytes:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(cp.returncode == 0, f"git {' '.join(args)} failed: {cp.stderr.decode(errors='replace').strip()}")
    return cp.stdout


def safe_path(raw: str) -> str:
    pure = PurePosixPath(raw)
    require(raw and not pure.is_absolute() and all(part not in {"", ".", ".."} for part in pure.parts),
            f"unsafe tracked path: {raw!r}")
    require(pure.as_posix() == raw and "\\" not in raw, f"noncanonical tracked path: {raw!r}")
    return raw


def index_records(repo: Path) -> list[Record]:
    raw = run_git(repo, "ls-files", "-s", "-z")
    records: list[Record] = []
    for item in raw.split(b"\0"):
        if not item:
            continue
        header, path_raw = item.split(b"\t", 1)
        fields = header.split()
        require(len(fields) == 3, "unexpected git index record")
        mode = fields[0].decode("ascii")
        path = safe_path(os.fsdecode(path_raw))
        if mode == "100644":
            records.append(Record(path, 0o644, stat.S_IFREG))
        elif mode == "100755":
            records.append(Record(path, 0o755, stat.S_IFREG))
        elif mode == "120000":
            records.append(Record(path, 0, stat.S_IFLNK))
        else:
            raise PermissionErrorContract(f"unsupported tracked index mode {mode}: {path}")
    require(records, "repository has no tracked paths")
    return records


def normalize(repo: Path) -> tuple[int, int]:
    repo = Path(os.path.abspath(repo))
    require(repo.is_dir() and not repo.is_symlink(), f"repository root is not a real directory: {repo}")
    records = index_records(repo)
    owner = os.geteuid()
    file_changes: list[tuple[Path, int]] = []
    directory_modes: dict[Path, int] = {}

    # Complete preflight before any chmod.
    for record in records:
        path = repo / record.path
        metadata = path.lstat()
        observed_type = stat.S_IFMT(metadata.st_mode)
        require(observed_type == record.file_type,
                f"tracked path type disagrees with Git index: {record.path}")
        if record.file_type == stat.S_IFREG:
            require(metadata.st_uid == owner or owner == 0,
                    f"tracked file is not owned by the current user: {record.path}")
            if stat.S_IMODE(metadata.st_mode) != record.expected_mode:
                file_changes.append((path, stat.S_IMODE(metadata.st_mode)))
        parent = path.parent
        while parent != repo.parent and parent != repo:
            directory_modes.setdefault(parent, stat.S_IMODE(parent.lstat().st_mode))
            parent = parent.parent
    directory_modes.setdefault(repo, stat.S_IMODE(repo.lstat().st_mode))
    for directory in directory_modes:
        metadata = directory.lstat()
        require(stat.S_ISDIR(metadata.st_mode) and not directory.is_symlink(),
                f"tracked parent is not a real directory: {directory}")
        require(metadata.st_uid == owner or owner == 0,
                f"tracked parent is not owned by the current user: {directory}")

    changed: list[tuple[Path, int]] = []
    try:
        for directory, original in sorted(directory_modes.items(), key=lambda item: (len(item[0].parts), str(item[0]))):
            if original != 0o755:
                os.chmod(directory, 0o755, follow_symlinks=False)
                changed.append((directory, original))
        expected_by_path = {repo / record.path: record.expected_mode for record in records if record.file_type == stat.S_IFREG}
        for path, original in sorted(file_changes, key=lambda item: os.fsencode(str(item[0]))):
            os.chmod(path, expected_by_path[path], follow_symlinks=False)
            changed.append((path, original))
    except BaseException as exc:
        rollback_errors: list[str] = []
        for path, original in reversed(changed):
            try:
                os.chmod(path, original, follow_symlinks=False)
                if stat.S_IMODE(path.lstat().st_mode) != original:
                    rollback_errors.append(f"mode verification failed: {path}")
            except OSError as rollback_exc:
                rollback_errors.append(f"{path}: {rollback_exc}")
        suffix = f"; rollback failures: {rollback_errors}" if rollback_errors else ""
        raise PermissionErrorContract(f"permission normalization failed: {exc}{suffix}") from exc

    for record in records:
        path = repo / record.path
        metadata = path.lstat()
        if record.file_type == stat.S_IFREG:
            require(stat.S_IMODE(metadata.st_mode) == record.expected_mode,
                    f"tracked file mode normalization failed: {record.path}")
        else:
            require(stat.S_ISLNK(metadata.st_mode), f"tracked symlink changed: {record.path}")
    for directory in directory_modes:
        require(stat.S_IMODE(directory.lstat().st_mode) == 0o755,
                f"tracked directory mode normalization failed: {directory}")
    return len(file_changes), sum(1 for mode in directory_modes.values() if mode != 0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    changed_files, changed_directories = normalize(args.repo)
    print(
        "normalize-tracked-permissions: ok "
        f"files_changed={changed_files} directories_changed={changed_directories} untracked_touched=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PermissionErrorContract, OSError, ValueError) as exc:
        print(f"normalize-tracked-permissions: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
