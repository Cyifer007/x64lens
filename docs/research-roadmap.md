# Research Roadmap

## Current checkpoint

Sprints 1 through 7 are validated through the Sprint 7 closeout checkpoint. Sprint 8 is active for mitigation and metadata depth. The repository now provides:

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
- a repeatable checkpoint demonstration.

The local `v0.1.0-dev` tag marks an integrated prototype. It is not a research release or evidence of universal performance superiority.

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

Status: implemented in stages. Patch 025 added deterministic malformed-input and candidate-capacity gates. Patch 028 added shared checked table arithmetic and table-end overflow probes. Patch 029 closes Sprint 7. Patch 030 opens Sprint 8 with bounded `PT_DYNAMIC` parsing for bind-now evidence, dynamic-entry count, and terminator state. Patch 031 adds the no, partial, and full RELRO evidence split. Patch 032 adds the first evidence-qualified canary indicator. Patch 033 adds the first stripped-status indicator and strict dynamic-string singleton policy. Patch 034 adds section-label annotations as metadata only, and Patch 035 hardens their rendering and ambiguity policy.

### Stage 2: candidate discovery and semantics

Discover bounded candidate windows, recognize exact suffixes, classify supported primitive types, preserve unknowns, and assign bounded heuristic scores.

Status: implemented for the initial exact-pattern set. Evidence provenance and broader primitives remain future work.

### Stage 3: evidence provenance and validity

Distinguish raw byte observations, exact suffix evidence, semantic-exact classification, decoder validation, and analysis completeness.

Status: planned for Sprint 9. This stage is the intended trigger for schema `0.2.0`.

### Stage 4: mitigation-aware triage

Connect static mitigation evidence and primitive coverage to defensive constraints without claiming vulnerability or exploitability.

Status: baseline indicators exist, Patch 030 adds bounded bind-now evidence, Patch 031 adds no, partial, and full RELRO reporting, Patch 032 adds an evidence-qualified canary indicator, Patch 033 adds a section-table stripped-status indicator, and Patch 034 adds section-label annotations. Evidence and triage work continues in later sprints.

### Stage 5: reproducible measurement

Use a fixed corpus, baseline versions, high-resolution timing, per-child resource measurements, raw result preservation, and generated summaries.

Status: smoke plumbing exists. Corpus and high-resolution infrastructure are planned for Sprints 11 and 12, with the comparative campaign in Sprint 13.

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
| Raw counts are noisy | Keep raw, exact, semantic, decoder-valid, unknown, and scored metrics separate. |
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

See [`roadmap-18-sprints.md`](roadmap-18-sprints.md) and [`research-release-plan.md`](research-release-plan.md).

## Patch 026 behavior oracle

The project fixed expected loader-level mitigation behavior before parser arithmetic was refactored. Patch 028 was accepted against the Patch 025 hostile-input campaign and the Patch 027-corrected mitigation matrix. Patch 030 then expands that oracle to bounded dynamic-table evidence, and Patch 031 uses it for RELRO refinement.


## Post-Sprint 7 research posture

Sprint 7 improves the trustworthiness of later measurements by hardening parser boundaries and deterministic oracles first. Patch 030 adds the first bounded Sprint 8 metadata reader, and Patch 031 composes that evidence into refined RELRO reporting. RQ1 performance work should continue to treat smoke timings as development evidence only. RQ2 semantic-value work should preserve raw/exact/semantic/scored boundaries. RQ3 operational-use work should emphasize evidence-qualified mitigation metadata in Sprint 8.

## Sprint 8 Patch 032 roadmap update

Mitigation-depth work now includes bounded dynamic-table evidence, refined RELRO states, and a bounded dynamic-string canary indicator. Remaining near-term metadata work should prioritize stripped-state and section labels as analyst annotations before moving into schema `0.2.0` evidence provenance.

## Sprint 8 Patch 033 roadmap update

Patch 033 completes the first stripped-status indicator and extends the mitigation oracle with dynamic string-table singleton and scan-cap boundary cases. Patch 034 completes section labels as annotations. Patch 035 resolves validation-discovered section-label hardening defects. Sprint 8 should pause for the historical review before Sprint 9 begins.

## Sprint 8 Patch 034 update

Patch 034 adds section-label annotations as metadata only, and Patch 035 hardens their rendering and ambiguity policy. This improves defender readability without changing the scanner, classifier, scoring, or mitigation authority boundaries. The result supports the later evidence-provenance schema transition because section-derived labels can be identified separately from loader-derived regions.


## Sprint 8 Patch 035 update

Patch 035 improves the reliability of section-derived annotations under hostile metadata. This keeps the research claim narrow: labels improve analyst readability, but all runtime authority and candidate counting still come from loader-derived regions and scanner/classifier records.
