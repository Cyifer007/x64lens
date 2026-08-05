#!/usr/bin/env python3
"""Create and verify one exact Git-less source-tree authority.

The create path reads the staged Git index without using the worktree as a byte
authority, materializes only stage-zero regular files, and derives the candidate
Git tree independently from their recorded modes and blob identities.  The
verify path needs no Git metadata and rejects missing, extra, linked, special,
mode-drifted, or byte-drifted members.

``create-context`` produces the only supported Docker build context: an exact
``source/`` tree, its manifest, and a transport Dockerfile copied byte-for-byte
from the staged ``Dockerfile`` blob.  Ignored, untracked, generated, and private
worktree members never enter that context.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
from typing import Any

SCHEMA = "x64lens-gitless-source-v1"
CONTEXT_SCHEMA = "x64lens-exact-docker-context-v1"
BUFFER = 1024 * 1024
MAX_FILES = 8192
MAX_DIRECTORIES = 2048


class SourceError(RuntimeError):
    """Raised when source identity or exact membership disagrees."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SourceError(message)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def safe(raw: Any) -> str:
    require(isinstance(raw, str) and raw, "source path must be a nonempty string")
    path = PurePosixPath(raw)
    require(
        not path.is_absolute()
        and path.as_posix() == raw
        and "\\" not in raw
        and all(part not in {"", ".", ".."} for part in path.parts),
        f"unsafe source path: {raw!r}",
    )
    return raw


def parent(raw: str) -> str:
    return "/".join(PurePosixPath(raw).parts[:-1])


