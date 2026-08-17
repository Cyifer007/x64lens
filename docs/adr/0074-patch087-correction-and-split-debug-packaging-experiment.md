# ADR 0074: Patch 087 Correction and Split-Debug Packaging Experiment

## Status

Accepted as the historical Patch 088 implementation decision. Patch 088 did
not complete exact-source acceptance and was superseded by Patch 089.

## Context

Patch 087 preserved the analyzer runtime and froze a paired workload/phase experiment, but independent review found bounded defects in transaction completion, exact permission-state handling, source-recovery descriptor preflight, replay launcher and Python-distribution custody, analyzer identity across checkout paths, expected-threshold validation, stage cleanup, evidence sealing, and delivery metadata.

The same review found no basis for another analyzer feature. The only strategic proposal ready for bounded execution was a two-build split-debug packaging experiment. The current executable has no GNU build ID, so the experiment must use SHA-256, `.gnu_debuglink` filename and CRC, exact symbol controls, and exit-status/stdout/stderr agreement across the frozen fifteen-profile matrix for each build rather than assuming build-ID pairing.

## Decision

Patch 088:

1. implements candidate corrections intended to address the Patch 087 transaction, recovery, replay, ABI-stage, oracle, evidence, and delivery findings;
2. keeps the analyzer, includes, schema, semantic classes, scores, capacity, and public reports unchanged;
3. normalizes replay analyzer identity through a checked GNU `objcopy --strip-debug` projection while retaining the original source-binary identity;
4. resolves bounded pipx launcher symlink chains, derives five Python distribution closures from hash-bearing `importlib.metadata` `RECORD` rows, verifies current files against those rows, and records `RECORD` and closure digests rather than relying on mutable package-tree walks;
5. adds an executable diagnostic two-build split-debug experiment contract with sixty behavior executions, thirty matched behavior pairs, eight companion controls, and twelve symbol-resolution checks; and
6. does not adopt split-debug packaging as product policy.

The experiment requires a runtime-size reduction of at least fifty percent in each build, exit-status/stdout/stderr agreement across the frozen fifteen-profile matrix for both builds, successful debug-companion resolution, rejection of missing or CRC-mismatched companions, and no configured `/tmp/`, `/home/`, or `/mnt/` prefix in packaged bytes or checked resolution locations. Normalized runtime and companion bytes must match across builds; any difference rejects the experiment. Because the current build lacks a GNU build ID, SHA-256 and `.gnu_debuglink` CRC are the identity authorities for this experiment.

## Preserved boundaries

- Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable authority.
- Scanner, matcher, classifier, side-cars, scoring, and reporters remain separate.
- Raw, exact-suffix, semantic-exact, unknown, future decoder-backed, and scored facts remain distinct.
- Candidate capacity remains 4,096; candidate 4,097 fails with exit code 6 before stdout.
- Malformed inputs produce no partial report.
- The reference analyzer remains dependency-free, decoder-free, deterministic, and single-worker.
- No public field, semantic class, score, schema, decoder, concurrency, exploitability, performance, RSS, or comparative-coverage claim is added.

## Consequences

Patch 088 did not complete the required exact-source gates. Its retained
split-debug result remains diagnostic: it consumed producer builds bound to the
authenticated candidate tree and does not authorize product packaging changes.

## Follow-up

Patch 089 reconciles the retained split-debug result and preserves the already
frozen workload/phase authority as unexecuted. Fresh NASM/native, Docker,
replay, split-debug, workload, parity, and independent exact-source gates remain
required against the exact Patch 089 tree. Other measurement proposals remain
separate gates.
