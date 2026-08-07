#!/usr/bin/env python3
"""Record and verify one immutable Docker image authority.

The repository tag is descriptive only. Downstream validation consumes the
recorded immutable image ID plus candidate-tree, exact-context, and source-
manifest labels. Retargeting the tag or substituting provenance records after
``docker-build`` cannot redirect source custody, tests, or parity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any

SCHEMA = "x64lens-docker-image-authority-v1"


class AuthorityError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuthorityError(message)


def strict_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def run_inspect(docker: str, reference: str) -> dict[str, Any]:
    cp = subprocess.run(
        [docker, "image", "inspect", reference],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(cp.returncode == 0, f"cannot inspect Docker image {reference}: {cp.stderr.decode(errors='replace').strip()}")
    value = json.loads(cp.stdout, object_pairs_hook=strict_pairs)
    require(isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict), "Docker inspect shape changed")
    return value[0]


def image_identity(record: dict[str, Any]) -> tuple[str, str, str, str]:
    image_id = record.get("Id")
    labels = ((record.get("Config") or {}).get("Labels") or {})
    tree = labels.get("org.x64lens.candidate-tree")
    context_sha256 = labels.get("org.x64lens.context-authority-sha256")
    source_sha256 = labels.get("org.x64lens.source-manifest-sha256")
    require(isinstance(image_id, str) and image_id.startswith("sha256:") and len(image_id) == 71, "Docker image lacks immutable ID")
    require(isinstance(tree, str) and len(tree) == 40 and all(c in "0123456789abcdef" for c in tree), "Docker image lacks candidate-tree label")
    require(isinstance(context_sha256, str) and len(context_sha256) == 64 and all(c in "0123456789abcdef" for c in context_sha256), "Docker image lacks context-authority digest label")
    require(isinstance(source_sha256, str) and len(source_sha256) == 64 and all(c in "0123456789abcdef" for c in source_sha256), "Docker image lacks source-manifest digest label")
    return image_id, tree, context_sha256, source_sha256


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    require(
        isinstance(value, dict)
        and set(value) == {
            "schema", "tag", "image_id", "candidate_tree", "context_authority_sha256",
            "source_manifest_sha256", "tag_is_descriptive_only",
        },
        "Docker image authority shape changed",
    )
    require(value["schema"] == SCHEMA and value["tag_is_descriptive_only"] is True, "Docker image authority identity changed")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def publish(path: Path, payload: bytes) -> None:
    path = Path(os.path.abspath(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    require(path.parent.is_dir() and not path.parent.is_symlink(), "Docker authority parent is unavailable or linked")
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    name = f".{path.name}.tmp.{os.getpid()}.{os.urandom(16).hex()}"
    fd = -1
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent_fd)
        written = 0
        while written < len(payload):
            count = os.write(fd, payload[written:])
            require(count > 0, "short Docker authority write")
            written += count
        os.fchmod(fd, 0o444)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(name, path.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        os.close(parent_fd)


def record(args: argparse.Namespace) -> int:
    inspected = run_inspect(args.docker, args.tag)
    image_id, tree, image_context_sha256, image_source_sha256 = image_identity(inspected)
    require(tree == args.candidate_tree, "Docker tag resolved to the wrong candidate tree")
    context = json.loads(args.context_authority.read_text(encoding="utf-8"), object_pairs_hook=strict_pairs)
    require(context.get("candidate_tree") == tree, "Docker context authority tree disagrees with image")
    source_manifest = args.context_authority.parent / "source-manifest.json"
    require(source_manifest.is_file(), "Docker context source manifest is missing")
    context_sha256 = sha256(args.context_authority)
    source_sha256 = sha256(source_manifest)
    require(image_context_sha256 == context_sha256, "Docker image context-authority label disagrees with exact context")
    require(image_source_sha256 == source_sha256, "Docker image source-manifest label disagrees with exact context")
    value = {
        "schema": SCHEMA,
        "tag": args.tag,
        "image_id": image_id,
        "candidate_tree": tree,
        "context_authority_sha256": context_sha256,
        "source_manifest_sha256": source_sha256,
        "tag_is_descriptive_only": True,
    }
    publish(args.path, canonical(value))
    verify_value(value, args.docker)
    print(f"docker-image-authority: ok action=record image_id={image_id} tree={tree} tag_descriptive_only=1")
    return 0


def verify_value(value: dict[str, Any], docker: str) -> None:
    inspected = run_inspect(docker, value["image_id"])
    image_id, tree, context_sha256, source_sha256 = image_identity(inspected)
    require(image_id == value["image_id"], "Docker immutable image ID changed")
    require(tree == value["candidate_tree"], "Docker immutable image tree label changed")
    require(context_sha256 == value["context_authority_sha256"], "Docker immutable image context provenance changed")
    require(source_sha256 == value["source_manifest_sha256"], "Docker immutable image source provenance changed")


def verify(args: argparse.Namespace) -> int:
    value = load(args.path)
    verify_value(value, args.docker)
    print(f"docker-image-authority: ok action=verify image_id={value['image_id']} tree={value['candidate_tree']} tag_not_resolved=1")
    return 0


def get_field(args: argparse.Namespace) -> int:
    value = load(args.path)
    require(args.field in {"image_id", "candidate_tree", "tag"}, "unsupported Docker authority field")
    print(value[args.field])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--path", type=Path, required=True)
    rec.add_argument("--docker", required=True)
    rec.add_argument("--tag", required=True)
    rec.add_argument("--candidate-tree", required=True)
    rec.add_argument("--context-authority", type=Path, required=True)
    ver = sub.add_parser("verify")
    ver.add_argument("--path", type=Path, required=True)
    ver.add_argument("--docker", required=True)
    get = sub.add_parser("get")
    get.add_argument("--path", type=Path, required=True)
    get.add_argument("--field", required=True)
    args = parser.parse_args()
    if args.action == "record":
        return record(args)
    if args.action == "verify":
        return verify(args)
    return get_field(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuthorityError, OSError, json.JSONDecodeError, UnicodeDecodeError, subprocess.SubprocessError) as exc:
        print(f"docker-image-authority: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
