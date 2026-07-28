#!/usr/bin/env python3
"""Run the 28-object private role/GNU-property metamorphic preflight.

The preflight crosses three bounded binary-role constructions with four x86
feature states. Each logical vector has a canonical PT_NOTE encoding and an
exact dual PT_NOTE/PT_GNU_PROPERTY encoding. Four single-axis mutants cover
unknown bits, conflicting feature evidence, property ordering, and role
contradiction. This is development evidence; it does not change public schema or
claim runtime CET enforcement.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from typing import Any

EXIT_MALFORMED = 5
ET_EXEC = 2
ET_DYN = 3
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
PT_NOTE = 4
PT_GNU_PROPERTY = 0x6474E553
PF_X = 1
PF_W = 2
PF_R = 4
DT_NULL = 0
DT_STRTAB = 5
DT_STRSZ = 10
DT_SONAME = 14
IBT = 1
SHSTK = 2

ROLE_EXECUTABLE = 1
ROLE_SHARED = 2
ROLE_CONTRADICTORY = 4
PROPERTY_ABSENT = 1
PROPERTY_PRESENT = 2
PROPERTY_CONTRADICTORY = 3

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


PRIVATE_PUBLIC_KEYS = {
    "binary_role",
    "role_state",
    "role_evidence",
    "ibt",
    "ibt_state",
    "shstk",
    "shstk_state",
    "gnu_property",
    "gnu_properties",
}


def private_public_key(key: str) -> bool:
    normalized = key.lower()
    return (
        normalized in PRIVATE_PUBLIC_KEYS
        or normalized.startswith("property_")
        or normalized.startswith("gnu_property")
        or normalized.startswith("ibt_")
        or normalized.startswith("shstk_")
    )


def assert_no_private_public_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            require(isinstance(key, str), "public JSON contains a non-string object key")
            require(not private_public_key(key),
                    f"private role/property fact leaked into public JSON: {key}")
            assert_no_private_public_fields(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_private_public_fields(child)


def load_property_helpers() -> Any:
    path = ROOT / "tools/sprint12-gnu-property-smoke.py"
    spec = importlib.util.spec_from_file_location("p066_property_helpers", path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def phdr(ptype: int, flags: int, offset: int, vaddr: int,
         filesz: int, memsz: int, align: int) -> tuple[int, ...]:
    return (ptype, flags, offset, vaddr, 0, filesz, memsz, align)


def build_object(role: str, property_bytes: bytes, *, dual: bool = False) -> bytes:
    image = bytearray(0x700)
    image[0:4] = b"\x7fELF"
    image[4] = 2
    image[5] = 1
    image[6] = 1

    headers: list[tuple[int, ...]] = []
    headers.append(phdr(PT_LOAD, PF_R | PF_X, 0x200, 0x400200, 1, 1, 1))
    image[0x200] = 0xC3

    etype = ET_EXEC
    entry = 0x400200
    if role in {"pie", "contradictory"}:
        etype = ET_DYN
        interp = b"/lib/ld.so\0"
        image[0x280:0x280 + len(interp)] = interp
        headers.append(phdr(PT_INTERP, PF_R, 0x280, 0, len(interp), len(interp), 1))
    if role in {"shared", "contradictory"}:
        etype = ET_DYN
        if role == "shared":
            entry = 0
        data_off = 0x400
        data_vaddr = 0x500400
        strtab_off = 0x480
        strtab = b"\0libheld.so\0"
        image[strtab_off:strtab_off + len(strtab)] = strtab
        dynamic = [
            (DT_STRTAB, data_vaddr + (strtab_off - data_off)),
            (DT_STRSZ, len(strtab)),
            (DT_SONAME, 1),
            (DT_NULL, 0),
        ]
        cursor = data_off
        for tag, value in dynamic:
            struct.pack_into("<qQ", image, cursor, tag, value)
            cursor += 16
        headers.append(phdr(PT_LOAD, PF_R | PF_W, data_off, data_vaddr, 0x100, 0x100, 1))
        headers.append(phdr(PT_DYNAMIC, PF_R | PF_W, data_off, data_vaddr,
                            len(dynamic) * 16, len(dynamic) * 16, 8))

    prop_off = 0x300
    image[prop_off:prop_off + len(property_bytes)] = property_bytes
    headers.append(phdr(PT_NOTE, PF_R, prop_off, 0, len(property_bytes), len(property_bytes), 8))
    if dual:
        headers.append(phdr(PT_GNU_PROPERTY, PF_R, prop_off, 0,
                            len(property_bytes), len(property_bytes), 8))

    phoff = 64
    require(phoff + len(headers) * 56 <= 0x200, "program headers overlap executable bytes")
    struct.pack_into(
        "<HHIQQQIHHHHHH", image, 16,
        etype, 62, 1, entry, phoff, 0, 0, 64, 56, len(headers), 0, 0, 0,
    )
    for index, record in enumerate(headers):
        struct.pack_into("<IIQQQQQQ", image, phoff + index * 56, *record)
    return bytes(image)


def run(command: list[str], *, expected: int = 0) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        check=False, timeout=5.0)
    require(cp.returncode == expected,
            f"command returned {cp.returncode}, expected {expected}: {command!r}\n"
            f"stdout={cp.stdout[:300]!r}\nstderr={cp.stderr[:500]!r}")
    return cp


def fact(probe: Path, target: Path) -> dict[str, int]:
    cp = run([str(probe), str(target)])
    value = json.loads(cp.stdout)
    require(isinstance(value, dict) and all(isinstance(v, int) for v in value.values()),
            "fact probe emitted an invalid JSON record")
    return value


PRIVATE_TEXT_MARKERS = (
    b"role_state",
    b"role_evidence",
    b"ibt_state",
    b"shstk_state",
    b"property_view_count",
    b"property_contributor_count",
    b"property_feature_count",
    b"property_unknown_count",
    b"property_conflict_count",
    b"gnu_property_private",
    b"binary role state",
    b"private gnu property",
)


def assert_no_private_public_text(payload: bytes) -> None:
    lowered = payload.lower()
    for marker in PRIVATE_TEXT_MARKERS:
        require(marker not in lowered, f"private role/property fact leaked into public text: {marker!r}")


def validate_public(analyzer: Path, target: Path) -> int:
    commands = [
        [str(analyzer), "info", str(target)],
        [str(analyzer), "mitigations", str(target)],
        [str(analyzer), "gadgets", "--format", "json", "--max-depth", "4", str(target)],
        [str(analyzer), "analyze", "--format", "json", "--max-depth", "4", str(target)],
    ]
    count = 0
    for command in commands:
        cp = run(command)
        require(cp.stdout, f"public command emitted empty output: {command!r}")
        assert_no_private_public_text(cp.stdout)
        if "--format" in command:
            report = json.loads(cp.stdout)
            require(report.get("schema_version") == "0.2.0", "metamorphic report changed schema")
            require(report.get("command") == command[1], "metamorphic report changed command identity")
            assert_no_private_public_fields(report)
        count += 1
    return count


def expected_property(value: int) -> tuple[int, int]:
    return (
        PROPERTY_PRESENT if value & IBT else PROPERTY_ABSENT,
        PROPERTY_PRESENT if value & SHSTK else PROPERTY_ABSENT,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyzer", type=Path, required=True)
    parser.add_argument("--fact-probe", type=Path, required=True)
    args = parser.parse_args()
    helpers = load_property_helpers()

    roles = {"exec": ROLE_EXECUTABLE, "pie": ROLE_EXECUTABLE, "shared": ROLE_SHARED}
    states = {"absent": 0, "ibt": IBT, "shstk": SHSTK, "both": IBT | SHSTK}
    objects = 0
    pairs = 0
    public_commands = 0

    with tempfile.TemporaryDirectory(prefix="x64lens-role-property-") as raw:
        root = Path(raw)
        for role, expected_role in roles.items():
            for state_name, bits in states.items():
                note = helpers.property_note([bits])
                pair_facts: list[dict[str, int]] = []
                for encoding, dual in (("canonical", False), ("dual", True)):
                    target = root / f"{role}-{state_name}-{encoding}.elf"
                    target.write_bytes(build_object(role, note, dual=dual))
                    first = fact(args.fact_probe, target)
                    second = fact(args.fact_probe, target)
                    require(first == second, f"nondeterministic private facts: {target.name}")
                    require(first["status"] == 0, f"valid metamorphic object failed: {target.name}: {first}")
                    require(first["role_state"] == expected_role, f"role mismatch: {target.name}: {first}")
                    expected_ibt, expected_shstk = expected_property(bits)
                    require((first["ibt_state"], first["shstk_state"]) == (expected_ibt, expected_shstk),
                            f"property state mismatch: {target.name}: {first}")
                    require(first["property_view_count"] == 1 and first["property_note_count"] == 1,
                            f"canonical private view mismatch: {target.name}: {first}")
                    require(first["property_contributor_count"] == (2 if dual else 1),
                            f"contributor delta mismatch: {target.name}: {first}")
                    require(first["property_feature_count"] == 1,
                            f"feature count mismatch: {target.name}: {first}")
                    public_commands += validate_public(args.analyzer, target)
                    pair_facts.append(first)
                    objects += 1
                left, right = pair_facts
                invariant = {
                    "role_state", "ibt_state", "shstk_state", "property_view_count",
                    "property_note_count", "property_feature_count", "property_feature_and",
                    "property_feature_or", "property_unknown_count", "property_conflict_count",
                }
                require(all(left[key] == right[key] for key in invariant),
                        f"logical state changed across exact-dual encoding: {role}/{state_name}")
                require(right["property_contributor_count"] == left["property_contributor_count"] + 1,
                        f"dual encoding did not add exactly one contributor: {role}/{state_name}")
                pairs += 1

        mutants: list[tuple[str, bytes, dict[str, int]]] = [
            ("unknown-bit", build_object("exec", helpers.property_note([IBT | 0x80])),
             {"status": 0, "role_state": ROLE_EXECUTABLE, "ibt_state": PROPERTY_PRESENT,
              "shstk_state": PROPERTY_ABSENT, "property_unknown_count": 1}),
            ("conflict", build_object("pie", helpers.property_note([IBT, 0])),
             {"status": 0, "role_state": ROLE_EXECUTABLE, "ibt_state": PROPERTY_CONTRADICTORY,
              "shstk_state": PROPERTY_ABSENT, "property_conflict_count": 1}),
            ("descending-order", build_object("shared", helpers.property_note([IBT], extra_type=1)),
             {"status": EXIT_MALFORMED}),
            ("role-contradiction", build_object("contradictory", helpers.property_note([IBT | SHSTK])),
             {"status": 0, "role_state": ROLE_CONTRADICTORY,
              "ibt_state": PROPERTY_PRESENT, "shstk_state": PROPERTY_PRESENT}),
        ]
        for name, blob, expected in mutants:
            target = root / f"mutant-{name}.elf"
            target.write_bytes(blob)
            first = fact(args.fact_probe, target)
            second = fact(args.fact_probe, target)
            require(first == second, f"nondeterministic mutant facts: {name}")
            for key, value in expected.items():
                require(first[key] == value, f"mutant {name} {key}={first[key]} expected={value}: {first}")
            if first["status"] == 0:
                public_commands += validate_public(args.analyzer, target)
            else:
                info = run([str(args.analyzer), "info", str(target)])
                require(info.stdout, f"info emitted empty output for structurally valid ELF header: {name}")
                assert_no_private_public_text(info.stdout)
                public_commands += 1
                for command in (
                    [str(args.analyzer), "mitigations", str(target)],
                    [str(args.analyzer), "gadgets", "--format", "json", str(target)],
                    [str(args.analyzer), "analyze", "--format", "json", str(target)],
                ):
                    cp = run(command, expected=EXIT_MALFORMED)
                    require(not cp.stdout, f"malformed mutant emitted public stdout: {name}")
                    public_commands += 1
            objects += 1

    require(objects == 28 and pairs == 12 and public_commands == 112,
            "metamorphic preflight accounting mismatch")
    print(
        "sprint12-role-property-metamorphic-smoke: ok "
        "objects=28 pairs=12 mutants=4 roles=3 property_states=4 "
        "deterministic=28 public_commands=112 schema=unchanged"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"sprint12-role-property-metamorphic-smoke: error: {exc}", file=__import__('sys').stderr)
        raise SystemExit(1)
