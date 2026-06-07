# Sprint 03 Retrospective

## Status

In progress. Patch 008 begins Phase A implementation and requires local validation.

## Sprint goal

Create the fast byte scanning core and introduce internal storage for raw gadget candidates.

## Phase A summary

Patch 008 implements the first raw scanner path using a fixed-capacity candidate buffer. This is intentionally a bridge design. The goal is to prove scanner correctness and parser safety before adding an arena allocator.

Implemented in Phase A:

- `x64lens gadgets <file>` command routing.
- `x64lens gadgets --max-depth N <file>` for `1 <= N <= 32`.
- Fixed-capacity `gadget_record` buffer.
- `gadget_summary` record for raw scanner counts.
- Executable-region scanner over `PT_LOAD + PF_X` regions from Sprint 2.
- Raw `ret` and `ret imm16` detection.
- Bounded backward byte-window extraction.
- Raw text output with VA, file offset, window start, length, terminator type, and bytes.
- Regression tests for raw scanner behavior against `tests/bin/gadgets`.

## Validation commands to run

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

## Expected validation signals

- `make test` ends with `tests: ok`.
- `make docker-test` ends with `tests: ok`.
- `x64lens gadgets ./tests/bin/gadgets` prints `Raw gadget candidates:`.
- Default max depth prints `0x0000000000000008`.
- Custom max depth prints `0x0000000000000004`.
- Output includes at least one `terminator: ret`.
- Output includes at least one `terminator: ret imm16`.
- Output includes raw `bytes:` fields.
- `objdump -d -Mintel` confirms the hand-authored fixture contains `ret` and `ret 0x10` instructions.

## Known limitations

- This is a pattern/terminator scanner, not a full x86_64 decoder.
- Raw candidates are not semantically classified yet.
- Candidate scoring is not implemented yet.
- JSON output is not implemented yet.
- Fixed-capacity candidate storage can return `EXIT_UNSUPPORTED` on very large binaries.
- Arena allocation remains Phase B or later.

## Contract review placeholder

Complete this section after local validation:

- Development contract:
- Parser safety contract:
- Comment/documentation contract:
- Output contract:
- Research contract:
- Context persistence contract:
