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
- [x] Compare `x64lens info` against `readelf -h` using toy binaries and `/bin/ls`.
- [x] Add `tools/compare-readelf.sh` helper for repeatable side-by-side review.

## Sprint 2

- [x] Parse program headers.
- [x] Identify `PT_LOAD` segments.
- [x] Identify `PF_X` executable regions.
- [x] Create executable-region record model.
- [x] Detect `PT_GNU_STACK`.
- [x] Detect NX stack.
- [x] Detect executable stack.
- [x] Detect PIE.
- [x] Detect RWX load segments.
- [x] Detect baseline RELRO using `PT_GNU_RELRO`.
- [x] Detect dynamic linking using `PT_DYNAMIC`.
- [x] Add `x64lens mitigations <file>` command.
- [x] Add `minimal_execstack` toy corpus target.
- [x] Add malformed program-header rejection test.
- [x] Validate Sprint 2 implementation on WSL2 and Docker.
- [x] Compare mitigation findings against `readelf -l` for toy binaries and `/bin/ls`.
- [x] Write `docs/sprints/sprint-02-retro.md`.

## Sprint 2 follow-up hardening

- [ ] Automate `readelf` field comparison instead of side-by-side review.
- [ ] Add `checksec` comparison when available.
- [ ] Add `rabin2 -I` comparison when available.
- [ ] Add full RELRO detection through dynamic-section parsing.
- [ ] Add canary indicator detection through dynamic symbol or symbol-table parsing.
- [ ] Add section-header labels for executable regions.

## Sprint 3

- [ ] Decide fixed candidate buffer vs immediate arena allocator for raw gadget candidates.
- [ ] Implement arena allocator or fixed candidate record buffer.
- [ ] Implement executable region scanner.
- [ ] Detect `ret` terminators.
- [ ] Detect `ret imm16` terminators.
- [ ] Add `--max-depth` or internal default max-depth constant.
- [ ] Extract bounded backward candidate windows.
- [ ] Output raw candidates.
- [ ] Validate against `tests/bin/gadgets`.
- [ ] Add first scanner smoke measurement.

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
