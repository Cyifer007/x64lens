# Sprint 11 Plan

## Status

Active diagnostic measurement sprint after Sprint 10 Patch 054 closeout.

## Sprint goal

Build the high-resolution benchmark runner and a provisional reproducible corpus
so measurements can guide capability work without freezing the publication
campaign prematurely.

## Planned deliverables

- [ ] Standard-library runner using monotonic nanosecond timing and per-child resource usage.
- [ ] Wall, user, system, max RSS, output bytes, exit status, tool hash, and target hash per row.
- [ ] Provisional GCC/Clang corpus across selected optimization, linkage, and hardening combinations.
- [ ] Exact build commands, source hashes, output hashes, licenses, and environment metadata.
- [ ] Timer-floor measurement and batching/larger-target policy.
- [ ] Separate core scanner, gadget JSON, and integrated `analyze` conditions.
- [ ] Baseline task-definition matrix for ROPgadget, Ropper, and ropr.
- [ ] Diagnostic campaign with development run counts and a capability/performance gap register.
- [ ] Explicit separation of diagnostic rows from future frozen campaign rows.

## Acceptance criteria

- [ ] Every row is reproducible and bound to immutable tool and target bytes.
- [ ] Failed runs are retained rather than dropped.
- [ ] Timing below the reliable floor is batched or labeled accordingly.
- [ ] Tool scope and output work are stated for every comparison.
- [ ] No diagnostic result is presented as publication-grade superiority evidence.
- [ ] The gap register identifies concrete Sprint 12-14 decisions.

## Out of scope

- Final corpus freeze.
- Publication repeated trials.
- Final score or coverage claims.

## Handoff

Sprint 12 uses diagnostic evidence to prioritize loader and mitigation precision
without changing the reference scanner definition.
