# Sprint 12 Patch 067 Validation Plan

## Status

Historical corrective implementation-candidate validation plan. Patch 067
required Patch 068, which subsequently required Patch 069 and Patch 070. Patch
070 was rejected after acceptance validation. Patch 071 required further
correction, and Patch 072's returned review rejected acceptance. Patches 070,
071, 072, and 073 were not accepted at their respective first returned review
boundaries. Patch 073 delivered the first custody/isolation correction and
policy deferral. Patch 074 was a superseded Sprint 12 closeout candidate. Patch
075 introduced bounded private static text-relocation evidence, and Patch 076
implemented distinct private `DT_RPATH` and `DT_RUNPATH` carrier/value
evidence. Patch 076 was superseded by Patch 077. Patch 077's review required
Patch 078, whose review required the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080. The
[Patch 068 plan](sprint-12-patch-068-validation.md) and
[Patch 069 plan](sprint-12-patch-069-validation.md) preserve the intervening
historical boundaries. Current validation expectations are recorded in the
[Patch 084 validation record](sprint-13-patch-084-validation.md). The
[Patch 073 validation record](sprint-12-patch-073-validation.md) preserves the
first custody/isolation correction and policy-deferral boundary. The
[Patch 071 validation record](sprint-12-patch-071-validation.md) preserves its
historical boundary. The
[Patch 070 validation record](sprint-12-patch-070-validation.md) preserves the
rejected boundary.

## Scope

Patch 067 introduced corpus/private transaction and oracle corrections and added
development-only private fact-probe layout attestation. Subsequent validation
found remaining transaction and oracle gaps assigned to Patch 068; Patch 069
then corrected the remaining Patch 068 corpus and matrix custody defects, and
Patch 070 attempted the next development-evidence correction but was rejected.
Patch 071 corrected the first blocker set; Patch 072 carried the remaining
correction and private acquisition/parity work, Patch 073 delivered the first
custody/isolation correction and policy deferral, and Patch 074 was the
superseded closeout candidate. Patch 075 introduced private static
text-relocation evidence, but its review required the Patch 076 correction.
Patch 067 changes no public CLI, JSON field, schema version, candidate
metric, semantic class, score, or runtime dependency.

## Source precondition

Patch 067 is defined against exact committed Patch 066 source
`ea5885e9c2e8e66edd7c5730660ce975a3dd8dad`. Validate the candidate against that
public source boundary.

## Focused validation

```bash
make provisional-corpus-ready
make provisional-corpus-verify
make patch066-corrective-regression-smoke
make sprint12-role-property-layout-smoke
make patch065-corrective-regression-smoke
make sprint12-binary-role-smoke
make sprint12-gnu-property-oracle-smoke
make sprint12-gnu-property-smoke
make sprint12-role-property-metamorphic-smoke
```

Expected Patch 067 results:

```text
patch066-corrective-regression-smoke: ok membership=1 root_binding=1 mode_rollback=1 private_fields=4 abi_mutation=1 layout_authority=1
sprint12-role-property-layout-smoke: ok qwords=24 fields=21 descriptor_bytes=192 mutations=2
```

The existing focused role/property gates must continue to report their maintained
case counts. The metamorphic gate must execute all 112 public command invocations.
Across the 56 JSON-producing `gadgets` and `analyze` paths, it must recursively
reject the maintained private role/property key vocabulary, including exact
private keys and the `property_`, `gnu_property`, `ibt_`, and `shstk_` prefixes.
The 28 `info` and 28 `mitigations` paths also receive bounded text-vocabulary checks; the JSON paths retain recursive private-key checks.

## Corpus transaction acceptance

The corrective gate must prove:

1. a member added after semantic verification is rejected before any mode
   change;
2. replacing the caller-visible corpus root name is rejected while both the
   displaced authenticated tree and foreign replacement remain unmodified;
3. the controlled injected final-verifier failure restores the original root and
   affected member modes;
4. ordinary authenticated mode-only drift still repairs and fully verifies.

## ABI and layout acceptance

The private layout gate must:

- assemble its descriptor directly from `include/structs.inc`;
- reconcile all 21 consumed field values and three descriptor-header qwords;
- reject a descriptor-version mutation;
- reject a field-offset mutation;
- link the descriptor into the development fact probe but not the analyzer.

This reconciliation attests the C/NASM layout and the development probe's record
interpretation only. Parser and classifier facts, analyzer behavior, and public
reporting remain separate validation surfaces.

The binary-role harness must check callee-entry alignment dynamically. Removing
both `sub rsp, 8` and `add rsp, 8` must fail the maintained source-shape oracle
and the rebuilt runtime harness.

## Full validation

```bash
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test
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

Record the selected Docker context and daemon before running:

```bash
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

Native Ubuntu Docker and Docker Desktop remain separate environment strata.

## Preserved contracts

- candidate capacity remains 4,096;
- candidate 4,097 returns exit code 6 before stdout;
- malformed parse failures emit no partial stdout;
- program headers remain executable mapping authority;
- the current aggregate metrics remain distinct: `raw_candidate_count`,
  `exact_pattern_count`, `semantic_candidate_count`,
  `unknown_candidate_count`, and `scored_candidate_count`;
- current evidence kinds remain `raw_only`, `exact_suffix`, and
  `semantic_exact`; `decoder_validated` and `semantic_decoded` remain reserved
  and unimplemented;
- private role/property facts remain absent from public text and JSON;
- the analyzer remains dependency-free, decoder-free, one-worker, bounded, and
  deterministic.

## Deferred work

Patch 068 added the subsequent private-fact diagnostic agreement gate for 48
held-out natural objects and 48 controlled metamorphic objects. Patch 069 added
authenticated external ELF reconciliation (`readelf -hW/-lW/-dW/-nW`).
Positive coordinate anchors, native/container private-fact parity, and any
public-policy decision remain separate gates. No Patch 067 row is publication
evidence.
