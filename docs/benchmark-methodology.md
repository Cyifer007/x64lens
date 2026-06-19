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
- scored candidate count,
- unknown candidate count,
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


## Sprint 4 smoke benchmark fields

Patch 015 extends `benchmarks/scripts/bench-scanner-smoke.sh` so development smoke TSV rows include:

```text
candidate_count
ret_count
ret_imm16_count
exact_pattern_count
semantic_primitive_count
unknown_candidate_count
output_bytes
```

These fields remain development evidence. They are useful for regression tracking and later benchmark design, but they are not publication claims until baseline tools, corpus manifests, repeated trials, and summary statistics are captured under the full methodology.


## Sprint 5 JSON and scoring smoke

Patch 017 extends development benchmark output with `scored_candidate_count`. This remains smoke evidence, not a publication claim. The scoring model is heuristic and exact-suffix based, so benchmark tables must keep score-related counts separate from raw and semantic counts.

Patch 017 also adds `gadgets --format json`; future benchmark scripts should prefer JSON for machine-readable extraction once the JSON path is validated across the corpus. Text parsing remains acceptable only for development smoke checks.

## System binary smoke validation

Patch 018 adds `make system-smoke` as a development validation target over installed ELF64 x86_64 binaries. This is not a research benchmark and must not be used for performance claims.

The purpose is to catch real-binary regressions in:

- ELF metadata reporting,
- mitigation reporting,
- gadget text output,
- gadget JSON output,
- JSON count relationships,
- primitive coverage structure,
- score and unknown-stack-delta encoding.

The target intentionally validates shape and invariants instead of exact gadget counts because `/bin/ls`, `/bin/cat`, `/bin/sh`, and similar binaries vary across Linux distributions and compiler builds.

Publication benchmarks still require fixed corpus manifests, tool versions, repeated runs, environment metadata, raw results, summary statistics, and baseline comparison against ROPgadget, Ropper, and ropr.


## Sprint 5 Patch 019 and Patch 020 baseline comparison smoke

Patch 019 adds a development-level baseline comparison harness. Patch 020 broadens the default target list and adds development toolchain diagnostics:

```bash
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
python3 benchmarks/scripts/summarize.py benchmarks/results/baseline-smoke-*.tsv
```

The harness always measures x64lens with:

```bash
x64lens gadgets --format json --max-depth <N> <target>
```

Default Patch 020 smoke targets are:

```text
tests/bin/gadgets
/bin/ls
/bin/cat
/bin/sh
/usr/bin/env
/usr/bin/printf
```

These targets intentionally match the real-binary smoke set where possible. The controlled fixture provides known semantic expectations; the system binaries provide shape, timing, memory, and exit-code evidence across common installed ELF64 binaries.

It optionally measures these baseline tools when installed:

```bash
ROPgadget --binary <target>
ropper --file <target>
ropr <target>
```

Missing optional baseline tools are recorded in metadata and skipped by default. This behavior keeps daily development validation stable while preserving environment evidence. Set `REQUIRE_BASELINES=1` when the test environment is expected to provide at least one baseline tool.

Patch 019 and Patch 020 rows preserve raw timing and memory evidence, but they do not establish superiority or coverage equivalence. Research-grade comparisons still require fixed baseline versions, normalized gadget definitions, repeated trials, corpus manifests, environment metadata, raw rows, and summary statistics.

## Optional baseline toolchain note

ROPgadget and Ropper are Python CLI baselines and are normally installed through `pipx`. ropr is a Rust CLI baseline and may require a newer Cargo than the Ubuntu 24.04 apt package provides. Benchmark metadata must record which optional baselines were present and the version strings reported by each tool. Missing optional baselines are acceptable for development smoke tests but must be disclosed in any benchmark interpretation.


## Analyze command benchmarking boundary

Sprint 6 Patch 022 adds `analyze` as an integrated checkpoint command. The baseline gadget-discovery smoke harness should continue using `gadgets --format json` for apples-to-apples comparison against ROPgadget, Ropper, and ropr because those tools primarily enumerate gadgets.

`analyze` should be benchmarked separately when the question is end-to-end defensive triage cost. That benchmark should make clear that x64lens is producing target metadata, mitigation facts, primitive coverage, scored candidate facts, and limitations in one command, while the baseline tools may be doing a narrower or different task.

## Sprint 6 smoke interpretation

Current smoke artifacts validate harness operation and provide early development evidence. They are not final comparative results. Use `make bench-summary-latest` for one newest run and review `docs/benchmark-smoke-interpretation.md` before interpreting timing or RSS differences.

The final campaign must not aggregate historical artifacts from different hosts or environments as a single experiment unless the methodology explicitly models those environments as separate strata.
