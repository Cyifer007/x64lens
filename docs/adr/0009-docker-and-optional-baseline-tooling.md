# ADR 0009: Docker Parity and Optional Baseline Tooling

## Status

Accepted.

## Context

Sprint 5 introduced development dependency checks, JSON validation, system-binary smoke tests, and optional baseline comparison tooling. This exposed two environment concerns:

- Docker validation must include the same required development tools as local validation.
- Optional baseline tools must not be treated as required build or test dependencies.

The ropr baseline is installed through Cargo and may require a newer Rust/Cargo toolchain than some Ubuntu LTS apt packages provide.

## Decision

- The Docker development image includes required development tools used by `make test`, including `zip` and `unzip`.
- `make docker-test` depends on `make docker-build` so dependency changes are validated against a current image.
- ROPgadget, Ropper, and ropr remain optional baselines.
- `REQUIRE_BASELINES=1` is enforced only by baseline-aware checks.
- ropr installation is handled by a dedicated helper that detects outdated Cargo and points to rustup stable.

## Consequences

This keeps the core x64lens build/test path dependency-light while still supporting reproducible comparison work. It also avoids false failures when optional baselines are absent and gives contributors a clear path when ropr requires a newer Rust toolchain.

## Future work

- Decide whether publication benchmark hosts should require ropr or treat it as best-effort.
- Record exact baseline versions and installation method in every publication-grade benchmark run.
- Consider prebuilt ropr artifacts only if the source and version provenance can be documented cleanly.
