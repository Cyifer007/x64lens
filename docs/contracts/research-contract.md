# Research Contract

## Research discipline

The project must preserve a clean evidence trail from implementation to benchmark to paper.

## Required evidence for claims

Any claim about performance, memory use, coverage, or analyst usefulness must include:

- tool version,
- schema version if output is involved,
- baseline tool version,
- corpus manifest,
- exact command,
- run count,
- environment metadata,
- raw results,
- summary statistics.

## Publication posture

The project should be written so that a reader can reproduce results without private binaries, private emails, or hidden assumptions.

## Faculty review vs peer review

Faculty review is valuable technical feedback and course evaluation. External peer review occurs through a conference, workshop, journal, or formal program committee.

## Threats to validity

Every paper draft must include limitations and threats to validity.

## Ethics

The research must avoid unauthorized targets, payload generation, and exploit delivery automation in the semester scope.

## Reviewer-preview rule

When a design critique identifies a likely peer-review objection, convert the objection into one of:

- an explicit limitation,
- a validation task,
- a benchmark metric,
- a roadmap item,
- an ADR,
- a paper threats-to-validity note.

Do not respond by broadening scope unless the current research question requires it.

## Campaign freeze rule

Publication-grade experiments require a frozen corpus, tool versions, commands, schema, benchmark runner, and environment stratum. A method change after freeze creates a new campaign identifier or requires a complete rerun of affected conditions.

## Provenance rule

Candidate coverage claims must identify the evidence layer being measured: raw, exact suffix, semantic exact, decoder validated, semantic decoded, unknown, or scored. A generic gadget count is insufficient for cross-tool claims.

## Release evidence rule

Research preview and final release claims must satisfy the gates in `docs/research-release-plan.md`. Smoke results demonstrate plumbing and regression stability, not universal performance or coverage.

## Sprint 9 report-completeness evidence rule

Research artifacts that consume schema `0.2.0` must preserve report type,
command identity, maximum depth, candidate capacity/count, truncation,
dropped-count knowledge, and executable-region progress. `analysis.complete`
means bounded enumeration completed over the loader-derived executable regions.
It is not decoder-validity or complete gadget-coverage evidence.

Failed capacity runs must remain failed rows or validation outcomes; they must
not be reclassified as emitted truncated reports.


## Decoder-gap evidence rule

External decoder/disassembler comparison is research evidence, not automatic
truth replacement. Every campaign must preserve the x64lens report, external
output, exact commands, versions, executable and target hashes, categorized
differences, and observed validation cost. Boundary, selection-model,
duplicate/canonicalization, and unsupported-family differences must remain
separate.

An embedded decoder decision must identify the affected claim and explain why an
external validation path is insufficient. No decoder is approved solely because
its count differs from the byte-oriented scanner.

## Decoder decision evidence rule

A mandatory decoder may not be introduced from count disagreement alone. The
decision must identify a material user-facing claim or task, use immutable
inputs, retain categorized disagreements and parser diagnostics, preserve raw
facts, and measure dependency, license, binary-size, latency, RSS, and hostile-
input costs. Patch 043 records a decoder-free default and an optional future
adapter seam.

## Acceleration evidence rule

Decoder and parallel execution claims require profile-specific raw evidence.
Report core scanning, candidate-scoped validation, and each worker-count
condition separately. Preserve output hashes and evidence-layer counts so a
speedup cannot hide changed work or changed semantics.

## Decoder and parallel-profile evidence rule

A decoder or parallel profile is a separate experimental condition. Its identity, dependencies, worker count, commands, binary hash, target hash, raw rows, CPU, RSS, and output-definition effects must be recorded. Candidate-scoped decoder validation must preserve raw and exact evidence and may not erase disagreement.

Claims about low observability are limited to dependency, import, helper-process, and resource surface. The project must not claim invisibility or guaranteed evasion of anti-analysis controls without separate evidence.

## Memory-effect evidence rule

Memory coverage claims must identify exact supported addressing forms and distinguish access direction, operand roles, address representation, clobbers, score state, and decoder validity. A base-plus-zero semantic-exact family does not establish general memory-gadget coverage or address controllability.

The fixed 819,200-byte analysis arena is an implementation-capacity fact after Patch 051. Runtime, RSS, throughput, and comparative claims still require the frozen benchmark methodology and raw evidence.


## Primitive-family coverage evidence rule

A pre-release primitive-family claim must identify the exact suffix domain, controlled fixture, effect and clobber facts, conservative fallback boundary, evidence tier, and score disposition. Cross-family fixtures must report a disjoint semantic partition instead of preserving stale family-specific counts. The Sprint 10 family coverage table is development evidence; it does not replace fixed-corpus comparison or decoder reconciliation.

## Architectural-effect research rule

