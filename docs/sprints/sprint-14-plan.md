# Sprint 14 Plan

## Status

Planned optional-profile ablation sprint.

## Sprint goal

Measure candidate-scoped decoder validation and deterministic concurrency
without changing the dependency-free one-worker reference profile.

## Planned deliverables

- [ ] Candidate-scoped decoder prototype or external adapter over retained candidate starts when the measured gap justifies it.
- [ ] Target-level concurrency baseline.
- [ ] Candidate-validation worker prototype when output-order and cleanup contracts can be preserved.
- [ ] Region-worker experiment only after overlap, deduplication, and global capacity rules are fixed.
- [ ] Separate binary/dependency identity, license, startup, wall, CPU, max RSS, output hash, and evidence counts by profile and worker count.
- [ ] Deterministic output and failure/cleanup regression tests.
- [ ] Decision record: retain optional profile, defer it, or reject it for `v0.1.0`.

## Acceptance criteria

- [ ] The reference profile remains available and unchanged.
- [ ] Optional profiles never erase raw or exact evidence.
- [ ] Parallel results are byte/fact-identical after documented ordering.
- [ ] One global candidate-capacity outcome is preserved.
- [ ] Interruptions reap every worker/helper process.
- [ ] No optional profile becomes default without measured benefit and accepted cost.

## Handoff

Sprint 15 freezes the release campaign definitions after all accepted profile and
capability decisions are complete.
