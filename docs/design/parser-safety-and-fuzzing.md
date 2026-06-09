# Parser Safety and Fuzzing Plan

## Purpose

x64lens parses untrusted binary files. Because the implementation is assembly-first, parser safety must be visible, testable, and documented. This document defines the safety posture and future fuzzing plan.

## Current safety model

The current parser model is conservative:

- map targets read-only,
- validate file size before reading structured fields,
- validate ELF identity before deeper parsing,
- validate offset plus size ranges before table iteration,
- treat malformed files as expected input classes,
- return stable nonzero exit codes for invalid inputs,
- avoid exploitability claims from parser metadata alone.

## Mandatory safety invariants

Every file-derived value must be treated as hostile until validated:

- offsets,
- sizes,
- counts,
- entry sizes,
- virtual addresses used for reporting,
- file offsets used for scanning,
- table boundaries,
- string-table offsets,
- dynamic-section offsets,
- symbol-table offsets.

Pointer arithmetic must be range-checked before dereference.

## Existing invalid input categories

The validation corpus already tracks or plans these malformed input categories:

- empty file,
- plain text file,
- truncated ELF magic or header,
- wrong architecture,
- malformed program-header offset,
- impossible header counts,
- oversized section table.

## Future mutation smoke target

Sprint 7 should add a lightweight mutation smoke harness before deeper mitigation parsing expands the attack surface.

Candidate layout:

```text
tests/malformed/
tools/fuzz-mutated-elf-smoke.sh
benchmarks/results/fuzz-smoke-*.tsv
```

Minimum acceptance criteria:

```text
no SIGSEGV
no SIGBUS
no unbounded runtime
stable nonzero exit code for malformed inputs
regression fixture added for every parser crash
mutation seed list documented
```

## Fuzzing scope

The first fuzzing harness does not need to be a full coverage-guided fuzzer. A deterministic mutation smoke test is enough to catch common parser safety regressions while keeping the toolchain simple.

Future work may add AFL++, honggfuzz, libFuzzer-backed helper binaries, or corpus minimization. Those are not required before the first semester checkpoint.

## Paper language

The paper should say that parser safety is handled through explicit range validation and malformed-input regression testing. It should not claim formal memory safety.

Recommended wording:

```text
The prototype uses explicit bounds checks and malformed-input regression tests to reduce parser crash risk. It does not provide language-level memory safety guarantees.
```
