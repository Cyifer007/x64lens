# Diagnostic Benchmark Task Definitions

## Purpose

Sprint 11 measurements are useful only when each row states what work was
performed. The machine-readable authority is
`benchmarks/task-definitions/sprint11-diagnostic-tasks.json`.

Patch 058 advances that authority to version 2. It retains the truthful x64lens
conditions established in Patch 055 and adds bounded, versioned native-output
adapters for ROPgadget, Ropper, and ropr. These definitions remain mutable
diagnostic authorities. Sprint 15 freezes the confirmatory task definitions
after loader, semantic, and optional-profile choices are complete.

## Reference profile

```text
profile: core-1w
runtime dependencies: none
mandatory decoder: no
worker count: 1
candidate capacity: 4096
output ordering: deterministic
```

The runner and baseline adapters are external research infrastructure. Their
Python dependency and optional baseline tools do not become dependencies of the
x64lens runtime artifact.

## Current task matrix

| Task | Status | Exact command template | Work represented |
|---|---|---|---|
| Core scanner | Unavailable | none | No public report-suppressed scanner-only path exists. Report timing must not be relabeled as scanner cost. |
| Gadget JSON | Implemented | `x64lens gadgets --format json --max-depth 4 <target>` | Complete current analysis pipeline plus schema `0.2.0` JSON rendering under `command: gadgets`. |
| Integrated-analysis JSON | Implemented | `x64lens analyze --format json --max-depth 4 <target>` | The same current analysis facts and JSON body under `command: analyze`; this is a command-path parity condition, not yet an independently broader workload. |
| ROPgadget report | Adapter implemented | `ROPgadget --binary <target> --depth 5 --only 'pop|ret' --nojop --nosys --silent` | ROPgadget-native return-oriented report under an explicit depth/filter/output scope. |
| Ropper report | Adapter implemented | `ropper --file <target> --nocolor --single --type rop --inst-count 5` | Ropper-native single-process return-oriented report with color disabled and an explicit instruction limit. |
| ropr report | Adapter implemented | `ropr --colour false --max-instr 5 --nojop --nosys <target>` | ropr-native return-oriented report with color, JOP, and syscall categories disabled for this task. |

The command templates define the Patch 058 diagnostic task. They do not claim
that each baseline performs identical internal work.

## Why core timing is unavailable

The current scanner does not terminate at a public output boundary. A successful
JSON command performs:

```text
ELF validation
  -> program-header and mitigation analysis
  -> executable-region discovery
  -> candidate scanning
  -> exact matching
  -> semantic classification
  -> provenance materialization
  -> memory and architectural effects
  -> scoring
  -> optional section annotation
  -> analysis-summary construction
  -> JSON rendering
```

A benchmark may measure that complete command, but it may not subtract guessed
reporting cost or describe the result as isolated scanner throughput. A future
core condition requires one of these reviewed designs:

- a report-suppressed internal profile with identical analysis semantics;
- an external narrow harness linked against a stable engine boundary; or
- a batch design whose work and output suppression are explicitly modeled.

Any such profile receives its own identity and cannot silently replace
`core-1w`.

## Gadget and analyze parity

Current schema `0.2.0` validation requires gadget and analyze reports for the
same target and options to match after removing only command identity. The two
conditions remain in the diagnostic specification because they can reveal
command-orchestration regressions. They must not be presented as a comparison
between a narrow gadget engine and a broader integrated engine until their
actual work scopes diverge by design.

## Baseline native-output contract

Every admitted baseline condition retains:

- executable path, mode, SHA-256, version command, and version output;
- exact measured command and working directory;
- immutable target path, mode, and SHA-256;
- bounded native stdout and stderr with hashes and sizes;
- explicit per-line, record-count, and instruction-count parser limits;
- exit, signal, timeout, and output-limit outcome;
- adapter path, identity, and SHA-256;
- late reauthentication that each retained path still names the recorded bytes; and
- a normalized artifact that references rather than replaces native output.

The Patch 058 adapters reject uncategorized native output. Parser failure is a
failed diagnostic condition, not zero baseline coverage.

## Normalized relation set

A raw executable-return-byte relation is explicitly unavailable for the external
baselines. ROPgadget, Ropper, and ropr expose decoder-backed gadget records; they
do not expose a loader-authoritative raw-byte scan that can be equated with
x64lens `raw_candidate_count`. Native return records therefore cannot substitute
for that evidence layer.

The first implemented cross-tool relation is intentionally narrow:

```text
canonical_exact_pop_rdi_ret
```

For each tool, the adapter retains the native record and emits:

```text
tool_native_record_count
unique_tool_native_record_count
tool_reported_return_terminator_record_count
unique_tool_reported_return_terminator_site_count
canonical_exact_pop_rdi_ret_record_count
unique_canonical_exact_pop_rdi_ret_relation_count
binary_fact_arg_control_rdi_present
```

The native and unique populations remain separate. The canonical relation
requires exact represented instructions `pop rdi; ret` or `pop rdi; retq`; it
is not inferred from a substring or tool summary line.

## Metric boundary

A baseline's reported total remains tool-specific. It must not be written into
an unlabeled cross-tool `gadget_count` column. Runtime, RSS, output size, native
record populations, normalized exact relations, and x64lens raw/exact/semantic/
unknown/scored metrics remain distinct.

The adapters do not establish task equivalence. They expose the remaining
differences in alignment policy, instruction decoding, invalid-instruction
filtering, duplicate handling, canonicalization, depth, and formatting work.

## Diagnostic claim boundary

Patch 058 establishes bounded baseline normalization and evidence identity. It
does not support claims that x64lens is faster, lower-RSS, more complete, or
more operationally useful than another tool. Those claims require the Sprint
15-frozen method and later preview/publication campaigns.
