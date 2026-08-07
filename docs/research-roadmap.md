# Research Roadmap

## Current checkpoint

Sprints 1 through 11 are complete. Sprint 12 remains the acceptance authority
for its loader and mitigation facts while Patch 081 records the public
retrospective and continues the remaining corrective work in Sprint 13.

Sprint 12 established ordinary program-header validity, explicit
extended-numbering outcomes, executable-overlap contributor provenance and
measured normalization deferral, a private PIE/DSO role lattice, bounded private
GNU-property IBT/SHSTK facts, natural and controlled private-fact strata, exact
GNU `readelf` reconciliation, outcome-blind external-natural acquisition,
corrected native/container parity protocols, private textrel/RPATH/RUNPATH
facts, and a public-policy decision of `defer`.

Patch 080 added three private single-pop role facets without public or score
projection. Patch 081 corrects its acceptance infrastructure, records
`docs/sprints/sprint-12-retro.md`, and runs the ordered two-pop task-value pilot.
Because current exact ordered-pop facts already answer the frozen tasks, a new
runtime tuple representation is deferred. Existing semantic classes and scores
remain unchanged.

All measurement evidence remains diagnostic, unfrozen, and
publication-ineligible. Sprint 15 still freezes the confirmatory campaign.

The repository now provides:

- a NASM-first ELF64 x86_64 parser and read-only mapping path,
- program-header-authoritative executable regions,
- baseline mitigation facts plus bounded dynamic-table bind-now evidence,
- raw return-terminator candidate discovery,
- arena-backed candidate records,
- exact suffix pattern recognition,
- conservative semantic classes and register coverage,
- heuristic scores,
- schema-versioned JSON,
- an integrated `analyze` command,
- controlled, system-binary, Docker, and public-documentation validation,
- baseline comparison smoke plumbing,
- automated `readelf` comparison and optional `checksec` / `rabin2 -I` review helpers,
- benchmark-integrity and Docker-context hygiene gates,
- monotonic diagnostic timing with accurately scoped Linux `wait4` resource rows,
  retained runner/specification identity, executable write-sealed tool/probe
  copies, non-executable execution-sealed target copies, timer-floor evidence,
  post-child artifact reconciliation, and subreaper-backed process-tree cleanup,
- standalone task-normalized baseline adapters with tool-specific metrics,
  represented-text relations, and an explicit unavailable raw-byte relation,
- campaign-bound normalization, retained-report-derived matched x64lens
  relations, bounded runtime closure, manifest-bound coordinate calibration, and
  a pre-execution 24-comparison plus six-control plan,
- a repeatable checkpoint demonstration.

The `v0.1.0-dev` tag identifies the Sprint 6 integrated-prototype checkpoint.
Patches 046 through 053 are later pre-release work, not a research release or
evidence of universal performance or coverage superiority. Patch 054 closes
Sprint 10 and activates Sprint 11 diagnostic measurement. Patches 055 through
057 implement and harden the runner, task-definition, and provisional-corpus
tranches. Patch 058 adds standalone baseline normalization, and accepted Patch
059 supplies the corrected stage-zero plane. Neither creates an executed
comparative or publication campaign or changes the reference analyzer. The
Patch 060 campaign remains mutable diagnostic evidence and does not support a
release-facing comparison claim.

## Sprint 7 evidence checkpoint

Patch 025 introduces development evidence for parser robustness without upgrading that evidence into a formal safety claim:

- a fixed 29-case mutation catalog derived from a controlled ELF64 seed,
- per-case expected and observed exit status, signal, timeout, elapsed-time, and output-size records,
- an explicit 4096-candidate arena boundary tested at both 4096 and 4097 terminators,
- exact 64-byte ELF64 section-header entry-size rejection,
- native, CI, and Docker validation paths.

Passing this gate demonstrates stable behavior for the reviewed cases. It does not establish memory safety or code-coverage completeness.

## Research stages

### Stage 1: deterministic binary facts

Build safe ELF64 identity, loader mappings, executable regions, and baseline mitigations.

Status: implemented in stages. Patch 025 added deterministic malformed-input and candidate-capacity gates. Patch 028 added shared checked table arithmetic and table-end overflow probes. Patch 029 closes Sprint 7. Patch 030 opens Sprint 8 with bounded `PT_DYNAMIC` parsing for bind-now evidence, dynamic-entry count, and terminator state. Patch 031 adds the no, partial, and full RELRO evidence split. Patch 032 adds the first evidence-qualified canary indicator. Patch 033 adds the first stripped-status indicator and strict dynamic-string singleton policy. Patch 034 adds section-label annotations as metadata only, Patch 035 hardens their rendering and ambiguity policy, Patch 036 hardens historical evidence-quality findings, Patch 037 adds comparison gates, and Patch 039 closes Sprint 8.

