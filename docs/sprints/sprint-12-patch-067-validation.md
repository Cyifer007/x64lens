# Sprint 12 Patch 067 Validation Plan

## Scope

Patch 067 corrects the Patch 066 corpus/private transaction and oracle findings
and adds development-only private fact-probe layout attestation. It changes no
public CLI, JSON field, schema version, candidate metric, semantic class, score,
or runtime dependency.

## Source precondition

Apply to the exact committed Patch 066 source named by the delivery runbook.
Use either the complete Git patch or the authenticated final-file overlay, never
both.

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
case counts. The metamorphic gate must execute all 84 public command paths while
rejecting any nested `role_state`, `role_evidence`, `ibt_state`, `shstk_state`,
`property_*`, or GNU-property private key in schema `0.2.0` output.

## Corpus transaction acceptance

The corrective gate must prove:

1. a member added after semantic verification is rejected before any mode
   change;
2. replacing the caller-visible corpus root name is rejected while both the
   displaced authenticated tree and foreign replacement remain unmodified;
3. a final verifier failure restores the original root and member modes;
4. ordinary authenticated mode-only drift still repairs and fully verifies.

## ABI and layout acceptance

The private layout gate must:

- assemble its descriptor directly from `include/structs.inc`;
- reconcile all 21 consumed field values and three descriptor-header qwords;
- reject a descriptor-version mutation;
- reject a field-offset mutation;
- link the descriptor into the development fact probe but not the analyzer.

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
- raw, exact, semantic-exact, unknown, decoder-backed, and scored facts remain
  distinct;
- private role/property facts remain absent from public text and JSON;
- the analyzer remains dependency-free, decoder-free, one-worker, bounded, and
  deterministic.

## Deferred work

The 96-object held-out natural/metamorphic confirmation, bounded external note
comparison, positive coordinate anchors, native/container private-fact parity,
and any public-policy decision remain subsequent diagnostic gates. No Patch 067
row is publication evidence.
