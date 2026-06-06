# Sprint 01 Retrospective

## Status

Draft. Complete this file after running the Patch 004 validation commands locally.

## Sprint goal

Build the initial repository foundation and replace the `info <file>` scaffold with a safe ELF64 x86_64 validation path.

## Completed in Patch 004

- Build scaffold and module layout exist.
- WSL2 and Docker development paths exist.
- Docker root-owned artifact issue has a documented fix and safer Makefile targets.
- `x64lens help` and `x64lens version` exist.
- `x64lens info <file>` now maps a target file read-only.
- ELF64 identity validation now checks magic bytes, class, endian, version, and machine type.
- Basic ELF header table ranges are bounds-checked.
- Text output reports target path, ELF type, entry, program header metadata, section header metadata, and file size.
- Invalid input tests cover non-ELF, truncated ELF, and wrong-architecture ELF cases.

## Validation commands

```bash
make fix-perms
make clean
make
make samples
make test
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info /bin/ls
./build/x64lens info ./tests/invalid/text.txt ; echo $?
./build/x64lens info ./tests/invalid/truncated_elf.bin ; echo $?
./build/x64lens info ./tests/invalid/wrong_arch_elf.bin ; echo $?
```

## Expected behavior

- `make` succeeds.
- `make test` succeeds.
- Valid ELF64 x86_64 binaries exit `0` and print basic metadata.
- Plain text files exit `4`.
- Truncated ELF files exit `5`.
- Wrong-architecture ELF-like files exit `4`.

## Known limitations

- Program headers are only range-validated; they are not semantically parsed yet.
- Section headers are only range-validated; labels such as `.text` and `.plt` are not reported yet.
- Output is text only. JSON output remains a later sprint target.
- Hex values are fixed-width for determinism and may become prettier later.
- The parser currently supports only ELF64 x86_64 little-endian targets.

## Next sprint focus

Sprint 2 should implement program-header parsing, identify executable `PT_LOAD` regions, and begin baseline mitigation reporting for NX stack, PIE, RWX load segments, and RELRO indicators.

## Contract review

- Parser safety contract upheld: file-derived table ranges are checked before use.
- Module boundary contract upheld: file mapping, ELF validation, reporting, and command orchestration are separated.
- Documentation parity contract upheld: architecture, backlog, changelog, and sprint notes were updated with implementation changes.
- Research contract upheld: no performance or exploitability claims are made from this patch.
