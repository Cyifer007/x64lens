# Eighteen-Sprint Roadmap

## Purpose

This document is the canonical roadmap for implementation and research after the validated Sprint 6 `v0.1.0-dev` checkpoint. It replaces the earlier twelve-sprint planning ceiling while preserving completed architecture contracts and metric definitions.

The roadmap separates four kinds of work that must not be collapsed into one sprint:

1. parser and metadata correctness,
2. candidate validity and semantic evidence,
3. reproducible corpus and benchmark work,
4. release and publication preparation.

## Current checkpoint

Sprints 1 through 9 are complete. Sprint 10 is active through the Patch 049 candidate. Sprint 9 established report and command identity, schema `0.2.0`, bounded complete-analysis state, per-candidate provenance, external decoder-gap evidence, immutable campaign inputs, signal-safe publication, portable ZIP metadata policy, and the evidence-based decision to retain a decoder-free one-worker reference profile while measuring candidate-scoped validation and parallel profiles separately.

The Sprint 10 decisions, effect contract, active boundary, and acceptance
gates are documented in [ADR 0032](adr/0032-ordered-multi-pop-foundation.md),
[ADR 0033](adr/0033-exact-register-transfer-effects.md), the
[Primitive Effect Model](design/primitive-effect-model.md), the
[Sprint 10 Plan](sprints/sprint-10-plan.md), and the
[Patch 047 Validation Plan](sprints/sprint-10-patch-047-validation.md),
[ADR 0034](adr/0034-bounded-stack-adjust-and-public-artifact-content-policy.md),
the [Patch 048 Validation Plan](sprints/sprint-10-patch-048-validation.md), and the [Patch 049 Validation Plan](sprints/sprint-10-patch-049-validation.md).

The implemented pipeline is:

```text
ELF64 validation
  -> loader-relevant executable regions
  -> raw return-terminator candidate discovery
  -> exact suffix pattern recognition
  -> conservative semantic classification
  -> heuristic scoring
  -> text and schema-versioned JSON reporting
  -> integrated analyze command
  -> smoke validation and baseline benchmark plumbing
```

The `v0.1.0-dev` tag identifies the Sprint 6 integrated-prototype checkpoint.
Patch 046 is the accepted Sprint 10 entry foundation. Patch 047 introduced exact
register transfer but was rejected as delivered. Patch 048 is the current
corrective stack-adjust/validation-hardening candidate and retains the transfer
foundation; all three are later pre-release development state, not the first
research release. Sprint 8 closed the mitigation-depth tranche with bounded
dynamic-table evidence, RELRO refinement, canary and stripped indicators,
section-label annotations, hostile metadata hardening, byte-safe JSON rendering,
evidence-hygiene gates, automated `readelf` comparison, and optional `checksec`
/ `rabin2 -I` comparison helpers.

## Sprint 7 closeout checkpoint

Sprint 7 established deterministic hostile-input evidence, explicit resource-limit behavior, a mitigation oracle, corrected generated-artifact hygiene, and shared checked arithmetic for table extents and bounded per-entry views. Regression promotion remains a continuing policy.

## Sprint 8 closeout checkpoint

Sprint 8 established mitigation-depth evidence and metadata annotations while preserving program-header runtime authority. Dynamic-table evidence now supports RELRO refinement and canary indicators; section tables support stripped status and optional section labels only as bounded metadata. Patch 039 closes the sprint after comparator helper hardening, benchmark-integrity coverage, Sprint 8 retrospective publication, and Sprint 9 handoff.

## Release gates

| Gate | Target point | Purpose |
|---|---|---|
| Integrated checkpoint | Sprint 6, complete | Demonstrate the end-to-end product path and preserve a known-good development tag. |
| Research preview candidate | End of Sprint 12 | Publish a bounded `v0.1.0-rc1` candidate with parser hardening, mitigation depth, evidence provenance, a reproducible corpus, and high-resolution benchmark tooling. |
| First research release | End of Sprint 18 | Publish `v0.1.0` with completed comparative experiments, case-study evidence, a frozen replication package, and paper-ready claims. |

A release gate is evidence-based. Calendar progress alone does not satisfy it.

## Sprint map

