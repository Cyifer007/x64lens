# ADR 0056: Whole-Batch Transaction Pilot and External-Evidence Custody

## Status

Accepted for Sprint 12 Patch 070.

## Context

Patch 069 retained a complete controlled role/property matrix and field-scoped
GNU `readelf` reconciliation, but review found that several development oracles
could still accept mutable or incomplete evidence. The same review confirmed
that all measured x64lens rows in the latest diagnostic campaign remained below
the reliable single-process timer floor. Lowering the floor or dividing a batch
elapsed time into synthetic per-invocation latency would overstate precision.

The reported local Make failure also showed that a historical corrective target
could run before its analyzer, private fact probe, and authenticated provisional
corpus existed.

## Decision

Patch 070 first closes the evidence-integrity defects:

- mode-only corpus repair retains descriptor, member, metadata, byte, ctime, and
  caller-visible root authority through the first mutation and successful
  return;
- rollback restores every original mode and surfaces restoration failure;
- sealed result trees are removed only through inode-bound quarantine cleanup;
- the Patch 068 corrective target declares its analyzer, probe, and corpus
  prerequisites;
- held-out and readelf authorities are exact semantic authorities, not count-only
  envelopes;
- every readelf process must succeed and the 1,224/96/288/120 field-disposition
  denominator is fixed;
- the controlled matrix includes one positive, fail-closed property-carrier
  overlap anchor;
- public leak checks cover all four public commands, both output streams, and
  snake, kebab, and camel naming variants;
- private apply and rollback bind final files to authenticated device/inode
  identities and the package-specific source base.

Patch 070 then adds a development-only whole-batch transaction pilot:

```text
27 cases x 3 repetitions = 81 executions
```

The pilot covers empty batches, complete success, first/middle/final nonzero,
timeout, stdout-limit, and stderr-limit failures, plus SIGINT and SIGTERM at four
transaction barriers. It requires exact failure positions, explicit unstarted
members, complete-or-absent publication, no stage or child residue, stable
normalized result hashes, and no file-descriptor growth.

The pilot does not record a performance result and never divides a batch elapsed
time into claimed single-run latency.

## Consequences

The reference analyzer remains unchanged: dependency-free, decoder-free,
one-worker, bounded, and deterministic. Public schema `0.2.0`, CLI behavior,
candidate capacity, semantic classes, scores, and report fields do not change.
GNU `readelf` remains external comparator evidence rather than runtime authority.

A later workload ladder may use whole-batch throughput only after this
transaction contract passes on the exact source and environment. Single-run
latency remains unresolved when the analyzer is below the reliable floor.

## Rejected alternatives

- Lowering the timer floor until x64lens produces an eligible number.
- Dividing batch elapsed time into synthetic per-process latency.
- Treating all-unavailable comparator fields as successful reconciliation.
- Retaining count-only matrix authorities that omit compiler, role, property,
  edge-family, or public-command semantics.
- Using recursive `rm -rf` against sealed or replaceable result paths.
- Publishing role, PIE/DSO, IBT, or SHSTK fields before natural-object and
  native/container private-fact gates close.