### Stage 2: candidate discovery and semantics

Discover bounded candidate windows, recognize exact suffixes, classify supported primitive types, preserve unknowns, and assign bounded heuristic scores.

Status: implemented for the initial exact-pattern set. Raw, exact-suffix, and semantic-exact provenance are now machine-readable; decoder-backed provenance and broader primitives remain future work.

### Stage 3: evidence provenance and validity

Distinguish raw byte observations, exact suffix evidence, semantic-exact classification, decoder validation, and analysis completeness.

Status: complete for the Sprint 9 scope. Patches 040-041 implement the schema `0.2.0` report envelope, completeness, parity, and raw/exact-suffix/semantic-exact provenance. Patches 042-045 implement and harden the external decoder-gap campaign, transactional evidence, parser/archive integrity, public-release boundaries, and the candidate-scoped optional decoder decision. Decoder-backed tiers remain unimplemented and optional; they may be added only through a separately measured side-car adapter.

### Stage 4: mitigation-aware triage

Connect static mitigation evidence and primitive coverage to defensive constraints without claiming vulnerability or exploitability.

Status: baseline indicators exist, Patch 030 adds bounded bind-now evidence, Patch 031 adds no, partial, and full RELRO reporting, Patch 032 adds an evidence-qualified canary indicator, Patch 033 adds a section-table stripped-status indicator, Patch 034 adds section-label annotations, and Patches 035-038 harden reporting, evidence hygiene, and comparator gates. Evidence and triage work continues in later sprints.

### Stage 5: reproducible measurement

Use a fixed corpus, baseline versions, high-resolution timing, per-child resource measurements, raw result preservation, and generated summaries.

Status: the diagnostic measurement foundation is implemented. Patches 055
through 058 provide the high-resolution runner, controlled reference conditions,
task authority, reproducible provisional corpus, and standalone baseline
adapters. Accepted Patch 059 adds campaign binding and the stage-zero
measurement plane. The Patch 060 implementation candidate accounts for all 30
provisional conditions, executes available-tool conditions, and generates
corpus-backed rows, development summaries, and the engineering gap register.
Patch 061 closes Sprint 11. Sprints 12 through 14 use diagnostic evidence
for capability hardening, while Sprint 15 freezes the campaign, Sprint 16 runs
the preview pilot, and Sprint 17 runs publication-grade repeated trials.

### Stage 6: operational case study

Evaluate whether semantic and mitigation-aware reports improve triage of public network-facing infrastructure binaries.

Status: planned for Sprint 20 after the measurement, triage, and automation
surfaces stabilize.

### Stage 7: publication and release

Freeze the evidence, reproduce the core workflow on a clean environment, audit claims, publish checksummed artifacts, and prepare the paper submission package.

Status: planned across Sprints 21 and 22.

## Research questions

### RQ1: performance and resource efficiency

How do runtime, CPU cost, max RSS, throughput, and output size compare with established gadget tools under a fixed corpus and methodology?

### RQ2: semantic and evidence value

Does separating raw candidates, exact suffix observations, semantic primitives, evidence tiers, unknowns, and scores provide more useful triage than raw gadget enumeration alone?

### RQ3: operational adoption

Can a dependency-light static analyzer support CI, vulnerability-management enrichment, or infrastructure-binary prioritization with clear limitations and stable machine-readable contracts?

## Reviewer-risk conversion

| Likely objection | Research response |
|---|---|
| NASM may not provide meaningful benefit | Measure runtime and memory, include task-equivalence caveats, and consider a narrow C/Rust ablation only if needed. |
| Assembly parser safety is weak | Add deterministic mutation smoke tests, parser regressions, explicit bounds invariants, and no formal memory-safety claim. |
| Exact suffix matching is brittle | Preserve evidence tiers, quantify decoder gaps, and add a decoder only through the measured decision gate. |
| Raw counts are noisy | Keep raw-candidate, exact-suffix, semantic-exact, decoder-validated, unknown-candidate, and scored metrics separate. |
| Mitigation findings can be overstated | Report evidence and confidence, distinguish indicators from proof, and avoid exploitability verdicts. |
| Benchmarks are not comparable | Separate gadget-discovery and end-to-end tasks, freeze commands and corpus, and reconcile definitions. |
| Results are not reproducible | Preserve hashes, versions, commands, raw rows, generated summaries, and a clean-environment rehearsal. |
| x86_64 scope is narrow | State it as a bounded research scope and keep architecture/format expansion as post-release work. |

