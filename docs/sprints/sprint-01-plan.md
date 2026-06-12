# Sprint 01 Plan

## Dates

Start: 2026-06-06
End: 2026-06-06

## Sprint goal

Build the initial project skeleton and ELF64 header validation path.

## Planned deliverables

- [x] Stand up Ubuntu 24.04 development environment.
- [x] Verify WSL2 build path.
- [x] Verify Docker Desktop/WSL2 build path.
- [ ] Verify devcontainer path from VS Code. This is not a Sprint 1 blocker because Docker validation passed.
- [x] Update local-only project context under `.local/project-context/` if maintained.
- [x] Add human-readable comments to current source and config scaffolding.
- [x] Repository scaffold.
- [x] Documentation skeleton.
- [x] Makefile build contract.
- [x] Initial NASM source modules.
- [x] Initial CLI contract.
- [x] Initial development, research, output, and release contracts.
- [x] Implement `help` command.
- [x] Implement `version` command.
- [x] Implement file open/stat/mmap.
- [x] Implement ELF magic validation.
- [x] Validate ELF64 class.
- [x] Validate little-endian encoding.
- [x] Validate x86_64 machine type.
- [x] Print basic ELF header metadata.
- [x] Add invalid input tests.
- [x] Add valid toy ELF test.

## Acceptance criteria

- [x] `make` succeeds on Linux with NASM installed.
- [x] `make test` succeeds after local validation.
- [x] `x64lens version` prints the tool version.
- [x] `x64lens help` prints usage.
- [x] `x64lens info <file>` identifies valid ELF64 x86_64 binaries.
- [x] invalid inputs fail safely.
- [x] Sprint retrospective is written.

## Demo commands

```bash
make clean
make
make test
./build/x64lens version
./build/x64lens help
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info /bin/ls
```

## Risks

- Docker bind-mounted builds can create root-owned generated artifacts if containers run as root. Mitigation: use `make docker-shell`, `make docker-test`, and `make ownership-check`.
- NASM module organization may need refactoring.
- Linux syscall details may slow file mapping.
- ELF offset validation must be strict to prevent unsafe reads.
- Early direct printing must not become permanent architecture.

## Notes

This sprint establishes the maintainable foundation. It is more important to get the contracts and safety discipline right than to rush into gadget scanning.


## Next steps after successful Sprint 1 testing

Sprint 1 testing succeeded. Completed closeout actions:

1. Commit the Sprint 1 baseline. Complete: `cb4d649`.
2. Update `docs/sprints/sprint-01-retro.md` with exact outputs. Complete.
3. Update local-only project state with completed items and Sprint 2 focus. Complete in closeout patch.
4. Send the sprint summary to the appropriate academic or research reviewer if needed. Pending maintainer action.
5. Begin Sprint 2 by implementing program header parsing and executable region mapping. Next technical step.

If Sprint 1 testing fails:

1. Capture exact command, output, exit code, and environment.
2. If the failure is `Permission denied` under `build/`, run `make ownership-check` and see `docs/troubleshooting.md`.
3. Run `make print-vars`.
3. Confirm NASM and binutils versions.
4. Confirm target machine is Linux x86_64.
5. Debug with the smallest failing command first, usually `x64lens version` before `x64lens info`.


## Patch 004 implementation notes

This patch advances Sprint 1 from CLI scaffold to a working `info <file>` path. The command now:

1. Opens the target through `openat`.
2. Reads file metadata through `fstat`.
3. Maps the file read-only with `mmap`.
4. Validates ELF magic, ELF64 class, little-endian encoding, and `EM_X86_64`.
5. Validates basic ELF header table ranges before reporting.
6. Prints basic ELF metadata for valid targets.
7. Rejects non-ELF, wrong-architecture, and truncated inputs with stable exit codes.

## Next steps after Patch 004 validation

Patch 004 validation succeeded locally and in Docker. Completed actions:

1. Capture command output for `./build/x64lens info ./tests/bin/minimal_nopie` and `/bin/ls`. Complete.
2. Compare the core fields against `readelf -h`. Deferred to Sprint 2 follow-up automation, not a Sprint 1 blocker.
3. Write `docs/sprints/sprint-01-retro.md`. Complete.
4. Update local-only `PROJECT_STATE.md`. Complete in closeout patch.
5. Commit the Sprint 1 implementation baseline. Complete: `cb4d649`.
6. Begin Sprint 2 with program-header parsing and executable-region mapping. Next technical step.

If validation fails:

1. Run `make print-vars`.
2. Run `make clean && make` and capture the first assembler or linker error.
3. If the binary builds but crashes, run `gdb --args ./build/x64lens info /bin/ls`.
4. Compare failure path against `src/info.asm`, `src/filemap.asm`, and `src/elf64.asm`.
