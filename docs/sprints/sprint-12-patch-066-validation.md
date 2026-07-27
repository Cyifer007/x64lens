# Sprint 12 Patch 066 Validation Plan

## Status

Current implementation-candidate validation plan. Patch 066 is not accepted
until clean native, Docker, parity, delivery, and independent Lane A validation
complete against the exact source.

## Purpose

Correct the Patch 065 parser, corpus-repair, test-oracle, ABI, private-backup,
and evidence-delivery findings, then run the bounded 28-object private
role/GNU-property metamorphic preflight without changing public output.

## Source contract

Patch 066 is defined against committed Patch 065 source
`5e1387e1771a16172b05b736afa5162229f74e4a`.

## Corrective gates

```bash
make patch065-corrective-regression-smoke
make patch064-corrective-regression-smoke
make provisional-corpus-ready
make provisional-corpus-verify
```

Expected focused correction:

```text
patch065-corrective-regression-smoke: ok readonly_fixture=1 descriptor_alignment=1 partial_overlap=1 abi_alignment=1 directory_identity=1 post_preflight_bytes=1
```

The gate proves that:

- copied read-only corpus authorities are made writable only inside the private
  mutation fixture;
- GNU property entry alignment is descriptor-relative;
- non-identical carrier overlap is malformed;
- the binary-role harness obeys the SysV nested-call stack rule;
- a substituted corpus directory is not chmoded;
- bytes changed after semantic preflight are rejected before mode repair.

The corrected private package separately requires:

```text
private-overlay-manager-smoke: ok ... signal_inventory=1 backup_signal=1
```

## GNU-property gates

```bash
make sprint12-gnu-property-oracle-smoke
make sprint12-gnu-property-smoke
```

Expected results:

```text
sprint12-gnu-property-oracle-smoke: ok cases=9 malformed=10 canonical_duplicates=1
sprint12-gnu-property-internal: ok cases=26 states=4 carriers=32 contributors=64 summary_bytes=264 context_bytes=3160 alignments=2 ordering=1
sprint12-gnu-property-smoke: ok private_cases=26 oracle_cases=9 public_pairs=3 malformed=9 unsupported=2 schema=unchanged alignments=2 ordering=1
```

The added positive case places a GNU property descriptor at an absolute file
offset congruent to four modulo eight while preserving descriptor-relative
entry alignment. The added negative case uses partially overlapping `PT_NOTE`
carriers and requires malformed exit `5` with empty stdout across
`mitigations`, `gadgets`, and `analyze`.

## Metamorphic preflight

```bash
make sprint12-role-property-metamorphic-smoke
```

Expected result:

```text
sprint12-role-property-metamorphic-smoke: ok objects=28 pairs=12 mutants=4 roles=3 property_states=4 deterministic=28 public_commands=84 schema=unchanged
```

The preflight requires state invariance across canonical and exact-dual carrier
encodings, exact contributor deltas, deterministic repeats, four single-axis
mutant outcomes, successful public-command execution for valid objects, and
malformed failure before stdout for the ordering mutant. The development fact
probe is not a product dependency or public report producer.

## Full native validation

```bash
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test

make patch065-corrective-regression-smoke
make sprint12-phdr-validity-smoke
make sprint12-overlap-provenance-smoke
make sprint12-overlap-decision-smoke
make sprint12-binary-role-smoke
make sprint12-gnu-property-smoke
make sprint12-role-property-metamorphic-smoke

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

Record the selected Docker daemon and context, then run:

```bash
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

Native Ubuntu Docker and Docker Desktop remain separate environment strata.
The role/property preflight must produce the same private facts in the selected
native and container strata.

## Preserved contracts

- candidate capacity remains 4,096;
- candidate 4,097 fails with exit `6` before stdout;
- malformed parser failures emit no partial stdout;
- program headers remain executable authority;
- raw, exact, semantic-exact, unknown, and scored populations retain their
  meanings;
- public schema and report fields remain unchanged;
- no mandatory decoder, worker, helper process, or runtime dependency is added.

## Known limitations and next gate

The 28-object preflight is controlled development evidence, not the wider
held-out confirmation and not publication evidence. After acceptance, the next
role/property gate should use the larger held-out matrix, bounded `readelf -n`
comparison, and native/container fact parity. Whole-batch workload ladders and
process-tree RSS calibration remain separate benchmark-method decisions.
