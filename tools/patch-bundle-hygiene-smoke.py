#!/usr/bin/env python3
"""Regression-test root-independent public bundle policy and ZIP metadata."""
from __future__ import annotations

import importlib.util
import io
import stat
import struct
import subprocess
import sys
import tempfile
import warnings
import zipfile
import zlib
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
    member_extra: tuple[str, bytes] | None = None
    directory_metadata_member: str | None = None
    raw_nul_member: bool = False
    nested_zip_member: str | None = None
    local_name_override: bytes | None = None
    local_extra_override: bytes | None = None
    local_flags_xor: int = 0
    force_zip64_member: str | None = None


def extra_field(header_id: int, payload: bytes) -> bytes:
    return struct.pack("<HH", header_id, len(payload)) + payload


def nested_zip_payload() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("inner.txt", "nested\n")
    return buffer.getvalue()


def make_zip(path: Path, case: Case) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.comment = case.archive_comment
            for member in case.members:
                payload: str | bytes = "fixture\n"
                if case.nested_zip_member == member:
                    payload = nested_zip_payload()
                if case.force_zip64_member == member:
                    info = zipfile.ZipInfo(member)
                    with archive.open(info, "w", force_zip64=True) as handle:
                        handle.write(payload.encode("utf-8") if isinstance(payload, str) else payload)
                    continue
                if (
                    (case.member_comment is not None and case.member_comment[0] == member)
                    or (case.member_extra is not None and case.member_extra[0] == member)
                    or case.directory_metadata_member == member
                ):
                    info = zipfile.ZipInfo(member)
                    if case.member_comment is not None and case.member_comment[0] == member:
                        info.comment = case.member_comment[1]
                    if case.member_extra is not None and case.member_extra[0] == member:
                        info.extra = case.member_extra[1]
                    if case.directory_metadata_member == member:
                        info.create_system = 3
                        info.external_attr = (stat.S_IFDIR | 0o755) << 16
                    archive.writestr(info, payload)
                else:
                    archive.writestr(member, payload)
            if case.symlink is not None:
                name, target = case.symlink
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, target)

    if case.raw_nul_member:
        marker = case.members[0].encode("ascii")
        if b"X" not in marker:
            raise RuntimeError(f"{case.name}: raw-NUL marker must contain X")
        replacement = marker.replace(b"X", b"\0", 1)
        blob = path.read_bytes()
        if blob.count(marker) != 2:
            raise RuntimeError(f"{case.name}: expected local and central raw-name copies")
        path.write_bytes(blob.replace(marker, replacement))

    if case.local_name_override is not None or case.local_extra_override is not None or case.local_flags_xor:
        blob = bytearray(path.read_bytes())
        local_offset = blob.find(b"PK\x03\x04")
        if local_offset < 0:
            raise RuntimeError(f"{case.name}: local header not found")
        name_length, extra_length = struct.unpack_from("<HH", blob, local_offset + 26)
        name_offset = local_offset + 30
        extra_offset = name_offset + name_length
        if case.local_name_override is not None:
            if len(case.local_name_override) != name_length:
                raise RuntimeError(f"{case.name}: local name override length mismatch")
            blob[name_offset : name_offset + name_length] = case.local_name_override
        if case.local_extra_override is not None:
            if len(case.local_extra_override) != extra_length:
                raise RuntimeError(f"{case.name}: local extra override length mismatch")
            blob[extra_offset : extra_offset + extra_length] = case.local_extra_override
        if case.local_flags_xor:
            flags = struct.unpack_from("<H", blob, local_offset + 6)[0]
            struct.pack_into("<H", blob, local_offset + 6, flags ^ case.local_flags_xor)
        path.write_bytes(blob)


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



