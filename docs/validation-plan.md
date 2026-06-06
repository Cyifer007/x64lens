# Validation Plan

## Validation goals

x64lens must be correct enough to support research claims and safe enough to parse hostile binaries without crashing or reading out of bounds.

## Validation categories

### 1. Build validation

```bash
make fix-perms
make clean
make
make samples
make test
```

Sprint 1 also validates the Docker path:

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

Sprint 1 expected codes:

| Input | Expected exit code |
|---|---:|
| plain text file | 4 |
| wrong-architecture ELF-like file | 4 |
| truncated ELF magic/header | 5 |
| empty file | 5 |

### 3. ELF metadata validation

Compare `x64lens info` against:

```bash
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info /bin/ls
readelf -h ./tests/bin/minimal_nopie
readelf -h /bin/ls
```

Sprint 1 only compares ELF identity and core ELF header metadata. Program-header semantics and section labels begin in Sprint 2.

### 4. Mitigation validation

Compare `x64lens mitigations` against:

```bash
checksec --file=<file>
rabin2 -I <file>
```

### 5. Gadget validation

Compare `x64lens gadgets` against:

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
