# Sprint 13 Patch 085 Validation

## Status

Implementation candidate pending exact-source native, Docker, producer, frozen-
replay, ABI-closure, parity, delivery, and independent acceptance gates.

## Scope

Patch 085 corrects the Patch 084 source-custody, recovery, lifecycle, ABI,
natural-campaign, fixed-tree, and delivery findings. It adds an exact 12-target
frozen replay authority and layered terminal attribution while preserving the
analyzer runtime, schema `0.2.0`, public fields, semantic classes, scores,
candidate capacity, and one-worker reference profile.

## Source preconditions

```text
branch: main
base HEAD: ed33f1991ae0d35aa6a295011f1f590a0222f7e5
base tree: 178f1d1c93a5a05fba5a77af2c378e63e5dc017b
tracked state: clean
```

The exact Patch 085 candidate tree is supplied by the authenticated application
package and exported as `S13_EXPECTED_CANDIDATE_TREE`. Validation targets do not
derive that authority from `git write-tree`.

## Focused validation

```bash
make patch084-corrective-regression-smoke
make sprint13-lifecycle-denominator-smoke
make sprint13-abi-role-query-contract-smoke
make sprint13-natural-coordinate-campaign-smoke
make sprint13-natural-frozen-replay-smoke
make sprint13-natural-terminal-attribution-smoke
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
```

Expected focused banners include:

```text
patch084-corrective-regression-smoke: ok ...
sprint13-lifecycle-denominator-smoke: ok ... successor_deltas=5 floors=24 mutations=13 ...
sprint13-natural-frozen-replay-smoke: ok targets=12 ... executions=48 reroll=0 ...
sprint13-natural-terminal-attribution-smoke: ok ... execution_outcomes=48 ... cells=9 ...
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

## ABI closure

```bash
mkdir -p .local/p085-results
S13_EXPECTED_CANDIDATE_TREE=<authenticated-P085-tree> \
S13_ABI_ROLE_RESULT_DIR=./.local/p085-results/abi-role \
  make sprint13-abi-role-query-smoke
```

The closure requires 36 semantically disjoint queries and 96 unchanged-public
command outcomes. Analyzer and target identities are authenticated before and
after execution.

## Exact frozen natural replay

Extract the predecessor natural-campaign evidence supplied by the Patch 085
package, then run:

```bash
mkdir -p .local/p085-results
S13_EXPECTED_CANDIDATE_TREE=<authenticated-P085-tree> \
S13_NATURAL_REPLAY_INPUT_DIR=/path/to/p084-natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p085-results/frozen-replay \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p085-results/terminal-attribution.json \
  make sprint13-natural-frozen-replay
```

The replay requires the exact twelve predecessor hashes, four tools per target,
48 executions, nine cells, 108 controls, and no target reroll. Terminal
attribution retains one reason per execution, relation, observation, and cell
layer.

## Docker and parity validation

```bash
S13_EXPECTED_CANDIDATE_TREE=<authenticated-P085-tree> make docker-build
make docker-run-root-smoke
make docker-source-custody-smoke
make docker-test
make docker-validation-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
```

The Docker source plane remains recursively authenticated and unwritable. All
mutable build and validation output remains outside that source plane.

## Complete acceptance candidate

```bash
mkdir -p .local/p085-results
S13_EXPECTED_CANDIDATE_TREE=<authenticated-P085-tree> \
S13_ABI_ROLE_RESULT_DIR=./.local/p085-results/abi-role-acceptance \
S13_PRODUCER_RESULT_DIR=./.local/p085-results/producer-acceptance \
S13_NATURAL_REPLAY_INPUT_DIR=/path/to/p084-natural-structural \
S13_NATURAL_REPLAY_RESULT_DIR=./.local/p085-results/frozen-replay-acceptance \
S13_NATURAL_ATTRIBUTION_RESULT=./.local/p085-results/terminal-attribution-acceptance.json \
  make sprint13-p085-acceptance-smoke
```

Expected final banner:

```text
sprint13-p085-acceptance-smoke: ok patch=85 sprint12=closed sprint13=active frozen-replay=complete terminal-attribution=layered lifecycle-deltas=5 abi-role-queries=36 public-closures=96 public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

## Failure expectations

- A missing or caller-derived candidate-tree authority is rejected.
- Development and confirmation ABI queries cannot overlap semantically.
- ABI evidence cannot replace a raced result directory.
- Target or analyzer mutation during ABI or natural execution fails closed.
- Git-less mode, hard-link, or ctime drift fails verification.
- Recovery leaves no owned residue after an injected first-open failure.
- Structural natural-campaign counts are recomputed from exact target, tool,
  observation, control, and cell membership.
- Candidate 4,097 still returns exit code 6 before stdout; malformed parser
  failures still emit no partial report.

## Evidence classification

Cloud-supported corrective and static gates do not substitute for a fresh NASM
build, strict ShellCheck, Docker execution, producer runs, actual parity, or the
complete frozen replay. All coordinate and terminal-attribution results remain
diagnostic and publication-ineligible.
