# Sprint 08 Plan

## Status

Closed. Sprint 8 is complete after Patch 039. Patch 030 opened the sprint with bounded dynamic-table parsing, Patch 031 refined RELRO evidence, Patch 032 added the first canary indicator, Patch 033 added the stripped-status indicator plus stricter dynamic string-table singleton policy, Patch 034 added section labels as analyst annotations, Patch 035 hardened section-label rendering and hostile overlap behavior, Patch 036 hardened historical review findings, Patch 037 closed comparator and benchmark-integrity gates, and Patch 038 attempted closeout helper hardening and Patch 039 corrected the closeout validation gaps, regenerated context handoff artifacts, and handed implementation sequencing to Sprint 9.

## Sprint goal

Increase mitigation and metadata accuracy without weakening loader-authority or parser-safety contracts.

## Planned deliverables

Sprint 8 should proceed in this order: bounded dynamic-table discovery, RELRO refinement, canary indicators, then optional section labels. Do not add primitive expansion until the new metadata paths pass deterministic malformed-input coverage.

- [x] Parse bounded `PT_DYNAMIC` entries required for `DT_BIND_NOW`, `DT_FLAGS`, and `DT_FLAGS_1` evidence. Implemented in Patch 030.
- [x] Distinguish no RELRO, partial RELRO, and full RELRO. Implemented in Patch 031.
- [x] Add canary indicators through bounded dynamic-string evidence. Implemented in Patch 032. Next refinement can use dynamic symbols or relocation evidence.
- [x] Add stripped-status indicators with explicit confidence wording. Implemented in Patch 033.
- [x] Add section labels for executable regions and candidate addresses as analyst annotations. Implemented in Patch 034 and hardened in Patch 035/Patch 036.
- [x] Preserve program headers as runtime mapping authority. Patch 035/Patch 036 keep labels subordinate, omit ambiguous overlap labels, and require file-offset plus virtual-address agreement.
- [x] Add controlled fixtures for no, partial, and full RELRO. Implemented in Patch 031.
- [x] Add controlled canary-present and canary-absent fixtures. Implemented in Patch 032.
- [x] Add automated `readelf` comparison checks. Implemented in Patch 037.
- [x] Add optional `checksec` and `rabin2 -I` comparison helpers when available. Implemented in Patch 037.
- [x] Extend JSON with compatible optional mitigation fields while schema remains `0.1.0`. Initial dynamic-table fields implemented in Patch 030.


## Recommended patch sequence

1. Bounded dynamic-section view for `PT_DYNAMIC` and `DT_*` entries. Completed in Patch 030.
2. RELRO evidence split into no, partial, and full states using controlled fixtures. Completed in Patch 031.
3. Canary indicator with explicit confidence wording. Completed in Patch 032.
4. Stripped-state indicator as section-derived metadata only. Completed in Patch 033.
5. Section labels as analyst annotations only, never as runtime mapping authority. Completed in Patch 034 and hardened in Patch 035/Patch 036.
6. Automated comparison helpers against `readelf` and optional external tools. Completed in Patch 037.
7. Sprint 8 closeout, optional-helper hardening, retrospective documentation, and Sprint 9 handoff. Initial closeout in Patch 038; accepted after correction in Patch 039.

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

## Patch 036 historical findings hardening update

Patch 036 is the historical-findings hardening pass after historical review. It does not expand primitives. It fixes byte-safe JSON rendering, label trust rules, Docker context hygiene, benchmark evidence hygiene, JSON validator consistency, temporary-output isolation, and robust diagnostics. Patch 037 closes the planned readelf/checksec/rabin2 comparison deliverables and fixes the Patch 036 benchmark summarizer finite-number gap. Patch 038 hardened optional comparator helper argument validation and published the Sprint 8 retrospective; Patch 039 corrected the missing benchmark-integrity RSS fixtures, strict shell lint findings, and stale private context handoff before final Sprint 8 acceptance.
