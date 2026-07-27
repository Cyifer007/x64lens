# ADR 0053: Corpus Custody and Private Fact-Probe Layout Attestation

## Status

Accepted architecture for the Sprint 12 Patch 067 implementation candidate.
Patch acceptance remains governed by native, Docker, and independent validation.

## Context

Patch 066 corrected GNU-property alignment and overlap handling and added a
28-object private role/property preflight. Its review confirmed that the product
parser and normal native/container behavior were substantially sound, but found
three evidence-integrity defects and two oracle defects:

- corpus mode repair could begin changing authenticated modes before detecting a
  newly added member;
- repair could continue through a retained descriptor after the caller-visible
  corpus root name had been replaced;
- a late verifier failure needed transactional restoration of every original
  mode;
- the public-output oracle did not reject the actual private fact key names; and
- the binary-role ABI oracle could accept removal of both stack adjustments.

The strategic reviews also identified one prerequisite for a broader held-out
role/property corpus: the development C fact probe must prove that the offsets
and sizes it consumes agree with the NASM-owned record layout.

## Decision

Patch 067 closes the transaction and oracle defects before expanding the corpus.

Corpus mode repair now retains:

```text
caller-visible parent descriptor and root name
root descriptor and creation-time identity
complete directory and regular-file descriptor set
checksum authority and manifest-authorized file hashes
original modes for transactional rollback
```

Immediately before the first `fchmod`, repair revalidates exact membership,
object type, device/inode identity, owner, timestamps, link count, bytes, and the
parent/name binding. A late verification failure restores every original mode
through retained descriptors. A foreign replacement remains untouched.

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
nested PHDR call. Removing either required stack adjustment is therefore both a
source-shape failure and a runtime harness failure.

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

- Corpus repair remains mode-only, fail-closed, and transactional.
- Public-output and ABI oracles now discriminate the exact defects they claim to
  prevent.
- Private fact evidence cannot be treated as authoritative until the C/NASM ABI
  descriptor reconciles.
- The larger natural/metamorphic held-out confirmation remains a subsequent
  diagnostic gate with a new identity.
