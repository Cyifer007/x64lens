# Sprint 08 Patch 030 Validation

## Patch purpose

Patch 030 opens Sprint 8 by adding a bounded `PT_DYNAMIC` table view and exposing
three compatible mitigation facts: bind-now evidence, dynamic-entry count, and
dynamic terminator state.

This patch also closes the Patch 029 advisory by tightening planning-document
validation instead of leaving a non-enforcing placeholder check.

## Implementation summary

- Extend the internal program-header summary record with dynamic-entry count,
  `DT_NULL` seen state, and bind-now state.
- Add ELF64 dynamic-table constants for `Elf64_Dyn`, `DT_NULL`, `DT_BIND_NOW`,
  `DT_FLAGS`, `DT_FLAGS_1`, `DF_BIND_NOW`, and `DF_1_NOW`.
- Parse `PT_DYNAMIC` through checked range validation and bounded per-entry table
  offsets.
- Add text output lines for bind-now, dynamic-entry count, and dynamic-table
  terminator state.
- Add optional JSON mitigation fields without changing schema version `0.1.0`.
- Expand the mitigation oracle from 11 to 14 valid cases and from seven to ten
  malformed cases.
- Add deterministic dynamic-table malformed cases for file-size greater than
  memory-size, file range outside EOF, and non-integral entry size.
- Tighten `tools/check-planning-docs.sh` by removing the non-enforcing advisory
  placeholder and requiring this ADR plus this validation record.

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
DEMO_TARGET=./tests/bin/gadgets MAX_DEPTH=4 make checkpoint-demo
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
BUNDLE=/path/to/030_x64lens_sprint8_dynamic_table_view_patch.zip make patch-bundle-hygiene
```

## Expected focused results

```text
planning-docs-check: ok plans=18 forward_plans=11
mitigation-matrix-smoke: ok
  valid cases: 14
  malformed cases: 10
malformed-smoke: ok
  cases: 31
  malformed cases: 28
validation-smoke: ok
```

`make capacity-smoke` should remain:

```text
capacity-smoke: ok exact=4096 overflow=4097 capacity=4096 overflow_exit=6
```

## Focused output checks

For a statically linked fixture without `PT_DYNAMIC`, `analyze` text should show:

```text
Dynamic linking: no
Bind now: not applicable
Dynamic entries: 0x0000000000000000
Dynamic terminator: not applicable
```

For normal dynamically linked controlled fixtures, mitigation output should show
`Dynamic linking: yes`, a bounded dynamic-entry count, and an explicit dynamic
terminator state. Bind-now-positive synthetic fixtures in the mitigation matrix
must report `Bind now: yes` through `DT_BIND_NOW`, `DT_FLAGS`, and `DT_FLAGS_1`.

## Acceptance notes

Patch 030 is an accuracy and parser-boundary patch, not a schema freeze or full
RELRO patch. Full RELRO still requires combining `PT_GNU_RELRO` with bind-now
evidence in a later Sprint 8 patch.
