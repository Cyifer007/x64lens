# Benchmark Methodology

## Purpose

Benchmarking is a first-class research feature of x64lens. The goal is to evaluate runtime, memory efficiency, coverage, semantic classification value, and reproducibility.

## Hypotheses

### H1

An assembly-first gadget scanning engine may reduce runtime and memory footprint relative to established gadget tools for bounded ELF64 x86_64 discovery tasks.

### H2

Semantic primitive classification may provide more actionable defensive triage evidence than raw gadget enumeration alone.

### H3

A dependency-light analyzer may reduce operational friction relative to heavyweight reverse engineering frameworks.

## Diagnostic and confirmatory benchmark phases

Benchmark design begins before capability freeze, but evidence is split into two classes.

### Diagnostic phase

Sprint 11 introduces the high-resolution runner and a provisional reproducible corpus. Diagnostic measurements use development run counts and may change the code, task definitions, corpus, or method. They are intended to reveal bottlenecks, coverage gaps, output-scope differences, and weak hypotheses. They must retain full identity and raw rows, but they are not merged into the publication campaign.

### Confirmatory phase

Sprint 15 freezes corpus membership, schema/extractor, runner, baseline versions, commands, output modes, maximum depth, cache policy, and environment strata. Sprint 16 runs the frozen preview pilot and Sprint 17 runs publication-grade repeated trials. Any affected change after freeze creates a new campaign identifier or requires a complete rerun.

This sequencing allows measurement to guide implementation without pretending that a mutable development checkpoint has already tested the final research hypotheses.

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
- target SHA-256 hash,
- tool binary or package hash when available,
- timer and resource-measurement implementation,
- CPU governor or power-policy state when available,
- process-affinity policy when used,
- run count,
- warmup count,
- tool execution order,
- warm or cold cache condition.

## Required metrics

- wall-clock runtime in nanoseconds,
- user CPU time,
- system CPU time,
- max RSS,
- input file size,
- throughput MiB/s,
- x64lens `raw_candidate_count`,
- each baseline's tool-reported and deduplicated candidate counts, labeled with
  the tool-specific definition until reconciled,
- x64lens `semantic_candidate_count`,
- x64lens `scored_candidate_count`,
- x64lens `unknown_candidate_count`,
- x64lens `exact_pattern_count`,
- output size,
- exit code,
- error count.

## Statistical reporting

For each tool and binary:

- run at least 5 trials during development,
- prefer 20 or more trials for publication results,
- report median,
- report p95,
- report min and max where useful,
- report median absolute deviation for publication campaigns,
- report confidence intervals only when the sampling and method justify them.

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


## Gadget and analyze command benchmarking boundary

The current schema `0.2.0` JSON adapter is shared by `gadgets` and `analyze`.
For the same target and options, the maintained parity contract requires their
analysis body to match after removing only command identity. Both commands run
the current metadata, mitigation, scanner, semantic, effect, score, summary, and
JSON path.

Patch 055 therefore retains both as command-path diagnostic conditions but does
not describe `gadgets --format json` as raw scanner cost or `analyze --format
json` as an independently broader workload. Baseline comparison may use the
gadget command label because it is the closest user-facing intent, but task
scope and output work must still be qualified. A distinct integrated-triage
benchmark becomes meaningful only when the command performs or emits a reviewed
additional analysis layer.

## Sprint 6 smoke interpretation

Current smoke artifacts validate harness operation and provide early development evidence. They are not final comparative results. Use `make bench-summary-latest` for one newest run and review `docs/benchmark-smoke-interpretation.md` before interpreting timing or RSS differences.

The final campaign must not aggregate historical artifacts from different hosts or environments as a single experiment unless the methodology explicitly models those environments as separate strata.


## Patch 024 higher-resolution benchmark plan

The Sprint 5 and Sprint 6 smoke harnesses use GNU `time` and correctly validate command execution, max RSS capture, version metadata, target coverage, and result summarization. They are not sufficient for final small-binary timing because elapsed output can round to `0.00` seconds.

Patch 053 moves this work to Sprint 11. Patch 055 implements the first
standard-library Python runner using a monotonic nanosecond clock and Linux
`wait4` resource information for each selected child instead of cumulative
parent-process measurements. A selected child's `wait4` record includes
descendants that child waited for.

