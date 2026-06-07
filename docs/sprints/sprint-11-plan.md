# Sprint 11 Plan

## Status

Candidate extended-semester sprint.

## Sprint goal

Integrate mitigation context, primitive coverage, and scoring into a coherent analysis report.

## Planned deliverables

- [ ] Produce a single `analyze` report combining target metadata, mitigations, primitive coverage, representative gadgets, scores, and limitations.
- [ ] Add mitigation-aware interpretation without claiming exploitability.
- [ ] Add JSON output parity for the text report.
- [ ] Add limitations block to every JSON report.
- [ ] Add optional CI-friendly nonzero policy modes only if clearly documented.

## Acceptance criteria

- [ ] `analyze` output is useful for defensive triage.
- [ ] Output distinguishes facts, heuristics, limitations, and future work.
- [ ] JSON validates against the repository schema.