def git_object(kind: bytes, payload: bytes) -> str:
    return hashlib.sha1(kind + b" " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(BUFFER)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
    return digest.hexdigest(), total


def run_git(repo: Path, *args: str) -> bytes:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(cp.returncode == 0, f"git {' '.join(args)} failed: {cp.stderr.decode(errors='replace').strip()}")
    return cp.stdout


def index_records(repo: Path) -> tuple[str, list[tuple[str, str, str]]]:
    require(subprocess.run(["git", "-C", str(repo), "diff", "--quiet", "--"], check=False).returncode == 0,
            "worktree differs from staged source authority")
    tree = run_git(repo, "write-tree").decode().strip()
    rows: list[tuple[str, str, str]] = []
    for raw in run_git(repo, "ls-files", "-s", "-z").split(b"\0"):
        if not raw:
            continue
        header, path_raw = raw.split(b"\t", 1)
        mode_raw, oid_raw, stage_raw = header.split()
        require(stage_raw == b"0", "source index contains non-stage-zero entries")
        mode = mode_raw.decode("ascii")
        require(mode in {"100644", "100755"}, f"unsupported Docker source Git mode {mode}: {os.fsdecode(path_raw)}")
        rows.append((safe(os.fsdecode(path_raw)), mode, oid_raw.decode("ascii")))
    rows.sort(key=lambda row: os.fsencode(row[0]))
    require(0 < len(rows) <= MAX_FILES, f"source file count outside bound: {len(rows)}")
    return tree, rows


def derive_tree(files: list[dict[str, Any]], directories: list[str]) -> str:
    directory_set = set(directories)
    all_directories = {"", *directory_set}
    children: dict[str, list[tuple[str, bool, str, str]]] = {item: [] for item in all_directories}
    for directory in directory_set:
        require(parent(directory) in all_directories, f"directory parent missing: {directory}")
    for item in files:
        path = safe(item["path"])
        require(parent(path) in all_directories, f"file parent missing: {path}")
        children[parent(path)].append((PurePosixPath(path).name, False, item["git_mode"], item["git_oid"]))
    for directory in sorted(directory_set, key=lambda item: (-item.count("/"), os.fsencode(item))):
        entries = children[directory]
        require(entries, f"empty directory cannot belong to a Git tree: {directory}")
        payload = tree_payload(entries)
        children[parent(directory)].append((PurePosixPath(directory).name, True, "40000", git_object(b"tree", payload)))
    require(children[""], "source tree has no root members")
    return git_object(b"tree", tree_payload(children[""]))


def tree_payload(entries: list[tuple[str, bool, str, str]]) -> bytes:
    ordered = sorted(
        ((os.fsencode(name) + (b"/" if is_dir else b""), is_dir, mode, oid)
         for name, is_dir, mode, oid in entries),
        key=lambda row: row[0],
    )
    chunks: list[bytes] = []
    for ordered_name, is_dir, mode, oid in ordered:
        name = ordered_name[:-1] if is_dir else ordered_name
        chunks.append(mode.encode("ascii") + b" " + name + b"\0" + bytes.fromhex(oid))
    return b"".join(chunks)


def create(repo: Path, root: Path, manifest_path: Path) -> dict[str, Any]:
    repo = Path(os.path.abspath(repo))
    root = Path(os.path.abspath(root))
    manifest_path = Path(os.path.abspath(manifest_path))
    require(not root.exists(), "source root already exists")
    require(manifest_path.parent.is_dir() and not manifest_path.parent.is_symlink(), "manifest parent is missing or linked")
    tree, records = index_records(repo)
    directories = sorted(
        {"/".join(PurePosixPath(path).parts[:index])
         for path, _mode, _oid in records
         for index in range(1, len(PurePosixPath(path).parts))},
        key=lambda item: (item.count("/"), os.fsencode(item)),
    )
    require(len(directories) <= MAX_DIRECTORIES, "source directory count exceeds bound")
    root.mkdir(mode=0o755)
    for directory in directories:
        target = root / directory
        target.mkdir(mode=0o755)
        target.chmod(0o755)
    files: list[dict[str, Any]] = []
    for path, git_mode, expected_oid in records:
        payload = run_git(repo, "show", f":{path}")
        require(git_object(b"blob", payload) == expected_oid, f"staged Git blob changed: {path}")
        target = root / path
        target.write_bytes(payload)
        mode = 0o755 if git_mode == "100755" else 0o644
        target.chmod(mode)
        files.append({
            "path": path,
            "git_mode": git_mode,
            "git_oid": expected_oid,
            "mode": f"{mode:04o}",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        })
    manifest = {
        "schema": SCHEMA,
        "candidate_tree": tree,
        "directories": directories,
        "files": files,
        "git_metadata_required": False,
    }
    require(derive_tree(files, directories) == tree, "materialized source does not derive the staged Git tree")
    manifest_path.write_bytes(canonical(manifest))
    manifest_path.chmod(0o444)
    verify(root, manifest)
    return manifest


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    require(isinstance(value, dict), "source manifest must be an object")
    return value


def verify(root: Path, manifest: dict[str, Any]) -> None:
    require(set(manifest) == {"schema", "candidate_tree", "directories", "files", "git_metadata_required"},
            "source manifest shape changed")
    require(manifest["schema"] == SCHEMA and manifest["git_metadata_required"] is False,
            "source manifest identity changed")
    candidate_tree = manifest["candidate_tree"]
    require(isinstance(candidate_tree, str) and len(candidate_tree) == 40 and all(c in "0123456789abcdef" for c in candidate_tree),
            "invalid source candidate tree")
    directories = manifest["directories"]
    files = manifest["files"]
    require(isinstance(directories, list) and isinstance(files, list), "source member authorities must be arrays")
    require(len(directories) <= MAX_DIRECTORIES and len(files) <= MAX_FILES, "source authority exceeds bounds")
    require(directories == sorted(directories, key=lambda item: (item.count("/"), os.fsencode(item))),
            "source directory order changed")
    expected_directories: set[str] = set()
    for item in directories:
        path = safe(item)
        require(path not in expected_directories, f"duplicate source directory: {path}")
        expected_directories.add(path)
    expected_files: set[str] = set()
    seen_inodes: set[tuple[int, int]] = set()
    normalized_files: list[dict[str, Any]] = []
    for item in files:
        require(isinstance(item, dict) and set(item) == {"path", "git_mode", "git_oid", "mode", "sha256", "size_bytes"},
                "source file record shape changed")
        path = safe(item["path"])
        require(path not in expected_files, f"duplicate source file: {path}")
        expected_files.add(path)
        require(item["git_mode"] in {"100644", "100755"}, f"invalid Git mode: {path}")
        expected_mode = "0755" if item["git_mode"] == "100755" else "0644"
        require(item["mode"] == expected_mode, f"transport mode disagrees with Git mode: {path}")
        require(isinstance(item["git_oid"], str) and len(item["git_oid"]) == 40, f"invalid Git object: {path}")
        require(isinstance(item["sha256"], str) and len(item["sha256"]) == 64, f"invalid SHA-256: {path}")
        require(type(item["size_bytes"]) is int and item["size_bytes"] >= 0, f"invalid size: {path}")
        target = root / path
        metadata = target.lstat()
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1, f"unsafe source member: {path}")
        key = (metadata.st_dev, metadata.st_ino)
        require(key not in seen_inodes, f"source hard-link topology changed: {path}")
        seen_inodes.add(key)
        require(f"{stat.S_IMODE(metadata.st_mode):04o}" == item["mode"], f"source mode changed: {path}")
        observed_sha, observed_size = hash_file(target)
        require((observed_sha, observed_size) == (item["sha256"], item["size_bytes"]), f"source bytes changed: {path}")
        payload = target.read_bytes()
        require(git_object(b"blob", payload) == item["git_oid"], f"source Git object changed: {path}")
        normalized_files.append(item)
    observed_files: set[str] = set()
    observed_directories: set[str] = set()
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        relative = current_path.relative_to(root).as_posix()
        if relative == ".":
            relative = ""
        for name in list(dirnames):
            target = current_path / name
            metadata = target.lstat()
            require(stat.S_ISDIR(metadata.st_mode), f"linked or special source directory: {target}")
            path = name if not relative else f"{relative}/{name}"
            observed_directories.add(safe(path))
        for name in filenames:
            target = current_path / name
            metadata = target.lstat()
            require(stat.S_ISREG(metadata.st_mode), f"linked or special source file: {target}")
            path = name if not relative else f"{relative}/{name}"
            observed_files.add(safe(path))
    require(observed_files == expected_files, f"source file membership changed: missing={sorted(expected_files-observed_files)[:5]} extra={sorted(observed_files-expected_files)[:5]}")
    require(observed_directories == expected_directories, f"source directory membership changed: missing={sorted(expected_directories-observed_directories)[:5]} extra={sorted(observed_directories-expected_directories)[:5]}")
    require(derive_tree(normalized_files, directories) == candidate_tree, "source Git tree derivation changed")


