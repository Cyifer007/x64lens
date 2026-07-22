# Benchmark and Capability Stage Gates

## Purpose

This document separates benchmark design from benchmark freeze. It defines how
measurement can guide development without turning mutable development evidence
into a publication result.

## Core decision

Design and exercise the benchmark system before the analyzer is feature-frozen,
but use two evidence classes:

```text
diagnostic evidence
  provisional corpus + mutable method
  guides engineering and may invalidate assumptions

confirmatory evidence
  frozen corpus + frozen method + frozen capability definitions
  supports preview, publication, and release claims
```

A diagnostic row can identify a bottleneck or coverage gap. It cannot be merged
into the confirmatory dataset after the tool, task definition, schema, corpus,
or method changes.

## Stage model

| Stage | Sprint | Purpose | Evidence status |
|---|---:|---|---|
| Diagnostic foundation | 11 | High-resolution runner, provisional corpus, baseline task mapping, timer floor, and development gap register | Mutable development evidence |
| Capability hardening | 12-14 | Correct loader/mitigation semantics, complete selected primitive roles, and test optional profiles | Separate experiment IDs; no final claim |
| Freeze | 15 | Freeze corpus, schema/extractor, tool versions, commands, runner, task definitions, and environment strata | Campaign authority |
| Preview | 16 | Pilot the frozen design and cut `v0.1.0-rc1` only when preview gates pass | Preview evidence |
| Comparative campaign | 17 | Repeated publication-grade trials and coverage reconciliation | Publication evidence |
| Defensive value | 18-20 | Triage model, automation interfaces, and infrastructure case study | Operational evidence |
| Replication and release | 21-22 | Independent rehearsal, paper freeze, checksummed release | Release evidence |

## Capability reassessment result

The current pre-release analyzer is not a general-purpose gadget suite. It is a
bounded evidence pipeline with these implemented strengths:

| Surface | Current bounded capability | Release treatment |
|---|---|---|
| ELF and loader | ELF64 x86-64 identity, checked tables, file-backed executable `PT_LOAD` regions | Preserve and tighten loader-conformance facts before freeze |
| Mitigations | NX, RWX, dynamic linking, coarse `ET_DYN`-based PIE, no/partial/full RELRO, bind-now, canary, and stripped indicators | Refine PIE/DSO and add bounded IBT/SHSTK evidence before preview |
| Single-pop | Exact recognition for all 16 GPRs; selected semantic roles | Decide generic pop roles and `r10` syscall-argument treatment in Sprint 13 |
| Ordered multi-pop | 30 ordered pairs over `rdi/rsi/rdx/rcx/r8/r9` | Keep; broaden only for a measured task gap |
| Register transfer | 210 distinct non-`rsp` qword register-direct moves | Keep unscored until source-value control is represented |
| Stack adjustment | 15 positive aligned imm8 adjustments | Keep current exact domain and reviewed score policy |
| Memory | Exact qword base-plus-zero, no-index loads and stores | Keep; broader addressing is conditional on measured need and complete operand facts |
| Evidence layers | Candidate provenance kinds `raw_only`, `exact_suffix`, and `semantic_exact`; `unknown_candidate` classification; nullable scores; analysis completeness; and candidate-indexed side-car effects | Preserve as the comparison and automation foundation |
| Validity | External decoder-gap artifacts; no runtime decoder-valid facts | Optional candidate-scoped profile only after ablation |

Before the first release, the project requires comparative evidence for the
explicitly bounded return-oriented task. It does not require a favorable result
or feature parity with every mode of ROPgadget, Ropper, ropr, radare2, or full
disassembly frameworks. A missing capability becomes pre-release work only when
diagnostic evidence shows that it would make a stated research hypothesis,
defensive task, or baseline comparison materially misleading.

## Diagnostic benchmark questions

Sprint 11 must answer engineering questions before it answers publication
hypotheses:

1. Which command scope is being measured: core scanner, gadget report, or
   integrated `analyze`?
2. Which output and validity work does each baseline perform?
3. Where is elapsed time spent: mapping, scanning, classification, effects,
   scoring, JSON formatting, or external validation?
4. Which targets exceed the timer floor without batching?
5. Which candidate-definition differences dominate count disagreement?
6. Does candidate-scoped validation reduce false-positive uncertainty at an
   acceptable dependency, latency, binary-size, and RSS cost?
7. Does target-level or candidate-validation concurrency improve wall time
   without changing output facts or global capacity behavior?

The diagnostic campaign may falsify the current performance hypotheses. That is
a useful result and should redirect implementation rather than be hidden.

## Mandatory capability gates before freeze

The following must be implemented or resolved before Sprint 15 freezes the
campaign:

- loader-authoritative policy for overlapping executable segments and duplicate
  raw observations;
- program-header alignment, congruence, virtual-range, and executable-entrypoint
  validation or explicit unsupported outcomes;
- release decision for generic exact single-pop semantics and the Linux syscall
  `r10` argument role;
- fixed score/null policy for every release-facing exact family;
- exact task and coverage definitions for x64lens and every baseline;
- complete current-family fixture and false-positive contracts.

## Mandatory capability gates before preview

