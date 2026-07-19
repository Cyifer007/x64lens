# Sprint 11 Plan

## Status

Active diagnostic measurement sprint after Sprint 10 Patch 054 closeout.
Patch 055 implements the runner and task-definition foundation; corpus,
baseline, summary, and gap-register work remains active.

## Sprint goal

Build the high-resolution benchmark runner and a provisional reproducible corpus
so measurements can guide capability work without freezing the publication
campaign prematurely.

## Planned deliverables

- [x] Standard-library runner using monotonic nanosecond timing and Linux direct-
  child resource usage, with descendant resources explicitly non-aggregate.
- [x] Wall, user, system, maximum RSS, faults, context switches, output bytes,
  exit status, signal state, tool hash, and target hash per row.
- [ ] Provisional GCC/Clang corpus across selected optimization, linkage, and
  hardening combinations.
- [x] Immutable tool/target snapshots, source and output hashes, target license,
  tool version output, and environment metadata for the initial controlled
  conditions.
- [x] Timer-floor measurement, below-floor labeling, warmup retention,
  counterbalanced ordering, and explicit warm/uncontrolled cache policy.
- [x] Machine-readable task authority for gadget JSON and analyze JSON, with the
  current command-only parity relationship stated explicitly.
- [x] Explicitly mark scanner-only cost unavailable instead of substituting
  report timing for a nonexistent core condition.
- [ ] Add a scanner-only profile only if diagnostic evidence justifies a
  reviewed report-suppression or instrumentation seam.
- [x] Initial baseline task records for ROPgadget, Ropper, and ropr, marked
  planned pending command and candidate-definition normalization.
- [ ] Implement baseline adapters and version-lock capture.
- [x] Controlled reference diagnostic campaign with development run counts.
- [ ] Provisional corpus campaign and capability/performance gap register.
- [x] Explicit separation of diagnostic rows from future frozen campaign rows.

## Patch sequence

1. **Patch 055:** correct the Patch 054 validation false negatives; add the
   standard-library high-resolution runner, process-tree cleanup, immutable
   snapshots, timer-floor evidence, initial task authority, and controlled
   reference conditions.
2. **Patch 056:** provisional corpus manifest and regeneration workflow,
   including compiler, optimization, linkage, hardening, source, output, hash,
   and license provenance.
3. **Patch 057:** normalized ROPgadget, Ropper, and ropr task adapters with
   version identity and failure-preserving rows.
4. **Patch 058:** development summaries, coverage reconciliation inputs, and the
   engineering gap register that directs Sprints 12 through 14.
5. **Patch 059:** Sprint 11 closeout and diagnostic checkpoint review, subject to
   findings from the preceding patches.

The exact later patch count remains evidence-driven; the sequence describes the
intended responsibility boundaries rather than a calendar guarantee.

## Acceptance criteria

- [x] Every runner row is bound to immutable tool and target bytes.
- [x] Failed runs, signals, timeouts, and extractor failures are retained rather
  than dropped.
- [x] Timing below the provisional reliable floor is labeled and cannot support
  an unqualified single-process interpretation.
- [x] Tool scope and output work are stated for every current condition.
- [x] Campaign publication is transactional and refuses to replace an existing
  result identity.
- [x] Measured process groups and escaped adopted descendants are cleaned up and reaped.
- [x] No diagnostic result is presented as publication-grade superiority
  evidence.
- [ ] The provisional corpus and baseline campaign cover enough conditions to
  produce a concrete Sprint 12-14 gap register.

## Out of scope

- Final corpus freeze.
- Publication repeated trials.
- Final score or coverage claims.
- Mandatory decoder or worker profiles.
- Runtime dependencies added for benchmark orchestration.

## Handoff

Sprint 12 uses diagnostic evidence to prioritize loader and mitigation precision
without changing the reference scanner definition. A behavior, schema, task, or
method change after a diagnostic campaign receives a new campaign identifier;
Sprint 15 remains the confirmatory freeze.
