# Sprint 05 Patch 021 Validation Plan

## Patch purpose

Patch 021 closes Sprint 5 by hardening the development environment after Patch 020 validation exposed three environment-specific issues:

1. The Docker image did not include `zip` and `unzip`, while `make test` now runs the full development tool check.
2. `REQUIRE_BASELINES=1` propagated into `dev-tools-check`, which incorrectly failed before the baseline-aware check executed.
3. The optional ropr baseline may require a newer Rust/Cargo toolchain than Ubuntu 24.04 apt provides.

This patch does not change analyzer semantics, JSON schema fields, scoring logic, scanner logic, or fixture expectations.

## Expected implementation changes

- Add `zip` and `unzip` to the Docker development image.
- Make `docker-test` rebuild the development image before running the container smoke test.
- Scope `REQUIRE_BASELINES=1` enforcement to baseline-aware checks only.
- Add a dedicated ropr installer helper that detects outdated Cargo and prints a rustup-based remediation path.
- Update onboarding and environment documentation to separate required development dependencies from optional baseline tools.
- Add a Sprint 5 retrospective documenting the current project state and Sprint 6 handoff.

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
BUNDLE=/path/to/021_x64lens_sprint5_closeout_environment_patch.zip make patch-bundle-hygiene
```

## Optional ropr validation

If ropr is not installed and Cargo is too old, this command should fail with a clear remediation path rather than a long dependency compiler error:

```bash
make install-ropr-user
```

If ropr is required, install a current user-local Rust toolchain and retry:

```bash
make install-rustup-user
. "$HOME/.cargo/env"
make install-ropr-user
make baseline-tools-check
```

## Expected results

- Required build and development checks pass on a correctly configured Ubuntu 24.04 environment.
- Missing ropr remains optional unless ropr-specific installation or validation is requested.
- `REQUIRE_BASELINES=1 RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke` succeeds when at least one of ROPgadget, Ropper, or ropr is available.
- `make docker-test` uses a current Docker image and no longer fails because `zip` or `unzip` is absent from the container.
- Public documentation remains repository-facing and avoids private workflow context.

## Sprint 5 closeout interpretation

Patch 021 is successful when Sprint 5 has a reproducible scoring and JSON pipeline, stronger local/system/Docker validation, optional baseline comparison plumbing, onboarding documentation, and a clean handoff into Sprint 6 checkpoint work.
