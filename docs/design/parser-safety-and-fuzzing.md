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

Patch 025 implements the initial deterministic campaign through:

```text
tests/malformed/README.md
tests/malformed/regressions/README.md
tools/malformed-elf-smoke.py
tools/fuzz-mutated-elf-smoke.sh
make malformed-smoke
make capacity-smoke
make docker-validation-smoke
```

The default seed is the controlled generated `tests/bin/minimal_nopie` fixture. The runner derives a fixed 29-case catalog at runtime and removes generated binaries by default. The current cases cover:

- truncated ELF identity and fixed headers,
- class, endianness, version, and machine mismatches,
- program-header offsets, entry sizes, counts, and table ranges,
- section-header offsets, fixed 64-byte entry size, counts, and table ranges,
- executable `PT_LOAD` offset, file-size, memory-size, and end-of-file relationships,
- a valid final-byte `0xc2` executable-region boundary probe,
- valid metadata and integrated JSON controls.

Dynamic entries, symbol tables, strings, relocations, and note structures are not reachable yet and therefore remain future catalog extensions.

Candidate storage has separate controlled 4096- and 4097-`ret` fixtures. The current arena stores 4096 records, so the exact boundary must produce a complete JSON report. The overflow fixture must make focused and integrated text and JSON paths return exit code `6`, emit no partial stdout, and preserve the stable unsupported-feature diagnostic.

## Required per-case evidence

Each mutation case records:

```text
case_id
input_class
seed_hash
mutation_description
command
expected_exit
exit_code
signal
timeout
wall_time_ns
stdout_size
stderr_size
result
stderr_preview
```

The runner writes ignored TSV and JSON metadata artifacts under `tests/results/malformed/`. Generated mutations remain temporary by default. Only minimized, reviewed regressions are committed.

## Acceptance criteria

- no SIGSEGV, SIGBUS, or other signal,
- no timeout or unbounded runtime,
- no unexpected zero exit code for malformed input,
- no partial stdout for malformed parse failures,
- stable documented failure class,
- successful valid control and boundary cases,
- no write or execute mapping of target bytes,
- explicit exit code `6` for candidate-capacity exhaustion,
- regression fixture added for every stable crash or incorrect bounds acceptance,
- native, CI, and Docker results agree on pass/fail behavior.

## Resource limits

Hostile files can encode extreme counts even when arithmetic is technically in range. Parser modules should define explicit implementation limits where iteration or allocation could become unbounded. Exceeding a documented limit should return `EXIT_UNSUPPORTED` or another stable error instead of consuming uncontrolled resources.

Candidate storage now fails explicitly with `EXIT_UNSUPPORTED` before report emission when the arena would overflow. Research reports must never silently stop at capacity. Future bounded analysis paths that intentionally return partial results will require explicit completeness fields before they are enabled.

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

## Patch 026 mitigation-specific oracle

The broad deterministic mutation campaign is supplemented by a smaller program-header truth table. The matrix verifies expected successful facts and exact malformed behavior around checked arithmetic. Invalid file-backed `PT_LOAD` ranges are rejected in shared ELF64 validation, then revalidated by the program-header analyzer. Patch 028 replaces repeated table arithmetic with shared helpers and adds explicit program-header and section-header table-end overflow probes.

## Patch 028 checked arithmetic layer

The shared helper layer now covers:

- unsigned multiplication overflow,
- unsigned addition overflow,
- offset-plus-length exclusive end validation,
- full table extent validation,
- bounded per-entry table offsets.

Future dynamic, symbol, relocation, note, and string-table parsers should use this layer or a direct successor rather than introducing new open-coded pointer arithmetic.
