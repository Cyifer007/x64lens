# ADR 0052: Role and GNU-Property Metamorphic Preflight

## Status

Accepted architecture introduced by Sprint 12 Patch 066, extended by Patch 067
layout attestation and the Patch 068 diagnostic matrix, and carried through
Patches 069 and 070. Patch 070 acceptance was rejected. Patch 071 corrected
the first development-evidence blockers, and the current Patch 072 candidate
carries the remaining correction plus private acquisition/parity work while
leaving runtime and schema boundaries unchanged.
Product and delivery acceptance remain governed by separate validation.

## Context

Patch 065 introduced private binary-role and x86 GNU-property evidence, but
subsequent validation identified parser, corpus-repair, ABI, and oracle defects:

- GNU property entries were aligned from the absolute file offset instead of
  relative to the property descriptor;
- partially overlapping note carriers could reach public reporting;
- copied read-only corpus authorities caused the corrective oracle to fail
  before exercising its intended mutation;
- corpus mode repair did not retain directory identity and manifest-authorized
  bytes through mutation;
- one internal role harness violated nested-call stack alignment.

The remaining evidence gap called for a small metamorphic fact preflight before
the separate natural/metamorphic diagnostic matrix or any public role/CET policy
decision.

## Decision

Patch 066 first corrects the Patch 065 parser, corpus-repair, ABI, and
oracle defects. It then adds one development-only 28-object metamorphic
preflight:

```text
three role constructions
  ET_EXEC executable-like
  ET_DYN + PT_INTERP executable-like
  ET_DYN + validated DT_SONAME shared-object-like

x four property states
  absent
  IBT
  SHSTK
  IBT + SHSTK

x two carrier encodings
  canonical PT_NOTE
  exact-dual PT_NOTE + PT_GNU_PROPERTY

plus four single-axis mutants
  unknown feature bit
  conflicting feature records
  descending property order
  contradictory executable/shared role evidence
```

A development-only C fact probe maps each object read-only and invokes the same
bounded assembly validators and classifiers used by x64lens. The probe is not
linked into the freestanding product and does not define report policy.

For every logical pair, the preflight requires:

- deterministic repeated facts;
- invariant role and IBT/SHSTK states;
- one canonical physical property view;
- exactly one additional original contributor in the dual encoding;
- unchanged schema `0.2.0` and no private role/property fields in public JSON;
- successful public command execution, or malformed failure before stdout for
  the ordering mutant.

## Parser corrections

GNU property entry alignment is descriptor-relative. Exact duplicate carrier
ranges remain canonicalized, but any non-identical physical overlap is malformed
before a property state can reach a reporter. Valid four-byte-aligned `PT_NOTE`
streams and partial-overlap failures are covered by both the independent byte
oracle and the internal assembly reconciliation harness.

## Corpus-repair corrections

Corpus mode repair opens and retains the checksum authority and every member
before semantic verification. It reauthenticates current path identity,
ownership, timestamps, link counts, sizes, and manifest-authorized bytes before
using descriptor-bound `fchmod`.

## Boundaries

Patch 066 does not:

- add public PIE/DSO, IBT, or SHSTK fields;
- change schema `0.2.0`;
- infer runtime CET enforcement;
- change executable-region authority, scanner behavior, candidate identity,
  capacity, semantic classes, or scores;
- freeze the later natural/metamorphic diagnostic matrix;
- add a runtime dependency.

Patch 067 added C/NASM layout attestation. Patch 068 addressed its remaining
custody boundary and defined a separate 96-object diagnostic agreement matrix:
48 held-out natural toolchain-produced objects plus 48 controlled metamorphic
objects. At the Patch 068 boundary, bounded external ELF reconciliation
(`readelf -hW/-lW/-dW/-nW`) remained subsequent work. Patch 069 added that
authenticated reconciliation. Patch 070 attempted the next evidence-gate correction but was rejected.
Patch 071 corrected the first blocker set; Patch 072 carries the remaining
correction and the separate native/container private-fact parity gate. Whole-batch timing and process-tree RSS also remain separate
measurement gates.

## Consequences

- The Patch 065 private facts receive a discriminating, deterministic controlled
  fixture preflight. This remains development evidence, not held-out or
  publication evidence.
- Original carrier provenance remains visible without accepting ambiguous
  overlap.
- The dependency-free, decoder-free, one-worker product profile remains intact.
- Public indicators remain blocked while the current diagnostic agreement and
  external-reconciliation candidate awaits acceptance, and until the later
  parity gate and public-policy review justify a compatible-output decision.
