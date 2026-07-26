#!/usr/bin/env python3
"""Validate Sprint 12 ordinary PHDR policy and extended-numbering outcomes.

The harness builds compiler-independent ELF64 x86_64 fixtures. Every malformed
or unsupported case is exercised through info, mitigations, gadgets, and analyze
so the common identity gate cannot diverge between command paths.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Iterable

ELF64_EHDR_SIZE = 64
ELF64_PHDR_SIZE = 56
ELF64_SHDR_SIZE = 64
PT_NULL = 0
PT_LOAD = 1
PF_X = 1
PF_W = 2
PF_R = 4
PN_XNUM = 0xFFFF
SHN_LORESERVE = 0xFF00
SHN_XINDEX = 0xFFFF
SHT_NULL = 0
EXIT_MALFORMED = 5
EXIT_UNSUPPORTED = 6
MALFORMED_DIAGNOSTIC = b"error: malformed or truncated ELF\n"
UNSUPPORTED_DIAGNOSTIC = b"error: unsupported binary feature\n"
COMMANDS = (
    ("info",),
    ("mitigations",),
    ("gadgets", "--format", "json", "--max-depth", "4"),
    ("analyze", "--format", "json", "--max-depth", "4"),
)


@dataclass(frozen=True)
class ProgramHeader:
    p_type: int = PT_LOAD
    flags: int = PF_R | PF_X
    offset: int = 0x1000
    vaddr: int = 0x401000
    paddr: int = 0x401000
    filesz: int = 0x100
    memsz: int = 0x100
    align: int = 0x1000


@dataclass(frozen=True)
class Case:
    case_id: str
    data: bytes
    expected_exit: int
    expected_stderr: bytes
    category: str


def pack_ehdr(
    *,
    e_type: int = 2,
    entry: int = 0,
    phoff: int = 0,
    shoff: int = 0,
    phnum: int = 0,
    shnum: int = 0,
    shstrndx: int = 0,
    phentsize: int = ELF64_PHDR_SIZE,
    shentsize: int = ELF64_SHDR_SIZE,
) -> bytes:
    ident = bytearray(16)
    ident[:4] = b"\x7fELF"
    ident[4] = 2  # ELFCLASS64
    ident[5] = 1  # little endian
    ident[6] = 1  # current version
    return struct.pack(
        "<16sHHIQQQIHHHHHH",
        bytes(ident),
        e_type,
        62,
        1,
        entry,
        phoff,
        shoff,
        0,
        ELF64_EHDR_SIZE,
        phentsize,
        phnum,
        shentsize,
        shnum,
        shstrndx,
    )


def pack_phdr(ph: ProgramHeader) -> bytes:
    return struct.pack(
        "<IIQQQQQQ",
        ph.p_type,
        ph.flags,
        ph.offset,
        ph.vaddr,
        ph.paddr,
        ph.filesz,
        ph.memsz,
        ph.align,
    )


def pack_shdr0(
    *,
    name: int = 0,
    sh_type: int = SHT_NULL,
    flags: int = 0,
    address: int = 0,
    offset: int = 0,
    size: int = 0,
    link: int = 0,
    info: int = 0,
    address_align: int = 0,
    entry_size: int = 0,
) -> bytes:
    return struct.pack(
        "<IIQQQQIIQQ",
        name,
        sh_type,
        flags,
        address,
        offset,
        size,
        link,
        info,
        address_align,
        entry_size,
    )


def ordinary_elf(
    phdrs: Iterable[ProgramHeader],
    *,
    entry: int,
    payload_byte: int = 0xC3,
) -> bytes:
    ph_list = list(phdrs)
    phoff = ELF64_EHDR_SIZE if ph_list else 0
    required = ELF64_EHDR_SIZE + len(ph_list) * ELF64_PHDR_SIZE
    for ph in ph_list:
        if ph.filesz:
            required = max(required, ph.offset + ph.filesz)
    data = bytearray(required)
    data[:ELF64_EHDR_SIZE] = pack_ehdr(entry=entry, phoff=phoff, phnum=len(ph_list))
    for index, ph in enumerate(ph_list):
        start = phoff + index * ELF64_PHDR_SIZE
        data[start : start + ELF64_PHDR_SIZE] = pack_phdr(ph)
        if ph.filesz and ph.offset < len(data):
            data[ph.offset] = payload_byte
    return bytes(data)




def ordinary_section_table(*, shnum: int, shstrndx: int) -> bytes:
    shoff = ELF64_EHDR_SIZE
    total = shoff + shnum * ELF64_SHDR_SIZE
    data = bytearray(total)
    data[:ELF64_EHDR_SIZE] = pack_ehdr(
        shoff=shoff,
        shnum=shnum,
        shstrndx=shstrndx,
    )
    data[shoff : shoff + ELF64_SHDR_SIZE] = pack_shdr0()
    return bytes(data)

def extended_phnum(
    *,
    actual: int = PN_XNUM,
    truncate: bool = False,
    sh_type: int = SHT_NULL,
    sh_name: int = 0,
    inactive_size: int = 0,
) -> bytes:
    phoff = ELF64_EHDR_SIZE
    phbytes = actual * ELF64_PHDR_SIZE
    shoff = phoff + phbytes
    total = shoff + ELF64_SHDR_SIZE
    if truncate:
        total = max(ELF64_EHDR_SIZE + ELF64_SHDR_SIZE, total - 1)
    data = bytearray(total)
    data[:ELF64_EHDR_SIZE] = pack_ehdr(
        phoff=phoff,
        phnum=PN_XNUM,
        shoff=shoff,
        shnum=1,
        shstrndx=0,
    )
    if shoff + ELF64_SHDR_SIZE <= len(data):
        data[shoff : shoff + ELF64_SHDR_SIZE] = pack_shdr0(
            name=sh_name,
            sh_type=sh_type,
            size=inactive_size,
            info=actual,
        )
    return bytes(data)


def extended_shnum(
    *,
    actual: int = SHN_LORESERVE,
    shstrndx: int = 0,
    sh_link: int = 0,
    inactive_info: int = 0,
    truncate: bool = False,
) -> bytes:
    shoff = ELF64_EHDR_SIZE
    try:
        table_bytes = actual * ELF64_SHDR_SIZE
    except OverflowError:
        table_bytes = 0
    # Malicious enormous counts use only section zero; the parser must reject
    # checked multiplication/range before any allocation or iteration.
    if actual > 1_000_000:
        total = ELF64_EHDR_SIZE + ELF64_SHDR_SIZE
    else:
        total = shoff + table_bytes
    if truncate and total > ELF64_EHDR_SIZE:
        total -= 1
    data = bytearray(total)
    data[:ELF64_EHDR_SIZE] = pack_ehdr(
        shoff=shoff,
        shnum=0,
        shstrndx=shstrndx,
    )
    if shoff + ELF64_SHDR_SIZE <= len(data):
        data[shoff : shoff + ELF64_SHDR_SIZE] = pack_shdr0(
            size=actual,
            link=sh_link,
            info=inactive_info,
        )
    return bytes(data)


def cases() -> list[Case]:
    base = ProgramHeader()
    valid = [
        ("align-zero", ProgramHeader(align=0), 0x401000),
        ("align-one", ProgramHeader(align=1, offset=0x1001, vaddr=0x401008, paddr=0x401008), 0x401008),
        ("align-page-entry-start", base, 0x401000),
        ("entry-last-byte", base, 0x4010FF),
        ("zero-entry", base, 0),
    ]
    out = [Case(name, ordinary_elf([ph], entry=entry), 0, b"", "ordinary_valid") for name, ph, entry in valid]

    malformed = [
        ("align-non-power-two", [ProgramHeader(align=3)], 0x401000),
        ("load-congruence-mismatch", [ProgramHeader(vaddr=0x401008, paddr=0x401008)], 0x401008),
        ("virtual-end-overflow", [ProgramHeader(vaddr=0xFFFFFFFFFFFFF000, paddr=0xFFFFFFFFFFFFF000, memsz=0x2000)], 0),
        ("entry-at-exclusive-end", [base], 0x401100),
        ("entry-in-gap", [base, ProgramHeader(offset=0x2000, vaddr=0x403000, paddr=0x403000)], 0x402000),
        ("entry-in-nonexec-load", [ProgramHeader(flags=PF_R)], 0x401000),
        ("entry-without-phdr", [], 0x401000),
    ]
    out.extend(Case(name, ordinary_elf(phs, entry=entry), EXIT_MALFORMED, MALFORMED_DIAGNOSTIC, "ordinary_malformed") for name, phs, entry in malformed)

    zero_phnum_nonzero_phoff = bytearray(pack_ehdr(phoff=ELF64_EHDR_SIZE, phnum=0))
    ordinary_nonnull_sh0 = bytearray(ordinary_section_table(shnum=1, shstrndx=0))
    struct.pack_into("<I", ordinary_nonnull_sh0, ELF64_EHDR_SIZE + 4, 1)
    out.extend(
        [
            Case(
                "zero-phnum-nonzero-phoff",
                bytes(zero_phnum_nonzero_phoff),
                EXIT_MALFORMED,
                MALFORMED_DIAGNOSTIC,
                "ordinary_malformed",
            ),
            Case(
                "ordinary-section-zero-nonnull",
                bytes(ordinary_nonnull_sh0),
                EXIT_MALFORMED,
                MALFORMED_DIAGNOSTIC,
                "ordinary_malformed",
            ),
        ]
    )

    out.extend(
        [
            Case("extended-phnum-valid", extended_phnum(), EXIT_UNSUPPORTED, UNSUPPORTED_DIAGNOSTIC, "extended_unsupported"),
            Case("extended-shnum-valid", extended_shnum(), EXIT_UNSUPPORTED, UNSUPPORTED_DIAGNOSTIC, "extended_unsupported"),
            Case(
                "extended-shstr-valid",
                extended_shnum(actual=SHN_LORESERVE + 1, shstrndx=SHN_XINDEX, sh_link=SHN_LORESERVE),
                EXIT_UNSUPPORTED,
                UNSUPPORTED_DIAGNOSTIC,
                "extended_unsupported",
            ),
        ]
    )

    # Targeted malformed extended-numbering structures.
    missing_shoff = bytearray(ELF64_EHDR_SIZE)
    missing_shoff[:] = pack_ehdr(phoff=ELF64_EHDR_SIZE, phnum=PN_XNUM, shoff=0, shnum=1)
    wrong_shentsize = bytearray(extended_phnum())
    struct.pack_into("<H", wrong_shentsize, 0x3A, ELF64_SHDR_SIZE - 1)
    bad_type = extended_phnum(sh_type=1)
    too_small_info = extended_phnum(actual=PN_XNUM - 1)
    small_shnum = extended_shnum(actual=SHN_LORESERVE - 1)
    shstr_low = extended_shnum(actual=SHN_LORESERVE + 1, shstrndx=SHN_XINDEX, sh_link=1)
    shstr_oob = extended_shnum(actual=SHN_LORESERVE + 1, shstrndx=SHN_XINDEX, sh_link=SHN_LORESERVE + 1)
    huge_shnum = extended_shnum(actual=0xFFFFFFFFFFFFFFFF)
    malformed_ext = [
        ("ordinary-reserved-shnum", ordinary_section_table(shnum=SHN_LORESERVE, shstrndx=0)),
        (
            "ordinary-reserved-shstrndx",
            ordinary_section_table(shnum=SHN_LORESERVE + 1, shstrndx=SHN_LORESERVE),
        ),
        ("extended-missing-section-zero", bytes(missing_shoff)),
        ("extended-wrong-shentsize", bytes(wrong_shentsize)),
        ("extended-section-zero-nonnull", bad_type),
        ("extended-phnum-section-zero-name", extended_phnum(sh_name=1)),
        ("extended-phnum-inactive-size", extended_phnum(inactive_size=1)),
        (
            "extended-shnum-inactive-info",
            extended_shnum(actual=SHN_LORESERVE, inactive_info=1),
        ),
        (
            "extended-shnum-inactive-link",
            extended_shnum(actual=SHN_LORESERVE, sh_link=1),
        ),
        ("extended-phnum-below-sentinel", too_small_info),
        ("extended-phnum-truncated", extended_phnum(truncate=True)),
        ("extended-shnum-below-reserve", small_shnum),
        ("extended-shnum-truncated", extended_shnum(truncate=True)),
        ("extended-shnum-overflow", huge_shnum),
        ("extended-shstr-below-reserve", shstr_low),
        ("extended-shstr-out-of-range", shstr_oob),
    ]
    out.extend(Case(name, data, EXIT_MALFORMED, MALFORMED_DIAGNOSTIC, "extended_malformed") for name, data in malformed_ext)
    return out


def run_case(analyzer: Path, case: Case, target: Path) -> int:
    target.write_bytes(case.data)
    executions = 0
    for command in COMMANDS:
        result = subprocess.run(
            [str(analyzer), *command, str(target)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
        executions += 1
        if result.returncode != case.expected_exit:
            raise AssertionError(
                f"{case.case_id} {' '.join(command)}: exit {result.returncode}, expected {case.expected_exit}; "
                f"stderr={result.stderr!r}"
            )
        if case.expected_exit == 0:
            if not result.stdout:
                raise AssertionError(f"{case.case_id} {' '.join(command)}: successful command emitted no stdout")
            if result.stderr:
                raise AssertionError(f"{case.case_id} {' '.join(command)}: unexpected stderr {result.stderr!r}")
            if "--format" in command:
                parsed = json.loads(result.stdout)
                if parsed.get("schema_version") != "0.2.0":
                    raise AssertionError(f"{case.case_id}: wrong JSON schema identity")
        else:
            if result.stdout:
                raise AssertionError(f"{case.case_id} {' '.join(command)}: failure emitted partial stdout")
            if result.stderr != case.expected_stderr:
                raise AssertionError(
                    f"{case.case_id} {' '.join(command)}: stderr {result.stderr!r}, expected {case.expected_stderr!r}"
                )
    return executions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyzer", type=Path, default=Path("build/x64lens"))
    args = parser.parse_args()
    analyzer = args.analyzer.resolve()
    if not analyzer.is_file() or not os.access(analyzer, os.X_OK):
        raise SystemExit(f"analyzer is not executable: {analyzer}")

    catalog = cases()
    counts: dict[str, int] = {}
    executions = 0
    with tempfile.TemporaryDirectory(prefix="x64lens-s12-phdr-") as tmp:
        target = Path(tmp) / "case.elf"
        for case in catalog:
            executions += run_case(analyzer, case, target)
            counts[case.category] = counts.get(case.category, 0) + 1

    print(
        "sprint12-phdr-validity-smoke: ok "
        f"cases={len(catalog)} executions={executions} "
        f"ordinary_valid={counts.get('ordinary_valid', 0)} "
        f"ordinary_malformed={counts.get('ordinary_malformed', 0)} "
        f"extended_unsupported={counts.get('extended_unsupported', 0)} "
        f"extended_malformed={counts.get('extended_malformed', 0)}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"sprint12-phdr-validity-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
