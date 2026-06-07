# Backlog

## Sprint 0 / Environment and context

- [x] Stand up WSL2 Ubuntu 24.04 or equivalent Linux development environment.
- [x] Verify NASM, binutils, gcc, make, python3, git, and time are installed.
- [x] Verify Docker/devcontainer build path.
- [ ] Keep VM images out of repository.

## Sprint 1

- [x] Implement file open/stat/mmap.
- [x] Implement ELF magic validation.
- [x] Validate ELF64 class.
- [x] Validate little-endian encoding.
- [x] Validate `EM_X86_64` machine type.
- [x] Print basic ELF header metadata.
- [x] Add invalid input tests.

## Sprint 1 follow-up hardening

- [x] Validate Sprint 1 implementation on WSL2 and Docker.
- [x] Write `docs/sprints/sprint-01-retro.md` after local validation.
- [ ] Compare `x64lens info /bin/ls` against `readelf -h /bin/ls`. This is a Sprint 2 validation hardening item, not a Sprint 1 blocker.
- [ ] Add a small `tools/compare-readelf.sh` enhancement for automated header comparison.

## Sprint 2

Patch 006 implements the first Sprint 2 code path. Items remain unchecked until local WSL2 and Docker validation succeeds.

- [ ] Parse program headers.
- [ ] Identify `PT_LOAD` segments.
- [ ] Identify `PF_X` executable regions.
- [ ] Detect `PT_GNU_STACK`.
- [ ] Detect NX stack.
- [ ] Detect PIE.
- [ ] Detect RWX load segments.
- [ ] Detect baseline RELRO.

## Sprint 3

- [ ] Implement arena allocator.
- [ ] Implement executable region scanner.
- [ ] Detect `ret` terminators.
- [ ] Detect `ret imm16` terminators.
- [ ] Add `--max-depth`.
- [ ] Output raw candidates.

## Sprint 4

- [ ] Add pattern table.
- [ ] Classify `pop reg; ret` gadgets.
- [ ] Classify `leave; ret`.
- [ ] Classify `syscall`.
- [ ] Add register bitmap.
- [ ] Add primitive coverage summary.

## Sprint 5

- [ ] Add scoring model.
- [ ] Add JSON output.
- [ ] Add benchmark harness.
- [ ] Compare with ROPgadget.
- [ ] Compare with Ropper.
- [ ] Compare with ropr if available.

## Sprint 6

- [ ] Finalize README.
- [ ] Finalize architecture document.
- [ ] Finalize benchmark methodology.
- [ ] Produce final benchmark table.
- [ ] Produce paper outline.
- [ ] Produce final demo script.

## Local-only/private process backlog

Private context files, course-specific notes, and session-state tracking belong under `.local/project-context/` and are intentionally excluded from public commits.
