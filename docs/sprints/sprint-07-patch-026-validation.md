# Sprint 07 Patch 026 Validation Plan

## Purpose

Patch 026 establishes a deterministic mitigation oracle before shared parser arithmetic is refactored. It adds 11 controlled valid ELF64 layouts, five malformed program-header layouts, command-path consistency checks, ignored JSON evidence, and explicit planning-count output.

## Changed behavior

- `x64lens_elf64_validate` rejects invalid file-backed `PT_LOAD` ranges before `info` can report target metadata.
- `info`, `mitigations`, and `analyze` therefore share the same malformed result for the matrix load-range defects.
- `make mitigation-matrix-smoke` validates exact mitigation and executable-region text plus the matching integrated JSON mitigation object.
- `make validation-smoke` and `make docker-validation-smoke` include the matrix.
- `make help` provides a stable discovery surface for major development targets.
- `make planning-docs-check` verifies all 18 sprint plans and reports the 12 forward plans separately.

## Required validation sequence

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make help
make print-vars
make check-tools
make build-tools-check
make sample-tools-check
make dev-tools-check
make baseline-tools-check
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
MALFORMED_TIMEOUT=2 make validation-smoke
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

## Matrix acceptance checks

A successful matrix run must report:

```text
mitigation-matrix-smoke: ok
  valid cases: 11
  malformed cases: 5
```

The newest JSON artifact must contain 16 records, no failed record, 11 valid cases, and five malformed cases. Every valid record must preserve the expected mitigation and executable-region lines. Every malformed record must include successful checks for `info`, `mitigations`, and `analyze`.

## Existing behavior preservation

Patch 025 gates remain authoritative:

- 11 candidates in the controlled gadget fixture,
- exact capacity success at 4096 records,
- fail-closed behavior at candidate 4097,
- 29 deterministic malformed-input campaign cases,
- native and Docker aggregate validation,
- schema `0.1.0`,
- version `0.1.0-dev`,
- unchanged `v0.1.0-dev` tag target.

## Observed validation outcome

The implementation, core regression suite, malformed-input campaign, capacity boundary, benchmarks, and Docker core suite completed successfully. The matrix and both aggregate validation paths stopped on one deterministic harness mismatch for `non-executable-load`:

```text
expected: "  none"
observed: "  none discovered from PT_LOAD + PF_X"
```

The runtime reporter output is the more explicit established text and is consistent with the loader-evidence boundary. The defect is the stale oracle expectation, not the Make dependency graph or the mitigation implementation. Patch 026 therefore remains implemented but is not fully accepted until Patch 027 corrects the harness and the native and Docker aggregate gates pass.

## Bundle hygiene

```bash
BUNDLE=/path/to/026_x64lens_sprint7_mitigation_oracle_patch.zip \
  make patch-bundle-hygiene
```

The patch is accepted when native, matrix, malformed-input, capacity, JSON, system-binary, documentation, planning, benchmark-smoke, Docker, and bundle-hygiene checks complete without regression evidence.
