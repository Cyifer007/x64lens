# Sprint 03 Retrospective

## Status

In progress. Patch 008 Phase A, Patch 009 Phase B, and Patch 010 Phase C validated locally and in Docker. Patch 011 Phase D adds exact byte-template pattern matching and requires local validation.

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
- Exact byte-template pattern labels are available after Patch 011, but raw candidates are not semantically classified yet.
- Candidate scoring is not implemented yet.
- JSON output is not implemented yet.
- Candidate storage remains bounded at 4096 records and can return `EXIT_UNSUPPORTED` on very large binaries.
- After Patch 010, candidate storage is arena-backed, but the scanner is still bounded and not growable yet.

## Contract review placeholder

Current status through Patch 010:

- Development contract: followed. Scanner facts are stored in records before reporting, and Patch 010 kept storage infrastructure separate from scanner logic.
- Parser safety contract: followed. Scanner reads only validated executable file-backed regions.
- Comment/documentation contract: followed. Source files and docs were updated with human-readable rationale.
- Output contract: followed. Output reports candidates and exact patterns without claiming exploitability.
- Research contract: followed. Runtime claims remain hypotheses until benchmark data exists.
- Context persistence contract: followed. Sprint 3 state and backlog are being updated as the sprint progresses.

## Phase A validation status

Patch 008 was locally validated in WSL2 and Docker. The validation output showed:

```text
[test] raw gadget scanner default depth
[test] raw gadget scanner custom max-depth
tests: ok
```

Docker validation also completed with `tests: ok`.

Manual fixture validation produced the expected scanner facts for `tests/bin/gadgets`:

```text
Candidate count: 0x0000000000000007
ret count: 0x0000000000000006
ret imm16 count: 0x0000000000000001
```

The `objdump -d -Mintel ./tests/bin/gadgets` check confirmed the fixture contains:

```text
401000: pop rdi
401001: ret
401002: pop rsi
401003: ret
401004: pop rdx
401005: ret
401006: pop rax
401007: ret
401008: leave
401009: ret
40100a: syscall
40100c: ret
40100d: ret 0x10
```

The `/bin/ls` spot check produced hundreds of raw candidates at max-depth 4. This is expected for a raw byte scanner over a real executable region. Many `ret imm16` observations are raw byte candidates, not confirmed instruction-boundary gadgets. Semantic filtering and decoder-aware interpretation are future work.

## Mitigation note for `tests/bin/gadgets`

The fixture reported:

```text
NX stack: unknown
RELRO: not found
Dynamic linking: no
```

This is expected. The fixture is a tiny static `-nostdlib` binary used for deterministic scanner bytes. It is not a mitigation fixture. Mitigation states are validated with `minimal_nopie`, `minimal_pie_canary`, and `minimal_execstack`.

## Phase B, Patch 009 plan

Patch 009 added the first scanner smoke benchmark and an objdump-backed fixture validation helper. It did not introduce semantic classification, scoring, JSON output, or the arena allocator. Patch 010 is the follow-on arena allocator phase.

Validation commands for Patch 009:

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
make validate-gadget-fixture
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
```

## Contract review after Phase A

- Development contract: followed. Scanner facts are stored in records before reporting.
- Parser safety contract: followed. Scanner reads only validated executable file-backed regions.
- Comment/documentation contract: followed. Source files and docs were updated with human-readable rationale.
- Output contract: followed. Output does not claim exploitability.
- Research contract: followed. Runtime claims remain hypotheses until benchmark data exists.
- Context persistence contract: followed. Sprint 3 state and backlog are being updated as the sprint progresses.


## Phase B validation status

Patch 009 validated locally and in Docker. The validation output showed:

```text
[test] raw gadget scanner default depth
[test] raw gadget scanner custom max-depth
tests: ok
validate-gadget-fixture: ok
scanner-smoke benchmark complete
```

The first scanner smoke benchmark produced TSV and metadata files under `benchmarks/results/` and recorded tool version, command, run count, timestamp, WSL2 kernel, NASM version, GNU ld version, and GCC version. These artifacts are development evidence and are intentionally ignored by Git unless explicitly promoted into a research artifact.

## Phase C plan

Patch 010 moves raw gadget candidate storage from a static `.bss` array to an mmap-backed arena. The expected scanner-visible behavior should remain unchanged:

- candidate capacity: 4096 records,
- hand-authored fixture candidate count: 7,
- ret count: 6,
- ret imm16 count: 1.

Validation commands for Patch 010:

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
make validate-gadget-fixture
make arena-smoke
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
```


## Phase C validation status

Patch 010 validated locally and in Docker. The user-provided terminal output showed:

```text
[test] raw gadget scanner default depth
[test] raw gadget scanner custom max-depth
tests: ok
validate-gadget-fixture: ok
arena-smoke: ok
scanner-smoke benchmark complete
```

Manual checks confirmed that `./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets` still reports:

```text
Candidate capacity: 0x0000000000001000
Candidate count: 0x0000000000000007
ret count: 0x0000000000000006
ret imm16 count: 0x0000000000000001
```

Patch 010 was committed and pushed as:

```text
106af47 feat: add Sprint 3 arena-backed candidate storage
```

## Phase D plan

Patch 011 adds exact byte-template pattern matching. The matcher should tag raw candidates with pattern IDs such as `pop rdi; ret`, `leave; ret`, `syscall; ret`, and `ret imm16`, while leaving `SEM_UNKNOWN_CANDIDATE` unchanged. This keeps Sprint 3 focused on scanner and pattern facts, and leaves semantic primitive classification for Sprint 4.

Validation commands for Patch 011:

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
```
