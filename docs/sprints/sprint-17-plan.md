# Sprint 17 Plan

## Status

Planned publication comparative campaign.

## Sprint goal

Run repeated trials under the frozen methodology and reconcile coverage and
resource results across x64lens and baseline tools.

## Planned deliverables

- [ ] At least 20 measured trials per practical tool/target/profile condition.
- [ ] Raw per-run rows with failures retained.
- [ ] Median, p95, median absolute deviation, min/max, and justified confidence intervals.
- [ ] Coverage tables separating raw, exact, semantic, decoder-backed, unknown, and scored facts.
- [ ] Baseline definition, duplicate, alignment, canonicalization, and work-scope reconciliation.
- [ ] Generated tables and figures from scripts.
- [ ] Frozen result archive and campaign checksum manifest.

## Acceptance criteria

- [ ] Every result traces to raw rows.
- [ ] No method change occurs during the campaign.
- [ ] Runtime/RSS comparisons use task-equivalent or explicitly qualified scopes.
- [ ] Coverage disagreement categories are preserved rather than collapsed.
- [ ] No claim extends beyond the frozen corpus and versions.

## Handoff

Sprint 18 converts measured facts into a defensive triage model without changing
the benchmark dataset.
