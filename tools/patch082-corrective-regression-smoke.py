#!/usr/bin/env python3
"""Discriminate every localized acceptance blocker promoted from P082 review."""
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
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRANSACTION = ROOT / "tools/git-patch-transaction.py"
RECOVERY = ROOT / "tools/recover-candidate-source.py"


class RegressionError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RegressionError(message)


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, expected: int | None = 0, stdout: Any = subprocess.PIPE) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(argv, cwd=cwd, env=env, stdout=stdout, stderr=subprocess.PIPE, check=False, timeout=120)
    if expected is not None:
        require(cp.returncode == expected, f"command failed ({cp.returncode}, expected {expected}): {' '.join(argv)}\nstderr={cp.stderr[-4000:]!r}")
    return cp


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def init_patch_repo(path: Path) -> dict[str, str]:
    path.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=path)
    run(["git", "config", "user.name", "regression"], cwd=path)
    run(["git", "config", "user.email", "regression@example.invalid"], cwd=path)
    (path / "tools").mkdir()
    (path / "tools/a.txt").write_text("base\n", encoding="utf-8")
    run(["git", "add", "."], cwd=path)
    run(["git", "commit", "-qm", "base"], cwd=path)
    head = run(["git", "rev-parse", "HEAD"], cwd=path).stdout.decode().strip()
    base_tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=path).stdout.decode().strip()
    (path / "tools/a.txt").write_text("candidate\n", encoding="utf-8")
    patch = path.parent / f"{path.name}-change.patch"
    patch.write_bytes(run(["git", "diff", "--binary", "--", "tools/a.txt"], cwd=path).stdout)
    patch_sha = hashlib.sha256(patch.read_bytes()).hexdigest()
    run(["git", "add", "tools/a.txt"], cwd=path)
    candidate_tree = run(["git", "write-tree"], cwd=path).stdout.decode().strip()
    run(["git", "restore", "--staged", "--worktree", "tools/a.txt"], cwd=path)
    return {"head": head, "base_tree": base_tree, "candidate_tree": candidate_tree, "patch": str(patch), "patch_sha": patch_sha}


def tx_command(repo: Path, identity: dict[str, str], action: str = "apply") -> list[str]:
    return [
        sys.executable, str(TRANSACTION), action,
        "--repo", str(repo), "--patch", identity["patch"], "--patch-sha256", identity["patch_sha"],
        "--branch", "main", "--base-head", identity["head"], "--base-tree", identity["base_tree"],
        "--candidate-tree", identity["candidate_tree"],
    ]


def exact_head_probe(tmp: Path) -> int:
    repo = tmp / "same-tree-head"
    identity = init_patch_repo(repo)
    run(["git", "commit", "--allow-empty", "-qm", "foreign same-tree head"], cwd=repo)
    cp = run(tx_command(repo, identity), expected=None)
    require(cp.returncode == 1 and b"base HEAD mismatch" in cp.stderr, "same-tree foreign HEAD was accepted")
    require(run(["git", "write-tree"], cwd=repo).stdout.decode().strip() == identity["base_tree"], "wrong-HEAD probe changed index")
    return 1


def parent_binding_probe(tmp: Path) -> int:
    repo = tmp / "parent-binding"
    identity = init_patch_repo(repo)
    env = os.environ.copy()
    env["X64LENS_PATCH_TRANSACTION_AFTER_CHECK_HOOK"] = "mv tools tools.original && mkdir tools && ln tools.original/a.txt tools/a.txt"
    cp = run(tx_command(repo, identity), env=env, expected=None)
    require(cp.returncode == 1 and b"parent binding changed" in cp.stderr, "patch-path parent replacement was accepted")
    require((repo / "tools/a.txt").read_text(encoding="utf-8") == "base\n", "parent-binding probe applied candidate bytes")
    require(run(["git", "write-tree"], cwd=repo).stdout.decode().strip() == identity["base_tree"], "parent-binding probe changed index")
    return 1


def output_failure_recovery_probe(tmp: Path) -> int:
    repo = tmp / "output-recovery"
    identity = init_patch_repo(repo)
    with open("/dev/full", "wb", buffering=0) as sink:
        cp = run(tx_command(repo, identity), expected=None, stdout=sink)
    require(cp.returncode == 1 and b"inverse recovery restored" in cp.stderr, "post-effect output failure did not report recovery")
    require((repo / "tools/a.txt").read_text(encoding="utf-8") == "base\n", "post-effect output failure left candidate bytes")
    require(run(["git", "write-tree"], cwd=repo).stdout.decode().strip() == identity["base_tree"], "post-effect output failure left candidate index")
    return 1


