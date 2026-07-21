# Sprint 11 Plan

## Status

Active diagnostic measurement sprint after Sprint 10 Patch 054 closeout.
Patches 055 and 056 implement the runner, task-definition, and provisional
corpus foundations; baseline adapters, summaries, and the gap register remain
active.

## Sprint goal

Build the high-resolution benchmark runner and a provisional reproducible corpus
so measurements can guide capability work without freezing the publication
campaign prematurely.

## Planned deliverables

- [x] Standard-library runner using monotonic nanosecond timing and Linux
  `wait4` resource usage, with selected-child, waited-descendant, and separately
  reaped-descendant scopes stated explicitly.
- [x] Wall, user, system, maximum RSS, faults, context switches, output bytes,
  exit status, signal state, tool hash, and target hash per row.
- [x] Provisional 24-target GCC/Clang corpus across `O0`/`O2`, requested
  executable/PIE/shared roles, and minimal/hardened combinations.
- [x] Hashed retained runner inputs, write-sealed diagnostic execution copies,
  source/license/builder snapshots, compiler/linker identities, exact build
  commands, generated-output hashes, and environment metadata.
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
   standard-library high-resolution runner, process-tree cleanup, hash-bound
   write-sealed inputs, final artifact reconciliation, timer-floor evidence,
   initial task authority, and controlled reference conditions.
2. **Patch 056 (implemented):** provisional 24-target corpus manifest and
   transactional regeneration workflow, including compiler, optimization,
   requested role, hardening, source, output, command, hash, environment, and
   license provenance.
3. **Patch 057:** normalized ROPgadget, Ropper, and ropr task adapters with
   version identity and failure-preserving rows.
4. **Patch 058:** development summaries, coverage reconciliation inputs, and the
   engineering gap register that directs Sprints 12 through 14.
5. **Patch 059:** Sprint 11 closeout and diagnostic checkpoint review, subject to
   findings from the preceding patches.

The exact later patch count remains evidence-driven; the sequence describes the
intended responsibility boundaries rather than a calendar guarantee.

## Acceptance criteria

- [x] Every runner row is bound to write-sealed tool and target bytes whose
  hashes match retained campaign files.
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
- [x] The provisional corpus regenerates byte/mode/mtime-identically twice and
  remains explicitly diagnostic, unfrozen, and not publication eligible.
- [ ] The baseline campaign covers enough conditions to produce a concrete
  Sprint 12-14 gap register.

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
