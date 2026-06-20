# Malformed-Input Test Surface

## Purpose

This directory documents the deterministic hostile-input regression surface used by Sprint 7 and later parser work.

The default campaign derives mutations at runtime from the controlled `tests/bin/minimal_nopie` fixture. Generated files are temporary and are not committed. The runner records compact TSV and metadata artifacts under `tests/results/malformed/`, which is ignored by Git.

## Commands

```bash
make malformed-smoke
make fuzz-mutated-elf-smoke
```

The second command is a compatibility alias. The current campaign is deterministic mutation smoke, not coverage-guided fuzzing.

Configuration can be overridden without changing the repository:

```bash
MALFORMED_SEED=./tests/bin/minimal_nopie \
MALFORMED_TIMEOUT=2 \
make malformed-smoke
```

## Current mutation classes

The initial catalog covers:

- truncated headers,
- ELF identity and machine mismatches,
- invalid ELF header sizes and versions,
- unsafe program-header table offsets, entry sizes, and counts,
- unsafe section-header table offsets, entry sizes, and counts,
- executable `PT_LOAD` file-range inconsistencies,
- an incomplete `ret imm16` byte at an executable-region boundary,
- valid control cases for metadata and integrated JSON analysis.

Every case records its seed hash, mutation description, command shape, expected and observed exit status, signal, timeout state, elapsed nanoseconds, and output sizes.

## Regression promotion

A mutation becomes a committed regression fixture when it exposes a crash, out-of-bounds condition, incorrect acceptance of an unsafe range, or another stable parser defect that must survive future refactoring.

Reviewed regression binaries belong in `tests/malformed/regressions/`. Each fixture must be accompanied by a short explanation of the defect, expected exit code, affected command paths, and the patch that fixed it.

## Limits

Passing this smoke campaign does not prove memory safety. It provides deterministic evidence that the covered malformed structures do not cause signals, timeouts, or unexpected success. Coverage-guided fuzzing remains a later gate after regression handling and instrumentation are stable.
