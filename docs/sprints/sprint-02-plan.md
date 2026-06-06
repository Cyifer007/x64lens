# Sprint 02 Plan

## Dates

Start: TBD
End: TBD

## Sprint goal

Map the binary as the loader would and detect first-order hardening metadata.

## Planned deliverables

- [ ] Program header parser.
- [ ] `PT_LOAD` parser.
- [ ] Executable region discovery using `PF_X`.
- [ ] `PT_GNU_STACK` detection.
- [ ] NX stack detection.
- [ ] PIE detection using ELF type.
- [ ] RWX segment detection.
- [ ] Initial RELRO detection using `PT_GNU_RELRO`.
- [ ] `x64lens mitigations <file>` command.
- [ ] Comparison script against `readelf` and `checksec`.

## Acceptance criteria

- [ ] Correctly identifies executable regions in toy binaries.
- [ ] Correctly reports PIE vs non-PIE sample binaries.
- [ ] Correctly reports executable stack vs NX stack.
- [ ] Handles malformed program header offsets safely.
- [ ] Updates sprint retrospective and changelog.
