# Sprint 11 Plan

## Status

Active diagnostic measurement sprint after Sprint 10 Patch 054 closeout.
Patches 055 and 056 implement the runner, task-definition, and provisional
corpus foundations. Patch 057 corrects the first runner, corpus, cleanup, and
validation-integrity findings. Patch 058 adds bounded task-normalized baseline
adapters and addresses additional evidence-integrity gaps found during Patch 057
validation. Patch 059 corrects adapter-to-row binding and establishes matched relations,
bounded runtime closure, coordinate calibration, and the pre-execution campaign
plan. Patch 060 corrects the remaining evidence-integrity findings, executes the
available-tool 30-condition campaign, retains unavailable conditions, generates
task-scoped summaries, and writes the engineering gap register. Patch 061
remains the Sprint 11 closeout.

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
- [x] Hashed retained runner inputs, executable write-sealed tool/probe copies,
  non-executable execution-sealed target copies, source/license/builder
  snapshots, compiler/linker identities, exact build
  commands, generated-output hashes, and environment metadata.
- [x] Timer-floor measurement, below-floor labeling, warmup retention,
  counterbalanced ordering, and explicit warm/uncontrolled cache policy.
- [x] Machine-readable task authority for gadget JSON and analyze JSON, with the
  current command-only parity relationship stated explicitly.
- [x] Explicitly mark scanner-only cost unavailable instead of substituting
  report timing for a nonexistent core condition.
- [ ] Add a scanner-only profile only if diagnostic evidence justifies a
  reviewed report-suppression or instrumentation seam.
- [x] Initial baseline task records for ROPgadget, Ropper, and ropr.
- [x] Versioned task-normalized baseline adapters with supplied-command
  reconciliation, bounded native stdout/stderr, authenticated tool, target,
  retained version-output, and native-stream files, duplicate preservation, and
  a canonical `pop rdi; ret` relation over represented instruction text.
- [x] Bind normalized artifacts to runner rows, campaign manifests, child
  outcomes, and capture identities before development summaries are generated.
- [x] Add matched x64lens report-derived relations, bounded runtime closure,
  manifest-bound coordinate calibration, and a fully accounted pre-execution
  24-comparison plus six-control plan.
- [x] Controlled reference diagnostic campaign with development run counts.
- [x] Provisional corpus campaign with complete condition accounting, generated task-scoped summaries, and an evidence-backed capability/performance gap register; unavailable baselines remain explicit environment states.
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
3. **Patch 057 (implemented candidate):** smallest diagnostic-integrity
   correction for non-executable target inputs, exact corpus workspace/member
   closure, checked staging cleanup, safe corpus removal, and non-root oracle
   parity.
4. **Patch 058 (implemented candidate):** additional runner/corpus integrity
   corrections plus normalized ROPgadget, Ropper, and ropr native-output
   adapters with bounded capture, supplied-command and artifact authentication,
   conservative represented-text parsing, and failure-preserving evidence.
5. **Patch 059 (implementation candidate):** correct remaining transaction and
   adapter-binding failures; establish report-derived matched x64lens relations,
   bounded runtime closure, manifest-bound coordinate calibration, and the
   pre-execution 30-condition stage-zero plan. No comparative campaign or gap
   register is produced.
6. **Patch 060 (implementation candidate):** correct the remaining Patch 059
   evidence-integrity findings; execute the authenticated available-tool
   24-comparison plus six-control campaign; retain unavailable states; generate
   task-scoped summaries; and write the engineering gap register that directs
   Sprints 12 through 14.
7. **Patch 061 (planned):** Sprint 11 closeout and diagnostic checkpoint review,
   subject to findings from the preceding patches.

The exact later patch count remains evidence-driven; the sequence describes the
intended responsibility boundaries rather than a calendar guarantee.

## Acceptance criteria

- [x] Every runner row is bound to immutable tool and target bytes whose hashes
  match retained campaign files; target inputs additionally require a kernel-
  enforced execution seal.
- [x] Failed runs, signals, timeouts, and extractor failures are retained rather
  than dropped.
- [x] Timing below the provisional reliable floor is labeled and cannot support
  an unqualified single-process interpretation.
- [x] Tool scope and output work are stated for every current condition.
- [x] Baseline native output, duplicates, task-specific totals, and the first
  canonical exact relation remain separate and authenticated.
- [x] Matched x64lens relations are derived from retained reports, address
  coordinates remain unaggregated until role-specific calibration succeeds, and
  runtime closure remains bounded observed evidence.
- [x] Campaign publication is transactional and refuses to replace an existing
  result identity.
- [x] Measured process groups and escaped adopted descendants are cleaned up and reaped.
- [x] No diagnostic result is presented as publication-grade superiority
  evidence.
- [x] The provisional corpus regenerates byte/mode/mtime-identically twice and
  remains explicitly diagnostic, unfrozen, and not publication eligible.
- [x] The generated gap register identifies concrete Sprint 12 and Sprint 13
  priorities from authenticated x64lens observations while preserving baseline
  unavailability and below-floor timing as non-product limitations.

## Out of scope

- Final corpus freeze.
- Publication repeated trials.
- Final score or coverage claims.
- Mandatory decoder or worker profiles.
- Runtime dependencies added for benchmark orchestration.

## Handoff

Planned Patch 060 produces the diagnostic evidence and gap register, and planned
Patch 061 closes Sprint 11. Sprint 12 then uses that evidence to prioritize
loader and mitigation precision without changing the reference scanner
definition. A behavior, schema, task, or method change after a diagnostic
campaign receives a new campaign identifier; Sprint 15 remains the confirmatory
freeze.