Architectural-effect coverage is a represented exact-suffix fact, not decoded
validity or complete machine-state modeling. Research artifacts must distinguish
complete and partial effect models and must not aggregate them into a universal
side-effect-accuracy claim without decoder-backed reconciliation.

The 819,200-byte command arena is a fixed allocation fact. Any runtime or RSS
claim requires the frozen benchmark methodology and raw measurements.


## Diagnostic measurement rule

Early measurement is encouraged when it can falsify assumptions or guide implementation priorities. Diagnostic campaigns must preserve versions, hashes, commands, raw rows, failures, and environment metadata, but their method and corpus may remain provisional. They cannot support final comparative claims and cannot be merged into a frozen campaign.

Confirmatory measurement begins only after the Sprint 15 campaign freeze. Method, corpus, schema/extractor, tool, task-definition, or capability changes after that point create a new campaign or require rerunning affected conditions.

## Diagnostic-before-freeze rule

Diagnostic measurement may begin before corpus and method freeze when its purpose is to discover bottlenecks, task mismatches, or capability gaps. Diagnostic rows retain complete provenance but remain development evidence. They cannot be merged into the Sprint 15-frozen confirmatory campaign after a material tool, corpus, schema, task, or method change.


## Sprint 11 diagnostic-row integrity rule

Each diagnostic process execution uses executable write-sealed tool bytes and
non-executable `MFD_NOEXEC_SEAL` target bytes carrying `F_SEAL_EXEC`, both bound
to hashed retained files, and records a resolvable campaign-relative replay
command, task/profile identity, phase, order, timer-floor classification,
wall/user/system time, `wait4` maximum RSS, output size and hashes, exit or
signal state, and extraction outcome. Retained version, timer, stdout, and
stderr artifacts are reconciled after the final child exits. Warmups and
failures remain in the raw dataset even when they are excluded from a primary
measured summary. The `wait4` counters
include descendants the selected child waited for; descendants reaped separately
by the runner are excluded, and maximum RSS is not a process-tree sum.

A timer-floor threshold is an interpretation warning, not a value to subtract
from measured time. Rows below the floor require a larger target or a separately
reviewed batch method. A command label is not evidence that two commands perform
different work.

## Provisional corpus evidence rule

Before campaign freeze, a provisional corpus may guide engineering only when
its source, license, build matrix, exact commands, compiler/linker identities,
environment, target hashes, and regeneration procedure are preserved. Generated
targets must be marked diagnostic, unfrozen, and not publication eligible.

Byte equality across two builds supports reproducibility only within the
recorded tool and host stratum. It does not establish corpus representativeness,
cross-toolchain reproducibility, task equivalence, mitigation accuracy, or a
performance advantage. Requested build roles must remain separate from loader
interpretation until analyzer evidence supports them.

Compiler and linker paths must be reauthenticated before publication, and the
command record must show how the requested linker was selected. This does not
prove immunity to transient mutation by an unrelated same-UID writer or capture
unbundled auxiliary compiler programs; those boundaries remain explicit until
the Sprint 15 campaign authority adopts a stronger execution-input model.

## Baseline-normalization evidence rule

Cross-tool comparison requires retained native output plus a versioned adapter
and task authority. Tool-native records, unique records, exact normalized
relations, x64lens evidence-layer counts, timing, RSS, and output size are
separate results. Adapter failure is preserved as a failed diagnostic condition;
it is not evidence of zero baseline coverage. Patch 058's canonical
`pop rdi; ret` relation over represented instruction text is a bounded
reconciliation surface, not a claim that the compared tools perform identical
work or that target bytes were decoded by the adapter.

Authenticated standalone files do not prove that a particular invocation
produced them. A current normalized artifact requires an explicit binding among
the runner row, manifest, child outcome, exact command, and retained tool, target,
version, stdout, and stderr identities.

## Stage-zero measurement-plane evidence rule

Matched x64lens relations must be derived from an authenticated retained report,
not a second target scan or a new ELF, classification, scoring, or reporting
authority. Native baseline records, duplicates, return-terminator sites,
normalized relations, x64lens evidence-layer populations, and binary presence
remain distinct. Baseline decoder output cannot substitute for unavailable
loader-authoritative raw executable-byte presence.

Coordinate comparisons remain blocked until manifest-bound `ET_EXEC`,
PIE-intended `ET_DYN`, and shared-object `ET_DYN` roles calibrate; `ET_DYN` alone
does not identify PIE or DSO. Runtime closure is bounded observed evidence, and
`complete` means complete only within the recorded path. A Python
version-command observation may be narrower than a later analysis command.

A fully accounted campaign plan is not an executed campaign. Stage-zero rows and
artifacts remain diagnostic, unfrozen, and publication-ineligible and cannot
support performance, RSS, coverage, superiority, defensive-utility, or
exploitability claims.
