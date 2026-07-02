# ADR 0016: Bounded Dynamic Table View

## Status

Accepted for Sprint 8 Patch 030.

## Context

Sprint 8 increases mitigation and metadata accuracy. The first required source of
additional evidence is `PT_DYNAMIC`, because full RELRO, bind-now state, canary
indicators, and later provenance-aware schema fields all depend on bounded reads
from dynamic metadata.

Before Patch 030, x64lens only recorded whether a `PT_DYNAMIC` program header was
present. That was enough for the baseline dynamic-linking boolean, but it could
not distinguish lazy binding from bind-now evidence and it did not provide a
reusable bounded-table pattern for future dynamic-symbol, string, relocation, or
GNU-hash readers.

## Decision

Patch 030 adds a deliberately narrow dynamic-table view inside `src/phdr.asm`.
The parser treats `PT_DYNAMIC` as an untrusted file-backed table of `Elf64_Dyn`
entries and applies the same checked-arithmetic policy introduced in Sprint 7:

- reject `p_filesz > p_memsz`,
- reject dynamic table ranges outside the mapped file,
- reject non-integral `Elf64_Dyn` table sizes,
- cap dynamic entries at `DYNAMIC_ENTRY_MAX`,
- derive every entry address through `x64lens_bounds_table_entry_offset`,
- stop at `DT_NULL` when present,
- record whether `DT_BIND_NOW`, `DT_FLAGS & DF_BIND_NOW`, or
  `DT_FLAGS_1 & DF_1_NOW` is present.

The runtime report gains compatible mitigation fields:

- bind-now state,
- bounded dynamic-entry count,
- dynamic-table terminator state.

The JSON schema remains `0.1.0` because these are optional compatible fields
inside the existing mitigation object. A later schema `0.2.0` transition can add
evidence provenance and confidence fields without changing this parser boundary.

## Consequences

Benefits:

- Sprint 8 gains its first bounded metadata table reader.
- Bind-now evidence is available for the Patch 031 RELRO split into partial and full.
- Future dynamic symbol, string, relocation, and canary work can reuse the same
  table-access pattern.
- The mitigation oracle now covers positive bind-now evidence and malformed
  dynamic-table ranges.

Tradeoffs:

- `PT_DYNAMIC` parsing adds a small bounded loop to mitigation analysis.
- Missing `DT_NULL` is reported as `Dynamic terminator: no` rather than being
  used as proof of exploitability or safety.
- Bind-now remains a loader-level static indicator. Patch 031 uses it only with
  `PT_GNU_RELRO` to derive the current full-RELRO label.

## Validation contract

Patch 030 must preserve all Sprint 7 parser-safety gates and expand the
mitigation oracle:

```bash
make test
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected high-level mitigation-matrix counts after Patch 030:

```text
valid cases: 14
malformed cases: 10
```

The matrix must include `DT_BIND_NOW`, `DT_FLAGS`, and `DT_FLAGS_1` bind-now
fixtures plus malformed dynamic-table range and entry-size cases.
