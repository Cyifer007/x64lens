# Eighteen-Sprint Roadmap

## Purpose

This document is the canonical roadmap for implementation and research after the validated Sprint 6 `v0.1.0-dev` checkpoint. It replaces the earlier twelve-sprint planning ceiling while preserving completed architecture contracts and metric definitions.

The roadmap separates four kinds of work that must not be collapsed into one sprint:

1. parser and metadata correctness,
2. candidate validity and semantic evidence,
3. reproducible corpus and benchmark work,
4. release and publication preparation.

## Current checkpoint

Sprints 1 through 7 are validated through the Sprint 7 closeout checkpoint. Sprint 8 is the next implementation tranche and focuses on mitigation and metadata depth.

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

The current checkpoint is tagged locally as `v0.1.0-dev`. It is a functional integrated prototype, not the first research release. Sprint 8 Patch 030 begins post-checkpoint mitigation-depth work with bounded dynamic-table evidence.

## Sprint 7 closeout checkpoint

Sprint 7 established deterministic hostile-input evidence, explicit resource-limit behavior, a mitigation oracle, corrected generated-artifact hygiene, and shared checked arithmetic for table extents and bounded per-entry views. Regression promotion remains a continuing policy, but it no longer blocks the Sprint 8 handoff.

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
| 8 | Mitigation and metadata depth | Full versus partial RELRO, canary indicators, section labels, stripped indicators, and external comparison checks. |
| 9 | Candidate provenance and decoder-gap measurement | Evidence side-car model, truncation reporting, validity tiers, and measured decoder decision gate. |
| 10 | Primitive expansion | Multi-pop, register-transfer, and narrowly justified memory primitives with side-effect facts and fixture coverage. |
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
- evidence provenance that distinguishes raw, exact-suffix, semantic, and decoder-validated facts,
- schema evolution from `0.1.0` when provenance or truncation fields materially change report meaning,
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
- Introduce schema `0.2.0` in Sprint 9 when evidence provenance, truncation state, or report-type identity becomes part of the machine-readable contract.
- Keep `0.2.x` backward-compatible through the preview and benchmark campaign.
- Do not introduce another breaking schema before `v0.1.0` unless a release-blocking correctness issue requires it.

See `docs/design/schema-evolution.md`.

## Decoder decision timeline

The raw scanner remains a fast prefilter. External decoders and baseline tools remain validators until measured evidence justifies an embedded decoder.

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
- Preserve raw, exact, semantic, validated, unknown, and scored metrics separately.
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

Patch 026 added the compiler-independent mitigation truth table and command-path malformed consistency gate. Patch 027 corrected the zero-region oracle expectation. Patch 028 added shared checked arithmetic and bounded table helpers while preserving both the Patch 025 hostile-input evidence and the corrected mitigation oracle. Patch 029 closes Sprint 7 and hands Sprint 8 a hardened parser baseline for dynamic-section, symbol, string, and section-label work. Patch 030 implements the first bounded dynamic-section view and should be preserved before RELRO refinement begins.


## Sprint 8 priority adjustment

Sprint 8 remains focused on mitigation-depth and metadata accuracy. Patch 030 completes the bounded `PT_DYNAMIC` parser seam. The next order is RELRO refinement, evidence-qualified canary indicators, and section or stripped-status annotations. Primitive expansion should wait until these metadata paths preserve malformed-input, capacity, mitigation-oracle, and checked-arithmetic gates.
