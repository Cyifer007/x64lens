# Sprint 14 Plan

## Status

Planned extended research sprint.

## Sprint goal

Create an evidence-backed defensive triage layer that combines mitigation state, primitive coverage, scores, provenance, and uncertainty.

## Planned deliverables

- [ ] Define a binary-level triage summary distinct from per-gadget score.
- [ ] Separate observed facts, heuristic interpretation, and limitations.
- [ ] Add representative primitive selection without hiding the full candidate set.
- [ ] Add mitigation-aware constraints, for example NX, PIE, RELRO, canary, and CET/IBT indicators.
- [ ] Add confidence and evidence references for each interpretation.
- [ ] Define what the tool can recommend to defenders without claiming vulnerability or exploitability.
- [ ] Add controlled tests for contradictory or incomplete evidence.

## Acceptance criteria

- [ ] Reports never state that a binary is exploitable without an independent vulnerability and runtime context.
- [ ] Triage conclusions can be traced to machine-readable facts.
- [ ] Unknown mitigation or candidate state remains visible.
- [ ] Per-gadget score and binary-level triage are separate concepts.
- [ ] Text and JSON remain consistent.

## Handoff

Sprint 15 stabilizes automation interfaces and schema behavior around the triage model.
