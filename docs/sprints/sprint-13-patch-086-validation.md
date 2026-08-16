# Sprint 13 Patch 086 Validation

## Status

Historical implementation candidate. Patch 086 did not complete exact-source
acceptance; Patch 087 carries its bounded transaction, replay, publication,
source-binding, delivery, and workload/phase-authority corrections.

## Scope

Patch 086 corrects the Patch 085 replay/attribution, transaction, source-recovery, custody-publication, ABI-expected, exact-tree, documentation, and delivery findings. It also adds a private production-vector equivalence gate over the existing candidate-role side-car.

No tracked file under `src/`, `include/`, or `schemas/` changes. Tool version `0.1.0-dev`, schema `0.2.0`, public output, semantic classes, scores, candidate capacity, deterministic ordering, and the decoder-free one-worker reference profile remain unchanged.

## Source preconditions

```text
branch: main
base HEAD: 98019d308020d48767f57333929a7b3313a90f74
base tree: b2d2549a4ec311d97e79925035f80d7535867ac0
tracked state: clean
candidate tree: 9e8d5a3fb0c27e6596d3e1d4475ae2a34ef6466d
```

The exact Patch 086 candidate tree is
`9e8d5a3fb0c27e6596d3e1d4475ae2a34ef6466d`. Validation exports that value
rather than deriving authority from a mutable index.

## Focused validation

```bash
make patch085-corrective-regression-smoke
make sprint13-natural-frozen-replay-v2-smoke
make sprint13-natural-terminal-attribution-v2-smoke
make sprint13-abi-role-vector-equivalence-contract-smoke
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
```

Expected banners include:

```text
patch085-corrective-regression-smoke: ok ...
sprint13-natural-frozen-replay-v2-smoke: ok targets=12 ... executions=48 raw_streams=96 ... run=deferred
sprint13-natural-terminal-attribution-v2-smoke: ok ... expected_required=1 run=deferred
sprint13-abi-role-vector-equivalence-smoke: ok internal_dispositions=48 targets=24 max_indices=98304 queries=36 public_closures=96 run=deferred
```

These are contract-only banners. The `vectors=N/N` banner is emitted only by
the full ABI-vector run below.

## Native and ABI validation

```bash
make fix-perms
make normalize-perms
make clean
make
make samples
make test
make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke

mkdir -p .local/p086-results
S13_EXPECTED_CANDIDATE_TREE=9e8d5a3fb0c27e6596d3e1d4475ae2a34ef6466d \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p086-results/abi-vector \
  make sprint13-abi-role-vector-equivalence-smoke
```

The ABI vector gate requires:

```text
48/48 internal dispositions
24 controlled targets
N/N occupied candidate-index vector matches, N <= 98,304
36/36 named ABI queries
96/96 unchanged-public command closures
```

## Replay-v2 execution contract

```bash
S13_EXPECTED_CANDIDATE_TREE=9e8d5a3fb0c27e6596d3e1d4475ae2a34ef6466d \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p086-results/frozen-replay \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p086-results/terminal-attribution.json \
  make sprint13-natural-frozen-replay-v2
```

The replay requires the exact twelve predecessor hashes and four execution tools for 48 executions. The result must seal 96 raw streams, target copies, runtime authority, isolated cache policy, selection freeze, manifest, and complete checksum membership. Terminal attribution must equal the mandatory P086 expected result. No target reroll is permitted.
This record defines the replay-v2 contract; it does not claim that a local replay
or terminal-attribution result has completed.

## Docker and parity validation

```bash
S13_EXPECTED_CANDIDATE_TREE=9e8d5a3fb0c27e6596d3e1d4475ae2a34ef6466d make docker-build
make docker-run-root-smoke
make docker-source-custody-smoke
make docker-test
make docker-validation-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
```

## Candidate aggregate

```bash
S13_EXPECTED_CANDIDATE_TREE=9e8d5a3fb0c27e6596d3e1d4475ae2a34ef6466d \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p086-results/abi-vector-acceptance \
S13_PRODUCER_RESULT_DIR=./.local/p086-results/producer-acceptance \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p086-results/frozen-replay-acceptance \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p086-results/terminal-attribution-acceptance.json \
  make sprint13-p086-acceptance-smoke
```

Expected banner:

```text
sprint13-p086-acceptance-smoke: ok patch=86 sprint12=closed sprint13=active frozen-replay=sealed terminal-attribution=expected abi-vector-equivalence=private public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

This was the Patch 086 candidate aggregate, not an acceptance result. Patch 086
did not complete independent exact-source acceptance.

## Failure expectations

- A replay result with a missing or unsealed raw member is rejected.
- A replay denominator or expected terminal distribution mutation is rejected.
- Tool, target, source, runtime, or cache authority drift fails closed.
- A patch-path hard-link alias is preserved while the authenticated base is restored.
- HUP, INT, or TERM during mutation enters the recovery path and leaves no owned residue.
- Candidate 4,097 still returns exit code 6 before stdout.
- Malformed parser failures still emit no partial stdout.

## Claim boundary

The recorded private ABI-vector equivalence remains diagnostic and
publication-ineligible. No completed local replay-v2 result is claimed here.
The replay selection is exact and no-reroll, while any replay evidence remains
private, diagnostic, `frozen=false`, and publication-ineligible.
Vector equivalence is not decoded validity, natural role incidence, task value,
public role policy, exploitability, comparative coverage, performance, RSS, or
concurrency evidence.
