# Backlog

## Sprint 0 / Environment and context

- [ ] Stand up WSL2 Ubuntu 24.04 or equivalent Linux development environment.
- [ ] Verify NASM, binutils, gcc, make, python3, git, and time are installed.
- [ ] Verify Docker/devcontainer build path.
- [ ] Upload or pin `PROJECT_CONTEXT.md` and `PROJECT_STATE.md` as project context.
- [ ] Confirm CSC-773 paper framing with Dr. Begian if needed.
- [ ] Confirm first Dr. Kramer checkpoint method: Zoom or email.
- [ ] Keep VM images out of repository.

## Sprint 1

- [ ] Implement file open/stat/mmap.
- [ ] Implement ELF magic validation.
- [ ] Validate ELF64 class.
- [ ] Validate little-endian encoding.
- [ ] Validate `EM_X86_64` machine type.
- [ ] Print basic ELF header metadata.
- [ ] Add invalid input tests.

## Sprint 2

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
