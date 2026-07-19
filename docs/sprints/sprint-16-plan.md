# Sprint 16 Plan

## Status

Planned research preview sprint.

## Sprint goal

Run a frozen high-resolution pilot campaign and prepare `v0.1.0-rc1` for
structured external feedback.

## Planned deliverables

- [ ] Pilot runs across every frozen condition and available baseline.
- [ ] Raw rows, generated summaries, timer-floor evidence, and environment metadata.
- [ ] Preview coverage reconciliation and explicit unsupported conditions.
- [ ] Source, binary, checksum, version, corpus, benchmark, and reproduction artifacts.
- [ ] Preview claim-to-evidence table and threats-to-validity update.
- [ ] `v0.1.0-rc1` tag only when every preview gate passes.

## Acceptance criteria

- [ ] Pilot results regenerate from raw rows.
- [ ] No diagnostic rows are merged into the frozen pilot.
- [ ] Native and Docker validation pass.
- [ ] Release archives and checksums verify.
- [ ] Preview claims remain bounded to measured versions, targets, tasks, and profiles.

## Handoff

Sprint 17 runs the publication-grade repeated campaign without changing the
frozen method.
