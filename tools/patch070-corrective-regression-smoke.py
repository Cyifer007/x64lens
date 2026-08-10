#!/usr/bin/env python3
"""Regress the Patch 070 findings corrected by Sprint 12 Patch 071.

The gate proves late member replacements are preserved, batch authority and
case outcomes fail closed, output caps are enforced while streaming, recursive
delivery manifests are exact, and tracked source custody excludes private or
host-specific state.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class RegressionError(RuntimeError):
    """Raised when a reproduced Patch 070 defect remains observable."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def load(name: str, relative: str) -> Any:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def cleanup_success_probe(module: Any, base: Path) -> None:
    owned = base / "owned-success"
    (owned / "nested").mkdir(parents=True)
    (owned / "value").write_bytes(b"value\n")
    (owned / "nested" / "child").write_bytes(b"child\n")
    (owned / "link").symlink_to("value")
    identity = module.parse_identity(module.identify(owned))
    module.remove(owned, identity)
    require(not owned.exists(), "ordinary authenticated cleanup failed")


def root_quarantines(base: Path) -> list[Path]:
    return sorted(path for path in base.iterdir() if path.name.startswith(".x64lens-cleanup.") and path.is_dir())


def cleanup_file_replacement_probe(module: Any, base: Path) -> None:
    owned = base / "owned-file-race"
    owned.mkdir()
    (owned / "victim").write_bytes(b"owned\n")
    escaped = base / "escaped-owned-file"
    identity = module.parse_identity(module.identify(owned))
    original = module.unlinkat_expected
    fired = False

    def replace(parent_fd: int, name: str, **kwargs: Any) -> None:
        nonlocal fired
        label = str(kwargs.get("label", ""))
        if not fired and label.endswith("/victim"):
            fired = True
            os.rename(name, escaped, src_dir_fd=parent_fd)
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | module.O_CLOEXEC, 0o600, dir_fd=parent_fd)
            try:
                os.write(fd, b"foreign\n")
            finally:
                os.close(fd)
        original(parent_fd, name, **kwargs)

    module.unlinkat_expected = replace
    rejected = False
    try:
        module.remove(owned, identity)
    except module.CleanupError:
        rejected = True
    finally:
        module.unlinkat_expected = original
    require(fired and rejected, "file replacement did not fail closed")
    require(escaped.read_bytes() == b"owned\n", "authenticated file was not preserved after substitution")
    foreign = [path for quarantine in root_quarantines(base) for path in quarantine.rglob("*")]
    require(any(path.is_file() and path.read_bytes() == b"foreign\n" for path in foreign),
            "foreign file replacement was deleted")


def cleanup_directory_replacement_probe(module: Any, base: Path) -> None:
    owned = base / "owned-directory-race"
    child = owned / "child"
    child.mkdir(parents=True)
    (child / "value").write_bytes(b"owned\n")
    escaped = base / "escaped-owned-directory"
    identity = module.parse_identity(module.identify(owned))
    original = module.unlinkat_expected
    fired = False

    def replace(parent_fd: int, name: str, **kwargs: Any) -> None:
        nonlocal fired
        label = str(kwargs.get("label", ""))
        if not fired and label.endswith("/child") and kwargs.get("directory") is True:
            fired = True
            os.rename(name, escaped, src_dir_fd=parent_fd)
            os.mkdir(name, mode=0o711, dir_fd=parent_fd)
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | module.O_CLOEXEC | module.O_NOFOLLOW, dir_fd=parent_fd)
            try:
                marker = os.open("foreign", os.O_WRONLY | os.O_CREAT | os.O_EXCL | module.O_CLOEXEC,
                                 0o600, dir_fd=fd)
                os.write(marker, b"foreign\n")
                os.close(marker)
            finally:
                os.close(fd)
        original(parent_fd, name, **kwargs)

    module.unlinkat_expected = replace
    rejected = False
    try:
        module.remove(owned, identity)
    except module.CleanupError:
        rejected = True
    finally:
        module.unlinkat_expected = original
    require(fired and rejected, "directory replacement did not fail closed")
    require(escaped.is_dir() and not any(escaped.iterdir()), "authenticated directory was not preserved after substitution")
    foreign = [path for quarantine in root_quarantines(base) for path in quarantine.rglob("foreign")]
    require(any(path.name == "foreign" and path.read_bytes() == b"foreign\n" for path in foreign),
            "foreign directory replacement was deleted")


def authority_mutation_probe(batch: Any, base: Path) -> None:
    authority_path = ROOT / "benchmarks/task-definitions/sprint12-batch-transaction-pilot-v3.json"
    original = json.loads(authority_path.read_text(encoding="utf-8"))
    mutations: list[tuple[str, Any]] = [
        ("publication-policy", lambda value: value.__setitem__("publish_only_complete_success", False)),
        ("stdout-cap", lambda value: value.__setitem__("maximum_stdout_bytes", 16 * 1024 * 1024)),
        ("acceptance", lambda value: value["acceptance"].__setitem__("failed_batch_count", 0)),
        (
            "case-outcome",
            lambda value: value["case_expectations"]["three-nonzero-middle"].__setitem__("published", True),
        ),
    ]
    for label, mutate in mutations:
        value = copy.deepcopy(original)
        mutate(value)
        path = base / f"mutated-{label}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        rejected = False
        try:
            batch.read_authority(path)
        except batch.PilotError:
            rejected = True
        require(rejected, f"mutated batch authority was accepted: {label}")

    authority = batch.read_authority(authority_path)
    wrong = copy.deepcopy(authority["case_expectations"]["singleton-success"])
    wrong["member_states"] = ["nonzero"]
    rejected = False
    try:
        batch.verify_case_record("singleton-success", wrong, authority)
    except batch.PilotError:
        rejected = True
    require(rejected, "case-level execution mismatch was accepted")


