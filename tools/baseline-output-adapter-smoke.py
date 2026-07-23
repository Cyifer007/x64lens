#!/usr/bin/env python3
"""Validate the Sprint 11 ROPgadget, Ropper, and ropr output adapters."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "benchmarks/scripts/baseline-output-adapter.py"
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint11-diagnostic-tasks.json"
FIXTURES = ROOT / "tests/fixtures/baseline-adapters"
TOOLS = ("ropgadget", "ropper", "ropr")


class SmokeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()



def load_adapter_module() -> Any:
    spec = importlib.util.spec_from_file_location("x64lens_baseline_output_adapter", ADAPTER)
    require(spec is not None and spec.loader is not None, "cannot load adapter module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def authority() -> dict[str, Any]:
    return json.loads(AUTHORITY.read_text(encoding="utf-8"))


def baseline(tool: str, source: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source if source is not None else authority()
    return next(item for item in source["baselines"] if item["id"] == tool)


def substituted_command(template: list[str], tool_path: Path, target_path: Path) -> list[str]:
    return [
        str(tool_path) if item == "<tool>" else str(target_path) if item == "<target>" else item
        for item in template
    ]


def invoke(
    *,
    tool: str,
    work: Path,
    native_stdout: Path,
    output: Path,
    task_authority: Path = AUTHORITY,
    command: list[str] | None = None,
    condition_id: str | None = None,
    target_sha256: str | None = None,
    version_text: str | None = None,
    native_stderr: Path | None = None,
    tool_mode: int = 0o755,
) -> subprocess.CompletedProcess[str]:
    tool_record = baseline(tool, json.loads(task_authority.read_text(encoding="utf-8")))
    tool_path = work / tool_record["executable_name"]
    if not tool_path.exists():
        tool_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    tool_path.chmod(tool_mode)
    target = work / "target.elf"
    if not target.exists():
        target.write_bytes(b"controlled baseline adapter target\n")
    version = work / f"{tool}-version.txt"
    version.write_text(version_text if version_text is not None else f"{tool} controlled-1.0\n", encoding="utf-8")
    stderr = native_stderr if native_stderr is not None else work / f"{tool}-stderr.bin"
    if not stderr.exists():
        stderr.write_bytes(b"")
    command_value = command or substituted_command(tool_record["command_template"], tool_path, target)
    argv = [
        sys.executable,
        str(ADAPTER),
        "--tool",
        tool,
        "--tool-version",
        "controlled-1.0",
        "--tool-executable",
        str(tool_path),
        "--version-output",
        str(version),
        "--condition-id",
        condition_id or tool_record["condition_id"],
        "--target-id",
        "controlled-target",
        "--target-path",
        str(target),
        "--target-sha256",
        target_sha256 or sha256(target),
        "--command-json",
        json.dumps(command_value, separators=(",", ":")),
        "--command-cwd",
        str(work),
        "--native-stdout",
        str(native_stdout),
        "--native-stderr",
        str(stderr),
        "--task-authority",
        str(task_authority),
        "--output",
        str(output),
    ]
    return subprocess.run(
        argv,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=15,
    )


def assert_no_generic_count(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            require(key != "gadget_count", f"generic gadget_count key at {path}.{key}")
            assert_no_generic_count(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_generic_count(item, f"{path}[{index}]")


def expect_failure(completed: subprocess.CompletedProcess[str], output: Path, label: str) -> None:
    require(completed.returncode == 2, f"{label} returned {completed.returncode}: {completed.stdout} {completed.stderr}")
    require(not output.exists(), f"{label} left partial normalized output")


def main() -> int:
    require(ADAPTER.is_file() and ADAPTER.stat().st_mode & 0o111, "adapter is missing or non-executable")
    source_authority = authority()
    expected_exact_lines = {"ropgadget": (3, 4), "ropper": (4, 5), "ropr": (3, 4)}
    valid_artifacts: dict[str, bytes] = {}
    adversarial_cases = 0

    with tempfile.TemporaryDirectory(prefix="x64lens-baseline-adapter-smoke-") as raw:
        temporary = Path(raw)
        for tool in TOOLS:
            work = temporary / tool
            work.mkdir()
            native = FIXTURES / f"{tool}-valid.txt"
            output = work / "normalized-1.json"
            first = invoke(tool=tool, work=work, native_stdout=native, output=output)
            require(first.returncode == 0, f"{tool} valid fixture failed: {first.stdout} {first.stderr}")
            require(f"tool={tool} records=5 return_records=5 pop_rdi_ret=2" in first.stdout, f"{tool} success banner mismatch")
            artifact = json.loads(output.read_text(encoding="utf-8"))
            require(artifact["schema_version"] == 1, f"{tool} adapter schema mismatch")
            require(artifact["adapter"]["id"] == "x64lens-sprint11-baseline-output-adapter-v1", f"{tool} adapter identity mismatch")
            require(artifact["evidence_class"] == "diagnostic" and artifact["frozen"] is False, f"{tool} evidence class mismatch")
            require(artifact["publication_eligible"] is False, f"{tool} publication boundary mismatch")
            require(artifact["tool"]["id"] == tool and artifact["tool"]["version"] == "controlled-1.0", f"{tool} identity mismatch")
            require(artifact["tool"]["executable"]["sha256"] == sha256(work / baseline(tool)["executable_name"]), f"{tool} executable hash mismatch")
            require(artifact["target"]["sha256"] == sha256(work / "target.elf"), f"{tool} target hash mismatch")
            require(artifact["native_output"]["stdout"]["sha256"] == sha256(native), f"{tool} stdout hash mismatch")
            metrics = artifact["metrics"]
            require(metrics == {
                "canonical_exact_pop_rdi_ret_record_count": 2,
                "duplicate_tool_native_record_count": 1,
                "tool_native_record_count": 5,
                "tool_reported_return_terminator_record_count": 5,
                "unique_canonical_exact_pop_rdi_ret_relation_count": 1,
                "unique_tool_native_record_count": 4,
                "unique_tool_reported_return_terminator_site_count": 4,
            }, f"{tool} metric mismatch: {metrics}")
            expected_exact = [
                {"address": "0x0000000000401000", "instructions": ["pop rdi", "ret"], "source_line": line}
                for line in expected_exact_lines[tool]
            ]
            require(artifact["normalized_relations"]["canonical_exact_pop_rdi_ret"]["records"] == expected_exact, f"{tool} exact relation mismatch")
            require(artifact["normalized_relations"]["binary_fact_arg_control_rdi_present"] is True, f"{tool} binary fact mismatch")
            require(artifact["native_output"]["uncategorized_stdout_line_count"] == 0, f"{tool} uncategorized line mismatch")
            assert_no_generic_count(artifact)
            valid_artifacts[tool] = output.read_bytes()

            output2 = work / "normalized-2.json"
            second = invoke(tool=tool, work=work, native_stdout=native, output=output2)
            require(second.returncode == 0 and output2.read_bytes() == valid_artifacts[tool], f"{tool} normalized output is not deterministic")

        # ANSI output is accepted only after exact byte counting and normalization.
        ansi_work = temporary / "ansi"
        ansi_work.mkdir()
        ansi_native = ansi_work / "ropr-ansi.txt"
        ansi_native.write_bytes(FIXTURES.joinpath("ropr-valid.txt").read_bytes().replace(b"0x0000000000401000", b"\x1b[31m0x0000000000401000\x1b[0m", 1))
        ansi_output = ansi_work / "normalized.json"
        ansi = invoke(tool="ropr", work=ansi_work, native_stdout=ansi_native, output=ansi_output)
        require(ansi.returncode == 0, f"ANSI fixture failed: {ansi.stderr}")
        require(json.loads(ansi_output.read_text(encoding="utf-8"))["native_output"]["ansi_sequences_removed_from_stdout"] == 2, "ANSI removal count mismatch")

        # Every negative control must fail before creating output.
        base_work = temporary / "negative"
        base_work.mkdir()
        valid_native = FIXTURES / "ropgadget-valid.txt"

        unknown = base_work / "unknown.txt"
        unknown.write_text(valid_native.read_text(encoding="utf-8") + "unclassified native line\n", encoding="utf-8")
        output = base_work / "unknown.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=unknown, output=output), output, "unknown line")
        adversarial_cases += 1

        nonreturn = base_work / "nonreturn.txt"
        nonreturn.write_text("0x0000000000401000 : jmp rax\n", encoding="utf-8")
        output = base_work / "nonreturn.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=nonreturn, output=output), output, "non-return record")
        adversarial_cases += 1

        invalid_utf8 = base_work / "invalid-utf8.txt"
        invalid_utf8.write_bytes(b"0x4000 : pop rdi ; ret\n\xff\n")
        output = base_work / "invalid-utf8.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=invalid_utf8, output=output), output, "invalid UTF-8")
        adversarial_cases += 1

        oversized_address = base_work / "oversized-address.txt"
        oversized_address.write_text("0x10000000000000000 : pop rdi ; ret\n", encoding="utf-8")
        output = base_work / "oversized-address.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=oversized_address, output=output), output, "oversized address")
        adversarial_cases += 1

        wrong_condition = base_work / "wrong-condition.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=wrong_condition, condition_id="wrong-condition"), wrong_condition, "wrong condition")
        adversarial_cases += 1

        command_record = baseline("ropgadget")
        tool_path = base_work / command_record["executable_name"]
        target_path = base_work / "target.elf"
        valid_command = substituted_command(command_record["command_template"], tool_path, target_path)
        wrong_command = list(valid_command)
        wrong_command[3] = "6"
        output = base_work / "wrong-command.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=output, command=wrong_command), output, "wrong command")
        adversarial_cases += 1

        output = base_work / "wrong-target-hash.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=output, target_sha256="0" * 64), output, "wrong target hash")
        adversarial_cases += 1

        output = base_work / "wrong-version.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=output, version_text="different version\n"), output, "missing version evidence")
        adversarial_cases += 1

        output = base_work / "nonexec-tool.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=output, tool_mode=0o644), output, "non-executable tool")
        (base_work / command_record["executable_name"]).chmod(0o755)
        adversarial_cases += 1

        # A self-consistent smaller authority cap must still reject oversized evidence.
        limited_authority = base_work / "limited-authority.json"
        limited_value = authority()
        limited = baseline("ropgadget", limited_value)
        limited["capture_policy"]["maximum_stdout_bytes"] = 4096
        limited_authority.write_text(json.dumps(limited_value, indent=2) + "\n", encoding="utf-8")
        oversized = base_work / "oversized.txt"
        oversized.write_bytes(valid_native.read_bytes() + b" " * 4096)
        output = base_work / "oversized.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=oversized, output=output, task_authority=limited_authority), output, "stdout cap")
        adversarial_cases += 1

        parser_limit_authority = base_work / "parser-limit-authority.json"
        parser_limit_value = authority()
        parser_native = baseline("ropgadget", parser_limit_value)["native_output_contract"]
        parser_native["maximum_line_bytes"] = 64
        parser_native["maximum_record_count"] = 2
        parser_native["maximum_instruction_count"] = 1
        parser_limit_authority.write_text(json.dumps(parser_limit_value, indent=2) + "\n", encoding="utf-8")

        long_line = base_work / "long-line.txt"
        long_line.write_text("0x4000 : " + "pop rax ; " * 10 + "ret\n", encoding="utf-8")
        output = base_work / "long-line.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=long_line, output=output, task_authority=parser_limit_authority), output, "line bound")
        adversarial_cases += 1

        too_many_records = base_work / "too-many-records.txt"
        too_many_records.write_text("0x4000 : ret\n0x4001 : ret\n0x4002 : ret\n", encoding="utf-8")
        output = base_work / "record-bound.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=too_many_records, output=output, task_authority=parser_limit_authority), output, "record bound")
        adversarial_cases += 1

        too_many_instructions = base_work / "too-many-instructions.txt"
        too_many_instructions.write_text("0x4000 : pop rdi ; ret\n", encoding="utf-8")
        output = base_work / "instruction-bound.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=too_many_instructions, output=output, task_authority=parser_limit_authority), output, "instruction bound")
        adversarial_cases += 1

        limited_stderr_authority = base_work / "limited-stderr-authority.json"
        limited_stderr_value = authority()
        baseline("ropgadget", limited_stderr_value)["capture_policy"]["maximum_stderr_bytes"] = 4
        limited_stderr_authority.write_text(json.dumps(limited_stderr_value, indent=2) + "\n", encoding="utf-8")
        noisy_stderr = base_work / "noisy-stderr.bin"
        noisy_stderr.write_bytes(b"12345")
        output = base_work / "stderr-cap.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=output, task_authority=limited_stderr_authority, native_stderr=noisy_stderr), output, "stderr cap")
        adversarial_cases += 1

        # Final-component symlinks are rejected without touching their victims.
        victim = base_work / "victim.txt"
        victim.write_text("unchanged\n", encoding="utf-8")
        stdout_link = base_work / "stdout-link"
        stdout_link.symlink_to(valid_native)
        output = base_work / "symlink-input.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=stdout_link, output=output), output, "symlink input")
        require(victim.read_text(encoding="utf-8") == "unchanged\n", "input symlink probe changed unrelated victim")
        adversarial_cases += 1

        real_output_parent = base_work / "real-output-parent"
        real_output_parent.mkdir()
        linked_output_parent = base_work / "linked-output-parent"
        linked_output_parent.symlink_to(real_output_parent, target_is_directory=True)
        linked_output = linked_output_parent / "normalized.json"
        completed = invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=linked_output)
        require(completed.returncode == 2 and not (real_output_parent / "normalized.json").exists(), "output parent symlink was accepted")
        adversarial_cases += 1

        output_link = base_work / "output-link.json"
        output_link.symlink_to(victim)
        completed = invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=output_link)
        require(completed.returncode == 2, "output symlink was accepted")
        require(output_link.is_symlink() and victim.read_text(encoding="utf-8") == "unchanged\n", "output symlink victim was modified")
        adversarial_cases += 1

        preexisting = base_work / "preexisting.json"
        preexisting.write_text("preserve\n", encoding="utf-8")
        completed = invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=preexisting)
        require(completed.returncode == 2 and preexisting.read_text(encoding="utf-8") == "preserve\n", "preexisting output was replaced")
        adversarial_cases += 1

        malformed_authority = base_work / "malformed-authority.json"
        malformed_value = authority()
        malformed_value["authority_id"] = "wrong-authority"
        malformed_authority.write_text(json.dumps(malformed_value), encoding="utf-8")
        output = base_work / "bad-authority-output.json"
        expect_failure(invoke(tool="ropgadget", work=base_work, native_stdout=valid_native, output=output, task_authority=malformed_authority), output, "wrong authority")
        adversarial_cases += 1

        # Mutating a retained input after parsing but before final authentication
        # must fail.  An in-process wrapper gives this race a deterministic
        # location without adding a production-only pause or test hook.
        late_work = temporary / "late-mutation"
        late_work.mkdir()
        late_record = baseline("ropgadget")
        late_tool = late_work / late_record["executable_name"]
        late_tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        late_tool.chmod(0o755)
        late_target = late_work / "target.elf"
        late_target.write_bytes(b"controlled late mutation target\n")
        late_version = late_work / "ropgadget-version.txt"
        late_version.write_text("ropgadget controlled-1.0\n", encoding="utf-8")
        late_native = late_work / "native.txt"
        late_native.write_bytes(valid_native.read_bytes())
        late_stderr = late_work / "stderr.bin"
        late_stderr.write_bytes(b"")
        late_output = late_work / "normalized.json"
        late_command = substituted_command(late_record["command_template"], late_tool, late_target)
        module = load_adapter_module()
        late_args = module.parse_args([
            "--tool", "ropgadget",
            "--tool-version", "controlled-1.0",
            "--tool-executable", str(late_tool),
            "--version-output", str(late_version),
            "--condition-id", late_record["condition_id"],
            "--target-id", "controlled-target",
            "--target-path", str(late_target),
            "--target-sha256", sha256(late_target),
            "--command-json", json.dumps(late_command, separators=(",", ":")),
            "--command-cwd", str(late_work),
            "--native-stdout", str(late_native),
            "--native-stderr", str(late_stderr),
            "--task-authority", str(AUTHORITY),
            "--output", str(late_output),
        ])
        original_builder = module.build_artifact

        def mutate_after_build(*args: Any, **kwargs: Any) -> dict[str, Any]:
            artifact = original_builder(*args, **kwargs)
            late_native.write_bytes(late_native.read_bytes() + b"0x0000000000402000 : ret\n")
            return artifact

        module.build_artifact = mutate_after_build
        try:
            try:
                module.normalize(late_args)
            except module.AdapterError as exc:
                require("native stdout" in str(exc), f"late mutation failed for the wrong reason: {exc}")
            else:
                raise SmokeError("late native-output mutation was accepted")
        finally:
            module.build_artifact = original_builder
        require(not late_output.exists(), "late mutation left partial normalized output")
        adversarial_cases += 1

    print(
        "baseline-output-adapter-smoke: ok "
        "tools=3 controlled_records=15 exact_relation_precision=1.000 "
        f"exact_relation_recall=1.000 adversarial_cases={adversarial_cases} generic_counts=0"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, SmokeError, subprocess.SubprocessError) as exc:
        print(f"baseline-output-adapter-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
