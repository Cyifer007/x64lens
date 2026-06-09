# Benchmark Methodology

## Purpose

Benchmarking is a first-class research feature of x64lens. The goal is to evaluate runtime, memory efficiency, coverage, semantic classification value, and reproducibility.

## Hypotheses

### H1

An assembly-first gadget scanning engine can outperform Python-heavy gadget discovery tools in raw runtime and memory footprint for ELF64 x86_64 binaries.

### H2

Semantic primitive classification provides more actionable exploitability triage than raw gadget enumeration alone.

### H3

A dependency-light analyzer can be integrated into enterprise workflows with lower operational friction than heavyweight reverse engineering frameworks.

## Baseline tools

Initial comparison candidates:

- ROPgadget,
- Ropper,
- ropr,
- radare2/rabin2 where appropriate,
- checksec for mitigation comparison only.

## Required benchmark metadata

Every benchmark run should record:

- x64lens version,
- output schema version,
- baseline tool versions,
- exact commands,
- host CPU,
- RAM,
- OS version,
- kernel version,
- compiler versions,
- NASM version,
- corpus manifest hash,
- run count,
- warm or cold cache condition.

## Required metrics

- wall-clock runtime,
- CPU time,
- max RSS,
- input file size,
- throughput MiB/s,
- gadget count,
- unique gadget count,
- semantic primitive count,
- exact pattern count,
- output size,
- exit code,
- error count.

## Statistical reporting

For each tool and binary:

- run at least 5 trials during development,
- prefer 20 or more trials for publication results,
- report median,
- report p95,
- report min and max where useful.

## Corpus tiers

### Tier 1: controlled toy corpus

Used for correctness and known expected output.

### Tier 2: Linux system binaries

Used for realistic everyday binaries.

### Tier 3: larger open-source binaries

Used for performance stress.

### Tier 4: compiler/hardening matrix

Used for mitigation and hardening research.

## Threats to validity

- Different tools may define gadgets differently.
- Capstone-backed Python tools may use native code internally.
- Disk cache effects may distort runtime.
- Output formatting may dominate small binaries.
- Corpus selection may bias results.
- A pattern-based scanner may undercount complex gadgets.
- Full disassembly tools may perform more work than x64lens.

Benchmark conclusions must reflect these limitations.

## Sprint 3 scanner smoke benchmark

Sprint 3 introduces the first development-level scanner benchmark. This is a smoke benchmark, not a publication benchmark. Its purpose is to validate that repeated scanner runs can be captured with enough metadata to support later research-grade benchmark design.

Run:

```bash
make bench-scanner-smoke
```

Optional controls:

```bash
RUNS=10 MAX_DEPTH=4 make bench-scanner-smoke
RUNS=5 MAX_DEPTH=8 benchmarks/scripts/bench-scanner-smoke.sh ./build/x64lens ./tests/bin/gadgets /bin/ls
```

The script writes a TSV results file and metadata sidecar under `benchmarks/results/`. The results include:

- tool name,
- command,
- max depth,
- target path,
- target size,
- run number,
- wall-clock runtime,
- maximum RSS,
- exit code,
- candidate count,
- `ret` count,
- `ret imm16` count,
- exact pattern count,
- output byte count.

The smoke benchmark must not be used to claim superiority over other tools. It exists to prove measurement plumbing before comparison against ROPgadget, Ropper, and ropr.


## Arena allocator note

Sprint 3 Patch 010 introduces arena-backed candidate storage. Scanner smoke benchmark results before and after this change should be compared only as development sanity checks. Publication results require a clean benchmark environment and repeated runs after the scanner, classifier, and output modes stabilize.


Patch 011 adds `exact_pattern_count` to the scanner smoke TSV. This is a development metric showing how many raw candidates were tagged with exact byte-template pattern IDs. It is not yet a semantic primitive count and must not be used as a claim about exploitable gadget availability.

## Sprint 3 closeout benchmark status

Sprint 3 created benchmark plumbing but not publication results. The scanner smoke benchmark now records raw candidate counts, `ret` counts, `ret imm16` counts, exact pattern counts, wall time, max RSS, target size, command, run count, and environment metadata.

Current interpretation boundaries:

- `candidate_count` is a raw terminator-centered candidate-window count.
- `exact_pattern_count` is an exact suffix pattern tag count.
- `exact_pattern_count` is not semantic primitive coverage.
- `semantic_primitive_count` begins only after Sprint 4 classifier work.
- Publication claims require repeated baseline comparisons after the scanner, classifier, scoring, and output modes stabilize.

## Expanded benchmark roadmap

Future benchmark phases should proceed in this order:

1. controlled fixture correctness,
2. scanner smoke measurements,
3. semantic primitive coverage measurement,
4. baseline tool comparison,
5. compiler and hardening matrix measurement,
6. network-facing infrastructure binary case study,
7. publication summary tables with raw result preservation.

## Metric boundary requirements

Benchmark rows must avoid collapsing unlike concepts into one ambiguous `gadget_count` field. Prefer explicit fields:

```text
raw_candidate_count
exact_pattern_count
semantic_candidate_count
unknown_candidate_count
scored_candidate_count
primitive_coverage_count
```

This matters because x64lens, ROPgadget, Ropper, and ropr may define candidate windows, gadgets, and useful primitives differently.

## Assembly-first benchmark caution

The NASM implementation is a hypothesis to evaluate, not a conclusion. Benchmark analysis must consider:

- disk cache effects,
- page faults,
- output size,
- formatting cost,
- executable-region size,
- whether baseline tools use native decoder libraries,
- whether baseline tools perform more semantic work than x64lens at the measured stage.

## Future ablation option

If reviewers challenge whether NASM matters, consider a small C or Rust reference scanner as an ablation baseline. This should be optional and narrow. It should not become a rewrite or replacement for the assembly-first engine.
