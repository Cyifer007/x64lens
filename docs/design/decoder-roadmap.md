# Decoder Roadmap

## Purpose

The current scanner is byte-oriented and the current matcher recognizes exact suffix templates. This design is intentionally narrower than full x86_64 decoding. The decoder roadmap defines how validity evidence can be added without replacing the raw scanner or weakening the dependency-light research design.

## Current implemented layers

```text
executable region
  -> raw terminator-centered candidate
  -> exact suffix pattern
  -> conservative semantic-exact class
  -> heuristic score
```

A pattern label proves only that the suffix bytes match the documented template. It does not prove that every byte in the printed backward window belongs to one valid instruction sequence from the window start.

## Preserved facts

Future decoder work must preserve:

- raw candidate offsets and windows,
- exact suffix pattern IDs,
- semantic-exact classes,
- unknown candidates,
- raw and exact benchmark metrics,
- independent scanner timing.

Decoder output is additional evidence, not a replacement history.

## Side-car integration model

Recommended record families:

```text
gadget_record[]
  raw scanner facts

candidate_evidence_record[]
  evidence kind, matched suffix range, completeness, validator identity

decode_record[]
  selected start, decoded length, instruction count, validity, operand facts
```

Variable-length instruction or operand data should use arena-backed offset/length references rather than pointers embedded in persistent output structures.

## Decoder responsibilities

A future decoder may:

- validate a selected candidate start,
- decode through the terminator,
- reject invalid or truncated encodings,
- report instruction count and length,
- report operand roles and memory access,
- report controlled and clobbered registers,
- support decoder-backed semantic classification.

A decoder must not own:

- file mapping,
- ELF identity,
- program-header parsing,
- executable-region discovery,
- raw terminator enumeration,
- mitigation analysis,
- score policy,
- output formatting.

## External validation before embedding

Before adding a runtime decoder dependency, use controlled fixtures and external tools to measure the gap:

- `objdump -d -Mintel`,
- ROPgadget,
- Ropper,
- ropr,
- optional radare2 or another decoder-backed validator.

The purpose is not to force exact count equality. The purpose is to identify why candidates differ and whether the difference affects x64lens claims or defensive usefulness.

## Sprint 9 decision evidence

Sprint 9 should measure at least:

- raw candidates that do not decode from the selected start,
- exact suffix matches embedded in unrelated instruction bytes,
- semantically useful baseline gadgets not represented by current patterns,
- differences caused by max-depth definitions,
- duplicate or canonicalization differences,
- runtime and memory cost of external decoder validation.

## Embedded decoder decision gate

An embedded decoder is approved only when all conditions are met:

1. a quantified correctness or coverage gap affects a release claim or user-facing result,
2. the dependency and license are acceptable,
3. decoder facts fit the side-car model,
4. raw scanner operation remains independently available,
5. decoder-backed and pattern-backed metrics remain separate,
6. runtime and memory impact can be measured as an ablation,
7. failure and malformed-input behavior are covered by tests.

## Integration options

### Optional external verification mode

A development or research helper may invoke an external decoder and write comparison artifacts. This keeps the runtime binary dependency-light but is not suitable as the only source of release-time facts.

### Optional linked decoder adapter

A future build profile may link a mature decoder behind an internal adapter. This requires clear build metadata and separate benchmark rows.

### Minimal internal decoder

A limited internal decoder may be justified for a tightly bounded instruction subset. This is high maintenance and should not be selected merely to preserve pure-assembly branding.

## Timeline

