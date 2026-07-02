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

Patch 025 established the first deterministic hostile-input and candidate-capacity evidence required by the preview gate. Patch 028 added shared checked table arithmetic and table-end overflow coverage. Patch 029 closes Sprint 7. Patch 030 adds bounded dynamic-table evidence for the first Sprint 8 mitigation-depth step. Patch 031 uses that evidence for no, partial, and full RELRO reporting. Patch 032 adds the first evidence-qualified canary indicator and schema hardening. Exercised regression promotion, stripped-state indicators, provenance-aware schema fields, reproducible corpus work, and high-resolution benchmarking remain open.

## `v0.1.0-rc1` gate

The preview candidate must include:

- native and Docker validation,
- hostile-input mutation smoke results,
- full/partial/no RELRO reporting when evidence exists,
- canary and stripped indicators with confidence wording,
- explicit candidate capacity and truncation state,
- schema `0.2.0` or later if provenance fields are introduced,
- target and tool hashes in benchmark metadata,
- a reproducible corpus manifest,
- one pilot comparison run across all supported baselines,
- source archive, Linux x86_64 binary, checksums, version output, and smoke benchmark artifact.

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

- `v0.1.0-dev` remains the local integrated checkpoint tag.
- `v0.1.0-rc1` is the first publishable preview tag after the Sprint 12 gate.
- `v0.1.0` is the first research release after the Sprint 18 gate.

A normal branch push does not publish tags. Release tags should be pushed explicitly only after the release checklist passes.

## Sprint 8 mitigation evidence gate

After Sprint 8 Patch 032, the mitigation oracle contains 20 valid cases and 12 malformed mitigation-matrix cases, including bounded dynamic-table evidence, full RELRO evidence combinations, canary-present and canary-absent indicators, direct gadgets JSON validation, duplicate dynamic-table rejection, and invalid dynamic string-table rejection. This evidence is development validation, not a publication comparison dataset, but it is required for the research preview gate.


## Sprint 7 gate result

Sprint 7 satisfies the parser-safety foundation needed before the research preview candidate. The accepted baseline includes deterministic malformed-input coverage, candidate-capacity failure behavior, a deterministic mitigation oracle, and shared checked parser arithmetic. Sprint 8 must build mitigation-depth evidence on top of that baseline rather than replacing it.

## Sprint 8 Patch 032 release-gate update

The research preview gate now includes evidence-qualified canary indicators and the stricter current JSON schema. Generated validation artifacts remain ignored; use `make clean-results` before broad release-package review or when stale local results could confuse text searches.
