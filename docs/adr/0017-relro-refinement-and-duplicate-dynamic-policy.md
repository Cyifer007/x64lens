# ADR 0017: RELRO Refinement and Duplicate Dynamic Policy

## Status

Accepted for Sprint 8 Patch 031.

## Context

Patch 030 added a bounded `PT_DYNAMIC` table view and exposed bind-now evidence
without changing the RELRO label. That made the required evidence available for
splitting RELRO into no, partial, and full states. It also exposed an edge case:
more than one `PT_DYNAMIC` program header makes dynamic-entry counts and
`DT_NULL` terminator state ambiguous under the current single-summary record.

## Decision

Patch 031 refines RELRO reporting as follows:

- no `PT_GNU_RELRO` reports text `RELRO: not found` and JSON `"relro":"none"`,
- `PT_GNU_RELRO` without bounded bind-now evidence reports `RELRO: partial` and
  JSON `"relro":"partial"`,
- `PT_GNU_RELRO` plus bounded bind-now evidence from `DT_BIND_NOW`,
  `DT_FLAGS & DF_BIND_NOW`, or `DT_FLAGS_1 & DF_1_NOW` reports `RELRO: full`
  and JSON `"relro":"full"`.

The underlying bind-now and dynamic-table fields remain separate facts. The
RELRO label is a composition of loader evidence, not a proof of complete runtime
safety.

Patch 031 rejects a second `PT_DYNAMIC` program header as malformed. This is the
conservative policy because x64lens currently has one dynamic-entry count, one
terminator flag, and one bind-now flag in the program-header summary. Accepting
several dynamic tables would require a broader evidence model before the output
could describe the result without ambiguity.

## Consequences

Benefits:

- RELRO reporting is more useful for defensive triage while preserving evidence
  boundaries.
- The current schema stays at `0.1.0` with compatible values in the existing
  `mitigations.relro` field.
- Duplicate dynamic tables fail closed instead of producing ambiguous
  `dynamic_terminated` output.
- The mitigation oracle now covers full-RELRO evidence paths and the duplicate
  dynamic-table policy.

Tradeoffs:

- Some unusual binaries with multiple `PT_DYNAMIC` headers are rejected until a
  future schema can represent per-table evidence.
- Full RELRO is still an evidence-qualified static label. It does not assert
  memory safety, exploitability, or runtime loader behavior beyond represented
  static metadata.

## Validation contract

Patch 031 must preserve Sprint 7 parser-safety gates, Patch 030 dynamic-table
fields, and the existing candidate-capacity contract:

```bash
make test
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected high-level mitigation-matrix counts after Patch 031:

```text
valid cases: 17
malformed cases: 11
```

The matrix must include all three full-RELRO bind-now evidence paths and the
`multiple-pt-dynamic` malformed case. Dynamic malformed coverage must include
`gadgets` text and JSON callers because those paths consume the program-header
summary before scanning executable regions.
