#!/usr/bin/env python3
"""Enforce x64lens public text and distributable-artifact content boundaries.

Repository scans and ZIP-content scans share one policy. ZIP content inspection
is deliberately separate from the metadata-only archive safety checker: this
module reads bounded textual member payloads but never extracts them.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator

ROOT = Path(__file__).resolve().parents[1]
MAX_TEXT_BYTES = 4 * 1024 * 1024
MAX_ZIP_TEXT_BYTES = 32 * 1024 * 1024
MAX_ZIP_MEMBERS = 4096

PUBLIC_PATHS = (
    "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
    "CODE_OF_CONDUCT.md", "Dockerfile", "Makefile", ".github", "docs",
    "paper", "src", "include", "tests", "tools", "benchmarks", "schemas",
)
TEXT_SUFFIXES = {
    ".md", ".asm", ".inc", ".sh", ".py", ".yml", ".yaml", ".json",
    ".tex", ".bib", ".patch", ".diff", ".txt", ".tsv",
}
TEXT_BASENAMES = {"Makefile", "Dockerfile"}
SELF_EXCLUSIONS = {
    "tools/check-public-content.py",
    "tools/check-public-docs.sh",
}
PATH_EXCLUSIONS = (
    "tests/bin/", "tests/results/", "tests/invalid/", "benchmarks/results/",
    ".local/", ".codex/", ".codex-log/", ".agents/",
)

CASE_SENSITIVE = tuple(
    re.compile(pattern)
    for pattern in (
        r"/mnt/data/",
        r"^\s*[A-Za-z0-9._-]+@[A-Za-z0-9._-]+:([~/]|[A-Za-z]:)",
        r"DESKTOP-[A-Z0-9-]+",
        r"x64lens_patch_[0-9]+",
        r"user-created whole-repository zip snapshots",
        r"in our (chat|conversation)",
        r"the file you (uploaded|attached)",
        r"as discussed in (chat|the conversation)",
        r"Codex",
        r"CODEX_LOCAL_MISSION",
    )
)
CASE_INSENSITIVE = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"x64lens[_ -]*(HEAD|source)[_ -]*[0-9]{8}[_ -]*[0-9]{6}([_ (.-]*(copy|[0-9]+)[) ]*)?[.]zip",
        r"x64lens[_ -]*(codex[_ -]*evidence|evidence)[_ -]*[0-9]{8}[_ -]*[0-9]{6}([_ (.-]*(copy|[0-9]+)[) ]*)?[.]tar[.]gz",
        r"[.]local/codex/reports/",
        # These phrases were removed from public source but remained recoverable
        # from a distributed unified diff. They describe private execution
        # context rather than repository behavior.
        r"^--.*private local agent workspaces",
        r"^--.*restricted filesystem sandbox",
        r"self[- ]authenticating application and evidence package",
        r"artifact[- ]supply findings",
    )
)
HOME_PATHS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"/home/[A-Za-z0-9._-]+(/|$)",
        r"/Users/[A-Za-z0-9._-]+(/|$)",
        r"/mnt/[A-Za-z]/Users/[A-Za-z0-9._-]+/",
        r"[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9._-]+[\\/]",
        r"\\\\wsl([.]localhost)?\\[^\\]+\\home\\[A-Za-z0-9._-]+[\\]",
    )
)


class PolicyError(RuntimeError):
    """Raised for malformed or unbounded content inputs."""


def is_text_candidate(name: str) -> bool:
    pure = PurePosixPath(name.replace("\\", "/"))
    return pure.name in TEXT_BASENAMES or pure.suffix.lower() in TEXT_SUFFIXES


def path_matches_or_contains(normalized: str, repository_path: str) -> bool:
    """Match a repository-relative path under any archive-root prefix."""
    target = repository_path.rstrip("/")
    return normalized == target or normalized.endswith("/" + target) or (
        repository_path.endswith("/") and f"/{target}/" in f"/{normalized}/"
    )


def is_public_candidate(name: str) -> bool:
    normalized = name.replace("\\", "/").lstrip("./")
    if any(path_matches_or_contains(normalized, excluded) for excluded in SELF_EXCLUSIONS):
        return False
    if any(path_matches_or_contains(normalized, excluded) for excluded in PATH_EXCLUSIONS):
        return False
    return is_text_candidate(normalized)


def collect_repository_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *PUBLIC_PATHS],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        names = result.stdout.splitlines()
    except (FileNotFoundError, subprocess.CalledProcessError):
        names = []
        for root_name in PUBLIC_PATHS:
            path = ROOT / root_name
            if path.is_file():
                names.append(root_name)
            elif path.is_dir():
                names.extend(str(item.relative_to(ROOT)) for item in path.rglob("*") if item.is_file())
    return sorted({ROOT / name for name in names if is_public_candidate(name)})


def scan_text(label: str, data: bytes, *, dockerfile: bool = False) -> list[str]:
    if len(data) > MAX_TEXT_BYTES:
        raise PolicyError(f"{label}: text candidate exceeds {MAX_TEXT_BYTES} bytes")
    text = data.decode("utf-8", errors="replace")
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for expression in CASE_SENSITIVE:
            if expression.search(line):
                findings.append(f"{label}:{lineno}: {line}")
        for expression in CASE_INSENSITIVE:
            if expression.search(line):
                findings.append(f"{label}:{lineno}: {line}")
        if not dockerfile:
            for expression in HOME_PATHS:
                if expression.search(line):
                    findings.append(f"{label}:{lineno}: {line}")
    return findings


def scan_paths(paths: Iterable[Path]) -> tuple[int, list[str]]:
    count = 0
    findings: list[str] = []
    for path in paths:
        if not path.is_file():
            raise PolicyError(f"missing public text file: {path}")
        label = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        if not is_text_candidate(label):
            continue
        count += 1
        findings.extend(scan_text(label, path.read_bytes(), dockerfile=Path(label).name == "Dockerfile"))
    return count, findings


def scan_zip(path: Path) -> tuple[int, list[str]]:
    if not path.is_file():
        raise PolicyError(f"missing ZIP: {path}")
    count = 0
    total = 0
    findings: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_MEMBERS:
                raise PolicyError(f"ZIP has {len(infos)} members; maximum is {MAX_ZIP_MEMBERS}")
            for info in infos:
                if info.is_dir() or not is_public_candidate(info.filename):
                    continue
                if info.file_size > MAX_TEXT_BYTES:
                    raise PolicyError(f"{info.filename}: text member exceeds {MAX_TEXT_BYTES} bytes")
                total += info.file_size
                if total > MAX_ZIP_TEXT_BYTES:
                    raise PolicyError(f"ZIP textual payload exceeds {MAX_ZIP_TEXT_BYTES} bytes")
                data = archive.read(info)
                count += 1
                findings.extend(
                    scan_text(
                        f"{path.name}:{info.filename}",
                        data,
                        dockerfile=PurePosixPath(info.filename).name == "Dockerfile",
                    )
                )
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise PolicyError(f"cannot inspect ZIP {path}: {exc}") from exc
    return count, findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--zip", dest="zip_path", type=Path)
    args = parser.parse_args(argv)
    if args.zip_path is not None and args.paths:
        parser.error("paths and --zip are mutually exclusive")

    try:
        if args.zip_path is not None:
            count, findings = scan_zip(args.zip_path)
            banner = "public-artifact-content-check"
        else:
            paths = args.paths or collect_repository_files()
            if not paths:
                raise PolicyError("no public text files discovered")
            count, findings = scan_paths(paths)
            banner = "public-docs-check"
    except PolicyError as exc:
        print(f"public-content-check: error: {exc}", file=sys.stderr)
        return 2

    if findings:
        for finding in findings:
            print(finding)
        print(f"{banner}: prohibited public content detected", file=sys.stderr)
        return 1
    print(f"{banner}: ok files={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
