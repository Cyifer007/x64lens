#!/usr/bin/env python3
"""Verify a GNU-style SHA-256 manifest relative to the manifest directory."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import sys

LINE_RE = re.compile(r"^([0-9a-fA-F]{64}) ([ *])(.+)$")


class ManifestError(RuntimeError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe_relative_name(raw: str) -> PurePosixPath:
    if "\\" in raw or "\x00" in raw:
        raise ManifestError(f"unsafe manifest path: {raw!r}")
    name = PurePosixPath(raw)
    if name.is_absolute() or not name.parts:
        raise ManifestError(f"manifest path must be relative: {raw!r}")
    if any(part in {"", ".", ".."} for part in name.parts):
        raise ManifestError(f"manifest path contains unsafe component: {raw!r}")
    return name


def verify(manifest: Path) -> int:
    manifest = manifest.resolve()
    if not manifest.is_file():
        raise ManifestError(f"manifest not found: {manifest}")

    root = manifest.parent
    seen: set[PurePosixPath] = set()
    count = 0
    for lineno, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        match = LINE_RE.fullmatch(line)
        if not match:
            raise ManifestError(f"line {lineno}: invalid SHA-256 manifest record")
        expected, _mode, raw_name = match.groups()
        name = safe_relative_name(raw_name)
        if name in seen:
            raise ManifestError(f"line {lineno}: duplicate manifest path: {raw_name}")
        seen.add(name)
        path = root.joinpath(*name.parts)
        if not path.is_file():
            raise ManifestError(f"line {lineno}: missing file: {raw_name}")
        observed = digest(path)
        if observed.lower() != expected.lower():
            raise ManifestError(f"line {lineno}: checksum mismatch: {raw_name}")
        count += 1

    if count == 0:
        raise ManifestError("manifest contains no file records")
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    try:
        count = verify(args.manifest)
    except (OSError, UnicodeError, ManifestError) as exc:
        print(f"checksum-manifest-verify: error: {exc}", file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"checksum-manifest-verify: ok entries={count} manifest={args.manifest.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
