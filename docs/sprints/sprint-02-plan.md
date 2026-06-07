# Sprint 02 Plan

## Dates

Start: TBD
End: TBD

## Sprint goal

Map the binary as the Linux loader would and report first-order executable-region and mitigation metadata.

Sprint 1 proved that `x64lens info <file>` can safely map and validate ELF64 x86_64 binaries. Sprint 2 moves from file identity to runtime-relevant structure by parsing program headers. Program headers are the authoritative source for loader mappings, so this sprint is the foundation for later executable-region scanning, mitigation analysis, and gadget discovery.

## Planned deliverables

- [ ] Parse ELF64 program headers in `src/phdr.asm`.
- [ ] Validate `e_phoff`, `e_phentsize`, and `e_phnum` before iterating.
- [ ] Identify `PT_LOAD` segments.
- [ ] Identify `PF_X` executable regions.
- [ ] Create an internal executable-region record model in `src/regions.asm` or `include/structs.inc`.
- [ ] Detect `PT_GNU_STACK`.
- [ ] Detect NX stack vs executable stack.
- [ ] Detect PIE using ELF type.
- [ ] Detect RWX load segments.
- [ ] Detect baseline RELRO using `PT_GNU_RELRO`.
- [ ] Add the initial `x64lens mitigations <file>` command path.
- [ ] Update `docs/mitigation-model.md` if interpretation changes.
- [ ] Update `docs/validation-plan.md` with program-header validation commands.
- [ ] Add tests for PIE/non-PIE and NX/executable-stack fixture behavior where feasible.

## Acceptance criteria

- [ ] `make clean && make && make test` succeeds.
- [ ] `make docker-test` succeeds.
- [ ] `x64lens info <file>` remains stable after program-header changes.
- [ ] `x64lens mitigations ./tests/bin/minimal_nopie` runs without crashing.
- [ ] `x64lens mitigations ./tests/bin/minimal_pie_canary` runs without crashing.
- [ ] Executable `PT_LOAD` ranges are reported or internally discoverable.
- [ ] PIE differs correctly between `minimal_nopie` and `minimal_pie_canary`.
- [ ] NX stack detection reflects the toy corpus compile flags.
- [ ] Malformed program-header offsets fail safely.
- [ ] Sprint 2 retrospective is written.

## Demo commands

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info ./tests/bin/minimal_pie_canary
./build/x64lens mitigations ./tests/bin/minimal_nopie
./build/x64lens mitigations ./tests/bin/minimal_pie_canary
readelf -h ./tests/bin/minimal_nopie
readelf -l ./tests/bin/minimal_nopie
readelf -h ./tests/bin/minimal_pie_canary
readelf -l ./tests/bin/minimal_pie_canary
```

## Suggested implementation order

1. Add program-header constants to `include/elf64.inc` if missing.
2. Add program-header record offsets to `include/structs.inc` or a dedicated include if useful.
3. Implement safe program-header iteration in `src/phdr.asm`.
4. Add helper routines for reading program-header fields without exceeding mapped file bounds.
5. Add executable-region discovery in `src/regions.asm`.
6. Add mitigation checks in `src/mitigations.asm`.
7. Add CLI routing for `mitigations <file>`.
8. Add text reporting for mitigation metadata.
9. Add regression tests.
10. Update documentation and sprint retrospective.

## Risks

- Program-header validation must avoid integer overflow when calculating `e_phoff + e_phentsize * e_phnum`.
- `PT_GNU_STACK` may be absent on some binaries, so NX interpretation must distinguish `present`, `absent`, and `unknown` states where appropriate.
- PIE detection from `ET_DYN` is reliable for common dynamically linked PIE executables, but shared libraries are also `ET_DYN`; output wording should remain careful.
- RELRO detection begins with `PT_GNU_RELRO`; full RELRO requires dynamic-section parsing and may be a later subtask if time is tight.

## Non-goals

- No gadget scanning in Sprint 2.
- No JSON output in Sprint 2 unless it falls out cheaply from internal records.
- No full section-header labeling yet unless it directly supports executable-region readability.
- No exploitability verdicts. Mitigation output should describe constraints, not assert exploitability.

## Next steps after successful Sprint 2 testing

If Sprint 2 testing succeeds:

1. Capture `mitigations` output for toy binaries.
2. Compare program-header and mitigation findings against `readelf -l` and `checksec` where available.
3. Update `docs/sprints/sprint-02-retro.md`.
4. Update local-only `PROJECT_STATE.md` with Sprint 2 status.
5. Start Sprint 3 with raw executable-region scanning and `ret` candidate discovery.

## Patch 006 implementation notes

Patch 006 begins Sprint 2 implementation. It adds the first `mitigations <file>` command path and introduces the internal program-header summary and executable-region record model.

Implemented in this patch, pending local validation:

1. CLI routing for `x64lens mitigations <file>`.
2. `src/mitigations.asm` command orchestration.
3. `src/phdr.asm` safe program-header iteration.
4. `src/regions.asm` executable-region record storage.
5. `include/structs.inc` Sprint 2 summary and region record offsets.
6. `src/report_text.asm` mitigation and executable-region text reporting.
7. `tests/run-tests.sh` regression checks for baseline mitigation behavior.
8. `minimal_execstack` toy binary for executable-stack/NX validation.

The patch intentionally does not implement full RELRO, canary detection, section labels, JSON output, or gadget scanning. Full RELRO requires dynamic-section parsing and remains later work unless Sprint 2 capacity allows it.

## Patch 006 validation commands

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
./build/x64lens mitigations ./tests/bin/minimal_nopie
./build/x64lens mitigations ./tests/bin/minimal_pie_canary
./build/x64lens mitigations ./tests/bin/minimal_execstack
readelf -l ./tests/bin/minimal_nopie
readelf -l ./tests/bin/minimal_pie_canary
readelf -l ./tests/bin/minimal_execstack
```

## Next steps after Patch 006 validation succeeds

1. Capture mitigation output for the three toy binaries.
2. Compare `LOAD`, `GNU_STACK`, `GNU_RELRO`, and `DYNAMIC` observations against `readelf -l`.
3. Update `docs/sprints/sprint-02-retro.md` with real command output.
4. Update local-only `PROJECT_STATE.md`.
5. Decide whether Sprint 2 needs one more hardening patch for `tools/compare-readelf.sh` automation before closing.
