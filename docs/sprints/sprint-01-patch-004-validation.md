# Sprint 01 Patch 004 Validation Guide

## Purpose

Patch 004 advances Sprint 1 from CLI scaffold to a working `info <file>` implementation. This guide defines the exact build, test, expected-output, limitation, next-step, and troubleshooting contract for the patch.

## Implementation summary

Patch 004 adds:

- `src/info.asm`: command orchestrator for `x64lens info <file>`.
- `src/filemap.asm`: read-only `openat`/`fstat`/`mmap`/`munmap`/`close` path.
- `src/bounds.asm`: file-size and offset-range validation helpers.
- `src/elf64.asm`: ELF magic, ELF64 class, endian, machine, and table-range validation.
- `src/report_text.asm`: basic text metadata output.
- `src/errors.asm`: stable diagnostics for expected failure classes.
- `src/hex.asm`: deterministic fixed-width hex formatting.
- `tests/run-tests.sh`: regression tests for valid ELF and invalid inputs.

## Build steps

```bash
make fix-perms
make clean
make
make samples
```

## Test steps

```bash
make test
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info /bin/ls
./build/x64lens info ./tests/invalid/text.txt ; echo $?
./build/x64lens info ./tests/invalid/truncated_elf.bin ; echo $?
./build/x64lens info ./tests/invalid/wrong_arch_elf.bin ; echo $?
```

Docker smoke test:

```bash
make docker-build
make docker-test
```

## Expected success behavior

- `make` links `build/x64lens`.
- `make test` ends with `tests: ok`.
- Valid ELF64 x86_64 targets exit `0` and print basic metadata.
- Plain text files exit `4`.
- Wrong-architecture ELF-like files exit `4`.
- Truncated ELF files exit `5`.

Expected text output shape:

```text
x64lens 0.1.0-dev
Target: ./tests/bin/minimal_nopie

Format:
  Type: ELF64
  Endian: little
  Machine: x86_64
  ELF Type: ET_EXEC
  Entry: 0x...
  Program header offset: 0x...
  Program header entry size: 0x...
  Program header count: 0x...
  Section header offset: 0x...
  Section header entry size: 0x...
  Section header count: 0x...
  File size: 0x...
```

## Known limitations

- Program headers are range-checked but not interpreted yet.
- Section headers are range-checked but not used for labels yet.
- Mitigation detection has not started.
- JSON output has not started.
- The code supports ELF64 x86_64 little-endian only.

## Next steps after success

1. Capture sample `info` output in `docs/sprints/sprint-01-retro.md`.
2. Optionally compare fields against `readelf -h` before or during Sprint 2 validation hardening.
3. Commit Patch 004.
4. Tag or note the Sprint 1 baseline once checkpoint documentation is ready.
5. Start Sprint 2: program-header parsing and executable-region mapping.

## Troubleshooting

If assembly fails:

```bash
make print-vars
nasm -v
ld -v
make clean
make V=1
```

If the binary exits unexpectedly:

```bash
gdb --args ./build/x64lens info /bin/ls
run
bt
info registers
```

If `make clean` fails with permission errors, repair ownership:

```bash
make fix-perms
make clean
```

Then use `make docker-shell` or `make docker-test` instead of manually running Docker as root.
