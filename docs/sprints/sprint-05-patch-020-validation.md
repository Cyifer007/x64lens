# Sprint 05 Patch 020 Validation Plan

## Patch purpose

Patch 020 adds development-environment onboarding, dependency diagnostics, optional baseline installation guidance, and broader default baseline smoke targets. It does not change analyzer semantics.

## Validation commands

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
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
make system-smoke
make validation-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
python3 benchmarks/scripts/summarize.py benchmarks/results/baseline-smoke-*.tsv
make docker-available-check
make docker-test
BUNDLE=/path/to/020_x64lens_sprint5_onboarding_dependency_patch.zip make patch-bundle-hygiene
```

## Expected results

- Dependency checks should report missing required build or validation tools before deeper targets run.
- Optional baseline tools should be reported without failing normal development checks.
- `REQUIRE_BASELINES=1 make baseline-tools-check` should fail if none of ROPGadget, Ropper, or ropr are available.
- `bench-baselines-smoke` should include the controlled fixture and available default system targets.
- Generated benchmark files should remain ignored by Git.
- Public patch bundles should exclude local context, generated binaries, benchmark results, and private files.

## Interpretation

Patch 020 is successful when onboarding documentation, dependency diagnostics, validation targets, and benchmark-smoke target coverage behave reproducibly on a clean development machine.
