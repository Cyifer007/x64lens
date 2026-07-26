# Sprint 12 Plan

## Status

Active loader and mitigation precision sprint after Sprint 11 Patch 061 closeout.

Related implementation records:

- [ADR 0048](../adr/0048-phdr-validity-and-extended-numbering-boundary.md)
- [Patch 062 validation](sprint-12-patch-062-validation.md)
- [ADR 0049](../adr/0049-executable-overlap-provenance-seam.md)
- [Patch 063 validation](sprint-12-patch-063-validation.md)

## Sprint goal

Resolve loader-identity, executable-region, and mitigation-evidence ambiguities
that would otherwise corrupt corpus labels or defensive triage.

## Entry order from Sprint 11 diagnostics

1. Validate program-header ranges, alignment, congruence, entrypoint behavior, and explicit extended-numbering outcomes.
2. Retain original PHDR identity and dense candidate-contributor provenance without changing scan or count policy.
3. Measure overlap incidence and redundant scan work, then decide whether executable-byte-union normalization should proceed.
4. Distinguish PIE executables from shared objects through bounded evidence.
5. Parse bounded GNU property notes for x86 IBT and SHSTK indicators.
6. Run a corrected held-out diagnostic confirmation under a new identifier
   after behavior changes, using positive role-controlled coordinate anchors
   and complete runtime closure for all five task paths.

## Planned deliverables

- [x] Validate `p_align`, offset/virtual congruence, virtual ranges, and executable-entrypoint states. Patch 062.
- [x] Detect ELF extended-numbering cases and return a bounded stable unsupported outcome after structural validation. Patch 062.
- [x] Retain original PHDR identity and dense same-slope candidate-contributor provenance without changing scan/count behavior. Patch 063.
- [ ] Measure executable-overlap incidence and redundant scan work, then decide whether executable-byte-union normalization should proceed.
- [ ] If normalization is selected, define deduplication and public count semantics while preserving Patch 063 contributor provenance.
- [ ] Distinguish PIE executables from `ET_DYN` shared objects through bounded evidence. Patch 064 completes the private fact lattice; a later patch owns public policy.
- [ ] Parse bounded GNU property notes for x86 IBT and SHSTK indicators.
- [x] Extend deterministic malformed-input coverage for the Patch 062 PHDR and extended-numbering paths; later Sprint 12 parsers must add their own fixtures.
- [ ] Run the corrected held-out diagnostic confirmation under a new campaign
  identity and record its facts separately from Sprint 11 rows and replays.

## Patch sequence

1. **Patch 062:** shared ordinary PHDR validity, explicit extended-numbering unsupported/malformed outcomes, and Patch 061 transaction corrections.
2. **Patch 063:** Patch 062 corrective hardening plus original-PHDR and dense contributor provenance; scan normalization remains deferred.
3. **Next:** measure executable-overlap incidence and redundant scan work, then decide whether normalization proceeds.
4. **If selected:** implement executable-byte-union normalization, deduplication, and public count semantics while preserving contributor provenance.
5. **Then:** bounded PIE-versus-DSO identity.
6. **Then:** bounded GNU-property IBT/SHSTK evidence.
7. **Closeout:** corrected held-out diagnostic confirmation and Sprint 12 reconciliation.

## Acceptance criteria

- [x] Program headers remain executable authority.
- [x] Patch 062 reads section-header entry zero only through bounded fixed-size validation; later tables retain the same requirement.
- [ ] PIE, DSO, IBT, and SHSTK facts have controlled positive, negative, contradictory, truncated, and duplicate cases where applicable.
- [x] Overlap contributors are retained internally without changing current counts. Patch 063.
- [ ] A measured decision records whether executable-byte-union normalization proceeds.
- [ ] If selected, the normalization policy prevents silent duplicate scan/count behavior and preserves contributing-PHDR evidence.
- [ ] Positive role-controlled anchors establish address-coordinate calibration.
- [ ] All five task paths have complete runtime-closure evidence.
- [ ] Comparison qualification is withheld unless both calibration and closure
  gates pass.
- [ ] Native and Docker facts agree.
- [ ] Diagnostic measurements are versioned separately after behavior changes.
- [ ] Held-out confirmation evidence remains diagnostic, unfrozen, and
  publication-ineligible.

## Handoff

Sprint 13 completes the release-facing semantic surface using the corrected
loader and mitigation facts.