Required runner behavior:

- record start and end with a monotonic nanosecond clock,
- capture child user time, system time, and max RSS,
- redirect tool output to controlled files or `/dev/null` according to the benchmark mode,
- preserve output byte count and exit status,
- hash the target and tool under test,
- support warmup runs that are excluded from measured rows,
- randomize or counterbalance tool order,
- record the selected cache policy,
- write one row per process execution,
- never discard failed rows silently.

### Resolution floor

Before a campaign, measure the runner's practical timing floor. When a target completes too quickly for stable single-process measurement, use one of these documented strategies:

1. choose a larger corpus target,
2. execute a fixed batch of independent tool invocations and divide only the wall-time aggregate, while retaining batch metadata,
3. report the result as below the reliable single-run resolution floor.

Do not convert `0.00` smoke values into performance claims.

### Diagnostic task modes

Use separate task identities only when the implementation performs a separately
defined workload:

| Mode | Current status | x64lens command | Research interpretation |
|---|---|---|---|
| Core scanner | Unavailable | none | No report-suppressed path exists. Report timing cannot be substituted for isolated scanner cost. |
| Gadget JSON | Implemented | `gadgets --format json` | Complete current analysis and JSON report under gadget command identity; closest user-facing baseline intent, with work-scope caveats. |
| Integrated-analysis JSON | Implemented parity condition | `analyze --format json` | Same current report body and facts under analyze command identity; useful for orchestration parity, not proof of broader work. |

A baseline row belongs in a comparison only when the compared task, output
scope, candidate definitions, and duplicate policy are stated. The maintained
machine authority is
[`benchmarks/task-definitions/sprint11-diagnostic-tasks.json`](../benchmarks/task-definitions/sprint11-diagnostic-tasks.json).

### Campaign freeze

In Sprint 15, before the Sprint 16 preview and Sprint 17 repeated trials:

- freeze corpus manifest and hashes,
- freeze baseline versions and commands,
- freeze x64lens commit and schema,
- freeze benchmark runner version,
- freeze output mode and max depth,
- record the host as a distinct experimental stratum.

Any method change after the freeze requires a new campaign identifier. Historical smoke rows and publication rows must not be merged.

### Coverage reconciliation

Runtime and memory are only part of the comparison. For each baseline, document:

- terminators included,
- maximum instruction or byte depth,
- aligned and unaligned behavior,
- duplicate handling,
- canonicalization,
- invalid-instruction filtering,
- whether output formatting is included,
- whether semantic or mitigation work is performed.

Coverage tables should compare explicitly named metrics, not a generic `gadget_count`.

## Sprint 8 Patch 036 benchmark evidence hardening

Patch 036 keeps scanner and baseline benchmark targets in the development-smoke category, but it tightens artifact integrity:

- `RUNS` must be a positive integer.
- `MAX_DEPTH` must be a positive integer within the documented smoke range.
- `wall_s`, `maxrss_kb`, and exit-code fields must remain numeric and nonnegative.
- Benchmark target size records the dereferenced analyzed file size so symlink targets such as `/bin/sh` do not record only the symlink inode size.
- `make bench-summary-latest` selects the newest nonempty TSV artifact.
- `make bench-summary` refuses to aggregate multiple TSV files unless `ALLOW_MIXED_BENCH_SUMMARY=1` is set. Mixed summaries remain exploratory and must not be used for publication evidence without matching metadata.

These checks do not make smoke timing publication-grade. Sprint 11 owns the
high-resolution diagnostic runner, environment metadata, provisional corpus
IDs, raw artifact retention, warmup/cache policy, and development statistical
method; Sprint 15 freezes the release-facing method.


## Patch 037 benchmark-integrity gate

Development benchmark summaries now reject malformed TSV rows before computing
summary tables. `benchmarks/scripts/summarize.py` requires finite, nonnegative
`wall_s` values and nonnegative integer RSS, exit-code, and run fields. Values
such as `nan`, `inf`, `-inf`, negative wall time, shifted GNU `time` diagnostic
text, and header-only artifacts are invalid evidence.

Run:

```bash
make benchmark-integrity-smoke
```

