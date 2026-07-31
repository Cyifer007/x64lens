# Sprint 12 Plan

## Status

Active loader and mitigation precision sprint after Sprint 11 Patch 061
closeout. Patch 064 did not pass validation, and Patch 065 required a further
correction. Patch 066 through Patch 068 required correction; Patch 069 is the
current implementation candidate pending acceptance validation.

Related implementation records:

- [ADR 0048](../adr/0048-phdr-validity-and-extended-numbering-boundary.md)
- [Patch 062 validation](sprint-12-patch-062-validation.md)
- [ADR 0049](../adr/0049-executable-overlap-provenance-seam.md)
- [Patch 063 validation](sprint-12-patch-063-validation.md)
- [ADR 0050](../adr/0050-fact-first-binary-role-lattice.md)
- [Patch 064 validation](sprint-12-patch-064-validation.md)
- [ADR 0051](../adr/0051-bounded-private-gnu-property-evidence.md)
- [Patch 065 validation](sprint-12-patch-065-validation.md)
- [ADR 0052](../adr/0052-role-property-metamorphic-preflight.md)
- [Patch 066 validation](sprint-12-patch-066-validation.md)
- [ADR 0053](../adr/0053-corpus-custody-and-private-layout-attestation.md)
- [Patch 067 validation](sprint-12-patch-067-validation.md)
- [ADR 0054](../adr/0054-private-role-property-diagnostic-matrix.md)
- [Patch 068 validation](sprint-12-patch-068-validation.md)
- [ADR 0055](../adr/0055-authenticated-role-property-readelf-reconciliation.md)
- [Patch 069 validation](sprint-12-patch-069-validation.md)

## Sprint goal

Resolve loader-identity, executable-region, and mitigation-evidence ambiguities
that would otherwise corrupt corpus labels or defensive triage.

## Entry order from Sprint 11 diagnostics

1. Validate program-header ranges, alignment, congruence, entrypoint behavior, and explicit extended-numbering outcomes.
2. Retain original PHDR identity and dense candidate-contributor provenance without changing scan or count policy.
3. Measure overlap incidence and redundant scan work, then decide whether executable-byte-union normalization should proceed.
4. Add bounded internal PIE-versus-shared-object evidence without changing the public PIE indicator.
5. Parse bounded GNU property notes for x86 IBT and SHSTK indicators.
6. Correct the Patch 067 corpus mutation and rollback boundaries, rebuild the
   private-layout authority from its structure definition, and extend leakage
   checks across all four file-analysis commands.
7. Add a 96-object private-fact diagnostic agreement gate under a new identity:
   48 held-out natural objects plus 48 controlled metamorphic objects.
8. Reconcile the private facts against bounded external ELF evidence
   (`readelf -hW/-lW/-dW/-nW`). Patch 069.
9. Prove native/container private-fact parity.
10. Only then review whether compatible public `0.2.x` role or GNU-property
   indicators are justified.

## Planned deliverables

- [x] Validate `p_align`, offset/virtual congruence, virtual ranges, and executable-entrypoint states. Patch 062.
- [x] Detect ELF extended-numbering cases and return a bounded stable unsupported outcome after structural validation. Patch 062.
- [x] Retain original PHDR identity and dense same-slope candidate-contributor provenance without changing scan/count behavior. Patch 063.
- [x] Measure executable-overlap incidence and redundant scan work, then record the diagnostic decision to defer executable-byte-union normalization. Patch 064.
- [ ] If normalization is selected, define deduplication and public count semantics while preserving Patch 063 contributor provenance.
- [ ] Accept an internal role-evidence lattice that keeps `ET_DYN` alone unknown
  and preserves unknown, executable-like, shared-object-like, ambiguous, and
  contradictory states. The Patch 064 design is carried by the current
  Patch 069 candidate.
- [ ] Accept bounded private GNU property-note evidence for x86 IBT and SHSTK
  without adding public report fields or changing schema `0.2.0`. Corrected in
  the current Patch 069 candidate.
- [x] Extend deterministic malformed-input coverage for the Patch 062 PHDR and extended-numbering paths; later Sprint 12 parsers must add their own fixtures.
- [x] Patch 068 introduced a 96-object private-fact diagnostic agreement gate
  under a distinct identity. The current Patch 069 candidate authenticates and
  corrects it while keeping the 48 held-out natural objects separate from the
  48 controlled metamorphic objects. Gate acceptance remains pending.
- [x] Reconcile eligible private facts against authenticated GNU
  `readelf -hW/-lW/-dW/-nW` evidence while retaining ambiguous, unavailable,
  and `not_eligible` cells. Patch 069.
- [ ] Prove native/container private-fact parity.
- [ ] Only then review whether compatible public `0.2.x` role or GNU-property
  indicators are justified.

## Patch sequence

