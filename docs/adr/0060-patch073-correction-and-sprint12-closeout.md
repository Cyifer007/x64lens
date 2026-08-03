# ADR 0060: Patch 073 correction and Sprint 12 closeout

## Status

Accepted for the Patch 074 implementation candidate. Final acceptance still
requires the complete native, Docker, retained external-natural, corrected
native/container parity, delivery, and independent Lane A gates.

## Context

Patch 073 preserved the runtime analyzer and executed the non-reinterpretive
public role/property policy gate as `defer`. Its review nevertheless identified
material defects in evidence custody and local acceptance tooling:

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

Patch 074 applies these decisions.

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

The role/property decision remains `defer`. Patch 074 adds no public PIE/DSO,
IBT, SHSTK, runtime-CET, text-relocation, RPATH, RUNPATH, or fortify field and
does not reinterpret `mitigations.pie`. Text relocations and separate validated
RPATH/RUNPATH evidence remain bounded future mitigation tranches. They require
checked parser facts, complete-table and duplicate semantics, hostile fixtures,
external reconciliation, schema review, and native/container parity before any
public projection.

### Sprint closeout

Patch 074 closes Sprint 12 and activates Sprint 13 after the complete acceptance
target passes. Sprint 13 owns the generic exact-pop semantic decision, Linux
syscall `r10` role decision, release-facing score/null policy, and only those
bounded family additions justified by diagnostic task value.

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

Patch 074 changes no tracked path under `src/`, `include/`, or `schemas/`. The
reference analyzer remains dependency-free, decoder-free, one-worker, bounded,
and deterministic. Program headers and file-backed `PT_LOAD + PF_X` ranges
remain executable authority. Raw, exact-suffix, semantic-exact, unknown, future
decoder-backed, and scored facts retain their existing meanings.

The corrected source is a closeout candidate, not evidence of acceptance by
itself. Native and Docker aggregates, retained external-natural acquisition,
corrected isolated parity, delivery rehearsal, and independent Lane A review
remain required before the closeout commit is accepted.
