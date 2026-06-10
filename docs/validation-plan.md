# Validation Plan

## Validation goals

x64lens must be correct enough to support research claims and safe enough to parse hostile binaries without crashing or reading out of bounds.

## Validation categories

### 1. Build validation

```bash
make fix-perms
make normalize-perms
make clean
make
make samples
make test
```

Docker path:

```bash
make docker-build
make docker-test
```

### 2. Invalid input validation

Test cases:

- empty file,
- text file,
- truncated ELF magic,
- wrong architecture,
- malformed program header offset,
- impossible header count,
- oversized section table.

Expected outcome: graceful failure and stable nonzero exit code.

Current expected codes:

| Input | Expected exit code |
|---|---:|
| plain text file | 4 |
| wrong-architecture ELF-like file | 4 |
| truncated ELF magic/header | 5 |
| malformed program-header range | 5 |
| empty file | 5 |

### 3. ELF metadata validation

Compare `x64lens info` against:

```bash
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info /bin/ls
readelf -h ./tests/bin/minimal_nopie
readelf -h /bin/ls
```

### 4. Program-header and mitigation validation

Compare `x64lens mitigations` against `readelf -l` first:

```bash
./build/x64lens mitigations ./tests/bin/minimal_nopie
./build/x64lens mitigations ./tests/bin/minimal_pie_canary
./build/x64lens mitigations ./tests/bin/minimal_execstack
readelf -l ./tests/bin/minimal_nopie
readelf -l ./tests/bin/minimal_pie_canary
readelf -l ./tests/bin/minimal_execstack
```

When available, compare hardening indicators against:

```bash
checksec --file=<file>
rabin2 -I <file>
```

Sprint 2 validation expectations:

| Target | Expected signal |
| ------ | --------------- |
| `minimal_nopie` | PIE disabled, NX stack enabled |
| `minimal_pie_canary` | PIE enabled, NX stack enabled, RELRO present |
| `minimal_execstack` | NX stack disabled |
| malformed PHDR copy | exit code `5` |


### Sprint 2 validation evidence

Sprint 2 validation succeeded locally and in Docker. The following high-level observations were confirmed:

| Target | x64lens observation | readelf comparison |
| ------ | ------------------- | ------------------ |
| `minimal_nopie` | PIE disabled, NX stack enabled, RELRO present, dynamic linking yes, one executable region | `EXEC`, `GNU_STACK RW`, `GNU_RELRO`, `DYNAMIC`, one `LOAD R E` segment |
| `minimal_pie_canary` | PIE enabled, NX stack enabled, RELRO present, dynamic linking yes, one executable region | `DYN`, `GNU_STACK RW`, `GNU_RELRO`, `DYNAMIC`, one `LOAD R E` segment |
| `minimal_execstack` | PIE disabled, NX stack disabled, RELRO present, dynamic linking yes, one executable region | `EXEC`, `GNU_STACK RWE`, `GNU_RELRO`, `DYNAMIC`, one `LOAD R E` segment |
| `/bin/ls` | PIE enabled, NX stack enabled, RELRO present, dynamic linking yes, one executable region | `DYN`, `GNU_STACK RW`, `GNU_RELRO`, `DYNAMIC`, one `LOAD R E` segment |

The current `tools/compare-readelf.sh` provides side-by-side output. Future hardening should parse and compare fields automatically.

### 5. Gadget validation

Sprint 3 validates raw scanner output first:

```bash
./build/x64lens gadgets ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
objdump -d -Mintel ./tests/bin/gadgets
```

Expected Sprint 3 signals:

| Target | Expected signal |
| ------ | --------------- |
| `tests/bin/gadgets` | reports `Raw gadget candidates:` |
| `tests/bin/gadgets` | reports at least one `terminator: ret` |
| `tests/bin/gadgets` | reports at least one `terminator: ret imm16` |
| `tests/bin/gadgets` | reports `Exact pattern count: 0x0000000000000007` |
| `tests/bin/gadgets` | reports exact patterns for `pop rdi; ret`, `leave; ret`, `syscall; ret`, and `ret imm16` |
| `--max-depth 4` | reports `Max depth: 0x0000000000000004` |

Later validation should compare `x64lens gadgets` against:

```bash
ROPgadget --binary <file>
ropper --file <file>
ropr <file>
objdump -d -Mintel <file>
```

Existing tools should be validators and benchmark baselines, not runtime dependencies.

### 6. Controlled gadget validation

Use hand-written assembly binaries with known byte patterns.

### 7. Regression validation

Every bug fix should add a regression input or expected output file when practical.

## Validation artifact policy

Benchmark and validation outputs should be saved under `benchmarks/results/` only when they are small, reproducible, and non-sensitive. Large generated outputs should not be committed unless explicitly needed for a paper artifact.

### 5. Sprint 3 raw gadget scanner validation

Patch 008 validates the raw scanner against a hand-authored fixture and a real system binary.

Core commands:

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

Explanatory fixture check:

```bash
make validate-gadget-fixture
```

Expected fixture signals:

| Signal | Expected value |
| ------ | -------------- |
| default max depth | `0x0000000000000008` |
| custom max depth | `0x0000000000000004` |
| candidate count | `0x0000000000000007` |
| `ret` count | `0x0000000000000006` |
| `ret imm16` count | `0x0000000000000001` |
| known bytes | `5f c3`, `0f 05 c3`, `c2 10 00` |

