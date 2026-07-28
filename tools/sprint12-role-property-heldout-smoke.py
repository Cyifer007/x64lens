#!/usr/bin/env python3
"""Confirm private binary-role and GNU-property facts on a 96-object matrix.

The gate keeps natural compiler/linker outputs and synthetic metamorphic objects
as separate evidence strata.  An independent standard-library ELF reader authors
expected private fact vectors; the assembly/C fact probe is executed three times
per object and must reproduce the exact vector.  No private fact is promoted into
schema 0.2.0 or public text by this development-only gate.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
EXIT_MALFORMED = 5
ET_EXEC = 2
ET_DYN = 3
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
PT_NOTE = 4
PT_GNU_PROPERTY = 0x6474E553
DT_NULL = 0
DT_STRTAB = 5
DT_STRSZ = 10
DT_SONAME = 14
DT_FLAGS_1 = 0x6FFFFFFB
DF_1_PIE = 0x08000000
NT_GNU_PROPERTY_TYPE_0 = 5
GNU_PROPERTY_X86_FEATURE_1_AND = 0xC0000002
IBT = 1
SHSTK = 2
ROLE_UNKNOWN = 0
ROLE_EXECUTABLE = 1
ROLE_SHARED = 2
ROLE_AMBIGUOUS = 3
ROLE_CONTRADICTORY = 4
PROPERTY_UNKNOWN = 0
PROPERTY_ABSENT = 1
PROPERTY_PRESENT = 2
PROPERTY_CONTRADICTORY = 3
ROLE_ET_EXEC = 1 << 0
ROLE_ET_DYN = 1 << 1
ROLE_ENTRY = 1 << 2
ROLE_INTERP = 1 << 3
ROLE_DF1_PIE = 1 << 4
ROLE_SONAME = 1 << 5
ROLE_DUP_INTERP = 1 << 6
ROLE_DUP_FLAGS1 = 1 << 7
ROLE_DUP_SONAME = 1 << 8
ROLE_CONFLICT_FLAGS1 = 1 << 9
ROLE_CONFLICT_SONAME = 1 << 10
FACT_FIELDS = (
    "status", "phnum", "role_state", "role_evidence", "interp_count",
    "flags1_count", "soname_count", "property_view_count",
    "property_contributor_count", "property_note_count",
    "property_feature_count", "property_feature_and", "property_feature_or",
    "property_unknown_count", "property_conflict_count",
    "property_overlap_count", "ibt_state", "shstk_state",
)


class HeldoutError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HeldoutError(message)


def align(value: int, amount: int) -> int:
    return (value + amount - 1) & ~(amount - 1)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_module(name: str, relative: str) -> Any:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(command: list[str], *, expected: int = 0, cwd: Path | None = None) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        check=False, timeout=20.0)
    require(cp.returncode == expected,
            f"command returned {cp.returncode}, expected {expected}: {command!r}\n"
            f"stdout={cp.stdout[:300]!r}\nstderr={cp.stderr[:600]!r}")
    return cp


def probe_fact(probe: Path, target: Path) -> tuple[bytes, dict[str, int]]:
    cp = run([str(probe), str(target)])
    value = json.loads(cp.stdout)
    require(isinstance(value, dict), "fact probe did not emit an object")
    require(tuple(value) == FACT_FIELDS, f"fact probe field order/shape changed: {tuple(value)}")
    require(all(isinstance(value[field], int) for field in FACT_FIELDS), "fact probe emitted noninteger facts")
    return cp.stdout, {field: int(value[field]) for field in FACT_FIELDS}


def phdrs(blob: bytes) -> tuple[int, int, list[tuple[int, int, int, int, int, int, int, int]]]:
    require(len(blob) >= 64 and blob[:7] == b"\x7fELF\x02\x01\x01", "not ELF64 little-endian")
    etype, machine, version, entry, phoff, _shoff, _flags, ehsize, phentsize, phnum, *_ = struct.unpack_from(
        "<HHIQQQIHHHHHH", blob, 16
    )
    require(machine == 62 and version == 1 and ehsize == 64 and phentsize == 56, "unsupported ELF header")
    require(phoff + phnum * 56 <= len(blob), "truncated program-header table")
    records = [struct.unpack_from("<IIQQQQQQ", blob, phoff + index * 56) for index in range(phnum)]
    return etype, entry, records


def va_to_offset(records: Iterable[tuple[int, ...]], va: int, length: int, blob: bytes) -> int:
    for ptype, _flags, off, vaddr, _paddr, filesz, _memsz, _align in records:
        if ptype != PT_LOAD or va < vaddr:
            continue
        delta = va - vaddr
        if delta <= filesz and length <= filesz - delta and off + delta + length <= len(blob):
            return off + delta
    raise HeldoutError("dynamic string address is not file-backed")


def empty_vector(phnum: int) -> dict[str, int]:
    return {field: 0 for field in FACT_FIELDS} | {"status": 0, "phnum": phnum}


def parse_role(blob: bytes, etype: int, entry: int, records: list[tuple[int, ...]], vector: dict[str, int]) -> None:
    interp_count = 0
    flags1: list[int] = []
    sonames: list[int] = []
    strtab: int | None = None
    strsz: int | None = None
    for ptype, _flags, off, _vaddr, _paddr, filesz, _memsz, _align in records:
        if ptype == PT_INTERP:
            interp_count += 1
            require(filesz >= 2 and off + filesz <= len(blob), "malformed PT_INTERP")
            data = blob[off:off + filesz]
            require(data[-1] == 0 and data[0] != 0 and b"\0" not in data[:-1], "invalid PT_INTERP string")
        if ptype != PT_DYNAMIC:
            continue
        require(filesz % 16 == 0 and off + filesz <= len(blob), "malformed PT_DYNAMIC")
        for cursor in range(off, off + filesz, 16):
            tag, value = struct.unpack_from("<qQ", blob, cursor)
            if tag == DT_NULL:
                break
            if tag == DT_FLAGS_1:
                flags1.append(value)
            elif tag == DT_STRTAB:
                require(strtab is None, "duplicate DT_STRTAB")
                strtab = value
            elif tag == DT_STRSZ:
                require(strsz is None, "duplicate DT_STRSZ")
                strsz = value
            elif tag == DT_SONAME:
                sonames.append(value)

    evidence = 0
    if etype == ET_EXEC:
        evidence |= ROLE_ET_EXEC
    elif etype == ET_DYN:
        evidence |= ROLE_ET_DYN
    if entry:
        evidence |= ROLE_ENTRY
    if interp_count:
        evidence |= ROLE_INTERP
    if interp_count > 1:
        evidence |= ROLE_DUP_INTERP
    if len(flags1) > 1:
        evidence |= ROLE_DUP_FLAGS1
    if any(value & DF_1_PIE for value in flags1):
        evidence |= ROLE_DF1_PIE
    if len(set(flags1)) > 1:
        evidence |= ROLE_CONFLICT_FLAGS1
    if sonames:
        require(strtab is not None and strsz is not None, "DT_SONAME lacks bounded string table")
        base = va_to_offset(records, strtab, strsz, blob)
        for index in sonames:
            require(index < strsz, "DT_SONAME index outside DT_STRSZ")
            tail = blob[base + index:base + strsz]
            nul = tail.find(b"\0")
            require(nul > 0, "DT_SONAME is empty or unterminated")
        evidence |= ROLE_SONAME
    if len(sonames) > 1:
        evidence |= ROLE_DUP_SONAME
    if len(set(sonames)) > 1:
        evidence |= ROLE_CONFLICT_SONAME

    contradiction = evidence & (
        ROLE_DUP_INTERP | ROLE_DUP_FLAGS1 | ROLE_DUP_SONAME |
        ROLE_CONFLICT_FLAGS1 | ROLE_CONFLICT_SONAME
    )
    if contradiction:
        state = ROLE_CONTRADICTORY
    elif etype == ET_EXEC:
        state = ROLE_CONTRADICTORY if evidence & (ROLE_DF1_PIE | ROLE_SONAME) else ROLE_EXECUTABLE
    elif etype == ET_DYN:
        executable = bool(evidence & (ROLE_INTERP | ROLE_DF1_PIE))
        shared = bool(evidence & ROLE_SONAME)
        if executable and shared:
            state = ROLE_CONTRADICTORY
        elif executable:
            state = ROLE_EXECUTABLE
        elif shared and not entry:
            state = ROLE_SHARED
        elif entry:
            state = ROLE_AMBIGUOUS
        else:
            state = ROLE_UNKNOWN
    else:
        state = ROLE_UNKNOWN

    vector.update(
        role_state=state,
        role_evidence=evidence,
        interp_count=interp_count,
        flags1_count=len(flags1),
        soname_count=len(sonames),
    )


def parse_properties(blob: bytes, records: list[tuple[int, ...]], vector: dict[str, int]) -> None:
    carriers: list[tuple[int, int, int, int]] = []
    for ptype, _flags, off, _vaddr, _paddr, filesz, _memsz, palign in records:
        if ptype in (PT_NOTE, PT_GNU_PROPERTY):
            require(off + filesz <= len(blob), "property carrier outside file")
            carriers.append((ptype, off, off + filesz, palign))
    require(len(carriers) <= 32, "property carrier capacity exceeded")

    canonical: list[tuple[int, int, int, int]] = []
    overlap_count = 0
    for carrier in carriers:
        ptype, off, end, palign = carrier
        for prior in canonical:
            if (off, end) == (prior[1], prior[2]):
                break
            if off < prior[2] and prior[1] < end:
                overlap_count += 1
                raise HeldoutError("partially overlapping property carriers")
        else:
            canonical.append(carrier)

    values: list[int] = []
    unknown = 0
    note_count = 0
    for ptype, off, end, palign in canonical:
        if ptype == PT_GNU_PROPERTY:
            require(palign == 8, "PT_GNU_PROPERTY alignment is not eight")
            note_align = 8
        elif palign in (0, 1, 4):
            note_align = 4
        elif palign == 8:
            note_align = 8
        else:
            raise HeldoutError("unsupported PT_NOTE alignment")
        cursor = off
        while cursor < end:
            if end - cursor < 12:
                require(not any(blob[cursor:end]), "nonzero short note tail")
                break
            namesz, descsz, ntype = struct.unpack_from("<III", blob, cursor)
            name_start = cursor + 12
            name_end = name_start + namesz
            desc_start = align(name_end, note_align)
            desc_end = desc_start + descsz
            next_note = align(desc_end, note_align)
            require(next_note <= end, "truncated note")
            require(not any(blob[name_end:desc_start]) and not any(blob[desc_end:next_note]),
                    "nonzero note padding")
            if namesz == 4 and blob[name_start:name_end] == b"GNU\0" and ntype == NT_GNU_PROPERTY_TYPE_0:
                require(descsz >= 8 and descsz % 8 == 0, "invalid GNU property descriptor size")
                note_count += 1
                pos = desc_start
                last_type: int | None = None
                while pos < desc_end:
                    require(desc_end - pos >= 8, "truncated property header")
                    prop_type, data_size = struct.unpack_from("<II", blob, pos)
                    if last_type is not None:
                        require(prop_type >= last_type, "descending GNU property type")
                    last_type = prop_type
                    data_start = pos + 8
                    data_end = data_start + data_size
                    next_prop = desc_start + align(data_end - desc_start, 8)
                    require(next_prop <= desc_end, "truncated property data")
                    require(not any(blob[data_end:next_prop]), "nonzero property padding")
                    if prop_type == GNU_PROPERTY_X86_FEATURE_1_AND:
                        require(data_size == 4, "bad feature width")
                        value, = struct.unpack_from("<I", blob, data_start)
                        values.append(value)
                        if value & ~(IBT | SHSTK):
                            unknown += 1
                    else:
                        unknown += 1
                    pos = next_prop
            cursor = next_note

    vector["property_view_count"] = len(canonical)
    vector["property_contributor_count"] = len(carriers)
    vector["property_note_count"] = note_count
    vector["property_feature_count"] = len(values)
    vector["property_unknown_count"] = unknown
    vector["property_overlap_count"] = overlap_count
    if not values:
        return
    and_value = values[0]
    or_value = values[0]
    for value in values[1:]:
        and_value &= value
        or_value |= value
    vector["property_feature_and"] = and_value
    vector["property_feature_or"] = or_value
    vector["property_conflict_count"] = int(and_value != or_value)
    for name, bit in (("ibt_state", IBT), ("shstk_state", SHSTK)):
        if and_value & bit:
            state = PROPERTY_PRESENT
        elif or_value & bit:
            state = PROPERTY_CONTRADICTORY
        else:
            state = PROPERTY_ABSENT
        vector[name] = state


def independent_vector(blob: bytes) -> dict[str, int]:
    etype, entry, records = phdrs(blob)
    vector = empty_vector(len(records))
    # Dynamic/SONAME parsing contributes raw evidence before role classification.
    try:
        parse_role(blob, etype, entry, records, vector)
    except HeldoutError:
        vector["status"] = EXIT_MALFORMED
        vector["role_state"] = ROLE_UNKNOWN
        return vector
    role_vector = dict(vector)
    try:
        parse_properties(blob, records, vector)
    except HeldoutError:
        # GNU-property failure occurs before the role classifier.  Preserve only
        # parser-authored SONAME/conflict evidence, matching the implementation
        # ordering while keeping all private property fields at their defaults.
        failed = empty_vector(len(records))
        failed["status"] = EXIT_MALFORMED
        failed["role_evidence"] = role_vector["role_evidence"] & (
            ROLE_SONAME | ROLE_CONFLICT_FLAGS1 | ROLE_CONFLICT_SONAME
        )
        failed["interp_count"] = role_vector["interp_count"]
        failed["flags1_count"] = role_vector["flags1_count"]
        failed["soname_count"] = role_vector["soname_count"]
        return failed
    return vector


def write_source(path: Path, compiler_tag: int, variant: int) -> None:
    path.write_text(
        ".text\n.global _start\n.type _start,@function\n_start:\n"
        + ("    nop\n" * variant)
        + "    ret\n.global x64lens_library_entry\n.type x64lens_library_entry,@function\n"
        + "x64lens_library_entry:\n"
        + ("    nop\n" * (variant + 1))
        + "    ret\n.section .rodata\n.global x64lens_heldout_identity\n"
        + f"x64lens_heldout_identity: .byte {compiler_tag}, {variant}\n"
        + '.section .note.GNU-stack,"",@progbits\n',
        encoding="utf-8",
    )


def natural_objects(root: Path) -> list[tuple[str, bytes, dict[str, Any]]]:
    result: list[tuple[str, bytes, dict[str, Any]]] = []
    ld = shutil.which("ld.bfd")
    require(ld is not None, "ld.bfd is required")
    for compiler, tag in (("gcc", 0x47), ("clang", 0x43)):
        executable = shutil.which(compiler)
        require(executable is not None, f"{compiler} is required")
        for variant in range(2):
            source = root / f"{compiler}-v{variant}.S"
            obj = root / f"{compiler}-v{variant}.o"
            write_source(source, tag, variant)
            run([executable, "-c", "-fPIC", "-o", str(obj), str(source)])
            for role in ("exec", "pie", "dso"):
                for state, bits in (("none", 0), ("ibt", IBT), ("shstk", SHSTK), ("both", IBT | SHSTK)):
                    name = f"natural-{compiler}-v{variant}-{role}-{state}.elf"
                    target = root / name
                    command = [ld, "--build-id=none"]
                    if role == "exec":
                        command += ["-e", "_start"]
                    elif role == "pie":
                        command += ["-pie", "-dynamic-linker", "/lib64/ld-linux-x86-64.so.2", "-e", "_start"]
                    else:
                        command += ["-shared", "-e", "0", "-soname", f"lib{name}.so"]
                    if bits & IBT:
                        command += ["-z", "ibt"]
                    if bits & SHSTK:
                        command += ["-z", "shstk"]
                    command += ["-o", str(target), str(obj)]
                    run(command)
                    blob = target.read_bytes()
                    result.append((name, blob, {"stratum": "natural", "compiler": compiler,
                                               "variant": variant, "role": role, "property_state": state,
                                               "command": command}))
    return result


def metamorphic_objects(root: Path) -> list[tuple[str, bytes, dict[str, Any]]]:
    """Create 48 metamorphic objects with parser-visible identity differences."""

    meta = load_module("p069_meta", "tools/sprint12-role-property-metamorphic-smoke.py")
    prop = load_module("p069_prop", "tools/sprint12-gnu-property-smoke.py")
    result: list[tuple[str, bytes, dict[str, Any]]] = []
    for role in ("exec", "pie", "shared"):
        for state, bits in (("none", 0), ("ibt", IBT), ("shstk", SHSTK), ("both", IBT | SHSTK)):
            note = prop.property_note([bits])
            for encoding, dual in (("canonical", False), ("dual", True)):
                name = f"metamorphic-{role}-{state}-{encoding}.elf"
                result.append((name, meta.build_object(role, note, dual=dual),
                               {"stratum": "metamorphic", "family": "positive", "role": role,
                                "property_state": state, "encoding": encoding}))

    edge_objects: list[tuple[str, bytes]] = []
    for variant in range(4):
        edge_objects.append((
            "unknown-bit",
            meta.build_object("exec", prop.property_note([IBT | (0x80 << variant)])),
        ))
        edge_objects.append((
            "conflict",
            meta.build_object(
                "pie",
                prop.property_note([IBT | (0x80 << variant), SHSTK if variant & 1 else 0]),
            ),
        ))
        edge_objects.append((
            "descending-order",
            meta.build_object("shared", prop.property_note([IBT], extra_type=1 + variant)),
        ))
        edge_objects.append((
            "role-contradiction",
            meta.build_object(
                "contradictory",
                prop.property_note([IBT | SHSTK | (0x80 << variant)]),
            ),
        ))

        bad_width = bytearray(prop.property_note([IBT], bad_size=True))
        # Descriptor starts at byte 16; property data starts at byte 24.  The
        # eight-byte width is invalid, and the varied data byte remains inside
        # the bounded property record consumed by both parsers.
        bad_width[24 + variant] = 0x40 + variant
        edge_objects.append(("bad-feature-width", meta.build_object("exec", bytes(bad_width))))

        bad_padding = bytearray(prop.property_note([IBT], nonzero_padding=True))
        # Four descriptor-relative padding bytes follow the four-byte feature
        # value. Vary one nonzero byte per object so the parser-visible layouts
        # are independent rather than SHA-only aliases outside all PHDRs.
        bad_padding[28 + variant] = 0xB0 + variant
        edge_objects.append(("nonzero-padding", meta.build_object("exec", bytes(bad_padding))))

    family_counts: dict[str, int] = {}
    for family, blob in edge_objects:
        variant = family_counts.get(family, 0)
        family_counts[family] = variant + 1
        name = f"metamorphic-edge-{family}-v{variant}.elf"
        result.append((name, blob, {"stratum": "metamorphic", "family": family,
                                   "variant": variant}))
    require(family_counts == {name: 4 for name in (
        "unknown-bit", "conflict", "descending-order", "role-contradiction",
        "bad-feature-width", "nonzero-padding",
    )}, "metamorphic edge-family accounting changed")
    return result


def identity(path: Path, label: str, *, executable: bool = False) -> dict[str, Any]:
    absolute = Path(os.path.abspath(path))
    metadata = absolute.lstat()
    require(stat.S_ISREG(metadata.st_mode), f"{label} is not a regular file: {absolute}")
    require(not absolute.is_symlink(), f"{label} may not be a symlink: {absolute}")
    if executable:
        require(os.access(absolute, os.X_OK), f"{label} is not executable: {absolute}")
    data = absolute.read_bytes()
    return {
        "path": str(absolute),
        "size_bytes": len(data),
        "sha256": sha256_bytes(data),
        "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
    }


def load_authority(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    authority_identity = identity(path, "held-out authority")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "held-out authority must be an object")
    require(set(value) == {
        "authority_id", "evidence_class", "frozen", "publication_eligible", "purpose",
        "natural_stratum", "metamorphic_stratum", "public_boundary", "acceptance",
    }, "held-out authority fields changed")
    require(value["authority_id"] == "sprint12-role-property-heldout-v1", "held-out authority id changed")
    require(value["evidence_class"] == "diagnostic", "held-out evidence class changed")
    require(value["frozen"] is False, "held-out authority must remain frozen=false")
    require(value["publication_eligible"] is False,
            "held-out authority must remain publication_eligible=false")
    natural = value["natural_stratum"]
    metamorphic = value["metamorphic_stratum"]
    boundary = value["public_boundary"]
    acceptance = value["acceptance"]
    require(isinstance(natural, dict) and natural.get("object_count") == 48,
            "held-out natural stratum changed")
    require(isinstance(metamorphic, dict) and metamorphic.get("object_count") == 48,
            "held-out metamorphic stratum changed")
    require(isinstance(boundary, dict) and boundary.get("schema_version") == "0.2.0"
            and boundary.get("private_fields_exposed") is False
            and boundary.get("public_policy_decision_authorized") is False
            and boundary.get("commands") == [
                "info", "mitigations", "gadgets --format json", "analyze --format json"
            ]
            and boundary.get("stdout_and_stderr_private_leak_scan") is True
            and boundary.get("formal_schema_authority_consumed") is True,
            "held-out public boundary changed")
    require(isinstance(acceptance, dict) and acceptance.get("object_count") == 96
            and acceptance.get("probe_run_count") == 288
            and acceptance.get("exact_vector_match_count") == 96
            and acceptance.get("natural_unique_identity_count") == 48
            and acceptance.get("provisional_overlap_count") == 0
            and acceptance.get("strata_close_independently") is True
            and acceptance.get("public_command_count") == 384
            and acceptance.get("retained_fact_field_count") == 18
            and acceptance.get("parser_visible_edge_layout_count") == 24
            and acceptance.get("provisional_target_count") == 24
            and acceptance.get("all_authorities_consumed") is True,
            "held-out acceptance authority changed")
    return value, authority_identity


def verify_provisional_corpus(root: Path) -> tuple[dict[str, Any], set[str], dict[str, Any]]:
    require(root.is_dir(), f"authenticated provisional corpus is missing: {root}")
    builder = load_module("p069_corpus_builder", "benchmarks/scripts/build-provisional-corpus.py")
    manifest = builder.verify_corpus(root)
    require(manifest.get("corpus_id") == root.name, "provisional corpus id changed")
    require(manifest.get("target_count") == 24, "provisional corpus target count changed")
    require(manifest.get("evidence_class") == "diagnostic"
            and manifest.get("frozen") is False
            and manifest.get("publication_eligible") is False,
            "provisional corpus authority changed")
    targets = root / "targets"
    paths = sorted(path for path in targets.iterdir() if path.is_file())
    require(len(paths) == 24, "provisional corpus targets are incomplete")
    hashes = {sha256_bytes(path.read_bytes()) for path in paths}
    require(len(hashes) == 24, "provisional corpus target identities are not unique")
    return manifest, hashes, identity(root / "corpus-manifest.json", "provisional corpus manifest")


def parser_visible_digest(blob: bytes) -> str:
    _etype, _entry, records = phdrs(blob)
    visible = bytearray(blob[:64 + len(records) * 56])
    for _ptype, _flags, off, _vaddr, _paddr, filesz, _memsz, _align in records:
        require(off + filesz <= len(blob), "parser-visible PHDR range exceeds object")
        visible.extend(struct.pack("<QQ", off, filesz))
        visible.extend(blob[off:off + filesz])
    return sha256_bytes(bytes(visible))


def validate_edge_diversity(objects: list[tuple[str, bytes, dict[str, Any]]]) -> None:
    groups: dict[str, set[str]] = {}
    for name, blob, metadata in objects:
        if not name.startswith("metamorphic-edge-"):
            continue
        family = str(metadata["family"])
        groups.setdefault(family, set()).add(parser_visible_digest(blob))
    require(len(groups) == 6, "metamorphic edge-family count changed")
    require(all(len(values) == 4 for values in groups.values()),
            "metamorphic edge variants are not parser-visible independent layouts")


def validate_formal_schema(schema: dict[str, Any], report: dict[str, Any], label: str) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise HeldoutError("python3-jsonschema is required for held-out schema validation") from exc
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(report), key=lambda error: list(error.absolute_path))
    require(not errors, f"formal schema rejected {label}: {errors[0].message if errors else ''}")


def public_commands(
    analyzer: Path,
    target: Path,
    expected: dict[str, int],
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    meta = load_module("p069_public_boundary", "tools/sprint12-role-property-metamorphic-smoke.py")
    commands = [
        ("info", [str(analyzer), "info", str(target)]),
        ("mitigations", [str(analyzer), "mitigations", str(target)]),
        ("gadgets", [str(analyzer), "gadgets", "--format", "json", "--max-depth", "4", str(target)]),
        ("analyze", [str(analyzer), "analyze", "--format", "json", "--max-depth", "4", str(target)]),
    ]
    malformed = expected["status"] == EXIT_MALFORMED
    records: list[dict[str, Any]] = []
    for command_id, command in commands:
        expected_exit = 0 if not malformed or command_id == "info" else EXIT_MALFORMED
        cp = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False, timeout=10.0)
        require(cp.returncode == expected_exit,
                f"public command {command_id} returned {cp.returncode}, expected {expected_exit}: {target.name}")
        meta.assert_no_private_public_text(cp.stdout)
        meta.assert_no_private_public_text(cp.stderr)
        if expected_exit == 0:
            require(cp.stdout, f"public command emitted empty stdout: {command_id}/{target.name}")
        else:
            require(not cp.stdout, f"malformed object emitted partial stdout: {command_id}/{target.name}")
        if command_id in {"gadgets", "analyze"} and expected_exit == 0:
            report = json.loads(cp.stdout)
            require(report.get("schema_version") == "0.2.0", "held-out report schema changed")
            require(report.get("command") == command_id, "held-out report command identity changed")
            meta.assert_no_private_public_fields(report)
            validate_formal_schema(schema, report, f"{target.name}/{command_id}")
        records.append({
            "command_id": command_id,
            "argv": command,
            "exit_code": cp.returncode,
            "stdout": cp.stdout,
            "stderr": cp.stderr,
            "stdout_sha256": sha256_bytes(cp.stdout),
            "stderr_sha256": sha256_bytes(cp.stderr),
        })
    return records


def render_tsv(rows: list[dict[str, Any]]) -> str:
    fields = ["name", "stratum", "family", "sha256", "size_bytes", "parser_visible_sha256",
              "repeat_sha256", "public_command_count"]
    fields += [f"expected_{field}" for field in FACT_FIELDS]
    fields += [f"observed_{field}" for field in FACT_FIELDS]
    lines = ["\t".join(fields)]
    for row in rows:
        values = [str(row.get(field, "")) for field in fields]
        lines.append("\t".join(values))
    return "\n".join(lines) + "\n"


def write_result(
    result_dir: Path,
    objects: list[tuple[str, bytes, dict[str, Any]]],
    rows: list[dict[str, Any]],
    public: dict[str, list[dict[str, Any]]],
    identities: dict[str, Any],
    authority: dict[str, Any],
    provisional_manifest: dict[str, Any],
) -> None:
    require(not result_dir.exists(), f"result directory already exists: {result_dir}")
    result_dir.mkdir(parents=True)
    object_dir = result_dir / "objects"
    facts_dir = result_dir / "facts"
    public_dir = result_dir / "public"
    object_dir.mkdir()
    facts_dir.mkdir()
    public_dir.mkdir()
    metadata_by_name = {name: metadata for name, _blob, metadata in objects}
    for name, blob, _metadata in objects:
        path = object_dir / name
        path.write_bytes(blob)
        path.chmod(0o444)
    for row in rows:
        name = str(row["name"])
        expected = {field: row[f"expected_{field}"] for field in FACT_FIELDS}
        observed = {field: row[f"observed_{field}"] for field in FACT_FIELDS}
        (facts_dir / f"{name}.expected.json").write_text(
            json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (facts_dir / f"{name}.observed.json").write_text(
            json.dumps(observed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (facts_dir / f"{name}.metadata.json").write_text(
            json.dumps(metadata_by_name[name], indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        target_public = public_dir / name
        target_public.mkdir()
        for record in public[name]:
            command_id = record["command_id"]
            (target_public / f"{command_id}.stdout").write_bytes(record["stdout"])
            (target_public / f"{command_id}.stderr").write_bytes(record["stderr"])
            retained = {key: value for key, value in record.items() if key not in {"stdout", "stderr"}}
            (target_public / f"{command_id}.json").write_text(
                json.dumps(retained, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
    (result_dir / "facts.tsv").write_text(render_tsv(rows), encoding="utf-8")
    manifest = {
        "format": "x64lens-sprint12-role-property-heldout-v2",
        "authority_id": authority["authority_id"],
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "object_count": len(objects),
        "natural_count": sum(row["stratum"] == "natural" for row in rows),
        "metamorphic_count": sum(row["stratum"] == "metamorphic" for row in rows),
        "probe_repeats": 3,
        "probe_run_count": len(objects) * 3,
        "public_command_count": sum(len(value) for value in public.values()),
        "fact_fields": list(FACT_FIELDS),
        "expected_vectors_retained": True,
        "observed_vectors_retained": True,
        "provisional_corpus_id": provisional_manifest["corpus_id"],
        "provisional_target_count": provisional_manifest["target_count"],
        "identities": identities,
        "rows_sha256": sha256_bytes((result_dir / "facts.tsv").read_bytes()),
    }
    (result_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files = sorted(path for path in result_dir.rglob("*") if path.is_file())
    checksum_lines = [f"{sha256_bytes(path.read_bytes())}  {path.relative_to(result_dir).as_posix()}" for path in files]
    (result_dir / "SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    for path in sorted(result_dir.rglob("*"), reverse=True):
        if path.is_dir():
            path.chmod(0o555)
        else:
            path.chmod(0o444)
    result_dir.chmod(0o555)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority", type=Path, required=True)
    parser.add_argument("--analyzer", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--provisional-corpus", type=Path, required=True)
    parser.add_argument("--fact-probe", type=Path, required=True)
    parser.add_argument("--result-dir", type=Path)
    args = parser.parse_args()

    authority, authority_identity = load_authority(args.authority)
    analyzer_identity = identity(args.analyzer, "analyzer", executable=True)
    schema_identity = identity(args.schema, "public JSON schema")
    probe_identity = identity(args.fact_probe, "private fact probe", executable=True)
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    require(isinstance(schema, dict) and schema.get("$schema") is not None,
            "public JSON schema authority is malformed")
    provisional_manifest, provisional_hashes, provisional_identity = verify_provisional_corpus(
        args.provisional_corpus
    )

    with tempfile.TemporaryDirectory(prefix="x64lens-role-property-heldout-") as raw:
        root = Path(raw)
        natural_root = root / "natural"
        natural_root.mkdir()
        objects = natural_objects(natural_root)
        metamorphic_root = root / "metamorphic"
        metamorphic_root.mkdir()
        objects += metamorphic_objects(metamorphic_root)
        require(len(objects) == 96, f"held-out object count is {len(objects)}, expected 96")
        validate_edge_diversity(objects)

        hashes = [sha256_bytes(blob) for _name, blob, _metadata in objects]
        require(len(set(hashes)) == 96, "held-out object identities are not unique")
        natural_hashes = set(hashes[:48])
        overlap = natural_hashes & provisional_hashes
        require(not overlap, "natural held-out objects overlap the provisional corpus")

        rows: list[dict[str, Any]] = []
        public: dict[str, list[dict[str, Any]]] = {}
        executions = root / "executions"
        executions.mkdir()
        for name, blob, metadata in objects:
            target = executions / name
            target.write_bytes(blob)
            expected = independent_vector(blob)
            repeats = [probe_fact(args.fact_probe, target) for _ in range(3)]
            require(repeats[0][0] == repeats[1][0] == repeats[2][0], f"nondeterministic probe bytes: {name}")
            observed = repeats[0][1]
            require(observed == expected,
                    f"private fact mismatch for {name}:\nexpected={expected}\nobserved={observed}")
            command_records = public_commands(args.analyzer, target, expected, schema)
            public[name] = command_records
            row: dict[str, Any] = {
                "name": name,
                "stratum": metadata["stratum"],
                "family": metadata.get("family", "natural"),
                "sha256": sha256_bytes(blob),
                "size_bytes": len(blob),
                "parser_visible_sha256": parser_visible_digest(blob),
                "repeat_sha256": sha256_bytes(repeats[0][0]),
                "public_command_count": len(command_records),
            }
            row.update({f"expected_{field}": expected[field] for field in FACT_FIELDS})
            row.update({f"observed_{field}": observed[field] for field in FACT_FIELDS})
            rows.append(row)

        natural = [row for row in rows if row["stratum"] == "natural"]
        metamorphic = [row for row in rows if row["stratum"] == "metamorphic"]
        require(len(natural) == 48 and len(metamorphic) == 48, "held-out strata are incomplete")
        malformed = sum(row["observed_status"] == EXIT_MALFORMED for row in rows)
        require(malformed == 12, f"malformed held-out count is {malformed}, expected 12")
        require(sum(row["public_command_count"] for row in rows) == 384,
                "held-out public-command accounting changed")
        if args.result_dir is not None:
            identities = {
                "authority": authority_identity,
                "analyzer": analyzer_identity,
                "schema": schema_identity,
                "fact_probe": probe_identity,
                "provisional_corpus_manifest": provisional_identity,
            }
            write_result(args.result_dir, objects, rows, public, identities, authority, provisional_manifest)

    print(
        "sprint12-role-property-heldout-smoke: ok "
        "objects=96 natural=48 metamorphic=48 probe_runs=288 public_commands=384 "
        "fact_fields=18 expected_vectors=96 observed_vectors=96 unique_natural=48 "
        "provisional_targets=24 provisional_overlap=0 edge_layouts=24 malformed=12 schema=0.2.0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, HeldoutError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"sprint12-role-property-heldout-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
