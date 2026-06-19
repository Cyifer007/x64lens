# Evidence Provenance Model

## Purpose

x64lens needs to explain not only what a candidate was classified as, but also which evidence justified that classification. This model prevents exact suffix observations from being confused with fully decoded instruction sequences and gives future decoders a stable integration seam.

## Evidence layers

| Layer | Meaning | Current status |
|---|---|---|
| Raw candidate | A bounded byte window ending in a supported terminator byte sequence inside an executable file-backed region. | Implemented. |
| Exact suffix | A recognized byte suffix ending at the candidate terminator. | Implemented. |
| Semantic exact | A semantic class justified only by a supported exact suffix rule. | Implemented. |
| Decoder validated | A selected candidate start decodes into a valid complete instruction sequence ending at the terminator. | Future. |
| Semantic decoded | A semantic class derived from decoded instruction facts, side effects, and operand roles. | Future. |

These layers are additive. A decoded record does not erase the raw candidate or exact suffix observation.

## Side-car record direction

A future evidence record should be keyed by candidate index instead of expanding variable-length facts inside `gadget_record`.

Conceptual fields:

```text
candidate_evidence_record:
  candidate_index
  evidence_kind
  matched_suffix_start
  matched_suffix_length
  decoded_start
  decoded_length
  instruction_count
  full_sequence_valid
  confidence
  validator_id
```

Variable-length instruction text or operand lists should live in separate arena-backed storage and be referenced by offset/length pairs.

## Confidence rule

Confidence describes the evidence source, not exploitability.

Suggested values:

- `raw_only`,
- `exact_suffix`,
- `decoded_validated`,
- `semantic_exact`,
- `semantic_decoded`.

A candidate can be useful while still carrying `exact_suffix` evidence only. Reports must expose that distinction.

## Truncation and completeness

Research output must distinguish analysis completion from candidate validity.

Future summary facts should include:

```text
candidate_capacity
candidate_truncated
candidate_dropped_count
regions_scanned
regions_total
analysis_complete
```

If dropped count cannot be computed without continuing the scan, report `candidate_truncated: true` and make the limitation explicit. Silent truncation is not allowed for research release artifacts.

## Metric interaction

Provenance adds new metrics without redefining existing ones:

```text
raw_candidate_count
exact_pattern_count
semantic_candidate_count
decoder_validated_count
semantic_decoded_count
unknown_candidate_count
scored_candidate_count
```

The existing counts remain valid historical measures. Decoder-backed counts are additional layers.

## Classifier interaction

The classifier should prefer the strongest available evidence while keeping the source visible:

1. decoder-backed semantic rule, when available,
2. exact-suffix semantic rule,
3. `unknown_candidate` when neither justifies a claim.

A decoder disagreement must not be hidden. The candidate should retain raw and exact facts, record the decoder outcome, and avoid unsupported semantic promotion.

## Benchmark interaction

Coverage comparisons must state which evidence layer is compared. Raw terminator windows should not be compared directly with canonical decoder-backed gadgets without a reconciliation step.

## Release gate

The provenance model becomes part of the machine-readable contract before `v0.1.0-rc1`. Introducing it is the planned trigger for schema `0.2.0`.
