# Sprint 12 Patch 066 Validation Plan

## Status

Historical implementation-candidate validation plan. Patch 066 required the
Patch 067 corrective candidate, which subsequently required Patch 068 and then
Patch 069 and Patch 070. Patch 070 was rejected after acceptance validation,
Patch 071 required further correction, and Patch 072's returned review rejected
acceptance. Patches 070, 071, 072, and 073 were not accepted at their
respective first returned review boundaries. Patch 073 delivered the first
custody/isolation correction and policy deferral. Patch 074 was a superseded
Sprint 12 closeout candidate. Patch 075 introduced bounded private static
text-relocation evidence, and Patch 076 implemented distinct private `DT_RPATH`
and `DT_RUNPATH` carrier/value evidence. Patch 076's review required Patch 077.
Patch 077's review required Patch 078, whose review required the Patch 079 corrective and private task-value candidate, whose review required Patch 080. The
[Patch 067 validation plan](sprint-12-patch-067-validation.md) preserves that
historical boundary, and the
[Patch 068 validation plan](sprint-12-patch-068-validation.md) preserves the next
historical boundary, and the
[Patch 069 validation plan](sprint-12-patch-069-validation.md) preserves the
next historical candidate boundary, and the
[Patch 070 validation record](sprint-12-patch-070-validation.md) preserves the
rejected boundary. Current validation expectations are in the
[Patch 080 validation record](sprint-13-patch-080-validation.md); the
[Patch 073 validation record](sprint-12-patch-073-validation.md) preserves the
first custody/isolation correction and policy-deferral boundary; the
[Patch 071 validation record](sprint-12-patch-071-validation.md) preserves its
historical boundary.

## Purpose

Correct the Patch 065 parser, corpus-repair, test-oracle, and ABI findings, then
run the bounded 28-object private role/GNU-property metamorphic preflight without
adding public report fields or changing schema `0.2.0`.

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

The gate requires that:

- copied read-only corpus authorities are made writable only inside the isolated
  mutation fixture;
- GNU property entry alignment is descriptor-relative;
- non-identical carrier overlap is malformed;
- the binary-role harness obeys the SysV nested-call stack rule;
- a substituted corpus directory is not chmoded;
- bytes changed after semantic preflight are rejected before mode repair.

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
- current aggregate metrics remain distinct: `raw_candidate_count`,
  `exact_pattern_count`, `semantic_candidate_count`,
  `unknown_candidate_count`, and `scored_candidate_count`;
- current evidence kinds remain `raw_only`, `exact_suffix`, and
  `semantic_exact`; `decoder_validated` and `semantic_decoded` remain reserved
  and unimplemented;
- public schema and report fields remain unchanged;
- no mandatory decoder, worker, helper process, or runtime dependency is added.

## Known limitations and next gate

The 28-object preflight is controlled development evidence, not the wider
natural/metamorphic diagnostic matrix and not publication evidence. Patch 068
adds that separate gate for 48 held-out natural objects and 48 controlled
metamorphic objects. Patch 069 added bounded external ELF reconciliation
(`readelf -hW/-lW/-dW/-nW`). Patch 071 supplied the first evidence-gate
correction, and Patch 072 supplies the remainder and implements the parity
gate. Patch 073 delivered the first custody/isolation correction and policy
deferral, and Patch 074 was a superseded closeout candidate. Patch 075
introduced private static text-relocation evidence, but its review required the
Patch 076 correction. Patch 076 implements distinct private RPATH/RUNPATH
evidence. Patch 078's review required the Patch 079 corrective and private
task-value candidate; Patch 079's review required Patch 080. Complete acceptance
remains pending against the exact Patch 080 source.
Whole-batch workload ladders and process-tree RSS calibration remain separate
benchmark-method decisions.
