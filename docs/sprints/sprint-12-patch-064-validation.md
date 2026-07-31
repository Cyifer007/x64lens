# Sprint 12 Patch 064 Validation

## Status

Historical validation record for the exact Patch 064 source. Patch 064 did not
pass validation; this document preserves its required outcomes rather than an
acceptance result. The
[Patch 065 validation record](sprint-12-patch-065-validation.md) and
[Patch 066 validation plan](sprint-12-patch-066-validation.md) preserve the
next intervening candidate boundaries. The
[Patch 067 validation plan](sprint-12-patch-067-validation.md) preserves the last
intervening candidate boundary, and the
[Patch 068 validation plan](sprint-12-patch-068-validation.md) preserves the
last historical candidate boundary. The current corrective and external-
reconciliation candidate is covered by the
[Patch 069 validation plan](sprint-12-patch-069-validation.md).

## Purpose

Patch 064 addresses the Patch 063 acceptance findings, records the measured
executable-overlap normalization gate as a diagnostic deferral, and adds a
bounded internal PIE-versus-DSO role-evidence lattice without changing public
output.

## Corrective scope

The patch:

- retains corpus-root descriptor authority through checksum authentication,
  mode repair, and semantic reverification;
- rejects corpus file or directory ownership drift;
- emits canonical all-zero section-header entry zero in the section-label
  fixture;
- rejects candidate capacity above 4,096 even when the current count is small;
- reconciles executable-region PHDR indexes with ordinary `e_phnum`, requiring
  in-range, strictly increasing, unique indexes;
- expands the ordinary and extended section-zero field oracle;

## Roadmap scope

The measured overlap survey observed no target with executable-region overlap,
no same-slope repeated executable bytes, and no repeated exact identities in
the bounded diagnostic sample. Patch 064 keeps Patch 063 contributor provenance
and defers range unioning and candidate identity deduplication. The decision is
validated by:

```bash
make sprint12-overlap-decision-smoke
```

Patch 064 also adds an internal role lattice over ELF type, entrypoint, a
bounded `PT_INTERP` carrier, `DF_1_PIE`, and validated `DT_SONAME` string
evidence. A raw SONAME tag or index is insufficient until it resolves to a
bounded, nonempty, in-range, NUL-terminated string. `ET_DYN` alone remains
unknown. The current public PIE indicator and schema `0.2.0` remain unchanged.
The current Patch 069 candidate carries these facts forward with the intervening
corrections and the separate bounded GNU-property IBT/SHSTK gate.

## Focused validation

```bash
make patch063-corrective-regression-smoke
make patch062-corrective-regression-smoke
make sprint12-phdr-validity-smoke
make sprint12-overlap-provenance-smoke
make sprint12-overlap-decision-smoke
make sprint12-binary-role-smoke
make section-label-smoke
```

Expected focused banners:

```text
patch063-corrective-regression-smoke: ok mode_root_continuity=1 owner_drift=1 section_zero=1
sprint12-phdr-validity-smoke: ok cases=49 executions=196 ordinary_valid=5 ordinary_malformed=18 extended_unsupported=4 extended_malformed=22
sprint12-overlap-provenance-smoke: ok phdr_indexes=5 dense_masks=1 empty=1 rejected=9 region_stride=64 evidence_stride=56
sprint12-overlap-decision-smoke: ok targets=3115 executable=3106 overlaps=0 repeated_bytes=0 repeated_identities=0 normalization=deferred provenance=retained
sprint12-binary-role-smoke: ok cases=17 states=5 malformed=4 unsupported=1 summary_bytes=200 public_output=unchanged
```

## Full native validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
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
make system-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

## Docker and parity validation

Record the selected Docker daemon before execution. Native Ubuntu Docker and
Docker Desktop are separate environment strata.

```bash
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

## Aggregate failure interpretation

`section-label-smoke` is the focused dependency for section-label behavior. A
failure there propagates through native validation, sprint closeout, and Docker
validation, so diagnose that focused result before interpreting the aggregates.
Generated-corpus mode and ownership verification are separate integrity gates.

## Preserved contracts

```text
candidate capacity:       4096
candidate overflow:       exit 6 before stdout
schema version:           0.2.0
public PIE indicator:     unchanged ET_DYN indicator
raw/exact/semantic tiers: unchanged
scanner ordering/counts:  unchanged
runtime dependencies:     none added
worker profile:           one-worker reference unchanged
```

## Known limitations

- The internal role state is not a public PIE/DSO conclusion.
- GNU-property IBT/SHSTK evidence is carried by the current Patch 069 candidate;
  this historical Patch 064 source did not include it.
- The overlap incidence measurement is one diagnostic corpus plus one system
  snapshot, not a population-wide estimate.
- Toolchain-limited static review does not substitute for the required native,
  strict-lint, Docker, and pinned-baseline gates.
