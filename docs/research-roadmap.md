# Research Roadmap

## Current checkpoint

Sprint 5 Patch 019 is the current implementation candidate. The repository now has a working NASM-first ELF64 x86_64 foundation, loader-relevant executable-region mapping, baseline mitigation reporting, raw gadget candidate scanning, arena-backed candidate storage, exact suffix pattern labels, first-pass semantic classification, semantic summary counts, register coverage, initial scoring, JSON output for gadgets, scanner smoke benchmark plumbing, validation hardening, and baseline comparison smoke scaffolding.

## Stage 1: CSC-732 foundation

Build a working NASM-first ELF64 x86_64 analyzer.

Primary outcome: functional scaffold and semester-grade tool.

Current status: complete through ELF64 validation, program-header analysis, mitigation baseline reporting, raw scanner foundation, exact suffix pattern matching, and first-pass semantic classification.

## Stage 2: benchmarkable scanner

Compare x64lens against ROPgadget, Ropper, and ropr.

Primary outcome: reproducible performance and coverage data.

Current status: development smoke benchmark exists. Research-grade comparison remains future work.

## Stage 3: semantic primitive scoring

Move beyond raw gadget counts into semantic utility.

Possible research question:

> Can semantic gadget usefulness be measured more accurately through side-effect and primitive-coverage analysis than through raw gadget count?

Current status: exact pattern IDs and the first Sprint 4 semantic classifier are implemented and validated. Patch 015 populates semantic classes, register bitmaps, stack deltas, side-effect flags, semantic counts, unknown counts, and register coverage for supported exact suffix patterns. Patch 017 begins scoring from these internal facts directly.

## Stage 4: mitigation-aware exploitability modeling

Connect NX, PIE, RELRO, canaries, RWX segments, CET, and IBT to plausible exploit strategy constraints.

Possible research question:

> How do modern mitigations change the practical usefulness of available gadget sets?

Current status: baseline PIE, NX stack, RWX load segment, dynamic linking, and baseline RELRO are implemented. Full RELRO, canary indicators, section labels, and CET/IBT indicators remain future work.

## Stage 5: compiler and hardening comparison

Evaluate how compiler flags and hardening profiles change semantic primitive availability.

Variables:

- GCC vs Clang,
- `-O0`, `-O1`, `-O2`, `-O3`, `-Os`,
- PIE vs non-PIE,
- stack protector variants,
- partial vs full RELRO,
- CET flags,
- LTO,
- static vs dynamic linking.

## Stage 6: network infrastructure triage

Connect the tool to network-facing infrastructure and operational security.

Possible research question:

> Can static binary exploitability analysis improve prioritization of network-exposed services and infrastructure software?

This stage is the strongest CSC-773 bridge because it ties binary hardening and primitive availability to advanced cyberinfrastructure defense.

## Stage 7: dissertation-scale work

Potential dissertation directions:

- semantic exploitability scoring,
- binary hardening effectiveness metrics,
- architecture-specific primitive modeling,
- AI-assisted analyst interpretation over deterministic low-level facts,
- network appliance binary triage,
- firmware-scale exploitability modeling,
- CET/IBT impact on code-reuse exploitability.

## Expanded sprint mapping

The near-term expanded plan is documented in `docs/roadmap-12-sprints.md`.

The guiding sequence is:

1. scanner correctness,
2. semantic classification,
3. scoring and JSON,
4. semester checkpoint,
5. mitigation hardening,
6. primitive expansion,
7. hardening corpus,
8. research-grade benchmarks,
9. integrated analysis,
10. paper and release preparation.

## Reviewer-readiness additions

The current roadmap should explicitly answer likely reviewer objections:

| Concern | Roadmap response |
|---|---|
| NASM is hard to justify | Add NASM rationale and measure performance/memory instead of assuming superiority. |
| Assembly parser safety | Add malformed-input regression and mutation smoke testing. |
| Exact patterns are brittle | Keep exact suffix patterns as a stage and add a decoder roadmap. |
| Raw counts are noisy | Separate raw candidates, exact patterns, semantic primitives, unknown candidates, and scores. |
| Tool is hard to maintain | Add contributor maintainability guidance and module extension notes. |
| x86_64 is narrow | Treat architecture scope as an explicit limitation and future engine seam. |

These additions refine the roadmap without changing the near-term implementation order.

## Patch 018 validation maturity checkpoint

Patch 018 improves the evidence trail before broader baseline comparisons begin. The repository now has reusable validation for JSON report invariants, controlled-fixture scoring facts, real-system-binary smoke behavior, Docker environment availability, and patch bundle hygiene.

This keeps Sprint 5 aligned with the research contract: reproducible claims require tool versions, schema versions, commands, corpus details, environment metadata, raw results, and summary statistics. Patch 018 is not a publication benchmark; it is the validation foundation needed before Sprint 6 checkpoint work and later Sprint 10 research benchmarks.


## Patch 019 benchmark scaffolding note

Patch 019 adds comparison scaffolding before research-grade benchmark execution. The goal is to prove that tool versions, exact commands, target hashes, run counts, timing, memory, and x64lens JSON-derived counts can be captured consistently. These rows remain development evidence until baseline tool definitions and corpus selection are finalized.


## Sprint 5 Patch 020 update

Patch 020 adds development-environment dependency checks, Ubuntu onboarding instructions, optional baseline-tool installation guidance, and broader default system-binary coverage for the baseline smoke harness.


## Sprint 5 research contribution

Sprint 5 created the first machine-readable evidence path for RQ1 and RQ2 by adding schema-versioned JSON, explicit count boundaries, scoring fields, system-binary smoke validation, and baseline smoke TSV generation. These outputs remain development evidence until the full benchmark methodology is run with controlled corpus documentation, repeated runs, exact tool versions, and preserved raw results.
