# Sprint 13 Patch 087 Validation

## Status

Historical implementation candidate. Patch 087 did not complete exact-source
acceptance and was superseded by Patch 088.

## Scope

Patch 087 implemented candidate corrections for Patch 086 transaction topology,
wrapper signal handling,
source-recovery and custody publication, replay runtime authority, terminal
attribution, ABI publication/source binding, documentation, and loose-delivery
findings. It also froze a paired workload and phase-attribution authority.

No tracked file under `src/`, `include/`, or `schemas/` changes. The runtime,
public schema, semantic classes, and scores remain unchanged. Tool version
`0.1.0-dev`, schema `0.2.0`, public output, candidate capacity, deterministic
ordering, and the decoder-free one-worker reference profile remain unchanged.

## Source preconditions

```text
branch: main
base HEAD: c6d1465e674aa04e61e06c80ec0dc3d719dfeba8
base tree: 9e8d5a3fb0c27e6596d3e1d4475ae2a34ef6466d
candidate HEAD: e5b3d6d6bd27acd3f4e41c3a2acbb231a6b9fc2b
tracked state: clean
candidate tree: 47a4ee9868914abc1736ed1ccc76515c0d46f676
```

This record identifies the reviewed Patch 087 implementation candidate exactly.
Acceptance callers must export that immutable tree through
`S13_EXPECTED_CANDIDATE_TREE`; a mutable index is not source authority.

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

These contract-only banners define private diagnostic authorities; they do not
record replay, terminal-attribution, ABI-vector, or workload/phase execution.

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

S13_EXPECTED_CANDIDATE_TREE=47a4ee9868914abc1736ed1ccc76515c0d46f676 \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p087-results/abi-vector \
  make sprint13-abi-role-vector-equivalence-smoke

S13_EXPECTED_CANDIDATE_TREE=47a4ee9868914abc1736ed1ccc76515c0d46f676 \
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
S13_EXPECTED_CANDIDATE_TREE=47a4ee9868914abc1736ed1ccc76515c0d46f676 make docker-build
make docker-run-root-smoke
make docker-source-custody-smoke
make docker-test
make docker-validation-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
```

## Historical candidate aggregate

```bash
S13_EXPECTED_CANDIDATE_TREE=47a4ee9868914abc1736ed1ccc76515c0d46f676 \
S13_ABI_ROLE_VECTOR_RESULT_DIR=./.local/p087-results/abi-vector-acceptance \
S13_PRODUCER_RESULT_DIR=./.local/p087-results/producer-acceptance \
S13_NATURAL_REPLAY_INPUT_DIR=./.local/p083-results/natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p087-results/frozen-replay-acceptance \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p087-results/terminal-attribution-acceptance.json \
  make sprint13-p087-acceptance-smoke
```

The historical aggregate defined this expected banner; it is not evidence of
completion or acceptance:

```text
sprint13-p087-acceptance-smoke: ok patch=87 sprint12=closed sprint13=active frozen-replay=sealed terminal-attribution=expected abi-vector-equivalence=private workload-phase-authority=frozen public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

## Workload and phase authority

The Patch 087 authority froze eight fixtures, reference and instrumented
profiles, one warmup and nine measured runs per profile/fixture, and 160 total
executions. Qualification requires:

```text
median >= 5 × retained timer floor
MAD / median <= 0.10
phase-sum residual <= 0.05
instrumented / reference median <= 1.03
qualified fixtures >= 6 of 8
private instrumentation <= 65,536 bytes
normalized public output equality
zero failures and regressions
```

The contract-only smoke validates the frozen method and mutation oracles. Full
execution remains a separate private diagnostic run. Qualification may motivate
a later bounded experiment, but cannot itself select an optimization or
authorize a performance claim.

## Failure expectations

- Changed-path hard-link topology is rejected before base/candidate classification.
- HUP, INT, or TERM during owned publication enters cleanup without owned residue.
- Package apply and rollback wrappers have no command after the transaction helper.
- Replay runtime, package closures, source, target, tool, raw-stream, and terminal expectations are exact.
- Candidate capacity remains 4,096; candidate 4,097 returns exit code 6 before stdout.
- Malformed parser failures still emit no partial stdout.

## Claim boundary

Replay, terminal-attribution, ABI-vector, and workload/phase evidence remains
private, diagnostic, and publication-ineligible. The workload/phase method is
frozen but unexecuted and selects no optimization. Patch 087 does not claim
comparative speed, RSS, comparative coverage, baseline equivalence, public role
evidence, score improvement, exploitability, decoder need, or concurrency
benefit. Patch 087 did not complete independent exact-source acceptance; Patch
088 carries the current acceptance boundary.
