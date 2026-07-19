# Sprint 15 Plan

## Status

Planned campaign-freeze sprint.

## Sprint goal

Freeze the corpus, schema/extractor, runner, baseline versions, commands, task
definitions, and environment strata for preview and publication measurement.

## Planned deliverables

- [ ] Final Tier 1-4 corpus manifest and regeneration workflow.
- [ ] Target/source/tool hashes and redistribution/license records.
- [ ] Frozen x64lens commit, schema, extractor, benchmark runner, max depth, and output modes.
- [ ] Frozen baseline versions and exact commands.
- [ ] Frozen warmup, ordering, affinity, cache, timer-floor, and batching policies.
- [ ] Coverage-definition reconciliation specification for every tool/profile.
- [ ] Campaign identifier and restart procedure.
- [ ] Clean preview of every condition with no missing metadata.

## Acceptance criteria

- [ ] Every target and tool is immutable and authenticated.
- [ ] Every compared task is explicitly defined.
- [ ] No release-blocking capability gate remains unresolved.
- [ ] Any later method or semantic change requires a new campaign or complete rerun.
- [ ] Private or proprietary binaries are not required for reproduction.

## Handoff

Sprint 16 runs the frozen pilot and prepares the research preview candidate.
