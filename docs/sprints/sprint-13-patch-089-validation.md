# Sprint 13 Patch 089 Validation

## Status

Implementation candidate pending exact-source fresh NASM/native, Docker,
producer, replay, both parity planes, ABI, split-debug, workload, delivery, and
independent acceptance gates.

## Scope

Patch 089 implements candidate corrections for the Patch 088 replay-identity, Python-distribution closure, split-debug result custody, producer/source binding, behavior and symbol denominators, signal cleanup, workload fixture identity, source-recovery capacity, and malformed-authority findings.

No tracked file under `src/`, `include/`, or `schemas/` changes. Tool version `0.1.0-dev`, schema `0.2.0`, public output, semantic classes, scores, candidate capacity, deterministic ordering, and the decoder-free one-worker reference profile remain unchanged.

## Source preconditions

| Role | Commit | Tree |
|---|---|---|
| Patch 089 base | `cf149850b04aeb72fbd32c049128c71bf4b60bde` | `5abf83e13f5b182d624b998ce888ec330e6789b9` |
| Reviewed Patch 089 input candidate | `c451dc9fccc69ea607cf112ab4b10f94dba17d2a` | `45959a8ce6cc48515553eff6f8e999487f41d4d0` |

The guarded application path requires branch `main`, the exact base HEAD and
tree, a clean index and worktree, and the authenticated patch digest.
Candidate-source recovery is a mutually exclusive application path. Any
Markdown correction produces a new proposed tree, whose identity must be
recorded by the final source-identity authority before exact-source acceptance.

## Focused validation

```bash
make patch088-corrective-regression-smoke
make sprint13-natural-frozen-replay-v2-smoke
make sprint13-natural-terminal-attribution-v2-smoke
make sprint13-split-debug-packaging-contract-smoke
make sprint13-workload-phase-attribution-smoke
make sprint12-closeout-smoke
make sprint12-continuation-smoke
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
```

Expected focused banners include:

```text
patch088-corrective-regression-smoke: ok ...
sprint13-natural-frozen-replay-v2-smoke: ok ... record_python_closures=5 run=deferred
sprint13-natural-terminal-attribution-v2-smoke: ok ... expected_required=1 run=deferred
sprint13-split-debug-packaging-smoke: ok mode=selftest ... producer_generations=3 ... mutation_rejections=10 signal_cleanup=1
sprint13-workload-phase-attribution-smoke: ok ... fixtures=8 ... mutation_rejections=17 execution=deferred
```

## Native validation

```bash
make ownership-check
make clean
make
make samples
make test
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p089-tree> make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

Permission repair helpers are not validation gates. Use them only after a diagnosed ownership or mode problem and rerun `make ownership-check` afterward.

## Replay execution

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p089-tree> \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p089-results/frozen-replay \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p089-results/terminal-attribution.json \
  make sprint13-natural-frozen-replay-v2
```

Replay validates predecessor raw-tool identities separately from the current analyzer projection. Every retained Python distribution closure must match the exact hash-bearing authority; a merely well-formed replacement closure is not accepted.

## Split-debug execution

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p089-tree> \
S13_PRODUCER_RESULT_DIR=./.local/p089-results/producer \
S13_SPLIT_DEBUG_PRODUCER_DIR=./.local/p089-results/producer \
S13_SPLIT_DEBUG_RESULT_DIR=./.local/p089-results/split-debug \
  make sprint13-split-debug-packaging-smoke
```

The result must authenticate two independent producer generations, sixty distinct behavior executions, thirty pairs, eight companion controls, twelve unique symbol resolutions, exact retained membership, canonical modes, unique inode topology, no-replace publication, and signal-safe cleanup.

A passing experiment remains opt-in diagnostic evidence. In the retained Patch
088 result, the runtime tier shrank 66.09%, but runtime plus companion produced
no total-transfer saving, and post-link path redaction did not establish
path-stable DWARF. Product adoption remains false.

## Workload/phase execution

The authority freezes eight distinct fixtures, two profiles, sixteen cells, sixteen warmups, 144 measured executions, and 160 total executions. Qualification requires at least six fixtures, a five-floor minimum, bounded dispersion, residual, overhead, private-storage, and complete-output criteria.

```bash
# Run only after the repository's instrumentation producer and exact candidate
# binaries are available under the retained authority.
make sprint13-workload-phase-attribution-smoke
```

Cloud evidence validates only the frozen authority and its rejection oracles.
The workload/phase experiment remains unexecuted. A measured phase result
requires the separate qualified run path and does not follow from selftest
success.

## Docker, ABI, and parity validation

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p089-tree> make docker-build
make docker-test
make docker-validation-smoke

S13_EXPECTED_CANDIDATE_TREE=<authenticated-p089-tree> \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p089-results/abi-vector \
  make sprint13-abi-role-vector-equivalence-smoke

make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
```

## Candidate aggregate

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-p089-tree> \
S13_PRODUCER_RESULT_DIR=./.local/p089-results/producer-acceptance \
S13_SPLIT_DEBUG_PRODUCER_DIR=./.local/p089-results/producer-acceptance \
S13_SPLIT_DEBUG_RESULT_DIR=./.local/p089-results/split-debug-acceptance \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p089-results/abi-vector-acceptance \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p089-results/frozen-replay-acceptance \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p089-results/terminal-attribution-acceptance.json \
  make sprint13-p089-acceptance-smoke
```

Expected future banner:

```text
sprint13-p089-acceptance-smoke: ok patch=89 sprint12=closed sprint13=active replay-predecessor-identity=separate python-closures=exact workload-fixtures=unique split-debug=opt-in-diagnostic path-stable=0 total-transfer-reduction=0 product-adoption=0 public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

The banner is an expectation until the exact-source local run completes.

## Claim boundary

Patch 089 adds no performance, RSS, comparative-coverage, baseline-equivalence, exploitability, public-role, score, decoder, concurrency, or production-packaging claim. Split-debug and workload/phase remain diagnostic experimental authorities.

The retained Patch 088 diagnostic campaign completed 30/30 conditions and
180/180 process rows, but all 60 x64lens timings were below the 5,894,690 ns
floor and 0/9 coordinate cells had a positive anchor. It authorizes no
performance, RSS, parity, coverage, superiority, or publication claim.
