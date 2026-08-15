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

## Current stage during Sprint 12

Sprint 12 remains the active acceptance authority. Patches 081 through 085 did not
complete acceptance; Patch 087 is the current exact-source implementation candidate.
Patch 074 was a superseded closeout candidate.
Patch 075 introduced private text-relocation evidence, Patch 076 added distinct bounded
RPATH/RUNPATH evidence, and Patch 077 required Patch 078, whose review required Patch
079. Patch 080 was superseded by Patch 081. Sprint 13 remains planned and activates only
after complete Patch 087 acceptance. The diagnostic corpus and method remain provisional
until Sprint 15. Sprints 13 and 14 may change capabilities or experimental profiles in
response to diagnostic evidence; such changes require new diagnostic identities and do
not contaminate the later frozen campaign.

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
baseline adapters, Patch 059 owns their campaign binding and the stage-zero
measurement plane. Patch 060 owns corpus-backed summaries and the engineering
gap register, and Patch 061 closes Sprint 11.

## Sprint 11 Patch 057 integrity status

The diagnostic gate now requires a non-executable execution-sealed target
object, exact command-workspace and corpus-member closure, verified staging
cleanup, and a manifest-recognized clean path. These are method-integrity gates,
not capability or performance results. At the Patch 057 boundary, baseline
normalization remained open for Patch 058; later evidence inserted the Patch 059
stage-zero correction before the Patch 060 campaign and gap register.

## Sprint 11 Patch 058 baseline-normalization status

The Patch 058 implementation candidate supplies bounded standalone native-output
adapters for ROPgadget, Ropper, and ropr. They preserve tool-specific records and
duplicates, expose a canonical `pop rdi; ret` relation over represented
instruction text, and keep the raw executable-return-byte relation explicitly
unavailable.

The adapters authenticate caller-supplied commands, files, hashes, limits, and
declared version text, but do not consume runner rows, campaign manifests, child
outcomes, or capture records. Patch 059 replaces that standalone interface with
campaign-bound normalization and the stage-zero measurement plane. Patch 060
runs the authenticated campaign and produces the summaries and engineering gap
register. Patch 061 closes Sprint 11. Sprint 15 remains the campaign freeze.

## Sprint 11 Patch 059 stage-zero status

Accepted Patch 059 adds no comparative result and no analyzer capability. It
binds normalized baseline artifacts to authenticated runner rows, derives a
matched x64lens relation from retained reports, records bounded runtime closure,
calibrates address coordinates across manifest-bound ELF roles, and fixes the
24-comparison plus six-control pre-execution plan.

Native records, duplicates, return-terminator sites, normalized relations,
x64lens evidence-layer populations, and binary presence remain separate. Baseline
raw executable-byte presence remains unavailable, and no generic cross-tool
`gadget_count` is introduced. All stage-zero artifacts remain diagnostic,
unfrozen, and publication-ineligible.

## Sprint 11 Patch 060 cloud checkpoint status

The Patch 060 authenticated cloud checkpoint accounts for all 30 planned
conditions. It executed 12 x64lens conditions, recorded 18 unavailable baseline
conditions, retained 12 warmup and 60 measured native rows, and excluded every
below-floor measured row from primary timing summaries. All 60 measured
x64lens rows were below the reliable floor and remain retained below-floor
observations, not zero timings or a speed result.

The campaign generated six x64lens relation artifacts, two bounded x64lens
task-path closure artifacts, an explicit coordinate-unavailable result, task
summaries, and the engineering gap register. The selected work is limited to
PIE-versus-DSO identity and GNU-property evidence in Sprint 12 plus exact-only
semantic-role review in Sprint 13. Decoder and concurrency remain deferred,
optional Sprint 14 ablations. Patch 061 closes Sprint 11, and Sprint 15 remains
the confirmatory campaign freeze.

## Sprint 11 Patch 061 closeout status

A later WSL2 all-tools replay, qualified only for an evidence-local correction
to the official ROPgadget 7.7 banner, executed 30/30 conditions and retained
180/180 successful process rows. Seventeen conditions were above the 6,361,100
ns reliable floor and 13 were below it; all 12 x64lens conditions were below
that floor. The replay produced 24 normalized relations, but two Python
task-path closures failed and coordinate calibration failed. It was not
comparison-qualified and does not replace the fresh, unmodified Patch 061
campaign required for empirical acceptance.

The cloud checkpoint and WSL2 replay are separate diagnostic strata. Both
remain unfrozen and publication-ineligible. Native execution, normalized
relations, runtime closure, coordinate qualification, and comparison status
remain independent; no generic cross-tool gadget count is permitted.

## Sprint 12 Patch 062 capability-gate update

The `program_header_validity` and `elf_extended_numbering` gates were resolved
by Patch 062. Patch 064 resolved `executable_overlap_policy` by measured
deferral under explicit reopening thresholds. Patches 064-076 carry the
candidate disposition for the private role/property and GNU-property gates
through implementation, diagnostic reconciliation, a corrected environment-
parity protocol, a public-policy decision of `defer`, bounded private static
text-relocation evidence, and distinct private RPATH/RUNPATH evidence. Patch 078
corrected the next parity and custody blockers, but its review required the
Patch 079 corrective and private task-value candidate; Patch 079's review
required Patch 080, which was superseded by Patch 081. Independent exact-source
Patch 087 acceptance remains pending. Any diagnostic campaign after acceptance requires a new
identifier when its task, capability, schema, or method changes.


## Sprint 12 Patch 074 superseded closeout gate update

The Patch 074 stage authority recorded twelve completed sprints and Sprint 13
active, but Patch 074 was superseded before that became project chronology.
Sprint 12 remains active. Patches 081 and 082 were not accepted; Patch 083 is
the current exact-source candidate pending complete local and independent
acceptance. The overlap, PIE/DSO, and GNU-
property gates are `resolved`:
overlap by measured deferral, and role/property projection by retained private
evidence plus an explicit non-reinterpretive public deferral. Resolution does
not mean a public field or runtime-CET claim exists. Patch 078 froze private
exact-pop role facets only; Patch 079 used non-causal deterministic presentation
order for private task-value qualification. Patch 080 retained three facets
privately and deferred public-field and score projection. Optional decoder
and deterministic concurrency remain Sprint 14 decisions.

The Patch 073 diagnostic campaign retained every x64lens row below its measured
timer floor and produced zero positive coordinate anchors. It remains
diagnostic, unfrozen, and publication-ineligible and supports no speed, peak-
RSS, parity, superiority, prevalence, or normalized-coverage claim.

## Patch 079 register-role task-value gate

The five Patch 079 role strata were independent capability gates; aggregate
gains could not rescue a failed stratum. Patch 080 found query reuse across the
development and confirmation-labeled partitions and replaced the task
authority. The Patch 079 result qualified a private facet for LC-08B input only.
Runtime projection, public fields, score/null policy, and confirmatory-campaign
inclusion remained separate gates.

## Patch 082 coordinate and producer gates

The controlled coordinate preflight is a method-discrimination gate over six
generated targets, nine tool-label-by-role cells, and two modeled observations
per cell. It does not execute natural baselines; natural qualification remains
separate. The implemented producer-backed ordered-pair and score/null gate
requires agreement across three independent build roots, but full retained
execution remains pending local validation. Neither gate freezes a campaign,
authorizes a public field, or adds a semantic family.
