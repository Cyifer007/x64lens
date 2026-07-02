#!/usr/bin/env python3
"""Deterministic ELF64 mitigation-oracle regression harness for x64lens.

The harness builds a bounded matrix of controlled ELF64 program-header and
dynamic-table layouts, checks the stable text facts emitted by ``mitigations``,
verifies integrated JSON syntax, and exercises malformed cases through the
command paths that parse each represented table. Generated binaries are
temporary. A compact JSON evidence artifact is retained under an ignored
results directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

SCRIPT_VERSION = "0.5.0"
HARNESS_SCHEMA = "0.1.0"
ELF64_EHDR_SIZE = 64
ELF64_PHDR_SIZE = 56
ELF64_SHDR_SIZE = 64
ET_EXEC = 2
ET_DYN = 3
EM_X86_64 = 62
PT_LOAD = 1
PT_DYNAMIC = 2
PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552
DT_NULL = 0
DT_STRTAB = 5
DT_STRSZ = 10
DT_BIND_NOW = 24
DT_FLAGS = 30
DT_FLAGS_1 = 0x6FFFFFFB
DF_BIND_NOW = 0x8
DF_1_NOW = 0x1
DYNAMIC_STRING_SCAN_MAX = 1048576
PF_X = 1
PF_W = 2
PF_R = 4
SHT_NULL = 0
SHT_SYMTAB = 2
SHT_STRTAB = 3
EXIT_OK = 0
EXIT_MALFORMED_ELF = 5
EXIT_UNSUPPORTED = 6
MALFORMED_MESSAGE = b"error: malformed or truncated ELF\n"
UNSUPPORTED_MESSAGE = b"error: unsupported binary feature\n"
NO_EXEC_REGION_LINE = "  none discovered from PT_LOAD + PF_X"


class HarnessError(RuntimeError):
    """Raised for invalid harness configuration or a failed invariant."""


@dataclass(frozen=True)
class ProgramHeader:
    p_type: int
    flags: int
    offset: int = 0
    vaddr: int = 0
    filesz: int = 0
    memsz: int = 0
    align: int = 0x1000
    payload: bytes = b""


@dataclass(frozen=True)
class ValidCase:
    name: str
    elf_type: int
    headers: tuple[ProgramHeader, ...]
    expected_summary_lines: tuple[str, ...]
    section_types: tuple[int, ...] = ()


@dataclass(frozen=True)
class MalformedCase:
    name: str
    data: bytes
    commands: tuple[tuple[str, ...], ...] | None = None
    expected_exit: int = EXIT_MALFORMED_ELF
    expected_stderr: bytes = MALFORMED_MESSAGE


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pack_phdr(header: ProgramHeader) -> bytes:
    return struct.pack(
        "<IIQQQQQQ",
        header.p_type,
        header.flags,
        header.offset,
        header.vaddr,
        header.vaddr,
        header.filesz,
        header.memsz,
        header.align,
    )


def build_elf(elf_type: int, headers: Sequence[ProgramHeader]) -> bytes:
    """Build a deterministic ELF64 image sufficient for static analysis."""
    if not headers:
        raise HarnessError("at least one program header is required")

    phoff = ELF64_EHDR_SIZE
    phnum = len(headers)
    file_size = max(
        [0x300]
        + [
            header.offset + header.filesz
            for header in headers
            if header.filesz > 0 and header.offset < (1 << 63)
        ]
    )
    file_size = max(file_size, phoff + phnum * ELF64_PHDR_SIZE)
    image = bytearray(file_size)

    ident = bytearray(16)
    ident[0:4] = b"\x7fELF"
    ident[4] = 2
    ident[5] = 1
    ident[6] = 1
    image[0:16] = ident

    executable = next(
        (header for header in headers if header.p_type == PT_LOAD and header.flags & PF_X),
        None,
    )
    entry = executable.vaddr if executable is not None else 0
    struct.pack_into(
        "<HHIQQQIHHHHHH",
        image,
        16,
        elf_type,
        EM_X86_64,
        1,
        entry,
        phoff,
        0,
        0,
        ELF64_EHDR_SIZE,
        ELF64_PHDR_SIZE,
        phnum,
        0,
        0,
        0,
    )

    for index, header in enumerate(headers):
        start = phoff + index * ELF64_PHDR_SIZE
        image[start : start + ELF64_PHDR_SIZE] = pack_phdr(header)
        if header.filesz:
            payload_start = header.offset
            payload_end = header.offset + header.filesz
            if header.payload:
                if len(header.payload) > header.filesz:
                    raise HarnessError(f"payload exceeds p_filesz for header {index}")
                image[payload_start:payload_start + len(header.payload)] = header.payload
            elif header.p_type == PT_LOAD:
                image[payload_start:payload_end] = b"\x90" * header.filesz
                if header.flags & PF_X:
                    image[payload_end - 1] = 0xC3

    return bytes(image)


def add_section_headers(data: bytes, section_types: Sequence[int]) -> bytes:
    """Append a minimal validated section table with controlled SHT_* types."""
    if not section_types:
        return data
    image = bytearray(data)
    shoff = (len(image) + 7) & ~7
    if shoff > len(image):
        image.extend(b"\0" * (shoff - len(image)))
    for section_type in section_types:
        header = bytearray(ELF64_SHDR_SIZE)
        struct.pack_into("<I", header, 0x04, section_type)
        image.extend(header)
    struct.pack_into("<Q", image, 0x28, shoff)
    struct.pack_into("<H", image, 0x3A, ELF64_SHDR_SIZE)
    struct.pack_into("<H", image, 0x3C, len(section_types))
    struct.pack_into("<H", image, 0x3E, 0)
    return bytes(image)


def build_case_elf(case: ValidCase) -> bytes:
    return add_section_headers(build_elf(case.elf_type, case.headers), case.section_types)


def load(offset: int, flags: int, size: int = 0x20, base: int = 0x400000) -> ProgramHeader:
    return ProgramHeader(
        PT_LOAD,
        flags,
        offset,
        base + offset,
        size,
        size,
        0x1000,
    )


def stack(flags: int) -> ProgramHeader:
    return ProgramHeader(PT_GNU_STACK, flags, align=16)


def relro(offset: int = 0x2000, base: int = 0x400000) -> ProgramHeader:
    return ProgramHeader(PT_GNU_RELRO, PF_R, offset, base + offset, 0x10, 0x10, 1)


def dyn_entry(tag: int, value: int = 0) -> bytes:
    return struct.pack("<QQ", tag, value)


def dynamic(
    offset: int = 0x2000,
    base: int = 0x400000,
    entries: tuple[tuple[int, int], ...] = ((DT_NULL, 0),),
) -> ProgramHeader:
    payload = b"".join(dyn_entry(tag, value) for tag, value in entries)
    return ProgramHeader(
        PT_DYNAMIC,
        PF_R | PF_W,
        offset,
        base + offset,
        len(payload),
        len(payload),
        8,
        payload,
    )



def string_load(
    payload: bytes,
    offset: int = 0x3000,
    base: int = 0x400000,
) -> ProgramHeader:
    return ProgramHeader(
        PT_LOAD,
        PF_R,
        offset,
        base + offset,
        len(payload),
        len(payload),
        0x1000,
        payload,
    )


def expected(
    *,
    pie: str,
    nx: str,
    relro_state: str,
    canary: str = "unknown",
    stripped: str = "unknown",
    rwx: str,
    dynamic_state: str,
    phnum: int,
    bind_now: str | None = None,
    dynamic_entries: int = 0,
    dynamic_terminator: str | None = None,
    loads: int,
    executable: int,
) -> tuple[str, ...]:
    return (
        f"  PIE: {pie}",
        f"  NX stack: {nx}",
        f"  RELRO: {relro_state}",
        f"  Canary indicator: {canary}",
        f"  Stripped indicator: {stripped}",
        f"  RWX load segment: {rwx}",
        f"  Dynamic linking: {dynamic_state}",
        f"  Bind now: {bind_now if bind_now is not None else ('no' if dynamic_state == 'yes' else 'not applicable')}",
        f"  Dynamic entries: 0x{dynamic_entries:016x}",
        f"  Dynamic terminator: {dynamic_terminator if dynamic_terminator is not None else ('yes' if dynamic_state == 'yes' else 'not applicable')}",
        f"  Program header count: 0x{phnum:016x}",
        f"  LOAD segments: 0x{loads:016x}",
        f"  Executable LOAD regions: 0x{executable:016x}",
    )


def valid_cases() -> tuple[ValidCase, ...]:
    rx = PF_R | PF_X
    rw = PF_R | PF_W
    rwx = PF_R | PF_W | PF_X
    return (
        ValidCase(
            "exec-no-stack",
            ET_EXEC,
            (load(0x1000, rx),),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="no",
                phnum=1,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "dyn-no-stack",
            ET_DYN,
            (load(0x1000, rx, base=0),),
            expected(
                pie="enabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="no",
                phnum=1,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "nx-stack",
            ET_EXEC,
            (load(0x1000, rx), stack(rw)),
            expected(
                pie="disabled",
                nx="enabled",
                relro_state="not found",
                rwx="no",
                dynamic_state="no",
                phnum=2,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "executable-stack",
            ET_EXEC,
            (load(0x1000, rx), stack(rwx)),
            expected(
                pie="disabled",
                nx="disabled",
                relro_state="not found",
                rwx="no",
                dynamic_state="no",
                phnum=2,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "relro",
            ET_EXEC,
            (load(0x1000, rx), relro()),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="partial",
                rwx="no",
                dynamic_state="no",
                phnum=2,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "dynamic",
            ET_EXEC,
            (load(0x1000, rx), dynamic()),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="yes",
                dynamic_entries=1,
                phnum=2,
                loads=1,
                executable=1,
            ),
        ),

        ValidCase(
            "dynamic-no-null-bounded",
            ET_EXEC,
            (load(0x1000, rx), dynamic(entries=((DT_FLAGS, 0),))),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="yes",
                bind_now="no",
                dynamic_entries=1,
                dynamic_terminator="no",
                phnum=2,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "dynamic-string-canary-absent",
            ET_EXEC,
            (
                load(0x1000, rx),
                string_load(b"\0puts\0printf\0"),
                dynamic(entries=((DT_STRTAB, 0x403000), (DT_STRSZ, 13), (DT_NULL, 0))),
            ),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                canary="absent",
                rwx="no",
                dynamic_state="yes",
                dynamic_entries=3,
                phnum=3,
                loads=2,
                executable=1,
            ),
        ),
        ValidCase(
            "dynamic-string-canary-present",
            ET_EXEC,
            (
                load(0x1000, rx),
                string_load(b"\0__stack_chk_fail\0puts\0"),
                dynamic(entries=((DT_STRTAB, 0x403000), (DT_STRSZ, 23), (DT_NULL, 0))),
            ),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                canary="present",
                rwx="no",
                dynamic_state="yes",
                dynamic_entries=3,
                phnum=3,
                loads=2,
                executable=1,
            ),
        ),
        ValidCase(
            "dynamic-bind-now-tag",
            ET_EXEC,
            (load(0x1000, rx), dynamic(entries=((DT_BIND_NOW, 0), (DT_NULL, 0)))),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="yes",
                bind_now="yes",
                dynamic_entries=2,
                phnum=2,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "dynamic-flags-bind-now",
            ET_EXEC,
            (load(0x1000, rx), dynamic(entries=((DT_FLAGS, DF_BIND_NOW), (DT_NULL, 0)))),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="yes",
                bind_now="yes",
                dynamic_entries=2,
                phnum=2,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "dynamic-flags-1-now",
            ET_EXEC,
            (load(0x1000, rx), dynamic(entries=((DT_FLAGS_1, DF_1_NOW), (DT_NULL, 0)))),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="yes",
                bind_now="yes",
                dynamic_entries=2,
                phnum=2,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "full-relro-bind-now-tag",
            ET_EXEC,
            (load(0x1000, rx), relro(), dynamic(entries=((DT_BIND_NOW, 0), (DT_NULL, 0)))),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="full",
                rwx="no",
                dynamic_state="yes",
                bind_now="yes",
                dynamic_entries=2,
                phnum=3,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "full-relro-flags-bind-now",
            ET_EXEC,
            (load(0x1000, rx), relro(), dynamic(entries=((DT_FLAGS, DF_BIND_NOW), (DT_NULL, 0)))),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="full",
                rwx="no",
                dynamic_state="yes",
                bind_now="yes",
                dynamic_entries=2,
                phnum=3,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "full-relro-flags-1-now",
            ET_EXEC,
            (load(0x1000, rx), relro(), dynamic(entries=((DT_FLAGS_1, DF_1_NOW), (DT_NULL, 0)))),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="full",
                rwx="no",
                dynamic_state="yes",
                bind_now="yes",
                dynamic_entries=2,
                phnum=3,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "rwx-load",
            ET_EXEC,
            (load(0x1000, rwx),),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="yes",
                dynamic_state="no",
                phnum=1,
                loads=1,
                executable=1,
            ),
        ),
        ValidCase(
            "non-executable-load",
            ET_EXEC,
            (load(0x1000, rw),),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="no",
                phnum=1,
                loads=1,
                executable=0,
            ),
        ),
        ValidCase(
            "split-rx-rw-loads",
            ET_EXEC,
            (load(0x1000, rx), load(0x2000, rw)),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="no",
                phnum=2,
                loads=2,
                executable=1,
            ),
        ),
        ValidCase(
            "overlapping-loads-characterized",
            ET_EXEC,
            (
                load(0x1000, rx, size=0x30),
                load(0x1010, rx, size=0x20),
            ),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                rwx="no",
                dynamic_state="no",
                phnum=2,
                loads=2,
                executable=2,
            ),
        ),
        ValidCase(
            "combined-hardening-evidence",
            ET_DYN,
            (
                load(0x1000, rx, base=0),
                load(0x2000, rw, base=0),
                stack(rw),
                relro(base=0),
                dynamic(base=0),
            ),
            expected(
                pie="enabled",
                nx="enabled",
                relro_state="partial",
                rwx="no",
                dynamic_state="yes",
                dynamic_entries=1,
                phnum=5,
                loads=2,
                executable=1,
            ),
        ),
        ValidCase(
            "dynamic-string-zero-size-absent",
            ET_EXEC,
            (
                load(0x1000, rx),
                string_load(b"\0"),
                dynamic(entries=((DT_STRTAB, 0x403000), (DT_STRSZ, 0), (DT_NULL, 0))),
            ),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                canary="absent",
                rwx="no",
                dynamic_state="yes",
                dynamic_entries=3,
                phnum=3,
                loads=2,
                executable=1,
            ),
        ),
        ValidCase(
            "section-table-without-symtab-stripped",
            ET_EXEC,
            (load(0x1000, rx),),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                stripped="stripped",
                rwx="no",
                dynamic_state="no",
                phnum=1,
                loads=1,
                executable=1,
            ),
            section_types=(SHT_NULL, SHT_STRTAB),
        ),
        ValidCase(
            "section-table-with-symtab-not-stripped",
            ET_EXEC,
            (load(0x1000, rx),),
            expected(
                pie="disabled",
                nx="unknown",
                relro_state="not found",
                stripped="not stripped",
                rwx="no",
                dynamic_state="no",
                phnum=1,
                loads=1,
                executable=1,
            ),
            section_types=(SHT_NULL, SHT_SYMTAB, SHT_STRTAB),
        ),
    )


def malformed_cases(control: bytes) -> tuple[MalformedCase, ...]:
    wrong_phentsize = bytearray(control)
    struct.pack_into("<H", wrong_phentsize, 0x36, ELF64_PHDR_SIZE - 1)

    truncated_table = bytearray(control)
    struct.pack_into("<H", truncated_table, 0x38, 2)
    truncated_table = truncated_table[: ELF64_EHDR_SIZE + 2 * ELF64_PHDR_SIZE - 1]

    phoff_out = bytearray(control)
    struct.pack_into("<Q", phoff_out, 0x20, len(phoff_out) + 0x1000)

    phdr_table_overflow = bytearray(control)
    struct.pack_into("<Q", phdr_table_overflow, 0x20, 0xFFFFFFFFFFFFFFF0)
    struct.pack_into("<H", phdr_table_overflow, 0x38, 1)

    shdr_table_overflow = bytearray(control)
    struct.pack_into("<Q", shdr_table_overflow, 0x28, 0xFFFFFFFFFFFFFFF0)
    struct.pack_into("<H", shdr_table_overflow, 0x3A, 64)
    struct.pack_into("<H", shdr_table_overflow, 0x3C, 1)

    load_out = bytearray(control)
    first_phdr = ELF64_EHDR_SIZE
    struct.pack_into("<Q", load_out, first_phdr + 0x08, len(load_out) - 1)
    struct.pack_into("<Q", load_out, first_phdr + 0x20, 2)
    struct.pack_into("<Q", load_out, first_phdr + 0x28, 2)

    load_overflow = bytearray(control)
    struct.pack_into("<Q", load_overflow, first_phdr + 0x08, 0xFFFFFFFFFFFFFFF8)
    struct.pack_into("<Q", load_overflow, first_phdr + 0x20, 0x10)
    struct.pack_into("<Q", load_overflow, first_phdr + 0x28, 0x10)

    dynamic_commands = (
        ("mitigations",),
        ("analyze", "--format", "json", "--max-depth", "4"),
        ("gadgets", "--max-depth", "4"),
        ("gadgets", "--format", "json", "--max-depth", "4"),
    )
    dynamic_control = bytearray(build_elf(ET_EXEC, (load(0x1000, PF_R | PF_X), dynamic())))
    dynamic_phdr = ELF64_EHDR_SIZE + ELF64_PHDR_SIZE

    dynamic_filesz_gt_memsz = bytearray(dynamic_control)
    struct.pack_into("<Q", dynamic_filesz_gt_memsz, dynamic_phdr + 0x20, 0x20)
    struct.pack_into("<Q", dynamic_filesz_gt_memsz, dynamic_phdr + 0x28, 0x10)

    dynamic_range_past_eof = bytearray(dynamic_control)
    struct.pack_into("<Q", dynamic_range_past_eof, dynamic_phdr + 0x08, len(dynamic_range_past_eof))
    struct.pack_into("<Q", dynamic_range_past_eof, dynamic_phdr + 0x20, 0x10)
    struct.pack_into("<Q", dynamic_range_past_eof, dynamic_phdr + 0x28, 0x10)

    dynamic_unaligned_size = bytearray(dynamic_control)
    dynamic_unaligned_size.extend(b"\0")
    struct.pack_into("<Q", dynamic_unaligned_size, dynamic_phdr + 0x20, 0x11)
    struct.pack_into("<Q", dynamic_unaligned_size, dynamic_phdr + 0x28, 0x11)

    multiple_dynamic = build_elf(
        ET_EXEC,
        (
            load(0x1000, PF_R | PF_X),
            dynamic(offset=0x2000, entries=((DT_NULL, 0),)),
            dynamic(offset=0x2040, entries=((DT_FLAGS, DF_BIND_NOW),)),
        ),
    )

    dynamic_strtab_unmapped = build_elf(
        ET_EXEC,
        (
            load(0x1000, PF_R | PF_X),
            dynamic(entries=((DT_STRTAB, 0x77770000), (DT_STRSZ, 0x10), (DT_NULL, 0))),
        ),
    )

    dynamic_duplicate_strtab = build_elf(
        ET_EXEC,
        (
            load(0x1000, PF_R | PF_X),
            string_load(b"\0__stack_chk_fail\0puts\0"),
            dynamic(
                entries=(
                    (DT_STRTAB, 0x403000),
                    (DT_STRTAB, 0x403001),
                    (DT_STRSZ, 23),
                    (DT_NULL, 0),
                )
            ),
        ),
    )

    dynamic_duplicate_strsz = build_elf(
        ET_EXEC,
        (
            load(0x1000, PF_R | PF_X),
            string_load(b"\0__stack_chk_fail\0puts\0"),
            dynamic(
                entries=(
                    (DT_STRTAB, 0x403000),
                    (DT_STRSZ, 23),
                    (DT_STRSZ, 3),
                    (DT_NULL, 0),
                )
            ),
        ),
    )

    dynamic_strsz_over_scan_cap = build_elf(
        ET_EXEC,
        (
            load(0x1000, PF_R | PF_X),
            dynamic(
                entries=(
                    (DT_STRTAB, 0x403000),
                    (DT_STRSZ, DYNAMIC_STRING_SCAN_MAX + 1),
                    (DT_NULL, 0),
                )
            ),
        ),
    )

    return (
        MalformedCase("wrong-phentsize", bytes(wrong_phentsize)),
        MalformedCase("truncated-program-header-table", bytes(truncated_table)),
        MalformedCase("program-header-offset-out-of-file", bytes(phoff_out)),
        MalformedCase("program-header-table-addition-overflow", bytes(phdr_table_overflow)),
        MalformedCase("section-header-table-addition-overflow", bytes(shdr_table_overflow)),
        MalformedCase("load-file-range-out-of-file", bytes(load_out)),
        MalformedCase("load-file-range-addition-overflow", bytes(load_overflow)),
        MalformedCase("dynamic-filesz-greater-than-memsz", bytes(dynamic_filesz_gt_memsz), dynamic_commands),
        MalformedCase("dynamic-file-range-out-of-file", bytes(dynamic_range_past_eof), dynamic_commands),
        MalformedCase("dynamic-entry-size-unaligned", bytes(dynamic_unaligned_size), dynamic_commands),
        MalformedCase("multiple-pt-dynamic", multiple_dynamic, dynamic_commands),
        MalformedCase("dynamic-strtab-unmapped", dynamic_strtab_unmapped, dynamic_commands),
        MalformedCase("duplicate-dt-strtab", dynamic_duplicate_strtab, dynamic_commands),
        MalformedCase("duplicate-dt-strsz", dynamic_duplicate_strsz, dynamic_commands),
        MalformedCase(
            "dynamic-strsz-over-scan-cap",
            dynamic_strsz_over_scan_cap,
            dynamic_commands,
            EXIT_UNSUPPORTED,
            UNSUPPORTED_MESSAGE,
        ),
    )


def run(command: Sequence[str], timeout: float) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            start_new_session=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise HarnessError(f"command timed out after {timeout}s: {' '.join(command)}") from exc


def permission_string(flags: int) -> str:
    return "".join(
        (
            "R" if flags & PF_R else "-",
            "W" if flags & PF_W else "-",
            "X" if flags & PF_X else "-",
        )
    )


def expected_region_lines(case: ValidCase) -> tuple[str, ...]:
    executable = tuple(
        header
        for header in case.headers
        if header.p_type == PT_LOAD and header.flags & PF_X
    )
    if not executable:
        return (NO_EXEC_REGION_LINE,)
    return tuple(
        "  - VA "
        f"0x{header.vaddr:016x}, "
        f"file offset 0x{header.offset:016x}, "
        f"file size 0x{header.filesz:016x}, "
        f"mem size 0x{header.memsz:016x}, "
        f"perms {permission_string(header.flags)}"
        for header in executable
    )


def assert_expected_text(case: ValidCase, stdout: bytes) -> None:
    text = stdout.decode("utf-8", errors="strict")
    lines = text.splitlines()

    summary_prefixes = tuple(
        line.split(":", maxsplit=1)[0] + ":"
        for line in case.expected_summary_lines
    )
    observed_summary = tuple(
        line
        for line in lines
        if line.startswith(summary_prefixes)
    )
    if observed_summary != case.expected_summary_lines:
        raise HarnessError(
            f"{case.name}: mitigation summary mismatch: "
            f"expected {case.expected_summary_lines!r}, "
            f"observed {observed_summary!r}"
        )

    try:
        region_start = lines.index("Executable regions:") + 1
    except ValueError as exc:
        raise HarnessError(f"{case.name}: missing executable-region section") from exc
    observed_regions = tuple(
        line for line in lines[region_start:] if line
    )
    expected_regions = expected_region_lines(case)
    if observed_regions != expected_regions:
        raise HarnessError(
            f"{case.name}: executable-region mismatch: "
            f"expected {expected_regions!r}, observed {observed_regions!r}"
        )


def expected_json_mitigations(case: ValidCase) -> dict[str, object]:
    values = {
        line.strip().split(":", maxsplit=1)[0]:
        line.split(":", maxsplit=1)[1].strip()
        for line in case.expected_summary_lines
    }
    nx_value = values["NX stack"]
    dynamic_linking = values["Dynamic linking"] == "yes"
    return {
        "nx_stack": (
            None
            if nx_value == "unknown"
            else nx_value == "enabled"
        ),
        "pie": values["PIE"] == "enabled",
        "relro": (
            "none"
            if values["RELRO"] == "not found"
            else values["RELRO"]
        ),
        "canary": values["Canary indicator"],
        "stripped": (
            "not_stripped"
            if values["Stripped indicator"] == "not stripped"
            else values["Stripped indicator"]
        ),
        "rwx_load_segment": values["RWX load segment"] == "yes",
        "dynamic_linking": dynamic_linking,
        "bind_now": None if not dynamic_linking else values["Bind now"] == "yes",
        "dynamic_entry_count": int(values["Dynamic entries"], 16),
        "dynamic_terminated": None if not dynamic_linking else values["Dynamic terminator"] == "yes",
    }


def validate_json(case: ValidCase, stdout: bytes) -> None:
    try:
        report = json.loads(stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessError(f"{case.name}: integrated JSON is invalid: {exc}") from exc
    if not isinstance(report, dict):
        raise HarnessError(f"{case.name}: integrated JSON root is not an object")
    if report.get("tool") != "x64lens":
        raise HarnessError(f"{case.name}: integrated JSON tool identity is invalid")

    target = report.get("target")
    if not isinstance(target, dict):
        raise HarnessError(f"{case.name}: integrated JSON target is not an object")
    if target.get("format") != "ELF64" or target.get("arch") != "x86_64":
        raise HarnessError(f"{case.name}: integrated JSON target identity is invalid")

    mitigations = report.get("mitigations")
    expected_mitigations = expected_json_mitigations(case)
    if mitigations != expected_mitigations:
        raise HarnessError(
            f"{case.name}: integrated JSON mitigation mismatch: "
            f"expected {expected_mitigations!r}, observed {mitigations!r}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--seed", required=True, type=Path)
    parser.add_argument("--timeout", default=2.0, type=float)
    parser.add_argument("--results-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    binary = args.binary.resolve()
    seed = args.seed.resolve()
    if not binary.is_file():
        raise HarnessError(f"x64lens binary does not exist: {binary}")
    if not seed.is_file():
        raise HarnessError(f"seed does not exist: {seed}")
    if args.timeout <= 0:
        raise HarnessError("timeout must be greater than zero")

    seed_data = seed.read_bytes()
    valid = valid_cases()
    control = build_elf(valid[0].elf_type, valid[0].headers)
    malformed = malformed_cases(control)
    records: list[dict[str, object]] = []
    malformed_count = sum(1 for case in malformed if case.expected_exit == EXIT_MALFORMED_ELF)
    unsupported_count = sum(1 for case in malformed if case.expected_exit == EXIT_UNSUPPORTED)

    with tempfile.TemporaryDirectory(prefix="x64lens-mitigation-matrix-") as temp:
        temp_dir = Path(temp)

        for case in valid:
            data = build_case_elf(case)
            fixture = temp_dir / f"{case.name}.elf"
            fixture.write_bytes(data)

            mitigation_cmd = [str(binary), "mitigations", str(fixture)]
            mitigation_result = run(mitigation_cmd, args.timeout)
            if mitigation_result.returncode != EXIT_OK:
                raise HarnessError(
                    f"{case.name}: mitigations exited {mitigation_result.returncode}: "
                    f"{mitigation_result.stderr.decode(errors='replace').strip()}"
                )
            if mitigation_result.stderr:
                raise HarnessError(f"{case.name}: mitigations emitted stderr")
            assert_expected_text(case, mitigation_result.stdout)

            analyze_cmd = [
                str(binary),
                "analyze",
                "--format",
                "json",
                "--max-depth",
                "4",
                str(fixture),
            ]
            analyze_result = run(analyze_cmd, args.timeout)
            if analyze_result.returncode != EXIT_OK:
                raise HarnessError(
                    f"{case.name}: analyze exited {analyze_result.returncode}: "
                    f"{analyze_result.stderr.decode(errors='replace').strip()}"
                )
            if analyze_result.stderr:
                raise HarnessError(f"{case.name}: analyze emitted stderr")
            validate_json(case, analyze_result.stdout)

            gadgets_json_cmd = [
                str(binary),
                "gadgets",
                "--format",
                "json",
                "--max-depth",
                "4",
                str(fixture),
            ]
            gadgets_json_result = run(gadgets_json_cmd, args.timeout)
            if gadgets_json_result.returncode != EXIT_OK:
                raise HarnessError(
                    f"{case.name}: gadgets JSON exited {gadgets_json_result.returncode}: "
                    f"{gadgets_json_result.stderr.decode(errors='replace').strip()}"
                )
            if gadgets_json_result.stderr:
                raise HarnessError(f"{case.name}: gadgets JSON emitted stderr")
            validate_json(case, gadgets_json_result.stdout)

            records.append(
                {
                    "case": case.name,
                    "input_class": "valid",
                    "fixture_sha256": sha256_bytes(data),
                    "expected_mitigation_lines": list(case.expected_summary_lines),
                    "expected_region_lines": list(expected_region_lines(case)),
                    "expected_json_mitigations": expected_json_mitigations(case),
                    "mitigations_exit_code": mitigation_result.returncode,
                    "analyze_exit_code": analyze_result.returncode,
                    "gadgets_json_exit_code": gadgets_json_result.returncode,
                    "result": "ok",
                }
            )

        malformed_commands = (
            ("info",),
            ("mitigations",),
            ("analyze", "--format", "json", "--max-depth", "4"),
        )
        for case in malformed:
            fixture = temp_dir / f"{case.name}.elf"
            fixture.write_bytes(case.data)
            command_records: list[dict[str, object]] = []
            active_commands = case.commands if case.commands is not None else malformed_commands
            for command_args in active_commands:
                command = [str(binary), *command_args, str(fixture)]
                result = run(command, args.timeout)
                if result.returncode != case.expected_exit:
                    raise HarnessError(
                        f"{case.name}/{command_args[0]}: expected exit {case.expected_exit}, "
                        f"received {result.returncode}"
                    )
                if result.stdout:
                    raise HarnessError(f"{case.name}/{command_args[0]}: emitted stdout")
                if result.stderr != case.expected_stderr:
                    raise HarnessError(
                        f"{case.name}/{command_args[0]}: unexpected stderr: "
                        f"expected {case.expected_stderr!r}, observed {result.stderr!r}"
                    )
                command_records.append(
                    {
                        "command": " ".join(command_args),
                        "exit_code": result.returncode,
                        "expected_exit_code": case.expected_exit,
                    }
                )

            input_class = "unsupported" if case.expected_exit == EXIT_UNSUPPORTED else "malformed"
            records.append(
                {
                    "case": case.name,
                    "input_class": input_class,
                    "fixture_sha256": sha256_bytes(case.data),
                    "commands": command_records,
                    "result": "ok",
                }
            )

    args.results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    result_path = args.results_dir / f"mitigation-matrix-{timestamp}.json"
    artifact = {
        "schema_version": HARNESS_SCHEMA,
        "harness_version": SCRIPT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "binary": str(binary),
        "seed": str(seed),
        "seed_sha256": sha256_bytes(seed_data),
        "timeout_seconds": args.timeout,
        "valid_cases": len(valid),
        "failure_cases": len(malformed),
        "malformed_cases": malformed_count,
        "unsupported_cases": unsupported_count,
        "records": records,
    }
    result_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("mitigation-matrix-smoke: ok")
    print(f"  seed: {seed}")
    print(f"  seed_sha256: {artifact['seed_sha256']}")
    print(f"  valid cases: {len(valid)}")
    print(f"  malformed cases: {malformed_count}")
    print(f"  unsupported cases: {unsupported_count}")
    print(f"  results: {result_path.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as exc:
        print(f"mitigation-matrix-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
