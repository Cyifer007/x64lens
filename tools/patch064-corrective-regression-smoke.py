#!/usr/bin/env python3
"""Regress confirmed Patch 064 parser, corpus, and permission defects.

This gate is intentionally independent of NASM. Assembly behavior remains owned
by the focused native oracles, while this script proves that the rejected source
forms are absent and that corpus mode repair authenticates all non-mode facts
before mutation without following a substituted hard link.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "benchmarks/corpus/generated/s11-p056-provisional-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_corpus() -> Any:
    path = ROOT / "benchmarks/scripts/build-provisional-corpus.py"
    spec = importlib.util.spec_from_file_location("p065_corpus", path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def copy_corpus(parent: Path) -> Path:
    require(CORPUS.is_dir(), f"authenticated source corpus is missing: {CORPUS}")
    parent.mkdir(parents=True, exist_ok=True)
    destination = parent / CORPUS.name
    shutil.copytree(CORPUS, destination, copy_function=shutil.copy2)
    # The authenticated source corpus is intentionally retained read-only. This
    # private test copy must make only the two files it deliberately rewrites
    # owner-writable; otherwise the oracle fails on permissions before it can
    # exercise semantic and checksum rejection.
    for relative in ("corpus-manifest.json", "SHA256SUMS.txt"):
        path = destination / relative
        os.chmod(path, stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR)
    return destination


def replace_checksum(manifest: Path, relative: str, digest: str) -> None:
    lines = manifest.read_text(encoding="utf-8").splitlines()
    replaced = False
    output: list[str] = []
    for line in lines:
        if line.endswith("  " + relative):
            output.append(f"{digest}  {relative}")
            replaced = True
        else:
            output.append(line)
    require(replaced, f"checksum entry not found: {relative}")
    manifest.write_text("\n".join(output) + "\n", encoding="utf-8")
    os.utime(manifest, ns=(0, 0), follow_symlinks=False)


def probe_assembly_corrections() -> None:
    phdr = (ROOT / "src/phdr.asm").read_text(encoding="utf-8")
    role = (ROOT / "src/binary_role.asm").read_text(encoding="utf-8")
    property_source = (ROOT / "src/gnu_property.asm").read_text(encoding="utf-8")
    structs = (ROOT / "include/structs.inc").read_text(encoding="utf-8")
    harness = (ROOT / "tests/internal/binary-role-reconciliation.asm").read_text(encoding="utf-8")

    require(not re.search(r"\[\s*r15\s*\+\s*rcx\s*\+\s*r8\s*\]", phdr),
            "unencodable three-register PHDR address remains")
    require(not re.search(r"mov\s+qword\s+\[[^\]]+\]\s*,\s*0x[0-9a-fA-F]{9,}", harness),
            "qword immediate-to-memory overflow form remains in role harness")
    require(not re.search(r"\[[^\]]+\+\s*E_(?:TYPE|ENTRY)\]", role),
            "binary-role classifier still rereads mapped ELF header bytes")
    require("cmp     byte [rdx], 0" in phdr and ".interp_interior_loop:" in phdr,
            "PT_INTERP empty/interior-NUL validation is missing")
    require(".dynamic_string_second_pass:" in phdr and ".dynamic_string_soname_terminator:" in phdr,
            "generalized dynamic-string second-pass SONAME validation is missing")
    summary_match = re.search(r"%define\s+PHDR_SUMMARY_RECORD_SIZE\s+(\d+)", structs)
    context_match = re.search(r"%define\s+GNU_PROPERTY_CONTEXT_SIZE\s+\([^\n]+\)", structs)
    require(summary_match is not None and int(summary_match.group(1)) - 200 <= 64,
            "Patch 065 phdr_summary exceeds the accepted 64-byte growth ceiling")
    require(context_match is not None and "GNU_PROPERTY_CTX_NOTES" in context_match.group(0),
            "GNU property context is not derived from bounded record arrays")
    require("cmp     dword [rsp + 104], GNU_PROPERTY_X86_FEATURE_1_AND" in property_source,
            "GNU property type scratch is not compared at its nonoverlapping dword width")
    require("mov     rsi, [rsp + 0]" in property_source and
            "mov     rdx, [rsp + 8]" in property_source,
            "GNU property parser does not revalidate the canonical carrier offset and size")
    require("cmp     qword [rsp + 104], GNU_PROPERTY_X86_FEATURE_1_AND" not in property_source,
            "GNU property type comparison overlaps the adjacent data-size scratch")


def probe_semantic_and_timestamp_preflight(corpus: Any, root: Path) -> None:
    semantic = copy_corpus(root / "semantic")
    drift = semantic / "commands.tsv"
    os.chmod(drift, 0o600)
    before_mode = stat.S_IMODE(drift.stat().st_mode)
    manifest_path = semantic / "corpus-manifest.json"
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    value["publication_eligible"] = True
    manifest_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.utime(manifest_path, ns=(0, 0), follow_symlinks=False)
    replace_checksum(semantic / "SHA256SUMS.txt", "corpus-manifest.json", corpus.sha256_file(manifest_path))
    try:
        corpus.repair_corpus_modes(semantic)
    except corpus.CorpusError:
        pass
    else:
        raise RuntimeError("semantic corpus drift was accepted by mode repair")
    require(stat.S_IMODE(drift.stat().st_mode) == before_mode,
            "mode repair mutated files before semantic verification completed")

    timestamp = copy_corpus(root / "timestamp")
    drift = timestamp / "commands.tsv"
    os.chmod(drift, 0o600)
    os.utime(drift, ns=(1, 1), follow_symlinks=False)
    before_mode = stat.S_IMODE(drift.stat().st_mode)
    try:
        corpus.repair_corpus_modes(timestamp)
    except corpus.CorpusError:
        pass
    else:
        raise RuntimeError("timestamp corpus drift was accepted by mode repair")
    require(stat.S_IMODE(drift.stat().st_mode) == before_mode,
            "mode repair mutated files before timestamp verification completed")


def probe_hardlink_substitution(corpus: Any, root: Path) -> None:
    candidate = copy_corpus(root / "hardlink")
    relative = PurePosixPath("commands.tsv")
    victim = candidate / relative
    os.chmod(victim, 0o600)
    external = root / "external-victim"
    external.write_bytes(b"foreign inode\n")
    os.chmod(external, 0o600)
    os.utime(external, ns=(0, 0), follow_symlinks=False)

    original = corpus.open_relative_member_nofollow
    fired = False

    def substitute(root_fd: int, member: PurePosixPath, *, directory: bool) -> int:
        nonlocal fired
        if not fired and member == relative and not directory:
            fired = True
            bound_root = Path(f"/proc/self/fd/{root_fd}")
            os.unlink(bound_root / member)
            os.link(external, bound_root / member)
        return original(root_fd, member, directory=directory)

    corpus.open_relative_member_nofollow = substitute
    try:
        try:
            corpus.repair_corpus_modes(candidate)
        except corpus.CorpusError:
            pass
        else:
            raise RuntimeError("hard-link substitution was accepted by mode repair")
    finally:
        corpus.open_relative_member_nofollow = original
    require(fired, "hard-link substitution probe did not fire")
    require(stat.S_IMODE(external.stat().st_mode) == 0o600,
            "mode repair chmod followed a substituted foreign hard link")


def probe_normalize_perms_nofollow(root: Path) -> None:
    work = root / "perms"
    for rel in (
        ".local", ".codex", ".agents", "build", "tests/bin",
        "benchmarks/corpus/generated", "benchmarks/results", "tests/results",
        "tools", "benchmarks/scripts", "tests",
    ):
        (work / rel).mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "tools/normalize-tracked-permissions.py",
                 work / "tools/normalize-tracked-permissions.py")
    (work / "tests/run-tests.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (work / "benchmarks/scripts/diagnostic_artifact.py").write_text("# helper\n", encoding="utf-8")
    os.chmod(work / "tests/run-tests.sh", 0o600)
    os.chmod(work / "benchmarks/scripts/diagnostic_artifact.py", 0o600)
    victims = [
        work / "benchmarks/results/victim.py",
        work / "tests/results/victim.py",
        work / "benchmarks/corpus/generated/victim.sh",
    ]
    for victim in victims:
        victim.write_text("victim\n", encoding="utf-8")
        os.chmod(victim, 0o600)
    os.symlink(victims[0], work / "tools/redirect.py")
    os.symlink(victims[1], work / "benchmarks/scripts/redirect.py")
    os.symlink(victims[2], work / "tools/redirect.sh")

    subprocess.run(["git", "init", "-q"], cwd=work, check=True)
    subprocess.run(
        ["git", "add", "tools/normalize-tracked-permissions.py", "tests/run-tests.sh",
         "benchmarks/scripts/diagnostic_artifact.py", "tools/redirect.py",
         "benchmarks/scripts/redirect.py", "tools/redirect.sh"],
        cwd=work, check=True,
    )
    subprocess.run(["git", "update-index", "--chmod=+x", "tests/run-tests.sh"],
                   cwd=work, check=True)
    cp = subprocess.run(
        ["make", "-f", str(ROOT / "Makefile"), "normalize-perms"],
        cwd=work, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    require(cp.returncode == 0, f"normalize-perms probe failed:\n{cp.stdout}\n{cp.stderr}")
    require(all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in victims),
            "normalize-perms followed a tracked symlink or touched an untracked output")
    require(stat.S_IMODE((work / "tests/run-tests.sh").stat().st_mode) == 0o755,
            "normalize-perms did not restore the tracked executable mode")
    require(stat.S_IMODE((work / "benchmarks/scripts/diagnostic_artifact.py").stat().st_mode) == 0o644,
            "normalize-perms did not restore the tracked regular-file mode")


def main() -> int:
    probe_assembly_corrections()
    corpus = load_corpus()
    with tempfile.TemporaryDirectory(prefix="x64lens-p065-corrective-") as raw:
        root = Path(raw)
        probe_semantic_and_timestamp_preflight(corpus, root)
        probe_hardlink_substitution(corpus, root)
        probe_normalize_perms_nofollow(root)
    print(
        "patch064-corrective-regression-smoke: ok "
        "assembly=2 interp=2 soname=2 module_boundary=1 property_layout=5 "
        "corpus_preflight=2 corpus_hardlink=1 normalize_nofollow=3"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"patch064-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
