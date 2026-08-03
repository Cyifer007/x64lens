#!/usr/bin/env python3
"""Regress the material findings returned by the Patch 073 review.

The smoke covers descriptor-retained delivery custody, hard-link and root-path
binding, exact parity-tree membership and executable modes, native-plane mount
isolation, selection-freeze inode identity, tracked-only permission
normalization, deferral-only public policy, strict mitigation-gap types, and
fail-closed cleanup when an owned root disappears from its authenticated name.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class RegressionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegressionError(message)


def load(name: str, relative: str) -> Any:
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def same_byte_replace(path: Path) -> None:
    data = path.read_bytes()
    mode = stat.S_IMODE(path.stat().st_mode)
    replacement = path.with_name(path.name + ".replacement")
    replacement.write_bytes(data)
    replacement.chmod(mode)
    os.replace(replacement, path)


def cleanup_root_disappearance(cleanup: Any, base: Path) -> None:
    owned = base / "owned"
    owned.mkdir()
    (owned / "payload").write_text("owned\n")
    token = cleanup.parse_identity(cleanup.identify(owned))
    moved = base / "moved"
    owned.rename(moved)
    try:
        cleanup.remove(owned, token)
    except cleanup.CleanupError as exc:
        require("disappeared" in str(exc), "cleanup disappearance diagnostic changed")
    else:
        raise RegressionError("renamed-away owned root was accepted as successful cleanup")
    require((moved / "payload").read_text() == "owned\n", "renamed-away payload was deleted")
    cleanup.remove(moved, token)
    require(not moved.exists(), "authenticated moved root could not be cleaned")


def custody_regressions(custody: Any, base: Path) -> None:
    root = base / "delivery"
    (root / "sub").mkdir(parents=True)
    payload = root / "sub" / "payload.bin"
    payload.write_bytes(b"AAAA")
    payload.chmod(0o644)
    manifest = root / "manifest.json"
    custody.create(root, manifest, "delivery-label")
    custody.verify(root, manifest)

    original_hook = custody._TEST_AFTER_TREE_SCAN_HOOK
    try:
        fired = False

        def mutate(_root: Path) -> None:
            nonlocal fired
            if fired:
                return
            fired = True
            same_byte_replace(payload)

        custody._TEST_AFTER_TREE_SCAN_HOOK = mutate
        try:
            custody.verify(root, manifest)
        except custody.CustodyError:
            pass
        else:
            raise RegressionError("late same-byte subtree replacement passed custody")
    finally:
        custody._TEST_AFTER_TREE_SCAN_HOOK = original_hook

    # Recreate a clean tree for topology and root-binding tests.
    shutil.rmtree(root)
    (root / "sub").mkdir(parents=True)
    (root / "sub" / "payload.bin").write_bytes(b"BBBB")
    custody.create(root, manifest, "delivery-label")
    custody.verify(root, manifest)

    manifest.chmod(0o644)
    value = json.loads(manifest.read_text())
    value["root_label"] = "foreign-label"
    manifest.write_text(json.dumps(value, indent=2) + "\n")
    manifest.chmod(0o444)
    try:
        custody.verify(root, manifest)
    except custody.CustodyError:
        pass
    else:
        raise RegressionError("root-label disagreement passed custody")

    # Root basename is part of schema v3 and must not survive rename.
    manifest.chmod(0o644)
    value["root_label"] = "delivery-label"
    manifest.write_text(json.dumps(value, indent=2) + "\n")
    manifest.chmod(0o444)
    renamed = base / "renamed-delivery"
    root.rename(renamed)
    try:
        custody.verify(renamed, renamed / "manifest.json")
    except custody.CustodyError:
        pass
    else:
        raise RegressionError("renamed custody root passed basename binding")

    # A symlink in any root ancestor is rejected before traversal.
    real_parent = base / "real-parent"
    real_root = real_parent / "root"
    real_root.mkdir(parents=True)
    (real_root / "payload").write_text("value\n")
    real_manifest = real_root / "manifest.json"
    custody.create(real_root, real_manifest, "real")
    alias = base / "alias-parent"
    alias.symlink_to(real_parent, target_is_directory=True)
    try:
        custody.verify(alias / "root", alias / "root" / "manifest.json")
    except (custody.CustodyError, OSError):
        pass
    else:
        raise RegressionError("symlinked custody ancestor passed verification")

    missing_root = base / "missing-parent"
    missing_root.mkdir()
    (missing_root / "payload").write_text("value\n")
    try:
        custody.create(missing_root, missing_root / "nested" / "manifest.json", "missing")
    except (custody.CustodyError, OSError):
        pass
    else:
        raise RegressionError("custody create manufactured an undeclared manifest parent")
    require(not (missing_root / "nested").exists(), "failed nested custody create left a directory")

    hard_root = base / "hardlink"
    hard_root.mkdir()
    source = hard_root / "source"
    source.write_text("value\n")
    os.link(source, hard_root / "alias")
    try:
        custody.create(hard_root, hard_root / "manifest.json", "hardlink")
    except custody.CustodyError:
        pass
    else:
        raise RegressionError("hard-linked payload topology passed custody")


def parity_regressions(parity: Any, base: Path) -> None:
    tree = base / "parity-tree"
    (tree / "tools").mkdir(parents=True)
    (tree / "data.txt").write_text("data\n")
    executable = tree / "tools" / "probe.py"
    executable.write_text("#!/usr/bin/env python3\n")
    executable.chmod(0o755)
    parity.seal_tree(tree)
    parity.verify_checksums(tree)
    require(stat.S_IMODE(executable.stat().st_mode) == 0o555,
            "parity sealing removed executable authority")

    tree.chmod(0o755)
    (tree / "foreign-link").symlink_to("data.txt")
    tree.chmod(0o555)
    try:
        parity.verify_checksums(tree)
    except parity.ParityError:
        pass
    else:
        raise RegressionError("undeclared parity symlink passed exact custody")

    fifo_tree = base / "fifo-tree"
    fifo_tree.mkdir()
    os.mkfifo(fifo_tree / "pipe")
    try:
        parity.seal_tree(fifo_tree)
    except parity.ParityError:
        pass
    else:
        raise RegressionError("parity special member passed sealing")

    nested = base / "nested-tree"
    child = nested / "child"
    child.mkdir(parents=True)
    (child / "value").write_text("value\n")
    parity.seal_tree(child)
    parity.seal_tree(nested)
    parity.verify_checksums(nested)
    top = (nested / parity.CHECKSUM_NAME).read_text()
    require("child/SHA256SUMS.txt" in top and "child/TREE_CUSTODY.json" in top,
            "top parity checksum omitted nested checksum authorities")

    mount = base / "mount-policy"
    inputs = mount / "inputs"
    heldout = mount / "heldout"
    output = mount / "output"
    native = mount / "native"
    for path in (inputs, heldout, output, native):
        path.mkdir(parents=True)
    valid = parity.build_container_command(
        docker="docker", image="image", inputs=inputs, heldout=heldout, container_write_root=output
    )
    policy = parity.validate_container_mount_policy(
        valid, native_result=native, inputs=inputs, heldout=heldout, container_write_root=output
    )
    require(policy["covering_native_mount_count"] == 0, "valid parity mount policy changed")
    bad = valid[:]
    image_index = bad.index("image")
    bad[image_index:image_index] = ["-v", f"{mount}:/work:ro"]
    try:
        parity.validate_container_mount_policy(
            bad, native_result=native, inputs=inputs, heldout=heldout, container_write_root=output
        )
    except parity.ParityError:
        pass
    else:
        raise RegressionError("ancestor mount covering the native plane passed parity policy")

    # Rehearse the required WSL2 publication mode transition locally.
    publication = base / "publication"
    write_root = publication / "output"
    plane = write_root / "plane"
    plane.mkdir(parents=True)
    (plane / "value").write_text("value\n")
    parity.seal_tree(plane)
    parity.verify_checksums(plane)
    before = plane.lstat()
    write_root.chmod(0o700)
    plane.chmod(0o700)
    published = publication / "container"
    plane.rename(published)
    published.chmod(0o555)
    require((published.lstat().st_dev, published.lstat().st_ino) == (before.st_dev, before.st_ino),
            "container-plane identity changed across publication")
    parity.verify_checksums(published)


def selection_freeze_regression(acquisition: Any, base: Path) -> None:
    staging = base / "selection"
    (staging / "objects").mkdir(parents=True)
    for name, data in (("selection-candidates.tsv", b"candidate\n"), ("selection.tsv", b"selected\n")):
        path = staging / name
        path.write_bytes(data)
        path.chmod(0o444)
    obj = staging / "objects" / "object.elf"
    obj.write_bytes(b"ELF")
    obj.chmod(0o444)
    candidates = acquisition.retained_identity(staging / "selection-candidates.tsv", "candidates")
    selection = acquisition.retained_identity(staging / "selection.tsv", "selection")
    frozen: dict[str, Any] = {
        "selection_candidates_sha256": candidates["sha256"],
        "selection_sha256": selection["sha256"],
        "selected_objects": {"object.elf": acquisition.retained_identity(obj, "object")},
    }
    freeze_path = staging / "selection-freeze.json"
    freeze_path.write_text(json.dumps(frozen, sort_keys=True) + "\n")
    freeze_path.chmod(0o444)
    freeze_identity = acquisition.retained_identity(freeze_path, "freeze")
    runtime = {
        "selection_candidates": candidates,
        "selection": selection,
        "selection_freeze": freeze_identity,
    }
    same_byte_replace(obj)
    try:
        acquisition.assert_selection_freeze(
            staging, frozen, freeze_identity["sha256"], runtime, checkpoint="same-byte-replacement"
        )
    except acquisition.AcquisitionError:
        pass
    else:
        raise RegressionError("same-byte selected-object inode replacement passed freeze custody")


def normalization_regression(normalizer: Any, base: Path) -> None:
    repo = base / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text("ignored.pyc\n")
    script = repo / "script.sh"
    data = repo / "data.txt"
    script.write_text("#!/bin/sh\nexit 0\n")
    data.write_text("data\n")
    script.chmod(0o755)
    data.chmod(0o644)
    subprocess.run(["git", "-C", str(repo), "add", ".gitignore", "script.sh", "data.txt"], check=True)
    script.chmod(0o644)
    data.chmod(0o666)
    ignored = repo / "ignored.pyc"
    ignored.write_bytes(b"ignored")
    ignored.chmod(0o600)
    ignored_before = ignored.lstat()
    changed_files, _changed_dirs = normalizer.normalize(repo)
    require(changed_files == 2, "tracked normalization change denominator changed")
    require(stat.S_IMODE(script.stat().st_mode) == 0o755 and stat.S_IMODE(data.stat().st_mode) == 0o644,
            "tracked modes were not normalized from Git authority")
    ignored_after = ignored.lstat()
    require((ignored_after.st_ino, stat.S_IMODE(ignored_after.st_mode), ignored_after.st_mtime_ns)
            == (ignored_before.st_ino, stat.S_IMODE(ignored_before.st_mode), ignored_before.st_mtime_ns),
            "tracked normalization touched an ignored file")


def authority_regressions(policy: Any, base: Path) -> None:
    policy_source = ROOT / "benchmarks/task-definitions/sprint12-role-property-public-policy-v1.json"
    value = json.loads(policy_source.read_text())
    value["decision"] = "authorize"
    value["authorization_rule"]["current_authorization"] = True
    value["authorization_rule"]["open_or_pending_required_prerequisite_count"] = 0
    value["authorization_rule"]["public_fields_added"] = 3
    for item in value["prerequisites"]:
        if item["required_for_authorization"]:
            item["status"] = "passed"
    mutated_policy = base / "authorize.json"
    mutated_policy.write_text(json.dumps(value) + "\n")
    try:
        policy.evaluate(mutated_policy)
    except policy.PolicyError:
        pass
    else:
        raise RegressionError("v1 policy authority authorized fields without a new reviewed gate")

    gap_source = ROOT / "benchmarks/task-definitions/sprint12-mitigation-competitive-gap-v1.json"
    gap = json.loads(gap_source.read_text())
    gap["current_private_or_deferred"].append(dict(gap["current_private_or_deferred"][0]))
    gap["prioritized_gap_tranches"][0]["priority"] = True
    gap["prioritized_gap_tranches"][0]["selected_for_next_bounded_mitigation_tranche"] = "yes"
    gap["patch_073_disposition"]["runtime_fields_added"] = False
    mutated_gap = base / "gap.json"
    mutated_gap.write_text(json.dumps(gap) + "\n")
    cp = subprocess.run(
        [sys.executable, str(ROOT / "tools/sprint12-mitigation-competitive-gap-smoke.py"),
         "--authority", str(mutated_gap)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(cp.returncode != 0, "wrong-type or duplicate mitigation-gap authority passed")


def main() -> int:
    cleanup = load("p074_cleanup", "tools/remove-owned-tree.py")
    custody = load("p074_custody", "tools/verify-delivery-custody.py")
    parity = load("p074_parity", "tools/sprint12-role-property-environment-parity-smoke.py")
    acquisition = load("p074_acquisition", "tools/sprint12-external-natural-acquisition-smoke.py")
    normalizer = load("p074_normalizer", "tools/normalize-tracked-permissions.py")
    policy = load("p074_policy", "tools/sprint12-role-property-public-policy-smoke.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p074-corrective-") as raw:
        base = Path(raw)
        for name in ("cleanup", "custody", "parity", "selection", "normalize", "authority"):
            (base / name).mkdir()
        cleanup_root_disappearance(cleanup, base / "cleanup")
        custody_regressions(custody, base / "custody")
        parity_regressions(parity, base / "parity")
        selection_freeze_regression(acquisition, base / "selection")
        normalization_regression(normalizer, base / "normalize")
        authority_regressions(policy, base / "authority")
    print(
        "patch073-corrective-regression-smoke: ok "
        "cleanup_missing_root=1 custody_late_subtree=1 custody_hardlink=1 "
        "custody_root_binding=2 custody_symlink_ancestor=1 custody_nested_parent=1 "
        "parity_executable=1 parity_symlink=1 parity_special=1 parity_nested_checksums=1 "
        "parity_mount_isolation=1 parity_publication=1 selection_inode=1 "
        "normalize_tracked_only=1 policy_authorize=1 gap_types_duplicates=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"patch073-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
