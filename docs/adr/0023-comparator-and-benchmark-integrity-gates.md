# ADR 0023: Comparator and benchmark-integrity gates

## Status

Accepted for Sprint 8 Patch 037.

## Context

Historical validation review confirmed that Sprint 8 still had two planned comparator
deliverables open: automated `readelf` comparison checks and optional
`checksec`/`rabin2 -I` comparison helpers. Patch 036 also hardened benchmark TSV
validation but left a nearby evidence defect: Python accepted `nan` and `inf` as
floating-point values.

## Decision

Patch 037 adds three gates:

1. `make readelf-comparison-smoke` compares stable x64lens metadata and
   loader-visible facts against `readelf -h` and `readelf -W -l`.
2. `make optional-tool-comparison-smoke` runs `checksec` and `rabin2 -I` when
   available, records their versions and output snippets, and skips them when
   absent.
3. `make benchmark-integrity-smoke` rejects empty, malformed, negative, and
   non-finite benchmark rows before summary output can be treated as evidence.

These gates preserve x64lens as the source of its own public contract.
External tools are comparators, not runtime dependencies or universal oracles.

## Consequences

- `readelf` comparison is now part of the native validation aggregate.
- `checksec`, `rabin2`, `strace`, and `shellcheck` are documented as optional
  local review tools.
- Benchmark smoke artifacts must contain finite nonnegative measurement values.
- Sprint 8 comparator deliverables can close after Patch 037 validation.
- Publication-grade benchmarking remains future Sprint 12/13 work.
