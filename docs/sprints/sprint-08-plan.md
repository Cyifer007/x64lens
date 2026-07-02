# Sprint 08 Plan

## Status

Next. Sprint 8 is the next public implementation tranche after Sprint 7 closeout. Patch 030 opens the sprint with bounded dynamic-table parsing.

## Sprint goal

Increase mitigation and metadata accuracy without weakening loader-authority or parser-safety contracts.

## Planned deliverables

Sprint 8 should proceed in this order: bounded dynamic-table discovery, RELRO refinement, canary indicators, then optional section labels. Do not add primitive expansion until the new metadata paths pass deterministic malformed-input coverage.

- [x] Parse bounded `PT_DYNAMIC` entries required for `DT_BIND_NOW`, `DT_FLAGS`, and `DT_FLAGS_1` evidence. Implemented in Patch 030.
- [ ] Distinguish no RELRO, partial RELRO, and full RELRO.
- [ ] Add canary indicators through bounded dynamic-symbol, symbol-table, or relocation evidence.
- [ ] Add stripped-status indicators with explicit confidence wording.
- [ ] Add section labels for executable regions and candidate addresses as analyst annotations.
- [ ] Preserve program headers as runtime mapping authority.
- [ ] Add controlled fixtures for no, partial, and full RELRO.
- [ ] Add controlled canary-present and canary-absent fixtures.
- [ ] Add automated `readelf` comparison checks.
- [ ] Add optional `checksec` and `rabin2 -I` comparison helpers when available.
- [x] Extend JSON with compatible optional mitigation fields while schema remains `0.1.0`. Initial dynamic-table fields implemented in Patch 030.


## Recommended patch sequence

1. Bounded dynamic-section view for `PT_DYNAMIC` and `DT_*` entries. Completed in Patch 030.
2. RELRO evidence split into no, partial, and full states using controlled fixtures.
3. Canary and stripped-state indicators with explicit confidence wording.
4. Section labels as analyst annotations only, never as runtime mapping authority.
5. Automated comparison helpers against `readelf` and optional external tools.

## Acceptance criteria

- [ ] Full and partial RELRO match controlled linker configurations.
- [ ] Canary output is labeled as an indicator, not proof of complete stack protection.
- [ ] Missing metadata produces `unknown` or equivalent explicit state instead of a guessed negative.
- [ ] Section labels never change executable-region boundaries.
- [x] The first dynamic table references are range-checked and bounded. Future symbol, string, relocation, section, and note references remain gated.
- [ ] Existing report count semantics remain unchanged.
- [x] Malformed mitigation-matrix coverage includes dynamic-table range and entry-size mutations. Future symbol, string, and section metadata mutations remain planned.

## Out of scope

- CET/IBT policy conclusions.
- Broad symbol recovery.
- Full disassembly.
- Primitive expansion.

## Handoff

Sprint 9 adds candidate evidence provenance, truncation/completeness state, and the schema `0.2.0` transition needed before research preview output freezes.
