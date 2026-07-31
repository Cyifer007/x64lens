# ADR 0055: Authenticated Role/Property Reconciliation Against GNU readelf

## Status

Accepted architecture for the Sprint 12 Patch 069 implementation candidate.
Product, native/container, and delivery acceptance remain subject to separate
validation against the exact candidate source.

## Context

Patch 068 introduced a 96-object private binary-role and GNU-property diagnostic
matrix, but follow-up validation showed that its maintained gate did not yet
bind all of the authorities it claimed to consume. That validation also showed
remaining corpus-repair transaction gaps:

- semantic verification could reopen mutable pathnames instead of consuming a
  retained descriptor-authoritative view;
- a signal after a real mode change could bypass complete rollback;
- root and nested-directory metadata changes were not represented in the
  retained tree identity;
- the matrix could report zero provisional-corpus overlap when the corpus was
  unavailable;
- the authority, analyzer, public schema, expected vectors, and complete fact
  vector were not all retained by the maintained result; and
- edge-object identities did not guarantee distinct parser-visible layouts.

The private fact plane also required an independent external reconciliation
before any public role or CET policy decision. GNU `readelf` is suitable as a
bounded comparator for represented ELF header, program-header, dynamic-table,
and GNU-property-note text. It is not runtime authority and it does not expose
all x64lens-private provenance or overlap facts.

## Decision

Patch 069 first closes the corpus and matrix custody defects, then adds a
separate diagnostic reconciliation authority:

```text
authenticated 96-object private-fact result
  + authenticated GNU readelf executable and version
  + exact readelf -hW/-lW/-dW/-nW commands
  -> retained raw comparator output
  -> field authority class: direct, derived, ambiguous, or unavailable
  -> per-object disposition: match, mismatch, ambiguous, unavailable, or not_eligible
  -> zero-unexplained-mismatch acceptance only over eligible dispositions
```

The corpus mode-repair path verifies semantic content through retained
file-descriptor authority, binds directory sizes as part of the retained tree
identity, defers and handles termination across the mutation transaction, and
restores every original mode before reporting a failed repair.

The 96-object matrix now requires and authenticates:

- its task authority;
- the analyzer executable;
- schema `0.2.0`;
- the private fact probe;
- the complete authenticated 24-target provisional corpus;
- all 18 expected and observed private fact fields per object;
- all four public command paths and both output streams; and
- 24 parser-visible edge layouts.

The `readelf` reconciliation assigns a field-level authority class before
comparison: direct, reproducibly derived, ambiguous, or unavailable. It records
a separate per-object disposition: `match`, `mismatch`, `ambiguous`,
`unavailable`, or `not_eligible`. Only `match` or `mismatch` dispositions backed
by direct or reproducibly derived authority enter the eligible denominator.
Ambiguous and unavailable cells remain explicit, as do `not_eligible` cells
that are inapplicable for the object/field combination; none may be converted
into agreement or disagreement.

## Boundaries

Patch 069 does not:

- make `readelf` loader, parser, mitigation, or reporting authority;
- add public PIE-versus-DSO, IBT, or SHSTK fields;
- change schema `0.2.0`;
- claim runtime CET enforcement from static GNU properties;
- redefine any candidate or mitigation count;
- change scanner, matcher, classifier, side-car, scoring, or reporter behavior;
- reopen executable-overlap normalization;
- qualify comparative latency, RSS, or cross-tool coverage; or
- freeze the confirmatory campaign.

The reconciliation remains diagnostic, unfrozen, and publication-ineligible.
A later native/container private-fact parity gate and a separate public-policy
review still own any public exposure decision.

## Consequences

- Private role/property facts have a reproducible, external, field-scoped
  comparator without surrendering x64lens authority.
- Mismatches cannot be hidden inside an aggregate label; every field disposition
  and raw `readelf` output is retained.
- Legitimate comparator limitations remain visible instead of being treated as
  false negatives.
- Public output and schema remain stable while Sprint 12 closes the private fact
  evidence plane.
