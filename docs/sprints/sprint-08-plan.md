# Sprint 08 Plan

## Status

Active. Sprint 8 is the current public implementation tranche after Sprint 7 closeout. Patch 030 opened the sprint with bounded dynamic-table parsing, Patch 031 refined RELRO evidence, Patch 032 added the first canary indicator, Patch 033 added the stripped-status indicator plus stricter dynamic string-table singleton policy, and Patch 034 adds section labels as analyst annotations, and Patch 035 hardens section-label rendering and hostile overlap behavior.

## Sprint goal

Increase mitigation and metadata accuracy without weakening loader-authority or parser-safety contracts.

## Planned deliverables

Sprint 8 should proceed in this order: bounded dynamic-table discovery, RELRO refinement, canary indicators, then optional section labels. Do not add primitive expansion until the new metadata paths pass deterministic malformed-input coverage.

- [x] Parse bounded `PT_DYNAMIC` entries required for `DT_BIND_NOW`, `DT_FLAGS`, and `DT_FLAGS_1` evidence. Implemented in Patch 030.
- [x] Distinguish no RELRO, partial RELRO, and full RELRO. Implemented in Patch 031.
- [x] Add canary indicators through bounded dynamic-string evidence. Implemented in Patch 032. Next refinement can use dynamic symbols or relocation evidence.
- [x] Add stripped-status indicators with explicit confidence wording. Implemented in Patch 033.
- [x] Add section labels for executable regions and candidate addresses as analyst annotations. Implemented in Patch 034 and hardened in Patch 035.
- [x] Preserve program headers as runtime mapping authority. Patch 035 keeps labels subordinate and omits ambiguous overlap labels.
- [x] Add controlled fixtures for no, partial, and full RELRO. Implemented in Patch 031.
- [x] Add controlled canary-present and canary-absent fixtures. Implemented in Patch 032.
- [ ] Add automated `readelf` comparison checks.
- [ ] Add optional `checksec` and `rabin2 -I` comparison helpers when available.
- [x] Extend JSON with compatible optional mitigation fields while schema remains `0.1.0`. Initial dynamic-table fields implemented in Patch 030.


## Recommended patch sequence

1. Bounded dynamic-section view for `PT_DYNAMIC` and `DT_*` entries. Completed in Patch 030.
2. RELRO evidence split into no, partial, and full states using controlled fixtures. Completed in Patch 031.
3. Canary indicator with explicit confidence wording. Completed in Patch 032.
4. Stripped-state indicator as section-derived metadata only. Completed in Patch 033.
5. Section labels as analyst annotations only, never as runtime mapping authority. Completed in Patch 034 and hardened in Patch 035.
6. Automated comparison helpers against `readelf` and optional external tools. Deferred until after the historical review pause.

## Acceptance criteria

- [x] Full and partial RELRO match controlled synthetic loader configurations.
- [x] Canary output is labeled as an indicator, not proof of complete stack protection.
- [x] Missing dynamic-string metadata produces canary `unknown` instead of a guessed negative.
- [x] Stripped status remains section-derived metadata only and never changes executable-region boundaries.
- [x] Section labels never change executable-region boundaries. Text labels are escaped and ambiguous executable overlap remains unlabeled.
- [x] The first dynamic table references are range-checked and bounded. Future symbol, string, relocation, section, and note references remain gated.
- [x] Existing report count semantics remain unchanged through the RELRO refinement.
- [x] Malformed mitigation-matrix coverage includes dynamic-table range, entry-size, duplicate-table, duplicate dynamic-string singleton, dynamic string-table reference, and string-table scan-cap mutations. Future symbol, relocation, section, and note mutations remain planned.

## Out of scope

- CET/IBT policy conclusions.
- Broad symbol recovery.
- Full disassembly.
- Primitive expansion.

## Handoff

After the planned historical review pause, Sprint 9 adds candidate evidence provenance, truncation/completeness state, and the schema `0.2.0` transition needed before research preview output freezes.
