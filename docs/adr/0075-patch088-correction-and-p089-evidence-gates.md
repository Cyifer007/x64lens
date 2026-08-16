# ADR 0075: Patch 088 Correction and Patch 089 Evidence Gates

## Status

Accepted as the Patch 089 implementation decision; exact-source acceptance remains pending.

## Context

Patch 088 retained the analyzer runtime and executed a bounded split-debug packaging preflight, but review found that several evidence authorities could still accept the wrong identity, an incomplete closure, or a resealed substitute. The frozen replay mixed predecessor raw-tool identity with the current debug-insensitive analyzer projection. Split-debug verification did not independently bind every retained member to the producer generation and source tree. The workload authority did not reject duplicate fixture identities. Candidate-source recovery buffered complete files and lacked explicit per-file and aggregate byte ceilings.

The findings were concentrated in orchestration, evidence, packaging, and recovery code. No review evidence justified changing the analyzer, public schema, semantic classes, scores, candidate capacity, decoder policy, or worker model.

## Decision

Patch 089:

1. separates predecessor replay identity from the current analyzer projection and requires exact hash-bearing Python distribution closures;
2. strengthens split-debug result custody with exact membership, mode, topology, producer-generation, source-tree, behavior-profile, known-symbol, and interruption checks;
3. requires the eight workload fixtures to match the frozen ordered authority exactly and to remain unique;
4. makes candidate-source recovery streaming and bounded by explicit per-file, aggregate-file, and archive-size ceilings, with normalized malformed-authority diagnostics;
5. applies the accepted public Markdown corrections and advances public chronology to Patch 089;
6. retains split-debug only as an opt-in diagnostic release experiment; and
7. adds no runtime or public product feature.

## Split-debug interpretation

The diagnostic experiment retains two independent builds, sixty behavior executions, thirty behavior pairs, eight companion controls, and twelve symbol resolutions. A runtime-tier size reduction of at least fifty percent remains required.

The current method uses bounded post-link path redaction. It is not path-stable DWARF production, and the runtime plus companion did not establish a total-transfer reduction in the retained preflight. Therefore:

```text
opt-in release experiment: allowed after fresh acceptance evidence
production/default adoption: not authorized
path-stable DWARF claim: not authorized
total-transfer saving claim: not authorized
```

## Preserved boundaries

- Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable authority.
- Mapping, ELF/loader parsing, raw scanning, exact matching, semantic classification, side-cars, scoring, and reporting remain separate.
- Raw, exact-suffix, semantic-exact, unknown, future decoder-backed, and scored facts remain distinct.
- Candidate capacity remains 4,096; candidate 4,097 returns exit code 6 before stdout.
- Malformed input emits no partial report.
- Targets remain read-only and are never executed.
- The reference runtime remains dependency-free, decoder-free, deterministic, and one-worker.
- Public schema remains `0.2.0`.

## Consequences

Patch 089 improves trust in replay, package, workload, and recovery evidence without manufacturing a performance, coverage, RSS, exploitability, or packaging-adoption claim. Fresh native, Docker, replay, split-debug, workload, parity, and independent acceptance remain required before the candidate can be accepted.

## Validation

Focused repository gates:

```bash
make patch088-corrective-regression-smoke
make sprint13-natural-frozen-replay-v2-smoke
make sprint13-natural-terminal-attribution-v2-smoke
make sprint13-split-debug-packaging-contract-smoke
make sprint13-workload-phase-attribution-smoke
make sprint12-closeout-smoke
make sprint12-continuation-smoke
```

Complete exact-source acceptance is owned by `make sprint13-p089-acceptance-smoke` in a qualified local environment.
