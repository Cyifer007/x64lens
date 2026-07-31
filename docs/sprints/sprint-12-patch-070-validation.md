# Sprint 12 Patch 070 Validation

## Purpose

Patch 070 corrects the remaining Patch 069 evidence-transaction, comparator,
private-package, and Make prerequisite defects, then adds the development-only
whole-batch transaction-conformance pilot required before below-floor batching
can support a throughput experiment.

## Unchanged product contracts

- tool version `0.1.0-dev`;
- schema version `0.2.0`;
- program-header executable authority;
- candidate capacity 4,096;
- candidate 4,097 returns exit 6 before stdout;
- malformed parse failures emit no partial stdout;
- dependency-free, decoder-free, one-worker reference runtime;
- no public PIE/DSO, IBT, or SHSTK field.

## Focused validation

```bash
make provisional-corpus-ready
make provisional-corpus-verify
make patch069-corrective-regression-smoke
make sprint12-batch-transaction-smoke
make sprint12-role-property-heldout-smoke
make sprint12-role-property-readelf-smoke
```

Expected Patch 070 banners:

```text
patch069-corrective-regression-smoke: ok retained_semantics=1 root_size=1 root_replacement=1 handlers=1 cleanup=2 make_prerequisites=4 private_leaks=8 authorities=2 readelf_exits=1 overlap_anchor=1

sprint12-batch-transaction-smoke: ok cases=27 executions=81 stable_hashes=81 failure_positions=13 signals=8 stage_residue=0 survivors=0 fd_growth=0 timing_claims=0

sprint12-role-property-heldout-smoke: ok objects=96 natural=48 metamorphic=48 probe_runs=288 public_commands=384 fact_fields=18 expected_vectors=96 observed_vectors=96 unique_natural=48 provisional_targets=24 provisional_overlap=0 edge_layouts=24 property_overlap_positive=1 malformed=12 schema=0.2.0

sprint12-role-property-readelf-smoke: ok objects=96 commands=384 fields=1728 eligible_matches=1224 eligible_mismatches=0 ambiguous=96 unavailable=288 not_eligible=120 public_policy=deferred
```

## Full acceptance

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

make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

Docker results must identify the selected context and daemon. Docker Desktop and
native Ubuntu Docker remain separate evidence strata.

## Evidence interpretation

The batch pilot proves transaction and cleanup semantics only. It is not a
runtime result. The role/property matrix and readelf reconciliation remain
diagnostic, unfrozen, and publication-ineligible. Static GNU properties do not
prove runtime CET enforcement, and zero comparator mismatches within the eligible
controlled denominator do not establish arbitrary-binary accuracy.
