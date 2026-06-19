# Sprint 15 Plan

## Status

Planned extended research sprint.

## Sprint goal

Stabilize machine-consumer interfaces for CI, vulnerability-management enrichment, and release compatibility.

## Planned deliverables

- [ ] Freeze schema `0.2.x` fields used by the release campaign.
- [ ] Add schema compatibility and migration tests.
- [ ] Add optional CI policy modes only when their semantics are explicit.
- [ ] Evaluate SARIF as a separate output adapter without changing analysis decisions.
- [ ] Add stable exit-code behavior for policy evaluation.
- [ ] Add representative JSON fixtures for supported report states.
- [ ] Document backward-compatibility guarantees for `v0.1.0`.

## Acceptance criteria

- [ ] Automation outputs are generated from internal facts.
- [ ] Policy failures are distinguishable from parser or runtime failures.
- [ ] SARIF, if added, remains an adapter rather than a second classifier.
- [ ] Schema and CLI compatibility tests pass in native and Docker environments.
- [ ] No breaking schema change occurs after campaign freeze without restarting affected experiments.

## Handoff

Sprint 16 applies the stabilized report and policy surfaces to an operational infrastructure case study.
