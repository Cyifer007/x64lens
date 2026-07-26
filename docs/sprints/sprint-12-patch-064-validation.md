# Sprint 12 Patch 064 Validation

## Purpose

Patch 064 resolves the Patch 063 acceptance findings, closes the measured
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
- regenerates private-package, command-ledger, evidence, and checksum
  inventories from one final artifact set.

## Roadmap scope

The measured overlap survey observed zero executable overlaps, repeated bytes,
or repeated exact identities in the bounded diagnostic sample. Patch 064 keeps
Patch 063 contributor provenance and defers range unioning and candidate
identity deduplication. The decision is validated by:

```bash
make sprint12-overlap-decision-smoke
```

The next bounded loader capability is an internal role lattice over ELF type,
entrypoint, `PT_INTERP`, `DF_1_PIE`, and `DT_SONAME`. `ET_DYN` alone remains
unknown. The current public PIE indicator and schema `0.2.0` remain unchanged.

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

## Make failure interpretation

The four reported aggregate failures were not four independent product defects.
The focused section-label target used a noncanonical section-zero fixture; that
failure then propagated through native validation, sprint closeout, and Docker
validation. Generated corpus verification also exposed mode-repair and ownership
integrity gaps. Patch 064 corrects those causes and keeps the aggregate targets
fail-fast.

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
- GNU-property IBT/SHSTK evidence remains a separate Sprint 12 patch.
- The overlap incidence measurement is one diagnostic corpus plus one WSL2
  system snapshot, not a population-wide estimate.
- Cloud validation without NASM, ShellCheck, Docker, and the pinned baseline
  tools cannot substitute for the WSL2 acceptance matrix.
