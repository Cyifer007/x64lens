# Sprint 11 Retrospective

## Outcome

Sprint 11 established and hardened the diagnostic measurement system required
before release-facing capability and benchmark decisions are frozen.

Completed work includes:

- a monotonic nanosecond runner with retained process, output, and resource
  evidence;
- timer-floor measurement, warmups, counterbalanced ordering, and explicit
  below-floor state;
- a reproducible 24-target GCC/Clang corpus with source, tool, command, license,
  and output identity;
- task-normalized ROPgadget, Ropper, and ropr adapters;
- matched x64lens relation extraction;
- task-path runtime-closure evidence;
- address-coordinate calibration with explicit blocked states;
- a 30-condition provisional campaign authority;
- generated summaries and an engineering gap register;
- transaction, cleanup, archive, and rollback-destination identity hardening.

## What the measurements showed

The earlier cloud checkpoint accounted for all 30 planned conditions: 12
x64lens conditions executed and 18 baseline conditions were retained as
unavailable. A later WSL2 replay recorded 30/30 conditions and 180/180
successful runner rows, with 24 relation artifacts. All 12 x64lens timings were
below the 6,361,100 ns reliable single-process floor.

Two Python task-path runtime-closure failures left those closures incomplete,
and coordinate calibration failed. The replay therefore was not
comparison-qualified and did not replace the required fresh, unmodified Patch
061 campaign. Baseline-native totals differed substantially, but those totals
reflect different discovery, filtering, duplicate, and canonicalization
policies and are not a common gadget metric.

The first normalized exact relation was absent across the selected targets. That
negative observation was insufficient for coordinate calibration and broad
coverage conclusions. The reports did expose a repeated exact-only
`pop rbp; ret` semantic gap, which supports the planned Sprint 13 generic-pop
role decision.

All checkpoint, replay, relation, timing, summary, and gap-register evidence
remains diagnostic, unfrozen, and publication-ineligible.

## What changed because of the evidence

- Single-run timing below the floor is no longer summarized as zero or success-
  eligible latency.
- Native execution and comparison qualification are independent states.
- Coordinate calibration requires positive role-controlled anchors.
- Python baseline closure retains isolated-environment launcher and prefix
  identity.
- A whole-batch policy is preregistered for unresolved fast conditions, without
  dividing batch time into claimed single-run latency.
- Cross-tool reporting rejects generic gadget counts and preserves each native
  population.

## What did not change

The analyzer remains:

```text
dependency-free
decoder-free
one-worker
bounded to 4096 candidates
deterministic
program-header authoritative
fail-closed on incomplete output
```

Sprint 11 added external development infrastructure and evidence. It did not
change analyzer assembly, schema `0.2.0`, candidate records, score policy, or the
819,200-byte command arena.

## Limitations carried forward

- A fresh unmodified all-tools campaign is required after Patch 061.
- Single-run x64lens latency remains unresolved for the small provisional
  targets.
- Process-tree RSS requires a calibrated scope beyond direct wait accounting.
- Address comparisons require positive coordinate anchors.
- The six-target screen cannot attribute compiler, optimization, linkage, or
  hardening effects independently.
- Diagnostic evidence remains mutable and cannot be relabeled as confirmatory.

## Contract review

The architecture, development, evidence, metric, release, and documentation
contracts remain valid. Patch 061 strengthens benchmark transaction and
rollback-destination identity without changing runtime product contracts.

## Sprint 12 handoff

Sprint 12 starts with bounded program-header validity and extended-numbering
outcomes, executable-overlap/provenance semantics, PIE-versus-DSO identity, and
GNU-property IBT/SHSTK evidence. Every new parser path requires checked ranges,
hostile fixtures, no-partial-output behavior, native/container agreement, and a
new diagnostic campaign identity. A private-fact diagnostic matrix is a
distinct gate with separate natural and controlled metamorphic strata. A
separate comparison-qualification campaign requires positive role-controlled
coordinate anchors and complete runtime closure for all five task paths.