## Release-linked milestones

| Milestone | Research outcome |
|---|---|
| `v0.1.0-dev` | Functional integrated prototype and known-good checkpoint. |
| `v0.1.0-rc1` | Hardened preview with provenance-aware output, reproducible corpus, and high-resolution pilot measurement. |
| `v0.1.0` | Fixed benchmark campaign, operational case study, replication package, paper-ready evidence, and checksummed release. |

## Long-arc directions after `v0.1.0`

Potential future research includes:

- optional embedded decoder integration,
- ARM64 and other architecture engines,
- PE and Mach-O formats,
- JOP, COP, and SROP primitive models,
- CET/IBT-aware semantic analysis,
- firmware and network-appliance case studies,
- AI-assisted interpretation over deterministic low-level facts,
- larger analyst-utility experiments.

These are post-release research decisions, not hidden requirements for the current roadmap.

See [`roadmap-22-sprints.md`](roadmap-22-sprints.md), [`design/benchmark-and-capability-stage-gates.md`](design/benchmark-and-capability-stage-gates.md), and [`research-release-plan.md`](research-release-plan.md).

## Patch 026 behavior oracle

The project fixed expected loader-level mitigation behavior before parser arithmetic was refactored. Patch 028 was accepted against the Patch 025 hostile-input campaign and the Patch 027-corrected mitigation matrix. Patch 030 then expands that oracle to bounded dynamic-table evidence, and Patch 031 uses it for RELRO refinement.


## Post-Sprint 7 research posture

Sprint 7 improves the trustworthiness of later measurements by hardening parser boundaries and deterministic oracles first. Patch 030 adds the first bounded Sprint 8 metadata reader, and Patch 031 composes that evidence into refined RELRO reporting. RQ1 performance work should continue to treat smoke timings as development evidence only. RQ2 semantic-value work should preserve raw/exact/semantic/scored boundaries. RQ3 operational-use work should emphasize evidence-qualified mitigation metadata in Sprint 8.

## Sprint 8 Patch 032 roadmap update

Mitigation-depth work now includes bounded dynamic-table evidence, refined RELRO states, and a bounded dynamic-string canary indicator. Remaining near-term metadata work should prioritize stripped-state and section labels as analyst annotations before moving into schema `0.2.0` evidence provenance.

## Sprint 8 Patch 033 roadmap update

Patch 033 completes the first stripped-status indicator and extends the mitigation oracle with dynamic string-table singleton and scan-cap boundary cases. Patch 034 completes section labels as annotations. Patch 035 resolves validation-discovered section-label hardening defects. Sprint 8 should pause for the historical review before Sprint 9 begins.

## Sprint 8 Patch 034 update

Patch 034 adds section-label annotations as metadata only, Patch 035 hardens their rendering and ambiguity policy, Patch 036 hardens historical evidence-quality findings, Patch 037 adds comparison gates, and Patch 039 closes Sprint 8. This improves defender readability without changing the scanner, classifier, scoring, or mitigation authority boundaries. The result supports the later evidence-provenance schema transition because section-derived labels can be identified separately from loader-derived regions.


## Sprint 8 Patch 035 update

Patch 035 improves the reliability of section-derived annotations under hostile metadata. This keeps the research claim narrow: labels improve analyst readability, but all runtime authority and candidate counting still come from loader-derived regions and scanner/classifier records.


## Sprint 8 closeout update

Sprint 8 is closed. The project now has sufficient mitigation-depth and metadata
hardening to begin Sprint 9 provenance work, but not enough evidence to make
publication-grade speed, coverage, or decoded-gadget parity claims. The next
research risk to retire is machine-readable evidence identity: what report was
run, against which target hash and command, whether candidate enumeration was
complete, and which evidence tier justified each semantic claim.


## Sprint 9 Patch 040 research update

Patch 040 retires the ambiguity around which command produced a JSON report and
whether bounded candidate enumeration completed. This improves evidence
identity, but it does not yet establish candidate validity provenance or target
hash provenance. A complete report can still contain exact-suffix evidence that
has not been decoder validated.

The next research risk is therefore unchanged at the candidate layer: quantify
canonical-boundary, selection-model, and exact-catalog gaps, preserve external
decoder comparison artifacts, and decide whether an embedded decoder is
justified from measured impact rather than implementation preference.


## Patch 041 research posture

Per-candidate provenance is now machine-readable, but no decoded-validity claim
is added. This strengthens RQ2 by making evidence source auditable and
strengthens later RQ1/RQ2 comparisons by preventing mixed tool/schema benchmark
summaries. The next research result must be a measured decoder-gap artifact, not
a broader pattern catalog.


