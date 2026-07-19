# Sprint 13 Plan

## Status

Planned semantic capability completion sprint.

## Sprint goal

Close measured release-facing semantic gaps without turning x64lens into a
general-purpose decoder or chain generator.

## Planned deliverables

- [ ] Decide and implement or explicitly reject a generic semantic role for all exact single-pop GPR patterns.
- [ ] Add the Linux syscall `r10` argument-control role when syscall setup remains a release-facing capability.
- [ ] Freeze score/null policy for every release-facing exact family.
- [ ] Use Sprint 11-12 diagnostics to select only bounded additional multi-pop, transfer, stack, or memory families that materially affect research tasks.
- [ ] Add exact fixtures, effects, false-positive boundaries, schema validation, and score decisions for any selected family.
- [ ] Record unsupported family gaps that remain outside the release scope.

## Acceptance criteria

- [ ] Every release-facing semantic family has controlled fixtures and complete represented effects or explicit partial state.
- [ ] Exact-only patterns are documented and machine-readable.
- [ ] No score is assigned without corresponding facts and rationale.
- [ ] New families preserve schema `0.2.x`, capacity, provenance, and deterministic output.
- [ ] Diagnostic results are restarted where task definitions change.

## Handoff

Sprint 14 tests optional validity and acceleration profiles against the stable
one-worker core.
