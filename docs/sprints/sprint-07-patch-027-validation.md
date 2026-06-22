# Sprint 07 Patch 027 Validation Plan

## Purpose

Patch 027 is a narrow correction to the deterministic mitigation oracle. Patch 026 runtime behavior emits the explicit zero-region text `none discovered from PT_LOAD + PF_X`, while the harness expected only `none`. The Make targets correctly propagated that harness failure. This patch updates the oracle, preserves runtime output, and restores the native and Docker aggregate gates.

## What Patch 027 changes

- Bump the mitigation harness implementation version to `0.1.1` without changing its evidence schema.
- Define one exact no-executable-region text constant in the harness.
- Use that constant for the `non-executable-load` expected region record.
- Preserve all analyzer, reporter, JSON schema, exit-code, and malformed-input behavior.
- Move the shared checked-arithmetic implementation to Patch 028.

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
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

## Focused acceptance checks

The matrix must report:

```text
mitigation-matrix-smoke: ok
  valid cases: 11
  malformed cases: 5
```

The newest evidence artifact under `tests/results/mitigation-matrix/` must contain a `non-executable-load` valid record whose `expected_region_lines` value is exactly:

```json
[
  "  none discovered from PT_LOAD + PF_X"
]
```

The runtime `mitigations` output for that generated case must match the same line, emit no stderr, and return zero. All five malformed cases must retain exit code `5`, empty stdout, and the stable malformed-ELF diagnostic through `info`, `mitigations`, and `analyze`.

## Preserved invariants

- Program headers remain authoritative for runtime executable mappings.
- Raw, exact, semantic, unknown, and scored populations remain distinct.
- Text and JSON continue to originate from internal records.
- Candidate capacity remains fail-closed at record 4097.
- Malformed file-backed `PT_LOAD` ranges fail before partial output.
- Schema remains `0.1.0`; tool version remains `0.1.0-dev`.
- The local `v0.1.0-dev` tag remains unchanged.

## Bundle hygiene

```bash
BUNDLE=/path/to/027_x64lens_sprint7_mitigation_oracle_correction_patch.zip \
  make patch-bundle-hygiene
```

Patch 027 is accepted only when the focused matrix, native aggregate, Docker aggregate, documentation, planning, benchmarks, and bundle-hygiene checks pass.
