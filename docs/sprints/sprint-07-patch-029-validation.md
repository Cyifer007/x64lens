# Sprint 07 Patch 029 Validation

## Patch purpose

Patch 029 closes Sprint 7, records the validated parser-safety and mitigation-oracle baseline, and updates the Sprint 8 handoff.

This patch is intentionally light on analyzer code. The analyzer behavior accepted in Patch 028 remains the technical baseline. Patch 029 protects the process and documentation state before the project moves into bounded dynamic metadata parsing in Sprint 8.

## Implementation summary

- Mark Sprint 7 complete.
- Add the Sprint 7 retrospective.
- Update Sprint 8 as the next implementation sprint.
- Preserve the Sprint 7 acceptance gates as Sprint 8 entry criteria.
- Update planning validation so the closed Sprint 7 state is checked structurally.

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
BUNDLE=/path/to/029_x64lens_sprint7_closeout_and_sprint8_handoff_patch.zip make patch-bundle-hygiene
```

## Expected focused results

```text
public-docs-check: ok
planning-docs-check: ok plans=18 forward_plans=11
mitigation-matrix-smoke: ok
  valid cases: 11
  malformed cases: 7
malformed-smoke: ok
  cases: 31
  malformed cases: 28
validation-smoke: ok
```

`make capacity-smoke` should remain:

```text
capacity-smoke: ok exact=4096 overflow=4097 capacity=4096 overflow_exit=6
```

## Acceptance notes

Patch 029 does not change CLI syntax, schema version, mitigation output fields, gadget record semantics, or scoring policy. Any analyzer-output change observed during validation should be treated as unexpected and investigated before Sprint 8 begins.
