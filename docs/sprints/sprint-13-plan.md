# Sprint 13 Plan

## Status

Patch 080 private register-role candidate; activation pending complete Patch 080 acceptance.
Patch 078 froze the private additive role authority. Patch 079 corrects the
remaining acceptance tooling and executes the preregistered task-value gate.
`generic_control`, `sysv_call_arguments`, and `linux_syscall_arguments` qualify
only as private task-value evidence for the next LC-08B policy decision.
`syscall_number` and `stack_pivot` remain deferred by the Patch 079 task gate;
their existing runtime semantics and scores remain unchanged. No runtime class,
public field, score, or schema changes in Patch 079.

## Sprint goal

Close measured release-facing semantic gaps without turning x64lens into a
general-purpose decoder or chain generator.

## Planned deliverables

- [x] Freeze an additive private role decision for all exact single-pop GPR patterns without collapsing generic, call, syscall, syscall-number, or pivot roles.
- [x] Freeze `r10` as the private Linux syscall argument-4 role, distinct from
  System V call argument-4 `rcx`; any public promotion remains deferred to the
  later LC-08B policy gate.
- [x] Record the LC-08B private/public/score decision in Patch 080; public and score projection remain deferred. Patch 079
  retains existing scores and leaves every private role facet unscored.
- [ ] Use Sprint 11-12 diagnostics to select only bounded additional multi-pop, transfer, stack, or memory families that materially affect research tasks.
- [ ] Add exact fixtures, effects, false-positive boundaries, schema validation, and score decisions for any selected family.
- [ ] Record unsupported family gaps that remain outside the release scope.

## Patch sequence

1. **Patch 078:** correct Patch 077 acceptance blockers and freeze the private
   multi-role exact-pop decision with no public or score change.
2. **Patch 079:** preregister and execute deterministically label-permuted
   register-role task-value queries; retain the result as private policy input.
3. **Later evidence-selected patches:** complete score/null policy and add only
   bounded families that materially improve the frozen tasks.

3. **Patch 080:** correct Patch 079, execute the corrected disjoint task and
   LC-08B policy gates, and add the private register-role side-car.
4. **Patch 081:** run the ordered two-pop role-tuple pilot or the next
   independently selected bounded semantic gate after Patch 080 acceptance.

## Acceptance criteria

- [ ] Every release-facing semantic family has controlled fixtures and complete represented effects or explicit partial state.
- [ ] Exact-only patterns are documented and machine-readable.
- [ ] No score is assigned without corresponding facts and rationale.
- [ ] New families preserve schema `0.2.x`, capacity, provenance, and deterministic output.
- [ ] Diagnostic results are restarted where task definitions change.

## Handoff

Sprint 14 tests optional validity and acceleration profiles against the stable
one-worker core.


## Patch 079 boundary

The role-task gate contains five independent strata with eight development and
four untouched confirmation tasks each. A stratum requires at least two
development gains, zero regressions, zero incorrect promotions, four of four
correct confirmation tasks, and at least one confirmation gain. Three strata
qualify only as private task-value evidence; `syscall_number` and `stack_pivot`
remain deferred. Passing does not authorize classifier, reporter, schema, or
score changes, and results cannot be pooled across strata.

Patch 080 should execute LC-08B against only the qualified private facets and
make an explicit runtime/public/score decision with complete fixtures, effects,
false-positive boundaries, schema compatibility, and diagnostic restart rules.