| Sprint | Theme | Primary outcome |
|---|---|---|
| 1 | ELF64 identity | Safe file mapping and `info <file>`. |
| 2 | Loader mapping | Program headers, executable regions, and baseline mitigation facts. |
| 3 | Scanner foundation | Raw candidates, arena storage, smoke benchmarking, and exact suffix patterns. |
| 4 | Semantic classification | Primitive classes, controlled-register coverage, stack deltas, and unknown preservation. |
| 5 | Scoring, JSON, and validation | Heuristic scores, schema `0.1.0`, system smoke tests, baseline harness, and environment hardening. |
| 6 | Integrated checkpoint | `analyze`, composable reporters, repeatable demo, checkpoint tag, and roadmap review. |
| 7 | Hostile-input hardening | Patch 025 establishes deterministic mutation and capacity gates; checked table arithmetic and regression promotion complete the sprint. |
| 8 | Mitigation and metadata depth | Complete: full versus partial RELRO, canary indicators, section labels, stripped indicators, external comparison checks, and closeout hardening. |
| 9 | Candidate provenance and decoder-gap measurement | Complete through Patch 045: identity, completeness, provenance, schema `0.2.0`, hardened comparison evidence, portable release policy, and bounded decoder/parallelism decisions. |
| 10 | Primitive expansion | Active: Patches 046-048 establish ordered two-pop, register-transfer, and stack-adjust effects; Patch 049 adds the first bounded qword base-plus-zero memory read/write family and authenticated public-overlay validation. |
| 11 | Reproducible corpus | Compiler, optimization, hardening, linkage, and target-manifest matrix with hashes and regeneration commands. |
| 12 | High-resolution benchmark infrastructure and preview | Nanosecond-resolution runner, per-child resource capture, pilot campaign, and `v0.1.0-rc1` research preview candidate. |
| 13 | Comparative benchmark campaign | Publication-grade repeated trials, coverage reconciliation, output-normalization analysis, and raw-result freeze. |
| 14 | Mitigation-aware triage model | Evidence-backed defensive interpretation that combines mitigations, primitive coverage, scores, and uncertainty without claiming exploitability. |
| 15 | Automation and schema stabilization | Schema `0.2.x` stabilization, report provenance, optional CI policy modes, and machine-consumer compatibility tests. |
| 16 | Infrastructure case study | Network-facing software case study, analyst workflow evaluation, and operational triage evidence. |
| 17 | Replication and paper freeze | Reproduction package, independent rebuild rehearsal, final figures/tables, and paper claim audit. |
| 18 | First research release | `v0.1.0`, checksummed artifacts, preserved raw evidence, final retrospective, and publication submission package. |

## Required capabilities before the research preview candidate

The `v0.1.0-rc1` gate requires all of the following:

- deterministic malformed-input smoke coverage with no SIGSEGV or SIGBUS,
- regression fixtures for every parser defect discovered,
- explicit candidate-capacity or truncation behavior,
- full versus partial RELRO distinction when evidence is available,
- canary and stripped-status indicators documented as indicators,
- section labels that remain subordinate to program-header mapping authority,
- evidence provenance that distinguishes current raw, exact-suffix, and
  semantic-exact facts, preserves unknown and scored populations separately,
  and reserves decoder-validated facts as optional additive evidence,
- current schema `0.2.0` report identity, bounded completeness, and candidate
  provenance, with explicit migration review for any incompatible future change,
- a reproducible corpus manifest with target hashes and build commands,
- a higher-resolution benchmark runner that avoids zero-valued timing on small binaries,
- documented baseline versions and exact commands,
- a release dry run with checksums and public-documentation validation.

## Required capabilities before the first research release

The `v0.1.0` gate additionally requires:

- repeated benchmark trials under a fixed methodology,
- raw result preservation and generated summaries,
- coverage-definition reconciliation against each baseline tool,
- a frozen schema and validator set for the release,
- a network-facing infrastructure or equivalent operational case study,
- a complete limitations and threats-to-validity section,
- an independently rehearsed build and reproduction path,
- a paper-ready claim-to-evidence matrix,
- release artifacts and SHA-256 checksums.

## Dependency order

The order is intentional:

```text
parser safety
  -> mitigation depth
  -> provenance and validity measurement
  -> primitive expansion
  -> corpus freeze
  -> benchmark infrastructure
  -> benchmark campaign
  -> triage model and case study
  -> release and publication freeze
```

Primitive breadth must not outrun evidence quality. Benchmark scale must not outrun corpus reproducibility. Release work must not outrun schema and claim stability.

## Schema timeline

- Keep schema `0.1.0` through Sprint 8 for compatible, optional mitigation additions.
- Schema `0.2.0` is the current producer contract, introduced in Sprint 9 Patch 040 for report identity and complete-analysis state and extended compatibly with per-candidate provenance in Patch 041.
- Keep `0.2.x` backward-compatible through the preview and benchmark campaign.
- Do not introduce another breaking schema before `v0.1.0` unless a release-blocking correctness issue requires it.

See `docs/design/schema-evolution.md`.

## Decoder decision timeline

The raw scanner remains a bounded candidate prefilter. External decoders and baseline tools remain validators until measured evidence justifies an embedded decoder.

