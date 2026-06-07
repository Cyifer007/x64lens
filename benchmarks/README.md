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
