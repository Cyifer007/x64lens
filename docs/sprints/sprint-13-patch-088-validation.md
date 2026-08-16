# Sprint 13 Patch 088 Validation

## Status

Historical implementation candidate. Patch 088 did not complete exact-source
acceptance and was superseded by Patch 089. This record preserves its intended
validation surface and claim boundaries.

## Scope

Patch 088 implements candidate corrections intended to address the Patch 087
transaction-completion, exact-mode, source-recovery descriptor, replay
launcher/distribution, analyzer-projection,
workload-oracle, ABI-stage, source-identity, evidence-ledger, and delivery
findings. It also adds a bounded two-build split-debug packaging experiment.

No tracked file under `src/`, `include/`, or `schemas/` changes. Tool version
`0.1.0-dev`, schema `0.2.0`, public output, semantic classes, scores, candidate
capacity, deterministic ordering, and the decoder-free one-worker reference
profile remain unchanged.

## Source preconditions

| Role | Commit | Tree |
|---|---|---|
| Patch 088 base | `e5b3d6d6bd27acd3f4e41c3a2acbb231a6b9fc2b` | `47a4ee9868914abc1736ed1ccc76515c0d46f676` |
| Reviewed Patch 088 input | `cf149850b04aeb72fbd32c049128c71bf4b60bde` | `5abf83e13f5b182d624b998ce888ec330e6789b9` |

The guarded application path requires branch `main`, the exact base HEAD and
tree, a clean index and worktree, and, when a patch package is used, the patch
digest supplied by its delivery manifest. Candidate-source recovery is a
mutually exclusive application path.

The reviewed-input tree above authenticates the source before documentation
correction. Every tracked correction produces a different tree. In the commands
below, set `<authenticated-post-correction-tree>` to the exact final tree from
the current source-identity manifest or delivery manifest; do not reuse a predecessor
tree or the reviewed-input tree after its bytes change.

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
make ownership-check
# After source-state capture, perform a clean rebuild.
make clean
make
make samples
make test
S13_EXPECTED_CANDIDATE_TREE=<authenticated-post-correction-tree> make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

`fix-perms` and `normalize-perms` are repair helpers, not validation gates. Run
them only after a diagnosed ownership or mode problem and explicit repair
authorization, then rerun `make ownership-check` before continuing.

A clean committed candidate may derive the producer tree from `HEAD^{tree}`. A
staged or otherwise non-clean candidate must provide the authenticated tree
explicitly.

## Split-debug execution

```bash
mkdir -p .local/p088-results

S13_EXPECTED_CANDIDATE_TREE=<authenticated-post-correction-tree> \
S13_PRODUCER_RESULT_DIR=./.local/p088-results/producer \
S13_SPLIT_DEBUG_PRODUCER_DIR=./.local/p088-results/producer \
S13_SPLIT_DEBUG_RESULT_DIR=./.local/p088-results/split-debug \
  make sprint13-split-debug-packaging-smoke
```

The experiment requires two independent producer builds, sixty behavior
executions, thirty paired comparisons, eight debug-companion controls, twelve
symbol resolutions, and a runtime-size reduction of at least fifty percent per build.
Exit status, stdout, and stderr must agree across the frozen fifteen-profile
matrix for both builds. Packaged bytes and checked resolution locations must not
contain the configured `/tmp/`, `/home/`, or `/mnt/` prefixes. A successful
experiment remains diagnostic and does not authorize product adoption.

## Docker, replay, ABI, and parity validation

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-post-correction-tree> make docker-build
make docker-test
make docker-validation-smoke

S13_EXPECTED_CANDIDATE_TREE=<authenticated-post-correction-tree> \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p088-results/abi-vector \
  make sprint13-abi-role-vector-equivalence-smoke

S13_EXPECTED_CANDIDATE_TREE=<authenticated-post-correction-tree> \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p088-results/frozen-replay \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p088-results/terminal-attribution.json \
  make sprint13-natural-frozen-replay-v2

make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
```

Replay resolves bounded launcher symlink chains and retains launcher and
interpreter identity separately. It derives five Python distribution closures
from hash-bearing `RECORD` rows, verifies the listed current files against those
hashes, and retains both `RECORD` and closure digests. It compares x64lens
through the checked strip-debug projection while retaining the raw source-binary
identity separately.

## Candidate aggregate

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-post-correction-tree> \
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

The banner was the Patch 088 expectation; Patch 089 now owns current exact-source acceptance.

## Claim boundary

Patch 088 adds no performance, RSS, comparative-coverage, baseline-equivalence,
exploitability, public-role, score, decoder, concurrency, or packaging-adoption
claim. The split-debug experiment is a diagnostic packaging study and remains
separate from the reference runtime contract.