## Patch 042 research posture

Patch 042 converts decoder uncertainty into reproducible development evidence
without modifying the analyzer. The controlled gate reconciles exact suffixes
against canonical GNU objdump boundaries, while the broader campaign preserves
tool and target hashes, exact commands, raw reports, disassembly, timing/RSS
smoke data, duplicate/canonicalization facts, and categorized disagreement
samples. These artifacts are evidence for the decision gate, not publication-
grade coverage or performance results.

Patch 043 records the reviewed outcome: the default runtime remains decoder-free,
and a future decoder is optional evidence infrastructure rather than required
runtime authority. The campaign is development evidence, not a publication
benchmark.

## Patch 043 research posture

The reviewed campaign found no canonical return terminator absent from x64lens
raw discovery in the selected development targets. The observed disagreements
were primarily expected byte-candidate versus canonical-boundary differences.
That evidence supports preserving the dependency-free default while keeping an
optional decoder adapter as a future research seam.

Patch 043 also strengthens research integrity: target snapshots identify the
bytes actually analyzed, external parser diagnostics remain visible, and result
publication is transactional across interruption. Performance and RSS values
from this campaign remain smoke evidence and cannot support superiority claims.

## Sprint 9 Patch 044 research decision

Patch 044 preserves the dependency-free scanner as the product baseline and
records a bounded hybrid research path. Candidate-scoped decoding can validate
possible starts inside retained windows; deterministic candidate-validation or
region/chunk profiles may later improve throughput. Sprints 11 and 14 must measure
these against one-worker core analysis before integration or performance
claims. Patch 045 subsequently completed the Sprint 9 closeout and release-readiness review.

## Sprint 9 research decision

The Sprint 9 evidence does not justify replacing the dependency-free scanner with mandatory whole-image decoding. The retained research direction is a staged profile:

```text
loader-authoritative executable regions
  -> bounded terminator scan
  -> exact recognition
  -> semantic-exact classification
  -> optional candidate-scoped decoder validation
  -> optional semantic-decoded classification
```

This preserves independent scanner timing and RSS while allowing a later fixed-corpus campaign to measure how decoding retained candidate windows qualifies candidate starts and changes decoder-validated or semantic-decoded coverage, memory, startup cost, and deployment friction as separate outcomes. Deterministic target-level or candidate-validation parallelism is measured separately; the one-worker core remains the reference profile.

## Sprint 10 entry status

Patch 046 demonstrates the first evidence-aware semantic expansion after the
Sprint 9 provenance gate. Patch 047 adds the first exact register-transfer
family and strengthens common effect validation without increasing the fixed
arena or adding a runtime dependency. Patch 048 adds a bounded exact stack-
adjust family, explicit arithmetic flag effects, and public-artifact content
validation while preserving the same record, arena, capacity, and dependency
profile. Memory families remain open and must
follow the same
fixture, provenance, and scoring boundaries.

## Sprint 10 Patch 047 checkpoint

Patch 047 adds a bounded semantic-exact register-transfer family without changing
the 112-byte candidate record, 4,096-candidate capacity, or dependency-free
runtime profile. The family records operand roles and destination clobber facts
but remains unscored. Memory primitives remain the next evidence-model challenge.

## Sprint 10 Patch 048 checkpoint

Patch 048 adds one semantic-exact stack-adjust family without changing scanner authority, record size, candidate capacity, schema version, or runtime dependencies. The family records a known immediate-derived stack delta and explicit stack/flag effects but remains unscored and decoder-unvalidated.

This increases represented primitive breadth while retaining the dependency-free reference profile. It does not establish a runtime, RSS, coverage, or defensive-utility advantage; those remain fixed-corpus research questions for later sprints.

## Sprint 10 Patch 049 research posture

Patch 049 adds semantic-exact memory facts for six controlled qword base-plus-zero examples while preserving conservative fallback for SIB, displacement, `rsp`, and 32-bit forms. This improves the representational foundation for later corpus and coverage work, but it does not establish general memory-gadget coverage, decoded validity, lower RSS, or faster execution.

The fixed arena grows by 64 KiB while candidate capacity remains unchanged. Sprint 11 diagnostic measurement may characterize the effect, but Sprint 16/17 frozen measurement is required for release claims.


## Patch 050 research posture

Patch 050 improves semantic evidence quality rather than primitive count. Current return-ending families now record the implicit return stack read, `syscall; ret` records architectural `rcx`/`r11` overwrites, and `leave; ret` records the `rbp` overwrite while retaining unknown stack delta. The family coverage table makes fixtures, fallbacks, false-positive boundaries, and score disposition reviewable as one contract.

