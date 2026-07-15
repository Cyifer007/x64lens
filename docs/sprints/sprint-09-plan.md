# Sprint 09 Plan

## Status

Closed by Patch 045.

## Sprint goal

Make candidate validity, evidence source, analysis completeness, report
identity, and the decoder decision explicit before adding more primitive
families.

## Delivered work

- [x] Fixed-size analysis-summary record for command identity and bounded
  completion facts.
- [x] Candidate capacity, truncation, dropped-count knowledge, region progress,
  and analysis-complete facts for successful reports.
- [x] Top-level report type and command identity.
- [x] Schema `0.2.0` with migration and compatibility documentation.
- [x] Retained representative final-shape schema `0.1.0` compatibility.
- [x] `gadgets` and `analyze` JSON parity with distinct command identity.
- [x] Dense evidence side-car keyed by candidate index.
- [x] Raw, exact-suffix, semantic-exact, and reserved decoder-backed evidence
  tiers without historical count redefinition.
- [x] Per-candidate evidence kind, validator identity, and matched suffix range.
- [x] Controlled and selected-system external decoder-gap campaigns.
- [x] Immutable target snapshots and complete campaign identity.
- [x] Transactional publication across ordinary failure, `SIGINT`, and
  `SIGTERM`.
- [x] Complete measured-child process-group cleanup.
- [x] Reviewed objdump prefix/return normalization and control-flow barriers.
- [x] Local/central ZIP metadata reconciliation and strict ZIP64 handling.
- [x] Synthetic public-boundary fixtures and root-independent archive policy.
- [x] Decoder-free default, optional candidate-scoped validation direction, and
  measurement gates for future parallel profiles.
- [x] Sprint-wide architecture, contract, documentation, release-boundary,
  metric, schema, and roadmap closeout review.

## Patch sequence

1. **Patch 040:** report and command identity, complete-analysis summary, schema
   `0.2.0`, representative historical compatibility, and parity gates.
2. **Patch 041:** candidate evidence side-car, exact-suffix/semantic-exact
   provenance, ABI correction, formal schema enforcement, and validation
   hardening.
3. **Patch 042:** portable public-bundle policy, decoder-gap measurement, and
   explicit decoder decision gate.
4. **Patch 043:** immutable target snapshots, campaign transaction and parser
   hardening, and the decoder-free default.
5. **Patch 044:** signal-window, child-cleanup, external-parser, ZIP metadata,
   and public-fixture corrections plus bounded acceleration design gates.
6. **Patch 045:** strict closeout correction, defensive deployment profile,
   documentation and release audit, retrospective, and Sprint 10 handoff.

## Acceptance criteria

- [x] Raw, exact-suffix, semantic-exact, unknown, and scored counts retain their
  meanings.
- [x] Successful reports state bounded enumeration completion.
- [x] Validators reject inconsistent identity, completeness, and provenance.
- [x] `gadgets` and `analyze` reuse shared report facts and adapters.
- [x] Capacity overflow remains fail-closed with no partial stdout.
- [x] Candidate provenance remains additive.
- [x] The decoder decision is evidence-based.
- [x] The default runtime remains freestanding, decoder-free, and single-worker.
- [x] Future decoder and parallel profiles have bounded, deterministic,
  reproducible acceptance gates.
- [x] Sprint closeout validation and retrospective are documented.

## Final decoder and acceleration decision

The development campaign demonstrated raw terminator recall for the reviewed
canonical return set, expected unaligned byte observations, and exact-catalog
undercoverage. It did not prove universal recall or justify whole-image decoding.

The core remains dependency-free. A future decoder may validate starts inside
retained candidate windows and write side-car evidence. Target-level parallelism
is available to external orchestration; candidate validation is the preferred
first in-process worker seam. Sprints 12 and 13 measure optional profiles before
any default changes.

## Out of scope retained after closeout

- Mandatory embedded decoder dependency.
- Forced multithreading or an unmeasured worker default.
- Broad primitive expansion.
- Publication-grade claims from development campaign evidence.
- Intentional partial-report output without truthful scanner progress and
  dropped-count semantics.

## Handoff

Sprint 10 expands primitive coverage through evidence-aware records and
controlled fixtures. It must preserve the defensive deployment profile and may
not use decoder or concurrency work to bypass semantic correctness.
