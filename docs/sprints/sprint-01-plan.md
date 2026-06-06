# Sprint 01 Plan

## Dates

Start: TBD
End: TBD

## Sprint goal

Build the initial project skeleton and ELF64 header validation path.

## Planned deliverables

- [ ] Stand up Ubuntu 24.04 development environment.
- [x] Verify WSL2 build path.
- [x] Verify Docker Desktop/WSL2 build path.
- [ ] Verify devcontainer path from VS Code.
- [ ] Update local-only project context under `.local/project-context/` if maintained.
- [ ] Add human-readable comments to current source and config scaffolding.
- [x] Repository scaffold.
- [x] Documentation skeleton.
- [x] Makefile build contract.
- [x] Initial NASM source modules.
- [x] Initial CLI contract.
- [x] Initial development, research, output, and release contracts.
- [ ] Implement `help` command.
- [ ] Implement `version` command.
- [ ] Implement file open/stat/mmap.
- [ ] Implement ELF magic validation.
- [ ] Validate ELF64 class.
- [ ] Validate little-endian encoding.
- [ ] Validate x86_64 machine type.
- [ ] Print basic ELF header metadata.
- [ ] Add invalid input tests.
- [ ] Add valid toy ELF test.

## Acceptance criteria

- [ ] `make` succeeds on Linux with NASM installed.
- [ ] `make test` succeeds.
- [ ] `x64lens version` prints the tool version.
- [ ] `x64lens help` prints usage.
- [ ] `x64lens info <file>` identifies valid ELF64 x86_64 binaries.
- [ ] invalid inputs fail safely.
- [ ] Sprint retrospective is written.

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

If Sprint 1 testing succeeds:

1. Commit and tag the Sprint 1 baseline.
2. Update `docs/sprints/sprint-01-retro.md` with exact outputs.
3. Update local-only project state with completed items and Sprint 2 focus.
4. Send the sprint summary to the appropriate academic or research reviewer if needed.
5. Begin Sprint 2 by implementing program header parsing and executable region mapping.

If Sprint 1 testing fails:

1. Capture exact command, output, exit code, and environment.
2. If the failure is `Permission denied` under `build/`, run `make ownership-check` and see `docs/troubleshooting.md`.
3. Run `make print-vars`.
3. Confirm NASM and binutils versions.
4. Confirm target machine is Linux x86_64.
5. Debug with the smallest failing command first, usually `x64lens version` before `x64lens info`.
