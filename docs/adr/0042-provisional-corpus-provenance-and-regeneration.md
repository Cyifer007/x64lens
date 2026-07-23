# ADR 0042: Provisional Corpus Provenance and Regeneration

## Status

Accepted for Sprint 11 Patch 056.

## Context

Patch 055 established a high-resolution diagnostic runner and demonstrated that
measurement integrity depends on explicit eligibility, hash-bound retained
inputs and write-sealed execution copies, child cleanup, late artifact
authentication, and transactional publication. Sprint 11 still lacked a
reproducible target set with source, license, build-command, tool, and output
identity.

Using installed system binaries alone would make results dependent on the host
distribution and would not provide exact build provenance. Committing generated
binaries would enlarge the public repository, obscure regeneration, and blur
the boundary between provisional development evidence and the Sprint 15-frozen
campaign. Starting Sprint 12 loader work first would leave benchmark design
without the evidence needed to prioritize that work.

## Decision

Add an external standard-library corpus builder over one project-authored,
freestanding C source and a versioned JSON matrix specification.

The Patch 056 matrix contains 24 targets:

```text
2 compiler drivers
x 2 optimization profiles
x 3 requested ELF roles
x 2 hardening profiles
= 24 targets
```

The generated corpus is identified as:

```text
evidence_class: diagnostic
frozen: false
publication_eligible: false
```

The builder:

1. validates the specification, source, license, platform, and required tools;
2. rejects reserved environment overrides;
3. snapshots source, license, specification, and builder inputs read-only;
4. records compiler-driver and requested-linker versions, target triples,
   paths, modes, timestamps, and SHA-256 identities;
5. forces the resolved GNU BFD linker directory through the compiler driver,
   then runs each compiler in a separate process group under a fixed
   environment and bounded output capture;
6. validates bounded ELF64 generation facts without executing a target;
7. publishes targets mode `0444`;
8. reauthenticates retained inputs, logs, tools, and outputs after the final
   compiler exits;
9. writes an exact checksum inventory and cross-linked command/target manifest;
10. normalizes file and directory modes and timestamps;
11. publishes through `renameat2(RENAME_NOREPLACE)` only after fsync; and
12. verifies the final tree before returning success.

Generated targets remain ignored under `benchmarks/corpus/generated/`. They are
also rejected from ordinary public source bundles and excluded from Docker build
contexts.

## Architecture boundary

Patch 056 does not modify the analyzer, CLI, JSON schema, scanner, classifier,
side-cars, scoring, capacity, decoder policy, or worker policy.

The builder's bounded ELF reader is a generation oracle. It confirms requested
matrix properties but does not become analyzer truth and does not resolve the
Sprint 12 PIE-versus-shared-object, GNU property, overlap, or extended-numbering
contracts. Program headers remain x64lens runtime mapping authority.

GCC and Clang are development inputs only. The freestanding x64lens runtime
remains dependency-free, decoder-free, one-worker, bounded, and suitable for
air-gapped or constrained deployment.

## Failure and interruption policy

A compiler failure, timeout, malformed output, source/tool mutation, integrity
mismatch, signal, unsafe member, or existing final identity produces no new
published corpus. Spawn registration defers `SIGINT` and `SIGTERM` until the
child is registered. Every compiler starts in a new session, and Linux
subreaper cleanup kills and reaps both same-group helpers and descendants that
escape through `setsid` before staging cleanup.

The smoke gate proves:

- two byte/mode/mtime-identical builds;
- exact 24-target matrix membership;
- source, license, command, and output reconciliation;
- explicit non-public eligibility;
- no-replace behavior;
- reserved-environment rejection;
- tamper rejection after checksum regeneration;
- symlink rejection;
- active-command cleanup for an escaped `setsid` descendant;
- deterministic interruption cleanup in the post-spawn registration window; and
- in-flight compiler output-limit enforcement with process-tree cleanup.

## Consequences

### Positive

- Diagnostic targets have reproducible source and build provenance.
- GCC/Clang, optimization, role, and hardening differences can be studied
  without changing the analyzer.
- Corpus bytes remain outside the public source tree and can be rebuilt locally.
- The same manifest surface can feed Patch 058 adapters and later campaign
  generation.
- The design preserves air-gapped runtime and CI/CD deployment characteristics.

### Limitations

- Byte reproducibility is established only within the recorded tool and host
  stratum; it is not asserted across compiler versions or distributions.
- Auxiliary compiler programs are not bundled, although compiler drivers and
  the requested linker are hashed and reauthenticated and the resolved linker
  directory is forced through the driver.
- Transient same-UID mutation of compiler or linker paths between identity
  checks remains outside this diagnostic builder's trust boundary.
- The 24-target matrix is intentionally small and does not represent the final
  Tier 1-4 corpus.
- Requested `ET_DYN` roles remain build intents, not release-facing loader
  classifications.
- Same-user mutation of a completed diagnostic corpus remains possible; callers
  must reverify and bind target hashes before measurement or promotion.

## Rejected alternatives

- **System binaries only:** rejected because distribution provenance and rebuild
  commands are not controlled.
- **Commit generated binaries:** rejected because provisional bytes should not
  become permanent public source artifacts.
- **Use x64lens output as the corpus oracle:** rejected because corpus creation
  must not circularly validate the analyzer under study.
- **Resolve Sprint 12 loader semantics in the builder:** rejected because that
  would duplicate or preempt the committed analyzer architecture.
- **Add corpus generation to the runtime CLI:** rejected because benchmark and
  build orchestration remain external development infrastructure.

## Patch 057 correction

Post-Patch-056 validation found that undeclared compiler side files could enter
the retained corpus, the raw Make clean recipe accepted an unsafe caller-
controlled path, and best-effort staging removal could hide residue. Patch 057
therefore requires an otherwise-empty shared command workspace, permits only the
one named compiler output, verifies the exact retained file and directory set,
derives cleanup solely from the validated corpus identifier and output root,
and removes staging through checked file-descriptor-relative traversal. The
clean target is phony and delegates to the builder; it contains no recursive
shell deletion. The non-root checksum-mutation oracle now makes its copied
checksum writable only for regeneration and restores the retained mode.
