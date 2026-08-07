# Sprint 13 Plan

## Status

Patch 081 ordered two-pop decision candidate; activation pending complete Patch 081 acceptance.
Patch 080 retains `generic_control`, `sysv_call_arguments`, and
`linux_syscall_arguments` only in the private side-car while public projection
and score changes remain deferred. Patch 081 corrects the remaining acceptance
and delivery boundary, records the Sprint 12 retrospective, and evaluates
whether a new ordered two-pop tuple representation adds value beyond existing
`stack_pop_order` facts. The pilot records zero incremental gains and therefore
defers the redundant runtime representation. Existing multi-pop semantics and
score 95 remain unchanged.

## Sprint goal

Close measured release-facing semantic gaps without turning x64lens into a
general-purpose decoder or chain generator.

## Planned deliverables

- [x] Freeze an additive private role decision for all exact single-pop GPR patterns without collapsing generic, call, syscall, syscall-number, or pivot roles.
- [x] Freeze `r10` as the private Linux syscall argument-4 role, distinct from
  System V call argument-4 `rcx`; Patch 080 retains both mappings privately and
  defers public promotion.
- [x] Record the LC-08B private/public/score decision in Patch 080; public and score projection remain deferred. Patch 079
  retains existing scores and leaves every private role facet unscored.
- [x] Execute the bounded ordered two-pop role-tuple pilot. Existing exact ordered-pop facts answer all frozen tasks, so no new runtime record is added.
- [x] Freeze the complete score/null partition: 25 exact patterns, 14 scored, 11 null, and three private role facets retained null.
- [ ] Use Sprint 11-12 diagnostics to select only bounded additional multi-pop, transfer, stack, or memory families that materially affect research tasks.
- [ ] Add exact fixtures, effects, false-positive boundaries, schema validation, and score decisions for any selected family.
- [ ] Record unsupported family gaps that remain outside the release scope.

## Patch sequence

1. **Patch 078:** correct Patch 077 acceptance blockers and freeze the private
   multi-role exact-pop decision with no public or score change.
2. **Patch 079:** execute the original non-causal, deterministically ordered
   register-role task-value queries; retain the result as private policy input.
3. **Patch 080:** correct Patch 079, execute the corrected disjoint task and
   LC-08B policy gates, and add the private register-role side-car.
4. **Patch 081:** correct Patch 080, record the Sprint 12 retrospective, run
   the ordered two-pop task-value pilot, defer a zero-gain tuple record, and
   freeze the complete score/null authority without runtime or public changes.
5. **Later evidence-selected patches:** add only bounded families or consumers
   that demonstrate incremental task value.

## Acceptance criteria

- [ ] Every release-facing semantic family has controlled fixtures and complete represented effects or explicit partial state.
- [ ] Exact-only patterns are documented and machine-readable.
- [ ] No score is assigned without corresponding facts and rationale.
- [ ] New families preserve schema `0.2.x`, capacity, provenance, and deterministic output.
- [ ] Diagnostic results are restarted where task definitions change.

## Handoff

Sprint 14 tests optional validity and acceleration profiles against the stable
one-worker core.


## Historical Patch 079 boundary

The Patch 079 role-task gate contained five independent strata with eight
development and four confirmation-labeled tasks each. Patch 080 found query
reuse across those partitions and replaced the task authority. Under the
original gate, a stratum required at least two development gains, zero
regressions, zero incorrect promotions, four of four correct confirmation
tasks, and at least one confirmation gain. Three strata qualified only as
private task-value evidence; `syscall_number` and `stack_pivot` remained
deferred. Passing did not authorize classifier, reporter, schema, or score
changes, and results could not be pooled across strata.

Patch 080 records the LC-08B decision for only the qualified private facets: it
retains them in a private additive side-car while deferring public and score
projection. Complete Patch 080 acceptance remains required before the next
Sprint 13 tranche.
