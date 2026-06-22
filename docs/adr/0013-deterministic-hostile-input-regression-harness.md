# ADR 0013: Deterministic Hostile-Input Regression Harness

## Status

Accepted for Sprint 7 Patch 025.

## Context

x64lens parses untrusted ELF64 files in assembly. Existing invalid fixtures prove several specific rejection paths, but they do not provide a repeatable mutation campaign, per-case signal and timeout evidence, or an explicit regression for candidate-storage exhaustion.

Coverage-guided fuzzing is premature while regression promotion, bounded execution, and result capture are still being established. The project first needs a deterministic safety gate that runs on developer systems, in CI, and in Docker without adding a new external runtime.

## Decision

The repository will use a Python-based deterministic mutation runner with these properties:

- one controlled generated ELF64 seed,
- a fixed, reviewed mutation catalog,
- bounded per-case execution time,
- explicit expected exit codes,
- signal and timeout capture,
- elapsed nanoseconds and output-size capture,
- SHA-256 identification of the seed,
- temporary generated mutation files by default,
- ignored TSV and metadata artifacts under `tests/results/malformed/`,
- failure on signals, timeouts, unexpected success, or unexpected exit classes.

The initial catalog covers ELF identity, fixed-header fields, program-header and section-header table ranges, executable `PT_LOAD` ranges, and an executable-region boundary probe. The invalid 63-byte ELF64 section-header stride is also preserved as the first minimized committed regression fixture.

Candidate-storage behavior is validated separately with controlled 4096- and 4097-terminator fixtures. The exact-capacity fixture must produce a complete report. The overflow fixture must return `EXIT_UNSUPPORTED` without partial output.

`make malformed-smoke` and `make capacity-smoke` are part of `make validation-smoke`. `make docker-validation-smoke` runs the same gate in the development container.

## Consequences

### Positive

- Parser-safety claims gain reproducible evidence rather than relying only on code inspection.
- Every covered case has a stable command, expected result, and machine-readable record.
- Generated hostile binaries do not pollute the repository.
- Capacity behavior is tested as an explicit contract instead of an implementation assumption.
- The harness can promote future failures into durable regression fixtures.

### Costs and limits

- Deterministic mutations do not measure code coverage.
- Passing the campaign is not a proof of memory safety.
- The catalog must expand when new parser modules are introduced.
- Compiler-generated seed bytes can differ across environments, so the artifact records the actual seed hash for each run.

## Follow-on work

Patch 026 adds a deterministic mitigation oracle before parser arithmetic changes. Patch 027 should introduce shared checked table arithmetic and grow the regression corpus around any defect exposed by either harness. Coverage-guided fuzzing remains gated on stable regression handling and suitable instrumentation.
