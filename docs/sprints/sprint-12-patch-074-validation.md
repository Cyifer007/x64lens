# Sprint 12 Patch 074 Validation

## Status

Historical superseded Sprint 12 closeout implementation candidate. Patch 074 did
not establish complete acceptance. Patch 075 introduced bounded private static
text-relocation evidence, and Patch 076 implemented distinct private `DT_RPATH`
and `DT_RUNPATH` carrier/value evidence. Patch 076 was superseded by Patch 077.
Patch 077 was superseded by Patch 078, whose review required the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080. Current validation expectations
are in the [Patch 083 validation record](sprint-13-patch-083-validation.md).

## Purpose

Patch 074 implements corrections for the confirmed Patch 073 custody, parity-
protocol, permission, selection-freeze, and authority-oracle findings,
reconciles the prior public Markdown proposals, and records the policy decision
as `defer`. It was the Patch 074 closeout candidate but was superseded; it did
not close Sprint 12 or activate Sprint 13.

It changes no tracked path under `src/`, `include/`, or `schemas/`. No runtime
mitigation field is added.

## Source boundary

Patch 074 applies to the committed Patch 073 source:

```text
base HEAD:   5833afdd1efc77b61d2fe63c41d31a23c759a296
base parent: 1ddd18a7c1d33001f1998d261ed2a3e4c77ca281
base tree:   920979629ec23123cc92dc05ab92d3d9ab1668c4
```

The delivered source-identity record is authoritative for the historical
Patch 074 candidate tree, patch digest, stable patch ID, and package digest.

## Focused Patch 073 correction

```bash
make patch073-corrective-regression-smoke
```

Expected shape:

```text
patch073-corrective-regression-smoke: ok ...
```

The regression covers:

- cleanup failure when an authenticated root disappears before removal;
- descriptor-retained rejection of late subtree mutation;
- hardlink-topology rejection;
- root-label, root-path, and symlink-ancestor binding;
- refusal to create a nested manifest through an unverified parent schedule;
- executable analyzer/probe retention in sealed parity inputs;
- exact parity rejection of symlinks, special files, and omitted nested checksum
  authorities;
- rejection of a container mount that covers the native plane;
- WSL2-safe container-plane publication with identity preservation;
- same-byte selected-object inode replacement;
- tracked-only permission normalization without ignored-tree mutation;
- deferral-only policy authorization; and
- strict mitigation-gap types and uniqueness.

Historical Patch 070 through Patch 072 corrective gates remain required because
Patch 074 preserves the still-valid behavior exercised by those gates.

## Delivery custody

The package and retained evidence use:

```text
x64lens-delivery-custody-v3
```

Verification binds root, ancestor, directory, file, and manifest identity;
exact modes; file sizes and SHA-256 values; link count; complete directory and
file membership; and post-hash path continuity. Links, hardlinks, special files,
cross-device members, undeclared members, and late mutation fail closed.

## External-natural acquisition

```bash
make sprint12-external-natural-acquisition-smoke
```

The retained 48-object acquisition must preserve:

```text
private probe processes:  144
public analyzer commands: 192
GNU readelf processes:    192
field dispositions:       864
eligible matches:         624
eligible mismatches:        0
ambiguous:                 48
unavailable:              192
```

Every selected object and authority remains device/inode/hash bound through the
final outcome checkpoint. These are diagnostic denominators, not mitigation
prevalence or publication evidence.

## Corrected native/container parity

```bash
make sprint12-role-property-environment-parity-smoke
```

Acceptance requires the same authenticated 96 objects, analyzer, probe, schema,
and harness bytes in both planes. Each plane must retain 288 probe processes,
5,184 private field cells, and 384 public command closures. The final comparison
must retain 10,368 combined private cells, 384 paired public tuples, and zero
private or public mismatches.

The container may write only its dedicated empty `/output` root. It must not
receive the native plane, repository, or any ancestor covering the native plane.
A same-host logic replay validates the comparator but does not satisfy this
native/container gate.

## Public-policy and mitigation-gap gates

```bash
make sprint12-role-property-public-policy-smoke
make sprint12-mitigation-competitive-gap-smoke
```

Expected policy result:

```text
decision=defer authorization=0 public_fields_added=0
existing_pie_preserved=1 runtime_cet_claim=0
```

At the Patch 074 boundary, text-relocation and separate RPATH/RUNPATH evidence
remained deferred bounded tranches, and Patch 074 added zero runtime fields.
Patch 075 subsequently implemented private static text-relocation evidence;
Patch 076 implements distinct RPATH/RUNPATH evidence.

## Sprint closeout authority

```bash
make sprint12-closeout-smoke
```

Expected result:

```text
sprint12-closeout-smoke: ok sprint=12 patches=13 decision=defer public_fields=0 external_natural_objects=48 eligible_matches=624 next_sprint=13
```

The closeout authority preserves:

```text
tool version:             0.1.0-dev
schema version:           0.2.0
candidate capacity:       4,096
analysis arena:           851,968 bytes
candidate 4,097:          exit 6 before stdout
malformed parse failures: no partial report
target mapping:           read-only
target execution:         never
reference profile:        dependency-free, decoder-free, one worker
```

## Complete native and Docker validation

```bash
make clean
make
make samples
make sprint-closeout-smoke
make docker-build
make docker-test
make docker-validation-smoke
```

Strict ShellCheck is part of `make sprint-closeout-smoke`. Docker availability
is a separate environment prerequisite; native evidence does not substitute for
Docker evidence.

## Historical candidate implementation aggregate

```bash
make sprint12-p074-acceptance-smoke
```

For the Patch 074 candidate, this aggregate exercised the complete native
validation surface, retained external-natural acquisition, corrected isolated
native/container parity,
deferral-only policy and mitigation-gap authorities, and the Sprint 12 closeout
authority. A passing result was necessary but not sufficient for acceptance:
package/source authentication, exact delivery rehearsal, and independent non-
documentation acceptance remain separate gates.

## Interpretation

At the Patch 074 boundary, passing every acceptance boundary on the same source
would have supported a bounded claim that Sprint 12's loader and private
mitigation-evidence work had an explicit implemented-or-deferred disposition and
an authenticated Sprint 13 handoff. That acceptance was not established, and
Patch 074 was superseded. Patch 075 introduced private static text-relocation
evidence, but its review required the Patch 076 correction. Patch 076 implements
distinct private RPATH/RUNPATH evidence. Patch 078 was superseded by the Patch
079 corrective and private task-value candidate, which was superseded by Patch 080,
which was superseded by Patch 081. Patch 081 was not accepted; complete
acceptance remains pending against the exact Patch 083 source. The historical Patch
074 candidate does not close Sprint 12 or support a public PIE/DSO, IBT, SHSTK,
runtime-CET, text-relocation, RPATH/RUNPATH, performance, RSS, coverage, or
exploitability claim beyond the existing report contract.
