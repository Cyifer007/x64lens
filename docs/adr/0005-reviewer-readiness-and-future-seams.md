# ADR 0005: Reviewer Readiness and Future Seams

## Status

Accepted.

## Context

The project has reached the end of Sprint 3 with ELF64 validation, program-header analysis, baseline mitigation reporting, raw gadget scanning, arena-backed candidate storage, and exact suffix pattern matching. At this point, future reviewer concerns are clear enough to document before they become implementation debt.

Likely concerns include:

- why the first engine is written in NASM,
- whether an assembly parser is safe on malformed inputs,
- whether exact byte patterns are too brittle,
- whether raw candidate counts are meaningful,
- whether the codebase can be maintained,
- whether x86_64 scope is too narrow.

## Decision

Keep the current architecture direction, but explicitly add planning seams for:

- NASM rationale,
- parser safety and mutation smoke testing,
- decoder integration,
- raw/exact/semantic metric separation,
- contributor maintainability,
- future architecture portability.

## Rationale

The critique does not require a rewrite. It requires better boundaries, clearer claims, and stronger validation. The existing module separation already supports this path.

## Consequences

- Sprint 4 remains semantic classification, not a decoder rewrite.
- Sprint 5 remains scoring and JSON, not a tooling pivot.
- Sprint 7 should include parser safety hardening and malformed-input smoke testing.
- Sprint 10 should include research-grade comparison against existing tools.
- Claims about performance, coverage, and usefulness remain hypotheses until measured.

## Non-decision

This ADR does not approve adding Capstone, Zydis, Rust, C, Go, ARM64, PE, or Mach-O support in the near term. Those remain future research directions unless benchmark evidence changes the priority.
