#!/usr/bin/env python3
"""Regress Patch 071 cleanup, batch, JSON-authority, and custody findings.

The probes target the final unlink boundary, inode-generation identity, legal
long components, parent-descriptor cleanup, post-leader deadlines, detached
processes, transaction-root substitution, publication transitions, duplicate
JSON keys, explicit case ordering, and recursive delivery custody.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint12-batch-transaction-pilot-v3.json"


class RegressionError(RuntimeError):
    pass


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


def fds() -> set[int]:
    return {int(value) for value in os.listdir("/proc/self/fd")}


def cleanup_baseline_and_long_name(cleanup: Any, base: Path) -> None:
    owned = base / "owned"
    owned.mkdir(parents=True)
    long_name = "x" * 240
    (owned / long_name).write_bytes(b"owned\n")
    (owned / "nested").mkdir()
    (owned / "nested" / "value").write_bytes(b"value\n")
    identity = cleanup.parse_identity(cleanup.identify(owned))
    cleanup.remove(owned, identity)
    require(not owned.exists(), "authenticated cleanup or legal long component failed")


def final_replacement(cleanup: Any, base: Path, *, kind: str) -> None:
    owned = base / f"final-{kind}-root"
    if kind == "file":
        owned.mkdir()
        (owned / "victim").write_bytes(b"owned\n")
    elif kind == "directory":
        (owned / "child").mkdir(parents=True)
    elif kind == "root":
        owned.mkdir()
    else:
        raise AssertionError(kind)
    identity = cleanup.parse_identity(cleanup.identify(owned))
    escaped = base / f"escaped-{kind}"
    original = cleanup.unlinkat
    fired = False

    def replace(parent_fd: int, name: str, *, directory: bool = False) -> None:
        nonlocal fired
        target = (kind == "file" and not directory) or (kind in {"directory", "root"} and directory)
        if not fired and target:
            fired = True
            os.rename(name, escaped, src_dir_fd=parent_fd)
            if directory:
                os.mkdir(name, mode=0o700, dir_fd=parent_fd)
            else:
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
                os.write(fd, b"foreign\n")
                os.close(fd)
        original(parent_fd, name, directory=directory)

    cleanup.unlinkat = replace
    rejected = False
    try:
        cleanup.remove(owned, identity)
    except cleanup.CleanupError:
        rejected = True
    finally:
        cleanup.unlinkat = original
    require(fired and rejected, f"final {kind} replacement was not rejected")
    require(escaped.exists(), f"owned {kind} did not remain preserved")
    foreign = [path for path in base.rglob("*") if path != escaped and path.name.startswith(".x64lens-cleanup.")]
    require(foreign or kind == "root", f"foreign {kind} replacement disappeared")


def generation_mismatch(cleanup: Any, base: Path) -> None:
    original = base / "generation-root"
    original.mkdir()
    old = cleanup.parse_identity(cleanup.identify(original))
    original.rmdir()
    time.sleep(0.02)
    original.mkdir()
    current = cleanup.parse_identity(cleanup.identify(original))
    forged = cleanup.RootIdentity(current.device, current.inode, old.birth_ns, current.mount_id)
    rejected = False
    try:
        cleanup.remove(original, forged)
    except cleanup.CleanupError:
        rejected = True
    require(rejected and original.is_dir(), "birth-time generation mismatch was accepted")


def ancestor_fd_probe(cleanup: Any, base: Path) -> None:
    container = base / "container"
    owned = container / "ancestor" / "owned"
    owned.mkdir(parents=True)
    (owned / "value").write_bytes(b"owned\n")
    identity = cleanup.parse_identity(cleanup.identify(owned))
    original_open = cleanup.os.open
    container_identity = (container.stat().st_dev, container.stat().st_ino)
    before = fds()
    fired = False

    def replace(path: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        nonlocal fired
        if not fired and path == "ancestor" and dir_fd is not None:
            parent = os.fstat(dir_fd)
            if (parent.st_dev, parent.st_ino) == container_identity:
                fired = True
                os.rename("ancestor", "ancestor-owned", src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
                os.mkdir("ancestor", 0o700, dir_fd=dir_fd)
                ancestor_fd = original_open("ancestor", os.O_RDONLY | os.O_DIRECTORY, dir_fd=dir_fd)
                os.mkdir("owned", 0o700, dir_fd=ancestor_fd)
                os.close(ancestor_fd)
        return original_open(path, flags, mode, dir_fd=dir_fd)

    cleanup.os.open = replace
    rejected = False
    try:
        cleanup.remove(owned, identity)
    except cleanup.CleanupError:
        rejected = True
    finally:
        cleanup.os.open = original_open
    after = fds()
    require(fired and rejected, "ancestor substitution was not rejected")
    require(after == before, f"ancestor substitution leaked descriptors: {sorted(after - before)}")


def authority_probes(batch: Any, base: Path) -> None:
    authority = batch.read_authority(AUTHORITY)
    raw = AUTHORITY.read_text(encoding="utf-8")
    duplicate_top = raw.replace('"schema_id": "sprint12-batch-transaction-pilot-v3",',
                                '"schema_id": "sprint12-batch-transaction-pilot-v3",\n  "schema_id": "duplicate",', 1)
    path = base / "duplicate-top.json"
    path.write_text(duplicate_top)
    try:
        batch.read_authority(path)
    except batch.PilotError:
        pass
    else:
        raise RegressionError("duplicate top-level authority key was accepted")

    value = json.loads(raw)
    families = value["case_families"]
    value["case_families"] = {name: families[name] for name in reversed(list(families))}
    path = base / "reordered.json"
    path.write_text(json.dumps(value, indent=2) + "\n")
    reordered = batch.read_authority(path)
    require(reordered["case_order"] == authority["case_order"],
            "case-family object order changed explicit execution order")

    expected = authority["case_expectations"]["singleton-success"]
    require(expected["publication_transitions"] == 1, "publication transition authority is incomplete")


def process_tree_probes(batch: Any, base: Path) -> None:
    inherited = batch.run_command(
        ["/bin/sh", "-c", "sleep 30 & exit 0"],
        timeout=0.1,
        stdout_limit=4096,
        stderr_limit=4096,
    )
    require(inherited.state == "timeout", f"leader-exit inherited pipe bypassed deadline: {inherited}")

    marker = base / "detached-marker"
    command = f"setsid /bin/sh -c 'sleep 0.5; echo survived > {marker}' </dev/null >/dev/null 2>&1 & exit 0"
    detached = batch.run_command(
        ["/bin/sh", "-c", command],
        timeout=0.2,
        stdout_limit=4096,
        stderr_limit=4096,
    )
    require(detached.state == "descendant", f"detached descendant was not classified: {detached}")
    time.sleep(0.6)
    require(not marker.exists(), "detached descendant survived cleanup")


def normal_root_replacement(batch: Any, base: Path) -> None:
    authority = batch.read_authority(AUTHORITY)
    original = batch.publish_complete
    state: dict[str, Path] = {}

    def replace(stage: Path, result: Path, record: dict[str, Any]) -> None:
        original(stage, result, record)
        root = stage.parent
        displaced = base / "normal-owned-displaced"
        root.rename(displaced)
        root.mkdir()
        (root / "result").mkdir()
        marker = root / "foreign"
        marker.write_text("foreign\n")
        state.update(root=root, displaced=displaced, marker=marker)

    batch.publish_complete = replace
    rejected = False
    try:
        batch.normal_transaction("singleton-success", authority)
    except batch.CLEANUP.CleanupError:
        rejected = True
    finally:
        batch.publish_complete = original
    require(rejected and state["marker"].read_text() == "foreign\n", "normal cleanup deleted replacement root")
    shutil.rmtree(state["root"])
    shutil.rmtree(state["displaced"])


def wait_for(path: Path, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 5
    while not path.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.005)
    require(path.exists(), f"worker failed to create {path}")


def signal_root_replacement(base: Path) -> None:
    sync = base / "signal-sync"
    sync.mkdir()
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "tools/sprint12-batch-transaction-smoke.py"),
         "--signal-worker", "sigterm-before-first", "--sync", str(sync)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    wait_for(sync / "worker-ready", process)
    (sync / "observer-ready").write_text("observer-ready\n")
    wait_for(sync / "ready", process)
    transaction = sync / "transaction"
    displaced = sync / "owned-displaced"
    transaction.rename(displaced)
    transaction.mkdir()
    marker = transaction / "foreign"
    marker.write_text("foreign\n")
    os.kill(process.pid, signal.SIGTERM)
    _stdout, _stderr = process.communicate(timeout=10)
    require(process.returncode != 143, "signal cleanup falsely succeeded after root replacement")
    require(marker.read_text() == "foreign\n" and displaced.is_dir(), "signal cleanup deleted foreign or owned root")
    shutil.rmtree(transaction)
    shutil.rmtree(displaced)
    for path in sync.iterdir():
        path.unlink()
    sync.rmdir()


def transient_publication_probe(batch: Any, base: Path) -> None:
    wrapper = base / "faulty-worker.py"
    wrapper.write_text(
        r"""#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import shutil
