# Sprint 12 Patch 070 Validation

## Status

Rejected as a Sprint 12 acceptance candidate after validation reproduced
blocking cleanup, batch-oracle, output-limit, and delivery-custody defects.
Patch 071 supplied the first corrective boundary, and Patch 072 supplies the
remaining correction plus acquisition and environment-parity gates. The batch
pilot, private-fact matrix, and `readelf` reconciliation remain diagnostic,
unfrozen, and publication-ineligible. Qualified native/container parity remains
pending, and public-policy review remains a separate later gate.

## Purpose

Patch 070 corrects the remaining Patch 069 evidence-transaction, comparator,
authority, and Make prerequisite defects, then adds the development-only
whole-batch transaction-conformance pilot required before below-floor batching
can support a throughput experiment.

## Source precondition

Patch 070 is defined against exact committed Patch 069 source:

```text
3bd8a8cea0529b72d19dd3c79b48c16f7943fed7
```

## Unchanged product contracts

- tool version `0.1.0-dev`;
- schema version `0.2.0`;
- program-header executable authority;
- candidate capacity 4,096;
- candidate 4,097 returns exit 6 before stdout;
- malformed parse failures emit no partial stdout;
- dependency-free, decoder-free, one-worker reference runtime;
- no runtime analyzer module or schema field change;
- no new role-derived PIE/DSO field or IBT/SHSTK field; the existing coarse
  `mitigations.pie` field remains unchanged.

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

sprint12-role-property-heldout-smoke: ok objects=96 natural=48 metamorphic=48 probe_runs=288 public_commands=384 fact_fields=18 expected_vectors=96 observed_vectors=96 unique_natural=48 provisional_targets=24 provisional_overlap=0 edge_layouts=24 property_overlap_positive=1 malformed=12 schema=0.2.0

sprint12-role-property-readelf-smoke: ok objects=96 commands=384 fields=1728 eligible_matches=1224 eligible_mismatches=0 ambiguous=96 unavailable=288 not_eligible=120 public_policy=deferred
```

The Patch 070 version-1 batch banner is not an acceptance authority. Patch 071
replaces it with case-specific expected records and derived totals.

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

The batch pilot validates runtime transaction and cleanup semantics only. It is
diagnostic, unfrozen, publication-ineligible method evidence, not a performance
result or a single-run-latency result. The batch remains the measurement unit;
its elapsed time is not divided into synthetic per-invocation latency. The
role/property matrix and readelf reconciliation remain diagnostic, unfrozen,
and publication-ineligible. Static GNU properties do not prove runtime CET
enforcement, and zero comparator mismatches within the eligible controlled
denominator do not establish arbitrary-binary accuracy.


## Review disposition

Patch 070 is not accepted. The retained private role/property and comparator
facts remain diagnostic inputs, but the following acceptance blockers require
Patch 071 correction:

- a late nested file or directory replacement could be unlinked;
- the batch authority omitted complete case-level expected outcomes;
- output limits were applied only after complete buffering; and
- source/evidence deliveries were not recursively closed and portable.

The first corrective validation authority is
[`sprint-12-patch-071-validation.md`](sprint-12-patch-071-validation.md); the
remaining correction and acquisition/parity gates are recorded in
[`sprint-12-patch-072-validation.md`](sprint-12-patch-072-validation.md).
