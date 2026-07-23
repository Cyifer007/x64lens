# Sprint 01 Retrospective

## Status

Complete.

## Dates

Start: 2026-05-27
End: 2026-06-05

## Sprint goal

Build the initial repository foundation and replace the `info <file>` scaffold with a safe ELF64 x86_64 validation path.

## Summary

Sprint 1 established the working foundation for `x64lens`. The repository now has a buildable NASM module layout, reproducible WSL2 and Docker validation paths, stable CLI commands for `help`, `version`, and `info <file>`, and a real ELF64 x86_64 metadata path backed by direct Linux syscalls.

The most important technical outcome is that `x64lens info <file>` is no longer a scaffold stub. It now maps a target file read-only, validates ELF64 x86_64 little-endian identity, bounds-checks core ELF table ranges, prints deterministic metadata, and rejects invalid inputs with stable exit codes.

## Completed deliverables

- [x] Ubuntu 24.04 WSL2 development path validated.
- [x] Docker Desktop with WSL2 integration validated.
- [x] Docker bind-mount permissions issue diagnosed and fixed through UID/GID-safe Makefile targets.
- [x] Repository scaffold validated.
- [x] Documentation scaffold validated.
- [x] Diagram source scaffold validated.
- [x] `make` build path validated.
- [x] `make test` path validated.
- [x] `make docker-build` validated.
- [x] `make docker-test` validated.
- [x] `x64lens version` implemented and validated.
- [x] `x64lens help` implemented and validated.
- [x] `x64lens info <file>` implemented and validated.
- [x] File open/stat/map/unmap path implemented.
- [x] ELF magic validation implemented.
- [x] ELF64 class validation implemented.
- [x] Little-endian validation implemented.
- [x] x86_64 machine type validation implemented.
- [x] Basic ELF header metadata reporting implemented.
- [x] Invalid input tests implemented.
- [x] Valid toy ELF test implemented.
- [x] Public/private context boundary preserved through `.local/` ignore behavior.

## Implementation notes

Sprint 1 added or materially updated these implementation modules:

- `src/info.asm`: command orchestrator for `x64lens info <file>`.
- `src/filemap.asm`: read-only `openat`/`fstat`/`mmap`/`munmap`/`close` path.
- `src/bounds.asm`: file-size and range validation helpers.
- `src/elf64.asm`: ELF64 identity and header table validation.
- `src/report_text.asm`: deterministic human-readable ELF metadata output.
- `src/errors.asm`: stable diagnostics for expected failure classes.
- `src/hex.asm`: fixed-width hexadecimal output formatting.
- `tests/run-tests.sh`: regression coverage for valid and invalid inputs.

## Validation environment

Validation was performed locally from WSL2 Ubuntu with NASM, GNU `ld`, GCC, Make, and Docker Desktop with WSL2 integration.

Docker validation used the repository-provided UID/GID-safe targets so bind-mounted build outputs are not created as root-owned artifacts.

## Validation commands run

```bash
make fix-perms
make clean
make
make samples
make test
./build/x64lens version
./build/x64lens help
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info /bin/ls
./build/x64lens info ./tests/invalid/text.txt ; echo $?
./build/x64lens info ./tests/invalid/truncated_elf.bin ; echo $?
./build/x64lens info ./tests/invalid/wrong_arch_elf.bin ; echo $?
make docker-build
make docker-test
```

## Key validation output

### Build

```text
$ make
mkdir -p build
nasm -f elf64 -g -F dwarf -Iinclude/ src/bounds.asm -o build/bounds.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/classifier.asm -o build/classifier.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/cli.asm -o build/cli.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/elf64.asm -o build/elf64.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/errors.asm -o build/errors.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/filemap.asm -o build/filemap.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/hex.asm -o build/hex.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/info.asm -o build/info.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/main.asm -o build/main.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/mitigations.asm -o build/mitigations.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/patterns.asm -o build/patterns.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/phdr.asm -o build/phdr.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/print.asm -o build/print.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/regions.asm -o build/regions.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/report_json.asm -o build/report_json.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/report_text.asm -o build/report_text.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/scanner.asm -o build/scanner.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/scoring.asm -o build/scoring.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/shdr.asm -o build/shdr.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/syscalls.asm -o build/syscalls.o
nasm -f elf64 -g -F dwarf -Iinclude/ src/version.asm -o build/version.o
ld  -o build/x64lens build/bounds.o build/classifier.o build/cli.o build/elf64.o build/errors.o build/filemap.o build/hex.o build/info.o build/main.o build/mitigations.o build/patterns.o build/phdr.o build/print.o build/regions.o build/report_json.o build/report_text.o build/scanner.o build/scoring.o build/shdr.o build/syscalls.o build/version.o
```

