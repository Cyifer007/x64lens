#!/usr/bin/env python3
"""Validate public x64lens patch/source ZIP metadata without extraction.

The policy rejects unsafe names, private state, generated outputs, opaque nested
artifacts, contradictory local/central headers, and malformed recognized extra
fields under any archive-root layout. Payload bytes are never extracted or
interpreted by this checker.
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
from typing import BinaryIO

WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
WINDOWS_FORBIDDEN_CHARS = frozenset('< > " | ? *'.replace(" ", ""))
PUBLIC_ARCHIVE_COMMENT_RE = re.compile(rb"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")
WINDOWS_RESERVED_BASENAMES = {
    "CON", "PRN", "AUX", "NUL", "CLOCK$", "CONIN$", "CONOUT$",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
    *(f"COM{index}" for index in "¹²³"),
    *(f"LPT{index}" for index in "¹²³"),
}

PRIVATE_DIRS = {
    ".git", ".local", ".codex", ".codex-log", ".agents", "private-notes",
    "local-context", "private", "proprietary", "malware", "secrets",
    "course-materials",
}
GENERATED_DIRS = {
    "build", "dist", "out", "__pycache__", ".venv", "venv", ".cache",
    ".tmp", ".vagrant", "packer_cache",
}
PRIVATE_BASENAMES = {"agents.override.md", "project_context.md", "project_state.md"}
PRIVATE_PATHS = {
    ("docs", "project-context-upload-guide.md"),
    ("docs", "csc-773-integration.md"),
    ("docs", "contracts", "context-persistence-contract.md"),
    ("docs", "ai-use-disclosure.md"),
}
FORBIDDEN_SUFFIXES = {
    ".o", ".pyc", ".pyo", ".pyd", ".docx", ".pdf", ".pcap", ".pcapng",
    ".ova", ".ovf", ".vmdk", ".vdi", ".qcow2", ".iso",
}
NESTED_ARCHIVE_SUFFIXES = {
    ".zip", ".tar", ".tgz", ".tar.gz", ".tar.bz2", ".tar.xz", ".gz",
    ".bz2", ".xz", ".7z", ".rar", ".jar", ".war", ".ear", ".whl",
    ".apk", ".xpi", ".ipa", ".epub",
}
GENERATED_TOY_BASENAMES = {
    "minimal_nopie", "minimal_pie_canary", "minimal_execstack", "gadgets",
    "gadgets_sprint10", "gadgets_sprint10_transfer",
    "gadgets_sprint10_stack_adjust", "gadgets_sprint10_memory",
    "gadgets_capacity_exact", "gadgets_capacity",
}

LOCAL_FILE_HEADER = struct.Struct("<IHHHHHIIIHH")
CENTRAL_FILE_HEADER = struct.Struct("<IHHHHHHIIIHHHHHII")
END_OF_CENTRAL_DIRECTORY = struct.Struct("<IHHHHIIH")
LOCAL_SIGNATURE = 0x04034B50
CENTRAL_SIGNATURE = 0x02014B50
EOCD_SIGNATURE = 0x06054B50
UINT16_SENTINEL = 0xFFFF
UINT32_SENTINEL = 0xFFFFFFFF


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


@dataclass(frozen=True)
class CentralRecord:
    version_needed: int
    flags: int
    compression: int
    mod_time: int
    mod_date: int
    crc32: int
    compressed_size_32: int
    uncompressed_size_32: int
    disk_start_16: int
    external_attr: int
    local_header_offset_32: int
    raw_name: bytes
    extra: bytes
    comment: bytes


@dataclass(frozen=True)
class LocalRecord:
    version_needed: int
    flags: int
    compression: int
    mod_time: int
    mod_date: int
    crc32: int
    compressed_size_32: int
    uncompressed_size_32: int
    raw_name: bytes
    extra: bytes
    data_offset: int


def contains_sequence(parts: tuple[str, ...], sequence: tuple[str, ...]) -> bool:
    width = len(sequence)
    return any(parts[index : index + width] == sequence for index in range(len(parts) - width + 1))


def decode_member_name(raw_name: bytes, flags: int) -> str:
    encoding = "utf-8" if flags & 0x800 else "cp437"
    try:
        return raw_name.decode(encoding, errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"member name is not valid {encoding}") from exc


def normalize_member_name(original: str, is_directory: bool | None = None) -> MemberPath:
    if not original:
        raise ValueError("empty archive member name")
    if CONTROL_RE.search(original):
        raise ValueError("control character in archive member name")
    if any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in original):
        raise ValueError("Unicode control, format, or surrogate character in archive member name")
    if "\\" in original:
        raise ValueError("backslash path separator is not portable")
    if original.startswith("/") or original.startswith("//") or WINDOWS_DRIVE_RE.match(original):
        raise ValueError("absolute or drive-qualified archive path")

    directory = original.endswith("/") if is_directory is None else is_directory
    normalized = original[:-1] if directory and original.endswith("/") else original
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
        is_directory=directory,
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


def read_at(handle: BinaryIO, offset: int, size: int, file_size: int, label: str) -> bytes:
    if offset < 0 or size < 0 or offset > file_size or size > file_size - offset:
        raise ValueError(f"{label} extends outside the archive")
    handle.seek(offset)
    data = handle.read(size)
    if len(data) != size:
        raise ValueError(f"{label} is truncated")
    return data


def locate_central_directory(handle: BinaryIO, file_size: int) -> tuple[int, int, int, bytes]:
    tail_size = min(file_size, 22 + UINT16_SENTINEL)
    tail_offset = file_size - tail_size
    tail = read_at(handle, tail_offset, tail_size, file_size, "ZIP end record search window")
    marker = struct.pack("<I", EOCD_SIGNATURE)
    relative = tail.rfind(marker)
    if relative < 0:
        raise ValueError("missing end-of-central-directory record")
    absolute = tail_offset + relative
    fixed = read_at(handle, absolute, END_OF_CENTRAL_DIRECTORY.size, file_size, "ZIP end record")
    (
        signature,
        disk_number,
        central_disk,
        entries_on_disk,
        total_entries,
        central_size,
        central_offset,
        comment_length,
    ) = END_OF_CENTRAL_DIRECTORY.unpack(fixed)
    if signature != EOCD_SIGNATURE:
        raise ValueError("invalid end-of-central-directory signature")
    if absolute + END_OF_CENTRAL_DIRECTORY.size + comment_length != file_size:
        raise ValueError("end-of-central-directory comment length or trailing data is inconsistent")
    if disk_number != 0 or central_disk != 0 or entries_on_disk != total_entries:
        raise ValueError("multi-disk ZIP archives are not permitted")
    if (
        total_entries == UINT16_SENTINEL
        or central_size == UINT32_SENTINEL
        or central_offset == UINT32_SENTINEL
    ):
        raise ValueError("archive-level ZIP64 containers are not permitted for public patch bundles")
    if central_offset > absolute or central_size > absolute - central_offset:
        raise ValueError("central directory range is invalid")
    if central_offset + central_size != absolute:
        raise ValueError("unexpected data appears between the central directory and end record")
    comment = read_at(
        handle,
        absolute + END_OF_CENTRAL_DIRECTORY.size,
        comment_length,
        file_size,
        "ZIP archive comment",
    )
    return central_offset, central_size, total_entries, comment


def parse_central_records(
    handle: BinaryIO,
    file_size: int,
    central_offset: int,
    central_size: int,
    count: int,
) -> list[CentralRecord]:
    records: list[CentralRecord] = []
    cursor = central_offset
    limit = central_offset + central_size
    for index in range(count):
        fixed = read_at(handle, cursor, CENTRAL_FILE_HEADER.size, file_size, f"central header {index}")
        values = CENTRAL_FILE_HEADER.unpack(fixed)
        if values[0] != CENTRAL_SIGNATURE:
            raise ValueError(f"central header {index} has an invalid signature")
        (
            _signature,
            _version_made,
            version_needed,
            flags,
            compression,
            mod_time,
            mod_date,
            crc32,
            compressed_size_32,
            uncompressed_size_32,
            name_length,
            extra_length,
            comment_length,
            disk_start_16,
            _internal_attr,
            external_attr,
            local_header_offset_32,
        ) = values
        variable_size = name_length + extra_length + comment_length
        variable = read_at(
            handle,
            cursor + CENTRAL_FILE_HEADER.size,
            variable_size,
            file_size,
            f"central header {index} variable data",
        )
        if cursor + CENTRAL_FILE_HEADER.size + variable_size > limit:
            raise ValueError(f"central header {index} exceeds the central directory")
        raw_name = variable[:name_length]
        extra = variable[name_length : name_length + extra_length]
        comment = variable[name_length + extra_length :]
        records.append(
            CentralRecord(
                version_needed=version_needed,
                flags=flags,
                compression=compression,
                mod_time=mod_time,
                mod_date=mod_date,
                crc32=crc32,
                compressed_size_32=compressed_size_32,
                uncompressed_size_32=uncompressed_size_32,
                disk_start_16=disk_start_16,
                external_attr=external_attr,
                local_header_offset_32=local_header_offset_32,
                raw_name=raw_name,
                extra=extra,
                comment=comment,
            )
        )
        cursor += CENTRAL_FILE_HEADER.size + variable_size
    if cursor != limit:
        raise ValueError("central directory size does not match its member records")
    return records


def parse_local_record(handle: BinaryIO, file_size: int, offset: int, central_offset: int) -> LocalRecord:
    fixed = read_at(handle, offset, LOCAL_FILE_HEADER.size, file_size, "local file header")
    (
        signature,
        version_needed,
        flags,
        compression,
        mod_time,
        mod_date,
        crc32,
        compressed_size_32,
        uncompressed_size_32,
        name_length,
        extra_length,
    ) = LOCAL_FILE_HEADER.unpack(fixed)
    if signature != LOCAL_SIGNATURE:
        raise ValueError("local file header has an invalid signature")
    variable_size = name_length + extra_length
    variable = read_at(
        handle,
        offset + LOCAL_FILE_HEADER.size,
        variable_size,
        file_size,
        "local file header variable data",
    )
    data_offset = offset + LOCAL_FILE_HEADER.size + variable_size
    if data_offset > central_offset:
        raise ValueError("local file header overlaps the central directory")
    return LocalRecord(
        version_needed=version_needed,
        flags=flags,
        compression=compression,
        mod_time=mod_time,
        mod_date=mod_date,
        crc32=crc32,
        compressed_size_32=compressed_size_32,
        uncompressed_size_32=uncompressed_size_32,
        raw_name=variable[:name_length],
        extra=variable[name_length:],
        data_offset=data_offset,
    )


def parse_extra_blocks(data: bytes) -> tuple[list[tuple[int, bytes]], list[str]]:
    blocks: list[tuple[int, bytes]] = []
    violations: list[str] = []
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
        blocks.append((header_id, data[offset : offset + size]))
        offset += size
    return blocks, violations


def zip64_expectations(record: CentralRecord, info: zipfile.ZipInfo) -> list[tuple[str, int, int]]:
    expected: list[tuple[str, int, int]] = []
    if record.uncompressed_size_32 == UINT32_SENTINEL:
        expected.append(("uncompressed size", 8, info.file_size))
    elif record.uncompressed_size_32 != info.file_size:
        expected.append(("central uncompressed size mismatch", 0, info.file_size))
    if record.compressed_size_32 == UINT32_SENTINEL:
        expected.append(("compressed size", 8, info.compress_size))
    elif record.compressed_size_32 != info.compress_size:
        expected.append(("central compressed size mismatch", 0, info.compress_size))
    if record.local_header_offset_32 == UINT32_SENTINEL:
        expected.append(("local header offset", 8, info.header_offset))
    elif record.local_header_offset_32 != info.header_offset:
        expected.append(("central local-header offset mismatch", 0, info.header_offset))
    volume = int(getattr(info, "volume", 0))
    if record.disk_start_16 == UINT16_SENTINEL:
        expected.append(("disk start", 4, volume))
    elif record.disk_start_16 != volume:
        expected.append(("central disk-start mismatch", 0, volume))
    return expected


def local_zip64_expectations(record: LocalRecord, info: zipfile.ZipInfo) -> list[tuple[str, int, int]]:
    expected: list[tuple[str, int, int]] = []
    if record.uncompressed_size_32 == UINT32_SENTINEL:
        expected.append(("uncompressed size", 8, info.file_size))
    if record.compressed_size_32 == UINT32_SENTINEL:
        expected.append(("compressed size", 8, info.compress_size))
    return expected


def inspect_extra_fields(
    data: bytes,
    member: MemberPath,
    *,
    location: str,
    raw_name: bytes,
    flags: int,
    expected_zip64: list[tuple[str, int, int]],
) -> list[str]:
    """Validate recognized ZIP metadata and strict cross-platform semantics."""

    blocks, violations = parse_extra_blocks(data)
    seen_ids: set[int] = set()
    zip64_seen = False
    for header_id, payload in blocks:
        if header_id in seen_ids:
            violations.append(f"duplicate ZIP extra field 0x{header_id:04x}")
        seen_ids.add(header_id)

        if header_id == 0x5455:  # extended timestamp
            if not payload:
                violations.append("empty extended-timestamp extra field")
                continue
            timestamp_flags = payload[0]
            full_size = 1 + 4 * sum(bool(timestamp_flags & bit) for bit in (1, 2, 4))
            if location == "central":
                permitted = {1, 5 if timestamp_flags & 0x01 else 1, full_size}
            else:
                permitted = {full_size}
            if timestamp_flags & ~0x07 or len(payload) not in permitted:
                violations.append("malformed extended-timestamp extra field")
        elif header_id == 0x7075:  # Info-ZIP Unicode path
            if len(payload) < 5 or payload[0] != 1:
                violations.append("malformed Unicode-path extra field")
                continue
            try:
                unicode_name = payload[5:].decode("utf-8")
            except UnicodeDecodeError:
                violations.append("invalid Unicode-path extra field encoding")
                continue
            expected_crc = struct.unpack_from("<I", payload, 1)[0]
            if zlib.crc32(raw_name) & UINT32_SENTINEL != expected_crc:
                violations.append("Unicode-path extra field has an invalid name CRC")
            if unicode_name != member.original:
                violations.append("Unicode-path extra field disagrees with member name")
        elif header_id == 0x7875:  # Info-ZIP Unix UID/GID
            if len(payload) < 3 or payload[0] != 1:
                violations.append("malformed Unix UID/GID extra field")
                continue
            uid_len = payload[1]
            uid_end = 2 + uid_len
            if uid_len < 1 or uid_len > 8 or uid_end >= len(payload):
                violations.append("malformed Unix UID/GID extra field")
                continue
            gid_len = payload[uid_end]
            if gid_len < 1 or gid_len > 8 or uid_end + 1 + gid_len != len(payload):
                violations.append("malformed Unix UID/GID extra field")
        elif header_id == 0x0001:  # ZIP64 sizes/offsets
            zip64_seen = True
            semantic = [item for item in expected_zip64 if item[1] != 0]
            mismatch_markers = [item for item in expected_zip64 if item[1] == 0]
            for label, _width, _value in mismatch_markers:
                violations.append(label)
            if not semantic:
                violations.append("ZIP64 extra field appears without a matching sentinel")
                continue
            expected_length = sum(width for _label, width, _value in semantic)
            if len(payload) != expected_length:
                violations.append("malformed ZIP64 extra field")
                continue
            cursor = 0
            for label, width, expected_value in semantic:
                value = int.from_bytes(payload[cursor : cursor + width], "little")
                cursor += width
                if value != expected_value:
                    violations.append(f"ZIP64 {label} disagrees with represented value")
        elif header_id == 0x000A:  # NTFS timestamps
            if len(payload) < 4:
                violations.append("malformed NTFS extra field")
                continue
            if payload[:4] != b"\0\0\0\0":
                violations.append("NTFS extra field has nonzero reserved bytes")
            cursor = 4
            attributes = 0
            seen_tags: set[int] = set()
            while cursor < len(payload):
                if len(payload) - cursor < 4:
                    violations.append("truncated NTFS extra-field attribute")
                    break
                tag, length = struct.unpack_from("<HH", payload, cursor)
                cursor += 4
                if length > len(payload) - cursor:
                    violations.append("truncated NTFS extra-field value")
                    break
                if tag in seen_tags:
                    violations.append(f"duplicate NTFS extra-field attribute 0x{tag:04x}")
                seen_tags.add(tag)
                if tag != 0x0001 or length != 24:
                    violations.append("unsupported NTFS extra-field attribute")
                cursor += length
                attributes += 1
            if attributes == 0:
                violations.append("NTFS extra field has no timestamp attribute")
        elif header_id in {0x5855, 0x7855}:  # legacy Info-ZIP Unix metadata
            if len(payload) not in {8, 12}:
                violations.append("malformed legacy Unix extra field")
        else:
            violations.append(f"unsupported ZIP extra field 0x{header_id:04x}")

    semantic_zip64 = [item for item in expected_zip64 if item[1] != 0]
    mismatch_markers = [item for item in expected_zip64 if item[1] == 0]
    if semantic_zip64 and not zip64_seen:
        violations.append("missing ZIP64 extra field for sentinel metadata")
    if mismatch_markers and not zip64_seen:
        for label, _width, _value in mismatch_markers:
            violations.append(label)
    return violations


def inspect_bundle(bundle: Path) -> tuple[int, list[Violation]]:
    violations: list[Violation] = []
    seen: dict[str, str] = {}
    file_size = bundle.stat().st_size

    with bundle.open("rb") as handle, zipfile.ZipFile(bundle) as archive:
        central_offset, central_size, expected_count, raw_comment = locate_central_directory(handle, file_size)
        records = parse_central_records(handle, file_size, central_offset, central_size, expected_count)
        infos = archive.infolist()
        if not infos:
            return 0, [Violation("<archive>", "bundle is empty")]
        if len(infos) != expected_count or len(records) != len(infos):
            return len(infos), [Violation("<archive>", "central-directory entry count is inconsistent")]
        if archive.comment != raw_comment:
            violations.append(Violation("<archive-comment>", "archive comment metadata is inconsistent"))
        archive_comment = raw_comment.strip()
        if archive_comment and not PUBLIC_ARCHIVE_COMMENT_RE.fullmatch(archive_comment):
            violations.append(
                Violation(
                    "<archive-comment>",
                    "archive comment must be empty or a 40/64-character hexadecimal source identity",
                )
            )

        for index, (record, info) in enumerate(zip(records, infos, strict=True)):
            try:
                central_name = decode_member_name(record.raw_name, record.flags)
                member = normalize_member_name(central_name)
            except ValueError as exc:
                violations.append(Violation(info.filename or f"<entry-{index}>", f"unsafe path: {exc}"))
                member = MemberPath(
                    original=info.filename or f"<entry-{index}>",
                    normalized=info.filename or f"<entry-{index}>",
                    parts=(info.filename or f"<entry-{index}>",),
                    folded_parts=((info.filename or f"<entry-{index}>").casefold(),),
                    is_directory=bool((info.filename or "").endswith("/")),
                )

            portable_key = unicodedata.normalize("NFC", member.normalized).casefold()
            prior = seen.get(portable_key)
            if prior is not None:
                violations.append(
                    Violation(member.original, f"duplicate or case-colliding path (already present as '{prior}')")
                )
            else:
                seen[portable_key] = member.original

            if record.flags != info.flag_bits:
                violations.append(Violation(member.original, "central flag metadata disagrees with ZIP parser state"))
            if record.version_needed != info.extract_version:
                violations.append(
                    Violation(member.original, "central required-version metadata is inconsistent")
                )
            if record.compression != info.compress_type:
                violations.append(Violation(member.original, "central compression metadata is inconsistent"))
            if record.crc32 != info.CRC:
                violations.append(Violation(member.original, "central CRC metadata is inconsistent"))
            if record.extra != info.extra:
                violations.append(Violation(member.original, "central extra-field metadata is inconsistent"))
            if record.comment != info.comment:
                violations.append(Violation(member.original, "central member comment metadata is inconsistent"))
            if record.external_attr != info.external_attr:
                violations.append(Violation(member.original, "central file-type metadata is inconsistent"))

            central_zip64 = zip64_expectations(record, info)
            for extra_violation in inspect_extra_fields(
                record.extra,
                member,
                location="central",
                raw_name=record.raw_name,
                flags=record.flags,
                expected_zip64=central_zip64,
            ):
                violations.append(Violation(member.original, f"central {extra_violation}"))

            try:
                local = parse_local_record(handle, file_size, info.header_offset, central_offset)
            except ValueError as exc:
                violations.append(Violation(member.original, f"local header: {exc}"))
                local = None

            if local is not None:
                local_member: MemberPath | None = None
                try:
                    local_name = decode_member_name(local.raw_name, local.flags)
                    local_member = normalize_member_name(local_name)
                except ValueError as exc:
                    violations.append(Violation(member.original, f"unsafe local-header path: {exc}"))
                if local.raw_name != record.raw_name:
                    violations.append(Violation(member.original, "local and central member names disagree"))
                if local_member is not None:
                    local_reason = forbidden_reason(local_member)
                    if local_reason is not None:
                        violations.append(Violation(local_member.original, f"local header exposes {local_reason}"))
                if local.flags != record.flags:
                    violations.append(Violation(member.original, "local and central flag metadata disagree"))
                if local.version_needed != record.version_needed:
                    violations.append(Violation(member.original, "local and central required-version metadata disagree"))
                if local.compression != record.compression:
                    violations.append(Violation(member.original, "local and central compression metadata disagree"))
                if local.mod_time != record.mod_time or local.mod_date != record.mod_date:
                    violations.append(Violation(member.original, "local and central DOS timestamp metadata disagree"))

                data_descriptor = bool(local.flags & 0x08)
                if data_descriptor:
                    if local.crc32 not in {0, info.CRC}:
                        violations.append(Violation(member.original, "local data-descriptor CRC metadata is contradictory"))
                elif local.crc32 != info.CRC:
                    violations.append(Violation(member.original, "local CRC metadata disagrees with central metadata"))

                for raw_value, actual, label in (
                    (local.uncompressed_size_32, info.file_size, "uncompressed size"),
                    (local.compressed_size_32, info.compress_size, "compressed size"),
                ):
                    allowed = {UINT32_SENTINEL}
                    if data_descriptor:
                        allowed.add(0)
                    if actual <= UINT32_SENTINEL:
                        allowed.add(actual)
                    if raw_value not in allowed:
                        violations.append(Violation(member.original, f"local {label} metadata is contradictory"))

                local_path_for_extra = local_member or member
                for extra_violation in inspect_extra_fields(
                    local.extra,
                    local_path_for_extra,
                    location="local",
                    raw_name=local.raw_name,
                    flags=local.flags,
                    expected_zip64=local_zip64_expectations(local, info),
                ):
                    violations.append(Violation(member.original, f"local {extra_violation}"))
                if local.data_offset + info.compress_size > central_offset:
                    violations.append(Violation(member.original, "compressed payload range overlaps the central directory"))

            unix_mode = record.external_attr >> 16
            if unix_mode and stat.S_ISLNK(unix_mode):
                violations.append(Violation(member.original, "symbolic-link member is not permitted"))
            file_type = stat.S_IFMT(unix_mode)
            if file_type not in {0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK}:
                violations.append(Violation(member.original, "special-file member is not permitted"))
            dos_directory = bool(record.external_attr & 0x10)
            if member.is_directory and file_type == stat.S_IFREG:
                violations.append(Violation(member.original, "directory name carries regular-file metadata"))
            if not member.is_directory and (file_type == stat.S_IFDIR or dos_directory):
                violations.append(Violation(member.original, "file name carries directory metadata"))
            if record.flags & 0x1:
                violations.append(Violation(member.original, "encrypted member is not inspectable"))
            if record.comment:
                violations.append(Violation(member.original, "per-member ZIP comments are not permitted"))

            reason = forbidden_reason(member)
            if reason is not None:
                violations.append(Violation(member.original, reason))

        return len(infos), violations


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="check x64lens public patch/source ZIP hygiene")
    parser.add_argument("bundles", nargs="+", type=Path)
    args = parser.parse_args(argv)

    failed = False
    for bundle in args.bundles:
        if not bundle.is_file():
            print(f"patch-bundle-hygiene: error: not a file: {bundle}", file=sys.stderr)
            failed = True
            continue
        try:
            entry_count, violations = inspect_bundle(bundle)
        except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
            print(f"patch-bundle-hygiene: error: cannot inspect {bundle}: {exc}", file=sys.stderr)
            failed = True
            continue

        if violations:
            for violation in violations:
                print(
                    "patch-bundle-hygiene: forbidden member: "
                    f"bundle={bundle} member={violation.member}: {violation.reason}",
                    file=sys.stderr,
                )
            print(
                "patch-bundle-hygiene: failed "
                f"bundle={bundle} entries={entry_count} violations={len(violations)}",
                file=sys.stderr,
            )
            failed = True
            continue

        print(f"patch-bundle-hygiene: ok entries={entry_count} bundle={bundle}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
