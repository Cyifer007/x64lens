# ADR 0053: Corpus Custody and Private Fact-Probe Layout Attestation

## Status

Accepted architecture for the Sprint 12 Patch 067 implementation candidate.
Patch acceptance remains governed by native, Docker, and independent validation.

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

A broader held-out role/property corpus also requires the development C fact
probe to establish that the offsets and sizes it consumes agree with the
NASM-owned record layout.

## Decision

The Patch 067 candidate addresses the transaction and oracle defects before any
corpus expansion.

Corpus mode repair now retains:

```text
caller-visible parent descriptor and root name
root descriptor and creation-time identity
complete directory and regular-file descriptor set
checksum authority and manifest-authorized file hashes
original modes retained for descriptor-bound rollback
```

Immediately before the first `fchmod`, repair revalidates exact membership,
object type, device/inode identity, owner, timestamps, link count, bytes, and the
parent/name binding. A late verification failure enters descriptor-bound
rollback for every retained original mode. The controlled injected-failure case
requires restoration of the root and affected member modes. A foreign
replacement remains untouched.

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

- add public PIE/DSO, IBT, or SHSTK fields;
- change schema `0.2.0`;
- change loader authority, scanner behavior, candidate identity, capacity,
  semantic classes, scores, or report counts;
- infer runtime CET enforcement from static properties;
- run or freeze the broader held-out corpus;
- add a runtime dependency.

The layout descriptor and fact probe are development-only objects and are not
linked into the freestanding analyzer.

## Consequences

- Corpus repair remains mode-only and fail-closed; late failure enters
  descriptor-bound rollback, with controlled restoration covered by the focused
  probe.
- The maintained public-JSON private-key and ABI mutation oracles discriminate
  their targeted controlled cases.
- C/NASM reconciliation attests only the development probe's record-layout
  interpretation. It does not establish parser or classifier correctness,
  analyzer behavior, runtime CET enforcement, or publication evidence.
- The larger natural/metamorphic held-out confirmation remains a subsequent
  diagnostic gate with a new identity.
