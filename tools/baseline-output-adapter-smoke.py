#!/usr/bin/env python3
"""Durable regression gate for runner-bound Sprint 11 baseline adapters."""
from __future__ import annotations

import csv
import hashlib
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

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "benchmarks/scripts/baseline-output-adapter.py"
COMMON = ROOT / "benchmarks/scripts/diagnostic_artifact.py"
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint11-diagnostic-tasks.json"
FIXTURES = ROOT / "tests/fixtures/baseline-adapters"

VERSIONS = {
    "ropgadget": "Version:        ROPgadget v7.7",
    "ropper": "Version: Ropper 1.13.13",
    "ropr": "ropr 0.2.26",
}
CONDITIONS = {
    "ropgadget": "ropgadget-rop-report",
    "ropper": "ropper-rop-report",
    "ropr": "ropr-rop-report",
}


class SmokeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def command_for(authority: dict[str, Any], tool: str, cwd: Path, tool_path: Path, target_path: Path) -> list[str]:
    baseline = next(item for item in authority["baselines"] if item["id"] == tool)
    return [
        os.path.relpath(tool_path, cwd) if item == "<tool>" else
        os.path.relpath(target_path, cwd) if item == "<target>" else
        item
        for item in baseline["command_template"]
    ]


def build_campaign(base: Path, *, authority: dict[str, Any] | None = None) -> tuple[Path, dict[str, dict[str, Any]]]:
    authority = authority or json.loads(AUTHORITY.read_text(encoding="utf-8"))
    campaign = base / "campaign"
    (campaign / "inputs/tools").mkdir(parents=True)
    (campaign / "inputs/targets").mkdir(parents=True)
    (campaign / "inputs/versions").mkdir(parents=True)
    (campaign / "outputs").mkdir(parents=True)
    target = campaign / "inputs/targets/controlled-gadgets"
    target.write_bytes(b"controlled adapter target\n")
    target.chmod(0o444)
    target_sha = sha256(target)
    rows: list[dict[str, Any]] = []
    tools: list[dict[str, Any]] = []
    result: dict[str, dict[str, Any]] = {}
    for order, tool in enumerate(("ropgadget", "ropper", "ropr"), start=1):
        baseline = next(item for item in authority["baselines"] if item["id"] == tool)
        executable = campaign / f"inputs/tools/{tool}"
        executable.write_text(f"#!/bin/sh\necho {tool}\n", encoding="utf-8")
        executable.chmod(0o555)
        version_dir = campaign / f"inputs/versions/{tool}"
        version_dir.mkdir()
        version_work = version_dir / "work"
        version_work.mkdir()
        version_stdout = version_dir / "stdout.bin"
        version_stdout.write_text(VERSIONS[tool] + "\n", encoding="utf-8")
        version_stdout.chmod(0o444)
        version_stderr = version_dir / "stderr.bin"
        version_stderr.write_bytes(b"")
        version_stderr.chmod(0o444)
        run_id = f"measured-001-{order:02d}-{CONDITIONS[tool]}"
        run_dir = campaign / f"outputs/{run_id}"
        work = run_dir / "work"
        work.mkdir(parents=True)
        stdout = run_dir / "stdout.bin"
        stdout.write_bytes((FIXTURES / f"{tool}-valid.txt").read_bytes())
        stdout.chmod(0o444)
        stderr = run_dir / "stderr.bin"
        stderr.write_bytes(b"")
        stderr.chmod(0o444)
        tool_sha = sha256(executable)
        command = command_for(authority, tool, work, executable, target)
        row = {
            "runner_schema_version": "2",
            "campaign_id": "adapter-smoke-v2",
            "run_id": run_id,
            "phase": "measured",
            "round": "1",
            "order_index": str(order),
            "condition_id": CONDITIONS[tool],
            "task_scope": "baseline_gadget_report",
            "tool_id": tool,
            "tool_version": VERSIONS[tool],
            "tool_sha256": tool_sha,
            "target_id": "controlled-gadgets",
            "target_sha256": target_sha,
            "target_license": "Apache-2.0 project-controlled fixture",
            "command_json": json.dumps(command, separators=(",", ":")),
            "command_cwd": str(work.relative_to(campaign)),
            "stdout_path": str(stdout.relative_to(campaign)),
            "stderr_path": str(stderr.relative_to(campaign)),
            "stdout_limit_bytes": str(baseline["capture_policy"]["maximum_stdout_bytes"]),
            "stderr_limit_bytes": str(baseline["capture_policy"]["maximum_stderr_bytes"]),
            "stdout_bytes": str(stdout.stat().st_size),
            "stdout_sha256": sha256(stdout),
            "stderr_bytes": "0",
            "stderr_sha256": sha256(stderr),
            "exit_code": "0",
            "process_outcome": "success",
            "outcome": "success",
        }
        rows.append(row)
        version_argv = [item.replace("<tool>", "{tool}") for item in baseline["version_command_template"]]
        tools.append({
            "id": tool,
            "version": VERSIONS[tool],
            "version_observed": VERSIONS[tool],
            "version_argv": version_argv,
            "version_command": [os.path.relpath(executable, version_work), *version_argv[1:]],
            "version_command_cwd": str(version_work.relative_to(campaign)),
            "sha256": tool_sha,
            "size_bytes": executable.stat().st_size,
            "snapshot_path": str(executable.relative_to(campaign)),
            "version_stdout_path": str(version_stdout.relative_to(campaign)),
            "version_stderr_path": str(version_stderr.relative_to(campaign)),
            "version_result": {
                "stdout_bytes": version_stdout.stat().st_size,
                "stdout_sha256": sha256(version_stdout),
                "stderr_bytes": 0,
                "stderr_sha256": sha256(version_stderr),
                "process_outcome": "success",
                "exit_code": 0,
                "signal": None,
                "timed_out": False,
            },
        })
        result[tool] = {"run_id": run_id, "stdout": stdout, "stderr": stderr}
    rows_path = campaign / "rows.tsv"
    write_tsv(rows_path, rows)
    rows_path.chmod(0o444)
    manifest = {
        "schema_version": 2,
        "campaign_id": "adapter-smoke-v2",
        "evidence_class": "diagnostic",
        "frozen": False,
        "publication_eligible": False,
        "artifacts": {"rows": "rows.tsv", "rows_sha256": sha256(rows_path)},
        "outcomes": {"row_count": len(rows)},
        "tools": tools,
        "targets": [{
            "id": "controlled-gadgets",
            "license": "Apache-2.0 project-controlled fixture",
            "sha256": target_sha,
            "size_bytes": target.stat().st_size,
            "snapshot_path": str(target.relative_to(campaign)),
        }],
    }
    manifest_path = campaign / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o444)
    return campaign, result


