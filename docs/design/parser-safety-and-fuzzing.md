# Parser Safety and Fuzzing Plan

## Purpose

x64lens parses untrusted binary files in assembly. Parser safety must therefore be explicit, testable, reproducible, and visible in release evidence. This plan defines the safety invariants, deterministic hostile-input campaign, regression policy, and future fuzzing gates.

## Current safety model

The validated checkpoint already uses these controls:

- target files are mapped read-only,
- ELF identity is validated before deeper parsing,
- file-derived offsets and table ranges are checked before dereference,
- executable scanning is restricted to file-backed `PT_LOAD + PF_X` ranges,
- internal candidate storage uses a bounded command-lifetime arena,
- malformed files are expected input classes,
- invalid inputs return stable nonzero exit codes,
- target bytes are never executed.

These controls reduce risk, but they are not formal memory-safety guarantees.

## Mandatory safety invariants

Every file-derived value remains hostile until validated:

- offsets,
- sizes,
- counts,
- entry sizes,
- offset-plus-size arithmetic,
- count-times-entry-size arithmetic,
- string offsets and terminators,
- dynamic entries,
- symbol entries,
- relocation entries,
- section entries,
- note headers and property lengths,
- executable-region ranges,
- candidate window boundaries.

Before dereference, code must prove:

```text
offset <= file_size
size <= file_size - offset
entry_size != 0 when count != 0
count <= bounded implementation limit when one exists
count * entry_size does not overflow
table_end <= file_size
```

Each derived entry must also remain inside the validated table range.

## Bounded table direction

Dynamic, symbol, string, relocation, section, and note parsing should share one documented bounded-table discipline. The implementation may use reusable helpers or repeated macros, but every parser must expose the same proof obligations.

Conceptual bounded view:

```text
file_base
file_size
table_offset
entry_size
entry_count
table_end
```

Parser modules should consume validated views rather than recomputing unchecked pointer arithmetic from raw ELF fields.

## Existing regression categories

The committed invalid corpus covers or plans coverage for:

- empty file,
- plain text file,
- truncated ELF identity or header,
- wrong class, endianness, or architecture,
- malformed program-header offset,
- invalid entry size,
- impossible header count,
- arithmetic overflow,
- range extending beyond end of file,
- oversized section table,
- malformed dynamic table,
- malformed symbol or string table,
- malformed GNU property note,
- executable segment with inconsistent file size.

## Sprint 7 deterministic mutation smoke

Sprint 7 should add:

```text
tests/malformed/seeds/
tests/malformed/regressions/
tools/fuzz-mutated-elf-smoke.sh
make malformed-smoke
```

The first campaign should be deterministic and reproducible. For each seed, apply a fixed mutation catalog to fields such as:

- ELF class, data encoding, machine, and type,
- program-header offset, count, and entry size,
- segment offset, file size, memory size, and flags,
- section-header offset, count, and entry size,
- dynamic tag/value pairs,
- symbol and string table links and sizes,
- note lengths and alignments,
- candidate-bearing executable bytes near region boundaries.

## Required per-case evidence

Each mutation case should record:

```text
case_id
seed_hash
mutation_description
command
exit_code
signal
timeout
wall_time
stderr_size
```

Generated mutations remain ignored by default. Only minimized, reviewed regressions are committed.

## Acceptance criteria

- no SIGSEGV,
- no SIGBUS,
- no unbounded runtime,
- no unexpected zero exit code for malformed input,
- stable documented failure class,
- no write or execute mapping of target bytes,
- regression fixture added for every crash or incorrect bounds acceptance,
- native and Docker results agree on pass/fail behavior.

## Resource limits

Hostile files can encode extreme counts even when arithmetic is technically in range. Parser modules should define explicit implementation limits where iteration or allocation could become unbounded. Exceeding a documented limit should return `EXIT_UNSUPPORTED` or another stable error instead of consuming uncontrolled resources.

Candidate storage also requires explicit completeness state. Research reports must never silently stop at capacity.

## Future coverage-guided fuzzing gate

AFL++, honggfuzz, or another coverage-guided workflow may be added after:

- deterministic mutation smoke is stable,
- regression promotion and minimization rules exist,
- the build can expose useful instrumentation or a compatible harness,
- corpus and crash artifacts can be handled without polluting normal release bundles.

Coverage-guided fuzzing is not required for the `v0.1.0-dev` checkpoint. Hostile-input regression evidence is required before the research preview candidate.

## Paper language

Approved posture:

```text
The prototype uses read-only target mappings, explicit bounds checks, bounded internal storage, deterministic malformed-input testing, and regression fixtures to reduce parser crash risk. It does not provide language-level or formally verified memory-safety guarantees.
```
