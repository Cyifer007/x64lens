#!/usr/bin/env python3
"""Validate bounded private GNU property facts and unchanged public output.

This standard-library oracle authors deterministic ELF64 inputs. It treats the
internal C/assembly reconciliation binary as the private-fact authority, uses an
independent Python note parser for the represented byte layouts, and verifies
that changing only private x86 feature bits does not change current public text
or schema 0.2.0 JSON output.
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import tempfile
from pathlib import Path

EXIT_MALFORMED = 5
EXIT_UNSUPPORTED = 6
PT_LOAD = 1
PT_INTERP = 3
PT_NOTE = 4
PT_GNU_PROPERTY = 0x6474E553
PF_X = 1
PF_R = 4
NT_GNU_PROPERTY_TYPE_0 = 5
GNU_PROPERTY_X86_FEATURE_1_AND = 0xC0000002
IBT = 1
SHSTK = 2


def align(value: int, amount: int) -> int:
    return (value + amount - 1) & ~(amount - 1)


def property_note(values: list[int], *, unknown_type: bool = False,
                  bad_size: bool = False, nonzero_padding: bool = False,
                  owner: bytes = b"GNU\0", note_type: int = NT_GNU_PROPERTY_TYPE_0,
                  extra_type: int | None = None) -> bytes:
    desc = bytearray()
    for value in values:
        ptype = 0xDEADBEEF if unknown_type else GNU_PROPERTY_X86_FEATURE_1_AND
        data = struct.pack("<I", value)
        if bad_size:
            data += b"\0" * 4
        desc += struct.pack("<II", ptype, len(data))
        desc += data
        while len(desc) % 8:
            desc.append(0xA5 if nonzero_padding else 0)
    if extra_type is not None:
        desc += struct.pack("<III", extra_type, 4, 0x11223344)
        while len(desc) % 8:
            desc.append(0)
    note = bytearray(struct.pack("<III", len(owner), len(desc), note_type))
    note += owner
    while len(note) % 4:
        note.append(0)
    note += desc
    while len(note) % 8:
        note.append(0)
    return bytes(note)


def unknown_note(*, note_align: int = 8, nonzero_padding: bool = False) -> bytes:
    owner = b"OTHR\0"
    note = bytearray(struct.pack("<III", len(owner), 0, 0x11223344))
    note += owner
    while len(note) % note_align:
        note.append(0xA5 if nonzero_padding else 0)
    return bytes(note)


def carrier_parts(carrier: tuple[int, int, bytes] | tuple[int, int, bytes, int]) -> tuple[int, int, bytes, int]:
    if len(carrier) == 3:
        ptype, off, data = carrier
        return ptype, off, data, 8
    ptype, off, data, palign = carrier
    return ptype, off, data, palign


def elf_with_carriers(
    carriers: list[tuple[int, int, bytes] | tuple[int, int, bytes, int]],
    *, size: int = 1024,
) -> bytes:
    phnum = 1 + len(carriers)
    phoff = 64
    normalized = [carrier_parts(carrier) for carrier in carriers]
    needed = max([size, 0x201, phoff + phnum * 56] + [off + len(data) for _, off, data, _ in normalized])
    blob = bytearray(needed)
    ident = bytearray(16)
    ident[:4] = b"\x7fELF"
    ident[4] = 2
    ident[5] = 1
    ident[6] = 1
    blob[:16] = ident
    struct.pack_into(
        "<HHIQQQIHHHHHH", blob, 16,
        2, 62, 1, 0x400200, phoff, 0, 0, 64, 56, phnum, 0, 0, 0,
    )
    # One fixed executable byte, isolated from note carriers.
    struct.pack_into("<IIQQQQQQ", blob, phoff,
                     PT_LOAD, PF_R | PF_X, 0x200, 0x400200, 0, 1, 1, 1)
    blob[0x200] = 0xC3
    for index, (ptype, off, data, palign) in enumerate(normalized, 1):
        struct.pack_into("<IIQQQQQQ", blob, phoff + index * 56,
                         ptype, PF_R, off, 0, 0, len(data), len(data), palign)
        blob[off:off + len(data)] = data
    return bytes(blob)


def independent_features(
    blob: bytes,
    carriers: list[tuple[int, int, bytes] | tuple[int, int, bytes, int]],
) -> tuple[int, int, int]:
    feature_values: list[int] = []
    unknown = 0
    seen_notes: set[tuple[int, int]] = set()
    canonical_carriers: list[tuple[int, int]] = []
    for carrier in carriers:
        ptype, off, data, palign = carrier_parts(carrier)
        if ptype == PT_GNU_PROPERTY and palign != 8:
            raise ValueError("misaligned PT_GNU_PROPERTY")
        if ptype == PT_NOTE:
            if palign in (0, 1, 4):
                note_align = 4
            elif palign == 8:
                note_align = 8
            else:
                raise ValueError("unsupported PT_NOTE alignment")
        else:
            note_align = 8
        end = off + len(data)
        for prior_off, prior_end in canonical_carriers:
            if (off, end) == (prior_off, prior_end):
                break
            if len(data) and prior_end > prior_off and off < prior_end and prior_off < end:
                raise ValueError("partially overlapping GNU-property carriers")
        else:
            canonical_carriers.append((off, end))
        cursor = off
        while cursor < end:
            if end - cursor < 12:
                if any(blob[cursor:end]):
                    raise ValueError("nonzero short tail")
                break
            namesz, descsz, ntype = struct.unpack_from("<III", blob, cursor)
            name_start = cursor + 12
            name_end = name_start + namesz
            desc_start = align(name_end, note_align)
            desc_end = desc_start + descsz
            next_note = align(desc_end, note_align)
            if next_note > end:
                raise ValueError("truncated note")
            if any(blob[name_end:desc_start]) or any(blob[desc_end:next_note]):
                raise ValueError("nonzero note padding")
            if namesz == 4 and blob[name_start:name_end] == b"GNU\0" and ntype == NT_GNU_PROPERTY_TYPE_0:
                if descsz < 8 or descsz % 8:
                    raise ValueError("invalid GNU property descriptor size")
                key = (cursor, next_note - cursor)
                if key not in seen_notes:
                    seen_notes.add(key)
                    pos = desc_start
                    last_type: int | None = None
                    while pos < desc_end:
                        if desc_end - pos < 8:
                            raise ValueError("truncated property header")
                        ptype, datasz = struct.unpack_from("<II", blob, pos)
                        if last_type is not None and ptype < last_type:
                            raise ValueError("descending GNU property type")
                        last_type = ptype
                        data_start = pos + 8
                        data_end = data_start + datasz
                        next_prop = desc_start + align(data_end - desc_start, 8)
                        if next_prop > desc_end:
                            raise ValueError("truncated property")
                        if any(blob[data_end:next_prop]):
                            raise ValueError("nonzero property padding")
                        if ptype == GNU_PROPERTY_X86_FEATURE_1_AND:
                            if datasz != 4:
                                raise ValueError("bad feature width")
                            value, = struct.unpack_from("<I", blob, data_start)
                            feature_values.append(value)
                            if value & ~(IBT | SHSTK):
                                unknown += 1
                        else:
                            unknown += 1
                        pos = next_prop
            cursor = next_note
    if not feature_values:
        return 0, 0, unknown
    and_value = feature_values[0]
    or_value = feature_values[0]
    for value in feature_values[1:]:
        and_value &= value
        or_value |= value
    return and_value, or_value, unknown


def run(command: list[str], *, expected: int, timeout: float = 3.0) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        timeout=timeout, check=False)
    if cp.returncode != expected:
        raise RuntimeError(
            f"command returned {cp.returncode}, expected {expected}: {command!r}\n"
            f"stdout={cp.stdout[:200]!r}\nstderr={cp.stderr[:400]!r}"
        )
    return cp




def validate_json_output(root: Path, payload: bytes, command: str, sequence: int) -> None:
    report = root / f"{command}-{sequence}.json"
    report.write_bytes(payload)
    validator = Path(__file__).resolve().with_name("validate-json-report.py")
    cp = subprocess.run(
        [
            "python3", str(validator), "--mode", "system",
            "--require-schema", "0.2.0", "--expected-command", command,
            "--require-provenance", "--require-sprint10-effects",
            "--require-sprint10-transfer", "--require-sprint10-memory",
            "--require-sprint10-architectural-effects", str(report),
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError(
            f"public JSON validation failed for {command}: "
            f"stdout={cp.stdout[:200]!r} stderr={cp.stderr[:400]!r}"
        )

def oracle_selftest() -> tuple[int, int]:
    """Exercise the independent property parser without an analyzer binary."""
    cases = [
        ([], (0, 0, 0)),
        ([(PT_NOTE, 0x300, property_note([0]))], (0, 0, 0)),
        ([(PT_NOTE, 0x300, property_note([IBT]))], (IBT, IBT, 0)),
        ([(PT_GNU_PROPERTY, 0x300, property_note([IBT | SHSTK]))],
         (IBT | SHSTK, IBT | SHSTK, 0)),
        ([(PT_NOTE, 0x300, property_note([IBT | 0x80]))],
         (IBT | 0x80, IBT | 0x80, 1)),
        ([(PT_NOTE, 0x300, property_note([0x11223344], unknown_type=True))],
         (0, 0, 1)),
    ]
    duplicate = property_note([IBT | SHSTK])
    cases.append((
        [(PT_NOTE, 0x300, duplicate), (PT_GNU_PROPERTY, 0x300, duplicate)],
        (IBT | SHSTK, IBT | SHSTK, 0),
    ))
    aligned_stream = unknown_note(note_align=8) + property_note([IBT | SHSTK])
    cases.append((
        [(PT_NOTE, 0x300, aligned_stream, 8)],
        (IBT | SHSTK, IBT | SHSTK, 0),
    ))
    # The second note's descriptor begins at absolute offset mod 8 == 4.
    # Property alignment is nevertheless valid because it is descriptor-relative.
    aligned4_stream = unknown_note(note_align=4) + property_note([IBT | SHSTK])
    cases.append((
        [(PT_NOTE, 0x300, aligned4_stream, 4)],
        (IBT | SHSTK, IBT | SHSTK, 0),
    ))
    for carriers, expected in cases:
        blob = elf_with_carriers(carriers)
        observed = independent_features(blob, carriers)
        if observed != expected:
            raise RuntimeError(f"independent oracle mismatch: got={observed} expected={expected}")

    malformed: list[tuple[bytes, list[tuple[int, int, bytes]]]] = []
    malformed.append((
        elf_with_carriers([(PT_NOTE, 0x300, b"\xa5" * 8)]),
        [(PT_NOTE, 0x300, b"\xa5" * 8)],
    ))
    truncated = bytearray(32)
    struct.pack_into("<III", truncated, 0, 4, 64, NT_GNU_PROPERTY_TYPE_0)
    truncated[12:16] = b"GNU\0"
    malformed.append((
        elf_with_carriers([(PT_NOTE, 0x300, bytes(truncated))]),
        [(PT_NOTE, 0x300, bytes(truncated))],
    ))
    bad_width = property_note([IBT], bad_size=True)
    malformed.append((
        elf_with_carriers([(PT_NOTE, 0x300, bad_width)]),
        [(PT_NOTE, 0x300, bad_width)],
    ))
    bad_padding = property_note([IBT], nonzero_padding=True)
    malformed.append((
        elf_with_carriers([(PT_NOTE, 0x300, bad_padding)]),
        [(PT_NOTE, 0x300, bad_padding)],
    ))
    bad_outer_padding = unknown_note(note_align=8, nonzero_padding=True)
    malformed.append((
        elf_with_carriers([(PT_NOTE, 0x300, bad_outer_padding, 8)]),
        [(PT_NOTE, 0x300, bad_outer_padding, 8)],
    ))
    misaligned_property = property_note([IBT])
    malformed.append((
        elf_with_carriers([(PT_GNU_PROPERTY, 0x300, misaligned_property, 4)]),
        [(PT_GNU_PROPERTY, 0x300, misaligned_property, 4)],
    ))
    malformed.append((
        elf_with_carriers([(PT_NOTE, 0x300, b"", 16)]),
        [(PT_NOTE, 0x300, b"", 16)],
    ))
    descending = property_note([IBT], extra_type=1)
    malformed.append((
        elf_with_carriers([(PT_NOTE, 0x300, descending)]),
        [(PT_NOTE, 0x300, descending)],
    ))
    empty_desc = property_note([])
    malformed.append((
        elf_with_carriers([(PT_NOTE, 0x300, empty_desc)]),
        [(PT_NOTE, 0x300, empty_desc)],
    ))
    overlap_note = property_note([IBT | SHSTK])
    overlap_tail = b"\0" * 12
    overlap_carriers = [
        (PT_NOTE, 0x300, overlap_note, 4),
        (PT_NOTE, 0x300 + len(overlap_note) - 4, overlap_tail, 4),
    ]
    malformed.append((elf_with_carriers(overlap_carriers), overlap_carriers))
    for blob, carriers in malformed:
        try:
            independent_features(blob, carriers)
        except ValueError:
            continue
        raise RuntimeError("independent oracle accepted malformed GNU property bytes")
    return len(cases), len(malformed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyzer", type=Path)
    parser.add_argument("--internal-harness", type=Path)
    parser.add_argument("--oracle-only", action="store_true")
    args = parser.parse_args()

    oracle_cases, malformed_cases = oracle_selftest()
    if args.oracle_only:
        print(
            "sprint12-gnu-property-oracle-smoke: ok "
            f"cases={oracle_cases} malformed={malformed_cases} canonical_duplicates=1"
        )
        return 0
    if args.analyzer is None or args.internal_harness is None:
        parser.error("--analyzer and --internal-harness are required unless --oracle-only is used")

    harness = run([str(args.internal_harness)], expected=0)
    expected_banner = b"sprint12-gnu-property-internal: ok cases=26 states=4 carriers=32 contributors=64 summary_bytes=264 context_bytes=3160 alignments=2 ordering=1\n"
    if harness.stdout != expected_banner:
        raise RuntimeError(f"unexpected internal harness output: {harness.stdout!r}")

    with tempfile.TemporaryDirectory(prefix="x64lens-gnu-property-") as td:
        root = Path(td)
        target = root / "property.elf"
        no_bits = property_note([0])
        both_bits = property_note([IBT | SHSTK])
        carriers_a = [(PT_NOTE, 0x300, no_bits)]
        carriers_b = [(PT_NOTE, 0x300, both_bits)]
        blob_a = elf_with_carriers(carriers_a)
        blob_b = elf_with_carriers(carriers_b)
        assert independent_features(blob_a, carriers_a) == (0, 0, 0)
        assert independent_features(blob_b, carriers_b) == (3, 3, 0)

        commands = [
            [str(args.analyzer), "mitigations", str(target)],
            [str(args.analyzer), "gadgets", "--format", "json", "--max-depth", "4", str(target)],
            [str(args.analyzer), "analyze", "--format", "json", "--max-depth", "4", str(target)],
        ]
        outputs: list[bytes] = []
        target.write_bytes(blob_a)
        for sequence, command in enumerate(commands):
            cp = run(command, expected=0)
            if "--format" in command:
                parsed = json.loads(cp.stdout)
                validate_json_output(root, cp.stdout, str(parsed["command"]), sequence)
            outputs.append(cp.stdout)
        target.write_bytes(blob_b)
        for sequence, (command, expected_output) in enumerate(zip(commands, outputs, strict=True), 10):
            cp = run(command, expected=0)
            if cp.stdout != expected_output:
                raise RuntimeError(f"private GNU-property facts changed public output: {command!r}")
            if "--format" in command:
                parsed = json.loads(cp.stdout)
                validate_json_output(root, cp.stdout, str(parsed["command"]), sequence)

        malformed: list[bytes] = []
        malformed.append(elf_with_carriers([(PT_NOTE, 0x300, b"\xa5" * 8)]))
        truncated = bytearray(32)
        struct.pack_into("<III", truncated, 0, 4, 64, 5)
        truncated[12:16] = b"GNU\0"
        malformed.append(elf_with_carriers([(PT_NOTE, 0x300, bytes(truncated))]))
        malformed.append(elf_with_carriers([(PT_NOTE, 0x300, property_note([3], bad_size=True))]))
        malformed.append(elf_with_carriers([(PT_NOTE, 0x300, property_note([3], nonzero_padding=True))]))
        malformed.append(elf_with_carriers([
            (PT_NOTE, 0x300, unknown_note(note_align=8, nonzero_padding=True), 8)
        ]))
        malformed.append(elf_with_carriers([
            (PT_GNU_PROPERTY, 0x300, property_note([3]), 4)
        ]))
        malformed.append(elf_with_carriers([
            (PT_NOTE, 0x300, property_note([3], extra_type=1), 8)
        ]))
        malformed.append(elf_with_carriers([
            (PT_NOTE, 0x300, property_note([]), 8)
        ]))
        overlap_note = property_note([IBT | SHSTK])
        malformed.append(elf_with_carriers([
            (PT_NOTE, 0x300, overlap_note, 4),
            (PT_NOTE, 0x300 + len(overlap_note) - 4, b"\0" * 12, 4),
        ]))

        for index, blob in enumerate(malformed):
            target.write_bytes(blob)
            for command in commands:
                cp = run(command, expected=EXIT_MALFORMED)
                if cp.stdout:
                    raise RuntimeError(f"malformed case {index} emitted partial stdout: {command!r}")

        target.write_bytes(elf_with_carriers([(PT_NOTE, 0x300, b"", 16)]))
        for command in commands:
            cp = run(command, expected=EXIT_UNSUPPORTED)
            if cp.stdout:
                raise RuntimeError(f"unsupported note alignment emitted stdout: {command!r}")

        # A recognized descriptor above the explicit 64 KiB cap is unsupported.
        huge_desc = bytearray(65560)
        struct.pack_into("<III", huge_desc, 0, 4, 65537, 5)
        huge_desc[12:16] = b"GNU\0"
        target.write_bytes(elf_with_carriers([(PT_NOTE, 0x300, bytes(huge_desc))], size=0x300 + len(huge_desc)))
        for command in commands:
            cp = run(command, expected=EXIT_UNSUPPORTED)
            if cp.stdout:
                raise RuntimeError(f"unsupported GNU-property case emitted stdout: {command!r}")

    print(
        "sprint12-gnu-property-smoke: ok private_cases=26 oracle_cases=9 "
        "public_pairs=3 malformed=9 unsupported=2 schema=unchanged alignments=2 ordering=1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
