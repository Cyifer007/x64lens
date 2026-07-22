# Sprint 11 Patch 056 Validation

## Purpose

Patch 056 adds the provisional corpus manifest and deterministic regeneration
workflow required by the Sprint 11 diagnostic benchmark foundation. It also
carries the accepted Patch 055 runner hardening into the current source state.
No analyzer runtime behavior, record layout, CLI field, schema meaning, score,
capacity, decoder policy, or worker policy changes.

## Implemented surface

```text
benchmarks/corpus/sources/sprint11-provisional-control-flow.c
benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json
benchmarks/scripts/build-provisional-corpus.py
tools/provisional-corpus-smoke.py
benchmarks/corpus/README.md
docs/adr/0042-provisional-corpus-provenance-and-regeneration.md
```

The generated corpus is ignored and excluded from normal public source and
Docker artifacts.

## Matrix contract

```text
GCC, Clang
x O0, O2
x non-PIE executable, PIE-style executable, shared object
x minimal, hardened
= 24 targets
```

Expected structural totals for the current matrix:

```text
ET_EXEC:                       8
ET_DYN:                       16
executable PT_GNU_STACK:      12
x86 IBT property:             12
x86 SHSTK property:           12
PT_GNU_RELRO:                  8
RWX PT_LOAD:                   0
executed targets:              0
```

The four hardened non-dynamic executables intentionally have no
`PT_GNU_RELRO`; RELRO is expected only for dynamic outputs in this provisional
matrix.

## Focused commands

```bash
make corpus-tools-check
make provisional-corpus-smoke
```

Expected output:

```text
corpus-tools-check: ok
provisional-corpus-smoke: ok targets=24 rebuilds=2 invalid_specs=8 tamper_cases=5 interruption_cleanup=3 capture_limits=1 clean_guards=1 make_clean_guards=1 membership_rejections=1
```

The smoke gate performs two complete builds and requires identical retained
files, modes, and normalized timestamps. It also validates:

- source and license hashes;
- exact matrix product and target ordering;
- compiler-driver and requested-linker identity, including a forced resolved
  linker-directory selector in each canonical command;
- canonical command and output relationships;
- bounded ELF generation facts;
- explicit `diagnostic`, `frozen=false`, and `publication_eligible=false` state;
- fixed environment and reserved-variable rejection;
- recorded target-nonexecution policy and target mode `0444`;
- late reauthentication;
- no-replace publication;
- regenerated-checksum semantic tamper rejection;
- non-regular member rejection;
- active-command cleanup of a descendant that escapes through `setsid`;
- compiler cleanup after `SIGINT` in the post-spawn registration window;
- exact compiler-workspace and retained-member closure;
- manifest-derived clean-path containment and Make `.PHONY` enforcement;
- cleanup of mode-locked staging members; and
- in-flight stdout capture-limit enforcement with no published or staging residue.

## Manual regeneration

```bash
make clean-provisional-corpus
make provisional-corpus-build
make provisional-corpus-verify
```

Expected output includes:

```text
provisional-corpus-build: ok corpus=s11-p056-provisional-v1 targets=24 compilers=2 optimizations=2 artifacts=3 hardening=2
provisional-corpus-verify: ok corpus=s11-p056-provisional-v1 targets=24 compilers=2 optimizations=2 artifacts=3 hardening=2
```

A second build without the explicit clean step must fail without changing the
existing result.

## Patch 055 corrective baseline

Patch 056 retains the corrected diagnostic-runner behavior:

- resource accounting describes the selected child plus descendants that child
  actually waited for, not an unsupported direct-child-only claim;
- diagnostic specifications must explicitly declare
  `publication_eligible=false`;
- signals cannot escape the child-registration window;
- measured tool, target, and timer inputs use write-sealed execution copies;
- retained artifacts are reauthenticated after the last measured child; and
- final publication remains no-replace and transaction-safe.

Required focused regression commands remain:

```bash
make patch054-corrective-regression-smoke
make diagnostic-task-definitions-smoke
make diagnostic-runner-smoke
make sprint11-diagnostic-reference-smoke
```

## Full acceptance

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make provisional-corpus-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

Docker metadata-path failures are environment failures only when the full
qualified container rerun passes. Generated corpus targets must not enter the
Docker context or a normal public source overlay.

## Preserved runtime invariants

- Program headers and file-backed `PT_LOAD + PF_X` remain executable authority.
- Candidate capacity remains 4096.
- Candidate 4097 fails before stdout.
- Malformed parse failures produce no partial stdout.
- The command arena remains 819200 bytes.
- Schema remains `0.2.0`.
- The reference runtime remains dependency-free, decoder-free, one-worker,
  bounded, and deterministic.

## Next step

Patch 057 corrects the diagnostic-integrity findings discovered after Patch
056. Patch 058 then adds normalized baseline adapters over the versioned corpus.
It must retain each baseline's task definition, version, command, failures, and
output scope rather than treating unlike gadget counts as equivalent.
