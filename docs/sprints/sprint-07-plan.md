# Sprint 07 Plan

## Status

Closed. Sprint 7 closed with Patch 029 after Patch 028 validated shared checked parser arithmetic, deterministic malformed-input coverage, candidate-capacity failure behavior, and the deterministic mitigation oracle.

## Sprint goal

Harden hostile-input handling before dynamic-section, symbol-table, and note parsing expand the parser attack surface.

## Rationale

The parser already performed explicit range checks before Sprint 7, but the evidence was example-driven. Sprint 7 converted parser safety from an implementation claim into a repeatable regression surface with bounded execution, per-case evidence, explicit resource-limit behavior, deterministic mitigation oracles, shared checked arithmetic, and clear promotion rules for future minimized fixtures.

## Delivered scope

### Patch 025 hostile-input hardening

- [x] Add a deterministic mutation smoke harness with a fixed reviewed catalog and bounded runtime.
- [x] Add `make malformed-smoke` and include it in `make validation-smoke`.
- [x] Record seed hash, mutation description, command, expected and observed exit code, signal, timeout, elapsed nanoseconds, and output sizes for every case.
- [x] Add a regression policy and reserved directory for minimized parser fixtures.
- [x] Commit the first minimized regression fixture for the invalid 63-byte ELF64 section-header stride defect.
- [x] Require the fixed 64-byte ELF64 section-header entry size when a section table is present.
- [x] Exercise program-header, section-header, executable-segment, and boundary range cases.
- [x] Define candidate-arena exhaustion as exit code `6` with no partial text or JSON report.
- [x] Add controlled 4096/4097 boundary fixtures and `make capacity-smoke`.
- [x] Add native, CI, and Docker integration through `make validation-smoke` and `make docker-validation-smoke`.
- [x] Preserve target mappings as read-only and internal arenas as non-executable.

### Patch 026 and Patch 027 mitigation oracle

- [x] Add a deterministic mitigation truth table independent of compiler-generated fixtures.
- [x] Cover `ET_EXEC`, `ET_DYN`, GNU stack states, RELRO, dynamic linking, RX/RW/RWX loads, split mappings, overlapping executable regions, and combined evidence.
- [x] Verify exact mitigation text and syntactically valid integrated JSON for every valid case.
- [x] Verify malformed program-header cases through `info`, `mitigations`, and `analyze`.
- [x] Reject invalid file-backed `PT_LOAD` ranges during shared ELF64 validation.
- [x] Add ignored JSON evidence with seed and fixture SHA-256 values.
- [x] Include `make mitigation-matrix-smoke` in native, CI, and Docker validation.
- [x] Correct the stale zero-executable-region oracle expectation while preserving the reporter's explicit evidence line.

### Patch 028 checked parser arithmetic

- [x] Add shared checked multiplication and addition helpers.
- [x] Add checked offset-plus-length validation that can return a trusted exclusive end.
- [x] Add checked table-extent validation for count-times-entry-size and table end.
- [x] Add a bounded per-entry offset helper for table iteration.
- [x] Route ELF64 and program-header analysis through the shared helpers.
- [x] Expand deterministic malformed coverage for program-header and section-header table-end overflow.
- [x] Fix the public-docs/generated-results interaction found during local validation.
- [x] Exclude private local agent workspaces from permission normalization, Docker build context filtering, Git ignore gaps, and patch-bundle hygiene.

### Patch 029 closeout

- [x] Close Sprint 7 and record the final validation expectations.
- [x] Update the Sprint 8 handoff so mitigation-depth work begins from the hardened parser baseline.
- [x] Review future sprint sequencing and keep Sprint 8 focused on bounded mitigation metadata rather than primitive expansion.

## Acceptance criteria

Sprint 7 is accepted when:

- [x] No deterministic mutation case causes SIGSEGV, SIGBUS, or another signal.
- [x] No deterministic mutation case exceeds the configured timeout.
- [x] Malformed inputs return stable documented nonzero exit codes and emit no partial stdout.
- [x] The valid controls and executable-region boundary probe complete successfully.
- [x] Candidate-capacity exhaustion returns exit code `6` for focused and integrated text and JSON commands, with no partial output.
- [x] Existing `info`, `mitigations`, `gadgets`, and `analyze` behavior remains compatible for valid fixtures.
- [x] Native, Docker, fixture, JSON, system-binary, malformed, capacity, and mitigation-oracle smoke checks pass after Patch 028.
- [x] Public documentation, planning consistency, and patch-bundle hygiene checks pass after generated result artifacts exist.

## Out of scope

- Full RELRO and canary detection, except parser helpers needed to support them.
- Primitive expansion.
- Embedded decoder integration.
- Coverage-guided fuzzing.
- Publication benchmark claims.

## Handoff

Sprint 8 starts from a stronger parser-safety baseline. The next sprint should add bounded `PT_DYNAMIC` and related metadata parsing for mitigation accuracy while preserving the Sprint 7 hostile-input, capacity, mitigation-oracle, and checked-arithmetic gates.
