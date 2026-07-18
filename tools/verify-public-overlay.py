#!/usr/bin/env python3
"""Authenticate and inspect a final-file public x64lens overlay without extraction.

The verifier combines four independent checks:

1. caller-supplied outer SHA-256 identity,
2. the production local/central ZIP metadata policy,
3. bounded public textual-content policy, and
4. an internal file hash/size/mode manifest.

The final-file overlay is a release/review artifact. Local Git application uses
the separately identified local patch so deleted tracked paths are represented.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HEX256 = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_SUFFIX = "PUBLIC_FILE_MANIFEST.json"


class VerificationError(RuntimeError):
    """Raised when authentication, policy, or manifest reconciliation fails."""


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise VerificationError(f"cannot import policy module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def load_manifest(archive: zipfile.ZipFile, name: str) -> dict[str, Any]:
    try:
        document = json.loads(archive.read(name).decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"invalid internal manifest {name}: {exc}") from exc
    require(isinstance(document, dict), "internal manifest must be a JSON object")
    require(isinstance(document.get("artifact"), str) and document["artifact"], "manifest artifact is required")
    source_base = document.get("source_base_commit")
    require(isinstance(source_base, str) and re.fullmatch(r"[0-9a-f]{40}", source_base), "manifest source_base_commit must be 40 lowercase hexadecimal characters")
    require(isinstance(document.get("files"), list), "manifest files must be an array")
    deleted = document.get("deleted_paths", [])
    require(isinstance(deleted, list) and all(isinstance(item, str) for item in deleted), "manifest deleted_paths must be a string array")
    require(len(deleted) == len(set(deleted)), "manifest deleted_paths contains duplicates")
    for path in deleted:
        require(path and not path.startswith("/") and "\\" not in path, f"manifest deleted path is invalid: {path}")
        pure = PurePosixPath(path)
        require(str(pure) == path and ".." not in pure.parts and "." not in pure.parts, f"manifest deleted path is non-canonical: {path}")
    return document


def verify_manifest(bundle: Path) -> tuple[int, int, str]:
    with zipfile.ZipFile(bundle) as archive:
        infos = archive.infolist()
        require(all(not info.is_dir() for info in infos), "public overlay must not contain directory entries")
        names = [info.filename for info in infos]
        require(len(names) == len(set(names)), "public overlay contains duplicate member names")
        manifests = [name for name in names if "/" not in name and name.endswith(MANIFEST_SUFFIX)]
        require(len(manifests) == 1, f"public overlay requires exactly one top-level *{MANIFEST_SUFFIX}")
        manifest_name = manifests[0]
        manifest = load_manifest(archive, manifest_name)

        records = manifest["files"]
        declared_count = manifest.get("file_count", len(records))
        require(isinstance(declared_count, int) and declared_count == len(records), "manifest file_count disagrees with files")
        deleted_paths = manifest.get("deleted_paths", [])
        declared_deleted_count = manifest.get("deleted_count", len(deleted_paths))
        require(isinstance(declared_deleted_count, int) and declared_deleted_count == len(deleted_paths), "manifest deleted_count disagrees with deleted_paths")

        expected_members = {manifest_name}
        seen_paths: set[str] = set()
        for index, record in enumerate(records):
            require(isinstance(record, dict), f"manifest files[{index}] must be an object")
            require(set(record) == {"path", "sha256", "size", "mode"}, f"manifest files[{index}] fields are invalid")
            path = record["path"]
            require(isinstance(path, str) and path and not path.startswith("/") and "\\" not in path, f"manifest files[{index}].path is invalid")
            pure = PurePosixPath(path)
            require(str(pure) == path and ".." not in pure.parts and "." not in pure.parts, f"manifest path is non-canonical: {path}")
            require(path not in seen_paths, f"manifest repeats path: {path}")
            seen_paths.add(path)
            expected_hash = record["sha256"]
            require(isinstance(expected_hash, str) and HEX256.fullmatch(expected_hash), f"invalid SHA-256 for {path}")
            expected_size = record["size"]
            require(isinstance(expected_size, int) and expected_size >= 0, f"invalid size for {path}")
            expected_mode = record["mode"]
            require(isinstance(expected_mode, str) and re.fullmatch(r"0[0-7]{3}", expected_mode), f"invalid mode for {path}")

            member = f"changed-files/{path}"
            expected_members.add(member)
            try:
                info = archive.getinfo(member)
                payload = archive.read(info)
            except KeyError as exc:
                raise VerificationError(f"manifest member missing: {member}") from exc
            require(info.file_size == expected_size == len(payload), f"size mismatch for {path}")
            require(sha256_bytes(payload) == expected_hash, f"SHA-256 mismatch for {path}")
            mode = stat.S_IMODE(info.external_attr >> 16)
            require(f"0{mode:03o}" == expected_mode, f"mode mismatch for {path}: expected {expected_mode}, got 0{mode:03o}")

        require(seen_paths.isdisjoint(set(deleted_paths)), "manifest cannot both include and delete the same path")
        require(set(names) == expected_members, "public overlay members disagree with internal manifest")
        return len(records), len(deleted_paths), manifest_name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args(argv)

    expected = args.expected_sha256.lower()
    try:
        require(HEX256.fullmatch(expected) is not None, "expected SHA-256 must contain 64 lowercase hexadecimal characters")
        require(args.bundle.is_file(), f"missing bundle: {args.bundle}")
        actual = sha256_file(args.bundle)
        require(actual == expected, f"outer SHA-256 mismatch: expected {expected}, got {actual}")

        metadata = load_module("x64lens_bundle_policy", ROOT / "tools" / "check-patch-bundle-hygiene.py")
        content = load_module("x64lens_public_content_policy", ROOT / "tools" / "check-public-content.py")
        entries, violations = metadata.inspect_bundle(args.bundle)
        require(not violations, f"metadata policy rejected {len(violations)} member(s): {violations[0].member}: {violations[0].reason}" if violations else "metadata policy rejected bundle")
        _, findings = content.scan_zip(args.bundle)
        require(not findings, f"public content policy rejected bundle: {findings[0]}" if findings else "public content policy rejected bundle")
        file_count, deleted_count, manifest_name = verify_manifest(args.bundle)
    except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile, VerificationError) as exc:
        print(f"public-overlay-verify: error: {exc}", file=sys.stderr)
        return 1

    print(
        "public-overlay-verify: ok "
        f"files={file_count} deleted={deleted_count} entries={entries} "
        f"manifest={manifest_name} sha256={actual}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
