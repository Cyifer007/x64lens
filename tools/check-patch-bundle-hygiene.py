#!/usr/bin/env python3
"""Validate public x64lens patch/source ZIP member paths without extraction.

The checker is intentionally path-policy focused. It rejects unsafe archive
names, private/local state, generated outputs, and opaque nested artifacts under
any archive-root layout. It does not infer repository truth from a preferred
prefix such as ``x64lens/`` or ``changed-files/``.
"""
from __future__ import annotations

import argparse
import re
import stat
import struct
import sys
import unicodedata
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path

WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
WINDOWS_FORBIDDEN_CHARS = frozenset('< > " | ? *'.replace(" ", ""))
PUBLIC_ARCHIVE_COMMENT_RE = re.compile(rb"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
WINDOWS_RESERVED_BASENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CLOCK$",
    "CONIN$",
    "CONOUT$",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
    *(f"COM{index}" for index in "¹²³"),
    *(f"LPT{index}" for index in "¹²³"),
}

PRIVATE_DIRS = {
    ".git",
    ".local",
    ".codex",
    ".codex-log",
    ".agents",
    "private-notes",
    "local-context",
    "private",
    "proprietary",
    "malware",
    "secrets",
    "course-materials",
}

GENERATED_DIRS = {
    "build",
    "dist",
    "out",
    "__pycache__",
    ".venv",
    "venv",
    ".cache",
    ".tmp",
    ".vagrant",
    "packer_cache",
}

PRIVATE_BASENAMES = {
    "agents.override.md",
    "project_context.md",
    "project_state.md",
}

PRIVATE_PATHS = {
    ("docs", "project-context-upload-guide.md"),
    ("docs", "csc-773-integration.md"),
    ("docs", "contracts", "context-persistence-contract.md"),
    ("docs", "ai-use-disclosure.md"),
}

FORBIDDEN_SUFFIXES = {
    ".o",
    ".pyc",
    ".pyo",
    ".pyd",
    ".docx",
    ".pdf",
    ".pcap",
    ".pcapng",
    ".ova",
    ".ovf",
    ".vmdk",
    ".vdi",
    ".qcow2",
    ".iso",
}

NESTED_ARCHIVE_SUFFIXES = {
    ".zip",
    ".tar",
    ".tgz",
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
    ".jar",
    ".war",
    ".ear",
    ".whl",
    ".apk",
    ".xpi",
    ".ipa",
    ".epub",
}

GENERATED_TOY_BASENAMES = {
    "minimal_nopie",
    "minimal_pie_canary",
    "minimal_execstack",
    "gadgets",
    "gadgets_capacity_exact",
    "gadgets_capacity",
}


@dataclass(frozen=True)
class MemberPath:
    original: str
    normalized: str
    parts: tuple[str, ...]
    folded_parts: tuple[str, ...]
    is_directory: bool


@dataclass(frozen=True)
class Violation:
    member: str
    reason: str


def contains_sequence(parts: tuple[str, ...], sequence: tuple[str, ...]) -> bool:
    width = len(sequence)
    return any(parts[index : index + width] == sequence for index in range(len(parts) - width + 1))


def normalize_member(info: zipfile.ZipInfo) -> MemberPath:
    original = info.filename
    raw_original = getattr(info, "orig_filename", original)
    if not original:
        raise ValueError("empty archive member name")
    if raw_original != original:
        raise ValueError("raw and effective ZIP member names disagree")
    if CONTROL_RE.search(original):
        raise ValueError("control character in archive member name")
    if any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in original):
        raise ValueError("Unicode control, format, or surrogate character in archive member name")
    if "\\" in original:
        raise ValueError("backslash path separator is not portable")
    if original.startswith("/") or original.startswith("//") or WINDOWS_DRIVE_RE.match(original):
        raise ValueError("absolute or drive-qualified archive path")

    is_directory = info.is_dir() or original.endswith("/")
    normalized = original[:-1] if is_directory and original.endswith("/") else original
    parts = tuple(normalized.split("/"))
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("non-canonical or traversing archive path")
    if any(part.endswith((" ", ".")) for part in parts):
        raise ValueError("Windows-ambiguous trailing space or dot")
    if any(any(character in WINDOWS_FORBIDDEN_CHARS for character in part) for part in parts):
        raise ValueError("Windows-forbidden character in archive path")
    if any(":" in part for part in parts):
        raise ValueError("colon-bearing archive path is not portable")
    if any(part.split(".", 1)[0].upper() in WINDOWS_RESERVED_BASENAMES for part in parts):
        raise ValueError("Windows-reserved device name in archive path")
    if any(unicodedata.normalize("NFC", part) != part for part in parts):
        raise ValueError("non-NFC Unicode archive path")

    return MemberPath(
        original=original,
        normalized="/".join(parts),
        parts=parts,
        folded_parts=tuple(part.casefold() for part in parts),
        is_directory=is_directory,
    )


