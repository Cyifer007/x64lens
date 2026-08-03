# Sprint 12 Patch 073 Validation

## Status

Historical implementation candidate. The public-policy gate executed as
`defer`, but Patch 073 was not accepted at its first returned review boundary.
Patch 074 is the final corrective Sprint 12 closeout candidate and still
requires complete acceptance.

## Purpose

Patch 073 delivered the first custody/isolation correction for the confirmed
Patch 072 cleanup, selection-freeze, delivery, parity-isolation, and
evidence-retention defects while executing the planned non-reinterpretive
public-policy gate. Patch 074 carries the remaining correction. The Patch 073
policy result is an explicit
**deferral**: no new PIE/DSO, IBT, SHSTK, text-relocation, RPATH, or RUNPATH
field is added. The existing coarse `mitigations.pie` field remains the
`ET_DYN` indicator, and static GNU properties do not prove runtime CET
enforcement.

The patch also records text-relocation evidence and distinct RPATH/RUNPATH
indicators as selected future bounded work. It adds none of those fields before
their parser, fixture, schema, and external-comparator gates exist.

## Source boundary

Patch 073 applies to the committed Patch 072 source:

```text
base HEAD:   1ddd18a7c1d33001f1998d261ed2a3e4c77ca281
base parent: d1c1f910e9bc925e01467e1449e65a2d36ad6f0f
base tree:   8f065e695de498434ed3c41aeb01fe85858aa27c
```

The delivery source-identity record is authoritative for the final candidate
tree, patch digest, and package digest.

Patch 073 changes no tracked path under `src/`, `include/`, or `schemas/` and
adds no public schema field.

## Focused correction gate

```bash
make patch072-corrective-regression-smoke
```

Expected shape:

```text
patch072-corrective-regression-smoke: ok ...
```

The gate covers:

- file, directory, and root substitution after the earlier final fingerprint;
- post-freeze selection mutation;
- root, directory, and manifest mode drift;
- same-size pathname substitution after file hashing;
- rejection of stale delivery-custody schema v1;
- exclusive container-plane write scope;
- mandatory retained parity results; and
- rejection of public-field authorization with open prerequisites.

The existing Patch 070 and Patch 071 corrective gates remain required because
Patch 073 preserves the valid behavior covered by those historical gates rather
than replacing it.

## Public-policy and mitigation-gap gates

```bash
make sprint12-role-property-public-policy-smoke
make sprint12-mitigation-competitive-gap-smoke
```

Expected results:

```text
sprint12-role-property-public-policy-smoke: ok decision=defer ... public_fields_added=0 existing_pie_preserved=1 runtime_cet_claim=0
sprint12-mitigation-competitive-gap-smoke: ok ... selected_next=text-relocations,runtime-search-path runtime_fields_added=0
```

The policy validator authenticates the current schema and reporter source bytes,
checks the exact current mitigation property set, and rejects new role/property
keys or labels. Diagnostic private facts do not satisfy an authorization
prerequisite merely because their internal agreement gate passes.

## Retained external-natural acquisition

```bash
make sprint12-external-natural-acquisition-smoke
```

The Make target chooses a unique retained result directory unless
`ROLE_PROPERTY_EXTERNAL_NATURAL_RESULT_DIR` is supplied. The harness verifies
its selection authority before loading outcome tools, before every object, and
after all outcomes. The manifest must state
`selection_freeze_verified_through_outcomes: true`.

## Intended corrected native/container parity gate

```bash
make sprint12-role-property-environment-parity-smoke
```

The Make target chooses a unique retained result directory unless
`ROLE_PROPERTY_PARITY_RESULT_DIR` is supplied. Acceptance requires:

- the same 96 authenticated object bytes in both planes;
- 288 private fact-probe processes and 5,184 private field cells per plane;
- 384 public command tuples per plane;
- one dedicated empty writable mount for the container plane;
- no native-plane mount in the container command;
- sealed retained inputs, held-out source, native plane, container plane,
  comparison, and run manifest; and
- zero private or public mismatches.

A same-host logic comparison is useful harness evidence but does not satisfy
this native/container gate.

## Complete native and Docker validation

```bash
make sprint-closeout-smoke
make docker-build
make docker-test
make docker-validation-smoke
```

The unchanged runtime must preserve:

```text
schema version:      0.2.0
candidate capacity:  4,096
candidate 4,097:     exit 6 before stdout
malformed input:     no partial report
target mapping:      read-only
target execution:    never
reference profile:   dependency-free, decoder-free, one worker
```

## Patch 073 candidate implementation aggregate

```bash
make sprint12-p073-acceptance-smoke
```

This aggregate covered the Patch 073 implementation surface: the complete native
aggregate, retained external-natural acquisition, intended corrected Docker
parity, policy deferral, and mitigation-gap authority. A pass was necessary but
did not establish acceptance. Package/source authentication, exact delivery
rehearsal, corrected actual native/container parity, and independent acceptance
remained separate boundaries.

## Interpretation

Patch 073 supports a bounded claim that the role/property public-policy gate was
executed and deferred without changing the existing public report contract. It
does not support a claim that static GNU properties prove runtime CET, that
`ET_DYN` alone distinguishes PIE from DSO, or that the external-natural sample
estimates mitigation prevalence.

Patch 074 carries the required remaining correction, exact delivery-rehearsal
requirement, and final Sprint 12 closeout-candidate authority. Current
expectations are in the
[Patch 074 validation record](sprint-12-patch-074-validation.md). Sprint 13 owns
semantic completion only after Patch 074 acceptance.
