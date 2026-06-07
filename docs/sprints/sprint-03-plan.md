# Sprint 03 Plan

## Status

In progress. Patch 008 begins Sprint 3 with a fixed-capacity candidate buffer.

## Sprint goal

Create the fast byte scanning core and introduce internal storage for raw gadget candidates.

Sprint 3 is expected to occur in phases. Phase A uses a fixed candidate buffer to prove scanner correctness. Phase B should attempt the arena allocator if Phase A validates cleanly and does not create avoidable scope risk. If the arena allocator would destabilize the scanner, it should carry forward as a Sprint 4 or Sprint 5 infrastructure item.

## Planned deliverables

- [x] Decide fixed candidate buffer vs immediate arena allocator. Decision: fixed buffer first.
- [x] Add `gadgets [--max-depth N] <file>` CLI routing.
- [x] Add candidate and scanner summary records.
- [x] Implement executable-region scanner over `PT_LOAD + PF_X` regions.
- [x] Detect `ret` terminators.
- [x] Detect `ret imm16` terminators.
- [x] Add bounded backward window extraction.
- [x] Add bounded `--max-depth` option.
- [x] Add raw gadget candidate output.
- [x] Update toy assembly sample with known `ret` and `ret imm16` bytes.
- [ ] Add first scanner smoke measurement.
- [ ] Assess whether simple arena allocator can land safely in Sprint 3 Phase B.
- [ ] Write Sprint 3 retrospective after local validation.

## Acceptance criteria

- [ ] `make clean && make && make test` succeeds.
- [ ] `make docker-test` succeeds.
- [ ] `x64lens mitigations <file>` remains stable after scanner changes.
- [ ] `x64lens gadgets ./tests/bin/gadgets` runs without crashing.
- [ ] `x64lens gadgets --max-depth 4 ./tests/bin/gadgets` runs without crashing.
- [ ] Raw `ret` candidate discovery works over executable regions only.
- [ ] Raw `ret imm16` candidate discovery works over executable regions only.
- [ ] Candidate output includes file offset and virtual address.
- [ ] Candidate output includes bounded byte-window start and length.
- [ ] Candidate extraction is bounded by default max depth.
- [ ] Scanner does not read outside executable-region file bounds.
- [ ] Invalid inputs fail safely through the `gadgets` command.
- [ ] Sprint 3 retrospective is written.

## Suggested validation commands

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
./build/x64lens mitigations ./tests/bin/gadgets
./build/x64lens gadgets ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
objdump -d -Mintel ./tests/bin/gadgets
```

## Phase A implementation notes

Patch 008 starts with fixed candidate storage because scanner correctness is the highest-risk technical item. The scanner now stores raw candidate facts before reporting, satisfying the internal-facts-before-output rule without prematurely introducing allocator complexity.

Implemented in Phase A:

1. `x64lens gadgets <file>` command path.
2. `x64lens gadgets --max-depth N <file>` with `1 <= N <= 32`.
3. Fixed `gadget_record` buffer with explicit capacity failure instead of truncation.
4. `gadget_summary` record for scanner counts and reporting.
5. Executable-region scanner over Sprint 2 `PT_LOAD + PF_X` regions.
6. `ret` and `ret imm16` terminator detection.
7. Bounded backward byte-window extraction.
8. Raw text report with VA, file offset, window start, length, terminator type, and bytes.

## Sprint 2 follow-up items assessed for Sprint 3

The following Sprint 2 follow-up items are not Sprint 3 Phase A blockers:

- Automated structured `readelf` comparison: useful validation hardening, but not required for scanner implementation.
- `checksec` comparison: useful once mitigation reporting expands, but not scanner-critical.
- `rabin2 -I` comparison: useful once external tool comparison begins, but not scanner-critical.
- Full RELRO detection: requires dynamic-section parsing and should not be mixed into raw scanner work.
- Canary detection: requires dynamic symbol or section/symbol parsing and should not be mixed into raw scanner work.
- Section labels for executable regions: useful for readability, but scanner correctness depends on program headers, not labels.

The only Sprint 2 follow-up directly worked into Sprint 3 is preparing executable-region records for scanner consumption. That dependency is already satisfied by Sprint 2.

## Risks

- Scanner bugs can easily become out-of-bounds reads. Region file offset plus region size must be validated before scanning.
- A full x86 decoder is not a Sprint 3 goal. Keep this sprint focused on raw candidate discovery.
- A fixed buffer can overflow on large binaries. The correct behavior is explicit `EXIT_UNSUPPORTED`, not silent truncation.
- The scanner is byte-pattern based. It may find unaligned raw candidates, which is acceptable for this phase and must be documented as a limitation.

## Non-goals

- No semantic classification in Sprint 3 Phase A.
- No scoring in Sprint 3 Phase A.
- No JSON output in Sprint 3 Phase A.
- No full decoder work.
- No full RELRO or canary implementation in Sprint 3 Phase A.

## Next steps after Phase A validation

If Patch 008 validates locally and in Docker:

1. Capture `gadgets` output for `tests/bin/gadgets`.
2. Compare candidate bytes against `objdump -d -Mintel tests/bin/gadgets`.
3. Add first scanner smoke measurement.
4. Decide whether to add the arena allocator in Sprint 3 Phase B or carry it forward.
5. Update `docs/sprints/sprint-03-retro.md` and local-only `PROJECT_STATE.md`.
