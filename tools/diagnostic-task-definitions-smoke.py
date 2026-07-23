#!/usr/bin/env python3
"""Validate Sprint 11 diagnostic task identity and honest scope boundaries."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint11-diagnostic-tasks.json"
REFERENCE_SPEC = ROOT / "benchmarks/specs/sprint11-reference-diagnostic.json"
STAGES = ROOT / "tests/expected/research-stage-gates.json"
ADAPTER = ROOT / "benchmarks/scripts/baseline-output-adapter.py"


class TaskError(RuntimeError):
    pass


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


def recursively_reject_generic_count(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            require(key != "gadget_count", f"forbidden generic gadget_count key at {path}.{key}")
            recursively_reject_generic_count(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            recursively_reject_generic_count(item, f"{path}[{index}]")


def main() -> int:
    try:
        authority = load(AUTHORITY)
        spec = load(REFERENCE_SPEC)
        stages = load(STAGES)

        require(authority.get("schema_version") == 2, "unsupported task authority schema")
        require(authority.get("authority_id") == "sprint11-diagnostic-task-definitions-v2", "task authority identity mismatch")
        require(authority.get("evidence_class") == "diagnostic", "task authority must be diagnostic")
        require(authority.get("frozen") is False, "task authority must remain mutable")
        require(authority.get("publication_eligible") is False, "task authority cannot be publication eligible")
        require(authority.get("reference_profile") == "core-1w", "reference profile mismatch")
        require(authority.get("campaign_freeze_sprint") == stages.get("campaign_freeze_sprint") == 15, "campaign freeze mismatch")

        adapter_policy = authority.get("adapter_policy")
        require(isinstance(adapter_policy, dict), "adapter policy is missing")
        require(adapter_policy.get("adapter_id") == "x64lens-sprint11-baseline-output-adapter-v1", "adapter identity mismatch")
        require(adapter_policy.get("adapter_path") == "benchmarks/scripts/baseline-output-adapter.py", "adapter path mismatch")
        require(adapter_policy.get("native_output_retained") is True, "native output retention is not required")
        require(adapter_policy.get("uncategorized_output_policy") == "reject", "uncategorized output must fail closed")
        require(adapter_policy.get("analysis_authority") is False, "adapter must not become analysis authority")
        require(adapter_policy.get("late_input_reauthentication") is True, "adapter inputs must be reauthenticated after parsing")
        require(ADAPTER.is_file() and ADAPTER.stat().st_mode & 0o111, "baseline adapter is missing or non-executable")

        relations = authority.get("normalized_relations")
        require(isinstance(relations, list) and len(relations) == 4, "expected four relation authorities")
        relation_ids = [item.get("id") for item in relations if isinstance(item, dict)]
        expected_relations = [
            "executable_return_byte_presence",
            "tool_reported_return_terminator_records",
            "canonical_exact_pop_rdi_ret",
            "binary_fact_arg_control_rdi_present",
        ]
        implemented_relations = expected_relations[1:]
        require(relation_ids == expected_relations, "relation authority identities or order changed")
        raw_relation = relations[0]
        require(raw_relation.get("status") == "unavailable", "raw-byte relation must remain explicitly unavailable")
        require(raw_relation.get("scope") == "cross_tool_raw_byte", "raw-byte relation scope mismatch")
        require(raw_relation.get("substitution_allowed") is False, "decoded baseline records cannot substitute for raw-byte evidence")
        require(all(item.get("status") == "implemented" for item in relations[1:]), "implemented relation status mismatch")
        exact_relation = relations[2]
        require(exact_relation.get("scope") == "cross_tool_exact_relation", "exact relation scope mismatch")
        require(exact_relation.get("comparison_key") == ["address", "instructions"], "exact relation key mismatch")
        require(exact_relation.get("canonical_instructions") == ["pop rdi", "ret"], "exact relation instruction domain mismatch")

        tasks = authority.get("tasks")
        require(isinstance(tasks, list) and len(tasks) == 3, "expected three x64lens task records")
        by_id = {task.get("id"): task for task in tasks if isinstance(task, dict)}
        require(len(by_id) == 3, "task identities must be unique")
        core = by_id.get("core_scanner")
        gadget = by_id.get("x64lens_gadget_json")
        analyze = by_id.get("x64lens_integrated_analysis_json")
        require(isinstance(core, dict) and core.get("status") == "unavailable", "core scanner must remain explicitly unavailable")
        require(core.get("substitution_allowed") is False, "report timing cannot substitute for core scanner timing")
        require(isinstance(gadget, dict) and gadget.get("status") == "implemented", "gadget JSON task must be implemented")
        require(isinstance(analyze, dict) and analyze.get("status") == "implemented", "analysis JSON task must be implemented")
        require(gadget.get("parity_group") == analyze.get("parity_group"), "current JSON commands must share the command-identity parity group")
        require(gadget.get("task_scope") == "gadget_report", "gadget task scope mismatch")
        require(analyze.get("task_scope") == "integrated_analysis", "analysis task scope mismatch")

        baselines = authority.get("baselines")
        require(isinstance(baselines, list) and len(baselines) == 3, "expected three baseline task records")
        baseline_by_id = {item.get("id"): item for item in baselines if isinstance(item, dict)}
        require(set(baseline_by_id) == {"ropgadget", "ropper", "ropr"}, "baseline identity mismatch")
        require(all(item.get("status") == "implemented" for item in baselines), "Patch 058 baseline adapters must be implemented")
        require(all(item.get("normalization_required") is True for item in baselines), "baseline normalization must remain explicit")
        require(all(item.get("task_scope") == "baseline_gadget_report" for item in baselines), "baseline task scope mismatch")
        require(len({item.get("condition_id") for item in baselines}) == 3, "baseline condition identities must be unique")

        expected_commands = {
            "ropgadget": ["<tool>", "--binary", "<target>", "--depth", "5", "--only", "pop|ret", "--nojop", "--nosys", "--silent"],
            "ropper": ["<tool>", "--file", "<target>", "--nocolor", "--single", "--type", "rop", "--inst-count", "5"],
            "ropr": ["<tool>", "--colour", "false", "--max-instr", "5", "--nojop", "--nosys", "<target>"],
        }
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
            require(native.get("require_utf8") is True and native.get("require_return_terminated") is True, f"{baseline_id} native parsing boundary mismatch")
            require(native.get("uncategorized_line_policy") == "reject", f"{baseline_id} uncategorized line policy mismatch")
            require(native.get("maximum_line_bytes") == 8192, f"{baseline_id} native line bound mismatch")
            require(native.get("maximum_record_count") == 262144, f"{baseline_id} native record bound mismatch")
            require(native.get("maximum_instruction_count") == 5, f"{baseline_id} native instruction bound mismatch")
            adapter = baseline.get("adapter")
            require(isinstance(adapter, dict) and adapter.get("id") == adapter_policy.get("adapter_id"), f"{baseline_id} adapter mismatch")
            require(adapter.get("path") == adapter_policy.get("adapter_path") and adapter.get("schema_version") == 1, f"{baseline_id} adapter contract mismatch")
            require("Only the canonical exact pop-rdi-return relation" in baseline.get("task_equivalence_note", ""), f"{baseline_id} task-equivalence boundary missing")

        require(spec.get("schema_version") == 2, "reference spec schema mismatch")
        require(spec.get("evidence_class") == "diagnostic", "reference spec must be diagnostic")
        require(spec.get("frozen") is False and spec.get("publication_eligible") is False, "reference spec claim boundary mismatch")
        capture_limits = spec.get("capture_limits")
        require(capture_limits == {"maximum_stdout_bytes": 16777216, "maximum_stderr_bytes": 1048576}, "reference capture limits mismatch")
        conditions = spec.get("conditions")
        require(isinstance(conditions, list) and len(conditions) == 2, "reference spec must contain two truthful implemented conditions")
        condition_ids = {item.get("id") for item in conditions}
        require(condition_ids == {gadget.get("condition_id"), analyze.get("condition_id")}, "reference conditions do not match task authority")
        require(all(item.get("task_scope") != "core_scanner" for item in conditions), "reference spec falsely substitutes a core scanner condition")
        require(all(item.get("profile_id") == "core-1w" and item.get("worker_count") == 1 for item in conditions), "reference profile identity mismatch")
        require({item.get("expected_report_command") for item in conditions} == {"gadgets", "analyze"}, "reference command identities mismatch")

        boundaries = authority.get("claim_boundaries")
        require(isinstance(boundaries, list) and len(boundaries) >= 6, "claim boundaries are incomplete")
        combined = " ".join(str(item) for item in boundaries).lower()
        require("development evidence" in combined and "generic gadget_count" in combined, "diagnostic/publication boundary is incomplete")
        require("adapter consumes" in combined and "authority" in combined, "adapter authority boundary is incomplete")
        recursively_reject_generic_count(authority)

    except TaskError as exc:
        print(f"diagnostic-task-definitions-smoke: error: {exc}", file=sys.stderr)
        return 1

    implemented = sum(task.get("status") == "implemented" for task in tasks)
    unavailable = sum(task.get("status") == "unavailable" for task in tasks)
    print(
        "diagnostic-task-definitions-smoke: ok "
        f"tasks={len(tasks)} implemented={implemented} unavailable={unavailable} "
        f"baselines={len(baselines)} baseline_adapters=3 relation_authorities={len(relations)} "
        f"implemented_relations=3 unavailable_relations=1 frozen=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
