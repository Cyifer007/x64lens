# Benchmarks

This directory contains the reproducible benchmark harness for x64lens.

Benchmarking is a first-class research feature. Do not make performance claims without preserving:

- tool versions,
- exact commands,
- corpus manifest,
- host metadata,
- run count,
- raw results,
- summary statistics.

See `docs/benchmark-methodology.md`.

## Contract

Benchmark results must be reproducible. Record tool versions, exact commands, CPU/RAM/platform, run count, and corpus manifest before using results in the paper.

## Sprint 3 scanner smoke benchmark

The first scanner smoke benchmark can be run with:

```bash
make bench-scanner-smoke
```

or directly:

```bash
RUNS=5 MAX_DEPTH=4 benchmarks/scripts/bench-scanner-smoke.sh ./build/x64lens ./tests/bin/gadgets /bin/ls
```

The script writes TSV results and a metadata file into `benchmarks/results/`. These files are ignored by Git unless explicitly promoted into a documented benchmark artifact.

This benchmark is a development smoke test. It is not publication evidence by itself.


## Sprint 3 arena-backed candidate storage

Patch 010 moves raw gadget candidate records into an mmap-backed arena. The scanner smoke benchmark can be used as a development sanity check before and after allocator changes, but these runs are not publication-quality results by themselves. Publication benchmarks require a stable corpus, clean environment, repeated trials, and baseline tool comparisons.


## Sprint 3 exact pattern count

Patch 011 adds an `exact_pattern_count` column to scanner smoke TSV output. This metric counts raw candidates tagged by `patterns.asm` with exact byte-template IDs. It is not a semantic primitive count and should not be interpreted as exploitability evidence until the classifier and scoring layers are implemented.


## Sprint 5 Patch 019 baseline comparison smoke

Patch 019 adds a development-level baseline comparison harness:

```bash
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
python3 benchmarks/scripts/summarize.py benchmarks/results/baseline-smoke-*.tsv
```

The harness always runs x64lens and optionally runs ROPgadget, Ropper, and ropr when those tools are installed. Missing optional baseline tools are recorded in the metadata sidecar and skipped by default. Set `REQUIRE_BASELINES=1` only in environments where at least one optional baseline tool is expected.

The baseline smoke TSV records tool path, tool version, exact command, target size, target SHA256, run number, wall-clock time, max RSS, exit code, output size, and x64lens JSON-derived raw/exact/semantic/unknown/scored counts. It is not a publication benchmark by itself.


## Sprint 11 Patch 055 diagnostic runner

Validate the high-resolution measurement and task-definition contracts with:

```bash
make diagnostic-tools-check
make diagnostic-runner-smoke
make diagnostic-task-definitions-smoke
make sprint11-diagnostic-reference-smoke
```

Run the controlled x64lens reference conditions after building the analyzer and
fixtures:

```bash
make bench-diagnostic-smoke
```

Set `DIAGNOSTIC_CAMPAIGN_ID` to choose a stable local result identity. Campaigns
are written under `benchmarks/results/diagnostic/` and remain ignored until a
later evidence-promotion decision.

Each campaign retains the runner and exact specification, immutable tool and target snapshots, isolated per-command environment roots, observed tool version
output, timer-floor samples, warmup and measured rows, direct-child process resource data,
stdout/stderr artifacts, and a manifest. Failed rows are preserved. Campaigns
are explicitly diagnostic, mutable, and not publication eligible.

The initial reference specification contains gadget JSON and analyze JSON
command conditions. It deliberately contains no scanner-only condition because
the current CLI has no report-suppressed scanner path. The two JSON commands
share the current analysis body and remain a command-identity parity pair rather
than independent work scopes.
