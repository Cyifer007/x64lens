# ADR 0062: Distinct Private RPATH and RUNPATH Evidence

## Status

Accepted for the Sprint 12 Patch 076 candidate. Public projection remains
deferred.

## Context

Patch 075 added a bounded private dynamic-metadata side-car for `DT_TEXTREL`
and `DF_TEXTREL`. The next mitigation-precision tranche needs runtime search-
path metadata, but `DT_RPATH` and `DT_RUNPATH` are different loader carriers
and must not be collapsed into one label or inferred security verdict.

The implementation must retain exact dynamic-entry and string provenance,
handle hostile bytes without lossy text interpretation, remain bounded, and
perform no path-derived file access. Program headers remain executable mapping
authority and public schema `0.2.0` remains unchanged.

## Decision

Extend the private dynamic-metadata context while preserving its first
2,128 bytes exactly. The appended view provides:

- one 64-record mixed carrier budget shared by `DT_TEXTREL`, `DT_FLAGS`,
  `DT_RPATH`, and `DT_RUNPATH`;
- at most 64 resolved search-path records;
- one 4,096-byte aggregate exact-value pool;
- dynamic-table index and checked dynamic-entry file offset;
- original dynamic string-table offset and translated file offset;
- exact byte length and byte-pool offset;
- distinct carrier, value, duplicate-conflict, first-record, and state facts for
  `DT_RPATH` and `DT_RUNPATH`.

A complete bounded dynamic table produces an independent private state for each
family:

- `unknown` when complete resolved evidence is unavailable;
- `absent` when the complete table contains no carrier for that family;
- `present` when one or more resolved values agree;
- `contradictory` when duplicate values in that family disagree byte-for-byte.

The values remain raw byte strings. x64lens does not split colon-separated
members, expand `$ORIGIN`, apply loader precedence, canonicalize paths, inspect
the host filesystem, or open any target-derived path. Empty values are retained
as exact zero-length evidence. Mixed carrier 65, search record 65, or aggregate
value byte 4,097 returns exit code 6 before public report output.

## Boundaries

The private side-car does not change:

- file mapping or loader-region selection;
- section metadata authority;
- gadget discovery, matching, semantics, provenance, effects, or scoring;
- public text or JSON fields;
- schema `0.2.0`;
- the existing coarse PIE indicator;
- runtime CET claims;
- the dependency-free, decoder-free, one-worker reference profile.

## Consequences

Patch 076 requires controlled valid, malformed, unsupported, duplicate,
hostile-byte, mixed-capacity, and value-capacity fixtures; exact C/NASM layout
reconciliation; GNU `readelf -dW` presence reconciliation where eligible; and
native/container parity over the complete private dynamic side-car.

A later public policy must separately define whether either family belongs in a
public report and how its limitations are represented. This ADR does not make
that policy decision.

## Fixed storage accounting

The private dynamic-metadata context grows from 5,288 bytes in Patch 075 to
13,064 bytes in Patch 076. The increase is 7,776 bytes per command-owned
context. The current command paths retain three replicated private contexts, so
the corresponding fixed `.bss` commitment is 39,192 bytes, an increase of
23,328 bytes over Patch 075. These are bounded allocation facts, not measured
process RSS, latency, or comparative-efficiency results.
