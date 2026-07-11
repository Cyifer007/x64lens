# ADR 0027: Candidate evidence side-car and contract hardening

## Status

Accepted for Sprint 9 Patch 041.

## Context

Patch 040 established schema `0.2.0`, command identity, and successful-analysis
completeness without changing raw, exact, semantic, unknown, or scored metric
meanings. The next Sprint 9 requirement is per-candidate provenance. That work
must not enlarge the scanner-owned `gadget_record` with decoder-specific or
variable-length state, and it must not imply that exact suffix evidence proves a
complete decoded instruction sequence.

Post-Patch-040 validation also identified contract and evidence-quality defects:

- multiple assembly helper frames, including the JSON reporter, did not
  maintain System V stack alignment before nested calls;
- the formal JSON Schema and the semantic validator enforced different current
  report rules;
- patch-bundle hygiene depended on selected archive-root prefixes;
- the capacity smoke accepted extra stderr lines after the expected diagnostic;
- focused JSON harnesses did not all apply the canonical current-report
  validator;
- benchmark summaries could merge rows produced by different tool or schema
  identities.

The runtime report path itself passed native and container validation. Patch 041
therefore combines the smallest provenance implementation with corrections to
the validation surfaces that establish trust in that implementation.

## Decision

### Dense candidate-index side-car

Add a fixed-size `candidate_evidence_record[]` allocated from the same
command-lifetime arena as `gadget_record[]`. The array is dense: record `i`
describes gadget record `i`. The index is not duplicated inside each record,
which avoids a second value that could contradict array position.

The initial 48-byte record stores:

```text
flags
semantic_source
validator_id
full_sequence_state
matched_suffix_offset
matched_suffix_length
```

Patch 041 materializes only facts already justified by the existing pipeline:

- every stored record is a raw candidate;
- a known pattern records exact-suffix evidence and its range inside the retained
  candidate byte window;
- a supported semantic class records `semantic_exact` provenance;
- validator identity is the raw scanner or exact-suffix matcher;
- full-sequence validity remains unknown.

The materializer runs after exact matching and semantic classification. It does
not scan, decode, classify, score, annotate sections, or emit output. Scoring and
all historical counts remain unchanged.

### JSON compatibility

Each current candidate report emits an `evidence` object with:

```json
{
  "kind": "semantic_exact",
  "raw_candidate": true,
  "exact_suffix": true,
  "semantic_source": "exact",
  "validator": "x64lens-exact-suffix",
  "matched_suffix_offset": 2,
  "matched_suffix_length": 2,
  "full_sequence_valid": null
}
```

The formal schema keeps `evidence` optional so reports produced by Patch 040
remain valid schema `0.2.0` documents. Current-producer validation uses
`--require-provenance` and requires evidence on every emitted candidate. This is
a backward-compatible `0.2.x` extension, not a new schema transition.

### Validator authority split

The Draft 2020-12 schemas are authoritative for document structure, required
fields, types, enums, and conditionals expressible in JSON Schema. The bundled
Python validator is additionally authoritative for arithmetic and
property-to-property invariants, including count reconciliation, region
progress, coverage/class agreement, suffix ranges, and current-producer
provenance completeness.

`make schema-compat-smoke` applies both layers to historical `0.1.0`, Patch 040
`0.2.0`, and current provenance-bearing `0.2.0` fixtures. `python3-jsonschema`
is a development and CI dependency only; the x64lens runtime remains
self-contained.

### Supporting corrections

- Correct every identified nested-call frame in the active command and reporting
  paths so `RSP` is 16-byte aligned before each System V `call`. This includes
  the JSON helper graph, numeric renderers, text-report helpers, arena mapping,
  and simple output/error wrappers; tail-call wrappers use `jmp` where no local
  return work remains.
- Make bundle-hygiene path matching independent of archive-root name and add
  synthetic regression archives.
- Compare capacity diagnostics byte-for-byte rather than matching one line with
  `grep`.
- Route successful JSON from malformed-input controls, mitigation fixtures, and
  section-label fixtures through the canonical validator.
- Group benchmark summaries by tool name, tool version, schema version, command,
  and target.
- Keep public documentation repository-facing and remove historical
  coordination narration from the affected closeout records.

## Alternatives rejected

### Expand `gadget_record`

Rejected because provenance and future decoder facts evolve independently from
raw scanner storage. Enlarging the raw record would couple the scanner to later
validation layers and make future variable-length decoder data harder to bound.

### Store an explicit candidate index in every side-car record

Rejected because the dense array position already supplies the key. A redundant
index would add memory and a new contradiction state without adding evidence.

### Require evidence in the formal `0.2.0` schema immediately

Rejected because Patch 040 already produced valid `0.2.0` reports. Making the
field formally required would retroactively invalidate those reports. The
current-producer validator provides the stronger requirement without breaking
same-version compatibility.

### Add target hashing or an embedded decoder in this patch

Rejected because target identity is a separate bounded provenance module and
decoder selection must follow measured gap evidence. Combining either concern
with the candidate side-car would obscure the acceptance boundary and increase
immediate attack surface.

## Consequences

Candidate semantics can now be traced to explicit machine-readable evidence
without changing candidate identity, counts, scores, executable-region
selection, or failure behavior. `analysis.complete` remains a statement about
bounded enumeration, while `full_sequence_valid: null` makes decoder uncertainty
visible per candidate.

The next Sprint 9 patch can measure decoder gaps against this stable provenance
surface. It should add comparison artifacts and a decoder decision record rather
than broadening primitive families or silently promoting exact evidence into
decoder validity.
