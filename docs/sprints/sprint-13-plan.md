# Sprint 13 Plan

## Status

Planned extended research sprint.

## Sprint goal

Run the fixed comparative benchmark campaign and reconcile coverage definitions across x64lens and baseline tools.

## Planned deliverables

- [ ] Freeze baseline tool versions and commands.
- [ ] Run at least 20 measured trials per tool/target condition where practical.
- [ ] Preserve raw per-run rows and environment metadata.
- [ ] Compute median, p95, median absolute deviation, and confidence intervals where justified.
- [ ] Reconcile raw, exact, semantic, decoded-valid, and baseline gadget definitions.
- [ ] Measure candidate and output-count differences separately from runtime.
- [ ] Record failed or unsupported targets rather than dropping them.
- [ ] Generate tables and figures from scripts.

## Acceptance criteria

- [ ] Every reported result can be traced to raw rows.
- [ ] Coverage comparisons state the compared definition.
- [ ] No claim extends beyond the measured corpus and versions.
- [ ] Timing and RSS summaries are reproducible from committed scripts.
- [ ] Any method change triggers a documented campaign restart or separate dataset.

## Handoff

Sprint 14 uses measured facts to refine mitigation-aware defensive triage without changing the benchmark dataset.
