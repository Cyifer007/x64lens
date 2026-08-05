# ADR 0053: Corpus Custody and Private Fact-Probe Layout Attestation

## Status

Historical architecture record for the Sprint 12 Patch 067 implementation
candidate. Patch 068 introduced the intermediate corrective contract and
diagnostic matrix; Patch 069 carried and corrected that boundary, and Patch 071
supplied the first evidence-gate correction. Patches 070, 071, 072, and 073 were
not accepted at their respective first returned review boundaries. Patch 073
delivered the first custody/isolation correction and the non-reinterpretive
policy deferral. Patch 074 was the superseded Sprint 12 closeout candidate.
Patch 075 introduced bounded private static text-relocation evidence. Patch 076
preserved that private prefix and implemented distinct private `DT_RPATH` and
`DT_RUNPATH` carrier/value evidence, but its review required the Patch 077
correction, whose review required the Patch 078 closeout correction, whose review required the current Patch 079 corrective and task-value candidate and
Sprint 13 entry candidate. Current validation expectations are in the
[Patch 078 validation record](../sprints/sprint-13-patch-078-validation.md).

## Context

Patch 066 corrected GNU-property alignment and overlap handling and added a
28-object private role/property preflight. Subsequent validation identified
three evidence-integrity defects and two oracle defects:

- corpus mode repair could begin changing authenticated modes before detecting a
  newly added member;
- repair could continue through a retained descriptor after the caller-visible
  corpus root name had been replaced;
- a late verifier failure required a descriptor-bound rollback path for retained
  original modes;
- the public-JSON oracle did not reject the maintained private fact key names; and
- the binary-role ABI oracle could accept removal of both stack adjustments.

The later private-fact diagnostic matrix also requires the development C fact
probe to establish that the offsets and sizes it consumes agree with the
NASM-owned record layout.

## Decision

Patch 067 introduced descriptor-bound custody and a controlled final-verifier
restoration case. Subsequent validation identified remaining first-mutation
membership, ancestor-chain binding, rollback-activation, and rollback-error
gaps. Patch 068 defined the complete pre-mutation activation, bounded retry,
verification, and surfaced-failure contract; Patch 069 corrects the remaining
semantic-custody, signal-rollback, and directory-identity defects in that
implementation.

Corpus mode repair now retains:

```text
caller-visible parent descriptor and root name
root descriptor and creation-time identity
complete directory and regular-file descriptor set
checksum authority and manifest-authorized file hashes
original modes retained for descriptor-bound rollback
```

Patch 067 established the retained descriptor set and a late-verifier
restoration case. The Patch 068 contract requires exact membership,
object type, device/inode identity, owner, timestamps, link count, bytes, and the
parent/name binding to be revalidated at the final mutation boundary. It also
requires a failure after mutation begins to restore original modes through
retained descriptors with bounded retries, verify each restoration, surface any
rollback failure, and leave a foreign replacement untouched. Patch 069 carries
that contract and adds the corrective transaction evidence.

The private fact-probe boundary now uses an assembly-emitted descriptor:

```text
include/structs.inc
  -> role-property-layout-authority.asm
  -> fixed magic/version/field-count descriptor
  -> independent C reconciliation harness
  -> development fact probe
```

The descriptor covers every private summary/context offset and size consumed by
the probe. The C contract independently records the expected Patch 067 ABI and
rejects version or field mutations. The probe validates the descriptor before
allocation or record interpretation and no longer hardcodes assembly-owned
layout offsets.

The binary-role harness also executes a callee-entry alignment canary before the
nested PHDR call. The maintained mutation removes both matched stack adjustments
and must fail both the source-shape oracle and the rebuilt runtime harness.

## Boundaries

Patch 067 does not:

- add a public role-derived PIE/DSO distinction or IBT/SHSTK indicators, or
  reinterpret the existing coarse `mitigations.pie` field;
- change schema `0.2.0`;
- change loader authority, scanner behavior, candidate identity, capacity,
  semantic classes, scores, or report counts;
- infer runtime CET enforcement from static properties;
- run or freeze the later private-fact diagnostic matrix;
- add a runtime dependency.

The layout descriptor and fact probe are development-only objects and are not
linked into the freestanding analyzer.

## Consequences

- Corpus repair remains mode-only and fail-closed. Patch 068 defined the
  descriptor-bound original-mode restoration contract with bounded retry and
  verification; Patch 069 corrects and retains that contract.
- The maintained public-JSON private-key and ABI mutation oracles discriminate
  their targeted controlled cases.
- C/NASM reconciliation attests only the development probe's record-layout
  interpretation. It does not establish parser or classifier correctness,
  analyzer behavior, runtime CET enforcement, or publication evidence.
- Patch 068 introduced the subsequent diagnostic agreement gate with a new
  identity: 48 held-out natural objects and 48 controlled metamorphic objects.
  Patch 069 authenticates and corrects that matrix, then adds external
  reconciliation.