import signal
import time

parser = argparse.ArgumentParser()
parser.add_argument("--signal-worker")
parser.add_argument("--sync", type=Path)
args = parser.parse_args()
signum = signal.SIGTERM if args.signal_worker.startswith("sigterm") else signal.SIGINT
caught = 0

def handler(received, _frame):
    global caught
    caught = received

signal.signal(signum, handler)
root = args.sync / "transaction"
root.mkdir()
(args.sync / "publication-state.json").write_text(
    json.dumps({"case": args.signal_worker, "state": "not_published", "transitions": 0}) + "\n"
)
(args.sync / "worker-ready").write_text("worker-ready\n")
deadline = time.monotonic() + 10
while not (args.sync / "observer-ready").exists() and time.monotonic() < deadline:
    time.sleep(0.005)
if not (args.sync / "observer-ready").exists():
    raise SystemExit(2)
(root / "result").mkdir()
(root / "result" / "bad").write_text("published\n")
(args.sync / "ready").write_text("ready\n")
while not caught:
    time.sleep(0.005)
shutil.rmtree(root)
raise SystemExit(128 + signum)
""",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    actual = batch.SCRIPT
    batch.SCRIPT = wrapper
    rejected = False
    try:
        batch.run_signal_case("sigterm-after-final")
    except batch.PilotError as exc:
        rejected = "transient publication observed" in str(exc)
    finally:
        batch.SCRIPT = actual
    require(rejected, "publish-then-delete signal worker was accepted as unpublished")


def custody_duplicate_probe(custody: Any, base: Path) -> None:
    root = base / "delivery"
    root.mkdir()
    (root / "value").write_text("value\n")
    manifest = root / "manifest.json"
    custody.create(root, manifest, "delivery")
    custody.verify(root, manifest)
    raw = manifest.read_text()
    manifest.write_text(raw.replace('"root_label": "delivery",', '"root_label": "delivery",\n  "root_label": "duplicate",', 1))
    try:
        custody.verify(root, manifest)
    except custody.CustodyError:
        pass
    else:
        raise RegressionError("duplicate delivery root_label was accepted")


def main() -> int:
    cleanup = load("p072_cleanup", "tools/remove-owned-tree.py")
    batch = load("p072_batch", "tools/sprint12-batch-transaction-smoke.py")
    custody = load("p072_custody", "tools/verify-delivery-custody.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p072-corrective-") as raw:
        base = Path(raw)
        names = ["baseline", "generation", "ancestor", "authority", "process", "normal", "signal", "publication", "custody"]
        names += [f"replace-{kind}" for kind in ("file", "directory", "root")]
        for name in names:
            (base / name).mkdir()
        cleanup_baseline_and_long_name(cleanup, base / "baseline")
        for kind in ("file", "directory", "root"):
            final_replacement(cleanup, base / f"replace-{kind}", kind=kind)
        generation_mismatch(cleanup, base / "generation")
        ancestor_fd_probe(cleanup, base / "ancestor")
        authority_probes(batch, base / "authority")
        process_tree_probes(batch, base / "process")
        normal_root_replacement(batch, base / "normal")
        signal_root_replacement(base / "signal")
        transient_publication_probe(batch, base / "publication")
        custody_duplicate_probe(custody, base / "custody")
    print(
        "patch071-corrective-regression-smoke: ok "
        "cleanup_long_name=1 final_file=1 final_directory=1 final_root=1 "
        "generation_identity=1 ancestor_fd=1 duplicate_json=2 case_order=1 "
        "leader_exit_deadline=1 detached_descendant=1 normal_root_cas=1 "
        "signal_root_cas=1 publication_transition=1 custody_duplicate=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"patch071-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
