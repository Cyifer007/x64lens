#!/usr/bin/env python3
"""Validate the bounded P087 workload and phase-attribution authority.

The P087 gate freezes denominators and qualification rules.  It deliberately
performs no product timing in its default selftest because the reference binary
has no accepted phase instrumentation profile in the managed cloud stratum.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any


class AuthorityError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise AuthorityError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityError(f"cannot read {path}: {exc}") from exc
    require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def exact_int(value: Any, name: str) -> int:
    require(type(value) is int, f"{name} must be an exact integer")
    return value


def exact_number(value: Any, name: str) -> float:
    require(type(value) in (int, float), f"{name} must be numeric")
    number = float(value)
    require(math.isfinite(number), f"{name} must be finite")
    return number


def validate_authority(a: dict[str, Any]) -> None:
    required = {
        "schema", "sprint", "patch", "evidence_class", "publication_eligible",
        "purpose", "timer_floor_ns", "profiles", "fixtures", "execution_plan",
        "qualification", "decision_boundary", "limitations",
    }
    require(set(a) == required, "authority object has unexpected or missing keys")
    require(a["schema"] == "x64lens-sprint13-workload-phase-attribution-v1", "wrong authority schema")
    require(exact_int(a["sprint"], "sprint") == 13, "wrong sprint")
    require(exact_int(a["patch"], "patch") == 87, "wrong patch")
    require(a["evidence_class"] == "diagnostic", "wrong evidence class")
    require(a["publication_eligible"] is False, "authority must remain publication-ineligible")
    floor = exact_int(a["timer_floor_ns"], "timer_floor_ns")
    require(floor == 6_231_575, "timer floor drift")

    profiles = a["profiles"]
    require(isinstance(profiles, list) and len(profiles) == 2, "expected two profiles")
    ids = [p.get("id") for p in profiles if isinstance(p, dict)]
    require(ids == ["reference", "instrumented"], "profile order or identity drift")
    require(profiles[0] == {"id": "reference", "instrumentation": False, "private_instrumentation_bytes": 0},
            "reference profile drift")
    instrumented = profiles[1]
    require(instrumented.get("instrumentation") is True, "instrumented profile must be enabled")
    require(exact_int(instrumented.get("private_instrumentation_bytes_max"), "profile bytes") == 65_536,
            "instrumentation byte cap drift")
    phases = instrumented.get("required_phases")
    require(phases == ["map_validate", "loader_metadata", "scan_exact", "semantic_effects",
                       "score", "report", "cleanup"], "phase partition drift")

    fixtures = a["fixtures"]
    require(isinstance(fixtures, list) and len(fixtures) == 8, "expected eight fixtures")
    fixture_ids = []
    for index, fixture in enumerate(fixtures):
        require(isinstance(fixture, dict), f"fixture {index} must be an object")
        require(set(fixture) == {"id", "command", "max_depth", "target_role"},
                f"fixture {index} shape drift")
        require(fixture["command"] in {"gadgets", "analyze", "mitigations"},
                f"fixture {index} command unsupported")
        if fixture["command"] == "mitigations":
            require(fixture["max_depth"] is None, f"fixture {index} mitigation max-depth must be null")
        else:
            require(type(fixture["max_depth"]) is int and fixture["max_depth"] in {4, 8},
                    f"fixture {index} invalid max-depth")
        fixture_ids.append(fixture["id"])
    require(len(set(fixture_ids)) == 8, "fixture IDs must be unique")

    plan = a["execution_plan"]
    require(isinstance(plan, dict), "execution_plan must be an object")
    expected_plan = {
        "warmups_per_profile_fixture": 1,
        "measured_runs_per_profile_fixture": 9,
        "profile_fixture_cells": 16,
        "warmup_executions": 16,
        "measured_executions": 144,
        "total_executions": 160,
        "counterbalance": "deterministic-paired-alternation",
        "cache_policy": "warm-uncontrolled-diagnostic",
    }
    require(plan == expected_plan, "execution denominator drift")

    q = a["qualification"]
    require(isinstance(q, dict), "qualification must be an object")
    require(exact_number(q.get("minimum_median_timer_floor_multiple"), "floor multiple") == 5.0,
            "floor multiple drift")
    require(exact_int(q.get("minimum_qualified_median_ns"), "minimum median") == floor * 5,
            "minimum median must equal five timer floors")
    require(exact_number(q.get("maximum_mad_to_median_ratio"), "MAD ratio") == 0.10,
            "MAD threshold drift")
    require(exact_number(q.get("maximum_phase_sum_residual_ratio"), "phase residual") == 0.05,
            "phase residual threshold drift")
    require(exact_number(q.get("maximum_instrumented_to_reference_ratio"), "overhead") == 1.03,
            "overhead threshold drift")
    require(exact_int(q.get("minimum_qualified_fixtures"), "minimum qualified fixtures") == 6,
            "qualified-fixture threshold drift")
    require(q.get("require_normalized_public_output_equality") is True, "output equality must be required")
    require(q.get("require_zero_regressions") is True and q.get("require_zero_failures") is True,
            "failure/regression closure must be exact")
    require(exact_int(q.get("private_instrumentation_bytes_max"), "instrumentation cap") == 65_536,
            "qualification instrumentation cap drift")

    boundary = a["decision_boundary"]
    require(boundary == {
        "reporter_batching_considered_only_if_report_share_at_least": 0.20,
        "scan_prefilter_considered_only_if_scan_share_at_least": 0.40,
        "no_optimization_selected_by_this_authority": True,
        "no_performance_claim_authorized": True,
        "no_public_fields_added": True,
        "no_semantic_changes": True,
        "no_score_changes": True,
        "schema_changed": False,
    }, "decision boundary drift")
    require(isinstance(a["limitations"], list) and len(a["limitations"]) >= 4,
            "limitations must remain explicit")


def validate_expected(e: dict[str, Any]) -> None:
    required = {
        "schema", "sprint", "patch", "decision", "fixtures", "profiles",
        "profile_fixture_cells", "warmup_executions", "measured_executions",
        "total_executions", "required_qualified_fixtures", "minimum_qualified_median_ns",
        "maximum_mad_to_median_ratio", "maximum_phase_sum_residual_ratio",
        "maximum_instrumented_to_reference_ratio", "private_instrumentation_bytes_max",
        "executed", "qualified_fixtures", "public_fields_added", "semantic_changes",
        "score_changes", "schema_changed", "publication_eligible",
    }
    require(set(e) == required, "expected object has unexpected or missing keys")
    require(e["schema"] == "x64lens-sprint13-workload-phase-attribution-result-v1", "wrong result schema")
    require(e["sprint"] == 13 and e["patch"] == 87, "expected identity drift")
    require(e["decision"] == "authority_frozen_execution_deferred", "wrong deferred decision")
    require(e["fixtures"] == 8 and e["profiles"] == 2 and e["profile_fixture_cells"] == 16,
            "expected cell denominators drift")
    require(e["warmup_executions"] == 16 and e["measured_executions"] == 144
            and e["total_executions"] == 160, "expected execution denominators drift")
    require(e["executed"] is False and e["qualified_fixtures"] is None,
            "P087 must not invent an executed cloud result")
    require(e["public_fields_added"] == 0 and e["semantic_changes"] == 0
            and e["score_changes"] == 0 and e["schema_changed"] is False,
            "public/runtime boundary drift")
    require(e["publication_eligible"] is False, "expected result must remain diagnostic")


def synthetic_result(authority: dict[str, Any]) -> dict[str, Any]:
    floor = authority["timer_floor_ns"]
    fixtures = []
    for index, fixture in enumerate(authority["fixtures"]):
        reference = [floor * 6 + index * 1000 + delta for delta in (-4000, -3000, -2000, -1000, 0, 1000, 2000, 3000, 4000)]
        instrumented = [int(value * 1.02) for value in reference]
        median = statistics.median(reference)
        mad = statistics.median(abs(value - median) for value in reference)
        phase_sum = statistics.median(instrumented) * 0.99
        fixtures.append({
            "id": fixture["id"],
            "reference_ns": reference,
            "instrumented_ns": instrumented,
            "reference_median_ns": median,
            "reference_mad_ns": mad,
            "phase_sum_median_ns": phase_sum,
            "output_equal": True,
            "failures": 0,
            "regressions": 0,
        })
    return {"fixtures": fixtures, "private_instrumentation_bytes": 65_536}


def qualify(authority: dict[str, Any], result: dict[str, Any]) -> int:
    require(set(result) == {"fixtures", "private_instrumentation_bytes"}, "result shape drift")
    require(result["private_instrumentation_bytes"] <= authority["qualification"]["private_instrumentation_bytes_max"],
            "private instrumentation cap exceeded")
    records = result["fixtures"]
    require(isinstance(records, list) and len(records) == 8, "result must contain eight fixtures")
    q = authority["qualification"]
    qualified = 0
    for record in records:
        reference = record["reference_ns"]
        instrumented = record["instrumented_ns"]
        require(len(reference) == 9 and len(instrumented) == 9, "each profile requires nine measured rows")
        require(all(type(value) is int and value > 0 for value in reference + instrumented), "timings must be positive integers")
        median = statistics.median(reference)
        mad = statistics.median(abs(value - median) for value in reference)
        inst_median = statistics.median(instrumented)
        phase_sum = exact_number(record["phase_sum_median_ns"], "phase sum")
        require(record["reference_median_ns"] == median and record["reference_mad_ns"] == mad,
                "stored summary does not match raw timings")
        conditions = [
            median >= q["minimum_qualified_median_ns"],
            (mad / median) <= q["maximum_mad_to_median_ratio"],
            abs(phase_sum - inst_median) / inst_median <= q["maximum_phase_sum_residual_ratio"],
            inst_median / median <= q["maximum_instrumented_to_reference_ratio"],
            record["output_equal"] is True,
            record["failures"] == 0,
            record["regressions"] == 0,
        ]
        qualified += int(all(conditions))
    require(qualified >= q["minimum_qualified_fixtures"], "fewer than six fixtures qualified")
    return qualified


def selftest(authority_path: Path, expected_path: Path) -> None:
    authority = load_json(authority_path)
    expected = load_json(expected_path)
    validate_authority(authority)
    validate_expected(expected)
    result = synthetic_result(authority)
    require(qualify(authority, result) == 8, "valid synthetic result did not qualify")

    mutations = 0
    for mutator in (
        lambda value: value["execution_plan"].__setitem__("total_executions", 159),
        lambda value: value["qualification"].__setitem__("minimum_qualified_fixtures", 5),
        lambda value: value["decision_boundary"].__setitem__("no_performance_claim_authorized", False),
        lambda value: value["profiles"][1].__setitem__("private_instrumentation_bytes_max", 65_537),
    ):
        changed = copy.deepcopy(authority)
        mutator(changed)
        try:
            validate_authority(changed)
        except AuthorityError:
            mutations += 1
        else:
            raise AuthorityError("authority mutation was accepted")

    for mutator in (
        lambda value: value.__setitem__("private_instrumentation_bytes", 65_537),
        lambda value: value["fixtures"][0].__setitem__("output_equal", False),
        lambda value: value["fixtures"][0].__setitem__("phase_sum_median_ns", value["fixtures"][0]["instrumented_ns"][4] * 0.80),
        lambda value: value["fixtures"][0].__setitem__("instrumented_ns", [int(v * 1.08) for v in value["fixtures"][0]["reference_ns"]]),
    ):
        changed = copy.deepcopy(result)
        mutator(changed)
        try:
            qualify(authority, changed)
        except AuthorityError:
            mutations += 1
        else:
            # One failed fixture may still leave seven qualified; force the gate by
            # applying the same defect to three fixtures when needed.
            if mutator.__code__.co_firstlineno:
                for record in changed["fixtures"][1:3]:
                    if record.get("output_equal") is True:
                        record["output_equal"] = False
                try:
                    qualify(authority, changed)
                except AuthorityError:
                    mutations += 1
                else:
                    raise AuthorityError("result mutation was accepted")

    print(
        "sprint13-workload-phase-attribution-smoke: ok "
        "fixtures=8 profiles=2 cells=16 warmups=16 measured=144 executions=160 "
        "minimum_qualified=6 floor_multiple=5 max_dispersion=0.10 "
        "max_phase_residual=0.05 max_overhead=1.03 private_bytes=65536 "
        f"mutation_rejections={mutations} execution=deferred public_fields_added=0 "
        "semantic_changes=0 score_changes=0 schema_changed=0"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("selftest")
    check.add_argument("--authority", type=Path, required=True)
    check.add_argument("--expected", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "selftest":
        selftest(args.authority, args.expected)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuthorityError as exc:
        print(f"sprint13-workload-phase-attribution-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