def phony_probe() -> int:
    module = load_module("p083_provisional", ROOT / "tools/provisional-corpus-smoke.py")
    sample = ".PHONY: first second\n.PHONY: clean-provisional-corpus third\\\n fourth\n"
    observed = module.parse_phony_targets(sample)
    require({"first", "second", "clean-provisional-corpus", "third", "fourth"} <= observed, "multi-declaration .PHONY parsing failed")
    return 1


def git_blob(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


def git_tree(entries: list[tuple[str, str, str]]) -> str:
    body = b"".join(mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(oid) for mode, name, oid in sorted(entries, key=lambda item: item[1].encode()))
    return hashlib.sha1(b"tree " + str(len(body)).encode() + b"\0" + body).hexdigest()


def umask_recovery_probe(tmp: Path) -> int:
    payload = b"exact source\n"
    oid = git_blob(payload)
    tree = git_tree([("100644", "a.txt", oid)])
    manifest = {
        "schema_id": "x64lens-candidate-source-tree-v1",
        "candidate_tree": tree,
        "directories": [],
        "files": [{
            "path": "a.txt", "type": "blob", "git_oid": oid, "git_mode": "100644",
            "mode": "0644", "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload),
        }],
    }
    manifest_path = tmp / "source-manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    archive = tmp / "source.tar.gz"
    info = tarfile.TarInfo("a.txt"); info.size = len(payload); info.mode = 0o644
    with tarfile.open(archive, "w:gz") as tar:
        tar.addfile(info, io.BytesIO(payload))
    destination = tmp / "recovered"
    def set_umask() -> None:
        os.umask(0o777)
    cp = subprocess.run(
        [sys.executable, str(RECOVERY), "--archive", str(archive), "--manifest", str(manifest_path), "--destination", str(destination)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60, preexec_fn=set_umask,
    )
    require(cp.returncode == 0, f"recovery failed under umask 0777: {cp.stderr!r}")
    require((destination.stat().st_mode & 0o7777) == 0o755 and ((destination / "a.txt").stat().st_mode & 0o7777) == 0o644, "recovery modes changed under umask 0777")
    require(not list(tmp.glob(".x64lens-recovery-stage.*")), "recovery left staging residue under umask 0777")
    return 1


def producer_probe(tmp: Path) -> tuple[int, int]:
    p081 = load_module("p083_patch081", ROOT / "tools/patch081-corrective-regression-smoke.py")
    producer = load_module("p083_producer", ROOT / "tools/sprint13-producer-authority-smoke.py")
    manifest = p081.create_synthetic_producer(tmp)
    producer.validate_manifest(manifest, "1" * 40)
    try:
        producer.validate_manifest(manifest, "2" * 40)
    except producer.ProducerError:
        wrong_tree = 1
    else:
        raise RegressionError("producer accepted a foreign candidate tree")
    analyzer = manifest.parent / "generation-1/x64lens"
    analyzer.chmod(0o444)
    try:
        producer.validate_manifest(manifest, "1" * 40)
    except producer.ProducerError:
        wrong_mode = 1
    else:
        raise RegressionError("producer accepted a non-executable retained analyzer")
    return wrong_tree, wrong_mode


def docker_contract_probe() -> int:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    parity = (ROOT / "tools/native-docker-json-parity-smoke.sh").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    require(makefile.count('run="$${X64LENS_RUN_ROOT:?}"') >= 2, "Docker test/validation do not use configured run root")
    require("run=${X64LENS_RUN_ROOT:?}" in parity, "Docker parity does not use configured run root")
    require("ENV X64LENS_RUN_ROOT=${HOME}/x64lens-run" in dockerfile, "image lacks writable run-root authority")
    require((ROOT / "tools/docker-run-root-smoke.sh").is_file(), "dynamic Docker run-root regression missing")
    return 1


def natural_campaign_probe() -> int:
    cp = run([sys.executable, str(ROOT / "tools/sprint13-natural-coordinate-campaign.py"), "selftest"])
    require(b"qualified=9 controls=108" in cp.stdout, "natural-coordinate campaign selftest did not close denominators")
    return 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p083-corrective-") as raw:
        tmp = Path(raw)
        exact_head = exact_head_probe(tmp)
        parent = parent_binding_probe(tmp)
        output = output_failure_recovery_probe(tmp)
        umask = umask_recovery_probe(tmp)
        producer_tree, producer_mode = producer_probe(tmp)
    phony = phony_probe()
    docker = docker_contract_probe()
    natural = natural_campaign_probe()
    print(
        "patch082-corrective-regression-smoke: ok "
        f"phony_multi_declaration={phony} exact_base_head={exact_head} patch_parent_binding={parent} "
        f"post_effect_output_recovery={output} recovery_umask_0777={umask} "
        f"producer_candidate_tree={producer_tree} producer_modes={producer_mode} "
        f"docker_writable_run_root={docker} natural_coordinate_selftest={natural} "
        "loose_retro_identity=delivery_gate evidence_postseal=delivery_gate"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"patch082-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
