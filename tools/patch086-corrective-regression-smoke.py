#!/usr/bin/env python3
"""Discriminate every P086 finding promoted into the P087 correction."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRANSACTION = ROOT / "tools/git-patch-transaction.py"
RECOVERY = ROOT / "tools/recover-candidate-source.py"
CUSTODY = ROOT / "tools/verify-delivery-custody.py"
REPLAY = ROOT / "tools/sprint13-natural-frozen-replay-v2-smoke.py"
ATTRIBUTION = ROOT / "tools/sprint13-natural-terminal-attribution-v2-smoke.py"
VECTOR = ROOT / "tools/sprint13-abi-role-vector-equivalence-smoke.py"


class RegressionError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RegressionError(message)


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        expected: int | None = 0, timeout: int = 120) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        check=False, timeout=timeout)
    if expected is not None:
        require(cp.returncode == expected,
                f"command returned {cp.returncode}, expected {expected}: {argv}\n{cp.stderr[-2000:]!r}")
    return cp


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def blob(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


def tree_one(name: str, oid: str) -> str:
    body = b"100644 " + name.encode() + b"\0" + bytes.fromhex(oid)
    return hashlib.sha1(b"tree " + str(len(body)).encode() + b"\0" + body).hexdigest()


def init_patch_repo(root: Path) -> dict[str, str]:
    root.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=root)
    run(["git", "config", "user.name", "p087"], cwd=root)
    run(["git", "config", "user.email", "p087@example.invalid"], cwd=root)
    (root / "tracked.txt").write_text("base\n", encoding="utf-8")
    run(["git", "add", "tracked.txt"], cwd=root)
    run(["git", "commit", "-qm", "base"], cwd=root)
    base_head = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.decode().strip()
    base_tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=root).stdout.decode().strip()
    (root / "tracked.txt").write_text("candidate\n", encoding="utf-8")
    run(["git", "add", "tracked.txt"], cwd=root)
    candidate_tree = run(["git", "write-tree"], cwd=root).stdout.decode().strip()
    patch = root.parent / f"{root.name}.patch"
    patch.write_bytes(run(["git", "diff", "--cached", "--binary"], cwd=root).stdout)
    run(["git", "reset", "--hard", "-q", "HEAD"], cwd=root)
    return {
        "base_head": base_head,
        "base_tree": base_tree,
        "candidate_tree": candidate_tree,
        "patch": str(patch),
        "sha": hashlib.sha256(patch.read_bytes()).hexdigest(),
    }


def tx_args(repo: Path, ids: dict[str, str], action: str) -> list[str]:
    return [
        sys.executable, str(TRANSACTION), action,
        "--repo", str(repo), "--patch", ids["patch"],
        "--patch-sha256", ids["sha"], "--branch", "main",
        "--base-head", ids["base_head"], "--base-tree", ids["base_tree"],
        "--candidate-tree", ids["candidate_tree"],
    ]


def hardlink_topology_probes(tmp: Path) -> tuple[int, int]:
    base = tmp / "base-hardlink"
    ids = init_patch_repo(base)
    os.link(base / "tracked.txt", tmp / "base-foreign.alias")
    cp = run(tx_args(base, ids, "apply"), cwd=base, expected=1)
    require(b"topology" in cp.stderr and (base / "tracked.txt").read_text() == "base\n",
            "pre-existing base hard link was accepted or mutated")

    candidate = tmp / "candidate-hardlink"
    ids2 = init_patch_repo(candidate)
    run(tx_args(candidate, ids2, "apply"), cwd=candidate)
    os.link(candidate / "tracked.txt", tmp / "candidate-foreign.alias")
    verify = run(tx_args(candidate, ids2, "verify-applied"), cwd=candidate, expected=1)
    repeat = run(tx_args(candidate, ids2, "apply"), cwd=candidate, expected=1)
    require(b"topology" in verify.stderr and repeat.returncode == 1
            and b"already applied" not in repeat.stderr,
            "hard-linked candidate was accepted as exact already-state")
    return 1, 1


def source_fixture(tmp: Path) -> tuple[Path, Path]:
    tmp.mkdir(parents=True, exist_ok=True)
    payload = b"good\n"
    oid = blob(payload)
    manifest = {
        "schema_id": "x64lens-candidate-source-tree-v1",
        "candidate_tree": tree_one("a.txt", oid),
        "directories": [],
        "files": [{
            "path": "a.txt", "type": "blob", "git_oid": oid,
            "git_mode": "100644", "mode": "0644",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }],
    }
    manifest_path = tmp / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
    archive_path = tmp / "source.tar.gz"
    info = tarfile.TarInfo("a.txt")
    info.size = len(payload)
    info.mode = 0o644
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.addfile(info, io.BytesIO(payload))
    return manifest_path, archive_path


def recovery_preflag_probes(tmp: Path) -> tuple[int, int]:
    recovery = load_module("p087_recovery_preflag", RECOVERY)
    manifest, archive = source_fixture(tmp)
    results = []
    for hook_name, destination_name in (
        ("_TEST_AFTER_STAGE_MKDIR_EFFECT_HOOK", "stage-window"),
        ("_TEST_AFTER_PUBLISH_RENAME_EFFECT_HOOK", "publish-window"),
    ):
        destination = tmp / destination_name
        setattr(recovery, hook_name, lambda *_args: os.kill(os.getpid(), signal.SIGTERM))
        try:
            try:
                with recovery.catchable_termination_guard("P087 recovery preflag"):
                    recovery.recover(archive, manifest, destination)
            except recovery.CatchableTermination:
                pass
            else:
                raise RegressionError(f"{hook_name} signal was accepted")
        finally:
            setattr(recovery, hook_name, None)
        require(not destination.exists() and not list(tmp.glob(".x64lens-recovery-stage.*")),
                f"{hook_name} left owned residue")
        results.append(1)
    return tuple(results)  # type: ignore[return-value]


def custody_preflag_probes(tmp: Path) -> tuple[int, int]:
    tmp.mkdir(parents=True, exist_ok=True)
    custody = load_module("p087_custody_preflag", CUSTODY)
    results = []
    for hook_name, root_name in (
        ("_TEST_AFTER_TEMP_CREATE_EFFECT_HOOK", "temp-window"),
        ("_TEST_AFTER_MANIFEST_LINK_EFFECT_HOOK", "link-window"),
    ):
        root = tmp / root_name
        root.mkdir()
        (root / "payload").write_text("payload", encoding="utf-8")
        manifest = root / "CUSTODY.json"
        setattr(custody, hook_name, lambda *_args: os.kill(os.getpid(), signal.SIGTERM))
        try:
            try:
                with custody.catchable_termination_guard("P087 custody preflag"):
                    custody.create(root, manifest, "delivery")
            except custody.CatchableTermination:
                pass
            else:
                raise RegressionError(f"{hook_name} signal was accepted")
        finally:
            setattr(custody, hook_name, None)
        require(not manifest.exists() and not list(root.glob(".custody.*")),
                f"{hook_name} left published or temporary custody evidence")
        results.append(1)
    return tuple(results)  # type: ignore[return-value]


def source_selftests() -> tuple[int, int, int]:
    run([sys.executable, str(REPLAY), "selftest"])
    run([sys.executable, str(ATTRIBUTION), "selftest"])
    run([sys.executable, str(VECTOR), "selftest"])
    return 1, 1, 1


def make_probe() -> int:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    require("patch086-corrective-regression-smoke" in text,
            "P087 corrective regression is not wired")
    require("sprint13-workload-phase-attribution-smoke" in text,
            "P087 workload/phase preflight is not wired")
    return 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p087-corrective-") as raw:
        tmp = Path(raw)
        base_hard, candidate_hard = hardlink_topology_probes(tmp)
        stage_signal, publish_signal = recovery_preflag_probes(tmp / "recovery")
        temp_signal, link_signal = custody_preflag_probes(tmp / "custody")
    replay, attribution, vector = source_selftests()
    make = make_probe()
    print(
        "patch086-corrective-regression-smoke: ok "
        f"base_hardlink_rejected={base_hard} candidate_hardlink_rejected={candidate_hard} "
        f"recovery_stage_preflag={stage_signal} recovery_publish_preflag={publish_signal} "
        f"custody_temp_preflag={temp_signal} custody_link_preflag={link_signal} "
        f"replay_runtime_pinned={replay} attribution_atomic={attribution} "
        f"abi_no_replace_retained_checksum={vector} make_wiring={make} "
        "wrapper_post_helper_signal=delivery_gate candidate_abi_source=artifact_gate loose_checksum=delivery_gate"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"patch086-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
