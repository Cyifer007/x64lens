#!/usr/bin/env python3
"""Deterministic section-label regression probes for x64lens.

The probes build tiny ELF64 files with controlled section-header metadata and
verify that section labels remain annotations: they may improve analyst
readability, but they must not let hostile section names split text reports or
let non-executable/ambiguous section headers masquerade as scanner authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Sequence

SCRIPT_VERSION = "0.1.0"
HARNESS_SCHEMA = "0.1.0"
ELF64_EHDR_SIZE = 64
ELF64_PHDR_SIZE = 56
ELF64_SHDR_SIZE = 64
ET_EXEC = 2
EM_X86_64 = 62
PT_LOAD = 1
PF_X = 1
PF_R = 4
SHT_NULL = 0
SHT_PROGBITS = 1
SHT_STRTAB = 3
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4
EXIT_OK = 0


class HarnessError(RuntimeError):
    """Raised when a section-label invariant fails."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def c_name_table(names: Sequence[bytes]) -> tuple[bytes, dict[bytes, int]]:
    table = bytearray(b"\0")
    offsets: dict[bytes, int] = {b"": 0}
    for name in names:
        if not name or b"\0" in name:
            raise HarnessError(f"invalid section name for fixture: {name!r}")
        offsets[name] = len(table)
        table.extend(name)
        table.append(0)
    return bytes(table), offsets


def pack_shdr(
    *,
    name: int = 0,
    sh_type: int = SHT_NULL,
    flags: int = 0,
    addr: int = 0,
    offset: int = 0,
    size: int = 0,
    addralign: int = 1,
) -> bytes:
    return struct.pack(
        "<IIQQQQIIQQ",
        name,
        sh_type,
        flags,
        addr,
        offset,
        size,
        0,
        0,
        addralign,
        0,
    )


def build_fixture(
    label_name: bytes,
    *,
    fake_nonexec_overlap: bool = False,
    ambiguous_exec_overlap: bool = False,
    label_addr_delta: int = 0,
) -> bytes:
    """Build a tiny executable ELF64 fixture with controlled section labels."""
    code = b"\x5f\xc3"  # pop rdi; ret
    code_offset = 0x1000
    code_vaddr = 0x401000
    shstr_offset = 0x1800

    names = [b".shstrtab", label_name]
    if fake_nonexec_overlap:
        names.append(b".fake")
    if ambiguous_exec_overlap:
        names.extend([b".x1", b".x2"])
    shstr, offsets = c_name_table(names)

    shoff = (shstr_offset + len(shstr) + 7) & ~7
    section_count = 2
    if fake_nonexec_overlap:
        section_count += 1
    if ambiguous_exec_overlap:
        section_count += 2
    else:
        section_count += 1

    file_size = shoff + section_count * ELF64_SHDR_SIZE
    image = bytearray(max(file_size, code_offset + len(code), shstr_offset + len(shstr)))

    ident = bytearray(16)
    ident[0:4] = b"\x7fELF"
    ident[4] = 2  # ELFCLASS64
    ident[5] = 1  # little-endian
    ident[6] = 1  # version
    image[0:16] = ident
    struct.pack_into(
        "<HHIQQQIHHHHHH",
        image,
        16,
        ET_EXEC,
        EM_X86_64,
        1,
        code_vaddr,
        ELF64_EHDR_SIZE,
        shoff,
        0,
        ELF64_EHDR_SIZE,
        ELF64_PHDR_SIZE,
        1,
        ELF64_SHDR_SIZE,
        section_count,
        1,  # .shstrtab index
    )

    struct.pack_into(
        "<IIQQQQQQ",
        image,
        ELF64_EHDR_SIZE,
        PT_LOAD,
        PF_R | PF_X,
        code_offset,
        code_vaddr,
        code_vaddr,
        len(code),
        len(code),
        0x1000,
    )
    image[code_offset : code_offset + len(code)] = code
    image[shstr_offset : shstr_offset + len(shstr)] = shstr

    shdrs = [pack_shdr()]
    shdrs.append(
        pack_shdr(
            name=offsets[b".shstrtab"],
            sh_type=SHT_STRTAB,
            offset=shstr_offset,
            size=len(shstr),
        )
    )
    if fake_nonexec_overlap:
        shdrs.append(
            pack_shdr(
                name=offsets[b".fake"],
                sh_type=SHT_PROGBITS,
                flags=0,
                addr=code_vaddr,
                offset=code_offset,
                size=len(code),
            )
        )
    if ambiguous_exec_overlap:
        for name in (b".x1", b".x2"):
            shdrs.append(
                pack_shdr(
                    name=offsets[name],
                    sh_type=SHT_PROGBITS,
                    flags=SHF_ALLOC | SHF_EXECINSTR,
                    addr=code_vaddr,
                    offset=code_offset,
                    size=len(code),
                )
            )
    else:
        shdrs.append(
            pack_shdr(
                name=offsets[label_name],
                sh_type=SHT_PROGBITS,
                flags=SHF_ALLOC | SHF_EXECINSTR,
                addr=code_vaddr + label_addr_delta,
                offset=code_offset,
                size=len(code),
            )
        )

    if len(shdrs) != section_count:
        raise HarnessError(f"internal section count mismatch: {len(shdrs)} != {section_count}")
    cursor = shoff
    for shdr in shdrs:
        image[cursor : cursor + ELF64_SHDR_SIZE] = shdr
        cursor += ELF64_SHDR_SIZE
    return bytes(image)


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


