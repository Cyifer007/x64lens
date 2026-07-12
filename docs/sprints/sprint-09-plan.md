# Sprint 09 Plan

## Status

Active through Patch 043; Patch 044 is the planned closeout review.

## Sprint goal

Make candidate validity, evidence source, analysis completeness, report identity,
and the decoder decision explicit before adding more primitive families.

## Planned deliverables

- [x] Add a fixed-size analysis-summary record for command identity and bounded
  completion facts.
- [x] Add candidate capacity, truncation, dropped-count knowledge, region
  progress, and analysis-complete facts to successful reports.
- [x] Add top-level report type and command identity.
- [x] Introduce schema `0.2.0` and migration notes.
- [x] Add retained representative final-shape schema `0.1.0` compatibility.
- [x] Preserve `gadgets` and `analyze` JSON parity while distinguishing command
  identity.
- [x] Add a dense evidence side-car keyed by candidate index.
- [x] Distinguish raw, exact-suffix, semantic-exact, and future decoder-backed
  evidence without redefining historical counts.
- [x] Add per-candidate evidence kind and validator identity to JSON.
- [x] Add controlled and selected-system external decoder-gap campaigns.
- [x] Bind campaign evidence to immutable analyzed target snapshots.
- [x] Make result publication transactional across ordinary failures, `SIGINT`,
  and `SIGTERM`.
- [x] Harden objdump parsing, diagnostics, and sequence barriers.
- [x] Record the embedded-decoder decision from authoritative campaign evidence.
- [x] Keep raw scanner output independently measurable.
- [ ] Complete the Sprint 9 architecture, documentation, environment,
  public/private-boundary, configuration, and roadmap closeout review.

## Patch sequence

1. **Patch 040:** report and command identity, complete-analysis summary, schema
   `0.2.0`, retained representative `0.1.0` compatibility, and parity gates.
2. **Patch 041:** candidate evidence side-car, exact/semantic provenance, ABI
   correction, formal schema enforcement, and validation hardening.
3. **Patch 042:** portable public-bundle policy, controlled and selected-system
   decoder-gap measurement, and an explicit decision gate.
4. **Patch 043:** immutable target snapshots, signal-safe transactional result
   publication, external-disassembly parser hardening, archive metadata and
   public-document boundary corrections, and the decoder-free default decision.
5. **Patch 044:** Sprint 9 closeout: architecture and contract audit, project
   context refresh, development-environment and Docker Buildx review,
   configuration review, roadmap reconciliation, and retrospective.

The sequence is intentionally additive. Decoder evidence must remain a side-car;
it may not replace raw scanner facts, exact suffix evidence, semantic-exact
classification, unknowns, or scores.

## Acceptance criteria

- [x] Existing raw, exact, semantic, unknown, and scored counts retain their
  documented meanings.
- [x] Successful reports state whether bounded candidate enumeration completed
  without capacity truncation.
- [x] Schema validators reject internally inconsistent identity, completeness,
  and current provenance state.
- [x] `gadgets` and `analyze` share report facts and one JSON implementation.
- [x] Candidate-arena overflow remains fail-closed with no partial stdout.
- [x] Candidate provenance is additive and does not redefine historical counts.
- [x] The decoder decision is documented from measured evidence.
- [x] The default runtime remains freestanding and decoder-free.
- [x] A future optional decoder is constrained to an evidence adapter/profile.
- [ ] Patch 044 completes the sprint-wide closeout audit and retrospective.

## Recorded decoder decision

The selected-system development campaign found no canonical return terminator
that was absent from x64lens raw discovery in the reviewed target set. It did
show expected byte-oriented candidates that do not begin at canonical
instruction boundaries. Those observations remain visible as validity-unknown
provenance rather than being discarded.

The default analyzer therefore remains dependency-free. A future decoder may be
added only as an optional verification profile when a fixed-corpus campaign
shows a material user-facing validity or semantic-coverage gap and separately
measures license, binary-size, latency, RSS, and hostile-input costs.

## Out of scope

- Mandatory embedded decoder dependency.
- Broad primitive expansion.
- Publication-grade benchmark claims from Sprint 9 smoke evidence.
- Intentional partial-report output before scanner progress and dropped-count
  semantics are implemented and validated.

## Handoff

Patch 044 closes Sprint 9 without introducing a stealth feature tranche. Sprint
10 may expand primitive coverage only through the evidence-aware records,
fixtures, and decoder decision established here.