1. **Patch 062:** shared ordinary PHDR validity, explicit extended-numbering unsupported/malformed outcomes, and Patch 061 transaction corrections.
2. **Patch 063:** Patch 062 corrective hardening plus original-PHDR and dense contributor provenance; scan normalization remains deferred.
3. **Patch 064:** intermediate source that did not pass validation, containing Patch 063 corrective hardening, a measured decision to defer normalization, and an internal-only role-evidence lattice with public output unchanged.
4. **Patch 065:** intermediate candidate that required correction, carrying the Patch 064 corrections plus bounded private GNU-property IBT/SHSTK facts with canonical carrier views and contributor provenance.
5. **Patch 066:** controlled 28-object role/property metamorphic preflight, with no new public report field or schema change; review required further correction.
6. **Patch 067:** corpus-custody correction plus a recursive public-JSON
   private-key oracle, ABI canary, and C/NASM fact-probe layout attestation.
7. **Patch 068:** remaining Patch 067 transaction/oracle correction plus a
   private-fact diagnostic agreement gate for 48 held-out natural objects and 48
   controlled metamorphic objects.
8. **Patch 069:** remaining Patch 068 corpus/matrix custody correction plus authenticated 96-object GNU `readelf` field reconciliation.
9. **Conditional:** reopen executable-byte-union normalization, deduplication, and public count semantics only when the recorded activation thresholds are crossed.
10. **Parity:** native/container private-fact parity over the authenticated matrix.
11. **Later policy gate:** decide whether compatible public `0.2.x` role or GNU-property indicators are justified.
12. **Closeout:** Sprint 12 reconciliation.

## Acceptance criteria

- [x] Program headers remain executable authority.
- [x] Patch 062 reads section-header entry zero only through bounded fixed-size validation; later tables retain the same requirement.
- [ ] The Patch 069 candidate's internal PIE-versus-shared-object lattice passes
  controlled unknown, executable-like, shared-object-like, ambiguous,
  contradictory, duplicate, malformed, and unsupported cases.
- [ ] The Patch 069 candidate's private IBT and SHSTK facts pass controlled
  positive, negative, contradictory, truncated, duplicate, overlap, cap, and
  unknown-property cases.
- [x] Overlap contributors are retained internally without changing current counts. Patch 063.
- [x] A measured decision records that executable-byte-union normalization remains deferred under explicit reopening thresholds. Patch 064.
- [ ] If selected, the normalization policy prevents silent duplicate scan/count behavior and preserves contributing-PHDR evidence.
- [ ] Positive role-controlled anchors establish address-coordinate calibration.
- [ ] All five task paths have complete runtime-closure evidence.
- [ ] Comparison qualification is withheld unless both calibration and closure
  gates pass.
- [ ] Native and Docker facts agree.
- [ ] Diagnostic measurements are versioned separately after behavior changes.
- [ ] The private-fact matrix of 48 held-out natural objects and 48 controlled
  metamorphic objects remains diagnostic, unfrozen, and publication-ineligible.

## Handoff

Sprint 13 completes the release-facing semantic surface using the corrected
loader and mitigation facts.


## Patch 066 boundary

Patch 066 corrects Patch 065 acceptance defects and adds the 28-object private
role/property metamorphic preflight. It adds no public role, IBT, or SHSTK field,
does not change schema `0.2.0`, and does not complete the later private-fact
matrix or public-policy gates.


## Patch 067 boundary

Patch 067 adds no public role or property field and does not widen the corpus. It
introduces corpus-custody and oracle corrections, then attests every
private fact-probe offset and size through a NASM-emitted descriptor and an
independent C contract. That reconciliation covers probe record interpretation,
not analyzer behavior. Patch 068 corrects the remaining custody boundary and adds
the separate natural/metamorphic diagnostic matrix.


## Patch 068 boundary

At its source boundary, Patch 068 added no public role or GNU-property field. Its
contract addressed the remaining Patch 067 corpus mutation and rollback
boundaries, rebuilt the private-layout authority from its structure definition,
extended private-field leakage checks across all four file-analysis commands,
and added a matrix for 48 held-out natural objects plus 48 controlled metamorphic
objects. Patch 068 required Patch 069 correction. The matrix remains diagnostic,
unfrozen, and publication-ineligible. At the Patch 068 boundary, bounded
external ELF reconciliation (`readelf -hW/-lW/-dW/-nW`) was a separate future
gate; Patch 069 now adds that reconciliation. Native/container private-fact
parity and public-policy review remain separate later gates.


## Patch 069 boundary

The current Patch 069 candidate adds no public role or GNU-property field. It
corrects the remaining
Patch 068 corpus semantic-custody, signal rollback, directory-identity, matrix
authority, private-leakage, retained-vector, edge-layout, and incremental-build
oracles. It then reconciles the authenticated matrix against exact GNU
`readelf -hW/-lW/-dW/-nW` evidence with field-specific eligibility rules.

The reconciliation remains diagnostic, unfrozen, and publication-ineligible.
`readelf` remains external evidence rather than runtime authority. Native/
container private-fact parity and public-policy review remain separate gates.

## Patch 070 boundary

Patch 070 corrects the remaining Patch 069 corpus, comparator, leak-oracle,
private-package, and Make prerequisite defects. It fixes the controlled field
disposition denominator at 1,224 matches, 96 ambiguous, 288 unavailable, and
120 not-eligible cells, and adds one positive fail-closed property-overlap
anchor. It also adds the 27-case, 81-execution whole-batch transaction pilot.
The pilot is a prerequisite for later below-floor throughput measurement; it
does not authorize divided latency or public role/property fields.