def forbidden_reason(member: MemberPath) -> str | None:
    parts = member.folded_parts
    basename = parts[-1]

    for directory in PRIVATE_DIRS:
        if directory.casefold() in parts:
            return f"private/local directory '{directory}'"

    if basename in PRIVATE_BASENAMES:
        return f"private/local file '{member.parts[-1]}'"
    if basename.endswith(".private.md"):
        return "private Markdown file"
    if basename == ".env.example":
        pass
    elif basename == ".env" or basename.startswith(".env."):
        return "local environment file"

    for private_path in PRIVATE_PATHS:
        folded = tuple(part.casefold() for part in private_path)
        if contains_sequence(parts, folded):
            return f"private repository path '{'/'.join(private_path)}'"

    if contains_sequence(parts, ("paper", "csc773")):
        return "private course-paper directory"

    for directory in GENERATED_DIRS:
        if directory.casefold() in parts:
            return f"generated/local directory '{directory}'"

    if contains_sequence(parts, ("tests", "bin")):
        return "generated test binary directory"
    if contains_sequence(parts, ("tests", "results")):
        return "generated test result directory"

    if contains_sequence(parts, ("benchmarks", "results")):
        if not (len(parts) >= 3 and parts[-3:] == ("benchmarks", "results", ".gitkeep")):
            if parts[-2:] != ("benchmarks", "results"):
                return "generated benchmark result"

    if contains_sequence(parts, ("tests", "toy-src")) and basename in GENERATED_TOY_BASENAMES:
        return "generated toy binary"

    lower_name = basename.casefold()
    if "syllabus" in lower_name and lower_name.endswith(".pdf"):
        return "private course PDF"
    if any(lower_name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
        return "generated/private file type"
    if any(lower_name.endswith(suffix) for suffix in NESTED_ARCHIVE_SUFFIXES):
        return "nested archive"

    return None



def inspect_extra_fields(info: zipfile.ZipInfo, member: MemberPath) -> list[str]:
    """Validate recognized ZIP metadata and reject opaque name/type overrides."""

    violations: list[str] = []
    data = info.extra
    offset = 0
    while offset < len(data):
        if len(data) - offset < 4:
            violations.append("truncated ZIP extra-field header")
            break
        header_id, size = struct.unpack_from("<HH", data, offset)
        offset += 4
        if size > len(data) - offset:
            violations.append(f"truncated ZIP extra field 0x{header_id:04x}")
            break
        payload = data[offset : offset + size]
        offset += size

        if header_id == 0x5455:  # extended timestamp
            if not payload:
                violations.append("empty extended-timestamp extra field")
                continue
            flags = payload[0]
            full_size = 1 + 4 * sum(bool(flags & bit) for bit in (1, 2, 4))
            central_size = 5 if flags & 0x01 else 1
            if flags & ~0x07 or len(payload) not in {central_size, full_size}:
                violations.append("malformed extended-timestamp extra field")
        elif header_id == 0x7075:  # Info-ZIP Unicode path
            if len(payload) < 5 or payload[0] != 1:
                violations.append("malformed Unicode-path extra field")
                continue
            try:
                unicode_name = payload[5:].decode("utf-8")
                raw_name = member.original.encode(
                    "utf-8" if info.flag_bits & 0x800 else "cp437"
                )
            except (UnicodeDecodeError, UnicodeEncodeError):
                violations.append("invalid Unicode-path extra field encoding")
                continue
            expected_crc = struct.unpack_from("<I", payload, 1)[0]
            if zlib.crc32(raw_name) & 0xFFFFFFFF != expected_crc:
                violations.append("Unicode-path extra field has an invalid name CRC")
            if unicode_name != member.original:
                violations.append("Unicode-path extra field disagrees with member name")
        elif header_id == 0x7875:  # Info-ZIP Unix UID/GID
            if len(payload) < 3 or payload[0] != 1:
                violations.append("malformed Unix UID/GID extra field")
                continue
            uid_len = payload[1]
            uid_end = 2 + uid_len
            if uid_len > 8 or uid_end >= len(payload):
                violations.append("malformed Unix UID/GID extra field")
                continue
            gid_len = payload[uid_end]
            if gid_len > 8 or uid_end + 1 + gid_len != len(payload):
                violations.append("malformed Unix UID/GID extra field")
        elif header_id == 0x0001:  # ZIP64 sizes/offsets
            if len(payload) not in {8, 16, 24, 28}:
                violations.append("malformed ZIP64 extra field")
        elif header_id == 0x000A:  # NTFS timestamps
            if len(payload) < 4:
                violations.append("malformed NTFS extra field")
                continue
            cursor = 4
            while cursor < len(payload):
                if len(payload) - cursor < 4:
                    violations.append("truncated NTFS extra-field attribute")
                    break
                tag, length = struct.unpack_from("<HH", payload, cursor)
                cursor += 4
                if length > len(payload) - cursor:
                    violations.append("truncated NTFS extra-field value")
                    break
                if tag != 0x0001 or length != 24:
                    violations.append("unsupported NTFS extra-field attribute")
                cursor += length
        elif header_id in {0x5855, 0x7855}:  # legacy Info-ZIP Unix metadata
            if len(payload) not in {8, 12}:
                violations.append("malformed legacy Unix extra field")
        else:
            violations.append(f"unsupported ZIP extra field 0x{header_id:04x}")

    return violations

def inspect_bundle(bundle: Path) -> tuple[int, list[Violation]]:
    violations: list[Violation] = []
    seen: dict[str, str] = {}

    with zipfile.ZipFile(bundle) as archive:
        infos = archive.infolist()
        if not infos:
            return 0, [Violation("<archive>", "bundle is empty")]

        archive_comment = archive.comment.strip()
        if archive_comment and not PUBLIC_ARCHIVE_COMMENT_RE.fullmatch(archive_comment):
            violations.append(
                Violation(
                    "<archive-comment>",
                    "archive comment must be empty or a 40/64-character hexadecimal source identity",
                )
            )

        for info in infos:
            try:
                member = normalize_member(info)
            except ValueError as exc:
                violations.append(Violation(info.filename or "<empty>", f"unsafe path: {exc}"))
                continue

            portable_key = unicodedata.normalize("NFC", member.normalized).casefold()
            prior = seen.get(portable_key)
            if prior is not None:
                violations.append(
                    Violation(member.original, f"duplicate or case-colliding path (already present as '{prior}')")
                )
            else:
                seen[portable_key] = member.original

            unix_mode = info.external_attr >> 16
            if unix_mode and stat.S_ISLNK(unix_mode):
                violations.append(Violation(member.original, "symbolic-link member is not permitted"))
            file_type = stat.S_IFMT(unix_mode)
            if file_type not in {0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK}:
                violations.append(Violation(member.original, "special-file member is not permitted"))
            dos_directory = bool(info.external_attr & 0x10)
            if member.is_directory and file_type == stat.S_IFREG:
                violations.append(Violation(member.original, "directory name carries regular-file metadata"))
            if not member.is_directory and (file_type == stat.S_IFDIR or dos_directory):
                violations.append(Violation(member.original, "file name carries directory metadata"))
            for extra_violation in inspect_extra_fields(info, member):
                violations.append(Violation(member.original, extra_violation))
            if info.flag_bits & 0x1:
                violations.append(Violation(member.original, "encrypted member is not inspectable"))
            if info.comment:
                violations.append(Violation(member.original, "per-member ZIP comments are not permitted"))

            reason = forbidden_reason(member)
            if reason is not None:
                violations.append(Violation(member.original, reason))

        return len(infos), violations


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="check x64lens public patch/source ZIP hygiene")
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args(argv)

    if not args.bundle.is_file():
        print(f"patch-bundle-hygiene: error: not a file: {args.bundle}", file=sys.stderr)
        return 1

    try:
        entry_count, violations = inspect_bundle(args.bundle)
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        print(f"patch-bundle-hygiene: error: cannot inspect {args.bundle}: {exc}", file=sys.stderr)
        return 1

    if violations:
        for violation in violations:
            print(
                f"patch-bundle-hygiene: forbidden member: {violation.member}: {violation.reason}",
                file=sys.stderr,
            )
        print(
            f"patch-bundle-hygiene: failed entries={entry_count} violations={len(violations)}",
            file=sys.stderr,
        )
        return 1

    print(f"patch-bundle-hygiene: ok entries={entry_count} bundle={args.bundle}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
