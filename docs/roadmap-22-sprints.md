# Twenty-Two-Sprint Roadmap

## Purpose

This is the canonical x64lens implementation and research roadmap. It replaces
the earlier twelve- and eighteen-sprint ceilings while preserving completed
architecture, validation, schema, and metric contracts.

The expansion separates diagnostic measurement from confirmatory measurement.
Benchmark infrastructure begins before capability freeze so evidence can guide
development. Publication results begin only after corpus, methods, schema, tool
versions, commands, and task definitions are frozen.

## Current checkpoint

Sprints 1 through 10 are complete after Patch 054. Sprint 11 is active as the
diagnostic benchmark foundation. Patches 055 and 056 implement the runner,
task-definition authority, and first reproducible 24-target provisional corpus.
Patch 057 corrects the diagnostic target-execution, corpus-membership, cleanup,
and safe-removal boundaries before baseline scope expands; adapters, corpus-
backed summaries, and the gap register remain active work. Sprint 15 freezes the
confirmatory campaign.

The reference runtime remains a bounded, dependency-free, decoder-free,
one-worker ELF64 x86_64 analyzer. Optional decoder or parallel profiles must
remain separate experimental conditions.

## Release gates

| Gate | Target | Required evidence |
|---|---:|---|
| Integrated checkpoint | Sprint 6, complete | Functional end-to-end prototype and `v0.1.0-dev` checkpoint |
| Diagnostic measurement checkpoint | Sprint 11 | Provisional corpus, high-resolution runner, task map, and gap register; no publication claims |
| Campaign freeze | Sprint 15 | Frozen corpus, schema/extractor, runner, baselines, commands, task definitions, and environment strata |
| Research preview candidate | Sprint 16 | Frozen pilot campaign, checksummed preview artifacts, and `v0.1.0-rc1` gates |
| Publication campaign | Sprint 17 | Repeated trials, coverage reconciliation, raw-row freeze, generated summaries |
| First research release | Sprint 22 | Case study, replication rehearsal, claim audit, paper, and checksummed `v0.1.0` artifacts |

Calendar progress does not satisfy an evidence gate.

## Sprint map

| Sprint | Theme | Primary outcome |
|---:|---|---|
| 1 | ELF64 identity | Read-only file mapping and `info` |
| 2 | Loader mapping | Program headers, executable regions, and baseline mitigations |
| 3 | Scanner foundation | Bounded raw candidates, arena storage, exact suffixes, smoke measurement |
| 4 | Semantic classification | Conservative primitive roles and unknown preservation |
| 5 | Scores, JSON, validation | Relative utility scores, schema, system and baseline smoke |
| 6 | Integrated checkpoint | `analyze`, composable reports, checkpoint tag, roadmap expansion |
| 7 | Hostile-input hardening | Deterministic mutation, capacity, mitigation oracle, checked arithmetic |
| 8 | Mitigation and metadata depth | Dynamic evidence, RELRO, canary, stripped, labels, comparators |
| 9 | Provenance and decoder-gap evidence | Schema `0.2.0`, completeness, candidate provenance, decoder decision |
| 10 | Evidence-aware primitive expansion | Multi-pop, transfer, stack-adjust, memory effects, architectural effects, score and fixture closure |
| 11 | Diagnostic benchmark foundation | Provisional corpus, high-resolution runner, baseline task normalization, development gap register |
| 12 | Loader and mitigation precision | PIE versus DSO, CET IBT/SHSTK, overlap policy, PHDR validity, extended-numbering outcome |
| 13 | Semantic capability completion | Generic pop/syscall roles, measured bounded family additions, score-policy completion |
| 14 | Optional profile ablations | Candidate-scoped decoder and deterministic concurrency experiments, reference-profile preservation |
| 15 | Corpus and method freeze | Final corpus, licenses, hashes, schema, runner, baselines, commands, task definitions |
| 16 | Preview campaign and `rc1` | Frozen pilot, preview reproduction, `v0.1.0-rc1` candidate |
| 17 | Comparative campaign | Publication-grade repeated trials, coverage reconciliation, raw-result freeze |
| 18 | Defensive triage model | Mitigation-aware binary interpretation with evidence and uncertainty |
| 19 | Automation and schema stabilization | CI policy semantics, compatibility, optional SARIF adapter evaluation |
| 20 | Infrastructure case study | Reproducible network-facing software evaluation and analyst tasks |
| 21 | Replication and paper freeze | Independent rehearsal, figures, claim matrix, release-candidate audit |
| 22 | First research release | `v0.1.0`, checksummed artifacts, paper and submission package |

