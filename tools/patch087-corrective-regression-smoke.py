#!/usr/bin/env python3
"""Discriminate every P087 finding promoted into the P088 correction."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRANSACTION = ROOT / "tools/git-patch-transaction.py"
RECOVERY = ROOT / "tools/recover-candidate-source.py"
REPLAY = ROOT / "tools/sprint13-natural-frozen-replay-v2-smoke.py"
ATTRIBUTION = ROOT / "tools/sprint13-natural-terminal-attribution-v2-smoke.py"
VECTOR = ROOT / "tools/sprint13-abi-role-vector-equivalence-smoke.py"
WORKLOAD = ROOT / "tools/sprint13-workload-phase-attribution-smoke.py"
SPLIT = ROOT / "tools/sprint13-split-debug-packaging-smoke.py"


class RegressionError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RegressionError(message)


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        expected: int | None = 0, timeout: int = 180) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        check=False, timeout=timeout)
    if expected is not None:
        require(cp.returncode == expected,
                f"command returned {cp.returncode}, expected {expected}: {argv}\n{cp.stderr[-3000:]!r}")
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
    run(["git", "config", "user.name", "p088"], cwd=root)
    run(["git", "config", "user.email", "p088@example.invalid"], cwd=root)
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


def terminal_success_probe(tmp: Path) -> tuple[int, int]:
    repo = tmp / "terminal"
    ids = init_patch_repo(repo)
    env = os.environ.copy()
    env["X64LENS_PATCH_TRANSACTION_BEFORE_STATUS_HOOK"] = "kill -TERM $PPID"
    applied = run(tx_args(repo, ids, "apply"), cwd=repo, env=env)
    lines = [line for line in applied.stdout.decode().splitlines() if line]
    require(len(lines) == 1 and lines[0].startswith("git-patch-transaction: ok action=apply "),
            "apply did not publish exactly one terminal success banner")
    require(run(["git", "write-tree"], cwd=repo).stdout.decode().strip() == ids["candidate_tree"],
            "pending signal reversed an externally successful apply")
    rolled = run(tx_args(repo, ids, "rollback"), cwd=repo, env=env)
    lines = [line for line in rolled.stdout.decode().splitlines() if line]
    require(len(lines) == 1 and lines[0].startswith("git-patch-transaction: ok action=rollback "),
            "rollback did not publish exactly one terminal success banner")
    require(run(["git", "write-tree"], cwd=repo).stdout.decode().strip() == ids["base_tree"],
            "pending signal reversed an externally successful rollback")
    return 1, 1


def exact_mode_probe(tmp: Path) -> int:
    repo = tmp / "mode"
    ids = init_patch_repo(repo)
    path = repo / "tracked.txt"
    path.chmod(0o444)
    cp = run(tx_args(repo, ids, "apply"), cwd=repo, expected=1)
    require(path.stat().st_mode & 0o777 == 0o444 and path.read_text() == "base\n",
            "noncanonical base mode was accepted or mutated")
    require(b"logical base" in cp.stderr or b"exact" in cp.stderr or b"mode" in cp.stderr,
            "mode rejection did not use the transaction error surface")
    path.chmod(0o644)
    return 1


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


def recovery_fd_probe(tmp: Path) -> int:
    recovery = load_module("p088_recovery_fd", RECOVERY)
    manifest, archive = source_fixture(tmp)
    destination = tmp / "result"
    old_count = recovery.open_fd_count
    old_limit = recovery.resource.getrlimit
    recovery.open_fd_count = lambda: 200
    recovery.resource.getrlimit = lambda _which: (128, 128)
    try:
        try:
            recovery.recover(archive, manifest, destination)
        except recovery.RecoveryError as exc:
            require("file-descriptor limit" in str(exc), "FD preflight failed for a different reason")
        else:
            raise RegressionError("under-capacity recovery was accepted")
    finally:
        recovery.open_fd_count = old_count
        recovery.resource.getrlimit = old_limit
    require(not destination.exists() and not list(tmp.glob(".x64lens-recovery-*")),
            "FD preflight failure left recovery residue")
    return 1


def replay_error_normalization_probe(tmp: Path) -> int:
    tmp.mkdir(parents=True, exist_ok=True)
    replay = load_module("p088_replay_error", REPLAY)
    authority = replay.validate_authority(replay.load(ROOT / "benchmarks/task-definitions/sprint13-natural-frozen-replay-v2.json"))
    input_dir = tmp / "input"
    input_dir.mkdir()
    result_dir = tmp / "result"

    class ForeignCampaignError(RuntimeError):
        pass

    class FakeAttr:
        @staticmethod
        def validate_input(_input: Path, _authority: dict[str, Any]) -> None:
            raise ForeignCampaignError("/tmp/private/source/path")

    original_module = replay.module

    def fake_module(name: str, path: Path) -> Any:
        if path == replay.ATTRIBUTION_V1:
            return FakeAttr
        if path in {replay.NATURAL, replay.REMOVE}:
            return SimpleNamespace()
        return original_module(name, path)

    replay.module = fake_module
    try:
        args = SimpleNamespace(
            input_dir=input_dir, result_dir=result_dir,
            x64lens=Path("/nonexistent/x64lens"), ropgadget=Path("/nonexistent/ROPgadget"),
            ropper=Path("/nonexistent/ropper"), ropr=Path("/nonexistent/ropr"),
            source_root=Path("/nonexistent/source"), source_manifest=Path("/nonexistent/manifest"),
            expected_candidate_tree="0" * 40, authority=ROOT / "benchmarks/task-definitions/sprint13-natural-frozen-replay-v2.json",
        )
        try:
            replay.run_replay(args, authority)
        except replay.ReplayError as exc:
            message = str(exc)
            require(message == "predecessor input authority rejected: ForeignCampaignError",
                    "imported authority failure was not normalized")
            require("/tmp/" not in message and "Traceback" not in message,
                    "normalized replay error leaked private path/traceback")
        else:
            raise RegressionError("imported replay error was accepted")
    finally:
        replay.module = original_module
    require(not result_dir.exists(), "normalized preflight error published a result")
    return 1


def projection_path_probe(tmp: Path) -> int:
    tmp.mkdir(parents=True, exist_ok=True)
    replay = load_module("p088_projection", REPLAY)
    gcc = shutil.which("gcc")
    objcopy = shutil.which("objcopy")
    require(gcc is not None and objcopy is not None, "projection probe requires gcc and objcopy")
    binaries: list[Path] = []
    for name in ("one", "two"):
        root = tmp / name
        root.mkdir()
        (root / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
        run([gcc, "-g", "-O0", "-Wl,--build-id=none", "main.c", "-o", "x64lens"], cwd=root)
        binaries.append(root / "x64lens")
    require(hashlib.sha256(binaries[0].read_bytes()).hexdigest() != hashlib.sha256(binaries[1].read_bytes()).hexdigest(),
            "path-dependence control did not produce distinct debug binaries")
    projected = tmp / "projected"
    run([objcopy, "--strip-debug", str(binaries[0]), str(projected)], cwd=tmp)
    expected = {
        "mode": "0755",
        "projection_sha256": hashlib.sha256(projected.read_bytes()).hexdigest(),
        "projection_size_bytes": projected.stat().st_size,
    }

    class Natural:
        @staticmethod
        def read_regular_authority(path: Path, _maximum: int) -> tuple[bytes, dict[str, Any]]:
            data = path.read_bytes()
            return data, {"mode": "0755", "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}

    left = replay.strip_debug_projection(Natural, binaries[0], expected)
    right = replay.strip_debug_projection(Natural, binaries[1], expected)
    require(left["projection_sha256"] == right["projection_sha256"],
            "strip-debug projection remained checkout-path dependent")
    return 1


def source_selftests() -> tuple[int, int, int, int, int]:
    run([sys.executable, str(WORKLOAD), "selftest",
         "--authority", str(ROOT / "benchmarks/task-definitions/sprint13-workload-phase-attribution-v1.json"),
         "--expected", str(ROOT / "tests/expected/sprint13-workload-phase-attribution-v1.json")])
    run([sys.executable, str(REPLAY), "selftest"])
    run([sys.executable, str(ATTRIBUTION), "selftest"])
    run([sys.executable, str(VECTOR), "selftest"])
    run([sys.executable, str(SPLIT), "selftest",
         "--authority", str(ROOT / "benchmarks/task-definitions/sprint13-split-debug-packaging-v1.json"),
         "--expected", str(ROOT / "tests/expected/sprint13-split-debug-packaging-v1.json")])
    return 1, 1, 1, 1, 1


def make_probe() -> tuple[int, int, int]:
    text = (ROOT / "Makefile").read_text(encoding="utf-8")
    require("patch087-corrective-regression-smoke" in text, "P088 corrective regression is not wired")
    require("sprint13-split-debug-packaging-contract-smoke" in text
            and "sprint13-split-debug-packaging-smoke" in text,
            "split-debug experiment is not wired")
    require("git diff --quiet -- && git diff --cached --quiet --" in text,
            "clean-tree producer fallback is missing")
    return 1, 1, 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p088-corrective-") as raw:
        tmp = Path(raw)
        apply_terminal, rollback_terminal = terminal_success_probe(tmp)
        exact_mode = exact_mode_probe(tmp)
        recovery_fd = recovery_fd_probe(tmp / "recovery")
        imported_error = replay_error_normalization_probe(tmp / "replay-error")
        projection = projection_path_probe(tmp / "projection")
    workload, replay, attribution, vector, split = source_selftests()
    make_wiring, clean_fallback, split_wiring = make_probe()
    print(
        "patch087-corrective-regression-smoke: ok "
        f"apply_terminal_success={apply_terminal} rollback_terminal_success={rollback_terminal} "
        f"exact_mode_rejected={exact_mode} recovery_fd_preflight={recovery_fd} "
        f"workload_thresholds={workload} replay_symlink_record_closure={replay} "
        f"attribution_atomic={attribution} abi_stage_signal={vector} "
        f"projection_path_independent={projection} imported_error_normalized={imported_error} "
        f"split_debug_contract={split} make_wiring={make_wiring} clean_tree_fallback={clean_fallback} "
        f"split_wiring={split_wiring} outer_sidecar=delivery_gate portable_component_checksums=delivery_gate "
        "source_identity_modes=delivery_gate evidence_ledger=delivery_gate"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"patch087-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
