#!/usr/bin/env python3
"""Regression probes for decoder-gap parser, snapshots, and publication safety."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import signal
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "decoder-gap-smoke.py"
spec = importlib.util.spec_from_file_location("x64lens_decoder_gap", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load decoder-gap module: {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = MODULE
spec.loader.exec_module(MODULE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_campaign(path: Path, marker: str, format_name: str) -> None:
    path.mkdir(parents=True)
    (path / "manifest.json").write_text(
        json.dumps({"format": format_name, "marker": marker}) + "\n", encoding="utf-8"
    )
    (path / f"{marker}-sentinel").write_text(marker + "\n", encoding="utf-8")


def test_parser() -> None:
    text = """\
Disassembly of section .text:
  0000000000401000: f3 c3                   repz ret
  0000000000401002: f2 c3                   bnd ret
  0000000000401004: C3                      RET
  0000000000401005: 62                      .byte 0x62
  0000000000401006: c3                      ret
  0000000000401007: 3e ff e0                notrack jmp rax
  000000000040100a: c3                      ret
  000000000040100b: cb                      retf
  000000000040100c: c3                      ret
  000000000040100d: c7 f8 00 00 00 00       xbegin 401013 <target>
  0000000000401013: c3                      ret
0000000000401014 <symbol_named_ret>:
  0000000000401014: 90                      nop
  0000000000401015: c3                      ret
  0000000000401020: 90                      nop
  0000000000401021: c3                      ret
"""
    instructions, diagnostics = MODULE.parse_objdump_with_diagnostics(text)
    returns = [item.address for item in instructions if MODULE.is_return(item)]
    expected_returns = [0x401000, 0x401002, 0x401004, 0x401006, 0x40100A, 0x40100C, 0x401013, 0x401015, 0x401021]
    if returns != expected_returns:
        raise RuntimeError(f"prefixed return normalization failed: {returns!r}")
    if diagnostics:
        raise RuntimeError(f"unexpected parser diagnostics: {diagnostics!r}")

    sequences = MODULE.build_canonical_sequences(instructions, 8)
    starts_by_terminator: dict[int, set[int]] = {}
    for sequence in sequences:
        starts_by_terminator.setdefault(sequence.terminator, set()).add(sequence.start)
    barrier_expectations = {
        0x401006: 0x401006,
        0x40100A: 0x40100A,
        0x40100C: 0x40100C,
        0x401013: 0x401013,
    }
    for terminator, earliest_allowed in barrier_expectations.items():
        starts = starts_by_terminator.get(terminator, set())
        if not starts or min(starts) < earliest_allowed:
            raise RuntimeError(
                f"canonical sequence crossed a parser barrier at 0x{terminator:x}: {sorted(starts)!r}"
            )
    if 0x401014 not in starts_by_terminator.get(0x401015, set()):
        raise RuntimeError("ordinary contiguous instruction was not retained before ret")
    if 0x401020 not in starts_by_terminator.get(0x401021, set()):
        raise RuntimeError("address-gap run did not restart correctly")

    malformed = "Disassembly of section .text:\n  401100: 90 90\n"
    _, malformed_diagnostics = MODULE.parse_objdump_with_diagnostics(malformed)
    if len(malformed_diagnostics) != 1 or "lacks a mnemonic" not in malformed_diagnostics[0].reason:
        raise RuntimeError("malformed objdump row did not produce a retained diagnostic")


def test_snapshots(root: Path) -> None:
    source_one = root / "one.bin"
    source_two = root / "two.bin"
    source_one.write_bytes(b"first-target\n")
    source_two.write_bytes(b"second-target-before\n")
    snapshots_dir = root / "snapshots"
    snapshots = [
        MODULE.snapshot_target(source_one, snapshots_dir, 0),
        MODULE.snapshot_target(source_two, snapshots_dir, 1),
    ]
    original_second = snapshots[1].sha256
    source_two.write_bytes(b"second-target-after\n")
    if digest(snapshots[1].snapshot_path) != original_second:
        raise RuntimeError("immutable snapshot changed after source mutation")
    if digest(source_two) == original_second:
        raise RuntimeError("source mutation probe did not change the source identity")
    if snapshots[0].snapshot_path.stat().st_mode & 0o222:
        raise RuntimeError("snapshot remains writable")


def test_publication(root: Path) -> None:
    for signum in (signal.SIGINT, signal.SIGTERM):
        for stage in ("before_backup", "after_backup", "before_publish", "after_publish"):
            case_root = root / f"signal-{signum}-{stage}"
            case_root.mkdir()
            results = case_root / "results"
            staging = case_root / "staging"
            write_campaign(results, "old", "x64lens-decoder-gap-manifest-v1")
            write_campaign(staging, "new", "x64lens-decoder-gap-manifest-v2")

            def hook(observed: str, *, expected: str = stage, signal_number: int = signum) -> None:
                if observed == expected:
                    raise MODULE.CampaignInterrupted(signal_number)

            try:
                MODULE.publish_results(staging, results, hook=hook)
            except MODULE.CampaignInterrupted as exc:
                if exc.signum != signum:
                    raise RuntimeError("publication hook returned the wrong signal") from exc
            else:
                raise RuntimeError(f"publication interruption did not fire at {stage}")

            if not results.is_dir() or not (results / "manifest.json").is_file():
                raise RuntimeError(f"publication interruption removed all valid results at {stage}")
            manifest = json.loads((results / "manifest.json").read_text(encoding="utf-8"))
            expected_marker = "new" if stage == "after_publish" else "old"
            if manifest.get("marker") != expected_marker:
                raise RuntimeError(
                    f"publication interruption retained {manifest.get('marker')!r}, expected {expected_marker!r}"
                )
            backup_dirs = list(case_root.glob(".decoder-gap-backup-*"))
            if backup_dirs:
                raise RuntimeError(f"publication left backup residue at {stage}: {backup_dirs!r}")

    normal_root = root / "normal"
    normal_root.mkdir()
    results = normal_root / "results"
    staging = normal_root / "staging"
    write_campaign(results, "old", "x64lens-decoder-gap-manifest-v1")
    write_campaign(staging, "new", "x64lens-decoder-gap-manifest-v2")
    MODULE.publish_results(staging, results)
    manifest = json.loads((results / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("marker") != "new" or list(normal_root.glob(".decoder-gap-backup-*")):
        raise RuntimeError("normal transactional replacement did not commit cleanly")

    unrelated = root / "unrelated"
    unrelated.mkdir()
    (unrelated / "sentinel").write_text("preserve\n", encoding="utf-8")
    try:
        MODULE.validate_results_destination(unrelated)
    except RuntimeError:
        pass
    else:
        raise RuntimeError("unrecognized results directory was accepted")
    if (unrelated / "sentinel").read_text(encoding="utf-8") != "preserve\n":
        raise RuntimeError("unrelated results directory was modified")


def main() -> int:
    test_parser()
    with tempfile.TemporaryDirectory(prefix="x64lens-decoder-gap-hardening-") as temp:
        root = Path(temp)
        test_snapshots(root)
        publication_root = root / "publication"
        publication_root.mkdir()
        test_publication(publication_root)
    print("decoder-gap-hardening-smoke: ok parser=1 snapshots=2 publication_interruptions=8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"decoder-gap-hardening-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
