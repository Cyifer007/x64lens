# ADR 0054: Private Role/Property Diagnostic Matrix — Held-Out Natural and Controlled Metamorphic Strata

## Status

Accepted architecture for the historical Sprint 12 Patch 068 implementation
candidate. Patch 069 corrected and authenticated the matrix, Patch 070 was
rejected, and Patch 071 supplied the first evidence-gate correction. The current
Patch 072 candidate carries the remaining correction and acquisition/parity
gates without promoting the diagnostic result. Product, delivery, and parity
acceptance remain subject to separate validation against the exact candidate
source.

## Context

Patch 067 attested the C/NASM development fact-probe layout but intentionally
left the broader private-fact matrix for a later patch. Subsequent validation
identified transaction and oracle defects that had to be corrected before new
evidence could be trusted:

- corpus mode repair could mutate modes before detecting a member added at the
  first mutation boundary;
- a caller-visible ancestor replacement could detach the authenticated corpus
  from the path for which success was reported;
- a post-mutation exception could precede rollback activation, and rollback
  errors could be suppressed;
- the Patch 063 displaced-root oracle still expected behavior that Patch 067
  correctly rejected;
- the layout authority did not rebuild after its NASM structure definition
  changed; and
- the public-output oracle did not exercise every public command path.

## Decision

The Patch 068 candidate contract defines corrections for those integrity
boundaries before adding a new private fact surface. It requires corpus repair
to retain the complete descriptor-bound tree and independently reauthenticate
the caller-visible absolute path at mutation and return boundaries. An
idempotent descriptor operation establishes a final maintained mutation
boundary; the complete path and member set must be proven again before the first
mode-changing operation. Rollback must be activated before mutation, retry and
verify restoration of every original mode, and report rollback failure rather
than suppressing it.

After those corrections, Patch 068 added a development-only 96-object
diagnostic agreement matrix:

```text
48 held-out natural toolchain-produced ELF objects
  GCC/Clang object inputs linked by ld.bfd
  two compilers
  two source variants
  three role constructions
  four GNU-property states

48 controlled metamorphic objects
  24 canonical/exact-alias positive objects
  24 unknown, conflicting, contradictory, or malformed edge objects
```

An independent standard-library ELF reader authors the expected private fact
vector for every object. The C/NASM fact probe must emit that exact vector three
times byte-identically. Held-out natural objects require 48 unique hashes and
zero hash overlap with an authenticated, verified provisional-corpus inventory.
Natural and metamorphic strata must be reported separately and evaluated
independently.

## Boundaries

Patch 068 does not:

- add a public role-derived PIE/DSO distinction or IBT/SHSTK indicators, or
  reinterpret the existing coarse `mitigations.pie` field;
- change schema `0.2.0`;
- infer runtime CET enforcement from static GNU properties;
- change executable-region authority, scanner behavior, candidate identity,
  capacity, semantic classes, scores, or public count meanings;
- reopen executable-overlap normalization;
- begin candidate-scoped decoding or concurrency; or
- freeze the confirmatory research campaign.

The natural and metamorphic strata remain separate, diagnostic, unfrozen, and
publication-ineligible. The matrix checks private fact agreement only; it is not
toolchain-prevalence evidence, and a later policy gate owns any public indicator
decision.

## Consequences

- Corpus mode repair is still a mode-only operation, but its mutation and
  rollback boundaries are independently testable and fail closed.
- Incremental builds rebuild the assembly layout authority when
  `include/structs.inc` changes.
- Public `info`, `mitigations`, `gadgets`, and `analyze` paths remain free of the
  private role/property vocabulary.
- Patch 069 subsequently added bounded external comparison. Patch 072 carries
  outcome-blind external-natural acquisition and native/container private-fact
  parity, while Patch 073 separately owns any public-policy decision.