The decision gate occurs after Sprint 9 evidence capture and no later than Sprint 13 coverage reconciliation. An embedded decoder is approved only if:

- a quantified correctness gap affects a research claim or user-facing result,
- the decoder can be isolated behind side-car records,
- raw scanner metrics remain available independently,
- runtime and memory costs can be measured separately,
- dependency and licensing consequences are documented.

## Primitive expansion rule

Every new primitive family requires:

1. a controlled source fixture,
2. disassembly-backed expected facts,
3. an evidence tier,
4. semantic-class documentation,
5. side-effect and clobber behavior,
6. text and JSON parity,
7. regression validation,
8. benchmark metric preservation.

A new exact pattern does not automatically become a semantic primitive. A semantic primitive does not automatically receive a score.

## Refactor-avoidance rules

- Keep file mapping, parsing, scanning, classification, scoring, and reporting separate.
- Add bounded views and side-car records instead of duplicating pointer arithmetic.
- Keep program headers authoritative for runtime mappings.
- Keep section headers and symbols as optional analyst annotations.
- Generate JSON and future outputs from internal facts, never from text scraping.
- Preserve raw-candidate, exact-suffix, semantic-exact, decoder-validated,
  unknown-candidate, and scored metrics separately.
- Preserve smoke evidence separately from publication evidence.
- Make schema changes at explicit gates, not opportunistically inside feature patches.

## Scope controls

Before `v0.1.0`, the project does not require:

- ARM64 support,
- PE or Mach-O parsing,
- exploit or payload generation,
- symbolic execution,
- remote target interaction,
- full JOP, COP, or SROP modeling,
- a mandatory embedded decoder,
- a GUI.

These remain post-release research directions unless measured evidence changes the priority.

## Sprint 7 to Sprint 8 handoff

Patch 026 added the compiler-independent mitigation truth table and command-path malformed consistency gate. Patch 027 corrected the zero-region oracle expectation. Patch 028 added shared checked arithmetic and bounded table helpers while preserving both the Patch 025 hostile-input evidence and the corrected mitigation oracle. Patch 029 closes Sprint 7 and hands Sprint 8 a hardened parser baseline for dynamic-section, symbol, string, and section-label work. Patch 030 implements the first bounded dynamic-section view. Patch 031 preserves that parser seam and adds the no/partial/full RELRO split. Patch 032 uses bounded dynamic-string evidence for the first canary indicator. Patch 033 uses bounded section-header evidence for the first stripped-status indicator and rejects duplicate dynamic string-table singleton entries. Patch 034 uses bounded section-name evidence for optional region and candidate labels. Patch 035 hardens label rendering, overlap ambiguity, and helper state handling. Patch 036 hardens byte-safe JSON, section-label trust, Docker context filtering, benchmark evidence, validator consistency, and temporary-output isolation.


## Sprint 8 priority adjustment

Sprint 8 remains focused on mitigation-depth and metadata accuracy. Patch 030 completes the bounded `PT_DYNAMIC` parser seam, Patch 031 completes the initial RELRO refinement, Patch 032 completes the first evidence-qualified canary indicator, and Patch 033 completes the first stripped-state indicator. Patch 034 completes the first section-label annotation pass, Patch 035 hardens it, and Patch 036 resolves the historical review hardening candidates before Sprint 9. Primitive expansion should wait until these metadata paths preserve malformed-input, capacity, mitigation-oracle, and checked-arithmetic gates.

## Sprint 8 Patch 032 roadmap update

Patch 032 completes the first canary indicator and resolves Patch 031 local review follow-ups for schema strictness, permanent mitigation-matrix coverage, and result-artifact cleanup. Patch 033 completes the first stripped-status indicator and promotes dynamic string-table singleton and scan-cap cases into the oracle. Sprint 8 should continue with comparison helpers unless validation reveals a parser defect.

## Sprint 8 Patch 034 roadmap update

Patch 033 completes stripped-state reporting and promotes dynamic string-table singleton and scan-cap cases into the mitigation oracle. Patch 034 completes section-label annotations while preserving program-header authority. Sprint 8 should pause for historical review before Sprint 9 evidence provenance. Optional comparison helpers remain deferred.


## Sprint 8 Patch 035 roadmap update

Patch 035 closes the first section-label hardening loop by escaping text labels, ignoring non-executable overlap, omitting ambiguous executable overlap, and making label-helper context stack-local. Patch 036 follows the historical review pause and closes byte-safe JSON, label-agreement, Docker context, benchmark-evidence, validator, and temporary-output hardening items before Sprint 9.

## Sprint 8 Patch 036 roadmap update

