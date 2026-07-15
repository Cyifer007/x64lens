# Research Release Plan

## Purpose

This plan defines the evidence and artifact gates for moving from the current `v0.1.0-dev` checkpoint to a research preview candidate and then to the first public research release.

## Release sequence

| Milestone | Planned version | Evidence level |
|---|---|---|
| Integrated development checkpoint | `v0.1.0-dev` | Functional pipeline, controlled fixture validation, system smoke testing, and development benchmark plumbing. |
| Research preview candidate | `v0.1.0-rc1` | Hardened parser and mitigation paths, provenance-aware output, reproducible corpus, high-resolution benchmark runner, and pilot results. |
| First research release | `v0.1.0` | Fixed comparative campaign, case study, replication package, claim audit, checksummed artifacts, and publication-ready documentation. |

## Current gate progress

Patch 025 established deterministic hostile-input and candidate-capacity evidence, Patch 028 added shared checked table arithmetic, and Patch 029 closed Sprint 7. Patches 030 through 039 completed Sprint 8 mitigation depth and evidence-hygiene gates. Patches 040 through 045 complete Sprint 9 with schema `0.2.0`, report and command identity, complete-analysis state, per-candidate provenance, compatibility fixtures, portable decoder-gap evidence, immutable and transaction-safe campaign artifacts, a decoder-free reference runtime, and public-release boundary hardening. Patch 046 begins Sprint 10 with ordered two-pop semantic evidence and explicit effect fields. Reproducible corpus work and high-resolution benchmarking remain open in Sprints 11 and 12.

## `v0.1.0-rc1` gate

The preview candidate must include:

- native and Docker validation,
- hostile-input mutation smoke results,
- full/partial/no RELRO reporting when evidence exists,
- canary and stripped indicators with confidence wording,
- explicit candidate capacity and truncation state,
- current schema `0.2.0` identity, completeness, and provenance, or an explicitly
  reviewed successor,
- a reviewed decoder-gap campaign and documented embedded-decoder decision,
- target and tool hashes in benchmark metadata,
- a reproducible corpus manifest,
- one pilot comparison run across all supported baselines,
- source archive, Linux x86_64 binary, checksums, version output, and smoke benchmark artifact.
- source and release ZIPs that pass the portable bundle policy.

The preview candidate may still carry known semantic-coverage limitations. Those limitations must be explicit and machine-readable where practical.

## `v0.1.0` gate

The first research release must additionally include:

- fixed corpus and baseline versions,
- publication-grade repeated trials,
- raw TSV or equivalent per-run evidence,
- generated summary tables and figures,
- candidate-definition reconciliation notes,
- a network-facing infrastructure or equivalent operational case study,
- final schema validators,
- final release notes,
- an independent reproduction rehearsal,
- a complete threats-to-validity section,
- a claim-to-evidence matrix.

## Claim-to-evidence matrix

Every release-facing claim should map to one or more artifacts:

| Claim category | Required evidence |
|---|---|
| Runtime or memory | Raw per-run rows, environment metadata, tool versions, target hashes, and summary statistics. |
| Gadget or primitive coverage | Explicit definitions, baseline commands, controlled fixtures, and reconciliation notes. |
| Parser robustness | Mutation corpus, signal/exit-code results, timeouts, and regression fixtures. |
| Mitigation accuracy | Controlled hardening fixtures and comparison against `readelf`, `checksec`, or equivalent tools. |
| Defensive usefulness | Defined triage task, representative reports, analyst criteria, and limitations. |
| Reproducibility | Public commands, source/build provenance, checksums, and an independent rehearsal log. |

## Artifact layout

Planned release artifacts:

```text
release/
  x64lens-<version>-linux-x86_64
  x64lens-<version>-source.zip
  x64lens-<version>-checksums.sha256
  x64lens-<version>-version.txt
  x64lens-<version>-benchmark-smoke.tsv
  x64lens-<version>-benchmark-smoke.meta
  x64lens-<version>-reproduction.md
```

Publication artifacts remain under `paper/` and benchmark evidence remains under `benchmarks/` until a release packaging step copies approved files into a release staging directory.

## Freeze rules

- Corpus membership freezes before the publication benchmark campaign.
- Baseline tool versions freeze before repeated trials.
- Schema shape freezes before the final campaign unless a correctness defect requires a documented restart.
- Generated tables and figures must come from preserved raw results.
- Manual edits to benchmark summaries are not release evidence.
- Release tags point to clean, validated commits.

## Tag policy

- `v0.1.0-dev` identifies the Sprint 6 integrated checkpoint.
- `v0.1.0-rc1` is the first publishable preview tag after the Sprint 12 gate.
- `v0.1.0` is the first research release after the Sprint 18 gate.

A normal branch push does not publish tags. Release tags should be pushed explicitly only after the release checklist passes.

## Sprint 8 mitigation evidence gate

After Sprint 8 Patch 034, the mitigation oracle contains 24 valid cases, 14 malformed mitigation-matrix cases, and one unsupported fail-closed case, including bounded dynamic-table evidence, full RELRO evidence combinations, canary-present and canary-absent indicators, stripped and not-stripped indicators, section-label fixture checks, direct gadgets JSON validation, duplicate dynamic-table rejection, duplicate dynamic-string singleton rejection, invalid dynamic string-table rejection, and string-table scan-cap rejection. This evidence is development validation, not a publication comparison dataset, but it is required for the research preview gate.