At the Patch 050 boundary, the new Sprint 10 families remained unscored. Patch
051 subsequently calibrates ordered two-pop argument control to 95 and positive
aligned stack adjustment to 35; transfer and memory remain unscored. Patch 053
owns the broader capability reassessment, including PIE-versus-DSO reporting,
CET/IBT/SHSTK property evidence, overlapping executable-segment count semantics,
and remaining score-policy questions before Sprint 15 freezes the campaign corpus.


## Sprint 10 Patch 052 corrective update

Patch 052 corrects the Patch 051 effect and gate findings without expanding the
primitive catalog. Full-width syscall descriptors, the zero-immediate return
boundary, contracted text separators, canonical memory side-car reconciliation,
numeric score-policy mutation gates, and strict-lint availability are permanent
validation surfaces. Patch 053 remains the architecture/capability reassessment;
Patch 054 closes Sprint 10; Sprint 11 is complete after Patch 061.


## Sprint 10 Patch 053 benchmark-informed roadmap update

Patch 053 adopts a twenty-two-sprint roadmap. Sprint 11 begins diagnostic measurement early enough to falsify performance assumptions and identify capability gaps. Those provisional results may redirect Sprints 12 through 14 and are never merged into the frozen campaign. Sprint 15 freezes the corpus, schema/extractor, runner, baselines, commands, task definitions, and environment strata; Sprint 16 owns the preview pilot and Sprint 17 owns publication-grade comparison. Sprints 18 through 22 complete triage, automation, case study, replication, and release.

The release does not require full decoding, JOP/COP/SROP, chain generation, symbolic execution, other architectures, or other file formats. It does require honest task definitions, measurable residual gaps, loader/mitigation precision, reproducible experiments, and bounded claims.


## Sprint 10 Patch 054 closeout update

Patch 054 closes Sprint 10 without changing analyzer behavior, schema, capacity,
decoder policy, or worker policy. It reconciles the public twenty-two-sprint
chronology, adds maintained roadmap and closeout gates, records the
checksum-manifest co-location rule and retrospective, and activates Sprint 11
diagnostic measurement. The Sprint 11 corpus is provisional development
evidence; Sprint 15 remains the confirmatory campaign freeze.


## Sprint 11 Patch 055 research posture

Patch 055 measures process and report behavior without modifying the analyzer.
The diagnostic runner preserves tool/target identity, commands, outputs,
failures, timer-floor samples, and Linux child resource usage in one complete
campaign tree. Its rows are development evidence and remain outside the frozen
preview/publication datasets.

The task review narrows one earlier assumption: the current public CLI has no
scanner-only output-suppression path, and gadget/analyze JSON is a command-
identity parity pair over the same report body. The project will not manufacture
three workloads from two implemented commands. A scanner-only profile and any
broader integrated-triage condition remain evidence-gated design decisions.

This preserves the research value of the dependency-free core. Sprint 11 can
now determine whether output cost, target size, baseline work scope, or a true
capability gap should drive the next implementation choice without contaminating
the Sprint 15-frozen campaign.

## Sprint 11 Patch 056 research posture

Patch 056 turns corpus construction into reproducible diagnostic evidence
without changing the analyzer. The first matrix provides controlled compiler,
optimization, requested role, and hardening variation while retaining exact
source, license, command, tool, environment, and output identity.

The corpus is intentionally small and mutable. It can reveal output-cost,
loader-role, mitigation, semantic, and baseline-definition gaps, but it cannot
support superiority or representativeness claims. Patch 057 first corrects the
measurement-integrity findings. Patch 058 adds normalized baseline adapters;
Patch 059 corrects their campaign binding and establishes the stage-zero plane;
Patch 060 uses the resulting rows to form the engineering gap register for
Sprints 12 through 14, and Patch 061 closes the diagnostic sprint.

## Sprint 11 Patch 057 research posture

Patch 057 adds no comparative result and no analyzer capability. It removes
known ways that diagnostic evidence could overstate target nonexecution, retain
undeclared compiler artifacts, hide failed cleanup, or delete an unsafe path.
Earlier development rows remain diagnostic and are not promoted. The corrected
method requires a new campaign identity before baseline comparison resumes.

## Sprint 11 Patch 058 research posture

Patch 058 adds no comparative result and no analyzer capability. Its adapters
preserve tool-native output and duplicate behavior, keep tool-specific metrics
separate, expose a canonical `pop rdi; ret` relation over represented instruction
text, and leave the raw executable-return-byte relation unavailable.

