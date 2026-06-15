# ADR 0008: Development toolchain checks and onboarding path

## Status

Accepted.

## Context

x64lens now depends on several distinct tool groups:

- build tools for NASM and linking,
- sample-corpus tools for controlled fixture binaries,
- validation tools for JSON, malformed input generation, and system-binary smoke testing,
- benchmark tools for timing and summarization,
- optional baseline tools for comparison against ROPgadget, Ropper, and ropr.

Missing tools should not be confused with analyzer defects. A new contributor or reviewer should be able to run a single diagnostic path and receive actionable setup guidance.

## Decision

The repository will provide explicit development-environment checks through `tools/check-dev-tools.sh` and Make targets:

```bash
make build-tools-check
make sample-tools-check
make dev-tools-check
make baseline-tools-check
make full-tools-check
make doctor
```

Ubuntu installation helpers will be explicit and opt-in:

```bash
make install-dev-deps-ubuntu
make install-baseline-tools-user
```

The normal build path will require only the build toolchain. The normal validation path will require the broader development toolchain. Optional baseline tools will be reported but not required unless the caller explicitly sets `REQUIRE_BASELINES=1`.

## Consequences

- Build failures caused by missing NASM or GNU ld fail early and clearly.
- Test and benchmark failures caused by missing Python, GCC, GNU time, or binutils helpers fail early and clearly.
- Optional baseline tools do not block normal development.
- Benchmark environments can opt into stricter baseline requirements.
- The README and onboarding documentation become part of the reproducibility story.
