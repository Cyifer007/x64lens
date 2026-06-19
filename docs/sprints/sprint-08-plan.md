# Sprint 08 Plan

## Status

Planned.

## Sprint goal

Increase mitigation and metadata accuracy without weakening loader-authority or parser-safety contracts.

## Planned deliverables

- [ ] Parse bounded `PT_DYNAMIC` entries required for `DT_BIND_NOW`, `DT_FLAGS`, and `DT_FLAGS_1` evidence.
- [ ] Distinguish no RELRO, partial RELRO, and full RELRO.
- [ ] Add canary indicators through bounded dynamic-symbol, symbol-table, or relocation evidence.
- [ ] Add stripped-status indicators with explicit confidence wording.
- [ ] Add section labels for executable regions and candidate addresses as analyst annotations.
- [ ] Preserve program headers as runtime mapping authority.
- [ ] Add controlled fixtures for no, partial, and full RELRO.
- [ ] Add controlled canary-present and canary-absent fixtures.
- [ ] Add automated `readelf` comparison checks.
- [ ] Add optional `checksec` and `rabin2 -I` comparison helpers when available.
- [ ] Extend JSON with compatible optional mitigation fields while schema remains `0.1.0`.

## Acceptance criteria

- [ ] Full and partial RELRO match controlled linker configurations.
- [ ] Canary output is labeled as an indicator, not proof of complete stack protection.
- [ ] Missing metadata produces `unknown` or equivalent explicit state instead of a guessed negative.
- [ ] Section labels never change executable-region boundaries.
- [ ] All table and string references are range-checked.
- [ ] Existing report count semantics remain unchanged.
- [ ] Malformed smoke coverage includes dynamic, symbol, string, and section metadata mutations.

## Out of scope

- CET/IBT policy conclusions.
- Broad symbol recovery.
- Full disassembly.
- Primitive expansion.

## Handoff

Sprint 9 adds candidate evidence provenance, truncation/completeness state, and the schema `0.2.0` transition needed before research preview output freezes.