This gate is still development evidence hygiene, not publication-grade timing.
Publication benchmarking still requires the Sprint 11 high-resolution
diagnostic foundation, a Sprint 15-frozen corpus and comparator inventory, and
normalized coverage definitions for the Sprint 17 campaign.

## Sprint 8 closeout benchmark-integrity rule

Patch 039 completes the benchmark-integrity smoke regression for non-finite
values after Patch 038 validation found the RSS fixture files missing. Benchmark TSV consumers must reject `nan`, `inf`, and `-inf` in both
wall-time and RSS fields. Negative, nonnumeric, empty, and header-only evidence
must also fail closed before summary generation.

This remains a development-smoke safeguard. Publication benchmarking still
requires the planned higher-resolution runner, frozen corpus, target/tool hashes,
run-order policy, metadata validator, and raw-row preservation planned for later
sprints.


## Sprint 9 Patch 041 benchmark identity rule

Development benchmark rows now carry explicit `tool_version` and
`schema_version` identities. The summarizer groups by:

```text
tool
tool_version
schema_version
command
target
```

Rows that differ in producer or schema identity must not collapse into one
summary group, even when command and target match. Historical rows that lack an
identity remain labeled `unknown` and must not be mixed into release evidence
without explicit normalization.

This correction protects research provenance but does not upgrade smoke timing
to publication-grade evidence. Sprint 11 owns high-resolution diagnostic
timing; Sprint 17 owns the fixed comparative campaign after the Sprint 15
freeze and Sprint 16 pilot.

## Sprint 9 Patch 042 decoder-gap campaign

Patch 042 adds a development comparison campaign that is separate from both the
runtime benchmark and the later publication campaign:

```bash
make decoder-gap-smoke
make decoder-gap-campaign
```

The campaign measures x64lens and GNU objdump independently and records:

- exact commands and versions,
- analyzer, campaign implementation, controlled expectation, canonical
  validator, Python interpreter, GNU time, objdump executable, and target
  SHA-256 hashes,
- monotonic wall time and GNU-time maximum RSS,
- raw x64lens schema `0.2.0` output,
- raw objdump disassembly,
- raw terminator overlap,
- exact-suffix canonical-boundary agreement,
- supported alternatives omitted by one-record-per-terminator selection,
- duplicate terminator, duplicate exact-evidence, and duplicate canonical-
  sequence counts,
- canonical sequences outside the current exact pattern catalog.

These timings are smoke-level cost observations. They are not publication-grade
results and must not be combined with the frozen Sprint 16/17 preview or publication campaigns. The
comparison also does not establish objdump as ground truth for loader-mapped
bytes: section coverage and canonical start selection are recorded threats to
validity.

## Sprint 9 Patch 043 decoder-decision methodology

Decoder-gap targets are copied to immutable snapshots before measurement. The
snapshot hash identifies the bytes analyzed by x64lens and GNU objdump. Result
trees retain campaign, validator, interpreter, external-tool, analyzer, target,
command, and option identities, together with parser diagnostics and categorized
comparison facts.

The selected-system campaign is development evidence. Its timing and RSS rows
must not be merged into publication benchmark results. A later optional decoder
profile requires a separate benchmark stratum so the dependency-free core and
verification mode can be compared without hiding their different workloads.

## Candidate-scoped decoder and parallelism ablations

Future performance work must benchmark these as separate profiles:

```text
core single-worker scanner/report
core plus candidate-scoped decoder validation
candidate validation with N workers
region/chunk scanning with N workers, if implemented
```

Rows must preserve profile identity, worker count, decoder identity/version,
binary size, wall/user/system time, peak RSS, output size, applicable
raw-candidate, exact-suffix, semantic-exact, decoder-validated,
semantic-decoded, unknown-candidate, and scored counts, and the
deterministic-output hash. Forced multithreading is not a valid optimization
conclusion: small targets may regress because worker creation, stacks, arenas,
overlap, and merge dominate useful work. Sprint 11 provides high-resolution
diagnostic measurement, and Sprint 14 owns the pre-freeze optional-profile
ablation decision.

## Sprint 9 profile-ablation requirement

Future performance claims must distinguish at least these profiles:

```text
core-1w              dependency-free scanner, one worker
core-N-targets       independent target-level concurrency
candidate-decode-1w  optional decoder over retained candidate windows
candidate-decode-Nw  optional bounded candidate-validation workers
region-Nw            optional deterministic executable-region workers
```

