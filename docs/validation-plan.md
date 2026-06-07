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
