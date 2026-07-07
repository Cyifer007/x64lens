# ADR 0025: Sprint 8 closeout correction

## Status

Accepted for Sprint 8 Patch 039.

## Context

Patch 038 closed the public Sprint 8 plan and hardened optional comparator
helpers, but local validation found three closeout defects before the sprint
could be accepted as final:

1. `make benchmark-integrity-smoke` did not generate the intended
   non-finite-RSS fixtures: `nan-rss.tsv`, `inf-rss.tsv`, and
   `neg-inf-rss.tsv`.
2. `SHELLCHECK_STRICT=1 make shellcheck-smoke` still reported actionable
   shell-helper findings.
3. The private local project-context handoff was stale and still described
   Patch 029 / Sprint 7 as the current state.

The analyzer runtime and Docker validation passed. The defect was in closeout
validation/tooling and private context freshness, not in ELF parsing, mitigation
facts, section-label handling, or gadget reporting.

## Decision

Patch 039 is the Sprint 8 closeout correction:

- `tools/benchmark-integrity-smoke.py` now generates and validates explicit
  `maxrss_kb` non-finite cases for `nan`, `inf`, and `-inf`.
- The patch-bundle hygiene script avoids overlapping shell `case` patterns for
  unsafe paths, and planning-doc checks document the intentional literal
  Markdown backticks that strict shell lint flagged.
- The closeout context refresh is regenerated from the post-Patch-039 state.
  Public project context and private local orchestration are packaged as
  separate local-only bundles and patches, not as public product artifacts.
- Patch 038 remains part of the historical public record, but Sprint 8 is not
  considered closed until Patch 039 validation passes.

## Consequences

Sprint 8 closeout now has an explicit correction record. The public repository
keeps optional comparison and benchmark-integrity tooling as development and
review evidence, not publication evidence. Private orchestration/context files
remain outside the public repository and must be refreshed at major sprint
milestones rather than after every patch.

Sprint 9 should begin only after this correction validates natively and in
Docker, with the next implementation focus on report identity, evidence
provenance, candidate completeness, and schema `0.2.0`.
