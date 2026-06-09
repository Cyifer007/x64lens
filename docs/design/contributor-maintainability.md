# Contributor Maintainability Plan

## Purpose

A NASM-heavy repository has a smaller contributor pool than a C, Rust, Go, or Python project. This document defines maintainability practices that reduce that cost.

## Maintainability principles

- Keep modules narrow.
- Keep public symbol names descriptive.
- Document inputs, outputs, and clobbers near exported routines.
- Prefer fixed record layouts over ad hoc output parsing.
- Add tests before broadening a parser or classifier path.
- Preserve shell helper scripts as directly executable files.
- Keep generated artifacts out of Git.

## Register convention notes

Assembly routines should document practical register behavior:

- input registers,
- output registers,
- clobbered registers,
- preserved registers where relevant,
- whether the routine calls other routines,
- whether the routine assumes mapped-file pointers are already range-checked.

This is not bureaucracy. It is the substitute for type signatures and compiler-enforced interfaces.

## Pattern extension process

When adding a new exact pattern:

1. add the `PATTERN_*` constant,
2. add matcher logic in `patterns.asm`,
3. add text rendering in `report_text.asm`,
4. add a controlled fixture if practical,
5. update `docs/semantic-taxonomy.md`,
6. update tests and fixture validator expectations,
7. avoid semantic claims until `classifier.asm` maps the pattern.

## Semantic extension process

When adding a new semantic class:

1. define the class in `docs/semantic-taxonomy.md`,
2. map exact or decoded evidence to the class in `classifier.asm`,
3. update primitive coverage fields,
4. add tests that prove both positive and unknown cases,
5. update JSON schema only when JSON output exposes the new fact.

## Script permission rule

Shell helpers under `tools/`, `benchmarks/scripts/`, and `tests/run-tests.sh` should remain executable. If a patch extraction or Windows file operation drops execute bits, run:

```bash
make normalize-perms
make script-perms-check
```

The repository should treat accidental mode-only changes as drift unless they are intentional.

## Future contributor documents

Candidate future public documents:

- `docs/register-conventions.md`,
- `docs/how-to-add-pattern.md`,
- `docs/how-to-add-semantic-class.md`,
- `docs/module-map.md`,
- `docs/debugging-nasm.md`.
