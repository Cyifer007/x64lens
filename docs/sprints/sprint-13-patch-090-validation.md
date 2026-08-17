# Sprint 13 Patch 090 Validation

## Status

Implementation candidate pending fresh NASM/native, ShellCheck, Docker, producer, replay, split-debug, reference-preflight, parity, delivery, and independent acceptance gates.

## Scope

Patch 090 corrects Patch 089 authority, replay, split-debug, source-recovery, bounded-input, transaction, documentation, evidence, and delivery findings. It also adds the bounded reference-only workload qualification preflight selected by strategic review.

No tracked path beneath `src/`, `include/`, or `schemas/` changes. Tool `0.1.0-dev`, schema `0.2.0`, public output, semantic classes, scores, candidate capacity, malformed-input behavior, deterministic ordering, and the decoder-free one-worker reference profile remain unchanged.

## Focused validation

```bash
make patch089-corrective-regression-smoke
make sprint13-workload-reference-preflight-contract-smoke
make sprint13-split-debug-packaging-contract-smoke
make sprint13-natural-frozen-replay-v2-smoke
make sprint13-natural-terminal-attribution-v2-smoke
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
```

Expected banners include:

```text
patch089-corrective-regression-smoke: ok ...
sprint13-workload-reference-preflight-smoke: ok mode=selftest fixtures=8 executions=80 ...
sprint13-split-debug-packaging-smoke: ok mode=selftest ...
```

## Reference-workload preflight

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p090-tree> \
S13_WORKLOAD_REFERENCE_PREFLIGHT_RESULT_DIR=./.local/p090-results/reference-preflight \
  make sprint13-workload-reference-preflight-smoke
```

The preflight runs one warmup and nine measured executions for each of eight fixed fixtures. Qualification requires at least six fixtures with successful stable output, median duration at least five times the authenticated floor, and MAD/median at most `0.10`.

The rows are diagnostic and reference-only. They must not be reused in the later paired phase-attribution matrix or cited as a performance comparison.

## Artifact-backed preflight observation

The retained unchanged-runtime analyzer completed 80/80 executions. Fewer than six fixtures qualified; only exact-capacity report workloads approached the intended duration class, while the remaining workloads were below the minimum duration, exceeded the dispersion bound, or both. The resulting diagnostic decision is `retire_phase_instrumentation_for_current_workloads`. A fresh Patch 090 run remains required for exact-source acceptance.

## Native validation

```bash
make ownership-check
make clean
make
make samples
make test
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p090-tree> make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

## Docker and parity validation

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p090-tree> make docker-build
make docker-test
make docker-validation-smoke
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p090-tree> make sprint12-role-property-environment-parity-smoke
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p090-tree> make sprint12-dynamic-metadata-environment-parity-smoke
```

## Complete acceptance

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p090-tree> make sprint13-p090-acceptance-smoke
```

Expected final banner:

```text
sprint13-p090-acceptance-smoke: ok patch=90 sprint12=closed sprint13=active reference-preflight=complete split-debug=opt-in-diagnostic product-adoption=0 public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

## Interpretation

A preflight pass authorizes only the fresh paired phase-attribution experiment. A preflight failure retires that experiment for the current workloads. Neither outcome changes product behavior or supports latency, RSS, comparative coverage, or superiority claims.
