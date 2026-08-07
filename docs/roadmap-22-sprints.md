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

Sprints 1 through 11 are complete. Sprint 12 remains the acceptance authority
for its loader and mitigation facts while Patch 081 records the semester
retrospective and carries the remaining Patch 080 corrective boundary into
Sprint 13. The roadmap may state "Sprints 1 through 12 are complete" and
"Sprint 13 is active" only after every exact-source native, Docker, parity,
delivery, and independent acceptance gate passes.

Sprint 12 delivered bounded ordinary-PHDR validity, explicit extended-numbering
outcomes, executable-overlap contributor provenance and measured normalization
deferral, private PIE/DSO and GNU-property evidence, controlled and held-out
private-fact matrices, authenticated GNU `readelf` reconciliation, outcome-blind
external-natural acquisition, corrected native/container parity protocols, an
explicit public-policy deferral, private text-relocation evidence, and distinct
private RPATH/RUNPATH evidence. The completed engineering scope and lessons are
recorded in [`sprints/sprint-12-retro.md`](sprints/sprint-12-retro.md).

Patch 080 added a private candidate-index role side-car for three qualified
single-pop facets while preserving public output and scores. Patch 081 corrects
its transaction, Git-less source, Docker provenance, helper-identity, and
evidence-seal findings. Patch 081 also runs a test-only ordered two-pop
role-tuple pilot. Existing `stack_pop_order` facts answer all frozen tasks, so a
new runtime tuple record is deferred. A separate authority retains the complete
25-pattern score/null partition.

All Sprint 11-13 campaign observations remain diagnostic, unfrozen, and
publication-ineligible. The retained P080 campaign had zero x64lens rows above
its reliable timer floor and zero positive coordinate anchors, so it supports no
speed, peak-RSS, parity, superiority, or normalized-coverage claim. Sprint 15
remains the confirmatory campaign freeze.

The reference runtime remains bounded, dependency-free, decoder-free,
one-worker, deterministic, read-only with respect to targets, and incapable of
target execution.

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
| 12 | Loader and mitigation precision | PHDR validity and extended numbering, overlap/provenance, PIE versus DSO, CET IBT/SHSTK, private-fact diagnostic matrix |
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
- positive role-controlled coordinate anchors and complete runtime closure for
  all five task paths before any diagnostic comparison qualification;
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

## Sprint 12 Patch 062 checkpoint

Patch 062 completes the ordinary PHDR-validity and explicit
extended-numbering-outcome gates without changing the reference scanner or
report schema. Its subsequent ordered gates were executable-overlap provenance,
PIE-versus-DSO evidence, and bounded GNU-property IBT/SHSTK evidence; the current
Sprint 12 status is recorded below.

## Sprint 12 Patch 063-064 checkpoint

Patch 063 retains lossless overlap provenance. The Patch 064 candidate
records the measured decision to defer executable-range normalization because
the bounded diagnostic sample produced no overlap activation, then adds an
internal-only fact-first PIE-versus-DSO role lattice without changing public
output. Patch 064 did not pass validation; its decision and required corrections
were carried through Patch 065 and Patch 066.

## Sprint 12 Patch 065-066 checkpoint

Patch 065 added bounded private GNU-property evidence but required correction.
Patch 066 fixes the parser and custody defects and adds the controlled 28-object
role/property metamorphic preflight. Public mitigation fields and schema `0.2.0`
remain unchanged; malformed non-identical carrier overlap now fails before
output. Patch 068 later adds the separate natural/metamorphic private-fact
matrix. At that historical boundary, Sprint 12 still required bounded external
ELF reconciliation. Patch 069 added exact `readelf -hW/-lW/-dW/-nW`
reconciliation; native/container private-fact parity
still precedes a separate public-policy review or Sprint 13 handoff.

## Sprint 12 Patch 067 checkpoint

Patch 067 added C/NASM layout reconciliation for the development fact probe but
required additional transaction and oracle correction. Patch 068 carries those
corrections and adds the separately identified diagnostic private-fact matrix.
The reconciliation attests probe record interpretation only; it does not
establish analyzer behavior or publication evidence. Patch 069 adds bounded
external reconciliation; native/container private-fact parity remains a
subsequent gate.

## Sprint 12 Patch 068 checkpoint

Patch 068 defined corrections for the remaining Patch 067 corpus mode-repair,
rollback, and public-output leakage boundaries and introduced a private-fact
diagnostic agreement gate for 48 held-out natural objects and 48 controlled
metamorphic objects. It required further correction. The natural and
metamorphic strata remain separate, diagnostic, unfrozen, and publication-
ineligible; public schema and output remain unchanged. At the Patch 068
boundary, bounded external reconciliation was still future work. Patch 069
added that reconciliation; native/container private-fact parity and a deliberate
public-policy decision remain later gates.

## Sprint 12 Patch 069 checkpoint

Patch 069 addressed the Patch 068 corpus and matrix custody gaps and added an
authenticated field-scoped GNU
`readelf -hW/-lW/-dW/-nW` reconciliation over the 96-object diagnostic matrix.
The controlled matrix records 1,224 eligible matches and zero unexplained
eligible mismatches; ambiguous, unavailable, and retained `not_eligible` cells
remain visible rather than being forced into parity. Public output and schema
`0.2.0` remain unchanged.

