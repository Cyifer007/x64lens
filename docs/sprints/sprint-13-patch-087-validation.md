# Sprint 13 Patch 087 Validation

## Status

Implementation candidate pending exact-source native, Docker, replay, producer,
parity, ABI, delivery, and independent acceptance gates.

## Scope

Patch 087 corrects Patch 086 transaction topology, wrapper signal handling,
source-recovery and custody publication, replay runtime authority, terminal
attribution, ABI publication/source binding, documentation, and loose-delivery
findings. It also freezes a paired workload and phase-attribution authority.

No tracked file under `src/`, `include/`, or `schemas/` changes. Tool version
`0.1.0-dev`, schema `0.2.0`, public output, semantic classes, scores, candidate
capacity, deterministic ordering, and the decoder-free one-worker reference
profile remain unchanged.

## Source preconditions

```text
branch: main
base HEAD: c6d1465e674aa04e61e06c80ec0dc3d719dfeba8
base tree: 9e8d5a3fb0c27e6596d3e1d4475ae2a34ef6466d
tracked state: clean
candidate tree: supplied by the authenticated Patch 087 package and runbook
```

The candidate tree is supplied externally through
`S13_EXPECTED_CANDIDATE_TREE`; the Makefile does not attempt to derive its own
authority from a mutable index.

## Focused validation

```bash
make patch086-corrective-regression-smoke
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

Expected banners include:

```text
patch086-corrective-regression-smoke: ok ...
sprint13-natural-frozen-replay-v2-smoke: ok targets=12 ... raw_streams=96 pinned_python_closures=5 run=deferred
sprint13-natural-terminal-attribution-v2-smoke: ok ... expected_required=1 run=deferred
sprint13-abi-role-vector-equivalence-smoke: ok ... candidate_source_bound=1 no_replace=1 run=deferred
sprint13-workload-phase-attribution-smoke: ok fixtures=8 profiles=2 ... executions=160 ... execution=deferred
```

## Native validation

```bash
make fix-perms
make normalize-perms
make clean
make
make samples
make test
make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

## Replay and ABI validation

```bash
mkdir -p .local/p087-results

S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p087-results/abi-vector \
  make sprint13-abi-role-vector-equivalence-smoke

S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p087-results/frozen-replay \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p087-results/terminal-attribution.json \
  make sprint13-natural-frozen-replay-v2
```

Replay requires the exact twelve predecessor target hashes, four tools, forty-
eight execution records, ninety-six raw streams, five pinned Python package
closures, isolated runtime state, and the mandatory expected terminal result.
Target rerolling is prohibited.

## Docker and parity validation

```bash
S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> make docker-build
make docker-run-root-smoke
make docker-source-custody-smoke
make docker-test
make docker-validation-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
```

## Candidate aggregate

```bash
S13_EXPECTED_CANDIDATE_TREE=<candidate-tree> \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p087-results/abi-vector-acceptance \
S13_PRODUCER_RESULT_DIR=./.local/p087-results/producer-acceptance \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p087-results/frozen-replay-acceptance \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p087-results/terminal-attribution-acceptance.json \
  make sprint13-p087-acceptance-smoke
```

Expected banner:

```text
sprint13-p087-acceptance-smoke: ok patch=87 sprint12=closed sprint13=active frozen-replay=sealed terminal-attribution=expected abi-vector-equivalence=private workload-phase-authority=frozen public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

## Workload and phase authority

The Patch 087 authority freezes eight fixtures, reference and instrumented
profiles, one warmup and nine measured runs per profile/fixture, and 160 total
executions. Qualification requires:

```text
median >= 5 × 6,231,575 ns
MAD / median <= 0.10
phase-sum residual <= 0.05
instrumented / reference median <= 1.03
qualified fixtures >= 6 of 8
private instrumentation <= 65,536 bytes
normalized public output equality
zero failures and regressions
```

The cloud selftest validates the authority and mutation oracles only. Full
execution remains a separate diagnostic run and cannot authorize a performance
claim.

## Failure expectations

- Changed-path hard-link topology is rejected before base/candidate classification.
- HUP, INT, or TERM during owned publication enters cleanup without owned residue.
- Package apply and rollback wrappers have no command after the transaction helper.
- Replay runtime, package closures, source, target, tool, raw-stream, and terminal expectations are exact.
- Candidate 4,097 still returns exit code 6 before stdout.
- Malformed parser failures still emit no partial stdout.

## Claim boundary

Patch 087 does not claim an executed phase result, comparative speed, RSS
superiority, coverage equivalence, public role evidence, score improvement,
decoder need, concurrency benefit, or exploitability. Independent Lane A
acceptance remains mandatory.
