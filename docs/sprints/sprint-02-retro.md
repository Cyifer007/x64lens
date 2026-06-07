# Sprint 02 Retrospective

## Status

Complete.

## Dates

Start: 2026-06-06
End: 2026-06-06

## Sprint goal

Map the binary as the Linux loader would and report first-order executable-region and mitigation metadata.

Sprint 1 proved that `x64lens info <file>` could safely map and validate ELF64 x86_64 binaries. Sprint 2 moved from file identity to runtime-relevant structure by parsing program headers, identifying executable load regions, and reporting baseline mitigation signals.

## Summary

Sprint 2 successfully added the first runtime mapping layer for `x64lens`. The tool now implements:

- `x64lens mitigations <file>` command routing.
- ELF64 program-header iteration in `src/phdr.asm`.
- `PT_LOAD` segment counting.
- `PT_LOAD + PF_X` executable-region extraction.
- Internal executable-region records in `src/regions.asm` and `include/structs.inc`.
- Baseline mitigation reporting for PIE, NX stack, RELRO presence, RWX load segments, and dynamic linking.
- A controlled executable-stack fixture, `minimal_execstack`, to validate NX stack disabled behavior.
- Regression tests for malformed program-header offsets and mitigation output behavior.

The key technical result is that `x64lens` now models the binary as the Linux loader would at the program-header layer. This is the correct foundation for Sprint 3 gadget scanning because the scanner should operate over executable `PT_LOAD + PF_X` regions, not over section headers.

## Completed deliverables

- [x] Parse ELF64 program headers in `src/phdr.asm`.
- [x] Validate `e_phoff`, `e_phentsize`, and `e_phnum` before iterating.
- [x] Identify `PT_LOAD` segments.
- [x] Identify `PF_X` executable regions.
- [x] Create internal executable-region record model in `src/regions.asm` and `include/structs.inc`.
- [x] Detect `PT_GNU_STACK`.
- [x] Detect NX stack vs executable stack.
- [x] Detect PIE using ELF type.
- [x] Detect RWX load segments.
- [x] Detect baseline RELRO using `PT_GNU_RELRO`.
- [x] Detect dynamic linking using `PT_DYNAMIC`.
- [x] Add initial `x64lens mitigations <file>` command path.
- [x] Add `minimal_execstack` toy corpus target.
- [x] Add tests for PIE/non-PIE and NX/executable-stack behavior.
- [x] Add malformed program-header offset regression test.
- [x] Compare program-header and mitigation output against `readelf -h` and `readelf -l`.

## Implementation notes

Sprint 2 added or materially updated these implementation modules:

- `src/main.asm`: dispatches `mitigations <file>`.
- `src/cli.asm`: includes `mitigations <file>` in help output.
- `src/mitigations.asm`: command orchestrator for file mapping, ELF validation, PHDR analysis, mitigation reporting, and cleanup.
- `src/phdr.asm`: safe program-header analysis.
- `src/regions.asm`: executable-region record storage.
- `src/report_text.asm`: mitigation and executable-region text output.
- `include/structs.inc`: `phdr_summary` and `executable_region` records.
- `tests/run-tests.sh`: regression coverage for Sprint 2 behavior.
- `tests/toy-src/Makefile`: adds `minimal_execstack`.
- `tools/compare-readelf.sh`: repeatable comparison helper for `x64lens` and `readelf`.

## Validation environment

Validation was performed locally from WSL2 Ubuntu using NASM, GNU `ld`, GCC, Make, binutils `readelf`, and Docker Desktop with WSL2 integration.

Docker validation used the repository-provided UID/GID-safe target:

```bash
make docker-test
```