Each row must record profile identity, worker count, decoder identity and version when present, binary hash, dependencies, target hash, wall time, child CPU, max RSS, output bytes, and the applicable raw-candidate, exact-suffix, semantic-exact, decoder-validated, semantic-decoded, unknown-candidate, and scored count definitions. A faster wall-clock result with materially higher aggregate CPU or RSS must not be reported as an unqualified improvement.

## Sprint 10 semantic-expansion comparison rule

Primitive-expansion rows must preserve both semantic and score counts. Patch 046
adds semantic multi-pop candidates without scoring them, so benchmark summaries
must not assume:

```text
semantic_candidate_count == scored_candidate_count
```

When comparing the new family with baseline tools, record the exact ordered
sequence, maximum-depth policy, duplicate policy, and whether the baseline
reports every canonical start or one terminator-centered record. Resource claims
remain deferred to the fixed corpus and high-resolution runner.

## Patch 049 fixed-arena interpretation

Patch 049 increases the fixed command arena from 655,360 to 720,896 bytes by adding one 16-byte memory-effect record for each of 4,096 candidate slots. This is a design allocation, not max RSS. Future benchmark rows must measure process max RSS separately and must not substitute arena arithmetic for resource evidence.


## Sprint 10 Patch 050 measurement boundary

Patch 050 changes semantic effect completeness and validation gates without adding a primitive family or changing the fixed 720,896-byte analysis arena. That allocation size is not a max-RSS measurement. Any claim that the completed effect model is faster, lower-memory, more deployable, or more useful requires the normal fixed-corpus and repeated-trial methodology.

Patch 051 calibrates ordered two-pop and positive aligned stack-adjust scores.
Patch 053 owns the broader capability reassessment and any additional score or
capability ablations; those conditions must remain separate benchmark profiles.
Historical smoke rows must not be reinterpreted as evidence for the strengthened
Patch 050 effect contract.

## Patch 051 fixed-allocation and score-measurement note

Patch 051 increases the fixed command arena from 720,896 to 819,200 bytes by adding one 24-byte architectural-effect record for each candidate slot. This is design arithmetic, not measured maximum RSS. The new multi-pop and stack-adjust scores also change score-count fixtures; benchmark rows must preserve commit, schema, score policy, and exact family definitions rather than mixing pre- and post-Patch-051 output.


## Patch 053 benchmark sequencing decision

The project will not freeze the final benchmark suite at the Sprint 10 boundary. Sprint 11 builds and exercises the runner with provisional targets so measured evidence can direct loader, mitigation, semantic, decoder, and concurrency decisions in Sprints 12 through 14. Diagnostic rows remain separate from preview and publication rows. See [`design/benchmark-and-capability-stage-gates.md`](design/benchmark-and-capability-stage-gates.md).


## Sprint 11 Patch 055 diagnostic runner implementation

Patch 055 implements the first higher-resolution runner at
`benchmarks/scripts/diagnostic-runner.py`. Its maintained behavior is:

- diagnostic-only campaign specifications with `frozen:false` and
  `publication_eligible:false`;
- hashed retained runner, campaign-specification, tool, target, and timer-probe
  files, with tool and probe execution through byte-identical executable
  write-sealed Linux `memfd` copies and target-byte delivery through a byte-
  identical non-executable `MFD_NOEXEC_SEAL` memfd carrying `F_SEAL_EXEC`;
- declared version reconciliation against retained version-command output;
- monotonic nanosecond wall timing and Linux `wait4` user, system, maximum RSS,
  fault, and context-switch measurements for the selected child; the counters
  include descendants that child waited for, exclude descendants reaped
  separately by the runner, and do not provide complete process-tree accounting;
- retained stdout/stderr bytes and SHA-256 values;
- distinct warmup and measured rows with listed or alternating order;
- explicit warm or uncontrolled cache policy;
- fixed C/UTC/path settings plus private per-command home, temporary, cache,
  configuration, and data roots;
- timer-floor samples and below-floor row labels;
- timeout, signal, nonzero-exit, same-group or escaped-descendant cleanup, and
  extractor outcomes;
