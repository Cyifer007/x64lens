#!/usr/bin/env python3
"""Validate the measured Sprint 12 overlap-normalization decision authority."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "benchmarks/task-definitions/sprint12-overlap-normalization-decision.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    value = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    require(value.get("schema_version") == 1, "unexpected overlap decision schema")
    require(value.get("evidence_class") == "diagnostic", "overlap decision is not diagnostic")
    require(value.get("frozen") is False, "overlap decision must remain unfrozen")
    require(value.get("publication_eligible") is False, "overlap decision cannot be publication evidence")
    require(value.get("decision") == "defer_normalization_preserve_provenance", "normalization is not deferred")

    scope = value.get("scope")
    observations = value.get("observations")
    thresholds = value.get("activation_thresholds")
    retained = value.get("retained_architecture")
    require(isinstance(scope, dict) and isinstance(observations, dict), "missing overlap scope or observations")
    require(isinstance(thresholds, dict) and isinstance(retained, dict), "missing overlap thresholds or architecture")
    require(scope.get("combined_targets") == 3115, "combined target count changed")
    require(scope.get("combined_executable_targets") == 3106, "executable target count changed")
    require(observations.get("overlap_targets") == 0, "overlap incidence no longer matches the decision")
    require(observations.get("same_slope_repeated_bytes") == 0, "repeated-byte observation changed")
    require(observations.get("repeated_exact_identities") == 0, "repeated identity observation changed")
    require(observations.get("capacity_slots_recovered_by_overlap_normalization") == 0, "capacity recovery changed")
    require(observations.get("capacity_outcomes_changed") == 0, "capacity outcome observation changed")
    require(thresholds.get("minimum_same_slope_repeated_byte_fraction") == 0.05, "repeated-byte threshold changed")
    require(thresholds.get("minimum_repeated_exact_identities") == 41, "identity threshold changed")
    require(thresholds.get("minimum_targets_meeting_a_threshold") == 2, "target threshold changed")
    require(retained.get("region_provenance") == "retained", "lossless region provenance was removed")
    require(retained.get("candidate_contributor_mask") == "retained", "candidate contributor provenance was removed")
    require(retained.get("scan_unioning") == "not_implemented", "scan unioning was activated without a new decision")
    require(retained.get("candidate_identity_deduplication") == "not_implemented", "identity deduplication was activated")
    require(retained.get("candidate_capacity") == 4096, "candidate capacity changed")
    require("gadget_count" not in json.dumps(value), "generic gadget_count appeared in overlap authority")

    evidence = value.get("source_evidence")
    require(isinstance(evidence, list) and len(evidence) == 3, "source evidence inventory changed")
    for record in evidence:
        require(isinstance(record, dict) and set(record) == {"artifact", "sha256"}, "malformed source evidence record")
        digest = record["sha256"]
        require(isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
                "invalid source evidence digest")

    print(
        "sprint12-overlap-decision-smoke: ok "
        "targets=3115 executable=3106 overlaps=0 repeated_bytes=0 repeated_identities=0 "
        "normalization=deferred provenance=retained"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"sprint12-overlap-decision-smoke: error: {exc}", file=sys.stderr)
        raise SystemExit(1)
