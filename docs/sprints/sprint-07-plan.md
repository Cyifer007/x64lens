# Sprint 07 Plan

## Status

Active. Patch 025 established the broad hostile-input gate. Patch 026 implemented the mitigation oracle, Patch 027 corrected its zero-region expectation, and Patch 028 consolidates shared checked table arithmetic before deeper dynamic and symbol parsing begins.

## Sprint goal

Harden hostile-input handling before dynamic-section, symbol-table, and note parsing expand the parser attack surface.

## Rationale

The parser already performs explicit range checks and rejects several committed malformed fixtures, but the evidence before Sprint 7 was example-driven. Sprint 7 converts parser safety from an implementation claim into a repeatable regression surface with bounded execution, per-case evidence, explicit resource-limit behavior, and a path for promoting discovered defects into durable fixtures.

## Patch 025 delivered scope

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

## Patch 026 delivered scope

- [x] Add a deterministic mitigation truth table independent of compiler-generated fixtures.
- [x] Cover `ET_EXEC`, `ET_DYN`, GNU stack states, RELRO, dynamic linking, RX/RW/RWX loads, split mappings, overlapping executable regions, and combined evidence.
- [x] Verify exact mitigation text and syntactically valid integrated JSON for every valid case.
- [x] Verify the five original malformed program-header cases plus two table-end overflow cases through `info`, `mitigations`, and `analyze`.
- [x] Reject invalid file-backed `PT_LOAD` ranges during shared ELF64 validation.
- [x] Add ignored JSON evidence with seed and fixture SHA-256 values.
- [x] Include `make mitigation-matrix-smoke` in native, CI, and Docker validation.
- [x] Clarify planning-check output as 18 total sprint plans and 12 forward plans.

## Patch 027 correction scope

- [x] Preserve the reporter's explicit zero-region evidence line.
- [x] Correct the mitigation oracle to expect `none discovered from PT_LOAD + PF_X`.
- [x] Add a focused correction validation plan and document the Patch 026 acceptance gap.
- [x] Keep the Make aggregate fail-fast behavior unchanged.

## Patch 028 delivered scope

- [x] Add shared checked multiplication and addition helpers.
- [x] Add checked offset-plus-length validation that can return a trusted exclusive end.
- [x] Add checked table-extent validation for count-times-entry-size and table end.
- [x] Add a bounded per-entry offset helper for table iteration.
- [x] Route ELF64 and program-header analysis through the shared helpers.
- [x] Expand deterministic malformed coverage for program-header and section-header table-end overflow.
- [x] Fix the public-docs/generated-results interaction found during Patch 027 local validation.
- [x] Exclude private local agent workspaces from permission normalization and public patch bundles.

## Remaining Sprint 7 work

- [ ] Promote every newly discovered stable parser defect into a minimized committed regression fixture when a non-synthetic defect is found.
- [ ] Add regression minimization guidance and fixture provenance fields.
- [ ] Decide whether any bounded analysis path requires explicit machine-readable completeness or truncation fields before schema `0.2.0`.
- [ ] Expand deterministic mutations when new file-derived tables become reachable.

## Acceptance criteria

The current Sprint 7 evidence gates are accepted when:

- [ ] No deterministic mutation case causes SIGSEGV, SIGBUS, or another signal.
- [ ] No deterministic mutation case exceeds the configured timeout.
- [ ] Malformed inputs return stable documented nonzero exit codes and emit no partial stdout.
- [ ] The valid controls and executable-region boundary probe complete successfully.
- [ ] Candidate-capacity exhaustion returns exit code `6` for focused and integrated text and JSON commands, with no partial output.
- [ ] Existing `info`, `mitigations`, `gadgets`, and `analyze` behavior remains compatible for valid fixtures.
- [ ] Native, Docker, fixture, JSON, system-binary, malformed, capacity, and mitigation-oracle smoke checks pass after Patch 028.
- [ ] Public documentation, planning consistency, and patch-bundle hygiene checks pass after generated result artifacts exist.

Sprint 7 is complete only after Patch 028 validates locally and no follow-up defect is found in the checked-arithmetic or generated-results cleanup path.

## Out of scope

- Full RELRO and canary detection, except parser helpers needed to support them.
- Primitive expansion.
- Embedded decoder integration.
- Coverage-guided fuzzing.
- Publication benchmark claims.

## Handoff

Patch 028 implements shared bounded table arithmetic while preserving the Patch 025 hostile-input gates and the corrected Patch 026 mitigation oracle. The next decision is whether Sprint 7 needs one final regression-promotion polish patch or can close and hand Sprint 8 the mitigation-depth work.
