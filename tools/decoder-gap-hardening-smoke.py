#!/usr/bin/env python3
"""Regression probes for decoder-gap parser, snapshots, and publication safety."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
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

    prefix_rows = [
        ("40", "rex ret"), ("41", "rex.B ret"), ("42", "rex.X ret"),
        ("43", "rex.XB ret"), ("44", "rex.R ret"), ("45", "rex.RB ret"),
        ("46", "rex.RX ret"), ("47", "rex.RXB ret"), ("48", "rex.W ret"),
        ("49", "rex.WB ret"), ("4a", "rex.WX ret"), ("4b", "rex.WXB ret"),
        ("4c", "rex.WR ret"), ("4d", "rex.WRB ret"), ("4e", "rex.WRX ret"),
        ("4f", "rex.WRXB ret"), ("2e", "cs ret"), ("3e", "ds ret"),
        ("26", "es ret"), ("36", "ss ret"), ("64", "fs ret"),
        ("65", "gs ret"), ("66", "retw"), ("67", "addr32 ret"),
        ("f0", "lock ret"), ("f2", "bnd ret"), ("f3", "repz ret"),
    ]
    rendered = ["Disassembly of section .text:", ""]
    for index, (prefix, decoded) in enumerate(prefix_rows):
        rendered.append(f"  {0x402000 + index * 2:x}: {prefix} c3\t{decoded}")
    rendered.extend(
        [
            "  402036: 2e eb 00\tcs jmp 402039 <barrier+0x3>",
            "  402039: c3\tret",
            "  40203a: 41 ff e0\tjmp r8",
            "  40203d: c3\tret",
            "  40203e: 66 66 66 66\tdata16 data16 data16 data16",
        ]
    )
    prefix_instructions, prefix_diagnostics = MODULE.parse_objdump_with_diagnostics("\n".join(rendered))
    expected_prefix_returns = [0x402000 + index * 2 for index in range(len(prefix_rows))]
    observed_prefix_returns = [item.address for item in prefix_instructions if MODULE.is_return(item)]
    if observed_prefix_returns != expected_prefix_returns + [0x402039, 0x40203D]:
        raise RuntimeError(
            f"full prefix/return normalization failed: {observed_prefix_returns!r}"
        )
    if len(prefix_diagnostics) != 1 or "prefix-only" not in prefix_diagnostics[0].reason:
        raise RuntimeError(f"prefix-only row was not retained as a diagnostic: {prefix_diagnostics!r}")
    segment_jump = next(item for item in prefix_instructions if item.address == 0x402036)
    if segment_jump.mnemonic != "jmp" or not MODULE.is_predecessor_barrier(segment_jump):
        raise RuntimeError("segment-prefixed jump was not normalized into a predecessor barrier")
    prefix_sequences = MODULE.build_canonical_sequences(prefix_instructions, 8)
    if any(item.terminator == 0x402039 and item.start < 0x402039 for item in prefix_sequences):
        raise RuntimeError("canonical sequence crossed a segment-prefixed jump")
    if any(item.terminator == 0x40203D and item.start < 0x40203D for item in prefix_sequences):
        raise RuntimeError("canonical sequence crossed a REX-prefixed indirect jump")


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


def test_post_rename_signal_window(root: Path) -> None:
    """Exercise the exact syscall/next-bytecode window found during review."""

    for signum in (signal.SIGINT, signal.SIGTERM):
        case_root = root / f"rename-window-{signal.Signals(signum).name.lower()}"
        case_root.mkdir()
        results = case_root / "results"
        staging = case_root / "staging"
        write_campaign(results, "old", "x64lens-decoder-gap-manifest-v2")
        write_campaign(staging, "new", "x64lens-decoder-gap-manifest-v2")

        path_type = type(results)
        original_replace = path_type.replace
        injected = False

        def replace_then_interrupt(self: Path, target: Path) -> Path:
            nonlocal injected
            replaced = original_replace(self, target)
            if self == results and Path(target).name.startswith(".decoder-gap-backup-"):
                injected = True
                raise MODULE.CampaignInterrupted(signum)
            return replaced

        path_type.replace = replace_then_interrupt
        try:
            try:
                MODULE.publish_results(staging, results)
            except MODULE.CampaignInterrupted as exc:
                if exc.signum != signum:
                    raise RuntimeError("rename-window probe observed the wrong signal") from exc
            else:
                raise RuntimeError("rename-window probe did not interrupt publication")
        finally:
            path_type.replace = original_replace

        if not injected:
            raise RuntimeError("rename-window probe did not execute after the prior-tree rename")
        manifest = json.loads((results / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("marker") != "old":
            raise RuntimeError("post-rename interruption did not restore the prior campaign")
        if list(case_root.glob(".decoder-gap-backup-*")):
            raise RuntimeError("post-rename interruption left backup residue")


def pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_measured_child_signal_cleanup(root: Path) -> None:
    helper = root / "measured-child.py"
    helper.write_text(
        """#!/usr/bin/env python3
import os
import pathlib
import sys
import time
pathlib.Path(sys.argv[1]).write_text(f\"pid={os.getpid()} pgid={os.getpgrp()}\\n\")
time.sleep(60)
""",
        encoding="utf-8",
    )

    for signum in (signal.SIGINT, signal.SIGTERM):
        case_root = root / f"measurement-{signal.Signals(signum).name.lower()}"
        case_root.mkdir()
        marker = case_root / "marker.txt"
        stdout = case_root / "stdout.bin"
        stderr = case_root / "stderr.bin"
        previous = signal.getsignal(signum)

        def handler(observed: int, _frame: object) -> None:
            raise MODULE.CampaignInterrupted(observed)

        def sender() -> None:
            deadline = time.monotonic() + 10.0
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            if marker.exists():
                os.kill(os.getpid(), signum)

        signal.signal(signum, handler)
        thread = threading.Thread(target=sender, daemon=True)
        thread.start()
        try:
            try:
                MODULE.run_measured(
                    [sys.executable, str(helper), str(marker)],
                    stdout,
                    stderr,
                    30.0,
                    case_root,
                )
            except MODULE.CampaignInterrupted as exc:
                if exc.signum != signum:
                    raise RuntimeError("measured-child probe observed the wrong signal") from exc
            else:
                raise RuntimeError("measured-child probe did not interrupt the measurement")
        finally:
            signal.signal(signum, previous)
            thread.join(timeout=2.0)

        if not marker.exists():
            raise RuntimeError("measured child did not publish its PID marker")
        fields = dict(item.split("=", 1) for item in marker.read_text(encoding="utf-8").split())
        child_pid = int(fields["pid"])
        deadline = time.monotonic() + 2.0
        while pid_exists(child_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        if pid_exists(child_pid):
            try:
                os.killpg(int(fields["pgid"]), signal.SIGKILL)
            except ProcessLookupError:
                pass
            raise RuntimeError(f"measured child group survived {signal.Signals(signum).name}")


def main() -> int:
    test_parser()
    with tempfile.TemporaryDirectory(prefix="x64lens-decoder-gap-hardening-") as temp:
        root = Path(temp)
        test_snapshots(root)
        publication_root = root / "publication"
        publication_root.mkdir()
        test_publication(publication_root)
        test_post_rename_signal_window(publication_root)
        measurement_root = root / "measurement"
        measurement_root.mkdir()
        test_measured_child_signal_cleanup(measurement_root)
    print(
        "decoder-gap-hardening-smoke: ok "
        "parser=2 snapshots=2 publication_interruptions=10 measured_signal_cleanup=2"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"decoder-gap-hardening-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
