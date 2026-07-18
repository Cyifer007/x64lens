# ADR 0038: Patch 051 Corrective Effect and Gate Hardening

## Status

Accepted for Sprint 10 Patch 052 validation.

Related documentation:

- [Architecture](../architecture.md)
- [Primitive Effect Model](../design/primitive-effect-model.md)
- [Family Coverage Table](../design/sprint10-family-coverage.md)
- [Exact-Pattern Catalog](../design/sprint10-exact-pattern-catalog.md)
- [Scoring Model](../scoring-model.md)
- [Output Contract](../contracts/output-contract.md)
- [Patch 052 Validation](../sprints/sprint-10-patch-052-validation.md)

## Context

Patch 051 introduced a fixed-size architectural-effect side-car and reconciled
semantic-family, exact-pattern, and fixture-suite contracts. Validation found
four implementation defects and two contract-gate gaps:

1. a 64-bit syscall effect descriptor was encoded through an imm32-only store
   and comparison;
2. valid `ret imm16 0` candidates were rejected by strict-greater stack-delta
   checks;
3. text side-effect lists used the register-list separator instead of the
   output contract's comma-space separator;
4. memory-effect reconciliation accepted noncanonical or wrong-index side-car
   records;
5. numeric score policy was not cross-checked between family and exact-pattern
   authorities; and
6. strict ShellCheck mode did not independently prove that the executable was
   available.

The defects are in effect materialization, scoring validation, text rendering,
and development gates. They do not justify a new primitive family or a broader
runtime dependency.

## Decision

Patch 052 makes the smallest corrective changes:

- materialize 64-bit effect descriptor constants in a register before qword
  stores or comparisons;
- accept `ret imm16` total stack deltas greater than or equal to the ordinary
  return delta;
- render side-effect lists with `, ` while retaining `|` for register sets;
- reconstruct the complete canonical memory descriptor from the candidate's
  exact pattern metadata and require byte-for-byte descriptor agreement;
- treat NASM number-overflow warnings as build errors;
- add a zero-immediate return fixture;
- add a standalone assembly mutation harness for dense memory side-car
  reconciliation;
- make score values machine-checkable across both family and exact-pattern
  gates; and
- add a missing-ShellCheck contract regression.

The raw scanner record, candidate capacity, arena size, schema version, and
runtime dependency surface remain unchanged.

## Consequences

### Positive

- Syscall flag facts retain all represented bits.
- The minimum valid `ret imm16` delta is covered by a controlled fixture.
- Text and JSON effect vocabulary use their documented formats.
- Memory side-car corruption fails closed without debugger-only instrumentation.
- Numeric score drift causes both maintained reconciliation gates to fail.
- Strict lint mode cannot silently degrade to a skip.
- Future qword-immediate truncation is rejected at assembly time.

### Tradeoffs

- One internal assembly harness adds a small build-time validation surface.
- The family and exact-pattern authorities remain intentionally duplicated, but
  a negative mutation gate now proves they cannot drift silently.
- NASM warnings that were previously advisory can block a build and must be
  resolved deliberately.

## Rejected alternatives

### Remove syscall flag facts

Rejected because the represented flags are valid architectural evidence. The
correct response is to encode the 64-bit descriptor safely.

### Treat `ret imm16 0` as unsupported

Rejected because the encoding is valid and has the same total stack delta as an
ordinary return.

### Mask contradictory memory records in the reporter

Rejected because the materializer, not the output adapter, owns internal effect
reconciliation.

### Add another primitive family in the corrective patch

Rejected because Patch 052 exists to restore the Patch 051 contract before the
Patch 053 capability reassessment.
