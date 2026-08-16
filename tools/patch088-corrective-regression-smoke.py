#!/usr/bin/env python3
"""Exercise the complete Patch 088 corrective boundary promoted by Patch 089."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class RegressionError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RegressionError(message)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect_failure(callable_value, label: str) -> None:
    try:
        callable_value()
    except Exception:
        return
    raise RegressionError(f"negative oracle accepted: {label}")


def replay_checks() -> tuple[int, int]:
    replay = load_module("p089_replay", ROOT / "tools/sprint13-natural-frozen-replay-v2-smoke.py")
    attr = load_module("p089_attr", ROOT / "tools/sprint13-natural-terminal-attribution-v2-smoke.py")
    authority_path = ROOT / "benchmarks/task-definitions/sprint13-natural-frozen-replay-v2.json"
    authority = load(authority_path)
    attr.validate_authority(authority)
    predecessor = replay.predecessor_authority(authority)
    expected = authority["input_authority"]["tool_identities"]
    require(predecessor["tools"] == expected, "replay did not project predecessor byte identities")
    require(predecessor["tools"]["x64lens"]["sha256"]
            == "39f6af5c7991b6fd7d46b7ac1afb6340164cee14cfcec2d7cd0a2f014bf1222e",
            "predecessor x64lens byte identity changed")
    changed = copy.deepcopy(authority)
    changed["runtime_authority"]["python_launchers"]["ropgadget"]["package_closures"][0]["closure_sha256"] = "0" * 64
    expect_failure(lambda: attr.validate_authority(changed), "Python closure digest")
    return 1, 1


def split_checks() -> tuple[int, int, int, int]:
    split = load_module("p089_split", ROOT / "tools/sprint13-split-debug-packaging-smoke.py")
    authority_path = ROOT / "benchmarks/task-definitions/sprint13-split-debug-packaging-v1.json"
    expected_path = ROOT / "tests/expected/sprint13-split-debug-packaging-v1.json"
    authority, expected = load(authority_path), load(expected_path)
    split.validate_authority(authority, expected)
    duplicate_symbol = copy.deepcopy(authority)
    duplicate_symbol["known_symbols"][1] = duplicate_symbol["known_symbols"][0]
    expect_failure(lambda: split.validate_authority(duplicate_symbol, expected), "duplicate split symbol")
    duplicate_behavior = copy.deepcopy(authority)
    duplicate_behavior["behavior_profiles"][1]["args"] = list(duplicate_behavior["behavior_profiles"][0]["args"])
    duplicate_behavior["behavior_profiles"][1]["target"] = duplicate_behavior["behavior_profiles"][0]["target"]
    expect_failure(lambda: split.validate_authority(duplicate_behavior, expected), "duplicate split behavior")

    with tempfile.TemporaryDirectory(prefix="x64lens-p089-split-result-") as raw:
        root = Path(raw) / "result"
        root.mkdir(mode=0o755)
        payload = root / "payload"
        payload.write_bytes(b"original")
        payload.chmod(0o444)
        result = {
            "retained_directories": [],
            "retained_members": [{"path": "payload", "sha256": sha(payload),
                                  "size_bytes": payload.stat().st_size, "mode": "0444"}],
        }
        manifest = root / "manifest.json"
        manifest.write_text("{}\n", encoding="utf-8"); manifest.chmod(0o444)
        checksums = root / "SHA256SUMS.txt"
        checksums.write_text(f"{sha(manifest)}  manifest.json\n{sha(payload)}  payload\n", encoding="utf-8")
        checksums.chmod(0o444)
        split.verify_result_tree(root, result)
        payload.chmod(0o644); payload.write_bytes(b"substitute"); payload.chmod(0o444)
        checksums.write_text(f"{sha(manifest)}  manifest.json\n{sha(payload)}  payload\n", encoding="utf-8")
        checksums.chmod(0o444)
        expect_failure(lambda: split.verify_result_tree(root, result), "resealed split artifact substitution")
    return 1, 1, 1, 1


def workload_checks() -> tuple[int, int]:
    workload = load_module("p089_workload", ROOT / "tools/sprint13-workload-phase-attribution-smoke.py")
    authority = load(ROOT / "benchmarks/task-definitions/sprint13-workload-phase-attribution-v1.json")
    result = workload.synthetic_result(authority)
    require(workload.qualify(authority, result) == 8, "valid workload authority did not qualify")
    duplicate = copy.deepcopy(result)
    duplicate["fixtures"][1] = copy.deepcopy(duplicate["fixtures"][0])
    expect_failure(lambda: workload.qualify(authority, duplicate), "duplicate workload fixture")
    unknown = copy.deepcopy(result)
    unknown["fixtures"][0]["id"] = "unknown-fixture"
    expect_failure(lambda: workload.qualify(authority, unknown), "unknown workload fixture")
    return 1, 1


def recovery_checks() -> tuple[int, int, int, int]:
    recovery = load_module("p089_recovery", ROOT / "tools/recover-candidate-source.py")
    malformed = {"candidate_tree": "0" * 40, "directories": [{"path": [], "mode": "0755"}], "files": []}
    expect_failure(lambda: recovery.parse_manifest(malformed), "non-string recovery path")

    file_record = {
        "path": "large", "type": "blob", "git_oid": "0" * 40, "git_mode": "100644",
        "mode": "0644", "sha256": "0" * 64, "size_bytes": recovery.MAX_SOURCE_FILE_BYTES + 1,
    }
    too_large = {"candidate_tree": "0" * 40, "directories": [], "files": [file_record]}
    expect_failure(lambda: recovery.parse_manifest(too_large), "per-file recovery capacity")

    aggregate_files = []
    per = recovery.MAX_SOURCE_FILE_BYTES
    for index in range(recovery.MAX_SOURCE_TOTAL_BYTES // per + 1):
        aggregate_files.append({**file_record, "path": f"f{index}", "size_bytes": per,
                                "git_oid": f"{index + 1:040x}"[-40:]})
    aggregate = {"candidate_tree": "0" * 40, "directories": [], "files": aggregate_files}
    expect_failure(lambda: recovery.parse_manifest(aggregate), "aggregate recovery capacity")

    with tempfile.TemporaryDirectory(prefix="x64lens-p089-streaming-git-") as raw:
        path = Path(raw) / "payload"
        payload = (b"streaming-git-blob\n" * 100_000)
        path.write_bytes(payload)
        fd = os.open(path, os.O_RDONLY)
        try:
            observed_sha, observed_size, observed_oid = recovery.hash_fd(fd, len(payload))
        finally:
            os.close(fd)
        expected_oid = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
        require(observed_sha == hashlib.sha256(payload).hexdigest()
                and observed_size == len(payload) and observed_oid == expected_oid,
                "streaming source hash disagreed")
    return 1, 1, 1, 1


def main() -> int:
    predecessor, package_closure = replay_checks()
    split_symbol, split_behavior, split_reseal, split_authority = split_checks()
    workload_duplicate, workload_unknown = workload_checks()
    recovery_type, recovery_file, recovery_total, recovery_stream = recovery_checks()
    print(
        "patch088-corrective-regression-smoke: ok "
        f"replay_predecessor_identity={predecessor} python_record_closure={package_closure} "
        f"split_symbol_unique={split_symbol} split_behavior_distinct={split_behavior} "
        f"split_reseal_rejected={split_reseal} split_authority={split_authority} "
        f"workload_duplicate_rejected={workload_duplicate} workload_unknown_rejected={workload_unknown} "
        f"recovery_type_normalized={recovery_type} recovery_file_cap={recovery_file} "
        f"recovery_total_cap={recovery_total} recovery_streaming_git={recovery_stream}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegressionError as exc:
        print(f"patch088-corrective-regression-smoke: error: {exc}", file=__import__("sys").stderr)
        raise SystemExit(1)
