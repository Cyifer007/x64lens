# Sprint 08 Patch 032 Validation

## Scope

Patch 032 adds the first evidence-qualified canary indicator and resolves the
Patch 031 local review follow-ups that are appropriate for public source:

- JSON Schema required fields and mitigation conditionals are tightened.
- Text mitigation output includes `Canary indicator: unknown|absent|present`.
- JSON mitigation output includes `"canary":"unknown|absent|present"`.
- Canary detection uses bounded `DT_STRTAB` and `DT_STRSZ` metadata from the
  already bounded `PT_DYNAMIC` table view.
- The dynamic string-table virtual address must resolve through a file-backed
  `PT_LOAD` range before scanning.
- The mitigation matrix includes canary-present and canary-absent cases, a valid
  dynamic table without `DT_NULL`, direct `gadgets --format json` validation for
  valid cases, and an invalid dynamic string-table reference malformed case.
- `make clean-results` removes ignored local validation and benchmark artifacts.

## Required local validation

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

DEMO_TARGET=./tests/bin/gadgets MAX_DEPTH=4 make checkpoint-demo

RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest

make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke

BUNDLE=/path/to/032_x64lens_sprint8_canary_indicator_patch.zip make patch-bundle-hygiene
git diff --check
git diff --cached --check
```

Expected focused output:

```text
planning-docs-check: ok plans=18 forward_plans=11
mitigation-matrix-smoke: ok
  valid cases: 20
  malformed cases: 12
capacity-smoke: ok exact=4096 overflow=4097 capacity=4096 overflow_exit=6
validation-smoke: ok
```

## Interpretation boundaries

- Canary output is an indicator, not proof that every function is protected.
- `unknown` is required when bounded dynamic string metadata is unavailable.
- `absent` requires a validated bounded dynamic string table.
- `present` requires an exact null-terminated `__stack_chk_fail` string.
- Dynamic strings must not change executable-region authority.
