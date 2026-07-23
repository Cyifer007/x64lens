#!/usr/bin/env python3
"""Validate Sprint 11 task identity, adapters, and comparison boundaries.

The smoke is structural except for one controlled command/output probe.  That
probe executes the exact configured ROPgadget argument template against a fake
compatible tool so an output-suppressing flag such as ``--silent`` cannot be
reintroduced while fixture-only adapter tests continue to pass.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint11-diagnostic-tasks.json"
REFERENCE_SPEC = ROOT / "benchmarks/specs/sprint11-reference-diagnostic.json"
STAGES = ROOT / "tests/expected/research-stage-gates.json"


class TaskError(RuntimeError):
    """Raised when the task authority or its controlled command probe drifts."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TaskError(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskError(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"{path.relative_to(ROOT)} must contain an object")
    return value


def require_executable(relative: str, label: str) -> Path:
    path = ROOT / relative
    require(path.is_file(), f"{label} is missing: {relative}")
    require(bool(path.stat().st_mode & 0o111), f"{label} is not executable: {relative}")
    return path


def recursively_reject_generic_count(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            require(key != "gadget_count", f"forbidden generic gadget_count key at {path}.{key}")
            recursively_reject_generic_count(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            recursively_reject_generic_count(item, f"{path}[{index}]")


def exact_command_probe(ropgadget: dict[str, Any]) -> None:
    """Prove the authority command emits the address-bearing evidence it promises."""

    template = ropgadget.get("command_template")
    require(isinstance(template, list) and all(isinstance(item, str) for item in template), "ROPgadget command template is invalid")
    require("--silent" not in template, "ROPgadget command suppresses required native output")

    with tempfile.TemporaryDirectory(prefix="x64lens-task-command-") as temporary:
        root = Path(temporary)
        tool = root / "ROPgadget"
        target = root / "target.elf"
        target.write_bytes(b"\x7fELFcontrolled")
        tool.write_text(
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "if '--version' in sys.argv:\n"
            "    print('Version: ROPgadget v7.7')\n"
            "    raise SystemExit(0)\n"
            "if '--silent' in sys.argv:\n"
            "    raise SystemExit(0)\n"
            "print('0x0000000000401000 : pop rdi ; ret')\n",
            encoding="utf-8",
        )
        tool.chmod(0o755)
        argv = [str(tool) if item == "<tool>" else str(target) if item == "<target>" else item for item in template]
        result = subprocess.run(
            argv,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
        )
        require(result.returncode == 0, f"controlled ROPgadget command failed with {result.returncode}")
        require(result.stderr == b"", "controlled ROPgadget command emitted unexpected stderr")
        require(
            re.search(rb"(?m)^0x[0-9a-fA-F]+\s*:\s*[^\r\n]*\bretq?\b", result.stdout) is not None,
            "configured ROPgadget command emitted no address-bearing return record",
        )


def main() -> int:
    try:
        authority = load(AUTHORITY)
        spec = load(REFERENCE_SPEC)
        stages = load(STAGES)

        require(authority.get("schema_version") == 3, "unsupported task authority schema")
        require(authority.get("authority_id") == "sprint11-diagnostic-task-definitions-v3", "task authority identity mismatch")
        require(authority.get("evidence_class") == "diagnostic", "task authority must be diagnostic")
        require(authority.get("frozen") is False, "task authority must remain mutable")
        require(authority.get("publication_eligible") is False, "task authority cannot be publication eligible")
        require(authority.get("reference_profile") == "core-1w", "reference profile mismatch")
        require(authority.get("campaign_freeze_sprint") == stages.get("campaign_freeze_sprint") == 15, "campaign freeze mismatch")

        adapter_policy = authority.get("adapter_policy")
        require(isinstance(adapter_policy, dict), "adapter policy is missing")
        require(adapter_policy.get("adapter_id") == "x64lens-sprint11-baseline-output-adapter-v2", "adapter identity mismatch")
        require(adapter_policy.get("adapter_path") == "benchmarks/scripts/baseline-output-adapter.py", "adapter path mismatch")
        require(adapter_policy.get("adapter_schema_version") == 2, "adapter schema mismatch")
        require(adapter_policy.get("native_output_retained") is True, "native output retention is not required")
        require(adapter_policy.get("uncategorized_output_policy") == "reject", "uncategorized output must fail closed")
        require(adapter_policy.get("analysis_authority") is False, "adapter must not become analysis authority")
        require(adapter_policy.get("late_input_reauthentication") is True, "adapter inputs must be reauthenticated after parsing")
        require(adapter_policy.get("campaign_row_binding_required") is True, "adapter must bind one runner row")
        require(adapter_policy.get("raw_line_limit_applied_before_ansi_normalization") is True, "raw line bound must precede ANSI normalization")
        require(adapter_policy.get("atomic_output_commit_with_postcommit_reauthentication") is True, "adapter output transaction is incomplete")
        require(adapter_policy.get("canonical_return_aliases") == {"retq": "ret"}, "return-alias policy mismatch")
        require_executable(adapter_policy["adapter_path"], "baseline adapter")

        x_policy = authority.get("x64lens_relation_policy")
        require(isinstance(x_policy, dict), "x64lens relation policy is missing")
        require(x_policy.get("extractor_id") == "x64lens-sprint11-relation-extractor-v1", "x64lens extractor identity mismatch")
        require(x_policy.get("artifact_schema_version") == 1, "x64lens relation artifact schema mismatch")
        require(x_policy.get("report_schema_version") == "0.2.0" and x_policy.get("report_command") == "gadgets", "x64lens report boundary mismatch")
        require(x_policy.get("campaign_row_binding_required") is True and x_policy.get("measured_phase_required") is True, "x64lens relation must bind one measured row")
        require(x_policy.get("normalized_relation_ids") == ["canonical_exact_pop_rdi_ret", "binary_fact_arg_control_rdi_present"], "x64lens relation set mismatch")
        require(
            x_policy.get("address_coordinates")
            == ["virtual_address_start", "virtual_address_terminator", "file_offset_start", "file_offset_terminator"],
            "x64lens address-coordinate set mismatch",
        )
        require_executable(str(x_policy.get("extractor_path")), "x64lens relation extractor")

        closure_policy = authority.get("runtime_closure_policy")
        require(isinstance(closure_policy, dict), "runtime closure policy is missing")
        require(closure_policy.get("generator_id") == "x64lens-sprint11-runtime-closure-v1", "runtime closure identity mismatch")
        require(closure_policy.get("artifact_schema_version") == 1, "runtime closure artifact schema mismatch")
        require(closure_policy.get("campaign_row_binding_required") is True and closure_policy.get("measured_phase_required") is True, "runtime closure must bind one measured row")
        require(closure_policy.get("closure_modes") == ["native_elf", "python_console_entrypoint", "script_interpreter"], "runtime closure modes changed")
        require(closure_policy.get("completeness_states") == ["complete", "partial"], "runtime closure completeness states changed")
        require_executable(str(closure_policy.get("generator_path")), "runtime closure generator")

        coordinate_policy = authority.get("address_coordinate_policy")
        require(isinstance(coordinate_policy, dict), "address-coordinate policy is missing")
        require(coordinate_policy.get("calibrator_id") == "x64lens-sprint11-address-coordinate-calibrator-v1", "coordinate calibrator identity mismatch")
        roles = coordinate_policy.get("required_roles")
        require(
            roles
            == [
                {"id": "et_exec", "artifact_id": "exec-nopie", "elf_type": "ET_EXEC"},
                {"id": "pie_et_dyn", "artifact_id": "exec-pie", "elf_type": "ET_DYN"},
                {"id": "shared_et_dyn", "artifact_id": "shared", "elf_type": "ET_DYN"},
            ],
            "coordinate role authority mismatch",
        )
        require(coordinate_policy.get("required_tools") == ["x64lens", "ropgadget", "ropper", "ropr"], "coordinate tool set mismatch")
        require(
            coordinate_policy.get("baseline_coordinates")
            == ["virtual_address", "file_offset", "ambiguous", "mismatch", "insufficient_relation_evidence"],
            "coordinate outcome vocabulary mismatch",
        )
        require_executable(str(coordinate_policy.get("calibrator_path")), "address-coordinate calibrator")

        relations = authority.get("normalized_relations")
        require(isinstance(relations, list) and len(relations) == 4, "expected four relation authorities")
        expected_relations = [
            "executable_return_byte_presence",
            "tool_reported_return_terminator_records",
            "canonical_exact_pop_rdi_ret",
            "binary_fact_arg_control_rdi_present",
        ]
        relation_ids = [item.get("id") for item in relations if isinstance(item, dict)]
        require(relation_ids == expected_relations, "relation authority identities or order changed")
        raw_relation = relations[0]
        require(raw_relation.get("status") == "unavailable" and raw_relation.get("scope") == "cross_tool_raw_byte", "raw-byte relation boundary mismatch")
        require(raw_relation.get("substitution_allowed") is False, "decoded baseline records cannot substitute for raw-byte evidence")
        require(all(item.get("status") == "implemented" for item in relations[1:]), "implemented relation status mismatch")
        require(relations[2].get("comparison_key") == ["address", "instructions"], "exact relation key mismatch")
        require(relations[2].get("canonical_instructions") == ["pop rdi", "ret"], "exact relation instruction domain mismatch")

        tasks = authority.get("tasks")
        require(isinstance(tasks, list) and len(tasks) == 3, "expected three x64lens task records")
        by_id = {task.get("id"): task for task in tasks if isinstance(task, dict)}
        require(len(by_id) == 3, "task identities must be unique")
        core = by_id.get("core_scanner")
        gadget = by_id.get("x64lens_gadget_json")
        analyze = by_id.get("x64lens_integrated_analysis_json")
        require(isinstance(core, dict) and core.get("status") == "unavailable" and core.get("substitution_allowed") is False, "core scanner boundary mismatch")
        require(isinstance(gadget, dict) and gadget.get("status") == "implemented" and gadget.get("task_scope") == "gadget_report", "gadget JSON task mismatch")
        require(isinstance(analyze, dict) and analyze.get("status") == "implemented" and analyze.get("task_scope") == "integrated_analysis", "analysis JSON task mismatch")
        require(gadget.get("parity_group") == analyze.get("parity_group"), "current JSON commands must share the command-identity parity group")

        baselines = authority.get("baselines")
        require(isinstance(baselines, list) and len(baselines) == 3, "expected three baseline task records")
        baseline_by_id = {item.get("id"): item for item in baselines if isinstance(item, dict)}
        require(set(baseline_by_id) == {"ropgadget", "ropper", "ropr"}, "baseline identity mismatch")
        require(all(item.get("status") == "implemented" for item in baselines), "baseline adapters must be implemented")
        require(all(item.get("normalization_required") is True for item in baselines), "baseline normalization must remain explicit")
        require(all(item.get("task_scope") == "baseline_gadget_report" for item in baselines), "baseline task scope mismatch")
        require(len({item.get("condition_id") for item in baselines}) == 3, "baseline condition identities must be unique")

        expected_commands = {
            "ropgadget": ["<tool>", "--binary", "<target>", "--depth", "5", "--only", "pop|ret", "--nojop", "--nosys"],
            "ropper": ["<tool>", "--file", "<target>", "--nocolor", "--single", "--type", "rop", "--inst-count", "5"],
            "ropr": ["<tool>", "--colour", "false", "--max-instr", "5", "--nojop", "--nosys", "<target>"],
        }
        version_regexes = {
            "ropgadget": r"^Version:\s+ROPgadget v[0-9][0-9A-Za-z._+-]*$",
            "ropper": r"^Version:\s+Ropper [0-9][0-9A-Za-z._+-]*$",
            "ropr": r"^ropr [0-9][0-9A-Za-z._+-]*$",
        }
        implemented_relations = expected_relations[1:]
        for baseline_id, baseline in baseline_by_id.items():
            require(baseline.get("command_template") == expected_commands[baseline_id], f"{baseline_id} command template mismatch")
            require(baseline.get("version_command_template") == ["<tool>", "--version"], f"{baseline_id} version command mismatch")
            require(baseline.get("normalized_relation_ids") == implemented_relations, f"{baseline_id} relation set mismatch")
            capture = baseline.get("capture_policy")
            require(isinstance(capture, dict), f"{baseline_id} capture policy missing")
            require(capture.get("maximum_stdout_bytes") == 16 * 1024 * 1024, f"{baseline_id} stdout cap mismatch")
            require(capture.get("maximum_stderr_bytes") == 1024 * 1024, f"{baseline_id} stderr cap mismatch")
            require(capture.get("output_limit_outcome") == "output_limit", f"{baseline_id} output-limit outcome mismatch")
            native = baseline.get("native_output_contract")
            require(isinstance(native, dict), f"{baseline_id} native output contract missing")
            require(native.get("maximum_line_bytes") == 8192 and native.get("maximum_line_bytes_scope") == "raw_bytes_before_ansi_normalization", f"{baseline_id} raw line bound mismatch")
            require(native.get("maximum_record_count") == 262144 and native.get("maximum_instruction_count") == 5, f"{baseline_id} parser bounds mismatch")
            require(native.get("return_alias_policy") == {"retq": "ret"}, f"{baseline_id} return alias mismatch")
            adapter = baseline.get("adapter")
            require(isinstance(adapter, dict), f"{baseline_id} adapter contract missing")
            require(
                adapter
                == {
                    "id": adapter_policy["adapter_id"],
                    "path": adapter_policy["adapter_path"],
                    "schema_version": 2,
                    "authority_schema_version": 3,
                    "campaign_row_binding_required": True,
                },
                f"{baseline_id} adapter contract mismatch",
            )
            version_contract = baseline.get("version_contract")
            require(isinstance(version_contract, dict), f"{baseline_id} version contract missing")
            require(version_contract.get("source") == "retained_runner_version_stdout", f"{baseline_id} version source mismatch")
            require(version_contract.get("comparison") == "exact_trimmed_first_line", f"{baseline_id} version comparison mismatch")
            require(version_contract.get("line_regex") == version_regexes[baseline_id], f"{baseline_id} version syntax mismatch")
            require("Only the canonical exact pop-rdi-return relation" in baseline.get("task_equivalence_note", ""), f"{baseline_id} task-equivalence boundary missing")

        exact_command_probe(baseline_by_id["ropgadget"])

        require(spec.get("schema_version") == 2, "reference spec schema mismatch")
        require(spec.get("evidence_class") == "diagnostic", "reference spec must be diagnostic")
        require(spec.get("frozen") is False and spec.get("publication_eligible") is False, "reference spec claim boundary mismatch")
        require(spec.get("capture_limits") == {"maximum_stdout_bytes": 16777216, "maximum_stderr_bytes": 1048576}, "reference capture limits mismatch")
        conditions = spec.get("conditions")
        require(isinstance(conditions, list) and len(conditions) == 2, "reference spec must contain two truthful implemented conditions")
        require({item.get("id") for item in conditions} == {gadget.get("condition_id"), analyze.get("condition_id")}, "reference conditions do not match task authority")
        require(all(item.get("task_scope") != "core_scanner" for item in conditions), "reference spec falsely substitutes a core scanner condition")
        require(all(item.get("profile_id") == "core-1w" and item.get("worker_count") == 1 for item in conditions), "reference profile identity mismatch")
        require({item.get("expected_report_command") for item in conditions} == {"gadgets", "analyze"}, "reference command identities mismatch")

        boundaries = authority.get("claim_boundaries")
        require(isinstance(boundaries, list) and len(boundaries) >= 8, "claim boundaries are incomplete")
        combined = " ".join(str(item) for item in boundaries).lower()
        require("development evidence" in combined and "generic gadget_count" in combined, "diagnostic/publication boundary is incomplete")
        require("adapter consumes" in combined and "authority" in combined, "adapter authority boundary is incomplete")
        require("runner manifest" in combined and "rows.tsv" in combined, "campaign-row binding boundary is incomplete")
        recursively_reject_generic_count(authority)

    except (TaskError, OSError, subprocess.SubprocessError) as exc:
        print(f"diagnostic-task-definitions-smoke: error: {exc}", file=sys.stderr)
        return 1

    implemented = sum(task.get("status") == "implemented" for task in tasks)
    unavailable = sum(task.get("status") == "unavailable" for task in tasks)
    print(
        "diagnostic-task-definitions-smoke: ok "
        f"tasks={len(tasks)} implemented={implemented} unavailable={unavailable} "
        f"baselines={len(baselines)} baseline_adapters=3 relation_authorities={len(relations)} "
        "implemented_relations=3 unavailable_relations=1 x64lens_relation=1 "
        "runtime_closure=1 coordinate_roles=3 exact_command_probe=1 frozen=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