## Validation commands run

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info ./tests/bin/minimal_pie_canary
./build/x64lens mitigations ./tests/bin/minimal_nopie
./build/x64lens mitigations ./tests/bin/minimal_pie_canary
./build/x64lens mitigations ./tests/bin/minimal_execstack
readelf -l ./tests/bin/minimal_nopie
readelf -l ./tests/bin/minimal_pie_canary
readelf -l ./tests/bin/minimal_execstack
./tools/compare-readelf.sh ./tests/bin/minimal_nopie ./build/x64lens
./tools/compare-readelf.sh ./tests/bin/minimal_pie_canary ./build/x64lens
./tools/compare-readelf.sh ./tests/bin/minimal_execstack ./build/x64lens
./build/x64lens info /bin/ls
./build/x64lens mitigations /bin/ls
readelf -l /bin/ls
```

## Key validation output

### Build

```text
cyifer007@Cyifer:~/x64lens$ make
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
cyifer007@Cyifer:~/x64lens$ make test
make -C tests/toy-src
make[1]: Entering directory '/home/cyifer007/x64lens/tests/toy-src'
make[1]: Nothing to be done for 'all'.
make[1]: Leaving directory '/home/cyifer007/x64lens/tests/toy-src'
mkdir -p tests/bin
cp tests/toy-src/minimal_nopie tests/bin/ 2>/dev/null || true
cp tests/toy-src/minimal_pie_canary tests/bin/ 2>/dev/null || true
cp tests/toy-src/minimal_execstack tests/bin/ 2>/dev/null || true
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
[test] malformed program header rejection
[test] mitigations non-PIE noexecstack
[test] mitigations PIE RELRO
[test] mitigations executable stack
tests: ok
```

### Docker validation

```text
cyifer007@Cyifer:~/x64lens$ make docker-test
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "/home/cyifer007/x64lens":/work -w /work x64lens-dev bash -lc 'make clean && make && make test'
rm -rf build
rm -rf tests/bin
make -C tests/toy-src clean || true
make[1]: Entering directory '/work/tests/toy-src'
rm -f minimal_nopie minimal_pie_canary minimal_execstack gadgets
make[1]: Leaving directory '/work/tests/toy-src'
mkdir -p build
...
bash tests/run-tests.sh
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
tests: ok
```

The omitted middle section is the expected NASM object build and `ld` link step, followed by the toy corpus build.

### `minimal_nopie` mitigation report

```text
cyifer007@Cyifer:~/x64lens$ ./build/x64lens mitigations ./tests/bin/minimal_nopie
x64lens 0.1.0-dev
Target: ./tests/bin/minimal_nopie

Mitigations:
  PIE: disabled
  NX stack: enabled
  RELRO: present
  RWX load segment: no
  Dynamic linking: yes
  Program header count: 0x000000000000000d
  LOAD segments: 0x0000000000000004
  Executable LOAD regions: 0x0000000000000001

Executable regions:
  - VA 0x0000000000401000, file offset 0x0000000000001000, file size 0x0000000000000161, mem size 0x0000000000000161, perms R-X
```

`readelf -l` confirmed the same high-level loader facts for this target: `EXEC` file type, 13 program headers, 4 `LOAD` segments, one `LOAD` segment with `R E` flags at virtual address `0x401000`, `GNU_STACK` with `RW`, `GNU_RELRO` present, and `DYNAMIC` present.

### `minimal_pie_canary` mitigation report

```text
cyifer007@Cyifer:~/x64lens$ ./build/x64lens mitigations ./tests/bin/minimal_pie_canary
x64lens 0.1.0-dev
Target: ./tests/bin/minimal_pie_canary

Mitigations:
  PIE: enabled
  NX stack: enabled
  RELRO: present
  RWX load segment: no
  Dynamic linking: yes
  Program header count: 0x000000000000000d
  LOAD segments: 0x0000000000000004
  Executable LOAD regions: 0x0000000000000001

Executable regions:
  - VA 0x0000000000001000, file offset 0x0000000000001000, file size 0x00000000000001bd, mem size 0x00000000000001bd, perms R-X
```

`readelf -l` confirmed the same high-level loader facts for this target: `DYN` file type, 13 program headers, 4 `LOAD` segments, one `LOAD` segment with `R E` flags at virtual address `0x1000`, `GNU_STACK` with `RW`, `GNU_RELRO` present, and `DYNAMIC` present.

### `minimal_execstack` mitigation report

```text
cyifer007@Cyifer:~/x64lens$ ./build/x64lens mitigations ./tests/bin/minimal_execstack
x64lens 0.1.0-dev
Target: ./tests/bin/minimal_execstack

Mitigations:
  PIE: disabled
  NX stack: disabled
  RELRO: present
  RWX load segment: no
  Dynamic linking: yes
  Program header count: 0x000000000000000d
  LOAD segments: 0x0000000000000004
  Executable LOAD regions: 0x0000000000000001

Executable regions:
  - VA 0x0000000000401000, file offset 0x0000000000001000, file size 0x0000000000000161, mem size 0x0000000000000161, perms R-X
