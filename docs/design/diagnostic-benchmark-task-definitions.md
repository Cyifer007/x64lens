# Diagnostic Benchmark Task Definitions

## Purpose

Sprint 11 measurements are useful only when each row states what work was
performed. This document defines the initial task authority used by Patch 055.
The machine-readable companion is
`benchmarks/task-definitions/sprint11-diagnostic-tasks.json`.

These definitions are mutable diagnostic authorities. Sprint 15 freezes the
confirmatory task definitions after loader, semantic, and optional-profile
choices are complete.

## Reference profile

```text
profile: core-1w
runtime dependencies: none
mandatory decoder: no
worker count: 1
candidate capacity: 4096
output ordering: deterministic
```

The runner is external research infrastructure. Its Python dependency does not
become a dependency of the x64lens runtime artifact.

## Current task matrix

| Task | Status | Command | Work represented |
|---|---|---|---|
| Core scanner | Unavailable | none | No public report-suppressed scanner-only path exists. Report timing must not be relabeled as scanner cost. |
| Gadget JSON | Implemented | `x64lens gadgets --format json --max-depth 4 <target>` | Complete current analysis pipeline plus schema `0.2.0` JSON rendering under `command: gadgets`. |
| Integrated-analysis JSON | Implemented | `x64lens analyze --format json --max-depth 4 <target>` | The same current analysis facts and JSON body under `command: analyze`; this is a command-path parity condition, not yet an independently broader workload. |
| ROPgadget report | Planned | pending normalization | Baseline-reported gadget task with explicit terminator, depth, duplicate, alignment, and output rules. |
| Ropper report | Planned | pending normalization | Baseline-reported gadget task with explicit terminator, depth, duplicate, alignment, and output rules. |
| ropr report | Planned | pending normalization | Baseline-reported gadget task with explicit terminator, depth, duplicate, alignment, and output rules. |

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

## Baseline normalization requirements

Before a baseline condition is admitted, record:

- exact executable or package version and identity;
- exact command and output mode;
- return terminators included;
- maximum instruction or byte depth;
- aligned and unaligned behavior;
- invalid-instruction filtering;
- duplicate and canonicalization policy;
- whether formatting is included;
- output bytes and failure behavior;
- candidate metric names specific to that tool.

A baseline's reported total remains tool-specific. It must not be written into
an unlabeled cross-tool `gadget_count` column.

## Diagnostic claim boundary

Patch 055 campaigns establish measurement plumbing and early observations only.
They do not support claims that x64lens is faster, lower-RSS, more complete, or
more operationally useful than another tool. Those claims require the Sprint
15-frozen method and later preview/publication campaigns.