## Why benchmarking begins before freeze

Diagnostic measurement serves engineering decisions. It can reveal that:

- the scanner is already fast enough and reporting dominates;
- output definitions make a comparison unfair;
- a coverage gap is material to a research question;
- candidate-scoped validation is worth its dependency cost;
- concurrency reduces wall time but harms RSS or determinism;
- a hypothesis is false and should be narrowed.

Those outcomes are valuable even when the method changes afterward. They are not
publication results.

Confirmatory measurement begins only after Sprint 15. Rows collected before the
freeze remain development evidence and are never silently merged into the final
campaign.

## Required capability gates before Sprint 15

- complete and tested current-family effects and score/null policy;
- executable-segment overlap and duplicate-count policy;
- bounded PHDR alignment, congruence, virtual-range, and entrypoint behavior;
- generic exact-pop and Linux syscall-register semantic decision;
- task-equivalent baseline definitions;
- stable current aggregate metrics: `raw_candidate_count`,
  `exact_pattern_count`, `semantic_candidate_count`,
  `unknown_candidate_count`, and `scored_candidate_count`, with separately
  defined decoder-backed metrics if an optional profile is admitted;
- no-partial-output, capacity, and malformed-input gates.

## Required capability gates before Sprint 16

- PIE executable versus shared-object distinction;
- bounded CET IBT and SHSTK GNU-property evidence;
- explicit ELF extended-numbering behavior;
- immutable target/report binding for every preview row;
- frozen schema/extractor and native/Docker parity;
- preview corpus and baseline licenses.

## Conditional pre-release capability work

Candidate-scoped decoding, deterministic worker profiles, and a small number of
broader ROP families are conditional. They enter the release only when
diagnostic evidence shows that a material research claim or defensive task
would otherwise be misleading. Every conditional profile receives separate
identity, dependency, RSS, CPU, wall-time, and output-equivalence evidence.

## Post-release scope

The first release does not require full disassembly, JOP/COP/SROP, chain
synthesis, symbolic execution, other architectures or formats, exploit
generation, a library API, a GUI, or remote service operation.

## Schema and campaign rules

- Keep `0.2.x` backward compatible through the preview and publication campaign.
- A correctness-required schema change after Sprint 15 restarts affected
  experiments or creates a separate campaign.
- Smoke, diagnostic, preview, publication, and case-study evidence remain
  separate datasets.
- Generated tables and figures come only from preserved raw rows.

## Architecture constraints

- Program headers remain runtime mapping authority.
- Dynamic and section metadata remain bounded evidence or annotations.
- Scanner, exact matcher, classifier, side-cars, scoring, and reporters remain
  separate.
- Optional decoder facts are additive and never erase raw observations.
- One-worker reference output remains deterministic and bounded.
- Public artifacts exclude private context and pass archive/content policies.

See:

- [`design/benchmark-and-capability-stage-gates.md`](design/benchmark-and-capability-stage-gates.md)
- [`research-release-plan.md`](research-release-plan.md)
- [`benchmark-methodology.md`](benchmark-methodology.md)
- [`adr/0039-benchmark-informed-capability-roadmap.md`](adr/0039-benchmark-informed-capability-roadmap.md)
