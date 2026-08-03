#!/usr/bin/env python3
"""Regress the independently confirmed Patch 072 acceptance defects.

The probes cover post-fingerprint cleanup substitution, immutable selection
freeze enforcement, root/directory/manifest mode custody, descriptor-bound
file/path identity, container-plane write isolation and retained-result
requirements, stale custody schemas, and public-policy authorization with open
prerequisites.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_AUTHORITY = ROOT / "benchmarks/task-definitions/sprint12-role-property-public-policy-v1.json"


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
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def cleanup_post_fingerprint_substitution(cleanup: Any, base: Path, kind: str) -> None:
    owned = base / "owned"
    if kind == "file":
        owned.mkdir()
        (owned / "victim").write_bytes(b"owned-file\n")
    elif kind == "directory":
        (owned / "child").mkdir(parents=True)
    elif kind == "root":
        owned.mkdir()
    else:
        raise AssertionError(kind)
    identity = cleanup.parse_identity(cleanup.identify(owned))
    escaped = base / "escaped-owned"
    state: dict[str, Any] = {"fired": False, "foreign_name": None}

    def substitute(parent_fd: int, name: str, directory: bool) -> None:
        target = (kind == "file" and not directory) or (kind in {"directory", "root"} and directory)
        if state["fired"] or not target:
            return
        state["fired"] = True
        state["foreign_name"] = name
        os.rename(name, escaped, src_dir_fd=parent_fd)
        if directory:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        else:
            fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
            try:
                os.write(fd, b"foreign-file\n")
            finally:
                os.close(fd)

    cleanup._TEST_PRE_UNLINK_RECHECK_HOOK = substitute
    rejected = False
    try:
        cleanup.remove(owned, identity)
    except cleanup.CleanupError:
        rejected = True
    finally:
        cleanup._TEST_PRE_UNLINK_RECHECK_HOOK = None
    require(state["fired"] and rejected, f"post-fingerprint {kind} substitution was accepted")
    require(escaped.exists(), f"owned {kind} object was not preserved")
    foreign_name = state["foreign_name"]
    require(isinstance(foreign_name, str), "missing foreign quarantine name")
    foreign_candidates = [path for path in base.rglob("*") if path.name == foreign_name]
    require(foreign_candidates, f"foreign {kind} replacement was deleted")


def selection_freeze_mutation(external: Any, base: Path) -> None:
    staging = base / "selection"
    objects = staging / "objects"
    objects.mkdir(parents=True)
    (objects / "object-00.elf").write_bytes(b"ELF-object\n")
    (objects / "object-00.elf").chmod(0o444)
    (staging / "selection-candidates.tsv").write_text("name\nobject-00.elf\n", encoding="utf-8")
    (staging / "selection.tsv").write_text("name\nobject-00.elf\n", encoding="utf-8")
    frozen = {
        "authority_id": "test",
        "authority_identity": {},
        "acquisition_harness_identity": {},
        "selection_rule": {},
        "selection_metadata": {},
        "selection_candidates_sha256": external.sha256_bytes((staging / "selection-candidates.tsv").read_bytes()),
        "selection_sha256": external.sha256_bytes((staging / "selection.tsv").read_bytes()),
        "selected_objects": {
            "object-00.elf": external.retained_identity(objects / "object-00.elf", "object")
        },
        "outcomes_inspected": False,
    }
    freeze_path = staging / "selection-freeze.json"
    freeze_path.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for path in (staging / "selection-candidates.tsv", staging / "selection.tsv", freeze_path):
        path.chmod(0o444)
    freeze_sha = external.sha256_bytes(freeze_path.read_bytes())
    external.assert_selection_freeze(staging, frozen, freeze_sha, checkpoint="nominal")
    (staging / "selection.tsv").chmod(0o644)
    with (staging / "selection.tsv").open("a", encoding="utf-8") as stream:
        stream.write("mutated\n")
    try:
        external.assert_selection_freeze(staging, frozen, freeze_sha, checkpoint="post-freeze-mutation")
    except external.AcquisitionError:
        pass
    else:
        raise RegressionError("post-freeze selection mutation was accepted")


def custody_mode_and_schema(custody: Any, base: Path) -> None:
    root = base / "delivery"
    nested = root / "records"
    nested.mkdir(parents=True)
    root.chmod(0o755)
    nested.chmod(0o750)
    payload = nested / "payload.bin"
    payload.write_bytes(b"payload\n")
    payload.chmod(0o640)
    manifest = root / "DELIVERY_CUSTODY_MANIFEST.json"
    value = custody.create(root, manifest, "test-delivery")
    require(value["schema_id"] == "x64lens-delivery-custody-v2", "custody v2 was not created")
    custody.verify(root, manifest)

    for target, mode, label in (
        (root, 0o777, "root"),
        (nested, 0o777, "directory"),
        (manifest, 0o777, "manifest"),
    ):
        original = stat.S_IMODE(target.stat().st_mode)
        target.chmod(mode)
        try:
            custody.verify(root, manifest)
        except custody.CustodyError:
            pass
        else:
            raise RegressionError(f"delivery {label} mode mutation was accepted")
        target.chmod(original)
        custody.verify(root, manifest)

    stale = root / "stale-v1.json"
    stale.write_text(json.dumps({"schema_id": "x64lens-delivery-custody-v1", "root_label": "stale", "files": []}) + "\n")
    stale.chmod(0o444)
    try:
        custody.verify(root, stale)
    except custody.CustodyError:
        pass
    else:
        raise RegressionError("stale delivery-custody v1 authority was accepted")
    stale.unlink()


def custody_path_substitution(custody: Any, base: Path) -> None:
    root = base / "delivery-race"
    root.mkdir()
    root.chmod(0o755)
    payload = root / "payload.bin"
    payload.write_bytes(b"same-size\n")
    payload.chmod(0o644)
    manifest = root / "DELIVERY_CUSTODY_MANIFEST.json"
    custody.create(root, manifest, "race-delivery")
    escaped = root / "payload-owned.bin"
    fired = False

    def substitute(parent_fd: int, name: str, relative: str) -> None:
        nonlocal fired
        if fired or relative != "payload.bin":
            return
        fired = True
        os.rename(name, escaped.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644, dir_fd=parent_fd)
        try:
            os.write(fd, b"same-size\n")
        finally:
            os.close(fd)

    custody._TEST_AFTER_FILE_HASH_HOOK = substitute
    rejected = False
    try:
        custody.verify(root, manifest)
    except custody.CustodyError:
        rejected = True
    finally:
        custody._TEST_AFTER_FILE_HASH_HOOK = None
    require(fired and rejected, "post-hash same-size pathname substitution was accepted")
    require(escaped.read_bytes() == b"same-size\n" and payload.read_bytes() == b"same-size\n",
            "custody substitution probe lost an object")


def parity_plane_isolation(parity: Any, base: Path) -> None:
    inputs = base / "inputs"
    heldout = base / "heldout"
    writable = base / "container-write"
    native = base / "native"
    for path in (inputs, heldout, writable, native):
        path.mkdir()
    command = parity.build_container_command(
        docker="/usr/bin/docker",
        image="x64lens-dev",
        inputs=inputs,
        heldout=heldout,
        container_write_root=writable,
    )
    policy = parity.validate_container_mount_policy(
        command,
        native_result=native,
        container_write_root=writable,
    )
    require(policy["writable_mount_count"] == 1 and policy["native_plane_exposed_to_container"] is False,
            "nominal parity isolation policy disagrees")
    bad = list(command)
    bad[bad.index("-w"):bad.index("-w")] = ["-v", f"{native}:/native:rw"]
    try:
        parity.validate_container_mount_policy(bad, native_result=native, container_write_root=writable)
    except parity.ParityError:
        pass
    else:
        raise RegressionError("native evidence plane write mount was accepted")

    parser = parity.build_parser()
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parser.parse_args([
                "run", "--heldout-authority", "a", "--provisional-corpus", "b",
                "--analyzer", "c", "--schema", "d", "--fact-probe", "e",
                "--docker-image", "image",
            ])
    except SystemExit as exc:
        require(exc.code != 0, "missing retained parity result unexpectedly succeeded")
    else:
        raise RegressionError("parity run accepted no retained result directory")


def policy_authorization_mutation(policy: Any, base: Path) -> None:
    nominal = policy.evaluate(POLICY_AUTHORITY)
    require(nominal["decision"] == "defer" and nominal["authorization"] is False,
            "nominal public-policy deferral disagrees")
    value = json.loads(POLICY_AUTHORITY.read_text(encoding="utf-8"))
    value["decision"] = "authorize"
    value["authorization_rule"]["current_authorization"] = True
    value["authorization_rule"]["public_fields_added"] = 3
    mutated = base / "authorize-with-open-prerequisites.json"
    mutated.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    try:
        policy.evaluate(mutated)
    except policy.PolicyError:
        pass
    else:
        raise RegressionError("public role/property fields were authorized with open prerequisites")


def main() -> int:
    cleanup = load("p073_cleanup_regression", "tools/remove-owned-tree.py")
    custody = load("p073_custody_regression", "tools/verify-delivery-custody.py")
    external = load("p073_external_regression", "tools/sprint12-external-natural-acquisition-smoke.py")
    parity = load("p073_parity_regression", "tools/sprint12-role-property-environment-parity-smoke.py")
    policy = load("p073_policy_regression", "tools/sprint12-role-property-public-policy-smoke.py")
    with tempfile.TemporaryDirectory(prefix="x64lens-p073-corrective-") as raw:
        base = Path(raw)
        for kind in ("file", "directory", "root"):
            target = base / f"cleanup-{kind}"
            target.mkdir()
            cleanup_post_fingerprint_substitution(cleanup, target, kind)
        selection_freeze_mutation(external, base)
        custody_mode_and_schema(custody, base)
        custody_path_substitution(custody, base)
        parity_plane_isolation(parity, base)
        policy_authorization_mutation(policy, base)
    print(
        "patch072-corrective-regression-smoke: ok "
        "cleanup_post_fingerprint_file=1 cleanup_post_fingerprint_directory=1 "
        "cleanup_post_fingerprint_root=1 selection_freeze_mutation=1 "
        "custody_root_mode=1 custody_directory_mode=1 custody_manifest_mode=1 "
        "custody_path_toctou=1 custody_v1_rejected=1 parity_write_isolation=1 "
        "parity_retention_required=1 policy_open_prerequisite_rejected=1"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RegressionError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"patch072-corrective-regression-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
