# Sprint 09 Plan

## Status

Active through Patch 044 corrective hardening; Patch 045 is the planned
closeout review.

## Sprint goal

Make candidate validity, evidence source, analysis completeness, report
identity, and the decoder decision explicit before adding more primitive
families.

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
  and `SIGTERM`, including the post-rename delivery window.
- [x] Kill and reap measured child process groups on timeout or interruption.
- [x] Normalize reviewed objdump prefix/return forms and control-flow barriers.
- [x] Reconcile ZIP local and central metadata and validate ZIP64 semantics.
- [x] Remove real transfer-artifact basenames from public negative fixtures.
- [x] Record the decoder-free default plus candidate-scoped optional decoder
  and evidence-gated parallelism direction.
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
4. **Patch 043:** immutable target snapshots, initial signal-aware result
   publication, external-disassembly parser hardening, and the decoder-free
   default decision.
5. **Patch 044:** corrective campaign and release-boundary hardening for signal
   windows, measured-child cleanup, objdump normalization, ZIP local/central
   reconciliation, ZIP64 semantics, public fixtures, and bounded acceleration
   design gates.
6. **Patch 045:** Sprint 9 closeout: architecture and contract audit, 40-file
   project-context refresh, development and Docker Buildx review, configuration
   and integration review, roadmap reconciliation, retrospective, and Sprint 10
   entry decision.

The sequence is intentionally additive. Decoder evidence remains a side-car and
may not replace raw scanner facts, exact suffix evidence, semantic-exact
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
- [x] The default runtime remains freestanding, single-worker, and decoder-free.
- [x] A future decoder is candidate-scoped and optional.
- [x] Any future parallel profile has deterministic merge, bounded global
  capacity, and measured RSS/latency gates.
- [ ] Patch 045 completes the sprint-wide closeout audit and retrospective.

## Recorded decoder and acceleration decision

The selected-system development campaign found no canonical return terminator
that was absent from x64lens raw discovery in the reviewed target set. It did
show expected byte-oriented candidates that do not begin at canonical
instruction boundaries and canonical return-ending sequences outside the
current exact catalog.

The default analyzer therefore remains dependency-free. A future decoder may
validate possible starts only inside retained candidate windows and write
side-car facts. This candidate-scoped design can reduce validity uncertainty
and expand semantic coverage without forcing whole-image decoding on every
invocation.

Multithreading is not forced in Sprint 9. Candidate validation is the preferred
first parallel seam; executable-region or chunk scanning requires overlap,
deduplication, global capacity, and deterministic merge. Sprint 12 and Sprint
13 will measure these profiles against one-worker operation before any default
changes.

## Out of scope

- Mandatory embedded decoder dependency.
- Forced multithreading or an unmeasured `--jobs` default.
- Broad primitive expansion.
- Publication-grade benchmark claims from Sprint 9 smoke evidence.
- Intentional partial-report output before scanner progress and dropped-count
  semantics are implemented and validated.

## Handoff

Patch 045 closes Sprint 9 without introducing a stealth feature tranche. Sprint
10 may expand primitive coverage only through the evidence-aware records,
fixtures, and bounded decoder/parallelism gates established here.
