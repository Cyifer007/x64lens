# Sprint 8 Patch 036 validation: historical findings hardening

## Scope

Patch 036 converts the historical-review findings into public hardening work. It fixes byte-safe JSON rendering for target paths and bounded section labels, requires section labels to agree on file offset and virtual address, prevents local `.env` files from entering Docker build context, strengthens benchmark smoke artifact integrity, avoids fixed temporary file collisions, and tightens JSON report validation.

## Required native validation

Run the standard repository hygiene and development checks:

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
```

Run the build and functional validation gates:

```bash
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
make section-label-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

Expected highlights:

- `section-label-smoke` passes with six focused cases, including newline escaping, high-bit JSON escaping, non-executable overlap rejection, ambiguous executable overlap omission, and file-offset/virtual-address mismatch omission.
- `validation-smoke` ends with `validation-smoke: ok`.
- JSON validation rejects reports whose `primitive_coverage.registers` omits a register that appears in a candidate `controls` list.
- Malformed and capacity counts remain stable unless intentionally updated by a later validation-plan patch.

## Required benchmark integrity checks

Patch 036 changes failure behavior for invalid benchmark inputs. These commands should fail before writing normal evidence:

```bash
RUNS=0 MAX_DEPTH=4 bash benchmarks/scripts/bench-scanner-smoke.sh ./build/x64lens ./tests/bin/gadgets
RUNS=0 MAX_DEPTH=4 bash benchmarks/scripts/bench-baselines-smoke.sh ./build/x64lens
RUNS=0 bash benchmarks/scripts/bench-x64lens.sh ./build/x64lens ./tests/bin/gadgets
```

After a valid baseline smoke run:

```bash
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
make bench-summary
```

Expected behavior:

- `bench-summary-latest` summarizes the newest nonempty TSV artifact.
- `bench-summary` summarizes one TSV by default or refuses mixed aggregation with guidance to use `ALLOW_MIXED_BENCH_SUMMARY=1` for exploratory multi-artifact summaries.
- TSV rows must have numeric nonnegative `wall_s` and `maxrss_kb` values.
- Symlink targets record the dereferenced analyzed-file size, not the symlink inode size.

## Required Docker validation

Run Docker checks when Docker is available:

```bash
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Additionally, use a safe sentinel-only Docker context probe to confirm `.env` and `.env.*` are excluded from the image. Do not read or print real local secrets.

## Patch-bundle hygiene

```bash
BUNDLE=/path/to/036_x64lens_sprint8_historical_findings_hardening_patch.zip \
  make patch-bundle-hygiene
```

The bundle must not include `.local/`, generated results, private project context, local environment files, or private validation evidence.

## Git acceptance

Before commit:

```bash
git status
git diff --stat
git diff --check
```

Commit after native and Docker validation succeeds or after Docker-only failures are classified as environment defects and rerun successfully outside the restricted filesystem sandbox:

```bash
git add .
git reset .local 2>/dev/null || true
git status
git commit -m "test: harden historical finding evidence gates"
git push
```