Scanner smoke benchmark:

```bash
make bench-scanner-smoke
```

The smoke benchmark records repeated local measurements but does not support publication claims until the benchmark corpus, baseline tools, environment metadata, and statistical summary are finalized.


### 6. Arena allocator validation

Sprint 3 Patch 010 moves raw gadget candidate records from static `.bss` storage to an mmap-backed arena. The scanner-visible behavior should remain unchanged. Validate with:

```bash
make arena-smoke
make validate-gadget-fixture
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 /bin/ls
```

Expected fixture signals:

| Signal | Expected |
| ------ | -------- |
| Candidate capacity | `0x0000000000001000` |
| Candidate count | `0x0000000000000007` |
| ret count | `0x0000000000000006` |
| ret imm16 count | `0x0000000000000001` |

The arena allocator does not change scanner semantics. It is infrastructure for command-lifetime analysis storage.


### Sprint 3 Phase D pattern validation

Patch 011 validates exact byte-template matching through the default regression suite and the objdump-backed fixture validator:

```bash
make test
make validate-gadget-fixture
make pattern-smoke
```

Expected fixture signals:

| Target | Expected signal |
| ------ | --------------- |
| `tests/bin/gadgets` | `Exact pattern count: 0x0000000000000007` |
| `tests/bin/gadgets` | `pattern: pop rdi; ret` |
| `tests/bin/gadgets` | `pattern: pop rsi; ret` |
| `tests/bin/gadgets` | `pattern: pop rdx; ret` |
| `tests/bin/gadgets` | `pattern: pop rax; ret` |
| `tests/bin/gadgets` | `pattern: leave; ret` |
| `tests/bin/gadgets` | `pattern: syscall; ret` |
| `tests/bin/gadgets` | `pattern: ret imm16` |

This validates exact byte templates only. It does not validate semantic classes, register control, scoring, or exploitability interpretation.

### 6. Sprint 3 scanner, arena, and pattern validation

Sprint 3 validation proved the raw scanner, arena-backed candidate storage, exact suffix pattern matcher, fixture validator, and scanner smoke benchmark path.

Validation commands:

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

Expected controlled fixture signals:

| Signal | Expected value |
| ------ | -------------- |
| Candidate count | 7 |
| ret count | 6 |
| ret imm16 count | 1 |
| Exact pattern count | 7 |
| Known labels | `pop rdi; ret`, `pop rsi; ret`, `pop rdx; ret`, `pop rax; ret`, `leave; ret`, `syscall; ret`, `ret imm16` |

Sprint 3 validation evidence from local WSL2 and Docker runs:

```text
make test -> tests: ok
make docker-test -> tests: ok
make validate-gadget-fixture -> validate-gadget-fixture: ok
make pattern-smoke -> validate-gadget-fixture: ok
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke -> scanner-smoke benchmark complete
```

Interpretation rule: exact pattern labels describe the recognized suffix ending at the terminator. They are not full semantic classifications and they are not exploitability claims.

### 7. Sprint 4 semantic validation status

Patch 015 adds validation for:

- semantic class labels,
- controlled-register bitmaps,
- stack-delta values,
- primitive coverage summaries,
- preservation of `unknown_candidate` for unsupported windows.

Current commands:

```bash
make validate-gadget-fixture
make semantic-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
```

`analyze <file>` is not implemented yet and should not be used as a Sprint 4 validation requirement until a later patch adds it.

## Parser safety and mutation smoke plan

Sprint 7 should add a deterministic malformed-input mutation smoke harness before deeper parsing expands the trusted code surface.

Proposed command shape:

```bash
make malformed-smoke
make fuzz-mutated-elf-smoke
```

Minimum acceptance criteria:

```text
no SIGSEGV
no SIGBUS
no unbounded runtime
stable nonzero exit code for malformed inputs
regression fixture added for every parser crash
```

The first version does not need coverage-guided fuzzing. A deterministic mutation smoke runner over known valid and malformed ELF seeds is enough to catch obvious parser regressions and support reviewer-facing safety discipline.

## Script permission validation

Patch extraction, Windows tooling, or cross-platform ZIP workflows can accidentally drop executable bits from shell helpers. `make scaffold-check` should validate that expected scripts remain executable through `make script-perms-check`.


### 8. Sprint 4 Patch 015 semantic classifier validation

Sprint 4 Patch 015 validates first-pass semantic classification through the controlled `tests/bin/gadgets` fixture.

Commands:

```bash
make validate-gadget-fixture
make semantic-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
```

Expected controlled fixture signals:

| Signal | Expected value |
| ------ | -------------- |
| Candidate count | `0x0000000000000007` |
| Exact pattern count | `0x0000000000000007` |
| Semantic primitive count | `0x0000000000000007` |
| unknown_candidate count | `0x0000000000000000` |
| arg_control count | `0x0000000000000003` |
| syscall_num_control count | `0x0000000000000001` |
| syscall_trigger count | `0x0000000000000001` |
| stack_pivot count | `0x0000000000000001` |
| alignment count | `0x0000000000000001` |
| Register coverage | `rax|rdx|rsi|rdi|rsp` |

This validation confirms classifier plumbing and fixture behavior. It is not a full decoder validation and does not establish exploitability.