### Test suite

```text
$ make test
make -C tests/toy-src
make[1]: Entering directory '<repo>/tests/toy-src'
make[1]: Nothing to be done for 'all'.
make[1]: Leaving directory '<repo>/tests/toy-src'
mkdir -p tests/bin
cp tests/toy-src/minimal_nopie tests/bin/ 2>/dev/null || true
cp tests/toy-src/minimal_pie_canary tests/bin/ 2>/dev/null || true
cp tests/toy-src/gadgets tests/bin/ 2>/dev/null || true
bash tests/run-tests.sh
[test] version
[test] help
[test] usage failure
[test] valid ELF64 info
[test] system ELF64 info
[test] non-ELF rejection
[test] truncated ELF rejection
[test] wrong architecture rejection
tests: ok
```

### Version and help

```text
$ ./build/x64lens version
x64lens 0.1.0-dev schema 0.1.0

$ ./build/x64lens help
x64lens 0.1.0-dev

Usage:
  x64lens help
  x64lens version
  x64lens info <file>

Planned commands:
  x64lens mitigations <file>
  x64lens gadgets <file>
  x64lens analyze <file>
  x64lens bench <file>
```

### Valid toy ELF64 target

```text
$ ./build/x64lens info ./tests/bin/minimal_nopie
x64lens 0.1.0-dev
Target: ./tests/bin/minimal_nopie

Format:
  Type: ELF64
  Endian: little
  Machine: x86_64
  ELF Type: ET_EXEC
  Entry: 0x0000000000401050
  Program header offset: 0x0000000000000040
  Program header entry size: 0x0000000000000038
  Program header count: 0x000000000000000d
  Section header offset: 0x0000000000003640
  Section header entry size: 0x0000000000000040
  Section header count: 0x000000000000001f
  File size: 0x0000000000003e00
```

### Valid system ELF64 target

```text
$ ./build/x64lens info /bin/ls
x64lens 0.1.0-dev
Target: /bin/ls

Format:
  Type: ELF64
  Endian: little
  Machine: x86_64
  ELF Type: ET_DYN
  Entry: 0x0000000000006d30
  Program header offset: 0x0000000000000040
  Program header entry size: 0x0000000000000038
  Program header count: 0x000000000000000d
  Section header offset: 0x0000000000022428
  Section header entry size: 0x0000000000000040
  Section header count: 0x000000000000001f
  File size: 0x0000000000022be8
```

### Invalid input exit codes

```text
$ ./build/x64lens info ./tests/invalid/text.txt ; echo $?
error: target is not an ELF64 x86_64 little-endian binary
4

$ ./build/x64lens info ./tests/invalid/truncated_elf.bin ; echo $?
error: malformed or truncated ELF
5

$ ./build/x64lens info ./tests/invalid/wrong_arch_elf.bin ; echo $?
error: target is not an ELF64 x86_64 little-endian binary
4
```

### Docker validation

