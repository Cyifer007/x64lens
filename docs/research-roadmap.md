# Research Roadmap

## Current checkpoint

Sprints 1 through 9 are complete. Sprint 10 is active through the Patch 053 architecture and capability reassessment candidate. Sprint 9 established report identity, completeness, schema `0.2.0`, candidate provenance, portable decoder-gap evidence, immutable campaign inputs, signal-safe publication and child cleanup, external-parser integrity, strict ZIP metadata policy, and the candidate-scoped decoder/parallelism decision. Patches 046 through 052 establish and harden ordered multi-pop, exact register-transfer, exact positive aligned stack-adjust, bounded structured memory effects, coarse and architectural effects, fixture contracts, selective scores, and fail-closed reconciliation. Patch 053 corrects the remaining Patch 052 harness/planning defects and separates diagnostic benchmarking from the frozen confirmatory campaign. The repository now provides:

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
- a repeatable checkpoint demonstration.

The `v0.1.0-dev` tag identifies the Sprint 6 integrated-prototype checkpoint. Patches 046 through 053 are later pre-release work, not a research release or evidence of universal performance or coverage superiority. Patch 054 closes Sprint 10 after Patch 053 local acceptance.

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

Status: smoke plumbing exists. Sprint 11 builds the high-resolution diagnostic runner and provisional corpus. Sprints 12 through 14 use diagnostic evidence for capability hardening. Sprint 15 freezes the campaign, Sprint 16 runs the preview pilot, and Sprint 17 runs publication-grade repeated trials.

### Stage 6: operational case study

Evaluate whether semantic and mitigation-aware reports improve triage of public network-facing infrastructure binaries.

Status: planned for Sprint 16 after the measurement and schema surfaces stabilize.

### Stage 7: publication and release

Freeze the evidence, reproduce the core workflow on a clean environment, audit claims, publish checksummed artifacts, and prepare the paper submission package.

Status: planned across Sprints 17 and 18.

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
Patch 054 remains Sprint 10 closeout.


## Sprint 10 Patch 053 benchmark-informed roadmap update

Patch 053 adopts a twenty-two-sprint roadmap. Sprint 11 begins diagnostic measurement early enough to falsify performance assumptions and identify capability gaps. Those provisional results may redirect Sprints 12 through 14 and are never merged into the frozen campaign. Sprint 15 freezes the corpus, schema/extractor, runner, baselines, commands, task definitions, and environment strata; Sprint 16 owns the preview pilot and Sprint 17 owns publication-grade comparison. Sprints 18 through 22 complete triage, automation, case study, replication, and release.

The release does not require full decoding, JOP/COP/SROP, chain generation, symbolic execution, other architectures, or other file formats. It does require honest task definitions, measurable residual gaps, loader/mitigation precision, reproducible experiments, and bounded claims.