## Sprint 7 gate result

Sprint 7 satisfies the parser-safety foundation needed before the research preview candidate. The accepted baseline includes deterministic malformed-input coverage, candidate-capacity failure behavior, a deterministic mitigation oracle, and shared checked parser arithmetic. Sprint 8 must build mitigation-depth evidence on top of that baseline rather than replacing it.

## Sprint 8 Patch 032 release-gate update

The research preview gate now includes evidence-qualified canary indicators and the stricter current JSON schema. Generated validation artifacts remain ignored; use `make clean-results` before broad release-package review or when stale local results could confuse text searches.

## Sprint 8 Patch 033 release-gate update

Patch 033 closes the first stripped-status indicator gate while preserving schema `0.1.0`. Release evidence may claim deterministic section-table metadata detection for represented cases, but must not claim complete symbol recovery or runtime hardening proof.

## Sprint 8 Patch 034 release-gate update

Patch 034 adds section-label annotations while preserving schema `0.1.0`. Release evidence may claim deterministic section-label annotation for represented safe section-name cases, but must not claim complete section recovery or runtime mapping authority from section headers.

## Patch 036 historical-review hardening note

Patch 036 closes several review-found blockers for trustworthy evidence: byte-safe JSON rendering, `.env` Docker context exclusion, benchmark smoke sanity validation, JSON coverage-register consistency, and temporary-file isolation. These fixes improve release hygiene, but they do not replace the Sprint 9 schema/provenance transition or the Sprint 12/13 publication benchmark campaign.


## Patch 037 comparator milestone

Sprint 8 closes the initial metadata/mitigation comparator gap with automated
`readelf` comparison and optional `checksec`/`rabin2 -I` capture. These are
necessary reviewer-confidence gates, not sufficient publication evidence. The
research preview still requires schema `0.2.0` provenance and the later frozen
benchmark corpus.

## Sprint 8 closeout gate

Sprint 8 is complete after Patch 039. Patch 040 adds report and command identity,
complete-analysis state, and schema `0.2.0`; Patch 041 adds current per-candidate
provenance; Patch 042 adds portable bundle enforcement and external decoder-gap
evidence with target/tool hashes. The research preview is still not ready.
Patch 043 records the reviewed decoder decision; Patch 045 subsequently verified
that decision and its supporting evidence. Sprint 11 and Sprint 12 still own corpus and benchmark freeze work.


## Sprint 9 Patch 040 release-gate update

Patch 040 satisfies the command-level report identity and successful-analysis
completeness portion of the preview gate. Current schema `0.2.0` reports state
candidate capacity/count, truncation, dropped-count knowledge, region progress,
and command identity. A retained representative final-shape schema `0.1.0`
snapshot remains available through a versioned compatibility path.

This is not the full provenance gate. Before `v0.1.0-rc1`, the project still
requires target and tool hashes where required, decoder-gap measurement, a
reproducible corpus, and the high-resolution pilot
benchmark path. Candidate-capacity overflow remains a failed command with no
partial report and must remain represented as a failure row in any measurement
harness.


## Sprint 9 Patch 041 release-gate update

The preview path now includes a dense candidate evidence side-car and current
JSON provenance requirements. Patch 040 schema `0.2.0` reports remain readable,
but preview candidates must satisfy current-producer provenance validation,
formal Draft 2020-12 validation, root-independent bundle hygiene, and benchmark
identity stratification.


## Sprint 9 Patch 042 release-gate update

Public source and patch ZIPs must pass the root-independent metadata-only bundle
policy. The policy rejects unsafe paths, private/local state, environment and
secret material, generated outputs, symlinks, case collisions, and nested
archives without extracting the bundle.

The decoder-gap campaign satisfies the measurement-surface portion of the
Sprint 9 gate by preserving analyzer, validator, objdump, and target identity;
SHA-256 hashes; exact commands; raw reports and disassembly; smoke timing/RSS;
and categorized boundary/canonicalization facts. It does not itself authorize a
runtime decoder. The preview gate requires a reviewed decoder decision plus the
later reproducible corpus and high-resolution pilot campaign.

## Sprint 9 Patch 043 release-gate update

Research-preview evidence must identify immutable target bytes actually analyzed,
not only a mutable source pathname. Decoder-gap publication must preserve one
complete recognized result across ordinary failure and process interruption.
Public archives must pass raw/effective-name, extra-metadata, cross-platform
path, nested-container, duplicate, case-collision, encryption, comment, and
special-file policy checks before extraction.

The default release binary remains decoder-free. A future decoder-enabled
artifact would be a separate profile with its own tool identity, dependency and
license record, malformed-input gate, and runtime/RSS benchmark stratum.

## Sprint 9 gate status

The provenance and schema portions of the preview gate are complete. Sprint 9 does not satisfy the full `v0.1.0-rc1` gate by itself: the fixed preview corpus, higher-resolution benchmark runner, pilot baseline campaign, preview artifact rehearsal, and release-tag decision remain later work.

The default release profile remains dependency-free and decoder-free. Any optional decoder-enabled or parallel profile must have a distinct build/runtime identity, independent benchmark rows, explicit dependency and licensing records, and equivalent malformed-input, capacity, completeness, and output-contract validation.
