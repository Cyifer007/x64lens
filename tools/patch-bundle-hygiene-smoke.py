#!/usr/bin/env python3
"""Regression-test root-independent public bundle policy and unsafe ZIP names."""
from __future__ import annotations

import importlib.util
import stat
import subprocess
import sys
import tempfile
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "tools" / "check-patch-bundle-hygiene.sh"
POLICY_PATH = ROOT / "tools" / "check-patch-bundle-hygiene.py"

spec = importlib.util.spec_from_file_location("x64lens_bundle_hygiene", POLICY_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load bundle policy: {POLICY_PATH}")
POLICY = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = POLICY
spec.loader.exec_module(POLICY)


@dataclass(frozen=True)
class Case:
    name: str
    members: tuple[str, ...]
    expected_success: bool
    expected_reason: str | None = None
    symlink: tuple[str, str] | None = None
    archive_comment: bytes = b""
    member_comment: tuple[str, bytes] | None = None


def make_zip(path: Path, case: Case) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.comment = case.archive_comment
            for member in case.members:
                if case.member_comment is not None and case.member_comment[0] == member:
                    info = zipfile.ZipInfo(member)
                    info.comment = case.member_comment[1]
                    archive.writestr(info, "fixture\n")
                else:
                    archive.writestr(member, "fixture\n")
            if case.symlink is not None:
                name, target = case.symlink
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, target)


def run_case(directory: Path, case: Case) -> None:
    archive = directory / f"{case.name}.zip"
    make_zip(archive, case)
    entry_count, violations = POLICY.inspect_bundle(archive)
    stderr = "\n".join(f"{item.member}: {item.reason}" for item in violations)
    if case.expected_success and violations:
        raise RuntimeError(f"{case.name}: clean archive rejected: {stderr}")
    if not case.expected_success and not violations:
        raise RuntimeError(f"{case.name}: forbidden archive accepted")
    if case.expected_reason and case.expected_reason not in stderr:
        raise RuntimeError(
            f"{case.name}: expected reason {case.expected_reason!r} not found in {stderr!r}"
        )
    if entry_count != len(case.members) + (1 if case.symlink is not None else 0):
        raise RuntimeError(f"{case.name}: unexpected entry count {entry_count}")


def run_wrapper_probe(directory: Path) -> None:
    archive = directory / "wrapper-probe.zip"
    make_zip(archive, Case("wrapper-probe", ("src/main.asm",), True))
    result = subprocess.run(
        ["bash", str(CHECKER), str(archive)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    if result.returncode != 0 or "patch-bundle-hygiene: ok" not in result.stdout:
        raise RuntimeError(f"wrapper probe failed: {result.stdout}{result.stderr}")


def cases() -> list[Case]:
    clean = [
        Case("clean-zero-root", ("src/main.asm",), True),
        Case("clean-one-root", ("root/src/main.asm", "root/.env.example"), True),
        Case("clean-changed-files", ("changed-files/src/main.asm", "PATCH_RUNBOOK.md"), True),
        Case("clean-benchmark-gitkeep", ("benchmarks/results/.gitkeep",), True),
        Case(
            "clean-source-identity-comment",
            ("src/main.asm",),
            True,
            archive_comment=b"1c79197ff8fa748d96a61356829c1b1d053fa027",
        ),
    ]

    rejected = [
        Case("generated-zero-root", ("src/main.asm", "tests/bin/gadgets"), False, "generated test binary"),
        Case("generated-one-root", ("root/src/main.asm", "root/tests/results/result.json"), False, "generated test result"),
        Case("generated-multiple-roots", ("a/src/main.asm", "b/benchmarks/results/run.tsv"), False, "generated benchmark result"),
        Case("generated-deep-root", ("a/b/src/main.asm", "a/b/build/main.o"), False, "generated/local directory"),
        Case("generated-toy-deep-root", ("a/tests/toy-src/subdir/gadgets",), False, "generated toy binary"),
        Case("private-zero-git", ("src/main.asm", ".git/config"), False, "private/local directory"),
        Case("private-zero-local", ("src/main.asm", ".local/codex/report.md"), False, "private/local directory"),
        Case("private-zero-codex", ("src/main.asm", ".codex/config.toml"), False, "private/local directory"),
        Case("private-zero-agents-override", ("src/main.asm", "AGENTS.override.md"), False, "private/local file"),
        Case("private-zero-env", ("src/main.asm", ".env"), False, "local environment file"),
        Case("private-rooted-project-context", ("root/src/main.asm", "root/PROJECT_CONTEXT.md"), False, "private/local file"),
        Case("private-rooted-secrets", ("root/src/main.asm", "root/secrets/key.txt"), False, "private/local directory"),
        Case("private-project-state", ("PROJECT_STATE.md",), False, "private/local file"),
        Case("private-notes", ("root/private-notes/notes.md",), False, "private/local directory"),
        Case("private-local-context", ("root/local-context/state.md",), False, "private/local directory"),
        Case("private-course-contract", ("docs/contracts/context-persistence-contract.md",), False, "private repository path"),
        Case("private-docx", ("root/course-materials/homework.docx",), False, "private/local directory"),
        Case("private-pdf", ("root/review.pdf",), False, "generated/private file type"),
        Case("nested-archive", ("root/evidence.tar.gz",), False, "nested archive"),
        Case("unsafe-parent", ("../outside.txt",), False, "unsafe path"),
        Case("unsafe-embedded-parent", ("root/../outside.txt",), False, "unsafe path"),
        Case("unsafe-absolute", ("/absolute.txt",), False, "unsafe path"),
        Case("unsafe-drive", ("C:/private.txt",), False, "unsafe path"),
        Case("unsafe-backslash", (r"root\.git\config",), False, "unsafe path"),
        Case("unsafe-windows-device", ("root/CON.txt",), False, "Windows-reserved device"),
        Case("unsafe-unicode-format", ("root/secret\u202efile.txt",), False, "Unicode control"),
        Case("unsafe-unicode-normalization", ("root/cafe\u0301.txt",), False, "non-NFC Unicode"),
        Case("casefold-git", ("root/.GIT/config",), False, "private/local directory"),
        Case("casefold-env", ("root/.EnV",), False, "local environment file"),
        Case("case-collision", ("root/src/main.asm", "ROOT/SRC/MAIN.ASM"), False, "case-colliding"),
        Case("symlink-member", ("root/src/main.asm",), False, "symbolic-link", ("root/link", "../../.env")),
        Case(
            "private-archive-comment",
            ("root/src/main.asm",),
            False,
            "archive comment",
            archive_comment=b"private local handoff",
        ),
        Case(
            "private-member-comment",
            ("root/src/main.asm",),
            False,
            "per-member ZIP comments",
            member_comment=("root/src/main.asm", b"private note"),
        ),
    ]
    return clean + rejected


def main() -> int:
    all_cases = cases()
    with tempfile.TemporaryDirectory(prefix="x64lens-bundle-hygiene-") as temp:
        directory = Path(temp)
        for case in all_cases:
            run_case(directory, case)
        run_wrapper_probe(directory)

    accepted = sum(case.expected_success for case in all_cases)
    rejected = len(all_cases) - accepted
    print(f"patch-bundle-hygiene-smoke: ok cases={len(all_cases)} accepted={accepted} rejected={rejected}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"patch-bundle-hygiene-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