def run_ok(binary: Path, fixture: Path, timeout: float, *args: str) -> bytes:
    result = run([str(binary), *args, str(fixture)], timeout)
    if result.returncode != EXIT_OK:
        raise HarnessError(
            f"{' '.join(args)} exited {result.returncode}: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )
    if result.stderr:
        raise HarnessError(f"{' '.join(args)} emitted stderr: {result.stderr!r}")
    return result.stdout


def json_sections(binary: Path, fixture: Path, timeout: float, command: str) -> set[object]:
    stdout = run_ok(binary, fixture, timeout, command, "--format", "json", "--max-depth", "4")
    report = json.loads(stdout)
    gadgets = report.get("gadgets")
    if not isinstance(gadgets, list):
        raise HarnessError(f"{command}: report does not contain gadget array")
    return {gadget.get("section") for gadget in gadgets}


def check_text_contains(binary: Path, fixture: Path, timeout: float, expected: bytes) -> None:
    for args in (("mitigations",), ("gadgets", "--max-depth", "4"), ("analyze", "--max-depth", "4")):
        stdout = run_ok(binary, fixture, timeout, *args)
        if expected not in stdout:
            raise HarnessError(f"{' '.join(args)} did not contain expected {expected!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--timeout", default=2.0, type=float)
    parser.add_argument("--results-dir", required=True, type=Path)
    args = parser.parse_args()

    binary = args.binary.resolve()
    if not binary.is_file():
        raise HarnessError(f"x64lens binary does not exist: {binary}")
    if args.timeout <= 0:
        raise HarnessError("timeout must be greater than zero")

    records: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="x64lens-section-label-") as temp:
        temp_dir = Path(temp)

        text_fixture = temp_dir / "text-label.elf"
        text_data = build_fixture(b".text")
        text_fixture.write_bytes(text_data)
        check_text_contains(binary, text_fixture, args.timeout, b"section: .text")
        sections = json_sections(binary, text_fixture, args.timeout, "gadgets")
        if sections != {".text"}:
            raise HarnessError(f"baseline .text JSON sections mismatch: {sections!r}")
        records.append({"case": "baseline-text-label", "result": "ok", "fixture_sha256": sha256_bytes(text_data)})

        newline_fixture = temp_dir / "newline-label.elf"
        newline_data = build_fixture(b".t\nxt")
        newline_fixture.write_bytes(newline_data)
        for args_tuple in (("mitigations",), ("gadgets", "--max-depth", "4"), ("analyze", "--max-depth", "4")):
            stdout = run_ok(binary, newline_fixture, args.timeout, *args_tuple)
            if b"section: .t\nxt" in stdout:
                raise HarnessError(f"{' '.join(args_tuple)} emitted raw newline section label")
            if b"section: .t\\x0axt" not in stdout:
                raise HarnessError(f"{' '.join(args_tuple)} did not emit escaped newline section label")
        sections = json_sections(binary, newline_fixture, args.timeout, "gadgets")
        if sections != {".t\nxt"}:
            raise HarnessError(f"newline JSON section mismatch: {sections!r}")
        records.append({"case": "newline-section-name-text-escaped", "result": "ok", "fixture_sha256": sha256_bytes(newline_data)})
        highbit_fixture = temp_dir / "highbit-label.elf"
        highbit_label = b".hi\xff"
        highbit_data = build_fixture(highbit_label)
        highbit_fixture.write_bytes(highbit_data)
        for args_tuple in (("mitigations",), ("gadgets", "--max-depth", "4"), ("analyze", "--max-depth", "4")):
            stdout = run_ok(binary, highbit_fixture, args.timeout, *args_tuple)
            if b"section: .hi\xff" in stdout:
                raise HarnessError(f"{' '.join(args_tuple)} emitted raw high-bit section label")
            if b"section: .hi\\xff" not in stdout:
                raise HarnessError(f"{' '.join(args_tuple)} did not emit escaped high-bit section label")
        expected_highbit = highbit_label.decode("latin-1")
        for command in ("gadgets", "analyze"):
            sections = json_sections(binary, highbit_fixture, args.timeout, command)
            if sections != {expected_highbit}:
                raise HarnessError(f"{command}: high-bit JSON section mismatch: {sections!r}")
        records.append({"case": "highbit-section-name-json-escaped", "result": "ok", "fixture_sha256": sha256_bytes(highbit_data)})

        mismatch_fixture = temp_dir / "mismatched-section-address.elf"
        mismatch_data = build_fixture(b".mismatch", label_addr_delta=0x1000)
        mismatch_fixture.write_bytes(mismatch_data)
        for args_tuple in (("mitigations",), ("gadgets", "--max-depth", "4"), ("analyze", "--max-depth", "4")):
            stdout = run_ok(binary, mismatch_fixture, args.timeout, *args_tuple)
            if b"section: .mismatch" in stdout:
                raise HarnessError(f"{' '.join(args_tuple)} emitted section label with mismatched sh_addr")
        for command in ("gadgets", "analyze"):
            sections = json_sections(binary, mismatch_fixture, args.timeout, command)
            if sections != {None}:
                raise HarnessError(f"{command}: mismatched sh_addr should be unlabeled, observed {sections!r}")
        records.append({"case": "mismatched-section-address-unlabeled", "result": "ok", "fixture_sha256": sha256_bytes(mismatch_data)})

        fake_fixture = temp_dir / "fake-overlap.elf"
        fake_data = build_fixture(b".text", fake_nonexec_overlap=True)
        fake_fixture.write_bytes(fake_data)
        check_text_contains(binary, fake_fixture, args.timeout, b"section: .text")
        fake_text = run_ok(binary, fake_fixture, args.timeout, "gadgets", "--max-depth", "4")
        if b"section: .fake" in fake_text:
            raise HarnessError("non-executable overlapping section captured gadget label")
        sections = json_sections(binary, fake_fixture, args.timeout, "gadgets")
        if sections != {".text"}:
            raise HarnessError(f"non-executable overlap JSON sections mismatch: {sections!r}")
        records.append({"case": "nonexec-overlap-does-not-label", "result": "ok", "fixture_sha256": sha256_bytes(fake_data)})

        ambiguous_fixture = temp_dir / "ambiguous-overlap.elf"
        ambiguous_data = build_fixture(b".text", ambiguous_exec_overlap=True)
        ambiguous_fixture.write_bytes(ambiguous_data)
        for args_tuple in (("mitigations",), ("gadgets", "--max-depth", "4"), ("analyze", "--max-depth", "4")):
            stdout = run_ok(binary, ambiguous_fixture, args.timeout, *args_tuple)
            if b"section: .x1" in stdout or b"section: .x2" in stdout:
                raise HarnessError(f"{' '.join(args_tuple)} emitted ambiguous executable section label")
        sections = json_sections(binary, ambiguous_fixture, args.timeout, "gadgets")
        if sections != {None}:
            raise HarnessError(f"ambiguous executable overlap should be unlabeled, observed {sections!r}")
        records.append({"case": "ambiguous-exec-overlap-unlabeled", "result": "ok", "fixture_sha256": sha256_bytes(ambiguous_data)})

    args.results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    result_path = args.results_dir / f"section-label-smoke-{timestamp}.json"
    artifact = {
        "schema_version": HARNESS_SCHEMA,
        "harness_version": SCRIPT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "binary": str(binary),
        "records": records,
        "cases": len(records),
    }
    result_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("section-label-smoke: ok")
    print(f"  cases: {len(records)}")
    print(f"  results: {result_path.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as exc:
        print(f"section-label-smoke: error: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
