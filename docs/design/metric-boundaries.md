# Metric Boundaries

## Purpose

x64lens keeps discovery, recognition, validation, semantics, scoring, and binary-level interpretation as separate metric layers. This prevents noisy byte observations from becoming overstated gadget or exploitability claims.

## Current metrics

| Metric | Meaning | Status |
|---|---|---|
| `raw_candidate_count` | Terminator-centered byte windows found in executable file-backed regions. | Implemented. |
| `ret_count` | Raw candidates ending in `ret`. | Implemented. |
| `ret_imm16_count` | Raw candidates ending in `ret imm16`. | Implemented. |
| `exact_pattern_count` | Raw candidates with a recognized exact suffix template. | Implemented. |
| `semantic_candidate_count` | Candidates assigned a supported semantic class. | Implemented. |
| `unknown_candidate_count` | Candidates deliberately left without a supported semantic class. | Implemented. |
| `scored_candidate_count` | Semantic candidates assigned a score by the current model. | Implemented. |
| `primitive_coverage` | Binary-level presence of implemented primitive classes and controlled registers. | Implemented. |

## Planned provenance metrics

Schema `0.2.0` should add, where implemented:

| Metric | Meaning |
|---|---|
| `decoder_validated_count` | Candidates validated as complete instruction sequences from a selected start. |
| `semantic_exact_count` | Semantic candidates justified by exact suffix rules. |
| `semantic_decoded_count` | Semantic candidates justified by decoded instruction facts. |
| `candidate_capacity` | Maximum candidate records available for the run. |
| `candidate_truncated` | Whether discovery ended before all executable bytes were examined because capacity was reached. |
| `candidate_dropped_count` | Additional candidates observed after capacity, when the scanner continues counting safely. |
| `regions_scanned` | Executable regions completed. |
| `regions_total` | Executable regions presented to the scanner. |
| `analysis_complete` | Whether the intended analysis completed without truncation or fatal unsupported state. |

New metrics are additive. They do not redefine historical counts.

## Why separation matters

A raw candidate may be:

- a valid and useful gadget,
- a valid but low-value return path,
- an exact suffix inside a longer valid instruction sequence,
- an unaligned byte sequence,
- an unsupported semantic form.

An exact suffix can justify a narrow pattern claim but not full-window validity. A semantic class can be justified by an exact rule or by decoder facts. A score can be assigned only after the semantic rule is known. A binary-level triage statement requires still more context.

## Count relationships

Current invariant:

```text
raw_candidate_count
  = semantic_candidate_count + unknown_candidate_count

exact_pattern_count <= raw_candidate_count
scored_candidate_count <= semantic_candidate_count
```

Future decoder counts may overlap exact counts, so they must not be added together as though they were disjoint unless the schema explicitly defines a partition.

## Benchmark reporting rule

Do not use an unlabeled `gadget_count` in research tables. Use the precise metric and evidence layer.

For comparisons with ROPgadget, Ropper, or ropr, document:

- terminator set,
- byte or instruction depth,
- aligned and unaligned behavior,
- invalid-instruction filtering,
- duplicate handling,
- canonicalization,
- output mode,
- whether semantic or mitigation work is included.

A baseline's reported gadget count is a tool-specific metric until reconciled.

## Score boundary

A score means relative utility under the current model. It is not:

- a probability of exploitation,
- a vulnerability severity,
- a binary-level risk score,
- evidence that a chain is constructible.

Unknown candidates remain unscored. Future decoder confidence, clobbers, memory dereferences, bad bytes, and mitigation context may influence score only after the corresponding facts exist.

## Binary-level triage boundary

A future triage summary is separate from per-candidate score. It may consume:

- mitigation evidence,
- primitive coverage,
- representative candidate quality,
- provenance,
- analysis completeness,
- limitations.

It must still avoid claiming exploitability without an independent vulnerability and runtime context.

## Smoke versus research evidence

System-binary smoke checks validate shape and invariants. Benchmark smoke checks validate measurement plumbing. Neither is publication evidence.

Publication tables require a fixed corpus, tool versions, commands, schema, repeated trials, environment metadata, raw results, and generated summaries.
