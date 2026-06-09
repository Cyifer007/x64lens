# Sprint 03 Retrospective

## Status

Complete.

## Dates

Start: 2026-06-06
End: 2026-06-07

## Sprint goal

Create the fast byte scanning core and introduce internal storage for raw gadget candidates.

## Summary

Sprint 3 successfully moved `x64lens` from loader-level executable-region discovery into the first working gadget discovery pipeline. The sprint produced a safe, bounded, record-backed raw scanner over executable `PT_LOAD + PF_X` regions, added repeatable scanner validation and smoke benchmarking, introduced mmap-backed arena storage for candidate records, and added exact byte-template suffix pattern labels.

The most important architectural result is that the repository now has a clean multi-stage analysis pipeline:

```text
program headers -> executable regions -> raw candidate scanner -> exact pattern matcher -> future semantic classifier -> future scoring/reporting
```

This keeps the future semantic work isolated. Sprint 4 can now focus on semantic primitive classification without refactoring file mapping, program-header parsing, executable-region modeling, raw scanning, or exact suffix matching.

## Phase A, raw scanner

Patch 008 implemented the initial raw scanner with fixed-capacity candidate storage.

Completed work:

- `x64lens gadgets <file>` command routing.
- `x64lens gadgets --max-depth N <file>` with bounded values.
- `gadget_record` and `gadget_summary` internal records.
- Executable-region scanning over `PT_LOAD + PF_X` regions.
- Raw `ret` and `ret imm16` terminator discovery.
- Bounded backward byte-window extraction.
- Raw candidate text output containing VA, file offset, window start, length, terminator type, and raw bytes.
- Regression checks against `tests/bin/gadgets`.

## Phase B, fixture validation and smoke benchmark

Patch 009 added repeatable validation and benchmark plumbing.

Completed work:

- `make validate-gadget-fixture`.
- `tools/validate-gadget-fixture.sh`.
- `make bench-scanner-smoke`.
- `benchmarks/scripts/bench-scanner-smoke.sh`.
- TSV output for development-level scanner measurements.
- Metadata sidecar output for host/tool environment details.

This phase did not create publication claims. It created the measurement plumbing required before later claims can be made.

## Phase C, arena-backed candidate storage

Patch 010 added `src/arena.asm` and moved raw gadget candidate storage to command-lifetime mmap-backed arena memory.

Completed work:

- `src/arena.asm` with a minimal anonymous mmap-backed allocator.
- Arena-backed `gadget_record[]` allocation.
- Preservation of the existing bounded capacity model.
- `make arena-smoke`.
- Continued local and Docker validation.

This phase improved scalability without making candidate storage growable yet. That was the correct tradeoff because it avoided destabilizing the scanner while removing the static `.bss` candidate array.

## Phase D, exact pattern matcher

Patch 011 added `src/patterns.asm` and exact byte-template suffix labels.

Completed work:

- `x64lens_patterns_match_exact`.
- Exact `PATTERN_*` IDs for:
  - `ret`
  - `ret imm16`
  - `pop rax; ret`
  - `pop rcx; ret`
  - `pop rdx; ret`
  - `pop rbx; ret`
  - `pop rsp; ret`
  - `pop rbp; ret`
  - `pop rsi; ret`
  - `pop rdi; ret`
  - `pop r8; ret` through `pop r15; ret`
  - `leave; ret`
  - `syscall; ret`
- `Exact pattern count` in text output.
- `exact_pattern_count` in scanner smoke benchmark TSV output.
- Fixture validator updates for exact pattern count and known pattern labels.

Important interpretation rule: Sprint 3 pattern labels describe the exact suffix ending at the terminator. They do not mean the entire raw backward byte window is a clean decoded instruction sequence. Full semantic classification begins in Sprint 4.

## Validation commands run

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

## Key validation output

### Standard tests

```text
[test] version
[test] help
[test] usage failure
[test] valid ELF64 info
[test] system ELF64 info
[test] non-ELF rejection
[test] truncated ELF rejection
[test] wrong architecture rejection
[test] malformed program header rejection
[test] mitigations non-PIE noexecstack
[test] mitigations PIE RELRO
[test] mitigations executable stack
[test] raw gadget scanner default depth
[test] raw gadget scanner custom max-depth
tests: ok
```

### Docker tests

```text
make docker-test
...
[test] raw gadget scanner default depth
[test] raw gadget scanner custom max-depth
tests: ok
```

### Fixture validation

```text
validate-gadget-fixture: ok
  fixture: ./tests/bin/gadgets
  x64lens: ./build/x64lens
  default candidates: 7
  default ret count: 6
  default ret imm16 count: 1
  default exact pattern count: 7
```

### Pattern smoke

```text
make pattern-smoke
...
validate-gadget-fixture: ok
  default candidates: 7
  default ret count: 6
  default ret imm16 count: 1
  default exact pattern count: 7
```

### Scanner smoke benchmark

```text
scanner-smoke benchmark complete
  results: /home/cyifer007/x64lens/benchmarks/results/scanner-smoke-20260607T215830Z.tsv
  metadata: /home/cyifer007/x64lens/benchmarks/results/scanner-smoke-20260607T215830Z.meta
  runs: 5
  max_depth: 4
```

### Controlled fixture output

```text
Candidate count: 0x0000000000000007
ret count: 0x0000000000000006
ret imm16 count: 0x0000000000000001
Exact pattern count: 0x0000000000000007
pattern: pop rdi; ret
pattern: pop rsi; ret
pattern: pop rdx; ret
pattern: pop rax; ret
pattern: leave; ret
pattern: syscall; ret
pattern: ret imm16
```

### `/bin/ls` smoke output

`/bin/ls` returned many raw candidates and exact pattern labels. This is expected for a byte-template scanner. The labels remain raw suffix labels, not final semantic claims.

## Contract review

- **Development contract:** followed. The scanner, pattern matcher, classifier, scoring, and reporting boundaries remained separate.
- **Parser safety contract:** followed. File-derived offsets and executable regions are validated before scanning.
- **Internal-facts-before-output rule:** followed. Scanner and pattern facts are stored in internal records before report rendering.
- **Comment and documentation contract:** followed. Touched source, test, benchmark, and documentation files were updated together.
- **Output contract:** followed. Text output reports raw facts and exact patterns without claiming exploitability.
- **Research contract:** followed. Smoke benchmark output is treated as development evidence, not publication evidence.
- **Context persistence contract:** followed. Sprint state, backlog, validation plan, benchmark methodology, and project context were updated.

## Known limitations after Sprint 3

- The scanner is pattern-based, not a full x86_64 decoder.
- Raw windows may include extra bytes before the exact suffix pattern.
- `ret imm16` can appear as a byte sequence inside other instructions because full decoding is not implemented yet.
- `Exact pattern count` is not the same as semantic primitive count.
- Register bitmaps are not populated yet.
- Stack deltas are not populated yet.
- Side-effect flags are not populated yet.
- Scores are not populated yet.
- JSON output is not implemented yet.
- Candidate storage is arena-backed but still bounded by `GADGET_RECORD_MAX`.

## Sprint 4 handoff

Sprint 4 should implement the first semantic classifier. The first classifier should consume `PATTERN_*` IDs and populate:

- `GADGET_SEMANTIC_CLASS`,
- `GADGET_REGS_CONTROLLED`,
- `GADGET_STACK_DELTA`,
- `GADGET_SIDE_EFFECT_FLAGS`,
- primitive coverage summary.

Do not implement scoring before semantic facts exist. Do not implement full JSON before the semantic record model stabilizes.
