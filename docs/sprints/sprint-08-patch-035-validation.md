# Sprint 08 Patch 035 validation plan

## Patch scope

Patch 035 hardens section-label annotations added in Patch 034. The patch keeps the feature but removes misleading or line-breaking annotation behavior on hostile section tables.

## Implemented behavior

- Text output escapes section-name control bytes, DEL, high-bit bytes, and backslash before rendering section labels.
- Section labels are emitted only from file-backed sections with both `SHF_ALLOC` and `SHF_EXECINSTR`.
- Ambiguous overlapping executable sections leave records unlabeled.
- Section-label helper state is stack-local to the annotation pass.
- `make section-label-smoke` adds deterministic probes for baseline `.text`, newline-bearing names, non-executable overlap, and ambiguous executable overlap.

## Required native validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make full-tools-check
make doctor
make clean
make
make samples
make test
make validate-gadget-fixture
make scanner-smoke
make arena-smoke
make pattern-smoke
make semantic-smoke
make json-smoke
make analyze-smoke
make system-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make fuzz-mutated-elf-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make section-label-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

## Required Docker validation

```bash
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

If Docker Buildx cannot write activity metadata in a restricted filesystem sandbox, rerun the Docker targets outside that sandbox before classifying the result. That condition is an environment defect, not a product defect, when the rerun passes.

## Expected key evidence

- `tests: ok`
- `capacity-smoke: ok exact=4096 overflow=4097 capacity=4096 overflow_exit=6`
- `malformed-smoke: ok` with 31 cases and 28 malformed cases
- `mitigation-matrix-smoke: ok` with 24 valid cases, 14 malformed cases, and one unsupported case
- `section-label-smoke: ok` with four cases
- `validation-smoke: ok`

The section-label smoke artifact is written under `tests/results/section-label/` and remains ignored by Git.
