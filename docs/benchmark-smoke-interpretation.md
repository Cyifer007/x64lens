
# Sprint 6 Benchmark Smoke Interpretation

## Purpose

This note explains what baseline smoke artifacts can demonstrate and what they
do not establish.

## Current evidence

The baseline harness is designed to run x64lens, ROPgadget, Ropper, and ropr
over the controlled gadget fixture and selected system binaries. It records
command identity, target, run count, elapsed wall time, maximum resident set
size, exit status, and environment metadata.

Repository-tracked artifacts do not currently support a comparative RSS or
wall-time conclusion. Any retained smoke rows remain exploratory until the
fixed-corpus methodology, tool identities, target hashes, and repeated
measurements make the comparison reproducible.

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


## Transition to research measurement

When retained, smoke rows verify harness execution and can expose timing
resolution that is too coarse for small-target conditions. They do not establish
a speed or memory superiority claim. Sprint 11 replaces this path for diagnostic
research evidence with monotonic nanosecond timing, accurately scoped Linux
`wait4` resource capture, target hashes, explicit cache and warmup policy, and a
provisional corpus.
Sprint 15 freezes the confirmatory corpus and method. See
`docs/benchmark-methodology.md`,
`docs/design/benchmark-and-capability-stage-gates.md`, and
`docs/roadmap-22-sprints.md`.

## Patch 036 artifact hygiene note

Patch 036 rejects invalid benchmark inputs and metric domains before normal summarization. Use `make bench-summary-latest` for the newest nonempty smoke artifact. Use `ALLOW_MIXED_BENCH_SUMMARY=1 make bench-summary` only for exploratory aggregation after confirming that the TSV files share compatible tool versions, corpus, schema, and environment metadata.


## Patch 037 evidence-integrity update

Benchmark smoke summaries reject non-finite timing values (`nan`, `inf`, and
`-inf`) and malformed rows. If a smoke artifact fails the summarizer, treat the
artifact as invalid measurement evidence and rerun after preserving the raw log
needed for diagnosis. Do not manually edit rows into a passing state.


## Patch 055 diagnostic transition

Patch 055 adds `make diagnostic-runner-smoke` and the controlled
`make bench-diagnostic-smoke` campaign. The new runner improves timer and
resource capture, hash-bound write-sealed input execution, failure retention,
post-child artifact reconciliation, and transactional publication. It does not
make the controlled campaign a comparative result.

The current reference specification measures gadget JSON and analyze JSON as a
command-identity parity pair. It does not contain a scanner-only row because no
truthful report-suppressed scanner path exists. Baseline adapters, corpus-backed
diagnostic rows, and the engineering gap register remain later Sprint 11 work.
