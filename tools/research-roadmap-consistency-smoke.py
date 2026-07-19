#!/usr/bin/env python3
"""Validate current roadmap chronology across active public authority documents."""
from __future__ import annotations

import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STAGE_SPEC = ROOT / "tests/expected/research-stage-gates.json"


class ContractError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def read(path: str) -> str:
    candidate = ROOT / path
    require(candidate.is_file(), f"missing authority document: {path}")
    return candidate.read_text(encoding="utf-8")


ACTIVE_AUTHORITY_PATHS = (
    "README.md",
    "docs/backlog.md",
    "docs/benchmark-methodology.md",
    "docs/benchmark-smoke-interpretation.md",
    "docs/design/benchmark-and-capability-stage-gates.md",
    "docs/design/candidate-scoped-decoder-and-parallelism.md",
    "docs/design/decoder-roadmap.md",
    "docs/design/defensive-deployment-profile.md",
    "docs/design/metric-boundaries.md",
    "docs/project-charter.md",
    "docs/publication-plan.md",
    "docs/research-release-plan.md",
    "docs/research-roadmap.md",
    "docs/roadmap-22-sprints.md",
    "docs/sprints/sprint-10-plan.md",
    "docs/versioning.md",
    *tuple(f"docs/sprints/sprint-{sprint:02d}-plan.md" for sprint in range(11, 23)),
)

REQUIRED_TEXT = {
    "README.md": (
        "Sprints 1 through 10 are complete",
        "Sprint 11 is active",
        "Sprint 15",
        "Sprint 16",
        "Sprint 17",
        "Sprint 22",
    ),
    "docs/roadmap-22-sprints.md": (
        "Sprints 1 through 10 are complete",
        "Sprint 11 is active",
        "Diagnostic measurement checkpoint",
        "Campaign freeze",
        "Research preview candidate",
        "Publication campaign",
        "First research release",
    ),
    "docs/research-roadmap.md": (
        "Sprints 1 through 10 are complete",
        "Sprint 11 is active",
        "Sprint 15 freezes",
        "Sprint 17 runs publication-grade",
    ),
    "docs/sprints/sprint-10-plan.md": (
        "Closed by Patch 054",
        "Sprint 11",
        "Sprint 15",
    ),
    "docs/sprints/sprint-11-plan.md": (
        "Active diagnostic measurement sprint",
        "Final corpus freeze",
    ),
    "docs/benchmark-methodology.md": (
        "Sprint 11",
        "Sprint 15",
        "Sprint 17",
    ),
    "docs/research-release-plan.md": (
        "Sprint 11",
        "Sprint 15",
        "Sprint 16",
        "Sprint 17",
        "Sprint 22",
    ),
}

FORBIDDEN_ACTIVE_CLAIMS = tuple(
    re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    for pattern in (
        r"Sprint 11\s+(?:freezes|will freeze|owns the freeze)",
        r"freeze(?:s|d)?\s+(?:the\s+)?(?:preview\s+)?corpus\s+in\s+Sprint 11",
        r"Sprint 12\s+(?:builds|introduces|owns)\s+(?:the\s+)?high-resolution\s+(?:runner|timing)",
        r"Sprint 13\s+(?:runs|owns|performs)\s+(?:the\s+)?(?:fixed|publication-grade)\s+comparative",
        r"Sprint 18\s+(?:publishes|performs|owns)\s+(?:the\s+)?first\s+research\s+release",
        r"current\s+release\s+candidate",
        r"requires\s+competitive\s+evidence",
        r"decoder\s+profile\s+(?:is|may be)\s+admitted\s+.*Sprint 17",
        r"Sprint 19\s+(?:freezes|will freeze)\s+.*schema",
    )
)


# Patch 055 preserves path-specific stale wording that previously escaped the
# broad chronology patterns. These literals are intentionally maintained as
# regression authorities: a future editorial rewrite may replace a literal only
# when the corresponding negative case is updated in the corrective smoke.
FORBIDDEN_PATH_CLAIMS = {
    "docs/backlog.md": (
        "Sprint 13 coverage",
        "Sprint 11 corpus freeze",
    ),
    "docs/benchmark-methodology.md": (
        "Sprint 12 should introduce",
        "Before Sprint 13 repeated trials",
    ),
    "docs/benchmark-smoke-interpretation.md": (
        "Sprint 12 replaces this path",
    ),
    "docs/design/decoder-roadmap.md": (
        "Sprint 12 and Sprint 13 own the measurement",
    ),
    "docs/sprints/sprint-19-plan.md": (
        "Freeze release-facing schema",
    ),
}


def main() -> int:
    try:
        spec = json.loads(STAGE_SPEC.read_text(encoding="utf-8"))
        milestones = (
            spec.get("diagnostic_sprint"),
            spec.get("campaign_freeze_sprint"),
            spec.get("preview_sprint"),
            spec.get("publication_campaign_sprint"),
            spec.get("release_sprint"),
        )
        require(milestones == (11, 15, 16, 17, 22), f"milestone mismatch: {milestones!r}")
        require(spec.get("completed_sprints") == 10, "completed_sprints must be 10")
        require(spec.get("active_sprint") == 11, "active_sprint must be 11")

        scanned = 0
        path_claims_checked = 0
        for path in ACTIVE_AUTHORITY_PATHS:
            text = read(path)
            scanned += 1
            for expression in FORBIDDEN_ACTIVE_CLAIMS:
                match = expression.search(text)
                require(match is None, f"{path}: stale active chronology: {match.group(0)!r}" if match else "")
            for literal in FORBIDDEN_PATH_CLAIMS.get(path, ()):
                path_claims_checked += 1
                require(literal.casefold() not in text.casefold(), f"{path}: stale path-specific chronology: {literal!r}")

        for path, needles in REQUIRED_TEXT.items():
            text = read(path)
            for needle in needles:
                require(needle in text, f"{path}: missing canonical chronology text: {needle!r}")

    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"research-roadmap-consistency-smoke: error: {exc}", file=sys.stderr)
        return 1

    print(
        "research-roadmap-consistency-smoke: ok "
        f"documents={scanned} milestones=5 forbidden_patterns={len(FORBIDDEN_ACTIVE_CLAIMS)} "
        f"path_claims={path_claims_checked} completed_sprints=10 active_sprint=11"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
