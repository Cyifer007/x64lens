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

Each diagnostic process execution retains immutable tool and target identity,
exact command, task/profile identity, phase, order, timer-floor classification,
wall/user/system time, direct-child maximum RSS, output size and hashes, exit or signal state,
and extraction outcome. Warmups and failures remain in the raw dataset even
when they are excluded from a primary measured summary. Descendant resource use
is not aggregated into the direct-child row and must remain an explicit limitation.

A timer-floor threshold is an interpretation warning, not a value to subtract
from measured time. Rows below the floor require a larger target or a separately
reviewed batch method. A command label is not evidence that two commands perform
different work.
