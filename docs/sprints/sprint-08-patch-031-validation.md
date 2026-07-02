# Sprint 08 Patch 031 Validation

## Patch purpose

Patch 031 refines RELRO reporting now that Patch 030 provides bounded bind-now
evidence. It also resolves the duplicate-`PT_DYNAMIC` ambiguity by failing closed
when more than one dynamic table is advertised.

## What changed

- Text mitigation output now reports `RELRO: not found`, `RELRO: partial`, or
  `RELRO: full`.
- JSON mitigation output now uses `"relro":"none"`, `"relro":"partial"`, or
  `"relro":"full"`.
- Full RELRO requires both `PT_GNU_RELRO` and bounded bind-now evidence from
  `DT_BIND_NOW`, `DT_FLAGS & DF_BIND_NOW`, or `DT_FLAGS_1 & DF_1_NOW`.
- A second `PT_DYNAMIC` program header is treated as malformed to avoid merging
  ambiguous dynamic-entry and terminator state.
- The mitigation matrix now covers `gadgets` text and JSON callers for dynamic
  malformed inputs.
- The JSON validator rejects unsupported RELRO values and requires full RELRO to
  be backed by dynamic linking and bind-now evidence.

## Expected validation

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
BUNDLE=/path/to/031_x64lens_sprint8_relro_refinement_patch.zip make patch-bundle-hygiene
```

## Expected focused results

```text
planning-docs-check: ok plans=18 forward_plans=11

mitigation-matrix-smoke: ok
  valid cases: 17
  malformed cases: 11

capacity-smoke: ok exact=4096 overflow=4097 capacity=4096 overflow_exit=6

malformed-smoke: ok
  cases: 31
  malformed cases: 28

validation-smoke: ok
```

## Contract checks

- `PT_LOAD + PF_X` remains executable-region authority.
- `PT_DYNAMIC` remains mitigation evidence only.
- RELRO labels are evidence-qualified mitigation facts, not exploitability or
  safety verdicts.
- Duplicate `PT_DYNAMIC` fails before stdout on command paths that parse the
  program-header summary.
- Raw, exact, semantic, unknown, validated, and scored gadget-count semantics are
  unchanged.
- Schema version remains `0.1.0`.
- The `v0.1.0-dev` tag remains pinned to the Sprint 6 checkpoint until a
  deliberate release operation changes it.
