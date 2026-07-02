# Sprint 08 Patch 033 Validation

## Scope

Patch 033 adds a stripped-status indicator, tightens duplicate dynamic string-table singleton handling, and expands the deterministic mitigation matrix.

## Expected behavior

- Text mitigation reports include `Stripped indicator: unknown`, `stripped`, or `not stripped`.
- JSON reports include `mitigations.stripped` with `unknown`, `stripped`, or `not_stripped`.
- Duplicate `DT_STRTAB` and duplicate `DT_STRSZ` entries fail closed as malformed input.
- A validated zero-length dynamic string table is completed negative canary evidence and reports canary `absent`.
- A dynamic string table above the scan cap fails closed as unsupported.
- Section-derived stripped status never changes executable-region boundaries.

## Required validation

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
MALFORMED_TIMEOUT=2 make validation-smoke
DEMO_TARGET=./tests/bin/gadgets MAX_DEPTH=4 make checkpoint-demo
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
make clean-results
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected mitigation-matrix summary after Patch 033:

```text
mitigation-matrix-smoke: ok
  valid cases: 23
  malformed cases: 14
  unsupported cases: 1
```