Before `v0.1.0-rc1`:

- distinguish PIE executables from `ET_DYN` shared objects with bounded evidence;
- parse bounded GNU property-note evidence for CET IBT and SHSTK;
- handle ELF extended numbering explicitly, either through bounded support or a
  stable unsupported result;
- bind every campaign report to immutable target bytes and decide whether
  ordinary JSON also carries a target digest;
- preserve native/Docker fact parity and the no-partial-output contract.

## Conditional profiles

### Candidate-scoped decoder

A decoder profile may enter the frozen pre-release campaign only when Sprint 11
diagnostic evidence identifies a material validity or task gap and the Sprint
14 ablation demonstrates a justified benefit at acceptable dependency, latency,
binary-size, RSS, and hostile-input cost. It validates retained candidate starts
and writes additive side-car evidence; it does not replace raw scanning. A gap
first identified during Sprint 17 is follow-up work unless the project assigns a
new campaign identifier or completely reruns every affected condition.

### Deterministic concurrency

Target-level concurrency is the lowest-risk throughput mode. In-process
candidate-validation or region workers require deterministic ordering, one
global capacity result, bounded per-worker memory, complete interruption
cleanup, and byte-identical facts to the one-worker reference.

### Broader ROP families

Add only bounded families that close a measured task gap and can be represented
without weakening provenance or effects. Any change after Sprint 15 restarts
affected measurements.

## Correct post-release deferrals

The first research release does not require:

- full built-in x86-64 disassembly;
- JOP, COP, COOP, SROP, DOP, BROP, or chain synthesis;
- symbolic execution or general dataflow;
- PE, Mach-O, ELF32, ARM64, or other architectures;
- exploit or payload generation;
- a GUI or remote-analysis service.

These remain valuable later research directions.

## Defensive deployment metrics

For every optional profile, record separately:

```text
binary hash and size
dynamic dependencies
helper-process count
worker count
startup cost
wall, user, and system time
maximum RSS
output hash
current aggregate counts:
  raw_candidate_count, exact_pattern_count, semantic_candidate_count,
  unknown_candidate_count, scored_candidate_count
decoder-backed counts, when defined by the optional profile
failure and cleanup behavior
```

A small dependency and process surface may support air-gapped or constrained
use. It is not evidence of invisibility or guaranteed anti-analysis evasion.

## Machine-readable authority

`tests/expected/research-stage-gates.json` is the machine-readable stage and
capability authority. Validate it with:

```bash
make research-stage-gates-smoke
```

## Current stage after Sprint 10

Patch 054 closes Sprint 10 and activates Sprint 11 diagnostic measurement. The reference analyzer and current semantic contracts are stable enough to measure, but the corpus and method remain provisional until Sprint 15. Sprints 12 through 14 may change capabilities or experimental profiles in response to diagnostic evidence; such changes require new diagnostic identities and do not contaminate the later frozen campaign.

## Sprint 11 Patch 055 foundation status

Patch 055 implements the first diagnostic runner and task-definition tranche:

- standard-library monotonic timing and Linux `wait4` resource capture whose
  selected-child, waited-descendant, and separately reaped-descendant scopes are
  explicit;
- retained runner/specification identity plus hashed tool, target, and
  timer-probe files executed through write-sealed Linux `memfd` copies;
- final reconciliation of retained version, timer, stdout, and stderr artifacts;
- retained warmup, measured, failed, signaled, timed-out, and extraction rows;
- explicit timer-floor and cache/order policy;
- process-group containment plus subreaper cleanup of escaped descendants;
- transactional no-replace result publication;
- truthful gadget/analyze JSON command conditions;
- an explicit unavailable state for scanner-only timing;
- planned, not yet implemented, baseline task records.

This satisfies runner plumbing and initial task identity. It does not complete
the Sprint 11 provisional corpus, baseline adapters, development summary, or
gap register. The diagnostic stage remains mutable and the campaign-freeze gate
remains Sprint 15.

## Sprint 11 Patch 056 provisional corpus status

Patch 056 completes the first corpus-regeneration tranche:

- one project-authored Apache-2.0 freestanding source;
- a 24-target GCC/Clang, optimization, requested-role, and hardening matrix;
- exact source, license, builder, compiler-driver, requested-linker, command,
  environment, output, and SHA-256 records;
- two-build byte/mode/mtime reproducibility;
- target nonexecution;
- explicit `diagnostic`, `frozen=false`, and `publication_eligible=false` state;
- signal-safe compiler cleanup, late reauthentication, and no-replace
  publication; and
- generated-corpus exclusion from Git, Docker, and ordinary public overlays.

This advances but does not complete the Sprint 11 diagnostic gate. Patch 057
corrects the runner and corpus integrity findings. Patch 058 owns normalized
baseline adapters, and Patch 059 owns corpus-backed summaries and the
engineering gap register.

## Sprint 11 Patch 057 integrity status

The diagnostic gate now requires a non-executable execution-sealed target
object, exact command-workspace and corpus-member closure, verified staging
cleanup, and a manifest-recognized clean path. These are method-integrity gates,
not capability or performance results. Baseline normalization remains open for
Patch 058, and the gap register remains open for Patch 059.
