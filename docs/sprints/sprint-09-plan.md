# Sprint 09 Plan

## Status

Active.

## Sprint goal

Make candidate validity, evidence source, analysis completeness, and report
identity explicit before adding more primitive families.

## Planned deliverables

- [x] Add a fixed-size analysis-summary record for command identity and bounded
  completion facts.
- [x] Add candidate capacity, truncation, dropped-count knowledge, region
  progress, and analysis-complete facts to successful reports.
- [x] Add top-level report type and command identity.
- [x] Introduce schema `0.2.0` and migration notes.
- [x] Add representative schema `0.1.0` compatibility validation.
- [x] Preserve `gadgets` and `analyze` JSON parity while distinguishing command
  identity.
- [x] Add an evidence side-car record keyed by candidate index.
- [x] Distinguish raw candidates, exact suffix observations, semantic-exact
  classifications, and future decoder-validated facts per candidate.
- [x] Add per-candidate evidence kind and validator identity to JSON.
- [ ] Measure exact-suffix false-positive and undercount risk on controlled and
  selected system binaries.
- [ ] Define the embedded-decoder decision gate from measured gaps.
- [ ] Keep raw scanner output independently measurable.

## Patch sequence

1. **Patch 040:** report identity, command identity, complete-analysis summary,
   schema `0.2.0`, historical `0.1.0` compatibility, and focused parity gates.
2. **Patch 041:** fixed-size candidate evidence side-car keyed by candidate
   index, exact-suffix and semantic-exact provenance, ABI correction, formal
   schema enforcement, and validation/evidence hardening.
3. **Decoder-gap patch:** controlled and selected-system-binary reconciliation,
   preserved comparison artifacts, and the embedded-decoder decision record.

The sequence is intentionally additive. Patch 040 does not place variable-length
provenance in `gadget_record`, and later provenance work must not replace raw
scanner facts or existing metrics.

## Acceptance criteria

- [x] Existing raw, exact, semantic, unknown, and scored counts retain their
  documented meanings.
- [x] Successful reports state whether bounded candidate enumeration completed
  without capacity truncation.
- [x] Schema validators reject internally inconsistent identity or completeness
  state.
- [x] `gadgets` and `analyze` maintain one JSON implementation and shared facts.
- [x] Candidate-arena overflow remains fail-closed with no partial stdout.
- [x] Candidate provenance is additive and does not redefine historical counts.
- [ ] New decoder-validity metrics are additive, not replacements.
- [ ] The decoder decision is documented from evidence, not preference.

## Out of scope

- Mandatory embedded decoder dependency.
- Broad primitive expansion.
- Publication-grade benchmark campaign.
- Intentional partial-report output before scanner progress and dropped-count
  semantics are implemented and validated.

## Handoff

Patch 041 completes the candidate provenance foundation. The next Sprint 9
patch measures decoder gaps on controlled and selected system binaries, records
comparison provenance, and decides whether an embedded decoder is justified.
Sprint 10 expands primitive coverage only after that measured decision gate.