The standalone adapters authenticate supplied files and declared metadata but do
not consume a runner row, campaign manifest, child outcome, or capture record.
Patch 059 therefore owns the execution-to-normalization correction and the
stage-zero plane. Patch 060 owns corpus-backed rows, development summaries, and
the engineering gap register. Patch 061 closes Sprint 11 and hands the accepted
diagnostic priorities to Sprint 12.

## Sprint 11 Patch 059 research posture

Patch 059 adds no comparative result and no analyzer capability. It binds
baseline normalization to one authenticated runner row, derives the matched
x64lens relation from a retained complete report, records bounded runtime
closure, and calibrates address coordinates across manifest-bound roles. The
maintained 30-condition plan remains pre-execution authority.

All derived artifacts remain diagnostic, unfrozen, and publication-ineligible.
Native baseline populations, normalized relations, x64lens evidence-layer
populations, and binary presence remain distinct; baseline raw executable-byte
presence remains unavailable. Patch 060 runs the provisional campaign and
produces the engineering gap register. Patch 061 closes the sprint.

## Sprint 11 Patch 060 initial diagnostic posture

The Patch 060 authenticated partial-tool diagnostic checkpoint accounts for all
30 provisional
conditions while executing only the 12 available x64lens conditions; 18
pinned-baseline conditions remain unavailable. The 72 native rows comprise 12
warmups and 60 measured rows. All 60 measured x64lens rows were below the timer
floor and excluded from primary timing summaries; they were not reported as
zero or as a speed result. Six x64lens relation artifacts and two bounded
task-path closure artifacts were generated, while coordinate status remained
unavailable and cross-tool address intersections remained blocked.

The gap register selects PIE-versus-DSO identity and bounded GNU-property
evidence for Sprint 12 and exact-only semantic-role review for Sprint 13.
Candidate-scoped decoding and concurrency remain deferred, optional Sprint 14
ablations. These findings may redirect engineering work but remain diagnostic,
mutable, unfrozen, and publication-ineligible.


## Sprint 11 closeout research posture

Sprint 11 produced method-validating diagnostic evidence rather than a
comparative result. A later all-tools diagnostic replay, qualified only for an
evidence-local correction to the official ROPgadget 7.7 banner, executed 30/30
conditions and retained 180/180 successful process rows. Seventeen conditions
were above the 6,361,100 ns reliable floor and 13 were below it; all 12 x64lens
conditions were below that floor. The replay produced 24 normalized relations,
but two Python task-path closures failed and coordinate calibration failed. It
was not comparison-qualified and remained separate from the preregistered Patch
061 campaign boundary.

The partial-tool checkpoint and all-tools replay remain separate diagnostic,
unfrozen, and publication-ineligible evidence strata. Baseline-native records
are not a common gadget population, and native execution, normalization,
runtime closure,
coordinate qualification, and comparison status remain independent. Patch 061
turns those observations into explicit method gates. Sprint 12 proceeds through
loader validity and extended numbering, overlap/provenance, PIE-versus-DSO
identity, GNU-property evidence, and a private-fact diagnostic matrix. Positive
coordinate anchors and five complete task-path closures belong to a separate
comparison-qualification campaign. Any changed behavior receives a new
diagnostic campaign identity.

## Sprint 12 Patch 062 research checkpoint

Patch 062 resolves the first loader-precision tranche: ordinary program-header alignment, congruence, file/virtual ranges, executable-entrypoint containment, and explicit structurally validated unsupported outcomes for ELF64 extended numbering. The next evidence risk is overlapping executable-segment scan/count/provenance semantics, followed by PIE-versus-DSO and GNU-property indicators.

## Sprint 12 Patch 063-064 overlap and role decision

Patch 063 established lossless original-PHDR and candidate contributor
provenance. The subsequent diagnostic survey found no target with
executable-region overlap, same-slope repeated executable bytes, or repeated
exact identities across 3,115 sampled targets. Patch 064 therefore defers
normalization, preserves current ordering, counts, capacity, and output, and
records explicit reopening thresholds rather than implementing a high-risk
semantic change without measured value.

The Patch 064 candidate began the PIE-versus-DSO gate with an internal fact lattice over
ELF type, entrypoint, a bounded `PT_INTERP` carrier, `DF_1_PIE`, and validated
`DT_SONAME` string evidence. The public `ET_DYN` indicator remains unchanged.
Patch 064 did not pass validation. Patch 065 carried its role decision forward,
corrected the Patch 064 validation findings, and added the independently bounded
GNU-property IBT/SHSTK gate.

## Sprint 12 Patch 065-066 research checkpoint

