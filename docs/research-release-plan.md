# Research Release Plan

## Purpose

This plan defines the evidence and artifact gates for moving from the current `v0.1.0-dev` checkpoint to a research preview candidate and then to the first public research release.

## Release sequence

| Milestone | Planned version | Target sprint | Evidence level |
|---|---|---:|---|
| Integrated development checkpoint | `v0.1.0-dev` | 6, complete | Functional pipeline, controlled fixtures, system smoke, and development benchmark plumbing. |
| Diagnostic measurement checkpoint | none | 11 | Provisional corpus, high-resolution runner, task definitions, and an engineering gap register; development evidence only. |
| Campaign freeze | none | 15 | Frozen corpus, schema/extractor, runner, baselines, commands, task definitions, and environment strata. |
| Research preview candidate | `v0.1.0-rc1` | 16 | Frozen pilot campaign, reproducible preview artifacts, and explicit remaining limitations. |
| Publication campaign | none | 17 | Repeated trials, coverage reconciliation, raw-row freeze, and generated summaries. |
| First research release | `v0.1.0` | 22 | Triage, automation, case study, replication rehearsal, claim audit, checksummed artifacts, and publication-ready documentation. |

## Current gate progress

Patch 025 established deterministic hostile-input and candidate-capacity
evidence, Patch 028 added shared checked table arithmetic, and Patch 029 closed
Sprint 7. Patches 030 through 039 completed Sprint 8 mitigation depth and
evidence-hygiene gates. Patches 040 through 045 complete Sprint 9 with schema
`0.2.0`, report and command identity, complete-analysis state, per-candidate
provenance, compatibility fixtures, portable decoder-gap evidence, immutable
and transaction-safe campaign artifacts, a decoder-free reference runtime, and
public-release boundary hardening. Patches 046 through 049 establish ordered
multi-pop, register-transfer, stack-adjust, and bounded memory families. Patch
050 completes their coarse effects, Patch 051 adds architectural effects and two
reviewed scores, and Patch 052 corrects the resulting effect and validation
findings. Patch 053 establishes the canonical twenty-two-sprint sequence, and
Patch 054 closes Sprint 10 and activates Sprint 11 diagnostic measurement.
Patches 055 and 056 implement the high-resolution runner, truthful task
authority, and first 24-target source-reproducible provisional corpus. Baseline
adapters, summaries, corpus-backed rows, and the gap register remain diagnostic
work. Loader, mitigation, semantic, and optional-profile decisions occupy
Sprints 12 through 14. The campaign freezes in Sprint 15, the preview pilot runs
in Sprint 16, and the publication campaign runs in Sprint 17.

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

- Diagnostic corpus membership and method may change through Sprint 14, but every diagnostic run keeps a distinct identity.
- Corpus membership, baseline versions, commands, schema/extractor, task definitions, and runner freeze in Sprint 15.
- A correctness or method change after Sprint 15 creates a new campaign identifier or requires a complete rerun of affected conditions.
- Generated tables and figures must come from preserved raw results.
- Manual edits to benchmark summaries are not release evidence.
- Release tags point to clean, validated commits.

## Tag policy

- `v0.1.0-dev` identifies the Sprint 6 integrated checkpoint.
- `v0.1.0-rc1` is the first publishable preview tag after the Sprint 16 gate.
- `v0.1.0` is the first research release after the Sprint 22 gate.

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

Patch 036 closes several review-found blockers for trustworthy evidence:
byte-safe JSON rendering, `.env` Docker context exclusion, benchmark smoke
sanity validation, JSON coverage-register consistency, and temporary-file
isolation. These fixes improve release hygiene, but they do not replace the
Sprint 9 schema/provenance transition or, under the current roadmap, the Sprint
11 diagnostic foundation and Sprint 15-17 confirmatory gates.


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
Patch 043 records the reviewed decoder decision; Patch 045 subsequently
verified that decision and its supporting evidence. At the Sprint 8 closeout
boundary, the then-current roadmap assigned corpus and benchmark-freeze work to
Sprints 11 and 12; the current roadmap assigns diagnostic work to Sprint 11 and
campaign freeze to Sprint 15.


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