def run_adapter(campaign: Path, run_id: str, authority: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ADAPTER), "--campaign-result", str(campaign), "--run-id", run_id,
         "--task-authority", str(authority), "--output", str(output)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=20,
    )


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def contains_generic_count(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key == "gadget_count" or contains_generic_count(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_generic_count(item) for item in value)
    return False


def refresh_campaign_hashes(campaign: Path) -> None:
    rows = campaign / "rows.tsv"
    manifest = campaign / "manifest.json"
    manifest.chmod(0o644)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["artifacts"]["rows_sha256"] = sha256(rows)
    manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest.chmod(0o444)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="x64lens-baseline-adapter-v2-") as raw:
        base = Path(raw)
        authority_copy = base / "authority.json"
        shutil.copy2(AUTHORITY, authority_copy)
        authority_copy.chmod(0o444)
        authority = json.loads(authority_copy.read_text(encoding="utf-8"))
        campaign, records = build_campaign(base, authority=authority)
        artifacts: dict[str, dict[str, Any]] = {}
        for tool in ("ropgadget", "ropper", "ropr"):
            output = base / f"{tool}.json"
            result = run_adapter(campaign, records[tool]["run_id"], authority_copy, output)
            require(result.returncode == 0, f"{tool} adapter failed: {result.stderr}")
            artifact = json.loads(output.read_text(encoding="utf-8"))
            artifacts[tool] = artifact
            metrics = artifact["metrics"]
            require(artifact["schema_version"] == 2, f"{tool} schema mismatch")
            require(artifact["adapter"]["id"].endswith("-v2"), f"{tool} adapter identity mismatch")
            require(artifact["campaign_binding"]["run_id"] == records[tool]["run_id"], f"{tool} row binding mismatch")
            require(metrics["tool_native_record_count"] == 5, f"{tool} native record count mismatch")
            require(metrics["unique_tool_native_record_count"] == 4, f"{tool} unique count mismatch")
            require(metrics["duplicate_tool_native_record_count"] == 1, f"{tool} duplicate count mismatch")
            require(metrics["canonical_exact_pop_rdi_ret_record_count"] == 2, f"{tool} exact relation count mismatch")
            require(not contains_generic_count(artifact), f"{tool} artifact contains generic gadget_count")

        # retq remains visible as native text but is canonicalized to ret in the
        # exact cross-tool relation.
        retq_campaign = base / "retq-campaign"
        shutil.copytree(campaign, retq_campaign)
        retq_stdout = retq_campaign / records["ropgadget"]["stdout"].relative_to(campaign)
        retq_stdout.chmod(0o644)
        retq_stdout.write_text("0x401000 : pop rdi ; retq\n", encoding="utf-8")
        retq_stdout.chmod(0o444)
        rows_path = retq_campaign / "rows.tsv"
        rows = list(csv.DictReader(rows_path.open(encoding="utf-8"), delimiter="\t"))
        for row in rows:
            if row["run_id"] == records["ropgadget"]["run_id"]:
                row["stdout_bytes"] = str(retq_stdout.stat().st_size)
                row["stdout_sha256"] = sha256(retq_stdout)
        rows_path.chmod(0o644)
        write_tsv(rows_path, rows)
        rows_path.chmod(0o444)
        refresh_campaign_hashes(retq_campaign)
        retq_output = base / "retq.json"
        retq_result = run_adapter(retq_campaign, records["ropgadget"]["run_id"], authority_copy, retq_output)
        require(retq_result.returncode == 0, f"retq canonicalization failed: {retq_result.stderr}")
        retq_artifact = json.loads(retq_output.read_text(encoding="utf-8"))
        relation = retq_artifact["normalized_relations"]["canonical_exact_pop_rdi_ret"]["records"][0]
        native = retq_artifact["native_output"]["native_records"][0]
        require(relation["instructions"] == ["pop rdi", "ret"], "retq relation was not canonicalized")
        require(native["native_instructions"] == ["pop rdi", "retq"], "retq native evidence was not preserved")

        adversarial = 0
        # Version substring attacks must fail exact first-line authentication.
        bad_version = base / "bad-version"
        shutil.copytree(campaign, bad_version)
        version_path = bad_version / "inputs/versions/ropgadget/stdout.bin"
        version_path.chmod(0o644)
        version_path.write_text("prefix Version:        ROPgadget v7.7 suffix\n", encoding="utf-8")
        version_path.chmod(0o444)
        manifest = bad_version / "manifest.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for tool in data["tools"]:
            if tool["id"] == "ropgadget":
                tool["version_result"]["stdout_bytes"] = version_path.stat().st_size
                tool["version_result"]["stdout_sha256"] = sha256(version_path)
        manifest.chmod(0o644)
        manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest.chmod(0o444)
        result = run_adapter(bad_version, records["ropgadget"]["run_id"], authority_copy, base / "bad-version.json")
        require(result.returncode == 2, "substring-only version evidence was accepted")
        adversarial += 1

        # Version-command syntax is part of the task authority and retained
        # campaign identity, not merely a version-output string.
        bad_version_argv = base / "bad-version-argv"
        shutil.copytree(campaign, bad_version_argv)
        manifest_path = bad_version_argv / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        for tool_record in data["tools"]:
            if tool_record["id"] == "ropgadget":
                tool_record["version_argv"] = ["{tool}", "--help"]
                tool_record["version_command"][-1] = "--help"
        manifest_path.chmod(0o644)
        manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest_path.chmod(0o444)
        result = run_adapter(bad_version_argv, records["ropgadget"]["run_id"], authority_copy, base / "bad-version-argv.json")
        require(result.returncode == 2 and "version argv differs from task authority" in result.stderr, "authority-inconsistent version argv was accepted")
        adversarial += 1

        # The raw-byte line bound applies before ANSI removal.
        raw_bound = base / "raw-bound"
        shutil.copytree(campaign, raw_bound)
        stdout = raw_bound / records["ropgadget"]["stdout"].relative_to(campaign)
        stdout.chmod(0o644)
        stdout.write_bytes(b"\x1b[31m" * 1800 + b"0x401000 : pop rdi ; ret\n")
        stdout.chmod(0o444)
        rows_path = raw_bound / "rows.tsv"
        rows = list(csv.DictReader(rows_path.open(encoding="utf-8"), delimiter="\t"))
        for row in rows:
            if row["run_id"] == records["ropgadget"]["run_id"]:
                row["stdout_bytes"] = str(stdout.stat().st_size)
                row["stdout_sha256"] = sha256(stdout)
        rows_path.chmod(0o644)
        write_tsv(rows_path, rows)
        rows_path.chmod(0o444)
        refresh_campaign_hashes(raw_bound)
        result = run_adapter(raw_bound, records["ropgadget"]["run_id"], authority_copy, base / "raw-bound.json")
        require(result.returncode == 2, "escape-heavy over-bound raw line was accepted")
        adversarial += 1

        # The running adapter must match the authority-declared path and schema.
        altered_authority = base / "altered-authority.json"
        altered = json.loads(authority_copy.read_text(encoding="utf-8"))
        altered["baselines"][0]["adapter"]["path"] = "benchmarks/scripts/not-the-running-adapter.py"
        altered_authority.write_text(json.dumps(altered) + "\n", encoding="utf-8")
        result = run_adapter(campaign, records["ropgadget"]["run_id"], altered_authority, base / "altered.json")
        require(result.returncode == 2, "authority-declared adapter path mismatch was accepted")
        adversarial += 1

        # Pre-existing outputs and symlink outputs are never replaced or followed.
        existing = base / "existing.json"
        existing.write_text("foreign\n", encoding="utf-8")
        result = run_adapter(campaign, records["ropgadget"]["run_id"], authority_copy, existing)
        require(result.returncode == 2 and existing.read_text() == "foreign\n", "pre-existing output was modified")
        adversarial += 1
        victim = base / "victim.txt"
        victim.write_text("victim\n", encoding="utf-8")
        symlink = base / "symlink.json"
        symlink.symlink_to(victim)
        result = run_adapter(campaign, records["ropgadget"]["run_id"], authority_copy, symlink)
        require(result.returncode == 2 and victim.read_text() == "victim\n", "symlink output victim was modified")
        adversarial += 1

        # In-process deterministic post-precommit mutation: the published inode
        # must be removed and the command must fail.
        adapter_module = load_module("baseline_adapter_under_smoke", ADAPTER)
        common_module = sys.modules["diagnostic_artifact"]
        late_output = base / "late-output.json"
        late_stdout = campaign / records["ropgadget"]["stdout"].relative_to(campaign)
        original_publish = adapter_module.atomic_publish_bytes

        def mutate_between_barriers(output: Path, data: bytes, *, reauthenticate, mode: int = 0o444):
            calls = 0
            def wrapped() -> None:
                nonlocal calls
                reauthenticate()
                calls += 1
                if calls == 1:
                    late_stdout.chmod(0o644)
                    late_stdout.write_bytes(late_stdout.read_bytes() + b"# late mutation\n")
                    late_stdout.chmod(0o444)
            return original_publish(output, data, reauthenticate=wrapped, mode=mode)

        adapter_module.atomic_publish_bytes = mutate_between_barriers
        try:
            code = adapter_module.main([
                "--campaign-result", str(campaign), "--run-id", records["ropgadget"]["run_id"],
                "--task-authority", str(authority_copy), "--output", str(late_output),
            ])
        except Exception:
            code = 2
        finally:
            adapter_module.atomic_publish_bytes = original_publish
        require(code != 0 and not late_output.exists(), "post-authentication input mutation produced a successful output")
        adversarial += 1
        # Restore the campaign for the final path-substitution probe.
        shutil.rmtree(campaign)
        campaign, records = build_campaign(base / "rebuilt", authority=authority)

        adapter_module = load_module("baseline_adapter_output_substitution_smoke", ADAPTER)
        common_module = sys.modules["diagnostic_artifact"]
        foreign = base / "foreign-final.txt"
        foreign.write_text("foreign final\n", encoding="utf-8")
        substituted = base / "substituted.json"
        escaped = base / "escaped-owned-output.json"
        original_rename = common_module._renameat2

        def substitute_after_rename(parent_fd: int, source_name: str, destination_name: str) -> None:
            original_rename(parent_fd, source_name, destination_name)
            os.rename(destination_name, escaped.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            fd = os.open(destination_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444, dir_fd=parent_fd)
            try:
                os.write(fd, b"foreign final\n")
                os.fsync(fd)
            finally:
                os.close(fd)

        common_module._renameat2 = substitute_after_rename
        try:
            try:
                adapter_module.main([
                    "--campaign-result", str(campaign), "--run-id", records["ropgadget"]["run_id"],
                    "--task-authority", str(authority_copy), "--output", str(substituted),
                ])
                code = 0
            except Exception:
                code = 2
        finally:
            common_module._renameat2 = original_rename
        require(code != 0, "output-path substitution produced exit zero")
        require(substituted.read_bytes() == b"foreign final\n", "foreign substituted output was deleted or modified")
        adversarial += 1

        print(
            "baseline-output-adapter-smoke: ok "
            "tools=3 controlled_records=15 exact_relation_precision=1.000 "
            "exact_relation_recall=1.000 adversarial_cases=" + str(adversarial) + " "
            "runner_binding=1 raw_line_bound=1 exact_version=1 retq_canonicalized=1 generic_counts=0"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SmokeError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"baseline-output-adapter-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
