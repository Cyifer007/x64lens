# ADR 0054: Held-Out Private Role and GNU-Property Confirmation

## Status

Accepted architecture for the Sprint 12 Patch 068 implementation candidate.
Patch acceptance remains subject to native, Docker, parity, and independent
validation against the exact candidate source.

## Context

Patch 067 attested the C/NASM development fact-probe layout but intentionally
left the broader held-out role/property confirmation for a later patch. Its
review also found transaction and oracle defects that had to be corrected before
new evidence could be trusted:

- corpus mode repair could mutate modes before detecting a member added at the
  first mutation boundary;
- a caller-visible ancestor replacement could detach the authenticated corpus
  from the path for which success was reported;
- a post-mutation exception could precede rollback activation, and rollback
  errors could be suppressed;
- the Patch 063 displaced-root oracle still expected behavior that Patch 067
  correctly rejected;
- the private installer could lose its created-directory list when the first
  authorization write failed;
- the layout-authority object omitted the NASM structure include from its Make
  prerequisites; and
- the public-output oracle did not exercise every public command path.

## Decision

Patch 068 closes those integrity defects before confirming any new fact surface.
Corpus repair now retains the complete descriptor-bound tree and independently
reauthenticates the caller-visible absolute path at mutation and return
boundaries. An idempotent descriptor operation establishes a final maintained
mutation boundary; the complete path and member set are proven again before the
first mode-changing operation. Rollback is activated before mutation, retries
mode restoration, verifies every restored mode, and reports rollback failure
rather than suppressing it.

The private installer retains one caller-owned created-directory transaction
list across directory creation, authorization, application, and rollback. A
failed first authorization write can therefore be retried and rolled back
without losing manager-created directory identities.

After those corrections, Patch 068 adds a development-only 96-object
confirmation matrix:

```text
48 natural compiler/linker outputs
  two compilers
  two source variants
  three role constructions
  four GNU-property states

48 metamorphic objects
  24 canonical/exact-alias positive objects
  24 unknown, conflicting, contradictory, or malformed edge objects
```

An independent standard-library ELF reader authors the expected private fact
vector for every object. The C/NASM fact probe must emit that exact vector three
times byte-identically. Natural objects require 48 unique hashes and zero hash
overlap with the authenticated provisional corpus. Natural and metamorphic
strata close independently.

## Boundaries

Patch 068 does not:

- add public PIE/DSO, IBT, or SHSTK fields;
- change schema `0.2.0`;
- infer runtime CET enforcement from static GNU properties;
- change executable-region authority, scanner behavior, candidate identity,
  capacity, semantic classes, scores, or public count meanings;
- reopen executable-overlap normalization;
- begin candidate-scoped decoding or concurrency; or
- freeze the confirmatory research campaign.

The held-out matrix remains diagnostic, unfrozen, and publication-ineligible.
It confirms private fact acquisition only; a later policy gate owns any public
indicator decision.

## Consequences

- Corpus mode repair is still a mode-only operation, but its mutation and
  rollback boundaries are independently testable and fail closed.
- Private orchestration recovery retains created-directory identity through an
  authorization-write failure.
- Incremental builds rebuild the assembly layout authority when
  `include/structs.inc` changes.
- Public `info`, `mitigations`, `gadgets`, and `analyze` paths remain free of the
  private role/property vocabulary.
- Sprint 12 may proceed to bounded external comparison, native/container private
  fact parity, and a later public-policy decision without conflating those gates.