- failed-row retention;
- post-child reconciliation of retained version, timer-floor, stdout, and
  stderr artifacts against their captured sizes and SHA-256 values;
- complete result-tree flush followed by atomic no-replace publication.

`make diagnostic-tools-check` must execute the runner's sealed executable-`memfd`
preflight. The runner requests `MFD_EXEC` on supporting kernels and retries
without the flag only when an older kernel reports `EINVAL`. A host that
prohibits executable memfds is incompatible with this runner.

This integrity model contains measured children; it does not claim a filesystem
sandbox against concurrent external processes running as the same user.
Diagnostic result trees are mutable after publication. Campaign workspaces must
exclude such writers, and retained evidence must be authenticated again before
promotion.

The reference specification uses one controlled target and the two truthful
current JSON command identities. It validates the runner and report extractor;
it is not the provisional corpus campaign, baseline comparison, or publication
evidence.

The timer-floor threshold is a diagnostic warning boundary, not a correction
factor. Patch 055 does not divide or subtract the floor from measured rows. A
below-floor condition requires a larger target or a future reviewed batching
method with explicit batch metadata.

## Sprint 11 Patch 056 provisional corpus method

The first provisional reproducible corpus is
`s11-p056-provisional-v1`. It contains 24 project-generated targets from one
freestanding Apache-2.0 source:

```text
GCC, Clang
x O0, O2
x requested non-PIE executable, PIE-style executable, shared object
x minimal, hardened
```

Every build retains canonical command arguments, compiler-driver and requested-
linker identity, a forced resolved-linker directory selector, target triple,
source/license/builder hashes, fixed effective environment, output hash and
size, target nonexecution state, and bounded ELF facts. Compiler output streams
are bounded, and Linux subreaper cleanup covers same-group and escaped helpers.
Two-build smoke validation requires byte-, mode-, and normalized-mtime identity.

This matrix is diagnostic sampling, not a representative population and not a
publication corpus. Compiler versions and auxiliary toolchain programs remain
part of the recorded environment stratum. Requested `ET_DYN` roles are not
release-facing PIE/DSO truth. Baseline comparisons may begin only after Patch
058 defines commands, output scope, duplicates, alignment, and failure handling
for each tool.

## Sprint 11 Patch 057 integrity correction

Target protection is now a benchmark prerequisite rather than a descriptive
mode. Tool and timer-probe snapshots are executable write-sealed Linux memfds.
Target snapshots require `MFD_NOEXEC_SEAL`, retain mode `0444`, and require
`F_SEAL_EXEC`; a host without that support cannot run this diagnostic method.
The guarantee applies to the passed target object and does not make the measured
tool an adversarially contained sandbox.

Corpus commands run from one empty retained workspace. Tool metadata commands
must leave it empty, and each compiler command may leave only its one named
bounded output. Verification reconstructs the exact expected member set instead
of accepting every checksummed regular file. Staging cleanup and explicit corpus
removal are verified operations. These corrections invalidate earlier Patch 056
diagnostic rows that depended on the weaker execution or membership model; any
new campaign receives a distinct identifier.

## Sprint 11 Patch 058 baseline normalization

Patch 058 introduces versioned diagnostic adapters for ROPgadget, Ropper, and
ropr. Each condition retains native stdout and stderr as the primary evidence.
Normalization runs afterward and is accepted only when the exact task command,
tool executable and version output, target, stream hashes and sizes, capture
limits, and adapter source identity agree.

The initial shared relation is exact `pop rdi; ret`. Reports preserve:

```text
tool-native records and duplicates
unique tool-native records
return-terminated records and sites
exact pop-rdi-return records
unique exact pop-rdi-return relations
binary presence of represented rdi argument control
```

These populations are not interchangeable with x64lens raw, exact, semantic,
unknown, or scored counts. The normalized artifacts contain no unlabeled
`gadget_count`. A parser rejection, output-limit event, nonzero exit, signal, or
timeout remains a failed diagnostic row and is not converted into zero coverage.

The controlled fixtures establish parser behavior for represented native syntax,
not universal baseline compatibility. Every baseline version admitted to a
campaign must retain its native output and pass the same identity and adversarial
parsing gates. Sprint 15 remains the command/task freeze and Sprint 17 remains
the coverage-reconciliation campaign.
