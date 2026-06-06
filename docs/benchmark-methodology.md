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
