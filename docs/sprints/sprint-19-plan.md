# Sprint 19 Plan

## Status

Planned automation and schema-stabilization sprint.

## Sprint goal

Stabilize machine-consumer interfaces for CI/CD, vulnerability-management
enrichment, and release compatibility.

## Planned deliverables

- [ ] Freeze release-facing schema `0.2.x` fields and compatibility guarantees.
- [ ] Add migration and representative state tests.
- [ ] Define optional CI policy modes with distinct policy exit semantics.
- [ ] Evaluate SARIF as a report adapter without duplicating analysis logic.
- [ ] Add machine-consumer compatibility tests in native and Docker environments.
- [ ] Document automation limitations and policy/analysis error separation.

## Acceptance criteria

- [ ] Automation outputs derive only from internal facts.
- [ ] Policy failures are distinguishable from parser or runtime failures.
- [ ] SARIF, if retained, remains an adapter.
- [ ] Any schema change affecting the frozen campaign is versioned and reconciled.

## Handoff

Sprint 20 applies the stabilized surfaces to a reproducible infrastructure case
study.
