# Sprint 08 Patch 038 validation

## Scope

Patch 038 closes Sprint 8, hardens the optional comparator helper UX found in
Patch 037 validation, completes benchmark-integrity coverage for non-finite RSS
values, documents strict shell lint policy, and realigns the roadmap so Sprint 9
is the next implementation tranche.

## Required checks

Patch 038 is a public source patch with small helper changes and broad planning
updates. It must run the same validation aggregate as Patch 037 plus targeted
probes for the corrected helper argument order.

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make help
make print-vars
make dev-tools-check
make baseline-tools-check
make analysis-tools-check
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
make section-label-smoke
make benchmark-integrity-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
BUNDLE="$PATCH" make patch-bundle-hygiene
git diff --check
```

## Targeted helper probes

When `checksec` is installed:

```bash
bash tools/compare-checksec.sh ./tests/bin/minimal_pie_canary ./build/x64lens
bash tools/compare-checksec.sh ./build/x64lens ./tests/bin/minimal_pie_canary
```

When `rabin2` is installed:

```bash
bash tools/compare-rabin2.sh ./tests/bin/minimal_pie_canary ./build/x64lens
bash tools/compare-rabin2.sh ./build/x64lens ./tests/bin/minimal_pie_canary
```

Both argument orders must print the same target identity in the first line and
must compare the same analyzed target.

## Acceptance criteria

- `make validation-smoke` exits 0.
- Docker validation exits 0, or any first Docker failure is isolated to an
environment-specific Docker metadata write restriction and an unsandboxed rerun
passes.
- Direct `checksec` and `rabin2` helpers no longer false-pass when arguments are
reversed.
- `make benchmark-integrity-smoke` directly exercises non-finite wall-time and
RSS values.
- `make shellcheck-smoke` passes in advisory mode, and strict mode is either
clean when `shellcheck` is installed or produces only documented intentional
findings that are tracked for future cleanup.
- Sprint 8 plan, Sprint 8 retrospective, roadmap, release plan, and validation
plan agree that Sprint 8 is closed and Sprint 9 is next.
