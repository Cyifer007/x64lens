# Sprint 03 Plan

## Status

Complete. Patch 008 Phase A, Patch 009 Phase B, Patch 010 Phase C, and Patch 011 Phase D were validated locally and in Docker.

## Sprint goal

Create the fast byte scanning core and introduce internal storage for raw gadget candidates.

Sprint 3 was completed in four intentionally narrow phases:

1. **Phase A, Patch 008:** implement the raw scanner with a fixed-capacity buffer.
2. **Phase B, Patch 009:** add fixture validation and scanner smoke benchmarking.
3. **Phase C, Patch 010:** replace fixed static backing with mmap-backed arena candidate storage.
4. **Phase D, Patch 011:** add exact byte-template pattern IDs and pattern labels while keeping semantic classification deferred to Sprint 4.

The sprint intentionally stops at raw candidate discovery plus exact suffix pattern tagging. Semantic primitive classification, register bitmaps, stack deltas, side-effect metadata, scoring, and JSON reports remain downstream work.

## Completed deliverables

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
- [x] Add first scanner smoke benchmark harness.
- [x] Run first scanner smoke measurement locally and capture results.
- [x] Assess whether simple arena allocator can land safely in Sprint 3. Decision: proceed in Phase C.
- [x] Add mmap-backed arena allocator for raw gadget candidate records.
- [x] Validate arena-backed scanner path locally and in Docker.
- [x] Add exact byte-template pattern IDs for known Sprint 3 fixture patterns.
- [x] Update `gadgets` output with exact pattern labels and pattern count.
- [x] Update fixture validator and scanner smoke benchmark for exact pattern count.
- [x] Validate exact pattern matcher locally and in Docker.
- [x] Write Sprint 3 retrospective after Phase D validation.

## Acceptance criteria

- [x] `make clean && make && make test` succeeds.
- [x] `make docker-test` succeeds.
- [x] `x64lens mitigations <file>` remains stable after scanner changes.
- [x] `x64lens gadgets ./tests/bin/gadgets` runs without crashing.
- [x] `x64lens gadgets --max-depth 4 ./tests/bin/gadgets` runs without crashing.
- [x] Raw `ret` candidate discovery works over executable regions only.
- [x] Raw `ret imm16` candidate discovery works over executable regions only.
- [x] Candidate output includes file offset and virtual address.
- [x] Candidate output includes bounded byte-window start and length.
- [x] Candidate extraction is bounded by default max depth.
- [x] Scanner does not read outside executable-region file bounds under current regression tests.
- [x] Invalid inputs fail safely through the `gadgets` command.
- [x] Exact pattern matcher tags the controlled gadget fixture.
- [x] Sprint 3 retrospective is finalized.

## Final validation commands

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
make validate-gadget-fixture
make pattern-smoke
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 /bin/ls | head -n 40
```

## Final validation signals

The controlled gadget fixture produced the expected count model:

```text
Candidate count: 0x0000000000000007
ret count: 0x0000000000000006
ret imm16 count: 0x0000000000000001
Exact pattern count: 0x0000000000000007
```

The fixture validator reported:

```text
validate-gadget-fixture: ok
  default candidates: 7
  default ret count: 6
  default ret imm16 count: 1
  default exact pattern count: 7
```

## Design notes carried forward

- `scanner.asm` owns raw candidate discovery only.
- `patterns.asm` owns exact byte-template suffix IDs only.
- `classifier.asm` will map exact pattern IDs into semantic records in Sprint 4.
- `scoring.asm` remains deferred until semantic facts exist.
- `report_text.asm` prints facts but does not decide facts.
- `report_json.asm` must later emit from internal records, not from text scraping.

## Sprint 4 handoff

Sprint 4 should begin with semantic classification over existing `PATTERN_*` IDs. The first implementation should populate semantic class, controlled-register bitmap, stack delta, and primitive coverage summary for the exact patterns already recognized in Sprint 3.
