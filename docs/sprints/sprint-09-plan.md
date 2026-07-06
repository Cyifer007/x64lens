# Sprint 09 Plan

## Status

Next.

## Sprint goal

Make candidate validity, evidence source, analysis completeness, and report identity explicit before adding more primitive families.

## Planned deliverables

- [ ] Add an evidence side-car record keyed by candidate index.
- [ ] Distinguish raw candidates, exact suffix observations, semantic-exact classifications, and future decoder-validated facts.
- [ ] Add candidate capacity, truncation, dropped-count when known, and analysis-complete facts.
- [ ] Add per-candidate evidence kind and validator identity to JSON.
- [ ] Add a top-level report type or command identity.
- [ ] Introduce schema `0.2.0` and migration notes.
- [ ] Add compatibility validation for schema `0.1.0` historical fixtures where practical.
- [ ] Measure exact-suffix false-positive and undercount risk on controlled and selected system binaries.
- [ ] Define the embedded-decoder decision gate from measured gaps.
- [ ] Keep raw scanner output independently measurable.

## Acceptance criteria

- [ ] Existing raw, exact, semantic, unknown, and scored counts retain their documented meanings.
- [ ] New decoder-validity metrics are additive, not replacements.
- [ ] Reports state whether analysis completed without capacity truncation.
- [ ] Schema validators reject internally inconsistent provenance or completeness state.
- [ ] `gadgets` and `analyze` maintain JSON parity.
- [ ] The decoder decision is documented from evidence, not preference.

## Out of scope

- Mandatory embedded decoder dependency.
- Broad primitive expansion.
- Publication-grade benchmark campaign.

## Handoff

Sprint 10 expands primitive coverage only through evidence-aware records and fixtures established here.