Sprint 12 still requires qualified native/container private-fact parity and a
separate public-policy decision before any new role-derived PIE/DSO or
IBT/SHSTK indicator is considered. The existing coarse `mitigations.pie` field
remains unchanged. The result remains diagnostic, unfrozen, and publication-
ineligible. Patch 069 required the further Patch 070 evidence-integrity
correction; Patch 070 acceptance was rejected; Patch 071 corrected the first
blocker set, and Patch 072 carries the remaining correction plus acquisition
and parity gates.

## Patch 070 through Patch 078 sequencing note

Patches 070, 071, 072, and 073 were not accepted at their respective first
returned review boundaries. Patch 071 corrected the first nested-cleanup, case-
oracle, streaming-limit, and delivery-custody blockers. Patch 072 carried the
narrower
generation, descendant, publication, duplicate-key, and delivery-completeness
corrections while completing outcome-blind external-natural acquisition and the
initial same-byte native/container parity protocol. Patch 073 carried the first
custody/isolation correction and executed public policy as an explicit
deferral. Patch 074 supplied the final topology, parity-protocol, permission,
selection-inode, and authority-oracle correction but was superseded as the
closeout candidate. Patch 075 introduced bounded private static text-relocation
evidence, and Patch 076 added distinct private RPATH/RUNPATH evidence. Patch
076's review required Patch 077. Patch 077 then required Patch 078, whose review
required the Patch 079 corrective and private task-value candidate, whose review required Patch 080,
pending complete acceptance. None of these patches advances the Sprint 15 freeze, adds
a public mitigation field, or changes the dependency-free one-worker reference
profile.


## Patch 072 evidence gate

The external-natural authority selects 48 installed-package objects after
package, path, mode, and ELF eligibility checks and before any x64lens, private
fact-probe, or GNU `readelf` outcome is consumed: twelve per source lineage with
seven executable and five library paths. The same-byte environment authority
compares the authenticated 96-object matrix with identical analyzer, probe, and
schema bytes across native and container planes. Retained diagnostic
acquisition evidence remains separate from the same-host logic-only parity
planes; qualified native/container parity remains pending. Both remain unfrozen
and publication-ineligible. Patch 073 therefore adds no public role/property
field and records
`defer`; this does not replace positive coordinate anchors, runtime closure,
whole-batch workload qualification, or the Sprint 15 campaign freeze. Corrected
write-isolated parity and independent acceptance remain active Sprint 12 gates.

## Patch 073 policy decision through Patch 076 continuation note

Patch 073 authenticated the unchanged public schema and reporter sources,
preserved `mitigations.pie`, and rejected authorization while required
prerequisites remained open. Patch 074 implements corrections for the remaining
delivery topology, late-mutation, hardlink, selection-inode, parity membership/
mount/publication, permission-normalization, and negative-oracle findings. The
competitive gap authority retains text-relocation and distinct RPATH/RUNPATH
indicators as separate bounded tranches. Patch 075 introduced private static
text-relocation evidence, and Patch 076 adds distinct private RPATH/RUNPATH
carrier/value evidence. No public mitigation field is added.


## Patch 076 bounded search-path checkpoint

Patch 076 preserves the Patch 075 private text-relocation prefix and appends
separate exact-byte `DT_RPATH` and `DT_RUNPATH` evidence with fixed carrier,
record, and byte budgets. It performs no path-derived open, loader emulation,
path expansion, public projection, or schema change. Complete native/container
private dynamic-metadata parity and independent acceptance remain required.
Patch 078 required the Patch 079 corrective and private task-value candidate, whose review required Patch 080.

## Sprint 12 Patch 077 historical checkpoint

Patch 077 was a Sprint 12 reconciliation candidate. It preserved
the implemented private textrel/RPATH/RUNPATH facts, corrected their surrounding
transactions and oracles, and added no public field. Its review required Patch
078, whose review in turn required Patch 079; Patch 079's review required Patch
080. Exact Patch 080 acceptance is still required before Sprint 13 activation;
the confirmatory campaign remains frozen only in Sprint 15.

## Historical Sprint 13 Patch 079 checkpoint

Patch 079 executed the first Sprint 13 task-value gate after correcting the
Patch 078 acceptance surface. `generic_control`, `sysv_call_arguments`, and
`linux_syscall_arguments` qualify only as private task-value evidence;
`syscall_number` and `stack_pivot` remain deferred by the Patch 079 task gate,
with existing runtime semantics and scores unchanged. Patch 079 projected no
role into runtime or public output. Patch 080 subsequently retained three role
facets privately and deferred public and score projection.

## Sprint 13 Patch 080 checkpoint

Patch 080 corrects Patch 079 and materializes generic-control, System V
call-argument, and Linux syscall-argument facets in a private bounded side-car.
It adds no public field, score, schema change, decoder, or worker. Patch 081 owns
the next evidence-selected semantic tranche after complete Patch 080 acceptance.

## Sprint 13 Patch 081 checkpoint

Patch 081 records the Sprint 12 retrospective, corrects the Patch 080 acceptance tooling, and closes the ordered two-pop convenience-record question with a negative task-value result. Existing exact ordered-pop facts remain sufficient; no runtime record, public field, semantic class, score, schema, capacity, dependency, or worker change is introduced. The next Sprint 13 tranche remains evidence-selected.
