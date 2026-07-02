# ADR 0019: Stripped Indicator and Dynamic String Singleton Policy

## Status

Accepted.

## Context

Sprint 8 added bounded dynamic-table and dynamic string-table evidence for RELRO and canary indicators. The next metadata step needs a stripped-status indicator without allowing section headers to influence runtime mapping or candidate scanning. Local review also identified that duplicate `DT_STRTAB` and `DT_STRSZ` entries could make canary evidence order-dependent.

## Decision

1. Report stripped status as an evidence-qualified indicator.
2. Use a bounded section-header scan for `SHT_SYMTAB` only.
3. Treat a validated section table containing `SHT_SYMTAB` as `not_stripped`.
4. Treat a validated section table without `SHT_SYMTAB` as `stripped`.
5. Treat missing section-table evidence as `unknown`.
6. Keep section headers as metadata only. Program headers remain the executable-region authority.
7. Reject duplicate `DT_STRTAB` and duplicate `DT_STRSZ` entries as malformed dynamic metadata.
8. Treat a zero-length but validated dynamic string table as completed negative canary evidence.
9. Treat a dynamic string table above the bounded scan cap as unsupported rather than silently truncating.

## Consequences

The text report gains:

```text
Stripped indicator: unknown|stripped|not stripped
```

The JSON report gains:

```json
"stripped": "unknown|stripped|not_stripped"
```

The field is an indicator, not a proof of runtime exploitability, source availability, or complete symbol recovery. Section labels and richer symbol provenance remain future schema `0.2.0` work.