Patch 036 converts the historical review pause into a hardening patch instead of opening new primitive expansion. It closes immediate evidence and reporting defects while keeping the larger release-gate work in place. Sprint 9 should still begin with provenance, completeness, report identity, and decoder-gap measurement. Sprint 12/13 still own publication-grade benchmarking and cross-tool reconciliation.


## Sprint 9 Patch 040 roadmap update

Patch 040 completes the command-level half of the Sprint 9 schema transition.
Current reports identify the producing command and state candidate capacity,
count, truncation, dropped-count knowledge, executable-region progress, and
  overall completion. A retained representative final-shape schema `0.1.0`
  snapshot remains available through a versioned compatibility path.

The patch deliberately preserves the fail-closed 4097-candidate behavior rather
than introducing a partial-report mode. The next Sprint 9 work is per-candidate
evidence provenance, followed by decoder-gap measurement and the embedded-
decoder decision gate. Primitive expansion remains a Sprint 10 concern.


## Sprint 9 Patch 041 roadmap update

The provenance foundation now has two separate records:

```text
analysis_summary                 command identity and enumeration completeness
candidate_evidence_record[]      per-candidate raw/exact-suffix/semantic-exact provenance
```

This completes the record seam required before decoder-gap measurement. The
next Sprint 9 work should quantify exact-suffix false positives, undercounted
semantic forms, definition differences, and validation cost. No primitive
family should be added merely to improve a count before that reconciliation.


## Sprint 9 Patch 042 roadmap update

Patch 042 implements the measurement boundary required by the decoder decision
timeline. It compares current provenance-bearing x64lens reports with canonical
GNU objdump disassembly on the controlled fixture and selected installed
system binaries, preserves hashes and raw artifacts, and separates boundary,
duplicate/canonicalization, supported-unselected, and unsupported-sequence
observations. The controlled case joins aggregate validation; host-dependent
system evidence remains a separate campaign.

This patch does not introduce decoder-backed facts or change raw, exact,
semantic, unknown, or scored metrics. Sprint 9 closes only after authoritative
campaign evidence is reviewed and the project records one of the permitted
outcomes: defer embedding, retain optional external verification, or approve an
isolated decoder adapter. Sprint 10 primitive expansion remains downstream of
that decision.

## Sprint 9 Patch 043 roadmap update

Patch 043 completes the decoder decision required before primitive expansion.
The core remains a freestanding dependency-free analyzer. A future decoder is an
optional side-car evidence profile, not a replacement scanner or mandatory
runtime dependency. This preserves a measurable low-footprint mode for offline,
incident-response, minimal-container, and CI/CD deployments.

Patch 044 is the corrective campaign and release-boundary hardening boundary.
Patch 045 completes the public architecture, contract, release-boundary,
roadmap, and validation review and publishes the Sprint 9 retrospective.
Feature discoveries are classified for Sprint 10 or later unless they block an
accepted Sprint 9 contract.

## Sprint 9 Patch 044 roadmap update

Patch 044 corrects the evidence and release-boundary defects discovered after
Patch 043 without changing analyzer assembly or schema. It also records the
preferred bounded future architecture: scan first, optionally decode retained
candidate windows, preserve all evidence tiers, and introduce parallelism only
as an independently benchmarked deterministic profile.

Patch 045 subsequently completed the Sprint 9 public closeout and release-readiness review.
Sprint 10 is now the active primitive-expansion tranche. Sprints 12 and 13 retain
candidate-decoder and worker-count ablations so RSS and startup cost are
measured rather than assumed.

## Sprint 9 closeout checkpoint

Patch 045 closed Sprint 9 without changing analyzer assembly, record layouts, CLI behavior, or schema shape. The accepted Sprint 9 boundary is:

- schema `0.2.0` report and command identity;
- explicit complete-analysis and capacity facts;
- candidate-index provenance for raw, exact-suffix, and semantic-exact evidence;
- external decoder-gap measurement with immutable inputs and transactional publication;
- a decoder-free, single-worker reference runtime;
- optional future candidate-scoped validation and parallel profiles, each gated by fixed-corpus measurement;
- portable public-archive and documentation-hygiene enforcement.

Sprint 10 may expand primitive families only through the established evidence, side-effect, fixture, and score boundaries. Decoder integration and in-process parallelism remain ablations for the reproducible corpus and benchmark stages rather than hidden prerequisites for primitive work.

## Sprint 10 Patch 049 roadmap update

Patch 049 implements the first memory-effect seam without changing the raw candidate stride, candidate capacity, schema version, decoder boundary, or one-worker reference profile. A 16-byte side-car represents only exact qword base-plus-zero read/write facts. Broader addressing forms remain future work.

The likely next step is Sprint 10 closeout: review implemented-family coverage and false-positive boundaries, preserve score deferral, and hand the complete primitive fixture set to Sprint 11 corpus construction.
