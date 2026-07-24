#!/usr/bin/env python3
"""Validate the preregistered whole-batch timing policy for below-floor rows.

This gate does not manufacture per-invocation latency.  It verifies that a later
batch campaign must retain whole-batch observations, use a contemporaneous floor,
require stable repeated batches, and compare only equal K values.
"""
from __future__ import annotations

import json
from pathlib import Path
import statistics
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "benchmarks/task-definitions/sprint11-p060-campaign-plan.json"


class PolicyError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PolicyError(message)


def median_absolute_deviation(values: Iterable[int]) -> float:
    sample = list(values)
    center = statistics.median(sample)
    return float(statistics.median(abs(value - center) for value in sample))


def eligible(values: list[int], *, floor_ns: int, minimum_batches: int, multiplier: int, maximum_ratio: float) -> bool:
    if len(values) < minimum_batches:
        return False
    center = float(statistics.median(values))
    if center < floor_ns * multiplier:
        return False
    return median_absolute_deviation(values) / center <= maximum_ratio


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    policy = plan["execution_policy"]["below_floor_protocol"]
    require(policy["status"] == "preregistered_not_yet_executed", "below-floor policy state changed")
    require(policy["whole_batch_sizes"] == [2, 4, 8, 16, 32, 64], "whole-batch size sequence changed")
    require(policy["minimum_batches"] >= 9, "too few whole batches are required")
    require(policy["eligibility_floor_multiplier"] >= 5, "whole-batch floor multiplier is too small")
    require(policy["maximum_mad_over_median"] <= 0.10, "whole-batch dispersion bound is too loose")
    require(policy["same_k_comparisons_only"] is True, "cross-K comparison was enabled")
    require(policy["divide_batch_time_into_single_run_latency"] is False, "batch time division was enabled")
    require(policy["prefer_larger_same_task_target"] is True, "larger same-task targets are no longer preferred")
    require(policy["fixed_affinity_when_available"] is True, "affinity policy changed")

    floor = 6_361_100
    minimum = policy["minimum_batches"]
    multiplier = policy["eligibility_floor_multiplier"]
    ratio = policy["maximum_mad_over_median"]
    stable = [40_000_000, 41_000_000, 39_500_000, 40_500_000, 40_250_000, 39_750_000, 40_100_000, 40_300_000, 39_900_000]
    below = [12_000_000] * minimum
    unstable = [34_000_000, 60_000_000, 35_000_000, 61_000_000, 36_000_000, 62_000_000, 37_000_000, 63_000_000, 38_000_000]
    require(eligible(stable, floor_ns=floor, minimum_batches=minimum, multiplier=multiplier, maximum_ratio=ratio), "stable above-floor whole batches were rejected")
    require(not eligible(below, floor_ns=floor, minimum_batches=minimum, multiplier=multiplier, maximum_ratio=ratio), "below-floor batches were accepted")
    require(not eligible(unstable, floor_ns=floor, minimum_batches=minimum, multiplier=multiplier, maximum_ratio=ratio), "unstable batches were accepted")

    print(
        "sprint11-below-floor-policy-smoke: ok "
        "batch_sizes=6 minimum_batches=9 floor_multiplier=5 mad_ratio=0.10 "
        "same_k_only=1 divided_latency=0 controls=3"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, PolicyError) as exc:
        print(f"sprint11-below-floor-policy-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
