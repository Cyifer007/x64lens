# ADR 0018: Canary Indicator and Bounded Dynamic-String Scan

## Status

Accepted for Sprint 8 Patch 032.

## Context

Sprint 8 is improving mitigation depth while preserving the parser-safety and
loader-authority contracts. Patch 030 added a bounded `PT_DYNAMIC` table view.
Patch 031 used that view to refine RELRO into no, partial, and full states.
The next mitigation-depth field is stack-canary evidence.

A strong canary conclusion would require richer symbol, relocation, and
possibly compiler-artifact evidence. Patch 032 intentionally implements a
narrow first checkpoint: scan a validated dynamic string table for the exact
null-terminated symbol `__stack_chk_fail`.

## Decision

Add `PHDR_SUMMARY_CANARY_STATE` with three states:

- `unknown`: bounded dynamic string metadata is unavailable.
- `absent`: a bounded dynamic string table was validated and scanned, but exact
  `__stack_chk_fail` evidence was not found.
- `present`: exact null-terminated `__stack_chk_fail` evidence was found.

Collect `DT_STRTAB` and `DT_STRSZ` while walking the bounded dynamic table. If
both are present, translate the dynamic string-table virtual address only
through a file-backed `PT_LOAD` range, validate the translated range, and scan
at most `DYNAMIC_STRING_SCAN_MAX` bytes. If the string table reference cannot be
resolved, fail closed as malformed input.

## Consequences

The text report says `Canary indicator:` to avoid implying complete stack
protection. JSON emits `mitigations.canary` as `unknown`, `absent`, or
`present`.

This preserves the architecture boundary:

- `PT_LOAD + PF_X` remains executable-region authority.
- `PT_DYNAMIC` and dynamic strings contribute mitigation evidence only.
- Section headers are not required for the first canary checkpoint.
- Canary reporting does not affect gadget counts, semantic classification, or
  scoring.

## Validation

Patch 032 expands the mitigation matrix to:

```text
valid cases: 20
malformed cases: 12
```

The added valid cases cover a dynamic table without `DT_NULL`, canary absent,
and canary present. The added malformed case rejects an unmapped dynamic string
table reference. Core regressions also assert canary absent for the controlled
non-PIE sample, canary present for the controlled PIE/canary sample, and canary
unknown for the static gadget fixture.
