# ADR 0060: Patch 073 correction and Sprint 12 closeout

## Status

Historical design record for the superseded Patch 074 Sprint 12 closeout
candidate. Patch 075 introduced bounded private static text-relocation evidence.
Patch 076 preserved that private prefix and implemented distinct private
`DT_RPATH` and `DT_RUNPATH` carrier/value evidence, but its review required the
Patch 077 correction. Patch 078 then became the Sprint 13 entry candidate,
and its review required the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080. Current validation expectations are in the
[Patch 089 validation record](../sprints/sprint-13-patch-089-validation.md).

## Context

Patches 070, 071, 072, and 073 were not accepted at their respective first
returned review boundaries. Patch 073 preserved the runtime analyzer and
executed the non-
reinterpretive public role/property policy gate as `defer`, but its returned
review identified material defects in evidence custody and local acceptance
tooling:

- executable analyzer and probe inputs lost execute permission when parity
  evidence was sealed;
- the required WSL2 Docker publication path could not publish the container
  plane reliably;
- an older duplicate-key regression attempted to rewrite a sealed manifest;
- recursive delivery custody did not reject every late subtree mutation,
  hardlink topology, root/ancestor substitution, or nested-manifest schedule;
- external-natural selection was content-bound but not inode-bound throughout
  outcome collection;
- the parity container could observe an ancestor mount that covered the native
  result plane;
- parity tree membership did not reject every symbolic-link, special-file, or
  undeclared nested-checksum case;
- broad permission normalization could alter tracked modes before failing on an
  ignored generated file; and
- the policy and mitigation-gap negative oracles accepted selected wrong-type or
  unauthorized mutations.

The review also confirmed that the runtime analyzer, public schema, candidate
capacity, malformed-input behavior, and private role/property parsers did not
need architectural replacement. The smallest correct next patch is therefore a
custody and closeout correction, not a new runtime mitigation family.

## Decision

Patch 074 applied these decisions.

### Delivery and evidence custody

Delivery custody advances to `x64lens-delivery-custody-v3`. Verification retains
root, ancestor, directory, and regular-file descriptors until final closure,
rehashes through the retained file descriptors, reauthenticates caller-visible
path bindings after hashing, rejects hardlinks, links, special files,
cross-device members, undeclared directories, and late subtree mutation, and
requires the manifest root label to agree with the authenticated root basename.
Manifest creation requires an existing authenticated parent and verifies the
new object immediately after no-replace publication.

A missing owned cleanup root is a failure, not proof that cleanup succeeded.
This preserves the distinction between removal of the authenticated owned tree
and disappearance caused by another actor.

### Outcome-blind selection

The external-natural freeze binds every selected object and authority file to
device, inode, type, mode, size, timestamps, link count, and SHA-256. Every
checkpoint compares the live object to that in-memory identity. Same-byte inode
replacement is therefore a mutation rather than an accepted equivalent input.

### Native/container parity

Parity inputs retain their required executable or read-only modes. The
container receives only three mounts:

```text
/inputs   read-only authenticated analyzer, probe, schema, and harness
/heldout  read-only authenticated 96-object input plane
/output   one empty dedicated writable container result root
```

No repository, `/work`, native result plane, or ancestor that covers the native
plane is mounted. Each plane and the final comparison use exact tree custody,
including nested checksum authorities and rejection of links, special files,
hardlinks, and undeclared empty directories. WSL2 publication temporarily opens
only the sealed container-plane root, verifies identity across publication, and
restores the sealed mode.

### Permission normalization

`make normalize-perms` operates only on Git-tracked regular files and their
tracked directory ancestry. It preflights the complete tracked set and rolls
back any mode change if a later operation fails. Ignored or untracked generated
state is outside this normalizer.

### Public policy and mitigation breadth

The role/property decision remains `defer`. Patch 074 added no public PIE/DSO,
IBT, SHSTK, runtime-CET, text-relocation, RPATH, RUNPATH, or fortify field and
did not reinterpret `mitigations.pie`. At that boundary, text relocations and
separate validated RPATH/RUNPATH evidence remained future mitigation tranches.
Patch 075 introduced private static text-relocation evidence, but its review
required the Patch 076 correction. Patch 076 implements distinct `DT_RPATH` and
`DT_RUNPATH` evidence. Public projection still
requires checked parser facts, complete-table and duplicate semantics, hostile
fixtures, external reconciliation, schema review, and native/container parity.

### Sprint closeout

Patch 074 would have closed Sprint 12 and activated Sprint 13 only after its
complete acceptance boundary passed, but it was superseded before acceptance.
Patch 075 introduced private text-relocation evidence, and Patch 076 added
distinct private RPATH/RUNPATH evidence. Patch 077 required Patch 078, whose
review required the Patch 079 corrective and private task-value candidate; Patch
079's review required Patch 080. Patch 078 froze private additive exact-pop roles
only, Patch 079 ran the task-value gate, and Patch 080 retained three facets in a
private side-car while deferring public-field and score changes.

## Rejected alternatives

- Publishing role/property fields from nominal or unfrozen diagnostic parity.
- Treating same-byte inode replacement as an unchanged selection freeze.
- Mounting the repository or a native-plane ancestor read-only into the parity
  container and calling that independent custody.
- Accepting hardlinks because their bytes and modes match.
- Normalizing all repository files before proving the complete operation can
  succeed.
- Adding text-relocation, RPATH/RUNPATH, or fortify fields without their parser,
  fixture, schema, and comparator authorities.
- Introducing mandatory decoding, default concurrency, JOP/COP/SROP, chain
  synthesis, exploit generation, or stealth/evasion behavior.

## Consequences

Patch 074 changed no tracked path under `src/`, `include/`, or `schemas/`. The
reference analyzer remains dependency-free, decoder-free, one-worker, bounded,
and deterministic. Program headers and file-backed `PT_LOAD + PF_X` ranges
remain executable authority. Raw, exact-suffix, semantic-exact, unknown, future
decoder-backed, and scored facts retain their existing meanings.

The corrected Patch 074 source was a closeout candidate, not evidence of
acceptance by itself. Patch 075 superseded it, introduced private static
text-relocation evidence, and then required the Patch 076 correction. Patch 076
added distinct private RPATH/RUNPATH evidence but required the Patch 077
correction. Patch 077 was superseded by Patch 078, whose review required Patch
079; Patch 079 was superseded by Patch 080, which was superseded by Patch 081.
Native and Docker aggregates, retained external-natural acquisition, corrected
isolated parity, delivery rehearsal, and independent exact-source acceptance
remain part of the independent exact-source Patch 089 acceptance boundary.
