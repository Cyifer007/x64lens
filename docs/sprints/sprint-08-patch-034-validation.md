# Sprint 08 Patch 034 Validation

## Patch identity

Sprint 08 Patch 034 adds bounded section-label annotations and resolves two Patch 033 review items.

## Scope

Patch 034 implements:

- section-name annotations for executable-region text output,
- section-name annotations for gadget text output,
- optional `section` fields in gadget JSON records,
- a bounded section-name helper that treats section headers as metadata only,
- schema and validator compatibility for older same-version reports missing `mitigations.stripped`,
- a mitigation-oracle case for a zero-length dynamic string table whose pointer is exactly at the end of its file-backed load.

## Required validation

Run the normal full native and Docker validation sequence:

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

Expected key results:

- `tests: ok`
- `capacity-smoke: ok exact=4096 overflow=4097 capacity=4096 overflow_exit=6`
- `malformed-smoke: ok` with 31 cases and 28 malformed cases
- `mitigation-matrix-smoke: ok` with 24 valid cases, 14 malformed cases, and one unsupported case
- `validation-smoke: ok`

## Manual spot checks

The controlled gadget fixture should show `.text` labels in text and JSON output:

```bash
./build/x64lens mitigations ./tests/bin/gadgets | grep 'section: .text'
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets | grep 'section: .text'
./build/x64lens gadgets --format json --max-depth 4 ./tests/bin/gadgets \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); assert {g.get("section") for g in r["gadgets"]} == {".text"}'
```

## Acceptance notes

Section labels are accepted only as annotations. They must not alter executable-region counts, candidate counts, semantic counts, scoring, or mitigation authority.
