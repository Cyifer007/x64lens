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
- [x] Add a reproducible exact-suffix/canonical-boundary gap campaign over the
  controlled fixture and selected system binaries.
- [x] Define the embedded-decoder decision gate and preserve hashes, commands,
  raw reports, disassembly, timing/RSS smoke facts, and categorized differences.
- [x] Keep raw scanner output independently measurable.
- [ ] Review authoritative local campaign evidence and record the embedded-
  decoder decision.

## Patch sequence

1. **Patch 040:** report identity, command identity, complete-analysis summary,
   schema `0.2.0`, retained representative final-shape `0.1.0` compatibility,
   and focused parity gates.
2. **Patch 041:** fixed-size candidate evidence side-car keyed by candidate
   index, exact-suffix and semantic-exact provenance, ABI correction, formal
   schema enforcement, and validation/evidence hardening.
3. **Patch 042:** portable public-bundle policy, controlled and selected-system
   decoder-gap measurement, comparison artifact provenance, and the explicit
   embedded-decoder decision gate.
4. **Decision closeout patch, only if needed:** review authoritative campaign
   evidence and record whether decoder embedding is deferred, optional, or
   approved behind an adapter.

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
- [ ] Any future decoder-validity metrics are additive, not replacements.
- [x] The decoder decision procedure is documented from evidence, not preference.
- [ ] The authoritative decoder decision is recorded after campaign review.

## Out of scope

- Mandatory embedded decoder dependency.
- Broad primitive expansion.
- Publication-grade benchmark campaign.
- Intentional partial-report output before scanner progress and dropped-count
  semantics are implemented and validated.

## Handoff

Patch 042 implements the decoder-gap measurement and decision-gate foundation
without changing runtime facts. Authoritative WSL2 evidence must now be reviewed
and the decoder decision recorded. Sprint 10 expands primitive coverage only
after that decision gate closes.
