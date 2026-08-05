# Sprint 13 Plan

## Status

Entry candidate at Patch 078; activation pending acceptance. Patch 078 freezes a
private additive register-role decision for all 16 exact single-pop patterns and
corrects the remaining Patch 077 transaction, parity, Docker-source, cleanup,
and delivery blockers. Sprint 12 remains the active acceptance authority until
the complete Patch 078 gate passes.

Patch 078 changes no runtime classifier, reporter, schema, or score. Patch 079 is
the planned blinded task-value tranche that determines whether any private role
facet should become a release-facing semantic fact.

## Sprint goal

Close measured release-facing semantic gaps without turning x64lens into a
general-purpose decoder or chain generator.

## Planned deliverables

- [x] Freeze an additive private role decision for all exact single-pop GPR patterns without collapsing generic, call, syscall, syscall-number, or pivot roles.
- [x] Freeze `r10` as the private Linux syscall argument-4 role, distinct from System V call argument-4 `rcx`; public promotion remains task-value gated.
- [ ] Freeze release-facing score/null policy after blinded role task-value evidence; Patch 078 retains existing scores and leaves new role facets unscored.
- [ ] Use Sprint 11-12 diagnostics to select only bounded additional multi-pop, transfer, stack, or memory families that materially affect research tasks.
- [ ] Add exact fixtures, effects, false-positive boundaries, schema validation, and score decisions for any selected family.
- [ ] Record unsupported family gaps that remain outside the release scope.

## Patch sequence

1. **Patch 078:** correct Patch 077 acceptance blockers and freeze the private
   multi-role exact-pop decision with no public or score change.
2. **Patch 079:** preregister and execute blinded register-role task-value
   queries; decide whether public promotion is justified.
3. **Later evidence-selected patches:** complete score/null policy and add only
   bounded families that materially improve the frozen tasks.

## Acceptance criteria

- [ ] Every release-facing semantic family has controlled fixtures and complete represented effects or explicit partial state.
- [ ] Exact-only patterns are documented and machine-readable.
- [ ] No score is assigned without corresponding facts and rationale.
- [ ] New families preserve schema `0.2.x`, capacity, provenance, and deterministic output.
- [ ] Diagnostic results are restarted where task definitions change.

## Handoff

Sprint 14 tests optional validity and acceleration profiles against the stable
one-worker core.
