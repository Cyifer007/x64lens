# ADR 0050: Fact-First Binary Role Lattice and Measured Overlap Deferral

## Status

Accepted architecture for Sprint 12. The Patch 064 implementation did not pass
validation. Patch 068 carried an intermediate corrective candidate; Patch 069
carried the decision forward, and the current Patch 070
candidate leaves the runtime lattice unchanged while correcting its development-
evidence gates. Independent acceptance remains pending.

## Context

Patch 063 retained original program-header identity in each executable-region
record and a dense contributor mask in each candidate-evidence record. That
lossless provenance made it possible to measure whether executable-region
normalization would remove material repeated work or capacity pressure before
changing scanner ordering or count semantics.

The diagnostic survey covered the authenticated 24-target provisional corpus
and 3,091 unique-inode system targets. Across 3,115 targets and 1,403,074,388
executable bytes, it observed no target with executable-region overlap,
same-slope repeated executable bytes, or repeated exact candidate identities.
Normalization would have recovered no candidate slots and changed no capacity
outcome in this sample. Controlled overlap fixtures also showed that identity
deduplication can change ordering, candidate windows, count tiers, and the
fail-closed 4,096 capacity result.

The more material remaining loader ambiguity is the public PIE indicator. The
current field is derived from `ET_DYN`, but shared objects also use `ET_DYN`.
Sprint 12 therefore needs a bounded evidence layer before it can consider a
release-facing PIE-versus-DSO policy.

## Decision

### Preserve overlap provenance and defer normalization

Patch 064 records a machine-readable diagnostic decision that:

- retains the Patch 063 original-PHDR and dense contributor provenance;
- does not union executable scan ranges;
- does not deduplicate candidates;
- does not change candidate order, counts, completeness, or capacity behavior;
- reopens normalization only when a newly admitted non-fixture corpus reaches
  at least 5 percent same-slope repeated executable bytes or 41 repeated exact
  identities on at least two targets.

This is a measured deferral, not a claim that executable overlap never occurs.

### Add an internal fact-first binary-role lattice

`phdr_summary` gains bounded internal facts for:

- `PT_INTERP` carrier count;
- `DT_FLAGS_1` carrier count and combined value;
- `DT_SONAME` carrier count and retained string-table index;
- bounded evidence that the retained SONAME index resolves to a nonempty,
  in-range, NUL-terminated string;
- evidence and contradiction bits; and
- one internal role state.

The summary grows from 144 to 200 bytes. The added 56 bytes are fixed command
state, not measured RSS.

`src/binary_role.asm` consumes only completed PHDR-summary facts, including the
copied ELF type and entrypoint, and assigns exactly one internal state. Patch 065
corrected the earlier implementation that reread mapped ELF bytes, and the
Patch 071 candidate carries that boundary forward without changing the
runtime analyzer:

```text
unknown
executable_like
shared_object_like
ambiguous
contradictory
```

The lattice uses these rules:

- `ET_DYN` alone remains `unknown`.
- `ET_DYN` plus `PT_INTERP` or `DF_1_PIE` is executable-like unless shared
  evidence conflicts.
- `ET_DYN` plus validated `DT_SONAME` string evidence, no strong executable
  evidence, and a zero entrypoint is shared-object-like.
- `ET_DYN` plus a nonzero entrypoint but no `PT_INTERP` or `DF_1_PIE` evidence
  is ambiguous, including when validated SONAME evidence is also present.
- Strong executable and shared evidence together is contradictory.
- Duplicate or conflicting role carriers are contradictory, not last-wins.
- `ET_EXEC` remains executable-like unless incompatible dynamic role evidence
  is present.

The existing public `mitigations.pie` indicator remains unchanged. Patch 064
adds no CLI field, JSON field, schema transition, score, semantic class, or
public PIE/DSO claim.

### Bound the new parser inputs

The `PT_INTERP` file span must contain at least one non-NUL path byte, be
file-backed, be no larger than 4,096 bytes, have no interior NUL, and end in one
NUL inside its checked range. Raw `DT_SONAME` presence is insufficient: every
carrier is validated, and each retained string-table index must resolve to a
bounded, nonempty, NUL-terminated string before it becomes shared-object
evidence. Dynamic role tags are consumed only through the existing bounded
`PT_DYNAMIC` iterator. On role-consuming command paths, malformed or unsupported
outcomes remain fail-closed before report output. Patch 065 introduced these
string-validation corrections, Patch 069 carried them forward, and the current
Patch 070 candidate leaves them unchanged.

## Consequences

### Positive

- The scanner and all public count meanings remain stable.
- Loader-role evidence becomes explicit without overstating `ET_DYN`.
- Unknown, ambiguous, and contradictory states remain explicit internally;
  duplicate or conflicting carriers force the contradictory state.
- GNU-property IBT/SHSTK parsing was introduced privately by Patch 065 and
  remains separate from public report policy in the Patch 070 candidate.
- The dependency-free, decoder-free, one-worker reference profile is unchanged.

### Costs

- `phdr_summary` grows by 56 bytes.
- Three command orchestrators call one additional internal classifier.
- The public PIE label remains intentionally broad until a later output-policy
  and schema review.

### Rejected alternatives

- Normalize executable overlap immediately despite zero measured activation.
- Treat `ET_DYN` as equivalent to PIE.
- Treat `PT_INTERP`, `DF_1_PIE`, or `DT_SONAME` as individually infallible.
- Apply first-wins or last-wins semantics to duplicate role carriers.
- Add a public schema field before positive, negative, ambiguous,
  contradictory, duplicate, and malformed fixtures exist.

## Validation

```bash
make patch063-corrective-regression-smoke
make sprint12-phdr-validity-smoke
make sprint12-overlap-provenance-smoke
make sprint12-overlap-decision-smoke
make sprint12-binary-role-smoke
make validation-smoke
make docker-validation-smoke
make native-docker-json-parity-smoke
```
