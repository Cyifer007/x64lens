# Research Roadmap

## Current checkpoint

Sprints 1 through 6 and Patch 024 are validated. Sprint 7 is active, and Patch 025 is the first hostile-input hardening candidate. The repository now provides:

- a NASM-first ELF64 x86_64 parser and read-only mapping path,
- program-header-authoritative executable regions,
- baseline mitigation facts,
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

Status: implemented in stages. Patch 025 adds deterministic malformed-input and candidate-capacity gates. Patch 028 adds shared checked table arithmetic and table-end overflow probes. Deeper metadata hardening remains for Sprint 8.

### Stage 2: candidate discovery and semantics

Discover bounded candidate windows, recognize exact suffixes, classify supported primitive types, preserve unknowns, and assign bounded heuristic scores.

Status: implemented for the initial exact-pattern set. Evidence provenance and broader primitives remain future work.

### Stage 3: evidence provenance and validity

Distinguish raw byte observations, exact suffix evidence, semantic-exact classification, decoder validation, and analysis completeness.

Status: planned for Sprint 9. This stage is the intended trigger for schema `0.2.0`.

### Stage 4: mitigation-aware triage

Connect static mitigation evidence and primitive coverage to defensive constraints without claiming vulnerability or exploitability.

Status: baseline indicators exist. Full RELRO, canary, stripped, section-label, evidence, and triage work spans Sprints 8 and 14.

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

The project fixed expected loader-level mitigation behavior before parser arithmetic was refactored. Patch 028 can therefore be evaluated for safety and equivalence against the Patch 025 hostile-input campaign and the Patch 027-corrected mitigation matrix.
