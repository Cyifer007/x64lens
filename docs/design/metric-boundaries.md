# Metric Boundaries

## Purpose

x64lens must keep raw scanner facts, exact pattern facts, semantic primitive facts, and score facts separate. This prevents misleading benchmark claims and avoids turning noisy byte-level output into overstated exploitability conclusions.

## Metric layers

| Metric | Meaning | Implemented stage |
|---|---|---|
| `raw_candidate_count` | Return-terminated byte windows found by the scanner. | Sprint 3 |
| `ret_count` | Raw candidates ending in `ret`. | Sprint 3 |
| `ret_imm16_count` | Raw candidates ending in `ret imm16`. | Sprint 3 |
| `exact_pattern_count` | Raw candidates with a recognized exact suffix pattern. | Sprint 3 |
| `semantic_candidate_count` | Candidates classified into semantic primitive classes. | Sprint 4, Patch 015 |
| `unknown_candidate_count` | Candidates intentionally left unclassified. | Sprint 4, Patch 015 |
| `scored_candidate_count` | Candidates assigned a usefulness score. | Sprint 5 target |
| `primitive_coverage` | Binary-level availability of useful primitive classes and controlled-register coverage. | Sprint 4 initial text summary, Sprint 5 JSON target |

## Why separation matters

A raw candidate may be a real useful gadget, a valid but unhelpful return path, or an unaligned byte sequence inside another instruction. Counting all of those as semantic primitives would overstate tool value.

A pattern label may identify a suffix such as `ret imm16` or `pop rdi; ret`, but a suffix label alone does not fully validate the entire candidate window.

A semantic primitive should mean the classifier can justify a specific primitive claim, such as argument-register control, syscall-number control, stack pivot, or syscall trigger.

A score should only be attached after semantic facts exist.

## Benchmark reporting rule

Benchmark rows should avoid a single generic `gadget_count` field when multiple meanings exist. Prefer explicit fields:

```text
raw_candidate_count
exact_pattern_count
semantic_candidate_count
unknown_candidate_count
scored_candidate_count
```

This makes comparisons against ROPgadget, Ropper, and ropr more honest, because each tool may define a gadget differently.

## Reviewer-facing rule

Do not claim that x64lens has better gadget coverage unless the comparison defines:

- what counts as a gadget,
- whether unaligned candidates are counted,
- whether exact suffix patterns are counted,
- whether semantically useful primitives are counted,
- whether output size and formatting are included in runtime.

## Sprint impact

Patch 015 implements the first semantic-count layer in text output and benchmark smoke TSVs. `x64lens gadgets` now emits raw candidate count, exact pattern count, semantic primitive count, unknown candidate count, per-class semantic counts, and register coverage separately.

Sprint 5 JSON should expose the same separation with explicit `limitations`. Sprint 10 research benchmarks should compute summary statistics over these separate fields rather than collapsing them into one count.
