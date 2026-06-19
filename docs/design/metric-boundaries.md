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
| `scored_candidate_count` | Candidates assigned a usefulness score. | Sprint 5 Patch 017 |
| `primitive_coverage` | Binary-level availability of useful primitive classes and controlled-register coverage. | Sprint 4 text summary, Sprint 5 JSON output |

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


## Sprint 4 closeout note

Patch 015 validation confirmed that the text reporter and scanner smoke benchmark preserve raw, exact, semantic, and unknown counts separately. On real binaries such as `/bin/ls`, many `alignment` records may be exact byte-suffix observations rather than confirmed instruction-boundary gadgets. This is acceptable for the current stage only because the output remains explicit about the scanner model and no exploitability verdict is emitted.


## Sprint 5 scoring boundary

Patch 017 adds `scored_candidate_count` and per-candidate score fields. A scored candidate is not the same thing as an exploitable gadget. It means the current model assigned a relative utility value to a candidate whose semantic class was justified by the classifier.

`unknown_candidate` records remain unscored. JSON should represent those scores as `null`, while the internal score field remains `0` as a sentinel.

## Patch 018 validation boundary

Patch 018 strengthens validation without changing metric meaning. `tools/validate-json-report.py` checks relationships between raw, exact, semantic, unknown, and scored counts. `tools/system-binary-smoke.sh` validates those relationships on real system binaries while avoiding brittle distro-specific count expectations.

This preserves the research boundary: system-binary smoke output is regression evidence, not publication evidence. Publication claims still require the benchmark methodology's controlled corpus, repeated runs, baseline tool versions, and summary statistics.


## Analyze metric boundary

Sprint 6 Patch 022 does not create new metric definitions. `analyze` reports the same raw candidate, exact pattern, semantic candidate, unknown candidate, and scored candidate metrics that already exist in the `gadgets` pipeline. Benchmark scripts should distinguish gadget-discovery comparisons from end-to-end analyze report comparisons.
