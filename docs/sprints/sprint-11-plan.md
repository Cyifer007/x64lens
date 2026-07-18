# Sprint 11 Plan

## Status

Planned.

## Sprint goal

Create a reproducible corpus and manifest that can support fixed research experiments rather than host-dependent smoke checks.

## Entry gate from Sprint 10 capability review

Sprint 11 corpus membership must not freeze ambiguous analyzer facts. Before corpus generation begins, Patch 051/052 must resolve or explicitly defer:

- PIE executable versus shared-object interpretation for `ET_DYN`;
- bounded GNU property evidence for CET/IBT/SHSTK;
- overlapping executable `PT_LOAD` region/count semantics;
- score policy for the new Sprint 10 families;
- capability-snapshot items classified as pre-release requirements.

The result must identify which expected corpus facts are machine-checkable and which remain explicit unknowns or limitations.

## Planned deliverables

- [ ] Build controlled binaries across GCC and Clang when available.
- [ ] Include selected optimization levels and linkage modes.
- [ ] Include PIE, stack-protector, RELRO, executable-stack, and static/dynamic variants.
- [ ] Include CET/IBT build variants when the host toolchain supports them.
- [ ] Record source hash, compiler version, exact command, output hash, file size, and expected mitigation facts.
- [ ] Add a manifest validator.
- [ ] Add corpus regeneration commands that do not depend on private inputs.
- [ ] Define fixed Tier 1 through Tier 4 corpus membership for the preview campaign.
- [ ] Record license and redistribution status for larger open-source targets.

## Acceptance criteria

- [ ] Controlled corpus outputs can be regenerated from public source and commands.
- [ ] Every benchmark target has a SHA-256 hash.
- [ ] Expected mitigation states are machine-checkable.
- [ ] Corpus membership is versioned and reviewable.
- [ ] Benchmark scripts consume the manifest without manual target edits.
- [ ] Private or proprietary binaries are not required for core reproduction.

## Out of scope

- Final repeated benchmark campaign.
- Network infrastructure case-study conclusions.
- Multi-architecture corpus support.

## Handoff

Sprint 12 freezes a preview corpus and adds higher-resolution benchmark infrastructure before the `v0.1.0-rc1` gate.
