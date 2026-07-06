# Sprint 08 Patch 037 validation

## Patch goal

Close the remaining Sprint 8 comparator deliverables and fix the Patch 036
benchmark summarizer defect discovered during Patch 036 validation.

## Implements

- Automated `readelf` comparison smoke for stable ELF header and loader facts.
- Optional `checksec` and `rabin2 -I` comparison helper smoke when those tools
  are installed.
- Optional local analysis-tool inventory for `checksec`, `rabin2`, `strace`, and
  `shellcheck`.
- Benchmark summarizer finite-number validation for `nan`, `inf`, and `-inf`.
- Benchmark-integrity smoke tests for empty, malformed, negative, and
  non-finite TSV rows.
- Remaining fixed `/tmp` smoke outputs are moved to per-run temporary
  directories.
- Docker context hygiene can be validated through a secret-safe isolated
  sentinel context.

## Required native validation

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
make analysis-tools-check
make full-tools-check
make doctor

make clean
make
make samples
make test
make benchmark-integrity-smoke
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
make section-label-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

## Optional local checks

```bash
make shellcheck-smoke
make docker-context-hygiene-smoke
```

`make shellcheck-smoke` is advisory unless `SHELLCHECK_STRICT=1` is set.
`make docker-context-hygiene-smoke` requires Docker.

## Docker validation

```bash
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

If Docker Buildx metadata writes fail only inside a restricted filesystem
sandbox and pass outside that sandbox, classify the first failure as an
environment defect.

## Expected result

- `benchmark-integrity-smoke: ok`
- `readelf-comparison-smoke: ok`
- `optional-tool-comparison-smoke: ok`, with optional tools listed or skipped
- `validation-smoke: ok`
- Docker validation passes in a normal Docker-capable WSL2 environment
