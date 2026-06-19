# Sprint 07 Plan

## Status

Planned after the Sprint 6 Patch 024 architecture review.

## Sprint goal

Harden hostile-input handling before dynamic-section, symbol-table, and note parsing expand the parser attack surface.

## Rationale

The current parser has explicit bounds checks and committed malformed fixtures, but the evidence is still example-driven. Sprint 7 converts parser safety from an implementation claim into a repeatable regression surface.

## Planned deliverables

- [ ] Add a deterministic mutation smoke harness with fixed seeds and bounded runtime.
- [ ] Add `make malformed-smoke` and include it in `make validation-smoke` after local stability is proven.
- [ ] Record signal, exit code, timeout, target mutation, and command for every case.
- [ ] Add a committed regression fixture for every crash or out-of-bounds defect discovered.
- [ ] Add shared helpers or documented rules for bounded table iteration before dynamic-section parsing begins.
- [ ] Validate multiplication, addition, entry-size, count, and end-offset overflow paths.
- [ ] Define explicit behavior when executable-region or gadget-record capacity is exceeded.
- [ ] Add machine-readable and text limitations for incomplete or truncated analysis when applicable.
- [ ] Preserve target mappings as read-only and internal arenas as non-executable.

## Acceptance criteria

- [ ] No mutation case causes SIGSEGV or SIGBUS.
- [ ] No mutation case exceeds the configured timeout.
- [ ] Malformed inputs return stable documented nonzero exit codes.
- [ ] Every new parser regression is represented by a durable fixture.
- [ ] Candidate-capacity behavior is explicit and never silently truncates a research report.
- [ ] Existing `info`, `mitigations`, `gadgets`, and `analyze` behavior remains compatible for valid fixtures.
- [ ] Native, Docker, fixture, JSON, system-binary, and malformed smoke checks pass.

## Out of scope

- Full RELRO and canary detection, except parser helpers needed to support them.
- Primitive expansion.
- Embedded decoder integration.
- Publication benchmark claims.

## Handoff

Sprint 8 consumes the hardened table-iteration and regression infrastructure to implement deeper mitigation and metadata evidence.
