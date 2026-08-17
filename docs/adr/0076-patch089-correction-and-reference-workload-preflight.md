# ADR 0076: Patch 089 Correction and Reference-Workload Preflight

## Status

Accepted as the Patch 090 implementation decision; exact-source acceptance remains pending.

## Context

Patch 089 preserved the analyzer runtime and narrowed split-debug packaging to an opt-in diagnostic experiment. Review found that several evidence authorities could still accept a resealed substitute, an aliased producer generation, a fabricated replay command, an archive mutated after opening, or an unbounded manifest/helper payload. Candidate-source recovery also leaked a descriptor on one rejected open path, and the split-debug regression wrote through a read-only test fixture.

The same review found no evidence requiring a change to ELF parsing, gadget discovery, semantic classification, scoring, public reporting, or schema `0.2.0`. Strategic review selected workload qualification as the highest-value next experiment, but required an 80-execution reference-only preflight before the paired 160-run phase-attribution matrix.

## Decision

Patch 090:

1. binds split-debug results to exact producer, source, tool, behavior, symbol, control, mode, and inode authorities;
2. rejects aliased producer generations and independently resealed result substitutions;
3. validates replay command vectors against the exact tool/target command grammar;
4. reauthenticates candidate-source archives after read, before publication, and before success;
5. bounds custody manifests and application helpers before allocation or execution;
6. fixes split-debug staging modes and read-only regression-fixture handling;
7. requires workload fixtures to be unique by semantic tuple, not only identifier;
8. executes an 80-run reference-only qualification preflight; and
9. adds no runtime analyzer, public output, semantic, score, schema, decoder, or concurrency change.

## Reference preflight contract

The preflight contains eight fixed fixtures, one warmup and nine measured executions per fixture:

```text
fixtures:              8
warmups:               8
measured executions: 72
total executions:     80
minimum qualified:     6
floor multiple:        5
maximum MAD/median: 0.10
```

A fixture qualifies only when every execution succeeds, output remains stable, the median exceeds five times the authenticated timer floor, and dispersion remains within the limit. These 80 rows are reference-only and may not be reused in the later paired 160-run phase-attribution matrix.

A successful preflight authorizes only the later measurement. A failed preflight retires phase instrumentation for the current workload set. Neither outcome is a product performance result.

## Artifact-backed preflight result

The retained unchanged-runtime analyzer completed all 80 executions with zero command failures and stable streams. Fewer than six of eight fixtures qualified; only exact-capacity report workloads approached the intended duration class. The result therefore selected:

```text
qualified fixtures: fewer than 6/8
decision: retire_phase_instrumentation_for_current_workloads
```

This is artifact-backed unchanged-runtime evidence, not a fresh Patch 090 build. Fresh local execution remains an acceptance check, but the current evidence does not justify building the paired phase-instrumentation matrix.

## Preserved boundaries

- Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable authority.
- Mapping, parsing, scanning, matching, classification, side-cars, scoring, and reporting remain separate.
- Raw, exact-suffix, semantic-exact, unknown, future decoder-backed, and scored facts remain distinct.
- Candidate capacity remains 4,096; candidate 4,097 returns exit code 6 before stdout.
- Malformed input produces no partial report.
- Targets remain read-only and are never executed.
- The reference runtime remains dependency-free, decoder-free, deterministic, and one-worker.
- Public schema remains `0.2.0`.

## Consequences

Patch 090 strengthens evidence and delivery trust without manufacturing a favorable benchmark result. The exact Patch 089 diagnostic floor is `5,894,690 ns`; all 60 measured x64lens rows remained below that floor and all nine natural coordinate cells lacked positive anchors. No performance, RSS, comparative coverage, superiority, or publication claim follows.

## Validation

Focused gates:

```bash
make patch089-corrective-regression-smoke
make sprint13-workload-reference-preflight-contract-smoke
make sprint13-split-debug-packaging-contract-smoke
make sprint13-natural-frozen-replay-v2-smoke
make sprint13-natural-terminal-attribution-v2-smoke
make public-docs-check
make planning-docs-check
```

Complete exact-source acceptance is owned by `make sprint13-p090-acceptance-smoke` in a qualified local environment.