## Sprint 10 Patch 049 release-gate update

Patch 049 adds a release-gate requirement for authenticated final-file public overlays. The outer SHA-256, ZIP metadata, bounded text policy, internal manifest, declared deletions, and exact member set must agree. Generated fixture executables must remain untracked and excluded from public source archives.

Memory-effect reports remain schema `0.2.0` semantic-exact output with decoder validity unknown and no score assignment.


## Sprint 10 Patch 050 release-gate update

The preview path now requires fail-fast specialty recipes plus the maintained
family coverage and effect-consistency gates. Patch 051 calibrates two score
entries; Patch 053 assigns PIE-versus-DSO semantics, CET/IBT/SHSTK property
evidence, overlapping executable-segment count semantics, and remaining
score-policy questions to explicit pre-freeze gates before Sprint 15 freezes the
confirmatory campaign.


## Sprint 10 Patch 052 corrective update

Patch 052 corrects the Patch 051 effect and gate findings without expanding the
primitive catalog. Full-width syscall descriptors, the zero-immediate return
boundary, contracted text separators, canonical memory side-car reconciliation,
numeric score-policy mutation gates, and strict-lint availability are permanent
validation surfaces. Patch 053 remains the architecture/capability reassessment;
Patch 054 remains Sprint 10 closeout.


## Sprint 10 Patch 053 roadmap update

Patch 053 separates diagnostic measurement from confirmatory measurement and expands the canonical roadmap to twenty-two sprints. Sprint 11 builds a provisional corpus and high-resolution runner so evidence can redirect development. Sprints 12 through 14 resolve loader/mitigation precision, semantic capability, and optional decoder/concurrency decisions. Sprint 15 freezes the campaign; Sprints 16 and 17 run the preview and publication campaigns; Sprints 18 through 22 complete triage, automation, case study, replication, and release.

Diagnostic results may invalidate or narrow the project hypotheses, but they are not merged into the frozen campaign. The release-facing benchmark and capability gates are maintained in [`design/benchmark-and-capability-stage-gates.md`](design/benchmark-and-capability-stage-gates.md).

## Sprint 10 Patch 054 release-gate update

Sprint 10 is closed after Patch 054. Sprint 11 diagnostic artifacts remain
mutable development evidence and cannot satisfy the preview or publication
campaign gates. The release path remains Sprint 15 freeze, Sprint 16 preview,
Sprint 17 publication campaign, and Sprint 22 first research release. A release
checksum inventory is valid only when every listed co-located artifact,
including any package manifest, is present and verifies independently of the
caller's working directory.


## Sprint 11 Patch 055 release-boundary update

Patch 055 diagnostic campaign trees are development evidence only. Hash-bound
write-sealed execution inputs, precise timing, failure retention, final artifact
reconciliation, and transactional publication improve evidence integrity but
do not satisfy the preview corpus, baseline, freeze, or repeated-trial gates.
The first controlled reference campaign cannot be relabeled as preview or
publication evidence.

## Sprint 11 Patch 056 release-gate update

Patch 056 supplies the first source-, license-, command-, tool-, environment-,
and output-authenticated provisional corpus. It advances the diagnostic
measurement checkpoint but does not satisfy the preview corpus gate. The
24-target matrix remains ignored, mutable, and explicitly
`publication_eligible:false`.

Before `v0.1.0-rc1`, Sprint 15 must replace or formally retain corpus membership
under frozen toolchain, license, task, and environment authorities. Any target
promoted from this provisional corpus must be reauthenticated and incorporated
under the frozen campaign identifier.

## Sprint 11 Patch 057 release-gate update

The preview path now requires kernel-enforced non-executable target input
objects for the diagnostic runner, exact corpus workspace and member closure,
verified staging cleanup, and specification-derived corpus removal. A mode-only
target claim, ignored cleanup failure, or checksummed undeclared compiler member
cannot satisfy the preview evidence gate. Patch 057 remains development
infrastructure and supplies no release-facing comparative result.