```

`readelf -l` confirmed `GNU_STACK` with `RWE`, which matches `x64lens` reporting `NX stack: disabled`.

### System binary spot check: `/bin/ls`

```text
cyifer007@Cyifer:~/x64lens$ ./build/x64lens mitigations /bin/ls
x64lens 0.1.0-dev
Target: /bin/ls

Mitigations:
  PIE: enabled
  NX stack: enabled
  RELRO: present
  RWX load segment: no
  Dynamic linking: yes
  Program header count: 0x000000000000000d
  LOAD segments: 0x0000000000000004
  Executable LOAD regions: 0x0000000000000001

Executable regions:
  - VA 0x0000000000004000, file offset 0x0000000000004000, file size 0x0000000000014f41, mem size 0x0000000000014f41, perms R-X
```

`readelf -l /bin/ls` confirmed `DYN` file type, 13 program headers, 4 `LOAD` segments, one executable `LOAD` segment at virtual address and file offset `0x4000`, `GNU_STACK` with `RW`, `GNU_RELRO` present, and `DYNAMIC` present.

## Acceptance criteria review

| Acceptance criterion | Status | Evidence |
|---|---:|---|
| `make clean && make && make test` succeeds | Complete | Local `make test` ended with `tests: ok` |
| `make docker-test` succeeds | Complete | Docker run ended with `tests: ok` |
| `x64lens info <file>` remains stable | Complete | `info` still reports valid metadata for toy binaries and `/bin/ls` |
| `x64lens mitigations ./tests/bin/minimal_nopie` runs | Complete | Reports PIE disabled, NX stack enabled, one executable region |
| `x64lens mitigations ./tests/bin/minimal_pie_canary` runs | Complete | Reports PIE enabled, NX stack enabled, RELRO present |
| Executable `PT_LOAD` ranges are reported | Complete | All tested targets report one executable region |
| PIE differs correctly between fixtures | Complete | `minimal_nopie` disabled, `minimal_pie_canary` enabled |
| NX stack detection reflects compile flags | Complete | noexecstack fixtures enabled, execstack fixture disabled |
| Malformed program-header offsets fail safely | Complete | Test suite includes malformed PHDR rejection |
| Sprint 2 retrospective is written | Complete | This document |

## Known limitations carried forward

- `RELRO: present` currently means `PT_GNU_RELRO` is present. Full RELRO requires dynamic-section parsing for `BIND_NOW` or `DF_BIND_NOW`.
- Canary detection is not implemented. It requires import/symbol parsing, such as `__stack_chk_fail` detection.
- Section-header labels are not yet attached to executable regions.
- JSON output is not yet implemented.
- Gadget scanning is not yet implemented.
- PIE detection is based on `ET_DYN`; shared libraries are also `ET_DYN`, so wording must remain careful.
- The current executable-region buffer is fixed-capacity, with `EXEC_REGION_MAX` set to 64.

## Contract review

- Development contract upheld: program-header parsing, executable-region modeling, mitigation reporting, and text output remain separated by module boundary.
- Parser safety contract upheld: program-header table and segment file ranges are validated before use.
- Comment/documentation contract upheld: touched assembly, config, script, and documentation files include human-readable purpose and workflow comments.
- Output contract upheld: text output reports mitigation indicators and loader facts without claiming exploitability.
- Research contract upheld: no performance, coverage, or exploitability claims were made without benchmark data.
- Context persistence contract upheld: local project state must be updated after this sprint closeout.

## Sprint 2 follow-up backlog

These are not blockers for Sprint 2 completion, but should be addressed in later sprints:

- Automate structured comparison against `readelf` instead of human side-by-side review.
- Add `checksec` comparison when available.
- Add `rabin2 -I` comparison when available.
- Add full RELRO detection through dynamic-section parsing.
- Add canary indicator detection through dynamic symbol or symbol table parsing.
- Attach section names to executable regions for human readability.
- Prepare executable-region records for Sprint 3 scanner consumption.

## Sprint 3 entry condition

Sprint 3 may begin. The next technical objective is:

```text
executable-region scanning -> ret terminator discovery -> bounded backward candidate windows -> raw candidate output
```

The first Sprint 3 implementation targets should be:

- `src/scanner.asm`
- `src/patterns.asm`
- `src/report_text.asm`
- `include/structs.inc`
- `tests/toy-src/gadgets.S`
- `tests/run-tests.sh`

Sprint 3 should also decide whether to introduce the arena allocator immediately or first use a small fixed-capacity candidate buffer as a bridge.