def run_wrapper_replay(directory: Path, all_cases: list[Case]) -> None:
    clean_archives = [directory / f"{case.name}.zip" for case in all_cases if case.expected_success]
    rejected_archives = [directory / f"{case.name}.zip" for case in all_cases if not case.expected_success]

    clean = subprocess.run(
        ["bash", str(CHECKER), *(str(path) for path in clean_archives)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if clean.returncode != 0:
        raise RuntimeError(f"production wrapper rejected a clean batch: {clean.stdout}{clean.stderr}")
    for archive in clean_archives:
        if f"bundle={archive}" not in clean.stdout:
            raise RuntimeError(f"production wrapper omitted clean archive result: {archive}")

    rejected = subprocess.run(
        ["bash", str(CHECKER), *(str(path) for path in rejected_archives)],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if rejected.returncode != 1:
        raise RuntimeError(
            f"production wrapper negative batch returned {rejected.returncode}: "
            f"{rejected.stdout}{rejected.stderr}"
        )
    for archive in rejected_archives:
        if f"failed bundle={archive}" not in rejected.stderr and f"cannot inspect {archive}" not in rejected.stderr:
            raise RuntimeError(f"production wrapper failed to reject/archive-report: {archive}")


def cases() -> list[Case]:
    timestamp_extra = extra_field(0x5455, b"\x01\x00\x00\x00\x00")
    visible_name = b"root/src/main.asm"
    unicode_override = extra_field(
        0x7075,
        b"\x01" + struct.pack("<I", zlib.crc32(visible_name) & 0xFFFFFFFF) + b"root/.git/config",
    )
    private_extra = extra_field(0xCAFE, b"private local handoff")
    uid_gid_zero = extra_field(0x7875, b"\x01\x00\x00")
    unneeded_zip64 = extra_field(0x0001, struct.pack("<Q", 0x1234))
    ntfs_nonzero_reserved = extra_field(0x000A, b"\x01\x00\x00\x00")
    duplicate_timestamps = timestamp_extra + extra_field(0x5455, b"\x01\x01\x00\x00\x00")
    clean_unicode = extra_field(
        0x7075,
        b"\x01" + struct.pack("<I", zlib.crc32(b"root/src/good.txt") & 0xFFFFFFFF) + b"root/src/good.txt",
    )
    private_unicode = extra_field(
        0x7075,
        b"\x01" + struct.pack("<I", zlib.crc32(b"root/src/good.txt") & 0xFFFFFFFF) + b"root/.git/configX",
    )

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
        Case(
            "clean-extended-timestamp",
            ("root/src/main.asm",),
            True,
            member_extra=("root/src/main.asm", timestamp_extra),
        ),
        Case(
            "clean-local-zip64-sentinel",
            ("root/src/good.txt",),
            True,
            force_zip64_member="root/src/good.txt",
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
        Case("nested-jar", ("root/evidence.jar",), False, "nested archive", nested_zip_member="root/evidence.jar"),
        Case("nested-whl", ("root/evidence.whl",), False, "nested archive", nested_zip_member="root/evidence.whl"),
        Case("unsafe-parent", ("../outside.txt",), False, "unsafe path"),
        Case("unsafe-embedded-parent", ("root/../outside.txt",), False, "unsafe path"),
        Case("unsafe-absolute", ("/absolute.txt",), False, "unsafe path"),
        Case("unsafe-drive", ("C:/private.txt",), False, "unsafe path"),
        Case("unsafe-backslash", (r"root\.git\config",), False, "unsafe path"),
        Case("unsafe-windows-device", ("root/CON.txt",), False, "Windows-reserved device"),
        Case("unsafe-windows-com-superscript", ("root/COM¹.txt",), False, "Windows-reserved device"),
        Case("unsafe-windows-lpt-superscript", ("root/LPT³",), False, "Windows-reserved device"),
        Case("unsafe-windows-conin", ("root/CONIN$",), False, "Windows-reserved device"),
        Case("unsafe-windows-conout", ("root/CONOUT$.txt",), False, "Windows-reserved device"),
        Case("unsafe-windows-less-than", ("root/bad<name.asm",), False, "Windows-forbidden character"),
        Case("unsafe-windows-greater-than", ("root/bad>name.asm",), False, "Windows-forbidden character"),
        Case("unsafe-windows-quote", ('root/bad"name.asm',), False, "Windows-forbidden character"),
        Case("unsafe-windows-pipe", ("root/bad|name.asm",), False, "Windows-forbidden character"),
        Case("unsafe-windows-question", ("root/bad?name.asm",), False, "Windows-forbidden character"),
        Case("unsafe-windows-star", ("root/bad*name.asm",), False, "Windows-forbidden character"),
        Case("unsafe-unicode-format", ("root/secret\u202efile.txt",), False, "Unicode control"),
        Case("unsafe-unicode-normalization", ("root/cafe\u0301.txt",), False, "non-NFC Unicode"),
        Case("unsafe-raw-nul", ("root/src/main.asmX/.git/config",), False, "control character", raw_nul_member=True),
        Case(
            "unsafe-unicode-path-override",
            ("root/src/main.asm",),
            False,
            "Unicode-path extra field disagrees",
            member_extra=("root/src/main.asm", unicode_override),
        ),
        Case(
            "unsafe-unknown-extra-field",
            ("root/src/main.asm",),
            False,
            "unsupported ZIP extra field",
            member_extra=("root/src/main.asm", private_extra),
        ),
        Case(
            "unsafe-file-directory-metadata",
            ("root/src/main.asm",),
            False,
            "file name carries directory metadata",
            directory_metadata_member="root/src/main.asm",
        ),
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
        Case(
            "uidgid-zero-length-identifiers",
            ("root/src/good.txt",),
            False,
            "malformed Unix UID/GID",
            member_extra=("root/src/good.txt", uid_gid_zero),
        ),
        Case(
            "zip64-unneeded-contradictory-size",
            ("root/src/good.txt",),
            False,
            "without a matching sentinel",
            member_extra=("root/src/good.txt", unneeded_zip64),
        ),
        Case(
            "ntfs-nonzero-reserved-no-attribute",
            ("root/src/good.txt",),
            False,
            "nonzero reserved bytes",
            member_extra=("root/src/good.txt", ntfs_nonzero_reserved),
        ),
        Case(
            "duplicate-conflicting-timestamps",
            ("root/src/good.txt",),
            False,
            "duplicate ZIP extra field",
            member_extra=("root/src/good.txt", duplicate_timestamps),
        ),
        Case(
            "local-name-private-central-name-clean",
            ("root/src/good.txt",),
            False,
            "local and central member names disagree",
            local_name_override=b"root/.git/configX",
        ),
        Case(
            "local-unknown-extra-central-timestamp",
            ("root/src/good.txt",),
            False,
            "local unsupported ZIP extra field",
            member_extra=("root/src/good.txt", timestamp_extra),
            local_extra_override=extra_field(0xCAFE, b"local"),
        ),
        Case(
            "local-unicode-private-central-unicode-clean",
            ("root/src/good.txt",),
            False,
            "local Unicode-path extra field disagrees",
            member_extra=("root/src/good.txt", clean_unicode),
            local_extra_override=private_unicode,
        ),
        Case(
            "local-encrypted-central-clear",
            ("root/src/good.txt",),
            False,
            "local and central flag metadata disagree",
            local_flags_xor=0x0001,
        ),
    ]
    return clean + rejected


def main() -> int:
    all_cases = cases()
    with tempfile.TemporaryDirectory(prefix="x64lens-bundle-hygiene-") as temp:
        directory = Path(temp)
        for case in all_cases:
            run_case(directory, case)
        run_wrapper_replay(directory, all_cases)

    accepted = sum(case.expected_success for case in all_cases)
    rejected = len(all_cases) - accepted
    print(
        "patch-bundle-hygiene-smoke: ok "
        f"cases={len(all_cases)} accepted={accepted} rejected={rejected} wrapper_replays={len(all_cases)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"patch-bundle-hygiene-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