Patch 065 established the bounded private GNU-property fact path for x86 IBT and
SHSTK but did not pass validation. Patch 066 corrects descriptor
alignment, overlap, corpus custody, ABI, and oracle defects,
then adds a 28-object role/property metamorphic preflight. The preflight is
controlled development evidence, remains unfrozen and publication-ineligible,
and changes no public report field. Patch 068 later adds the separate natural
and metamorphic private-fact matrix. At that historical boundary, bounded
external ELF reconciliation remained future work. Patch 069 added exact
`readelf -hW/-lW/-dW/-nW` reconciliation;
native/container private-fact parity must follow before any compatible public
`0.2.x` indicator is considered.

## Sprint 12 Patch 067 research checkpoint

Patch 067 does not broaden public mitigation reporting. It introduces
evidence-custody and oracle corrections and adds an assembly-emitted private
fact-probe ABI descriptor reconciled by an independent C contract. This
attestation covers probe record
interpretation only; it is a prerequisite, not product validation or publication
evidence. Patch 068 addressed the remaining custody boundary and added the separate
diagnostic agreement matrix. Diagnostic campaign rows remain unfrozen and
cannot support performance, RSS, coverage, or runtime-CET claims. Patch 069
subsequently corrects and authenticates that matrix and adds external
reconciliation.

## Sprint 12 Patch 068 research checkpoint

Patch 068 defined corrections for the remaining Patch 067 evidence-transaction
boundaries and introduced a 96-object private
role/GNU-property diagnostic agreement gate. Its 48 held-out natural
toolchain-produced objects remain separate from 48 controlled metamorphic
objects; an independent reader authors every expected vector, and the gate
requires three byte-identical probe results per object. Validation remains
pending at that historical boundary; Patch 068 required the Patch 069 and Patch
070 corrections. The matrix is diagnostic, unfrozen, publication-ineligible,
and not prevalence evidence. It does not authorize public fields or runtime-CET claims.
At the Patch 068 boundary, external comparison remained future work. Patch 069
added that comparison; native/container private-fact parity and a public-policy
decision remain open.

## Sprint 12 Patch 069 research checkpoint

Patch 069 addressed the Patch 068 evidence-custody defects and introduced an
authenticated 96-object private role/property matrix for its diagnostic scope.
It then retained 384 authenticated GNU
`readelf` executions and 1,728 field dispositions. The controlled result
contains 1,224 eligible matches and zero unexplained eligible mismatches, while
ambiguous, unavailable, and retained `not_eligible` cells—inapplicable for their
object/field combinations—remain outside the denominator. Patch 069 required
the further Patch 070 evidence-integrity correction. Patch 070 acceptance was
rejected; Patch 071 supplied the first correction, and Patch 072 supplies the
remaining correction plus acquisition and parity gates.

This is external diagnostic reconciliation, not public mitigation policy,
prevalence evidence, runtime-CET evidence, or publication evidence. Sprint 12
still requires qualified native/container private-fact parity and a separate
non-reinterpretive public-policy decision. Patch 072 implements the broader
outcome-blind natural-object acquisition gate.

## Sprint 12 Patch 070 review and Patch 071 corrective checkpoint

Patches 070, 071, 072, and 073 were not accepted at their respective first
returned review boundaries. Patch 071 preserves valid Patch 070 facts and
replaces those boundaries with identity-bound cleanup, an
outcome-complete version-2 authority, streaming 4 KiB output caps, and delivery
verification for regular-file path/hash/size/mode plus implied-directory
membership. This remains diagnostic, unfrozen, publication-ineligible method
evidence, not performance evidence.

At the Patch 071 boundary, external-natural acquisition and environment parity
were deferred to Patch 072. Patch 072 implements both gates; qualified native/
container parity evidence remains pending. The latest real campaign still
supports no x64lens single-run latency, RSS-superiority, generic gadget-count,
or normalized-coverage claim. Patch 073 executed the non-reinterpretive public-
policy gate as an explicit deferral. Patch 074 supplied the final custody and
parity-protocol correction but was superseded as the closeout candidate. Patch
075 introduced bounded private static text-relocation evidence, but its review
required the Patch 076 correction. Patch 076 implements distinct bounded private
RPATH/RUNPATH evidence, but its review required the Patch 077 correction. Patch
077 required the Patch 078 entry candidate. Patch 078's review required the
Patch 079 corrective and private task-value candidate. Patch 079's review
required Patch 080, which remains pending complete acceptance before the Sprint
13 handoff.


## Sprint 12 Patch 072 external-natural and parity checkpoint

