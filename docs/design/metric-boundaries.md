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

## Current analysis-completeness metrics

Schema `0.2.0` adds command-level completion facts without redefining candidate
populations:

| Metric | Meaning | Current status |
|---|---|---|
| `candidate_capacity` | Maximum candidate records available for the run. | Implemented; currently 4096. |
| `candidate_count` | Candidate records emitted in the report. | Implemented; equals `raw_candidate_count`. |
| `candidate_truncated` | Whether report emission intentionally stopped before enumeration completed. | Implemented field; current successful reports are `false`. |
| `candidate_dropped_count` | Candidates excluded from an emitted report, when known. | Implemented with a known flag; current successful reports use known zero. |
| `regions_scanned` | Executable regions completed by the scanner. | Implemented. |
| `regions_total` | Loader-derived executable regions presented to the scanner. | Implemented. |
| `analysis_complete` | Whether bounded candidate enumeration completed over all presented regions. | Implemented as `analysis.complete`. |

Candidate-capacity exhaustion still produces no report, so it is not represented
as an emitted truncated result. The scanner stops on the 4097th candidate and
does not continue to measure a dropped total.

## Per-candidate provenance state

Patch 041 adds provenance fields without adding or redefining aggregate counts.
Every current candidate identifies raw presence, exact-suffix presence, semantic
source, validator identity, matched suffix range, and full-sequence-validity
state. `full_sequence_valid` remains unknown until decoder evidence exists.

## Planned decoder metrics

Later Sprint 9 work may add, where implemented:

| Metric | Meaning |
|---|---|
| `decoder_validated_count` | Candidates validated as complete instruction sequences from a selected start. |
| `semantic_exact_count` | Semantic candidates justified by exact suffix rules. |
| `semantic_decoded_count` | Semantic candidates justified by decoded instruction facts. |

New metrics are additive. They do not redefine historical counts or the Patch
040 completion fields.

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

## Dynamic metadata counts

`dynamic_entry_count` is not a gadget count and must not be mixed with raw,
exact, semantic, unknown, validated, or scored candidate counts. It is a bounded
mitigation-metadata count: the number of `Elf64_Dyn` records inspected before
the checked table ended or `DT_NULL` was encountered. It exists to explain the
scope of the dynamic-table evidence used for bind-now and future RELRO work.

## Sprint 8 Patch 034 section-label boundary

Section labels are annotation metadata. They must not be counted as discovered candidates, exact pattern matches, semantic primitives, validated gadgets, scored gadgets, or exploitability evidence. A labeled gadget and an unlabeled gadget with the same address, bytes, terminator, pattern, semantic class, stack delta, and score are the same candidate for metric purposes.


## Sprint 8 Patch 035 label ambiguity boundary

Section labels are intentionally absent when section metadata is ambiguous. Missing labels must not be counted as unknown gadgets, failed semantic classification, or scanner incompleteness. Raw candidate count, exact pattern count, semantic primitive count, unknown candidate count, scored candidate count, register coverage, and score values remain independent of section-label availability.


## Sprint 9 Patch 040 completeness boundary

`analysis.complete` answers one narrow question: did the bounded scanner finish
all program-header-derived executable regions without emitting a truncated
candidate set? It does not mean:

- every candidate is decoder-valid,
- every useful gadget family is recognized,
- semantic classification is complete,
- mitigation metadata is complete,
- a binary is exploitable or safe.

For current successful reports:

```text
analysis.candidate_count == counts.raw_candidate_count
analysis.candidate_truncated == false
analysis.candidate_dropped_count_known == true
analysis.candidate_dropped_count == 0
analysis.regions_scanned == analysis.regions_total
analysis.complete == true
```

The exact-capacity report can therefore be complete at 4096 candidates. The
4097-candidate input is a command failure, not a truncated report, and remains
outside report-count datasets unless the failed row is recorded separately by a
benchmark or validation harness.


## Sprint 9 Patch 041 provenance boundary

Candidate evidence and candidate counts answer different questions:

```text
counts.raw_candidate_count
  how many raw candidate windows were retained

gadgets[i].evidence
  which evidence justifies facts for candidate i
```

`semantic_exact` does not mean decoder-valid. `analysis.complete` does not
upgrade candidate evidence. Scores continue to consume semantic facts and do
not consume or manufacture decoder validity.

## Patch 042 decoder-gap comparison metrics

The external comparison campaign adds development metrics without changing the
runtime JSON count model:

| Metric | Meaning |
|---|---|
| `raw_terminator_intersection_count` | Return terminator addresses observed by both x64lens and canonical objdump disassembly. |
| `x64lens_raw_not_objdump_count` | Byte-oriented x64lens terminators absent from objdump's canonical instruction boundaries. |
| `objdump_terminator_not_x64lens_count` | Canonical objdump return instructions absent from x64lens raw candidates. |
| `x64lens_exact_boundary_match_count` | Selected exact suffixes reproduced with the same start, terminator, and bytes by objdump. |
| `x64lens_exact_boundary_disagreement_count` | Selected exact suffixes not reproduced by the canonical boundary model. |
| `objdump_supported_unselected_count` | Canonical suffixes matching the current exact catalog but not selected by the one-record-per-terminator model. |
| `objdump_unsupported_sequence_count` | Canonical return-ending sequences outside the current exact catalog. |
| `x64lens_duplicate_terminator_count` | Additional x64lens records sharing an already-observed terminator address. |
| `x64lens_duplicate_exact_evidence_count` | Additional exact-evidence records sharing the same suffix start, terminator, and bytes. |
| `objdump_duplicate_return_terminator_count` | Additional canonical return instructions sharing an already-observed address. |
| `objdump_duplicate_canonical_sequence_count` | Canonical sequences sharing the same start, terminator, and bytes after normalization. |

These are comparison metrics, not new gadget populations in schema `0.2.0`.
They must not be added to raw/exact/semantic counts or interpreted as
exploitability. The raw disassembly and report artifacts remain necessary for
reviewing section coverage, canonicalization, and max-depth differences.
