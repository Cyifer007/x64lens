# Sprint 12 Patch 065 Validation

## Status

Historical implementation-candidate validation record. Patch 065 did not pass
independent validation and required Patch 066. Patch 066 subsequently required
Patch 067, which required Patch 068; Patch 068 in turn required the Patch 069
corrective and external-reconciliation candidate, which required Patch 070.
Patch 070 was rejected after acceptance validation. Patch 071 required further
correction, and Patch 072's returned review rejected acceptance. Patches 070,
071, 072, and 073 were not accepted at their respective first returned review
boundaries. Patch 073 delivered the first custody/isolation correction and
policy deferral. Patch 074 was a superseded Sprint 12 closeout candidate. Patch
075 is active, owns the remaining correction plus private static text-relocation
evidence, and still requires complete acceptance; Patch 076 implements
distinct RPATH/RUNPATH evidence. The
[Patch 066 validation plan](sprint-12-patch-066-validation.md) preserves that
intervening boundary, and the
[Patch 067 validation plan](sprint-12-patch-067-validation.md) preserves a
subsequent historical candidate boundary, and the
[Patch 068 validation plan](sprint-12-patch-068-validation.md) preserves the
next historical candidate boundary, and the
[Patch 069 validation plan](sprint-12-patch-069-validation.md) preserves the
next historical candidate boundary, and the
[Patch 070 validation record](sprint-12-patch-070-validation.md) preserves the
rejected boundary. Use the
[Patch 076 validation record](sprint-12-patch-076-validation.md) for current
validation expectations; the
[Patch 073 validation record](sprint-12-patch-073-validation.md) preserves the
first custody/isolation correction and policy-deferral boundary; the
[Patch 071 validation record](sprint-12-patch-071-validation.md) preserves its
historical boundary.

## Review outcome

Patch 065 did not pass acceptance. Validation identified descriptor-relative GNU
property alignment, non-identical carrier-overlap rejection, corpus repair
identity/byte continuity, binary-role harness ABI alignment, copied-read-only
regression-fixture behavior, and oracle defects. Patch 066 addressed those
findings but required the further Patch 067 correction.
Patch 067 in turn required the Patch 068 correction, which subsequently
required Patch 069 and then Patch 070.

## Purpose

Validate the Patch 064 corrective work and the bounded private GNU-property
IBT/SHSTK evidence layer without adding public report fields or changing schema
`0.2.0`.

## Source contract

Patch 065 is defined against exact committed Patch 064 source
`d9b73dce2b34bebc1230171115d307206d33dead`.

## Corrective gates

```bash
make patch064-corrective-regression-smoke
make provisional-corpus-ready
make provisional-corpus-verify
```

The corrective smoke rejects the unencodable PHDR address form and qword
immediate-to-memory overflow forms, requires complete `PT_INTERP` and
`DT_SONAME` validation, enforces the binary-role summary-only boundary and the 64-byte summary-growth ceiling,
requires the GNU-property parser to revalidate each canonical carrier's retained
offset and size before reading it, authenticates all non-mode corpus facts before
repair, prevents hard-link chmod redirection, and proves permission normalization
does not follow links into generated evidence trees. The corrected public-output
oracle invokes the relevant analyzer commands and compares retained text and JSON
bytes rather than inferring reporter parity from internal facts.

## Binary-role gate

```bash
make sprint12-binary-role-smoke
```

Expected result:

```text
sprint12-binary-role-smoke: ok cases=21 states=5 malformed=7 unsupported=1 summary_bytes=264 classifier_bounds=1
```

The gate covers empty and interior-NUL interpreter paths, every SONAME carrier,
duplicate/conflicting role evidence, classifier bounds, and all five private
role states.

## GNU-property gate

```bash
make sprint12-gnu-property-oracle-smoke
make sprint12-gnu-property-smoke
```

Expected results:

```text
sprint12-gnu-property-oracle-smoke: ok cases=8 malformed=9 canonical_duplicates=1
sprint12-gnu-property-internal: ok cases=25 states=4 carriers=32 contributors=64 summary_bytes=264 context_bytes=3160 alignments=2 ordering=1
sprint12-gnu-property-smoke: ok private_cases=25 oracle_cases=8 public_pairs=3 malformed=8 unsupported=2 schema=unchanged alignments=2 ordering=1
```

The internal harness covers:

- no evidence;
- IBT-only and IBT+SHSTK facts;
- exact duplicate carriers and original contributor identity;
- unknown properties and feature bits;
- identical and conflicting duplicates;
- wrong owner and wrong note type;
- four- and eight-byte note-stream alignment, the ELF64
  `PT_GNU_PROPERTY` eight-byte requirement, and exact-duplicate alignment
  reconciliation;
- truncation, bad widths, inner and outer padding, overlap,
  descriptor size and property ordering, range-versus-cap precedence, note floods, and all implementation caps.

The independent standard-library oracle authors controlled ELF64 inputs,
executes `mitigations`, `gadgets --format json`, and `analyze --format json`, and
requires byte-identical public output when only private feature bits change.
Malformed and unsupported cases emit no partial stdout.

## Full native validation

```bash
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test
make sprint12-phdr-validity-smoke
make sprint12-overlap-provenance-smoke
make sprint12-overlap-decision-smoke
make sprint12-binary-role-smoke
make sprint12-gnu-property-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make section-label-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
make system-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

## Docker and parity

Record the selected Docker context and daemon before validation, then run:

```bash
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

Native and container results must agree. Docker Desktop and native Ubuntu
Docker are separate environment strata.

## Preserved contracts

- candidate capacity remains 4,096;
- candidate 4,097 fails before stdout with exit code 6;
- malformed parser failures emit no partial stdout;
- program headers remain executable authority;
- current aggregate metrics remain distinct: `raw_candidate_count`,
  `exact_pattern_count`, `semantic_candidate_count`,
  `unknown_candidate_count`, and `scored_candidate_count`;
- current evidence kinds remain `raw_only`, `exact_suffix`, and
  `semantic_exact`; `decoder_validated` and `semantic_decoded` remain reserved
  and unimplemented;
- no public JSON or text field changes;
- no new mandatory runtime dependency, decoder, or worker profile is added.

## Known limitations

GNU-property facts remain private development evidence. They do not prove that
CET is enabled at runtime, that every indirect branch is protected, or that a
binary is safe or exploitable. The Patch 068 natural/metamorphic private-fact
matrix remains diagnostic, unfrozen, and publication-ineligible. Bounded
external ELF reconciliation was future work at the Patch 065 boundary; the
Patch 069 candidate added exact `readelf -hW/-lW/-dW/-nW` reconciliation.
Patch 071 supplied the first evidence-gate correction, and Patch 072 carried
the remainder and added the environment-parity protocol. Patch 072's returned
review rejected acceptance. Patch 073 delivered the first custody/isolation
correction and recorded the public-policy decision as `defer`; Patch 074 was a
superseded closeout candidate. Patch 075 owns the remaining correction plus
private static text-relocation evidence. Corrected actual native/container
parity and Patch 075 acceptance remain pending; Patch 076 owns the planned
distinct RPATH/RUNPATH tranche.
