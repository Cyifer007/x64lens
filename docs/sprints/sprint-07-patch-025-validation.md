# Sprint 07 Patch 025 Validation Plan

## Purpose

Patch 025 establishes the first deterministic hostile-input regression gate. It adds mutation-based malformed-ELF testing, explicit candidate-capacity validation, exact ELF64 section-entry-size rejection, native and Docker validation targets, and CI integration.

## Changed behavior

- ELF64 files with a nonzero section-header count must use the fixed 64-byte ELF64 section-entry size.
- `tests/malformed/regressions/elf64-shentsize-63.bin` preserves the defect as a minimized 128-byte fixture.
- A controlled 4096-terminator fixture must produce a complete report, while a 4097-terminator fixture must return exit code `6` instead of producing a partial gadget or analysis report.
- `make validation-smoke` now includes malformed-input and capacity checks.
- `make docker-validation-smoke` runs the full native-equivalent validation ladder in the development container.

## Required validation sequence

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make build-tools-check
make sample-tools-check
make dev-tools-check
make baseline-tools-check
make doctor
make clean
make
make samples
make test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
make analyze-smoke
make system-smoke
make capacity-smoke
make malformed-smoke
make validation-smoke
MALFORMED_TIMEOUT=2 make fuzz-mutated-elf-smoke
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
make docker-available-check
make docker-build
make docker-test
make docker-validation-smoke
```

## Malformed-input acceptance checks

The deterministic campaign must report:

- no signal for any case,
- no timeout for any case,
- stable expected exit codes,
- nonzero exits for malformed structures,
- successful valid control and boundary cases,
- a seed SHA-256 value,
- a TSV results artifact,
- a metadata artifact.

The initial campaign contains 29 cases: 26 malformed structures, two valid controls, and one valid executable-region boundary probe.

## Candidate-capacity acceptance checks

`make capacity-smoke` must first confirm the exact 4096-candidate JSON report is complete, then confirm all four overflow command forms return exit code `6`:

```text
gadgets text
gadgets JSON
analyze text
analyze JSON
```

No command may emit partial stdout. Stderr must contain the stable unsupported-feature diagnostic.

## Existing behavior preservation

The controlled gadget fixture must retain:

- 11 raw candidates,
- 10 `ret` candidates,
- 1 `ret imm16` candidate,
- 11 exact patterns,
- 11 semantic candidates,
- 0 unknown candidates,
- 11 scored candidates.

Fixture JSON remains schema `0.1.0`. System-binary smoke checks remain shape-based and must not assert distribution-specific counts.

## Bundle hygiene

```bash
BUNDLE=/path/to/025_x64lens_sprint7_hostile_input_hardening_patch.zip \
  make patch-bundle-hygiene
```

The patch is accepted when native, malformed, capacity, JSON, system-binary, benchmark-smoke, Docker, documentation, planning, and bundle-hygiene checks complete without regression evidence.
