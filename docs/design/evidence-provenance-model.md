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

## Implemented side-car record

Patch 041 implements a dense fixed-size evidence array keyed implicitly by the
matching `gadget_record[]` index. The index is not duplicated inside the record,
so array position cannot disagree with a stored key.

Implemented fields:

```text
candidate_evidence_record:
  evidence_flags
  semantic_source
  validator_id
  full_sequence_state
  matched_suffix_offset
  matched_suffix_length
```

The implemented record contains no decoded instruction sequence. Future
variable-length instruction text or operand lists should live in separate
arena-backed storage and be referenced by offset/length pairs.

## Evidence-kind vocabulary

The schema evidence-kind values are:

- current producer values: `raw_only`, `exact_suffix`, and `semantic_exact`;
- reserved future values: `decoder_validated` and `semantic_decoded`.

These values describe the evidence source, not exploitability or a numeric
confidence score.

A candidate can be useful while still carrying `exact_suffix` evidence only. Reports must expose that distinction.

## Truncation and completeness

Research output must distinguish analysis completion from candidate validity.

Schema `0.2.0` now includes command-level summary facts:

```text
candidate_capacity
candidate_count
candidate_truncated
candidate_dropped_count
candidate_dropped_count_known
regions_scanned
regions_total
analysis_complete
```

Current successful reports are complete, untruncated, and have a known dropped
count of zero. Candidate-capacity exhaustion still fails before output, because
the scanner does not continue far enough to compute a truthful dropped count.
A future partial mode must make unknown dropped state explicit and preserve the
no-silent-truncation rule.

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

Patches 040-041 established schema `0.2.0` and per-candidate raw,
exact-suffix, and semantic-exact provenance. Patches 042-045 supplied external
comparison evidence for the decoder decision without adding runtime decoder
facts. Decoder-backed provenance remains a reserved additive layer for a future
optional profile.


## Sprint 9 Patch 040 foundation

Patch 040 separates command-level evidence identity from candidate-level
evidence provenance:

```text
analysis_summary
  one record per command invocation
  report type, command, options, capacity, progress, completeness

candidate_evidence_record[]
  implemented dense record per candidate index
  raw-candidate, exact-suffix, semantic-exact, validator, and future decoder facts
```

This avoids overloading `gadget_record` and prevents `analysis.complete` from
being misread as decoder validity. A report can be complete for all raw
candidate windows while every candidate still carries only exact-suffix or
unknown semantic evidence.

`gadgets` and `analyze` share one report type (`analysis`) and one report body,
but preserve command identity. Patches 042-045 used this envelope for external
decoder-gap measurement rather than broadening primitive families.


## Sprint 9 Patch 041 current JSON evidence

Current producers emit one `evidence` object for every candidate. `kind` names
the strongest represented evidence layer while separate fields preserve the
underlying facts:

```text
raw_only
exact_suffix
semantic_exact
decoder_validated      reserved for future implemented evidence
semantic_decoded       reserved for future implemented evidence
```

For Patch 041, `full_sequence_valid` is always `null`. This is intentional: a
complete command report can enumerate every raw candidate while still lacking
instruction-boundary validation for each candidate.

## Patch 042 comparison-artifact provenance

The runtime candidate evidence side-car remains unchanged. Patch 042 adds a
separate development artifact layer for decoder-gap research:

```text
x64lens JSON + target bytes + objdump disassembly
  -> decoder-gap comparison JSON
  -> fixed-column summary TSV
  -> run manifest and decision input
```

Every campaign records analyzer, canonical validator, objdump executable, and
target SHA-256 hashes; tool versions; exact commands; max depth; raw reports;
raw disassembly; smoke-level timing/RSS; and duplicate/canonicalization facts.
These artifacts may qualify or challenge an exact-suffix interpretation, but
they do not mutate the original raw-candidate, exact-suffix, semantic-exact,
unknown-candidate, or scored facts.

A canonical-boundary disagreement is not silently relabeled as a false positive.
The source of disagreement remains explicit because objdump is section-derived
external evidence while x64lens scanning remains program-header-authoritative.

## Patch 043 immutable campaign provenance

Development comparison artifacts now distinguish the requested source path from
the retained immutable target snapshot. The snapshot SHA-256 and size identify
the bytes analyzed by both x64lens and the external comparison tool. Source path
and source-file metadata remain descriptive lineage; they are not allowed to
certify different bytes.

External parse diagnostics and interruption outcomes are campaign evidence, not
runtime candidate facts. The default runtime remains decoder-free, and any
future decoder-backed record remains additive to the candidate-index side-car.

## Sprint 9 closeout status

The candidate-index side-car is implemented for raw, exact-suffix, and semantic-exact evidence. Current `full_sequence_valid` remains unknown because the core does not decode complete instruction sequences. Decoder-validated and semantic-decoded states remain reserved additive layers.

The preferred future experiment validates only retained candidate windows after bounded scanning and exact recognition. This preserves raw scanner evidence and cost measurements while bounding decoder work. Decoder disagreement must remain visible rather than deleting or rewriting raw and exact facts.

## Sprint 10 ordered structural facts

Patch 046 adds exact structural facts to the existing raw candidate record
without changing the evidence side-car size:

```text
pattern_register_count
pattern_register_order
```

These facts describe the recognized suffix and are validated before semantic
promotion. They do not change `full_sequence_valid`, which remains unknown for
exact-suffix evidence. JSON `stack_pop_order` therefore belongs to the exact
recognition layer, while `controls`, `clobbers`, stack delta, and
`side_effects` belong to semantic classification.

For multi-pop candidates, the external validator checks that ordered metadata,
exact suffix bytes, evidence length, controlled-register set, and semantic facts
agree. The candidate remains `semantic_exact`, not decoder validated.
