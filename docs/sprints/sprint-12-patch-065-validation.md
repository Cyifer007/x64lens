# Sprint 12 Patch 065 Validation Plan

## Status

Historical implementation-candidate validation record. Patch 065 was committed
locally but independent validation required a corrective patch. Patch 066
preserves the accepted private-fact architecture and owns the current corrected
commands, expected banners, and acceptance decision.

## Review outcome

Patch 065 did not pass acceptance. Review confirmed descriptor-relative GNU
property alignment, non-identical carrier-overlap rejection, corpus repair
identity/byte continuity, private-backup signal safety, binary-role harness ABI
alignment, and copied-read-only regression-fixture defects. See the
[Patch 066 validation plan](sprint-12-patch-066-validation.md).

## Purpose

Validate the Patch 064 corrective work and the bounded private GNU-property
IBT/SHSTK evidence layer without changing public output or schema `0.2.0`.

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
- raw, exact, semantic-exact, unknown, and scored counts retain their meanings;
- no public JSON or text field changes;
- no new mandatory runtime dependency, decoder, or worker profile is added.

## Known limitations

GNU-property facts remain private development evidence. They do not prove that
CET is enabled at runtime, that every indirect branch is protected, or that a
binary is safe or exploitable. After Patch 066 acceptance, held-out role/property
confirmation remains diagnostic, unfrozen, and publication-ineligible. Bounded
`readelf -n` reconciliation and native/container fact parity must follow before
a separate review decides whether compatible public `0.2.x` indicators are
justified.
