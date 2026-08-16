# Sprint 13 Patch 088 Validation

## Status

Implementation candidate pending exact-source native, Docker, producer, replay, parity, ABI, split-debug, delivery, and independent acceptance gates.

## Scope

Patch 088 corrects the Patch 087 transaction-completion, exact-mode, source-recovery descriptor, replay launcher/distribution, analyzer-projection, workload-oracle, ABI-stage, source-identity, evidence-ledger, and delivery findings. It also adds a bounded two-build split-debug packaging experiment.

No tracked file under `src/`, `include/`, or `schemas/` changes. Tool version `0.1.0-dev`, schema `0.2.0`, public output, semantic classes, scores, candidate capacity, deterministic ordering, and the decoder-free one-worker reference profile remain unchanged.

## Source preconditions

Use the exact base and candidate identities recorded in the Patch 088 source-identity authority. The guarded application path requires branch `main`, the exact base HEAD and tree, a clean index and worktree, and the authenticated patch SHA-256. The candidate-source recovery path is mutually exclusive.

## Focused validation

```bash
make patch087-corrective-regression-smoke
make sprint13-split-debug-packaging-contract-smoke
make sprint13-natural-frozen-replay-v2-smoke
make sprint13-natural-terminal-attribution-v2-smoke
make sprint13-abi-role-vector-equivalence-contract-smoke
make sprint13-workload-phase-attribution-smoke
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
```

Expected contract banners include:

```text
patch087-corrective-regression-smoke: ok ...
sprint13-split-debug-packaging-smoke: ok mode=selftest builds=2 behavior_profiles=15 behavior_executions=60 behavior_pairs=30 companion_controls=8 symbol_resolutions=12 minimum_reduction=0.50 product_adoption=0 ...
sprint13-natural-frozen-replay-v2-smoke: ok ... record_python_closures=5 run=deferred
sprint13-natural-terminal-attribution-v2-smoke: ok ... expected_required=1 run=deferred
sprint13-abi-role-vector-equivalence-smoke: ok ... run=deferred
sprint13-workload-phase-attribution-smoke: ok ... execution=deferred ...
```

## Native validation

```bash
make fix-perms
make normalize-perms
make clean
make
make samples
make test
S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

A clean committed candidate may derive the producer tree from `HEAD^{tree}`. A staged or otherwise non-clean candidate must provide the authenticated tree explicitly.

## Split-debug execution

```bash
mkdir -p .local/p088-results

S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> \
S13_PRODUCER_RESULT_DIR=./.local/p088-results/producer \
S13_SPLIT_DEBUG_PRODUCER_DIR=./.local/p088-results/producer \
S13_SPLIT_DEBUG_RESULT_DIR=./.local/p088-results/split-debug \
  make sprint13-split-debug-packaging-smoke
```

The experiment requires two independent producer builds, sixty behavior executions, thirty paired comparisons, eight debug-companion controls, twelve symbol resolutions, at least fifty-percent runtime-size reduction per build, zero behavior disagreement, and no local-path leakage. A successful experiment remains diagnostic and does not authorize product adoption.

## Docker, replay, ABI, and parity validation

```bash
S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> make docker-build
make docker-test
make docker-validation-smoke

S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p088-results/abi-vector \
  make sprint13-abi-role-vector-equivalence-smoke

S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p088-results/frozen-replay \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p088-results/terminal-attribution.json \
  make sprint13-natural-frozen-replay-v2

make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
```

Replay resolves bounded launcher symlink chains, retains launcher and interpreter identity separately, authenticates five Python distributions through RECORD members, and compares x64lens through the checked strip-debug projection. The raw source-binary identity remains retained separately.

## Candidate aggregate

```bash
S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> \
S13_PRODUCER_RESULT_DIR=./.local/p088-results/producer-acceptance \
S13_SPLIT_DEBUG_PRODUCER_DIR=./.local/p088-results/producer-acceptance \
S13_SPLIT_DEBUG_RESULT_DIR=./.local/p088-results/split-debug-acceptance \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p088-results/abi-vector-acceptance \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p088-results/frozen-replay-acceptance \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p088-results/terminal-attribution-acceptance.json \
  make sprint13-p088-acceptance-smoke
```

Expected future banner:

```text
sprint13-p088-acceptance-smoke: ok patch=88 sprint12=closed sprint13=active frozen-replay=sealed terminal-attribution=expected abi-vector-equivalence=private workload-phase-authority=frozen split-debug=diagnostic product-adoption=0 public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

The banner is an expectation until the exact-source local run completes.

## Claim boundary

Patch 088 adds no performance, RSS, comparative-coverage, baseline-equivalence, exploitability, public-role, score, decoder, concurrency, or packaging-adoption claim. The split-debug experiment is a diagnostic packaging study and remains separate from the reference runtime contract.
