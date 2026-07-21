# Provisional Diagnostic Corpus

## Purpose

Sprint 11 uses a reproducible **development corpus** to test benchmark plumbing,
task definitions, loader-role differences, hardening combinations, and future
coverage gaps before the confirmatory campaign freezes in Sprint 15. The corpus
is deliberately provisional: its membership, build matrix, and method may change
when diagnostic evidence exposes a weak assumption.

Generated binaries are ignored local artifacts. The tracked repository contains
only the project-authored source, versioned corpus specification, builder,
validation harness, and documentation needed to regenerate them.

## Current corpus identity

```text
corpus_id:           s11-p056-provisional-v1
evidence_class:      diagnostic
frozen:              false
publication_eligible:false
targets:             24
```

The matrix is the exact cross product below:

| Dimension | Values | Count |
|---|---|---:|
| Compiler driver | GCC, Clang | 2 |
| Optimization | `-O0`, `-O2` | 2 |
| Requested ELF role | non-PIE executable, PIE-style executable, shared object | 3 |
| Hardening profile | minimal, hardened | 2 |

The project-authored source is:

```text
benchmarks/corpus/sources/sprint11-provisional-control-flow.c
```

It is freestanding, links without libc or startup objects, and defines a direct
Linux exit path. The builder **never executes generated targets**. Targets are
published mode `0444` for static analysis only.

## Build and verify

Check only the tools needed for corpus regeneration:

```bash
make corpus-tools-check
```

Build the versioned corpus:

```bash
make provisional-corpus-build
```

Verify an existing result:

```bash
make provisional-corpus-verify
```

Run the complete temporary regression, including two independent builds:

```bash
make provisional-corpus-smoke
```

Remove the generated version explicitly:

```bash
make clean-provisional-corpus
```

A second build with the same corpus identifier is rejected. Regeneration is an
explicit operation: remove the generated result first or introduce a new
versioned corpus identifier.

## Generated layout

The default local result is:

```text
benchmarks/corpus/generated/s11-p056-provisional-v1/
  corpus-manifest.json
  commands.tsv
  SHA256SUMS.txt
  inputs/
    spec/
    source/
    license/
    builder/
    tool-versions/
  logs/
  targets/
  work/
```

The manifest records:

- corpus and evidence-class identity;
- source, license, builder, compiler-driver, and requested-linker identities;
- exact matrix membership and one command record per target;
- canonical replay arguments with retained-input placeholders;
- output path, mode, size, SHA-256, and bounded ELF facts;
- effective fixed environment and host stratum;
- explicit target-nonexecution and publication boundaries.

`commands.tsv` and the manifest cross-reference each target. Verification checks
the complete member set, checksums, file types, link counts, modes, normalized
metadata, matrix order, command/output relationships, source/license bindings,
and ELF facts.

## Integrity and cleanup model

Corpus construction follows a fail-closed transaction:

```text
validated specification and repository inputs
  -> read-only retained snapshots
  -> bounded compiler matrix
  -> bounded ELF64 structural oracle
  -> late input/log/output reauthentication
  -> exact checksum manifest
  -> regular-file and metadata validation
  -> fsync files and directories
  -> renameat2(RENAME_NOREPLACE)
  -> final verification
```

`SIGINT`, `SIGTERM`, compiler timeout, compiler failure, malformed output,
mutation, or integrity failure removes staging state and publishes no final
corpus. Compiler children run in isolated process groups. Linux subreaper
cleanup also adopts, kills, and reaps descendants that escape their original
session or process group. Compiler stdout and stderr are drained concurrently through nonblocking pipes.
Each stream is bounded during execution; exceeding the specification limit
terminates and reaps the compiler process tree before staging is removed.

The fixed build environment rejects specification overrides for `PATH`, `HOME`,
`TMPDIR`, Python loader variables, dynamic-loader injection variables, and
compiler search-path variables. The effective `PATH` is derived from resolved
required tool locations plus standard system paths.

## ELF facts and authority boundary

The builder contains a small bounded ELF64 **generation oracle**. It verifies
only facts needed to prove that the requested build matrix was materialized:

- ELF64 little-endian x86_64 identity;
- `ET_EXEC` or `ET_DYN` output type;
- nonzero or unconstrained entry-point state as specified;
- `PT_LOAD`, executable-load, and RWX-load counts;
- `PT_DYNAMIC`, `PT_INTERP`, `PT_GNU_STACK`, and `PT_GNU_RELRO` presence;
- bounded GNU property-note evidence for x86 IBT and SHSTK.

This oracle is development infrastructure, not a second x64lens parser and not
runtime authority. Requested build-role labels do not settle the Sprint 12
PIE-versus-shared-object interpretation. Program headers remain the analyzer's
executable mapping authority.

## Reproducibility boundary

The smoke gate requires all retained files to match byte-for-byte and mode-for-
mode across two independent builds in one environment stratum. That result does
not imply cross-distribution or cross-toolchain-version reproducibility.
Compiler drivers and the requested GNU BFD linker are hashed and reauthenticated.
Each command also forces the resolved linker directory through the compiler
driver before applying `-fuse-ld=bfd`. Auxiliary compiler subprograms are not
bundled. The manifest therefore records
versions, target triples, resolved paths, hashes, and the host stratum needed to
interpret the result.

An unrelated same-UID process could transiently modify a compiler or linker path
between identity checks and restore it afterward. That threat remains outside
this provisional builder's trust boundary and is one reason these artifacts are
diagnostic rather than frozen evidence.

The generated corpus remains mutable same-user development evidence. Reverify
it immediately before a diagnostic campaign and bind campaign rows to target
hashes. Sprint 15 owns the final corpus, toolchain, license, and environment
freeze.

## Public artifact boundary

`benchmarks/corpus/generated/` is excluded from Git, Docker contexts, public
source overlays, and public bundle acceptance. Generated binaries may be
packaged later only as an explicitly approved research artifact with their own
license, checksum, and campaign contract.

## Next step

Patch 057 consumes this manifest surface when normalizing ROPgadget, Ropper, and
ropr task adapters. It must preserve tool-specific definitions and failed rows
rather than treating the 24 targets as proof of comparable coverage.
