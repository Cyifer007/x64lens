# ADR 0012: Expand the Roadmap and Use Evidence-Based Research Release Gates

## Status

Accepted for Sprint 6 Patch 024.

## Context

The original six-sprint plan expanded to twelve sprints as implementation progressed faster than expected. By Sprint 6, x64lens had already delivered an integrated `analyze` command, scoring, JSON, system-binary validation, baseline smoke benchmarking, and a repeatable checkpoint demo.

Continuing with the old sprint boundaries would create two risks:

1. broadening primitive coverage before parser safety and candidate validity are measured,
2. treating benchmark plumbing as publication evidence before corpus and measurement controls are mature.

## Decision

Adopt an eighteen-sprint roadmap with three explicit gates:

- completed `v0.1.0-dev` integrated checkpoint,
- `v0.1.0-rc1` research preview candidate after Sprint 12,
- `v0.1.0` first research release after Sprint 18.

Reorder the next implementation tranche so hostile-input hardening and mitigation accuracy precede primitive breadth. Add evidence provenance and schema evolution before research-grade benchmark collection.

## Consequences

Positive consequences:

- parser and release risks are addressed before larger claims,
- candidate validity can improve without replacing the raw scanner,
- benchmark campaigns gain stable corpus, schema, and measurement contracts,
- publication work receives a clearer claim-to-evidence trail,
- Sprints 13 through 18 have defined outcomes instead of becoming unstructured feature expansion.

Tradeoffs:

- some primitive expansion moves later,
- schema `0.2.0` is planned before the research preview candidate,
- the first final research release moves beyond the original twelve-sprint boundary,
- additional planning documents and validation gates must be maintained.

## Rejected alternatives

### Continue the twelve-sprint plan unchanged

Rejected because Sprint 11 still described initial `analyze` integration after that command had already shipped, and the plan did not allocate enough space for provenance, high-resolution timing, case-study evidence, and a separate replication freeze.

### Add a full decoder immediately

Rejected because the project does not yet have measured evidence showing that an embedded decoder is necessary for the bounded research claims. External tools remain validators until the decoder decision gate.

### Expand patterns before parser hardening

Rejected because broader semantic claims would increase the evidence surface while hostile-input and mitigation parsing remain less mature.
