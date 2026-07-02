# Design Notes

This directory records future-facing architecture seams that should be understood before implementation changes begin.

- [`nasm-rationale.md`](nasm-rationale.md): why the assembly-first engine is being evaluated and how to avoid unsupported claims.
- [`parser-safety-and-fuzzing.md`](parser-safety-and-fuzzing.md): hostile-input invariants, deterministic mutation testing, regression policy, and future fuzzing gates.
  - Implemented Patch 025 surfaces: `tools/malformed-elf-smoke.py`, `make malformed-smoke`, `make capacity-smoke`, and ADR 0013.
- [`mitigation-fixture-matrix.md`](mitigation-fixture-matrix.md): compiler-independent valid and malformed program-header layouts used by the mitigation oracle, including Patch 030 dynamic-table evidence.
- [`decoder-roadmap.md`](decoder-roadmap.md): optional decoder integration without replacing the raw scanner.
- [`evidence-provenance-model.md`](evidence-provenance-model.md): raw, suffix, semantic, decoder, completeness, and truncation evidence layers.
- [`metric-boundaries.md`](metric-boundaries.md): required separation between discovery, recognition, validation, semantic, score, and triage metrics.
- [`schema-evolution.md`](schema-evolution.md): schema `0.1.0` compatibility rules and the planned `0.2.0` transition.
- [`contributor-maintainability.md`](contributor-maintainability.md): maintainability expectations for NASM-heavy development.

These documents are architecture constraints, not implementation claims. Code, tests, schemas, and release artifacts must be updated when a planned seam becomes implemented behavior.
