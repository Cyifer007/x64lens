# Sprint 12 Plan

## Status

Active loader and mitigation precision sprint after Sprint 11 Patch 061 closeout.

## Sprint goal

Resolve loader-identity, executable-region, and mitigation-evidence ambiguities
that would otherwise corrupt corpus labels or defensive triage.

## Entry order from Sprint 11 diagnostics

1. Validate program-header ranges, alignment, congruence, entrypoint behavior, and explicit extended-numbering outcomes.
2. Define overlapping executable-region scan, deduplication, and provenance semantics.
3. Distinguish PIE executables from shared objects through bounded evidence.
4. Parse bounded GNU property notes for x86 IBT and SHSTK indicators.
5. Rerun the diagnostic campaign under a new identifier after behavior changes.

## Planned deliverables

- [ ] Distinguish PIE executables from `ET_DYN` shared objects through bounded evidence.
- [ ] Parse bounded GNU property notes for x86 IBT and SHSTK indicators.
- [ ] Define overlapping executable `PT_LOAD` scan, deduplication, and count semantics.
- [ ] Validate or explicitly reject unsupported `p_align`, offset/virtual congruence, virtual ranges, and executable-entrypoint states.
- [ ] Detect ELF extended-numbering cases and provide bounded support or stable unsupported outcomes.
- [ ] Extend deterministic mitigation and malformed-input fixtures for every new parser path.
- [ ] Re-run the diagnostic suite and record changed facts separately from Sprint 11 rows.

## Acceptance criteria

- [ ] Program headers remain executable authority.
- [ ] No new table is read without bounded range and count validation.
- [ ] PIE, DSO, IBT, and SHSTK facts have controlled positive, negative, contradictory, truncated, and duplicate cases where applicable.
- [ ] Overlapping segments cannot silently duplicate counts under the chosen policy.
- [ ] Native and Docker facts agree.
- [ ] Diagnostic measurements are versioned separately after behavior changes.

## Handoff

Sprint 13 completes the release-facing semantic surface using the corrected
loader and mitigation facts.