Patch 072 changes no analyzer runtime or public schema. It hardens generation-
aware cleanup, process-tree deadline/reaping behavior, publication-transition
authority, duplicate-key rejection, and complete delivery custody. It freezes
selection of 48 installed-package natural objects after package, path, mode,
and ELF eligibility checks and before any x64lens, private fact-probe, or GNU
`readelf` outcome is consumed. The objects span four distinct source lineages;
the acquisition retains all 144 private probe runs, 192 public commands, 192
exact GNU `readelf` processes, and 864 field dispositions.

A separate same-byte 96-object gate compares native and container environments
while holding target, analyzer, fact-probe, and schema bytes constant. It keeps
5,184 private fields per environment and 384 paired public tuples. Package
source/build-origin and environment effects remain separate. Retained
diagnostic acquisition evidence and the two same-host logic-only parity planes
remain distinct; qualified native/container parity remains pending. All
retained planes are diagnostic, unfrozen, publication-ineligible, and
insufficient for
runtime-CET or public-field claims. Patch 073 recorded `defer`; Patch 074
preserves zero public role/property fields and the coarse PIE indicator. Patch
075 adds private static text-relocation evidence; Patch 076 implements the
distinct RPATH/RUNPATH tranche.


## Sprint 12 Patch 074 through Patch 078 reconciliation research posture

Patch 074 changes no runtime analyzer, include, or public schema path. It
implements corrections for the final evidence-custody and parity-protocol
findings by retaining descriptors through final topology verification,
rejecting hardlinks and late subtree mutation, binding external-natural
selection to inode identity, preserving parity executable modes and exact tree
membership, excluding native-plane ancestors from container mounts, and
limiting permission normalization to preflighted Git-tracked paths.

The public role/property decision remains `defer`. Text-relocation and separate
RPATH/RUNPATH evidence were not Patch 074 runtime output. Patch 075 introduced
bounded private static text-relocation evidence, and Patch 076 implements
distinct private RPATH/RUNPATH evidence. Neither adds a public field or runtime-
CET claim. Patch 076's review required the Patch 077 correction. Sprint 13
remains planned and activates only after complete Patch 080 acceptance. Patch
078 freezes private additive exact-pop roles, including Linux syscall argument
4 in `r10` and System V call argument 4 in `rcx`. Patch 079 executed the
deterministically presentation-ordered task-value gate. Patch 080 records the
LC-08B private-retention and public/score-projection deferral decision. All
Sprint 11-12 campaign observations remain diagnostic and cannot be promoted
into the Sprint 15-frozen confirmatory dataset.


## Sprint 12 Patch 076 research posture

Patch 076 turns runtime search-path uncertainty into bounded private evidence
without turning path strings into loader or security conclusions. The 36-object
matrix separates carrier presence, exact values, malformed input, unsupported
capacity, external presence comparison, and public non-projection. Native and
container facts remain separate evidence planes. No performance, prevalence,
runtime resolution, safety, or exploitability claim follows from this tranche.

## Sprint 12 Patch 077 historical research update

Patch 077 added no new measured capability. It converted the Patch 076 review
findings into durable transaction, comparator, parity, and evidence gates while
preserving the private dynamic-metadata results. These were development
correctness facts, not publication performance, coverage, or mitigation-
prevalence evidence.

## Sprint 13 Patch 078 research update

Patch 078 adds no measured capability and changes no analyzer runtime or public
schema. Its private register-role authority defines questions for Patch 079
deterministically presentation-ordered task-value qualification; it does not authorize runtime-semantic,
public-field, score, performance, coverage, or mitigation-prevalence claims.

## Historical Sprint 13 Patch 079 checkpoint

Patch 079 corrected the remaining Patch 078 acceptance tooling and ran the
preregistered register-role task-value gate. `generic_control`,
`sysv_call_arguments`, and `linux_syscall_arguments` qualify only as private
task-value evidence; `syscall_number` and `stack_pivot` remain deferred, with
existing runtime semantics and scores unchanged. The
patch added no runtime family, score, public field, decoder, worker, or schema
change. Its review required Patch 080.

## Sprint 13 Patch 080 checkpoint

Patch 080 corrects the complete Patch 079 acceptance finding set and implements
the first private additive role side-car. Three facets qualify privately; public
projection and score changes remain deferred. Patch 081 may run the ordered
two-pop role-tuple pilot or the next independently measured Sprint 13 gate after
Patch 080 acceptance.

## Sprint 13 Patch 081 decision

The first ordered two-pop consumer pilot does not justify another runtime representation. All 30 structural pairs reconcile, but existing `stack_pop_order` facts already satisfy the frozen tasks. The roadmap therefore retains the current exact family and moves the next semantic or consumer addition behind a new incremental-value gate.
