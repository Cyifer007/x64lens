# Decoder-Gap Measurement and Embedded-Decoder Decision Gate

## Purpose

This gate converts decoder concerns into reproducible evidence. It prevents a
full decoder from being added because of preference, branding, or raw count
differences that arise from incompatible definitions.

## Implemented measurement surface

Patch 042 provides:

```bash
make decoder-gap-smoke
make decoder-gap-campaign
```

The controlled smoke validates the hand-authored gadget fixture. The campaign
adds selected installed ELF64 x86_64 binaries when present. Generated evidence
is written under `tests/results/decoder-gap/` and remains outside public source
bundles.

Each run preserves:

- x64lens, Python, GNU time, and objdump version strings;
- analyzer, campaign implementation, controlled expectation, validator,
  Python, GNU time, objdump, and target SHA-256 hashes;
- exact campaign, analyzer, validator, and objdump commands;
- max depth;
- x64lens JSON and canonical schema/provenance validation;
- objdump disassembly;
- per-command wall-time and max-RSS smoke measurements;
- duplicate terminator and duplicate canonical-sequence counts;
- per-target comparison JSON;
- a fixed-column TSV and aggregate JSON manifest.

## Comparison definitions

### Raw terminator agreement

`raw_terminator_intersection_count` is the overlap between x64lens byte-oriented
return terminators and return instructions in objdump's canonical disassembly.

`x64lens_raw_not_objdump_count` is a **boundary disagreement**, not automatically
a false positive. The byte may be inside another canonical instruction, or
objdump may lack section-derived coverage for a loader-mapped range.

`objdump_terminator_not_x64lens_count` is a potential raw-scanner coverage gap.
It requires review of executable-region and section-coverage differences before
being called a scanner defect.

### Exact-suffix boundary agreement

An x64lens exact suffix agrees when objdump contains the same start address,
terminator address, and bytes as one canonical contiguous sequence under the
campaign's predecessor-byte limit.

A disagreement does not erase the raw or exact byte observation. It means the
external canonical disassembly did not reproduce that selected start as one
instruction sequence.

### Supported but unselected alternatives

x64lens currently stores one candidate record per terminator and one selected
exact pattern per candidate. Objdump may expose another supported suffix at the
same terminator, such as the single `ret` suffix beneath a selected `pop reg;
ret`. These are counted separately from unsupported instruction families.

### Unsupported canonical sequences

Canonical return-ending sequences outside the current exact-pattern catalog are
coverage observations. They are not automatically semantic primitives and do
not receive scores until Sprint 10 evidence, side-effect, and fixture rules are
satisfied.

## Controlled acceptance gate

The controlled fixture must preserve:

```text
raw candidates:                         11
exact patterns:                         11
semantic candidates:                    11
unknown candidates:                      0
scored candidates:                      11
objdump return terminators:             11
x64lens raw not in objdump:               0
objdump terminators not in x64lens:       0
x64lens exact boundary matches:          11
x64lens exact boundary disagreements:     0
candidate byte mismatches:                0
```

The fixture intentionally exposes supported-but-unselected `ret` alternatives.
That fact documents the one-record-per-terminator model; it is not a controlled
failure.

The controlled fixture must also report zero duplicate x64lens terminators,
zero duplicate exact-evidence keys, zero duplicate objdump return addresses, and
zero duplicate canonical sequence keys.

## Evidence completeness before a decision

An embedded-decoder decision requires all of the following:

1. a passing controlled campaign;
2. at least three selected system binaries with target hashes and preserved raw
   artifacts;
3. categorized disagreements rather than generic count differences;
4. manual review of representative boundary disagreements and unsupported
   canonical sequences;
5. external validator version and command provenance;
6. measured wall-time and RSS overhead for the validation path;
7. dependency and license review for any proposed decoder;
8. a design showing that decoder records remain side-cars and raw scanning stays
   independently available;
9. malformed-input and failure-mode tests for the proposed adapter.

## Decision outcomes

### Defer embedding

Choose this when gaps do not invalidate current claims, are primarily definition
or canonicalization differences, or the cost exceeds demonstrated value.
Continue using external comparison artifacts.

### Optional external verification mode

Choose this when decoder evidence is useful for research or operator review but
a runtime dependency is not justified.

### Optional linked decoder adapter

Choose this when a material correctness or coverage gap affects a release claim
and a mature decoder can remain behind a separate adapter and build profile.

### Minimal internal decoder

Choose this only for a tightly bounded instruction subset when the maintenance
burden is justified by measured evidence. Pure-assembly branding is not a valid
reason.

## Non-automatic rule

No single mismatch percentage automatically approves a decoder. The decision
must explain which user-facing or research claim is affected, which evidence
would become stronger, and what cost is introduced.

## Patch 043 recorded decision

The reviewed selected-system development campaign did not expose a canonical
return terminator absent from x64lens raw discovery. Its principal differences
were expected byte-oriented observations that did not begin at canonical
instruction boundaries. Those facts do not invalidate the documented raw,
exact-suffix, or semantic-exact claims.

The decision is therefore **defer mandatory embedding**. The default runtime
remains decoder-free and dependency-free. A future decoder may be implemented
only as an optional external or linked verification profile when a frozen corpus
demonstrates a material user-facing validity or semantic-coverage gap and when
license, binary-size, latency, RSS, malformed-input, and deployment costs are
measured as a separate stratum.

Patch 043 strengthens the evidence used by this decision: every comparison uses
one immutable target snapshot, objdump parse diagnostics are retained, and
result publication is transactional across ordinary failures, `SIGINT`, and
`SIGTERM`. The campaign remains development evidence and is not a publication
performance result.
