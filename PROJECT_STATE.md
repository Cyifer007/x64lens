# x64lens Project State

This file tracks the active state of the project so future chat sessions do not drift.

## Current sprint

**Sprint 1:** repository foundation, environment setup, CLI skeleton, file mapping, ELF64 validation.

## Current status

- Repository skeleton exists.
- Documentation skeleton exists.
- Build contract exists.
- Initial assembly source modules exist.
- CLI scaffold exists for `help`, `version`, and `info <file>`.
- `info <file>` is still a scaffold stub.
- CSC-732 and CSC-773 are now joined into one project with separate deliverables.

## Active blockers

- A reliable Ubuntu 24.04 development environment must be selected and stood up.
- NASM must be available in the development environment.
- The current ChatGPT sandbox does not include NASM, so build validation must happen in WSL2, Docker, Codespaces, a VM, or Codex until the environment is available here.

## Next implementation step

Implement Sprint 1 runtime foundations:

1. Add `openat`, `fstat`, `mmap`, `munmap`, and `close` wrappers.
2. Implement `filemap.asm` to map a local target file read-only.
3. Implement `bounds.asm` helper routines for file offset validation.
4. Implement `elf64.asm` header validation.
5. Replace the `info` stub with real ELF64 metadata output.
6. Update tests to expect valid ELF detection and invalid input rejection.

## Next testing step

After implementation succeeds:

```bash
make clean
make
make samples
make test
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info /bin/ls
./build/x64lens info ./tests/invalid/text.txt
```

## Next documentation step

Update:

- `docs/sprints/sprint-01-retro.md`
- `docs/backlog.md`
- `docs/architecture.md`
- `PROJECT_STATE.md`

## Decision log

- Tool name remains `x64lens` for technical honesty and precise initial scope.
- `binlens` is avoided because it is too broad and creates possible naming confusion.
- WSL2 plus Docker/devcontainer is the preferred development model.
- VM images should not be committed to the repository.
- Diagrams should be kept as Mermaid/Graphviz source in the repository, not as manually edited screenshots only.
