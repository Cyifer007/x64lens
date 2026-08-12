# ADR 0056: Whole-Batch Transaction Pilot and External-Evidence Custody

## Status

Superseded in part by ADR 0057 and further by ADR 0058. Patch 070 established
the intended transaction and evidence-custody direction, but its nested cleanup,
case oracle, output-cap, and delivery-closure implementation did not satisfy
acceptance.

## Context

Patch 069 retained a complete controlled role/property matrix and field-scoped
GNU `readelf` reconciliation, but follow-up validation showed that several
development oracles could still accept mutable or incomplete evidence. The
Patch 073 diagnostic campaign left every measured x64lens row below the reliable
single-process timer floor and produced zero positive coordinate anchors. It
authorizes no speed, RSS, superiority, or normalized coverage claim. Lowering
the floor or dividing a batch elapsed time into synthetic per-invocation latency
would overstate precision.

A historical corrective target also lacked declared analyzer, private fact
probe, and authenticated provisional-corpus prerequisites.

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
- every readelf process must succeed and the complete 1,728-cell disposition
  accounting is fixed: 1,224 eligible matches, zero eligible mismatches, 96
  ambiguous, 288 unavailable, and 120 `not_eligible`; the last three categories
  remain outside the eligible denominator;
- the controlled matrix includes one positive, fail-closed property-carrier
  overlap anchor;
- public leak checks cover all four public commands, both output streams, and
  snake, kebab, and camel naming variants.

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


## Patch 071 supersession

Patch 071 preserves this ADR's no-divided-latency and complete-or-absent
publication decisions while replacing the insufficient implementation with
identity-bound nested cleanup, an outcome-complete version-2 case authority,
streaming output caps, and regular-file path/hash/size/mode delivery verification
with exact implied-directory membership. See
[ADR 0057](0057-identity-bound-cleanup-outcome-complete-batch-and-delivery-custody.md).

ADR 0058 records the remaining Patch 071 correction and the version-3 authority
used by Patch 072, together with outcome-blind external-natural acquisition and
the initial native/container private-fact parity protocol. Patch 072's returned
review rejected current acceptance. ADR 0059 records the first Patch 073
custody/isolation correction and policy deferral. ADR 0060 records the Patch 074
correction and superseded closeout candidate. ADR 0061 records the Patch 075
private static text-relocation tranche, which Patch 076 extended with distinct
private RPATH/RUNPATH evidence. Patch 076 was superseded by the Patch 077
correction, Patch 077 by Patch 078, Patch 078 by the Patch 079 corrective and
private task-value candidate, Patch 079 by Patch 080, and Patch 080 by Patch 081.
Patch 081 was not accepted; Patch 082 is the current artifact-backed
implementation candidate, pending full local execution and independent
acceptance.