- Sprint 9 Patch 040: report identity and analysis-completeness envelope.
- Sprint 9 Patch 041: candidate-index provenance and exact-suffix evidence.
- Sprint 9 Patch 042: external objdump gap measurement and explicit decision gate.
- Sprint 9 Patch 043: immutable evidence, signal-safe publication, parser hardening, and a recorded decoder-free default with an optional adapter seam.
- Sprint 9 Patch 044: corrective campaign hardening and candidate-scoped decoder/parallelism gate.
- Sprint 9 Patch 045: closeout audit; no mandatory decoder implementation.
- Sprint 10: evidence-aware primitive expansion without requiring an embedded decoder.
- Sprint 11: diagnostic coverage evidence identifies whether a decoder profile is materially useful.
- Sprint 14: candidate-scoped decoder ablation and pre-freeze decision.
- Sprint 17: frozen coverage reconciliation reports any retained profile separately.
- Post-`v0.1.0`: broader decoder-backed analysis remains a primary research direction if not required earlier.

## Classification preference

When multiple evidence sources exist, the classifier should prefer the strongest justified source while reporting provenance:

```text
decoder-backed semantic fact
  > exact-suffix semantic fact
  > unknown candidate
```

A decoder disagreement must remain visible. The tool should not hide raw or exact facts simply because a stronger validator rejected semantic promotion.


## Patch 040 interaction

`analysis.complete` is deliberately decoder-neutral. It states that raw
candidate enumeration completed within capacity; it does not set
`full_sequence_valid` or promote semantic evidence. The candidate evidence
side-car remains the decoder integration point.


## Patch 042 measurement implementation

`tools/decoder-gap-smoke.py` is the first implemented external verification
surface. It preserves current x64lens JSON and raw objdump disassembly, then
separates:

- raw return-terminator overlap,
- x64lens byte terminators absent from canonical objdump boundaries,
- canonical objdump return terminators absent from x64lens raw output,
- exact-suffix start/byte agreement,
- duplicate x64lens terminators, duplicate exact-evidence keys, and duplicate
  canonical sequence keys,
- supported canonical alternatives not selected by the one-record-per-
  terminator report model,
- canonical return-ending sequences outside the current exact pattern catalog.

The tool records target, analyzer, canonical validator, and objdump hashes;
exact commands; versions; smoke-level wall time; and maximum RSS. It does not write decoder facts back
into `candidate_evidence_record`, change semantic classes, or alter scores.

The controlled fixture is a regression gate. Selected system binaries are a
research campaign whose counts are interpreted under
[`decoder-gap-decision-gate.md`](decoder-gap-decision-gate.md).

## Patch 043 decoder decision

The default `x64lens` binary remains decoder-free. This preserves the core
research variable and operational contract: freestanding NASM, direct syscalls,
small dependency surface, low startup/RSS potential, and straightforward
air-gapped or minimal-container deployment.

Decoder-backed facts remain useful, but they must be optional side-car evidence.
Any future adapter receives its own build identity, dependency and license
record, failure contract, malformed-input regression suite, and performance/RSS
ablation. It must not remove raw candidates or silently rewrite exact and
semantic-exact history.

## Patch 044 candidate-scoped refinement

The preferred future decoder boundary is bounded candidate validation rather
than whole-image decoding. The raw scanner first discovers terminators and
retains windows. An optional adapter may then try valid starts within each
window, emit `decode_record[]` side-car facts, and support semantic-decoded
classification. Raw discovery remains independently runnable and measurable.

Parallelism is a separate decision. Candidate-index validation is the lowest-
risk first seam; executable-region and chunk scanning require deterministic
ordering, overlap and deduplication rules, a global capacity contract, and
bounded per-worker memory. Sprint 12 and Sprint 13 own the measurement and
ablation gates before any default-runtime change.

## Patch 053 benchmark-informed decoder timeline

Sprint 11 diagnostic evidence should quantify which coverage disagreements
matter to the research tasks. Sprint 14 owns the optional candidate-scoped
decoder ablation. The reference analyzer remains decoder-free.

A decoder profile may proceed only when it preserves raw and exact evidence,
uses bounded retained candidate starts, records its dependency and license, and
shows a material correctness or task benefit relative to its binary-size,
startup, CPU, RSS, and hostile-input costs. Any accepted profile is frozen with
its own identity in Sprint 15 and measured separately thereafter.
