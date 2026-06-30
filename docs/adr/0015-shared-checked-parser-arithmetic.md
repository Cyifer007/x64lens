# ADR 0015: Shared checked parser arithmetic

## Status

Accepted in Sprint 7 Patch 028.

## Context

x64lens parses untrusted ELF64 files in assembly. Earlier parser code already
rejected unsafe ranges, but program-header and section-header table calculations
still repeated count-times-entry-size and offset-plus-length arithmetic in more
than one module. Repetition makes future dynamic, symbol, relocation, string,
and note parsing more likely to drift.

Sprint 8 will add deeper mitigation evidence that depends on more file-derived
tables. Before that work starts, the parser needs a reusable bounded-table seam.

## Decision

Patch 028 centralizes low-level arithmetic checks in `src/bounds.asm`:

- `x64lens_bounds_mul_u64_checked`,
- `x64lens_bounds_add_u64_checked`,
- `x64lens_bounds_range_end_valid`,
- `x64lens_bounds_table_extent_valid`,
- `x64lens_bounds_table_entry_offset`.

`src/elf64.asm` now validates program-header and section-header table extents
through the shared helper before iterating. It also computes each program-header
entry offset through the bounded per-entry helper before forming a pointer.

`src/phdr.asm` keeps its defense-in-depth validation, but it now uses the same
shared helpers for table extents, per-entry offsets, and file-backed `PT_LOAD`
range ends.

## Consequences

Benefits:

- arithmetic policy has one implementation point,
- future table parsers inherit the same count, extent, and per-entry rules,
- table-end and file-range overflow probes become explicit regression cases,
- mitigation and hostile-input harnesses protect refactors from output drift.

Tradeoffs:

- program-header iteration now performs a small helper call per entry,
- Sprint 7 keeps schema `0.1.0` because this is internal safety behavior, not a
  report-identity or completeness change,
- helper names become part of the internal NASM module contract.

## Validation contract

Patch 028 must preserve all Patch 025, Patch 026, and Patch 027 gates while
adding checked-arithmetic coverage:

```bash
make test
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected high-level matrix counts after Patch 028:

```text
valid cases: 11
malformed cases: 7
```
