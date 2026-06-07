# Sprint 03 Plan

## Sprint goal

Create the fast byte scanning core and introduce internal storage for gadget candidates.

## Planned deliverables

- [ ] Simple arena allocator backed by `mmap`.
- [ ] Executable region scanner.
- [ ] `ret` terminator detection.
- [ ] `ret imm16` detection.
- [ ] Bounded backward window extraction.
- [ ] `--max-depth` flag.
- [ ] Raw gadget candidate output.
- [ ] Toy assembly sample with known gadgets.
- [ ] First scanner performance measurement.


## Acceptance criteria

- [ ] `make clean && make && make test` succeeds.
- [ ] `make docker-test` succeeds.
- [ ] `x64lens mitigations <file>` remains stable after scanner changes.
- [ ] `x64lens gadgets ./tests/bin/gadgets` runs without crashing.
- [ ] Raw `ret` candidate discovery works over executable regions only.
- [ ] `ret imm16` candidates are either detected or explicitly deferred with tests documenting current behavior.
- [ ] Candidate output includes file offset and virtual address.
- [ ] Candidate extraction is bounded by default max depth.
- [ ] Scanner does not read outside executable-region file bounds.
- [ ] Sprint 3 retrospective is written.

## Suggested implementation order

1. Decide fixed candidate buffer vs arena allocator for Sprint 3.
2. Add candidate record offsets to `include/structs.inc` if the existing gadget record is too rich for raw candidates.
3. Add `gadgets <file>` CLI routing.
4. Reuse the `mitigations` path to map, validate, parse PHDRs, and build executable regions.
5. Implement a scanner loop over executable-region file ranges.
6. Detect `ret` (`0xc3`) first.
7. Add bounded backward byte-window extraction.
8. Add `ret imm16` (`0xc2 xx xx`) detection.
9. Emit raw text output.
10. Add regression checks against `tests/bin/gadgets`.

## Risks

- Scanner bugs can easily become out-of-bounds reads. Region file offset plus region size must be validated before scanning.
- A full x86 decoder is not a Sprint 3 goal. Keep this sprint focused on raw candidate discovery.
- Direct printing is acceptable for the first raw scanner output, but candidate facts should move into records before semantic classification.

## Non-goals

- No semantic classification in Sprint 3 unless raw scanning completes early.
- No scoring in Sprint 3.
- No JSON output in Sprint 3 unless it falls out cheaply from internal records.
- No full decoder work.
