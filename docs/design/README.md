# Design Notes

This directory records future-facing architecture seams that should be understood before implementation changes begin.

- [`nasm-rationale.md`](nasm-rationale.md): why the assembly-first engine is being evaluated and how to avoid unsupported claims.
- [`parser-safety-and-fuzzing.md`](parser-safety-and-fuzzing.md): hostile-input invariants, deterministic mutation testing, regression policy, and future fuzzing gates.
  - Implemented Patch 025 surfaces: `tools/malformed-elf-smoke.py`, `make malformed-smoke`, `make capacity-smoke`, and ADR 0013.
- [`mitigation-fixture-matrix.md`](mitigation-fixture-matrix.md): compiler-independent valid and malformed program-header layouts used by the mitigation oracle, including Patch 030 dynamic-table evidence, Patch 031 RELRO refinement, and Patch 032 canary indicators.
- [`decoder-roadmap.md`](decoder-roadmap.md): optional decoder integration without replacing the raw scanner.
- [`defensive-deployment-profile.md`](defensive-deployment-profile.md): reference runtime constraints for dependency-free, air-gapped, low-resource defensive deployment.
- [`primitive-effect-model.md`](primitive-effect-model.md): ordered pop and register-transfer relations, clobber, stack, side-effect, and scoring boundaries for Sprint 10 primitive expansion.
- [`evidence-provenance-model.md`](evidence-provenance-model.md): raw, suffix, semantic, decoder, completeness, and truncation evidence layers.
- [`metric-boundaries.md`](metric-boundaries.md): required separation between discovery, recognition, validation, semantic, score, and triage metrics.
- [`schema-evolution.md`](schema-evolution.md): current schema `0.2.0`, retained representative final-shape `0.1.0` compatibility, and future `0.2.x` evolution rules.
- [`decoder-gap-decision-gate.md`](decoder-gap-decision-gate.md): external decoder-gap evidence definitions and the embedded-decoder decision procedure.
- [`contributor-maintainability.md`](contributor-maintainability.md): maintainability expectations for NASM-heavy development.

These documents are architecture constraints, not implementation claims. Code, tests, schemas, and release artifacts must be updated when a planned seam becomes implemented behavior.

## Sprint 8 Patch 032 design note

The canary indicator is the first dynamic-string consumer. It must remain downstream of bounded `PT_DYNAMIC` parsing, file-backed `PT_LOAD` translation, and range validation. The indicator is intentionally narrower than full symbol recovery and should be refined later through symbol-table or relocation evidence rather than by broadening unchecked string scanning.

## Sprint 8 Patch 033 stripped-status update

Patch 033 reports stripped status as an evidence-qualified mitigation metadata field. Text uses `Stripped indicator: unknown`, `stripped`, or `not stripped`; JSON uses `mitigations.stripped` values `unknown`, `stripped`, or `not_stripped`. The section-header scan is bounded and never selects executable regions or candidate scan ranges. Duplicate `DT_STRTAB` and `DT_STRSZ` dynamic entries fail closed as malformed input so canary evidence is not order-dependent.

## Sprint 8 Patch 034 section-label update

Patch 034 adds section labels as optional annotations. Section names flow from bounded section-header and section-name string-table evidence. They do not change loader-derived executable regions, scanner ranges, semantic classes, or scores.

## Sprint 8 Patch 036 historical-findings hardening update

Patch 036 hardens implemented seams discovered during historical review. Byte-safe JSON escaping, section-label file-offset/virtual-address agreement, benchmark artifact sanity checks, Docker context filtering, validator cross-field checks, and temporary-output isolation are now implementation constraints. Larger provenance, decoder-gap, and publication-benchmark work remains governed by the future design notes rather than being folded into this cleanup patch.


## Comparator and evidence-integrity notes

See ADR 0023 for the Patch 037 decision to add automated `readelf` comparison,
optional external mitigation/metadata helpers, and finite benchmark-row
validation.

## Sprint 9 bounded acceleration design

- [`candidate-scoped-decoder-and-parallelism.md`](candidate-scoped-decoder-and-parallelism.md)
  defines the optional decoder and deterministic concurrency gates established
  by Patch 044.

## Sprint 10 reading path

1. [`../architecture.md`](../architecture.md)
2. [`../adr/0032-ordered-multi-pop-foundation.md`](../adr/0032-ordered-multi-pop-foundation.md)
3. [`../adr/0033-exact-register-transfer-effects.md`](../adr/0033-exact-register-transfer-effects.md)
4. [`../adr/0034-bounded-stack-adjust-and-public-artifact-content-policy.md`](../adr/0034-bounded-stack-adjust-and-public-artifact-content-policy.md)
5. [`primitive-effect-model.md`](primitive-effect-model.md)
6. [`../semantic-taxonomy.md`](../semantic-taxonomy.md)
7. [`../json-schema.md`](../json-schema.md)
8. [`../sprints/sprint-10-plan.md`](../sprints/sprint-10-plan.md)
9. [`../sprints/sprint-10-patch-047-validation.md`](../sprints/sprint-10-patch-047-validation.md)
10. [`../sprints/sprint-10-patch-048-validation.md`](../sprints/sprint-10-patch-048-validation.md)
11. [`../roadmap-18-sprints.md`](../roadmap-18-sprints.md)
