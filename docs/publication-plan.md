# Publication Plan

## Candidate title

x64lens: An Assembly-First Semantic Gadget and Mitigation-Aware Analyzer for ELF64 x86_64 Binaries

## Paper shape

The initial target is an IEEE-style paper with a bounded systems-security contribution and a public replication package.

Planned sections:

1. Introduction.
2. Related work.
3. Design and implementation.
4. Safety and evidence model.
5. Evaluation methodology.
6. Results.
7. Defensive triage case study.
8. Discussion and threats to validity.
9. Future work.
10. Conclusion.

## Core contribution

The intended contribution is not simply that the implementation uses assembly. The contribution is an evaluated, dependency-light pipeline that separates:

- loader-relevant ELF facts,
- raw gadget candidate discovery,
- exact suffix evidence,
- semantic primitive coverage,
- candidate provenance,
- mitigation context,
- heuristic utility scores,
- reproducible measurement.

## Claim discipline

The paper may claim only what the preserved evidence supports.

Examples:

- Runtime and memory claims require fixed versions, commands, corpus hashes, repeated trials, raw rows, and generated statistics.
- Coverage claims require explicit gadget definitions and reconciliation with baseline tools.
- Parser robustness claims require hostile-input and regression evidence.
- Defensive usefulness claims require defined analyst tasks and a reproducible case study.
- The paper must not claim exploitability without an independent vulnerability and runtime context.

## Required artifacts

- public repository,
- release tag,
- source and Linux x86_64 artifacts,
- SHA-256 checksums,
- corpus manifest and build commands,
- baseline versions and exact commands,
- raw benchmark results,
- generated summaries, tables, and figures,
- JSON schema and validators,
- hostile-input regression evidence,
- case-study materials,
- reproduction instructions,
- IEEE source and bibliography,
- claim-to-evidence matrix.

## Milestones

| Sprint | Publication milestone |
|---|---|
| 7 | Deterministic hostile-input results, minimized parser regressions, explicit capacity behavior, and checked table-arithmetic foundation. |
| 8 | Mitigation accuracy fixtures and comparison evidence. |
| 9 | Provenance model and schema `0.2.0`. |
| 11 | Reproducible corpus and manifest freeze candidate. |
| 12 | High-resolution pilot results and `v0.1.0-rc1` preview package. |
| 13 | Publication-grade comparative campaign and raw-result freeze. |
| 16 | Infrastructure case study and analyst-utility evidence. |
| 17 | Paper, figures, claim matrix, and replication freeze. |
| 18 | `v0.1.0` release and submission package. |

## Current robustness evidence

Patch 025 adds the first bounded robustness evidence surface: a deterministic 29-case malformed-input campaign, per-case signal and timeout capture, a minimized ELF64 section-entry-size regression, and an explicit candidate-capacity failure fixture. These are development and regression artifacts. They do not justify a formal memory-safety claim or a complete robustness result until the catalog, shared arithmetic layer, and later metadata parsers are evaluated.

## Reviewer-risk sections

The paper should address:

- why NASM is evaluated,
- parser safety without language-level memory safety,
- exact suffix versus decoded validity,
- evidence provenance,
- raw/exact/semantic/validated/scored metric separation,
- candidate truncation and completeness,
- baseline task and output differences,
- timing resolution and cache policy,
- corpus selection bias,
- x86_64 and ELF64 scope,
- future decoder and multi-architecture work.

## Evaluation split

Use separate evaluation questions:

1. **Engine cost:** raw or gadget-report runtime, CPU, RSS, and throughput.
2. **Coverage:** candidate and semantic differences under explicit definitions.
3. **Mitigation accuracy:** controlled fixture and external-tool agreement.
4. **Robustness:** malformed-input outcomes and regression coverage.
5. **Operational value:** analyst task performance or structured case-study interpretation.

Do not combine these into a single superiority claim.

## Release relationship

`v0.1.0-rc1` is a research preview suitable for faculty and external feedback. `v0.1.0` is the first research release intended to accompany the final replication and submission package.

See [`research-release-plan.md`](research-release-plan.md) and [`roadmap-18-sprints.md`](roadmap-18-sprints.md).

## Mitigation-oracle evidence

The implementation now has a compiler-independent mitigation truth table. Patch 030 expands it with bounded dynamic-table evidence for bind-now indicators and malformed dynamic-table rejection. Patch 031 adds no, partial, and full RELRO labels backed by that bounded evidence. Patch 032 adds canary-present and canary-absent indicator rows backed by bounded dynamic-string evidence. Patch 033 adds stripped and not-stripped rows backed by bounded section-header evidence and strict duplicate dynamic string-table singleton rejection. Patch 034 adds section-label annotations and a zero-length dynamic string-table endpoint oracle case. The paper may describe represented program-header, dynamic-table, and section-table combinations plus consistent malformed rejection as deterministic validation evidence. It must not generalize the matrix into full mitigation coverage, full stack-protector proof, complete symbol recovery, or memory-safety proof.

## Sprint 8 Patch 032 publication note

Canary reporting is a static indicator only. Any paper text must describe it as exact `__stack_chk_fail` evidence from a validated dynamic string table, not as proof that the binary or every function is protected by stack canaries.

## Sprint 8 Patch 034 publication note

Stripped reporting is a static section-table metadata indicator only. Any paper text must describe it as bounded `SHT_SYMTAB` evidence, not as proof of source availability, complete symbol recovery, or loader behavior.


## Sprint 9 Patch 040 publication note

Schema `0.2.0` now records which command produced the report and whether bounded
candidate enumeration completed over all loader-derived executable regions.
Publication text may describe this as explicit report identity and enumeration
completeness. It must not describe `analysis.complete` as decoder validation,
complete gadget coverage, exploitability, or memory-safety evidence.

Per-candidate evidence provenance and decoder-gap measurement remain required
before coverage claims are frozen.
