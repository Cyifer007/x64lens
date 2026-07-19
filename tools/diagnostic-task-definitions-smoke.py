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


def main() -> int:
    try:
        authority = load(AUTHORITY)
        spec = load(REFERENCE_SPEC)
        stages = load(STAGES)

        require(authority.get("schema_version") == 1, "unsupported task authority schema")
        require(authority.get("evidence_class") == "diagnostic", "task authority must be diagnostic")
        require(authority.get("frozen") is False, "task authority must remain mutable")
        require(authority.get("publication_eligible") is False, "task authority cannot be publication eligible")
        require(authority.get("reference_profile") == "core-1w", "reference profile mismatch")
        require(authority.get("campaign_freeze_sprint") == stages.get("campaign_freeze_sprint") == 15, "campaign freeze mismatch")

        tasks = authority.get("tasks")
        require(isinstance(tasks, list) and len(tasks) == 3, "expected three task records")
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
        require({item.get("id") for item in baselines} == {"ropgadget", "ropper", "ropr"}, "baseline identity mismatch")
        require(all(item.get("status") == "planned" for item in baselines), "Patch 055 must not imply baseline adapters are complete")
        require(all(item.get("normalization_required") is True for item in baselines), "baseline normalization must remain explicit")

        require(spec.get("schema_version") == 1, "reference spec schema mismatch")
        require(spec.get("evidence_class") == "diagnostic", "reference spec must be diagnostic")
        require(spec.get("frozen") is False and spec.get("publication_eligible") is False, "reference spec claim boundary mismatch")
        conditions = spec.get("conditions")
        require(isinstance(conditions, list) and len(conditions) == 2, "reference spec must contain two truthful implemented conditions")
        condition_ids = {item.get("id") for item in conditions}
        require(condition_ids == {gadget.get("condition_id"), analyze.get("condition_id")}, "reference conditions do not match task authority")
        require(all(item.get("task_scope") != "core_scanner" for item in conditions), "reference spec falsely substitutes a core scanner condition")
        require(all(item.get("profile_id") == "core-1w" and item.get("worker_count") == 1 for item in conditions), "reference profile identity mismatch")
        require({item.get("expected_report_command") for item in conditions} == {"gadgets", "analyze"}, "reference command identities mismatch")

        boundaries = authority.get("claim_boundaries")
        require(isinstance(boundaries, list) and len(boundaries) >= 4, "claim boundaries are incomplete")
        combined = " ".join(str(item) for item in boundaries).lower()
        require("development evidence" in combined and "generic gadget_count" in combined, "diagnostic/publication boundary is incomplete")

    except TaskError as exc:
        print(f"diagnostic-task-definitions-smoke: error: {exc}", file=sys.stderr)
        return 1

    implemented = sum(task.get("status") == "implemented" for task in tasks)
    unavailable = sum(task.get("status") == "unavailable" for task in tasks)
    print(
        "diagnostic-task-definitions-smoke: ok "
        f"tasks={len(tasks)} implemented={implemented} unavailable={unavailable} "
        f"baselines={len(baselines)} frozen=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
