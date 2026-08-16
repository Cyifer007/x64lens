#!/usr/bin/env python3
"""Validate sealed P087 replay evidence and attribute terminal states by layer."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import signal
import stat
import sys
import tempfile
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint13-natural-frozen-replay-v2.json"
EXPECTED = ROOT / "tests/expected/sprint13-natural-terminal-attribution-v2.json"
TOOLS = ("x64lens", "ropgadget", "ropper", "ropr")
STATES = ("qualified", "insufficient", "unavailable", "mismatch", "ambiguous")
PINNED_PYTHON_LAUNCHERS: dict[str, Any] = {
    "ropgadget": {
        "invocation_suffix": ".local/share/pipx/venvs/ropgadget/bin/python",
        "resolved_interpreter": {
            "sha256": "1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118",
            "size_bytes": 8020928,
            "mode": "0755",
        },
        "package_closures": [
            {
                "distribution": "ROPGadget", "version": "7.7", "package_root": "ropgadget",
                "files": 20, "bytes": 128237,
                "closure_sha256": "65c8178aa6118b81da46409d09dae9edccae8823f8ee77f260372fa9dcda4319",
            },
            {
                "distribution": "capstone", "version": "5.0.9", "package_root": "capstone",
                "files": 38, "bytes": 10003152,
                "closure_sha256": "33691cb329bc89ef1828d9967202853d41a78e670a08a43b90497c7eb5acb033",
            },
        ],
    },
    "ropper": {
        "invocation_suffix": ".local/share/pipx/venvs/ropper/bin/python",
        "resolved_interpreter": {
            "sha256": "1643dacd9feaedc58f3cc581e4d22577dfe25c09b10282936186ccf0f2e61118",
            "size_bytes": 8020928,
            "mode": "0755",
        },
        "package_closures": [
            {
                "distribution": "ropper", "version": "1.13.13", "package_root": "ropper",
                "files": 34, "bytes": 363557,
                "closure_sha256": "b5372a3222b9086d45db49a11f544d874c810094b8832e5a038cef610bd07c7f",
            },
            {
                "distribution": "capstone", "version": "5.0.9", "package_root": "capstone",
                "files": 38, "bytes": 10003152,
                "closure_sha256": "33691cb329bc89ef1828d9967202853d41a78e670a08a43b90497c7eb5acb033",
            },
            {
                "distribution": "filebytes", "version": "0.10.2", "package_root": "filebytes",
                "files": 7, "bytes": 86137,
                "closure_sha256": "73ddfadfa6adad8d8bbbed549d58dc358bc6ad500f549e308b19f0a8bae0b02c",
            },
        ],
    },
}


class AttributionError(RuntimeError):
    pass


class CatchableTermination(AttributionError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise AttributionError(message)


def fail(message: str) -> NoReturn:
    print(f"sprint13-natural-terminal-attribution-v2-smoke: error: {message}", file=sys.stderr)
    raise SystemExit(1)


def strict(items: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in items:
        require(key not in out, f"duplicate JSON key: {key}")
        out[key] = value
    return out


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


@contextmanager
def signal_guard(label: str):
    guarded = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM)
    previous = {sig: signal.getsignal(sig) for sig in guarded}

    def handler(signum: int, _frame: object) -> None:
        for candidate in guarded:
            signal.signal(candidate, signal.SIG_IGN)
        raise CatchableTermination(f"{label} interrupted by {signal.Signals(signum).name}")

    for sig in guarded:
        signal.signal(sig, handler)
    try:
        yield
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)


@contextmanager
def defer_catchable_signals():
    previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGHUP, signal.SIGINT, signal.SIGTERM})
    try:
        yield
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous)


def safe_rel(value: str) -> str:
    require(isinstance(value, str) and value != "", "empty checksum path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and "\\" not in value, "unsafe checksum path")
    require(all(part not in {"", ".", ".."} for part in path.parts), "unsafe checksum path")
    return path.as_posix()


def checksum_map(root: Path) -> dict[str, str]:
    path = root / "SHA256SUMS.txt"
    require(path.is_file() and not path.is_symlink(), "replay checksum manifest missing")
    declared: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        require(len(line) >= 67 and line[64:66] == "  ", "malformed replay checksum row")
        digest, rel = line[:64], safe_rel(line[66:])
        require(all(char in "0123456789abcdef" for char in digest), "invalid checksum digest")
        require(rel not in declared and rel != "SHA256SUMS.txt", "duplicate/self checksum path")
        declared[rel] = digest
    actual: dict[str, str] = {}
    for item in root.rglob("*"):
        rel = item.relative_to(root).as_posix()
        metadata = item.lstat()
        require(not stat.S_ISLNK(metadata.st_mode), "linked replay evidence rejected")
        if stat.S_ISREG(metadata.st_mode):
            require(metadata.st_nlink == 1, f"unsafe replay member: {rel}")
            if rel != "SHA256SUMS.txt":
                actual[rel] = sha(item)
        elif not stat.S_ISDIR(metadata.st_mode):
            raise AttributionError(f"special replay member: {rel}")
    require(declared == actual, "replay checksum membership or bytes changed")
    return declared


def validate_package_closures(authority: dict[str, Any]) -> None:
    runtime = authority["runtime_authority"]
    require(runtime["tool_count"] == 4 and runtime["record_verified_package_closures"] == 5,
            "runtime closure denominator changed")
    launchers = runtime["python_launchers"]
    require(set(launchers) == {"ropgadget", "ropper"}, "Python launcher authority changed")
    count = 0
    for tool, record in launchers.items():
        require(record["invocation_suffix"].endswith(f"/venvs/{tool}/bin/python"),
                "Python launcher suffix changed")
        interpreter = record["resolved_interpreter"]
        require(set(interpreter) == {"sha256", "size_bytes", "mode"} and interpreter["mode"] == "0755",
                "resolved interpreter authority changed")
        for closure in record["package_closures"]:
            require(set(closure) == {"distribution", "version", "package_root", "closure_policy"}
                    and closure["closure_policy"] == "importlib_metadata_record_sha256",
                    "Python RECORD closure descriptor changed")
            count += 1
    require(count == 5, "Python RECORD closure denominator changed")

def validate_authority(value: Any) -> dict[str, Any]:
    keys = {
        "schema", "sprint", "patch", "campaign_id", "predecessor_campaign_id",
        "evidence_class", "frozen", "publication_eligible", "input_authority",
        "selection", "tools", "adapters", "execution", "runtime_authority",
        "result_contract", "terminal_attribution", "claim_boundary", "limitations",
    }
    require(isinstance(value, dict) and set(value) == keys, "P088 replay authority shape changed")
    require(value["schema"] == "x64lens-sprint13-natural-frozen-replay-authority-v2"
            and value["sprint"] == 13 and value["patch"] == 88,
            "P088 replay authority identity changed")
    require(value["campaign_id"] == "s13-p088-natural-frozen-replay-v2"
            and value["predecessor_campaign_id"] == "s13-p083-natural-coordinate-v1",
            "P088 replay lineage changed")
    require(value["evidence_class"] == "diagnostic" and value["frozen"] is False
            and value["publication_eligible"] is False,
            "P088 replay evidence boundary changed")
    require(len(value["selection"]) == 12 and len({item["target_id"] for item in value["selection"]}) == 12,
            "target denominator changed")
    require({item["role"] for item in value["selection"]} == {"et_exec", "pie_et_dyn", "shared_et_dyn"},
            "role denominator changed")
    execution = value["execution"]
    require(execution["execution_denominator"] == 48 and execution["executions_per_target"] == 4
            and execution["tools"] == list(TOOLS) and execution["reroll"] is False,
            "execution authority changed")
    input_authority = value["input_authority"]
    require(type(input_authority["executions"]) is int and input_authority["executions"] == 48
            and input_authority["selected_targets"] == 12 and input_authority["cells"] == 9
            and input_authority["controls"] == 108,
            "predecessor denominator authority changed")
    require(sum(input_authority["cell_counts"].values()) == 9, "predecessor cell counts changed")
    terminal = value["terminal_attribution"]
    require(terminal["execution_outcomes"] == 48 and terminal["relation_outcomes"] == 48
            and terminal["observations"] == 36 and terminal["cells"] == 9
            and terminal["precedence_mutations"] == 16,
            "terminal denominator changed")
    require(value["result_contract"] == {
        "checksum_complete": True,
        "expected_result_required": True,
        "raw_streams": 96,
        "run_records": 48,
        "target_files": 12,
    }, "result contract changed")
    validate_package_closures(value)
    return value


def execution_reason(record: dict[str, Any], tool: str) -> str:
    if record.get("timeout") is True:
        return "timeout"
    if record.get("output_limited") is True:
        return "output_limit"
    if record.get("signal") is not None:
        return "signal"
    if record.get("exit_code") == 0:
        return "success"
    if tool == "x64lens" and record.get("exit_code") == 6:
        return "unsupported"
    return "nonzero_exit"


def precedence_selftest() -> int:
    cases = [
        ({"timeout": True, "output_limited": True, "signal": 9, "exit_code": 0}, "x64lens", "timeout"),
        ({"timeout": True, "output_limited": False, "signal": None, "exit_code": 6}, "x64lens", "timeout"),
        ({"timeout": False, "output_limited": True, "signal": 9, "exit_code": 0}, "x64lens", "output_limit"),
        ({"timeout": False, "output_limited": True, "signal": None, "exit_code": 6}, "x64lens", "output_limit"),
        ({"timeout": False, "output_limited": False, "signal": 9, "exit_code": 0}, "x64lens", "signal"),
        ({"timeout": False, "output_limited": False, "signal": 15, "exit_code": 6}, "x64lens", "signal"),
        ({"timeout": False, "output_limited": False, "signal": None, "exit_code": 0}, "x64lens", "success"),
        ({"timeout": False, "output_limited": False, "signal": None, "exit_code": 0}, "ropper", "success"),
        ({"timeout": False, "output_limited": False, "signal": None, "exit_code": 6}, "x64lens", "unsupported"),
        ({"timeout": False, "output_limited": False, "signal": None, "exit_code": 6}, "ropper", "nonzero_exit"),
        ({"timeout": False, "output_limited": False, "signal": None, "exit_code": 1}, "x64lens", "nonzero_exit"),
        ({"timeout": False, "output_limited": False, "signal": None, "exit_code": 17}, "ropr", "nonzero_exit"),
        ({"timeout": True, "output_limited": True, "signal": None, "exit_code": None}, "ropr", "timeout"),
        ({"timeout": False, "output_limited": True, "signal": None, "exit_code": None}, "ropr", "output_limit"),
        ({"timeout": False, "output_limited": False, "signal": 9, "exit_code": None}, "ropr", "signal"),
        ({"timeout": False, "output_limited": False, "signal": None, "exit_code": 127}, "ropgadget", "nonzero_exit"),
    ]
    for record, tool, expected in cases:
        require(execution_reason(record, tool) == expected, f"precedence failure: {tool}/{expected}")
    return len(cases)


def validate_result(root: Path, authority: dict[str, Any], authority_sha256: str) -> tuple[dict[str, Any], dict[str, str]]:
    checks = checksum_map(root)
    for name in ("manifest.json", "selection-freeze.json", "runtime-authority.json"):
        require(name in checks, f"missing sealed replay authority: {name}")
    result = load(root / "manifest.json")
    freeze = load(root / "selection-freeze.json")
    runtime = load(root / "runtime-authority.json")
    require(result["schema"] == "x64lens-sprint13-natural-frozen-replay-result-v2" and result["patch"] == 88,
            "replay result identity changed")
    require(result["campaign_id"] == authority["campaign_id"] and result["authority_sha256"] == authority_sha256,
            "replay campaign or authority changed")
    expected_summary = {
        "selected_count": 12,
        "role_counts": {role: sum(item["role"] == role for item in authority["selection"])
                        for role in ("et_exec", "pie_et_dyn", "shared_et_dyn")},
    }
    require(freeze == {
        "schema": "x64lens-sprint13-natural-selection-freeze-v2",
        "selection": authority["selection"],
        "summary": expected_summary,
    }, "selection freeze changed")
    require(result["selection_freeze"] == expected_summary, "selection-freeze summary changed")
    require(runtime["schema"] == "x64lens-sprint13-natural-runtime-authority-v2" and set(runtime["tools"]) == set(TOOLS),
            "runtime authority changed")
    require(runtime["environment"] == authority["runtime_authority"]["environment"],
            "runtime environment authority changed")
    require(set(result["tool_identities"]) == set(TOOLS), "result tool identity membership changed")
    for tool in TOOLS:
        expected = authority["tools"][tool]
        current = result["tool_identities"][tool]
        runtime_tool = runtime["tools"][tool]["executable"]
        if tool == "x64lens":
            require(current.get("identity_policy") == "strip_debug_projection"
                    and runtime_tool.get("identity_policy") == "strip_debug_projection",
                    "x64lens projection policy changed")
            for key in ("projection_sha256", "projection_size_bytes"):
                require(current.get(key) == expected[key] and runtime_tool.get(key) == expected[key],
                        f"x64lens projection changed: {key}")
        else:
            for key in ("sha256", "size_bytes", "mode"):
                require(current.get(key) == expected[key] and runtime_tool.get(key) == expected[key],
                        f"tool/runtime authority changed: {tool}/{key}")
        if tool in authority["runtime_authority"]["python_launchers"]:
            expected_launcher = authority["runtime_authority"]["python_launchers"][tool]
            observed_closures = runtime["tools"][tool]["package_closures"]
            require(len(observed_closures) == len(expected_launcher["package_closures"]),
                    f"Python package closure denominator changed: {tool}")
            for requested, observed in zip(expected_launcher["package_closures"], observed_closures):
                for key in ("distribution", "version", "package_root", "closure_policy"):
                    require(observed.get(key) == requested.get(key),
                            f"Python package closure changed: {tool}/{key}")
                require(observed.get("files", 0) > 0 and observed.get("bytes", 0) > 0
                        and len(observed.get("closure_sha256", "")) == 64
                        and len(observed.get("record_sha256", "")) == 64,
                        f"Python RECORD closure incomplete: {tool}")
            resolved = runtime["tools"][tool]["interpreter"]["resolved_interpreter"]
            for key in ("sha256", "size_bytes", "mode"):
                require(resolved[key] == expected_launcher["resolved_interpreter"][key],
                        f"Python interpreter authority changed: {tool}/{key}")
    expected_runs = {(item["target_id"], tool) for item in authority["selection"] for tool in TOOLS}
    observed: set[tuple[str, str]] = set()
    raw: set[str] = set()
    require(set(result["outcomes"]) == {item["target_id"] for item in authority["selection"]},
            "replay target membership changed")
    for target_id, outcome in result["outcomes"].items():
        require(set(outcome["tools"]) == set(TOOLS), f"tool membership changed: {target_id}")
        for tool, record in outcome["tools"].items():
            observed.add((target_id, tool))
            for stream in ("stdout", "stderr"):
                rel = safe_rel(record[stream]["path"])
                require(rel in checks and rel.startswith(f"runs/{target_id}/{tool}/"), f"unsealed raw stream: {rel}")
                raw.add(rel)
                path = root / rel
                require(record[stream]["sha256"] == sha(path)
                        and record[stream]["size_bytes"] == path.stat().st_size,
                        f"raw stream descriptor changed: {rel}")
    require(observed == expected_runs and len(raw) == 96, "replay raw denominator changed")
    require({f"targets/{item['target_id']}" for item in authority["selection"]} <= set(checks),
            "target evidence missing")
    require(result["execution_count"] == 48 and result["complete_execution_denominator"] == 48
            and len(result["cells"]) == 9 and result["control_count"] == 108,
            "replay manifest denominators changed")
    return result, checks


def attribute(result: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    execution = {key: 0 for key in ("success", "unsupported", "timeout", "output_limit", "signal", "nonzero_exit")}
    relation = {key: 0 for key in authority["terminal_attribution"]["relation_reasons"]}
    for outcome in result["outcomes"].values():
        for tool, record in outcome["tools"].items():
            execution[execution_reason(record, tool)] += 1
            state = record["relation_status"]
            require(state in relation, f"unknown relation state: {state}")
            relation[state] += 1
    observation = {key: 0 for key in authority["terminal_attribution"]["observation_reasons"]}
    cells = {key: 0 for key in authority["terminal_attribution"]["cell_reasons"]}
    for cell in result["cells"]:
        state = cell["terminal_state"]
        require(state in cells, f"unknown cell state: {state}")
        cells[state] += 1
        for item in cell["observations"]:
            state = item["status"]
            require(state in observation, f"unknown observation state: {state}")
            observation[state] += 1
    output = {
        "schema": "x64lens-sprint13-natural-terminal-attribution-result-v2",
        "sprint": 13,
        "patch": 88,
        "campaign_id": result["campaign_id"],
        "execution_outcomes": sum(execution.values()),
        "execution_reasons": execution,
        "relation_outcomes": sum(relation.values()),
        "relation_reasons": relation,
        "observations": sum(observation.values()),
        "observation_reasons": observation,
        "cells": sum(cells.values()),
        "cell_reasons": cells,
        "precedence_mutations": precedence_selftest(),
        "raw_streams_verified": 96,
        "target_files_verified": 12,
        "checksum_complete": True,
        "decision": "sealed_terminal_layers_attributed_without_reinterpretation",
        "public_fields_added": 0,
        "semantic_changes": 0,
        "score_changes": 0,
        "schema_changed": False,
    }
    require(output["execution_outcomes"] == 48 and output["relation_outcomes"] == 48
            and output["observations"] == 36 and output["cells"] == 9,
            "attribution denominator changed")
    return output


def same_file(fd: int, path: Path) -> bool:
    retained = os.fstat(fd)
    visible = path.stat(follow_symlinks=False)
    return stat.S_ISREG(visible.st_mode) and (retained.st_dev, retained.st_ino) == (visible.st_dev, visible.st_ino)


def write_noreplace(path: Path, payload: bytes) -> None:
    require(path.parent.is_dir() and not path.parent.is_symlink(), "output parent unavailable or linked")
    temp = path.parent / f".{path.name}.tmp.{os.getpid()}.{os.urandom(16).hex()}"
    fd = -1
    temp_exists = False
    published = False
    try:
        with defer_catchable_signals():
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
            temp_exists = True
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            require(written > 0, "short attribution write")
            view = view[written:]
        os.fsync(fd)
        os.fchmod(fd, 0o444)
        os.fsync(fd)
        with defer_catchable_signals():
            os.link(temp, path, follow_symlinks=False)
            published = True
            os.unlink(temp)
            temp_exists = False
        require(same_file(fd, path), "published attribution identity changed")
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except BaseException:
        if published:
            try:
                if fd >= 0 and same_file(fd, path):
                    path.unlink()
            except OSError:
                pass
        if temp_exists:
            try:
                if fd >= 0 and same_file(fd, temp):
                    temp.unlink()
            except OSError:
                pass
        raise
    finally:
        if fd >= 0:
            os.close(fd)


def selftest(authority: dict[str, Any]) -> None:
    require(precedence_selftest() == 16, "precedence denominator changed")
    mutated = json.loads(json.dumps(authority))
    mutated["input_authority"]["executions"] = 47
    try:
        validate_authority(mutated)
    except AttributionError:
        pass
    else:
        raise AttributionError("false replay denominator accepted")
    mutated = json.loads(json.dumps(authority))
    mutated["runtime_authority"]["python_launchers"]["ropgadget"]["package_closures"][0]["closure_policy"] = "mutable_filesystem_walk"
    try:
        validate_authority(mutated)
    except AttributionError:
        pass
    else:
        raise AttributionError("changed Python RECORD closure policy accepted")
    with tempfile.TemporaryDirectory(prefix="x64lens-attribution-publication-selftest-") as raw:
        output = Path(raw) / "result.json"
        original_write = os.write
        calls = 0

        def injected(fd: int, data: bytes | memoryview) -> int:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError(5, "injected write failure")
            return original_write(fd, data[:7])

        os.write = injected  # type: ignore[assignment]
        try:
            try:
                write_noreplace(output, b"{" + b"x" * 8192 + b"}\n")
            except OSError:
                pass
            else:
                raise AttributionError("injected partial write was accepted")
        finally:
            os.write = original_write  # type: ignore[assignment]
        require(not output.exists(), "partial attribution final file survived failure")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("selftest", "run"))
    parser.add_argument("--authority", type=Path, default=AUTHORITY)
    parser.add_argument("--expected", type=Path, default=EXPECTED)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        authority_path = args.authority.resolve(strict=True)
        authority = validate_authority(load(authority_path))
        selftest(authority)
        if args.action == "selftest":
            print("sprint13-natural-terminal-attribution-v2-smoke: ok precedence_mutations=16 execution_outcomes=48 relation_outcomes=48 observations=36 cells=9 raw_streams=96 record_python_closures=5 expected_required=1 run=deferred")
            return 0
        require(args.input_dir is not None and args.output is not None, "--input-dir and --output are required")
        with signal_guard("terminal attribution"):
            result, _checks = validate_result(args.input_dir.resolve(strict=True), authority, sha(authority_path))
            output = attribute(result, authority)
            require(args.expected is not None, "--expected is mandatory")
            require(output == load(args.expected.resolve(strict=True)), "terminal attribution differs from mandatory expected result")
            write_noreplace(Path(os.path.abspath(args.output)), canonical(output))
        print("sprint13-natural-terminal-attribution-v2-smoke: ok precedence_mutations=16 execution_outcomes=48 relation_outcomes=48 observations=36 cells=9 raw_streams=96 record_python_closures=5 expected_required=1 run=complete")
        return 0
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, AttributionError) as exc:
        fail(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
