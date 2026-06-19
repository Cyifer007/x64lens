# Twelve-Sprint Roadmap

## Purpose

The original semester plan was six sprints. Current progress supports an expanded twelve-sprint arc if velocity remains high. This roadmap preserves the architecture direction without requiring premature refactors or unsupported claims.

## Guiding rule

Each sprint must produce one bounded, testable improvement. Do not implement features merely because they are interesting. Every feature must map to a sprint goal, research question, benchmark method, enterprise adoption need, or architecture seam.

## Sprint map

| Sprint | Theme | Main outcome |
| ------ | ----- | ------------ |
| 1 | ELF64 identity | Safe file mapping and `info <file>` |
| 2 | Loader mapping | Program headers, executable regions, baseline mitigations |
| 3 | Scanner foundation | Raw candidates, arena storage, exact suffix patterns |
| 4 | Semantic classification | Primitive classes, register bitmaps, stack deltas, semantic summary counts |
| 5 | Scoring and JSON | Initial score model and schema-versioned gadget reports |
| 6 | Semester checkpoint | Demo path, documentation, benchmark seed, paper scaffold |
| 7 | Mitigation hardening | Full RELRO, canary indicators, section labels, external comparison helpers |
| 8 | Primitive expansion | Multi-pop, register-transfer, limited memory templates |
| 9 | Compiler/hardening corpus | Build matrix and corpus manifest |
| 10 | Research benchmarks | Repeated baseline comparisons and summary tables |
| 11 | Integrated analysis hardening | Refined `analyze` report, richer mitigation context, and release-ready JSON parity |
| 12 | Publication/release | IEEE paper draft, release artifacts, reproduction package |

## Architecture checkpoints

### After Sprint 4 Patch 015

Validated. The pipeline now reaches the first semantic layer:

```text
ELF parser -> PHDR analyzer -> executable regions -> scanner -> exact pattern matcher -> semantic classifier
```

### After Sprint 6

The repository should support the first complete research narrative:

```text
binary -> facts -> primitives -> scores -> text/JSON reports -> benchmark evidence
```

### After Sprint 12

The repository should support repeatable review:

```text
source + corpus + scripts + raw results + paper draft + release artifacts
```

## Refactor-avoidance principles

- Add side-car records rather than overloading existing records.
- Keep pattern matching separate from semantic classification.
- Keep scoring separate from classification.
- Keep reporting separate from analysis decisions.
- Keep JSON generation from internal records, not from text output.
- Keep program headers authoritative for runtime mappings.
- Treat section headers as labels and analyst context.
- Keep benchmark scripts reproducible and raw-result preserving.

## Long-arc research direction

The long arc remains:

1. prove safe binary parsing and executable-region mapping,
2. measure raw scanner performance,
3. classify semantic primitive coverage,
4. connect primitive coverage to mitigation context,
5. compare against established tools,
6. evaluate hardening profiles and network-facing infrastructure binaries,
7. prepare the work for publication and later dissertation-scale expansion.

## Reviewer-driven refinements

Patch 14 adds reviewer-facing planning without changing the core twelve-sprint direction.

| Sprint | Added planning emphasis |
|---|---|
| Sprint 4 | Conservative semantic classification, unknown candidates preserved, no overclassification. |
| Sprint 5 | JSON limitations, explicit unknown stack-delta representation, classifier fixture hardening, and separate raw/exact/semantic/scored counts. |
| Sprint 6 | Public checkpoint includes NASM rationale and pattern-scanner limitations. |
| Sprint 7 | Parser safety hardening, malformed-input mutation smoke, full RELRO and canary indicators. |
| Sprint 8 | Pattern expansion with false-positive tracking. |
| Sprint 9 | Compiler and hardening matrix for controlled corpus evidence. |
| Sprint 10 | Repeated baseline comparisons against ROPgadget, Ropper, ropr, and selected metadata tools. |
| Sprint 11 | Integrated analysis while preserving limitations and metric separation. |
| Sprint 12 | IEEE paper, reproduction package, raw results, release artifacts, and reviewer response posture. |

## Do-not-refactor-yet list

Do not rewrite in Rust, C, or Go before the assembly-first research question is measured. Do not add ARM64, PE, or Mach-O before the ELF64 x86_64 pipeline is research-grade. Do not embed a full decoder before external comparison data shows that exact-pattern limitations materially affect the paper claims.


## Sprint 5 Patch 017 checkpoint

Patch 017 adds the first scoring model and initial `gadgets --format json` output while preserving scanner, pattern, classifier, scoring, and reporting boundaries.

## Sprint 5 validation-hardening checkpoint

Patch 018 adds a validation-hardening layer inside Sprint 5. This does not change the twelve-sprint direction. It reduces downstream refactor and publication risk by making JSON, scoring, system-binary smoke testing, Docker availability, and patch bundle hygiene repeatable before deeper benchmark and mitigation work begins.


## Sprint 5 Patch 019 checkpoint

Patch 019 advances Sprint 5 from scanner-only smoke measurement to baseline comparison smoke measurement. This does not complete the research benchmark sprint. It creates the reproducible capture path needed before Sprint 10 publication-grade repeated comparisons.


## Sprint 5 Patch 020 update

Patch 020 adds development-environment dependency checks, Ubuntu onboarding instructions, optional baseline-tool installation guidance, and broader default system-binary coverage for the baseline smoke harness.


## Sprint 5 closeout

Sprint 5 completed the first scoring and JSON layer, validation hardening, baseline smoke benchmarking, onboarding, dependency checks, Docker parity hardening, and optional baseline installation guidance. Sprint 6 should now act as a checkpoint and integration sprint rather than a large refactor.


## Sprint 6 Patch 022 adjustment

The integrated `analyze` command moved earlier than the original long-roadmap placement because Sprint 5 delivered scoring, JSON output, validation hardening, and baseline comparison plumbing ahead of schedule. The earlier command is intentionally a checkpoint integration, not a claim that all mitigation hardening or full decoding work is complete.

This preserves the later Sprint 7 through Sprint 12 arc:

- Sprint 7 hardens mitigation and parser safety facts used by `analyze`.
- Sprint 8 expands primitive templates.
- Sprint 9 broadens compiler and hardening corpus coverage.
- Sprint 10 scales benchmark methodology.
- Sprint 11 polishes `analyze` into a stronger integrated report.
- Sprint 12 prepares release and publication artifacts.