```text
$ make docker-test
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "<repo>":/work -w /work x64lens-dev bash -lc 'make clean && make && make test'
rm -rf build
rm -rf tests/bin
make -C tests/toy-src clean || true
make[1]: Entering directory '/work/tests/toy-src'
rm -f minimal_nopie minimal_pie_canary gadgets
make[1]: Leaving directory '/work/tests/toy-src'
mkdir -p build
nasm -f elf64 -g -F dwarf -Iinclude/ src/bounds.asm -o build/bounds.o
...
ld  -o build/x64lens build/bounds.o build/classifier.o build/cli.o build/elf64.o build/errors.o build/filemap.o build/hex.o build/info.o build/main.o build/mitigations.o build/patterns.o build/phdr.o build/print.o build/regions.o build/report_json.o build/report_text.o build/scanner.o build/scoring.o build/shdr.o build/syscalls.o build/version.o
make -C tests/toy-src
make[1]: Entering directory '/work/tests/toy-src'
cc -no-pie -fno-stack-protector -z noexecstack -o minimal_nopie minimal.c
cc -fPIE -pie -fstack-protector-all -Wl,-z,relro,-z,now -z noexecstack -o minimal_pie_canary minimal.c
cc -nostdlib -static -no-pie -o gadgets gadgets.S
make[1]: Leaving directory '/work/tests/toy-src'
mkdir -p tests/bin
cp tests/toy-src/minimal_nopie tests/bin/ 2>/dev/null || true
cp tests/toy-src/minimal_pie_canary tests/bin/ 2>/dev/null || true
cp tests/toy-src/gadgets tests/bin/ 2>/dev/null || true
bash tests/run-tests.sh
[test] version
[test] help
[test] usage failure
[test] valid ELF64 info
[test] system ELF64 info
[test] non-ELF rejection
[test] truncated ELF rejection
[test] wrong architecture rejection
tests: ok
```

## Commit evidence

Sprint 1 implementation was committed and pushed as:

```text
commit cb4d649
message: feat: implement Sprint 1 ELF64 info path
```

The remote reported that the repository moved to:

```text
git@github.com:<owner>/x64lens.git
```

## Acceptance criteria review

| Acceptance criterion | Status | Evidence |
|---|---:|---|
| `make` succeeds on Linux with NASM installed | Complete | Local build output links `build/x64lens` |
| `make test` succeeds | Complete | `tests: ok` |
| `x64lens version` prints the tool version | Complete | `x64lens 0.1.0-dev schema 0.1.0` |
| `x64lens help` prints usage | Complete | Help text printed expected usage |
| `x64lens info <file>` identifies valid ELF64 x86_64 binaries | Complete | `minimal_nopie` and `/bin/ls` parsed successfully |
| Invalid inputs fail safely | Complete | text and wrong-arch exit `4`, truncated ELF exits `5` |
| Sprint retrospective is written | Complete | This document |

## Known limitations carried forward

- Program headers are range-validated but not semantically parsed yet.
- Section headers are range-validated but not used for labels yet.
- Mitigation detection has not started.
- JSON output has not started.
- The tool supports only ELF64 x86_64 little-endian targets in Sprint 1.
- Direct text reporting is acceptable for Sprint 1, but analysis facts should move into internal records by Sprint 3.

## Sprint 1 follow-up backlog

These are not blockers for Sprint 1 completion, but should be completed early in Sprint 2:

- Compare `x64lens info` against `readelf -h` for `minimal_nopie` and `/bin/ls`.
- Add or improve `tools/compare-readelf.sh` so ELF header comparisons become repeatable.
- Optionally tag the Sprint 1 baseline after this closeout patch is committed.

## Contract review

- Development contract upheld: source/config comments are present, module boundaries were preserved, build steps and test steps were documented.
- Parser safety contract upheld: file-derived sizes and ranges are validated before metadata reporting.
- Output contract upheld: exit codes are stable for the implemented path, and text output is deterministic.
- Research contract upheld: no performance, exploitability, or analyst-usefulness claims were made without benchmark data.
- Release contract partially applicable: this is not a formal public release, but `make`, `make test`, and Docker smoke testing pass locally.
- Maintained public Sprint 1 status, roadmap, backlog, and validation authorities were reconciled at closeout.

## Sprint 2 entry condition

Sprint 2 may begin. The next technical objective is:

```text
program header parsing -> PT_LOAD discovery -> PF_X executable region mapping -> baseline mitigation signals
```

The first Sprint 2 implementation target should be `phdr.asm`, `regions.asm`, and the initial `mitigations` command path.
