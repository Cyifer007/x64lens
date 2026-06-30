# Sprint 07 Patch 028 Validation

## Patch purpose

Patch 028 fixes the local validation problems discovered during Patch 027
local validation and implements the next Sprint 7 parser-safety step: shared checked
arithmetic for table extents, offset-plus-length validation, count handling, and
bounded per-entry table offsets.

## Validation issue corrected from Patch 027

Local validation showed that generated ignored files under `tests/results/mitigation-matrix/`
caused `make public-docs-check`, `make validation-smoke`, and
`make docker-validation-smoke` to fail because the public-docs scanner walked
ignored generated artifacts containing absolute local paths.

Patch 028 changes `tools/check-public-docs.sh` to scan tracked public files when
inside a Git worktree and to exclude generated result directories in fallback
mode. Generated validation evidence remains ignored and should not make aggregate
validation cleanup-sensitive.

Local automation also showed that `make normalize-perms` can fail when
private agent workspaces are exposed read-only. Patch 028 excludes those private
local workspaces from permission normalization and patch-bundle hygiene.

## Implementation summary

- Added checked arithmetic helpers in `src/bounds.asm`.
- Routed ELF64 program-header and section-header table validation through
  `x64lens_bounds_table_extent_valid`.
- Routed program-header entry pointer derivation through
  `x64lens_bounds_table_entry_offset`.
- Routed file-backed `PT_LOAD` range validation through
  `x64lens_bounds_range_end_valid` where the checked end matters.
- Added program-header and section-header table-end overflow regression cases.
- Expanded the mitigation matrix malformed case count from five to seven.
- Hardened public-doc scanning, Docker context filtering, patch-bundle hygiene,
  and permission normalization around ignored/private/generated directories.

## Required validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make help
make print-vars
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
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
BUNDLE=/path/to/028_x64lens_sprint7_checked_parser_arithmetic_patch.zip make patch-bundle-hygiene
```

## Expected focused results

```text
public-docs-check: ok
mitigation-matrix-smoke: ok
  valid cases: 11
  malformed cases: 7
validation-smoke: ok
```

`make test` should include:

```text
[test] malformed table extent overflow rejection
tests: ok
```

`make capacity-smoke` should remain:

```text
capacity-smoke: ok exact=4096 overflow=4097 capacity=4096 overflow_exit=6
```

## Acceptance notes

This patch changes internal validation and hostile-input handling. It does not
change CLI syntax, schema version, gadget semantics, scoring policy, or reporter
field names. If any expected mitigation line changes, treat it as a regression
unless a separate output-contract change is proposed and documented.
