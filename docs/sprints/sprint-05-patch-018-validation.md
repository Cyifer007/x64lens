# Sprint 05 Patch 018 Validation Hardening Notes

## Status

Validated.

## Sprint goal

Strengthen validation after the first scoring and JSON implementation. Patch 017 validated successfully, but the validation workflow exposed two process gaps:

1. Docker availability failures need to be clearly distinguished from code failures.
2. JSON and real-binary smoke testing should use reusable validators instead of ad hoc one-off checks.

Patch 018 is a testing, validation, documentation, and packaging-hygiene patch. It does not change scanner, classifier, scoring, or JSON report semantics.

## What changes

Patch 018 adds:

- `tools/validate-json-report.py`, a standard-library JSON report validator.
- `tools/system-binary-smoke.sh`, a real-system-binary smoke runner.
- `tools/check-patch-bundle-hygiene.sh`, a patch ZIP hygiene checker.
- `make system-smoke` for `/bin/ls`, `/bin/cat`, `/bin/sh`, `/usr/bin/env`, and `/usr/bin/printf` style targets when available.
- `make validation-smoke` as a local pre-commit aggregation target.
- `make docker-available-check` for clearer Docker environment triage.
- Stronger `make json-smoke` validation for both supported `--format` and `--max-depth` flag orders.
- Documentation updates for validation maturity, system binary testing, and bundle hygiene.

## Expected validation commands

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make clean
make
make samples
make test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
make system-smoke
make validation-smoke
make docker-available-check
make docker-test
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
```

`make docker-test` remains required for reproducibility when Docker is available. If `make docker-available-check` fails, the failure should be triaged as an environment issue before treating Patch 018 as an implementation failure.

## JSON validator coverage

The new JSON validator checks:

- required top-level fields,
- schema and tool identity,
- target metadata shape,
- mitigation field types,
- count fields and count relationships,
- primitive coverage shape,
- per-gadget required fields,
- hex formatting for virtual addresses and file offsets,
- compact hex byte strings,
- terminator, semantic class, register, score, and stack-delta invariants,
- non-empty limitations,
- exact controlled-fixture facts in fixture mode.

## System binary smoke coverage

The real-binary smoke runner validates installed ELF64 x86_64 binaries without relying on brittle distro-specific counts. For each usable target, it runs:

```bash
x64lens info <target>
x64lens mitigations <target>
x64lens gadgets --max-depth 4 <target>
x64lens gadgets --format json --max-depth 4 <target>
python3 tools/validate-json-report.py --mode system <json-output>
```

The command validates output shape and invariants, not specific gadget totals. This makes it safe to run across Ubuntu versions, Docker images, and WSL installations.

## Patch bundle hygiene

Patch and release bundles should not contain local-only or generated state. The new hygiene checker rejects:

- `.git/`,
- `.local/`,
- `build/`,
- `tests/bin/`,
- generated toy binaries,
- generated benchmark results,
- object files,
- Python bytecode,
- DOCX/PDF/ZIP files.

Expected check:

```bash
BUNDLE=/path/to/018_x64lens_sprint5_validation_hardening_patch.zip make patch-bundle-hygiene
```

## Acceptance criteria

- [x] `make test` passes.
- [x] `make validate-gadget-fixture` passes.
- [x] `make semantic-smoke` passes.
- [x] `make json-smoke` passes with the new validator.
- [x] `make system-smoke` passes against installed ELF64 x86_64 system binaries.
- [x] `make validation-smoke` passes locally.
- [x] `make docker-available-check` correctly distinguishes Docker environment availability.
- [x] `make docker-test` passes when Docker is available.
- [x] Patch bundle hygiene check passes against the generated patch ZIP.

## Failure triage

| Failure | First area to inspect |
|---|---|
| `validate-json-report.py` fails on fixture mode | `src/report_json.asm`, `include/structs.inc`, `src/scoring.asm`, `src/classifier.asm` |
| `validate-json-report.py` fails on system mode only | real-binary output edge case, JSON count relationships, candidate capacity handling |
| `system-smoke` fails on one target | rerun against `/bin/ls`; inspect target architecture with `file <target>` and `readelf -h <target>` |
| `docker-available-check` fails | Docker Desktop WSL integration or Docker Engine availability |
| patch hygiene fails | regenerate the bundle excluding local-only and generated paths |

## Non-goals

Patch 018 does not implement a full decoder, baseline tool comparison, canary detection, full RELRO detection, or mitigation-aware `analyze` orchestration. Those remain roadmap items.


## Validation result

Patch 018 validation confirmed the strengthened validation path:

```text
make test -> tests: ok
make validate-gadget-fixture -> validate-gadget-fixture: ok
make semantic-smoke -> validate-gadget-fixture: ok
make json-smoke -> json-smoke: ok
make system-smoke -> system-binary-smoke: ok
make validation-smoke -> validation-smoke: ok
make docker-available-check -> docker-available-check: ok
make docker-test -> tests: ok
make patch-bundle-hygiene -> patch-bundle-hygiene: ok
```