def streaming_cap_probe(batch: Any, base: Path) -> None:
    marker = base / "producer-completed"
    producer = (
        "import os, pathlib; "
        "remaining=16*1024*1024; chunk=b'x'*65536; "
        "exec(\"while remaining:\\n n=os.write(1, chunk[:min(len(chunk), remaining)])\\n remaining-=n\"); "
        f"pathlib.Path({str(marker)!r}).write_text('completed\\n')"
    )
    result = batch.run_command(
        [sys.executable, "-c", producer],
        timeout=10.0,
        stdout_limit=4096,
        stderr_limit=4096,
    )
    require(result.state == "stdout_limit", f"oversized producer classified as {result.state}")
    require(result.exit_code is None, "output-limit classification retained a misleading child exit")
    require(result.stdout_bytes == 4097 and result.stderr_bytes == 0,
            f"streaming cap retained unexpected bytes: {result}")
    require(not marker.exists(), "producer completed after the output cap should have terminated it")


def custody_probe(custody: Any, base: Path) -> None:
    root = base / "delivery"
    (root / "nested").mkdir(parents=True)
    (root / "a.txt").write_text("a\n")
    (root / "nested" / "b.txt").write_text("b\n")
    manifest = root / "DELIVERY_MANIFEST.json"
    custody.create(root, manifest, "synthetic-delivery")
    custody.verify(root, manifest)

    extra = root / "extra.txt"
    extra.write_text("extra\n")
    rejected = False
    try:
        custody.verify(root, manifest)
    except custody.CustodyError:
        rejected = True
    require(rejected, "undeclared delivery member was accepted")
    extra.unlink()

    (root / "nested" / "b.txt").unlink()
    rejected = False
    try:
        custody.verify(root, manifest)
    except custody.CustodyError:
        rejected = True
    require(rejected, "missing delivery member was accepted")
    (root / "nested" / "b.txt").write_text("b\n")
    custody.verify(root, manifest)

    empty = root / "undeclared-empty-directory"
    empty.mkdir()
    rejected = False
    try:
        custody.verify(root, manifest)
    except custody.CustodyError:
        rejected = True
    require(rejected, "undeclared empty delivery directory was accepted")
    empty.rmdir()

    (root / "unsafe-link").symlink_to("a.txt")
    rejected = False
    try:
        custody.verify(root, manifest)
    except custody.CustodyError:
        rejected = True
    require(rejected, "symbolic-link delivery member was accepted")


def source_custody_probe() -> None:
    manifest_path = os.environ.get("X64LENS_SOURCE_MANIFEST")
    authority_root_path = os.environ.get("X64LENS_SOURCE_AUTHORITY_ROOT")
    require(
        bool(manifest_path) == bool(authority_root_path),
        "Git-less source manifest and authority root must be supplied as one pair",
    )
    if manifest_path:
        source = load("p082_gitless_source", "tools/gitless-source-manifest.py")
        value = source.load_manifest(Path(manifest_path))
        authority_root = Path(authority_root_path)
        source.verify(authority_root, value)
        rows = [(item["git_mode"].encode("ascii"), item["path"]) for item in value["files"]]
    else:
        completed = subprocess.run(
            ["git", "ls-files", "-s", "-z"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        require(completed.returncode == 0, f"git source inventory failed: {completed.stderr!r}")
        rows = []
        for raw in completed.stdout.split(b"\0"):
            if not raw:
                continue
            metadata, path_bytes = raw.split(b"\t", 1)
            rows.append((metadata.split(b" ", 1)[0], path_bytes.decode("utf-8", "surrogateescape")))
    prohibited = []
    symlinks = []
    for mode, path in rows:
        if mode == b"120000":
            symlinks.append(path)
        parts = Path(path).parts
        if path == ".env.local" or ".local" in parts or ".git" in parts or "build" in parts or "tests/bin" in path:
            prohibited.append(path)
    require(not symlinks, f"source authority contains symbolic links: {symlinks[:5]}")
    require(not prohibited, f"source authority contains private/generated paths: {prohibited[:5]}")


def main() -> int:
    cleanup = load("p071_cleanup", "tools/remove-owned-tree.py")
    batch = load("p071_batch", "tools/sprint12-batch-transaction-smoke.py")
    custody = load("p071_custody", "tools/verify-delivery-custody.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p071-corrective-") as raw:
        root = Path(raw)
        cleanup_success_probe(cleanup, root / "cleanup-success")
        race_root = root / "cleanup-races"
        race_root.mkdir()
        cleanup_file_replacement_probe(cleanup, race_root)
        cleanup_directory_replacement_probe(cleanup, race_root)
        authority_root = root / "authority"
        authority_root.mkdir()
        authority_mutation_probe(batch, authority_root)
        streaming_cap_probe(batch, root / "streaming")
        custody_probe(custody, root / "custody")
    source_custody_probe()
    print(
        "patch070-corrective-regression-smoke: ok "
        "cleanup_success=1 file_replacement=1 directory_replacement=1 "
        "authority_mutations=4 case_mismatch=1 streaming_cap=1 "
        "delivery_extra=1 delivery_missing=1 delivery_empty_directory=1 "
        "delivery_symlink=1 source_custody=1 gitless_source=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"patch070-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