def create_context(repo: Path, context: Path) -> dict[str, Any]:
    context = Path(os.path.abspath(context))
    require(not context.exists(), "Docker context already exists")
    context.mkdir(mode=0o755)
    source = context / "source"
    manifest_path = context / "source-manifest.json"
    manifest = create(repo, source, manifest_path)
    dockerfile_payload = run_git(Path(os.path.abspath(repo)), "show", ":Dockerfile")
    transport = context / "Dockerfile.transport"
    transport.write_bytes(dockerfile_payload)
    transport.chmod(0o644)
    # The generated root ignore file intentionally excludes nothing.  The only
    # copied subtree is source/, which was already constructed from the index.
    (context / ".dockerignore").write_text("# exact generated context; no path exclusions\n", encoding="utf-8")
    (context / ".dockerignore").chmod(0o644)
    authority = {
        "schema": CONTEXT_SCHEMA,
        "candidate_tree": manifest["candidate_tree"],
        "source_manifest_sha256": hash_file(manifest_path)[0],
        "transport_dockerfile_sha256": hashlib.sha256(dockerfile_payload).hexdigest(),
        "source_files": len(manifest["files"]),
        "source_directories": len(manifest["directories"]),
        "ignored_or_untracked_members_copied": 0,
    }
    (context / "context-authority.json").write_bytes(canonical(authority))
    (context / "context-authority.json").chmod(0o444)
    verify(source, manifest)
    return authority


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create_parser = sub.add_parser("create")
    create_parser.add_argument("--repo", type=Path, required=True)
    create_parser.add_argument("--root", type=Path, required=True)
    create_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--root", type=Path, required=True)
    verify_parser.add_argument("--manifest", type=Path, required=True)
    context_parser = sub.add_parser("create-context")
    context_parser.add_argument("--repo", type=Path, required=True)
    context_parser.add_argument("--context", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "create":
        value = create(args.repo, args.root, args.manifest)
        print(f"gitless-source-manifest: ok action=create tree={value['candidate_tree']} files={len(value['files'])} directories={len(value['directories'])}")
    elif args.command == "verify":
        value = load_manifest(args.manifest)
        verify(args.root, value)
        print(f"gitless-source-manifest: ok action=verify tree={value['candidate_tree']} files={len(value['files'])} directories={len(value['directories'])}")
    else:
        value = create_context(args.repo, args.context)
        print(f"gitless-source-manifest: ok action=create-context tree={value['candidate_tree']} files={value['source_files']} ignored_or_untracked=0")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, SourceError, subprocess.SubprocessError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(f"gitless-source-manifest: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
