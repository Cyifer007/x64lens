
# Sprint 6 Benchmark Smoke Interpretation

## Purpose

This note explains what the current baseline smoke artifacts demonstrate and what they do not yet establish.

## Current evidence

The baseline harness successfully runs x64lens, ROPgadget, Ropper, and ropr over the controlled gadget fixture and selected system binaries. It records command identity, target, run count, elapsed wall time, maximum resident set size, exit status, and environment metadata.

The observed development runs show that x64lens completes the current exact-pattern and semantic pipeline with substantially lower reported RSS and lower coarse wall-clock values than the optional baselines on the tested host. Those observations are encouraging, but they are not yet publication claims.

## Why the current numbers are not final results

- Smoke runs use small run counts.
- `/usr/bin/time` rounds very short executions coarsely, including values reported as `0.00` seconds.
- The compared tools do not perform identical work or use identical gadget definitions.
- Output volume and formatting cost differ.
- Cache state, WSL2 behavior, host load, and tool startup cost can affect small targets.
- Historical TSV files must not be merged across hosts as though they were one controlled experiment.

## Correct use

Use the newest run for local inspection:

```bash
RUNS=5 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
```

Use `make bench-summary` only when intentionally aggregating compatible artifacts from the same controlled methodology.

## Research benchmark requirements

The publication campaign must use a frozen corpus manifest, pinned tool versions, warm-up policy, repeated runs, higher-resolution timing, captured output size, comparable output modes where possible, median and percentile statistics, and explicit threats-to-validity analysis.
