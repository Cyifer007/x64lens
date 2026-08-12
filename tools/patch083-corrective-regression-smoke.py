#!/usr/bin/env python3
"""Discriminate every P083 finding promoted into the P084 correction."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRANSACTION = ROOT / "tools/git-patch-transaction.py"
RECOVERY = ROOT / "tools/recover-candidate-source.py"
GITLESS = ROOT / "tools/gitless-source-manifest.py"
NATURAL = ROOT / "tools/sprint13-natural-coordinate-campaign.py"


class RegressionError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RegressionError(message)


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, expected: int | None = 0) -> subprocess.CompletedProcess[bytes]:
    cp = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=120)
    if expected is not None:
        require(cp.returncode == expected, f"command failed ({cp.returncode}, expected {expected}): {' '.join(argv)}\n{cp.stderr[-4000:]!r}")
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
    patch = path.parent / f"{path.name}.patch"
    patch.write_bytes(run(["git", "diff", "--binary", "--", "tools/a.txt"], cwd=path).stdout)
    patch_sha = hashlib.sha256(patch.read_bytes()).hexdigest()
    run(["git", "add", "tools/a.txt"], cwd=path)
    candidate_tree = run(["git", "write-tree"], cwd=path).stdout.decode().strip()
    run(["git", "restore", "--staged", "--worktree", "tools/a.txt"], cwd=path)
    return {"head": head, "base_tree": base_tree, "candidate_tree": candidate_tree, "patch": str(patch), "patch_sha": patch_sha}


def tx(repo: Path, identity: dict[str, str], action: str) -> list[str]:
    return [
        sys.executable, str(TRANSACTION), action,
        "--repo", str(repo), "--patch", identity["patch"], "--patch-sha256", identity["patch_sha"],
        "--branch", "main", "--base-head", identity["head"], "--base-tree", identity["base_tree"],
        "--candidate-tree", identity["candidate_tree"],
    ]


def post_effect_binding_probe(tmp: Path) -> tuple[int, int]:
    apply_repo = tmp / "apply-rebind"
    identity = init_patch_repo(apply_repo)
    env = os.environ.copy()
    env["X64LENS_PATCH_TRANSACTION_AFTER_APPLY_EFFECT_HOOK"] = (
        "mv tools tools.owned-effect && mkdir tools && cp tools.owned-effect/a.txt tools/a.txt"
    )
    cp = run(tx(apply_repo, identity, "apply"), env=env, expected=None)
    require(cp.returncode == 1 and b"parent binding changed after effect" in cp.stderr, "post-apply parent rebind was accepted")
    require((apply_repo / "tools/a.txt").read_text(encoding="utf-8") == "candidate\n", "foreign apply replacement was not preserved")
    require(b"git-patch-transaction: ok" not in cp.stdout, "post-apply rebind emitted success")

    rollback_repo = tmp / "rollback-rebind"
    identity2 = init_patch_repo(rollback_repo)
    run(tx(rollback_repo, identity2, "apply"))
    env2 = os.environ.copy()
    env2["X64LENS_PATCH_TRANSACTION_AFTER_ROLLBACK_EFFECT_HOOK"] = (
        "mv tools tools.owned-effect && mkdir tools && cp tools.owned-effect/a.txt tools/a.txt"
    )
    cp2 = run(tx(rollback_repo, identity2, "rollback"), env=env2, expected=None)
    require(cp2.returncode == 1 and b"parent binding changed after effect" in cp2.stderr, "post-rollback parent rebind was accepted")
    require((rollback_repo / "tools/a.txt").read_text(encoding="utf-8") == "base\n", "foreign rollback replacement was not preserved")
    require(b"git-patch-transaction: ok" not in cp2.stdout, "post-rollback rebind emitted success")
    return 1, 1


def git_blob(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()


def git_tree(mode: str, name: str, oid: str) -> str:
    body = mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(oid)
    return hashlib.sha1(b"tree " + str(len(body)).encode() + b"\0" + body).hexdigest()


def executable_binary_rollback_probe(tmp: Path) -> int:
    repo = tmp / "binary-mode-rollback"
    repo.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=repo)
    run(["git", "config", "user.name", "regression"], cwd=repo)
    run(["git", "config", "user.email", "regression@example.invalid"], cwd=repo)
    binary = repo / "generated.bin"
    binary.write_bytes(b"\x7fELF" + bytes(range(64)))
    binary.chmod(0o755)
    (repo / "keep.txt").write_text("keep\n", encoding="utf-8")
    run(["git", "add", "generated.bin", "keep.txt"], cwd=repo)
    run(["git", "commit", "-qm", "base executable binary"], cwd=repo)
    head = run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.decode().strip()
    base_tree = run(["git", "rev-parse", "HEAD^{tree}"], cwd=repo).stdout.decode().strip()
    binary.unlink()
    patch = tmp / "binary-mode-delete.patch"
    patch.write_bytes(run(["git", "diff", "--binary", "--", "generated.bin"], cwd=repo).stdout)
    patch_sha = hashlib.sha256(patch.read_bytes()).hexdigest()
    keep_oid = run(["git", "rev-parse", "HEAD:keep.txt"], cwd=repo).stdout.decode().strip()
    # Derive the post-delete root tree hash without writing that tree object.
    # The helper must materialize it from the exact applied index.
    candidate_tree = git_tree("100644", "keep.txt", keep_oid)
    run(["git", "restore", "--worktree", "generated.bin"], cwd=repo)
    absent = run(["git", "cat-file", "-e", f"{candidate_tree}^{{tree}}"], cwd=repo, expected=None)
    require(absent.returncode != 0, "candidate tree remained present before absent-object application probe")
    identity = {"head": head, "base_tree": base_tree, "candidate_tree": candidate_tree, "patch": str(patch), "patch_sha": patch_sha}
    run(tx(repo, identity, "apply"))
    require(run(["git", "cat-file", "-e", f"{candidate_tree}^{{tree}}"], cwd=repo, expected=None).returncode == 0, "application did not materialize the candidate tree object")
    require(not binary.exists(), "binary deletion was not applied")
    run(tx(repo, identity, "rollback"))
    require(binary.exists(), "binary deletion rollback did not restore the file")
    require((binary.stat().st_mode & 0o777) == 0o755, "binary deletion rollback did not restore executable mode")
    require(run(["git", "write-tree"], cwd=repo).stdout.decode().strip() == base_tree, "binary rollback did not restore exact base tree")
    return 1


def corrupt_recovery_probe(tmp: Path) -> int:
    expected_payload = b"good\n"
    corrupt_payload = b"evil\n"
    oid = git_blob(expected_payload)
    tree = git_tree("100644", "a.txt", oid)
    manifest = {
        "schema_id": "x64lens-candidate-source-tree-v1",
        "candidate_tree": tree,
        "directories": [],
        "files": [{
            "path": "a.txt", "type": "blob", "git_oid": oid, "git_mode": "100644",
            "mode": "0644", "sha256": hashlib.sha256(expected_payload).hexdigest(),
            "size_bytes": len(expected_payload),
        }],
    }
    manifest_path = tmp / "corrupt-manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    archive = tmp / "corrupt.tar.gz"
    info = tarfile.TarInfo("a.txt"); info.size = len(corrupt_payload); info.mode = 0o644
    with tarfile.open(archive, "w:gz") as tar:
        tar.addfile(info, io.BytesIO(corrupt_payload))
    destination = tmp / "corrupt-result"
    cp = run([sys.executable, str(RECOVERY), "--archive", str(archive), "--manifest", str(manifest_path), "--destination", str(destination)], expected=None)
    require(cp.returncode == 1 and b"SHA-256 disagrees" in cp.stderr, "same-size corrupt source member was not rejected")
    require(not destination.exists(), "corrupt recovery published a destination")
    require(not list(tmp.glob(".x64lens-recovery-*")), "corrupt recovery left stage/quarantine/delete residue")
    return 1


def docker_expected_tree_probe(tmp: Path) -> int:
    repo = tmp / "docker-tree"
    repo.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=repo)
    run(["git", "config", "user.name", "regression"], cwd=repo)
    run(["git", "config", "user.email", "regression@example.invalid"], cwd=repo)
    (repo / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    (repo / "a.txt").write_text("base\n", encoding="utf-8")
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-qm", "base"], cwd=repo)
    base_tree = run(["git", "write-tree"], cwd=repo).stdout.decode().strip()
    (repo / "a.txt").write_text("candidate\n", encoding="utf-8")
    run(["git", "add", "a.txt"], cwd=repo)
    context = tmp / "wrong-context"
    cp = run([sys.executable, str(GITLESS), "create-context", "--repo", str(repo), "--context", str(context), "--expected-candidate-tree", base_tree], expected=None)
    require(cp.returncode == 1 and b"differs from expected candidate tree" in cp.stderr, "Docker context accepted a foreign candidate tree")
    require(not context.exists(), "wrong-tree Docker preflight left a context residue")
    return 1


def natural_authority_probe(tmp: Path) -> tuple[int, int, int]:
    module = load_module("p084_natural", NATURAL)
    authority = module.load_json(ROOT / "benchmarks/task-definitions/sprint13-natural-positive-coordinate-v1.json")
    module.validate_authority(authority)
    mutations = []
    for path, value in (
        (("campaign_id",), "foreign"),
        (("relation_id",), "foreign"),
        (("selection", "target_rule"), "last eligible path"),
        (("execution", "timeout_seconds"), 121),
        (("execution", "stdout_limit_bytes"), 1),
        (("qualification", "positive_targets_required"), 1),
        (("qualification", "control_total"), 107),
        (("qualification", "terminal_states"), ["qualified"]),
    ):
        changed = json.loads(json.dumps(authority))
        cursor = changed
        for key in path[:-1]: cursor = cursor[key]
        cursor[path[-1]] = value
        mutations.append(changed)
    rejected = 0
    for changed in mutations:
        try: module.validate_authority(changed)
        except module.CampaignError: rejected += 1
        else: raise RegressionError("natural authority mutation was accepted")
    require(rejected == 8, "natural authority mutation denominator changed")

    target_records: dict[str, dict[str, Any]] = {}
    outcomes: dict[str, dict[str, Any]] = {}
    for role in module.ROLES:
        for slot in range(1, 5):
            target_id = f"{role}-{slot}"
            target = {
                "target_id": target_id,
                "role": role,
                "sha256": hashlib.sha256(target_id.encode()).hexdigest(),
            }
            target_records[target_id] = target
            outcomes[target_id] = {
                "target": target,
                "tools": {name: {} for name in ("x64lens", *module.BASELINES)},
            }
    cells=[]
    states=["insufficient"]*5+["unavailable"]*4
    index = 0
    for baseline in module.BASELINES:
        for role in module.ROLES:
            status = "insufficient_relation_evidence" if states[index] == "insufficient" else "unavailable"
            observations = [
                {
                    "target_id": target_id,
                    "target_sha256": target_records[target_id]["sha256"],
                    "status": status,
                }
                for target_id in sorted(
                    (item for item, target in target_records.items() if target["role"] == role),
                    key=os.fsencode,
                )
            ]
            cells.append(module.cell_result(baseline, role, observations))
            index += 1
    result={
        "selection_freeze":{"selected_count":12,"role_counts":{role:4 for role in module.ROLES}},
        "execution_count":48,"complete_execution_denominator":48,"outcomes":outcomes,"cells":cells,
        "cell_counts":{state:sum(cell["terminal_state"] == state for cell in cells) for state in ("qualified","insufficient","unavailable","mismatch","ambiguous")},
        "control_count":sum(len(cell["controls"]) for cell in cells),
    }
    module.require_structural_complete(result)
    try: module.require_acceptance_complete(result)
    except module.CampaignError: acceptance_rejected=1
    else: raise RegressionError("zero-qualified natural campaign satisfied acceptance completion")

    repo = tmp / "natural-source"
    repo.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=repo)
    run(["git", "config", "user.name", "regression"], cwd=repo)
    run(["git", "config", "user.email", "regression@example.invalid"], cwd=repo)
    (repo / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    run(["git", "add", "."], cwd=repo); run(["git", "commit", "-qm", "base"], cwd=repo)
    tree=run(["git", "write-tree"],cwd=repo).stdout.decode().strip()
    source_root=tmp/"source-root"; source_manifest=tmp/"source-manifest.json"
    run([sys.executable,str(GITLESS),"create","--repo",str(repo),"--root",str(source_root),"--manifest",str(source_manifest),"--expected-candidate-tree",tree])
    bound=module.authenticate_source_authority(source_root,source_manifest,tree)
    require(bound["candidate_tree"]==tree and len(bound["source_manifest_sha256"])==64,"natural source binding missing")
    try: module.authenticate_source_authority(source_root,source_manifest,"0"*40)
    except module.CampaignError: source_rejected=1
    else: raise RegressionError("natural campaign accepted a foreign source tree")
    return rejected, acceptance_rejected, source_rejected


def docker_contract_probe() -> tuple[int, int]:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    script = (ROOT / "tools/docker-run-root-smoke.sh").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    require("chown -R ubuntu:ubuntu /work" not in dockerfile, "Dockerfile still grants runtime ownership of /work")
    require("test ! -w /work" in script and "find /work -type f -writable" in script and 'X64LENS_RUN_ROOT_ATTEMPT="$attempt"' in script, "dynamic Docker read-only/source loop contract missing")
    require("--expected-candidate-tree \"$$expected_tree\"" in makefile and 'test "$$tree" = "$$expected_tree"' in makefile, "Docker Make path is not bound to expected candidate tree")
    return 1,1


def source_state_probe() -> int:
    generated = "tests/toy-src/gadgets_sprint13_ordered_pairs"
    ignore_lines = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    require(generated in ignore_lines or f"/{generated}" in ignore_lines,
            "generated ordered-pair binary is not ignored")
    git_probe = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=ROOT, expected=None)
    if git_probe.returncode == 0:
        cp=run(["git","check-ignore","-q",generated],cwd=ROOT,expected=None)
        require(cp.returncode==0,"generated ordered-pair binary is not ignored")
        cp2=run(["git","ls-files","--error-unmatch",generated],cwd=ROOT,expected=None)
        require(cp2.returncode!=0,"generated ordered-pair binary remains tracked")
        return 1

    manifest_raw = os.environ.get("X64LENS_SOURCE_MANIFEST", "/x64lens-source-manifest.json")
    root_raw = os.environ.get("X64LENS_SOURCE_AUTHORITY_ROOT", os.fspath(ROOT))
    manifest_path = Path(manifest_raw)
    source_root = Path(root_raw)
    require(manifest_path.is_file(), "Git-less generated-source check requires X64LENS_SOURCE_MANIFEST")
    helper = load_module("p084_gitless_source_state", GITLESS)
    manifest = helper.load_manifest(manifest_path)
    helper.verify(source_root, manifest)
    require(generated not in {item["path"] for item in manifest["files"]},
            "generated ordered-pair binary remains in Git-less source authority")
    return 1

def shell_contract_probe() -> int:
    text=(ROOT/"tools/docker-run-root-smoke.sh").read_text(encoding="utf-8")
    require('for attempt in 1 2; do' in text and 'X64LENS_RUN_ROOT_ATTEMPT="$attempt"' in text,"Docker attempt loop variable remains unused")
    return 1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-p084-corrective-") as raw:
        tmp=Path(raw)
        post_apply,post_rollback=post_effect_binding_probe(tmp)
        binary_rollback=executable_binary_rollback_probe(tmp)
        corrupt=corrupt_recovery_probe(tmp)
        docker_tree=docker_expected_tree_probe(tmp)
        authority,acceptance,source=natural_authority_probe(tmp)
    docker_readonly,docker_make=docker_contract_probe()
    source_state=source_state_probe()
    shell=shell_contract_probe()
    print(
        "patch083-corrective-regression-smoke: ok "
        f"post_apply_parent={post_apply} post_rollback_parent={post_rollback} "
        f"binary_mode_rollback={binary_rollback} recovery_corrupt_cleanup={corrupt} docker_expected_tree={docker_tree} "
        f"natural_authority_mutations={authority} natural_acceptance_rejected={acceptance} natural_source_binding={source} "
        f"docker_source_readonly={docker_readonly} docker_make_binding={docker_make} generated_source_removed={source_state} shellcheck_attempt={shell} "
        "cloud_evidence_self_seal=delivery_gate loose_delivery=delivery_gate"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"patch083-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
