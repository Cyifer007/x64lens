# Sprint 18 Plan

## Status

Planned defensive triage sprint.

## Sprint goal

Create an evidence-backed binary-level triage layer that combines mitigation,
primitive coverage, score, provenance, completeness, and uncertainty without
claiming exploitability.

## Planned deliverables

- [ ] Binary-level triage record separate from per-candidate score.
- [ ] Observed facts, heuristic interpretation, confidence, and limitations as separate fields.
- [ ] Representative primitive selection without hiding the full candidate set.
- [ ] Mitigation-aware constraints including PIE/DSO, RELRO, NX, canary, IBT, and SHSTK when known.
- [ ] Controlled contradictory and incomplete-evidence fixtures.
- [ ] Analyst task definitions for later case-study use.

## Acceptance criteria

- [ ] Every conclusion traces to machine-readable facts.
- [ ] Unknown state remains visible.
- [ ] Reports never state that a binary is exploitable without an independent vulnerability and runtime context.
- [ ] Text and JSON agree.
- [ ] Benchmark data remains frozen.

## Handoff

Sprint 19 stabilizes automation and compatibility around the triage model.
