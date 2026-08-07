# Sprint 13 Patch 081 Validation

## Purpose

Patch 081 corrects the Patch 080 transaction, recovery, Git-less custody,
Docker-provenance, already-state, helper-identity, and evidence-seal findings.
It also records the Sprint 12 retrospective, runs a test-only ordered two-pop
role-tuple pilot, and freezes the complete score/null partition.

## Source boundary

Patch 081 is incremental from committed Patch 080. It changes no analyzer
assembly, include file, or JSON schema. Runtime semantic classes, public output,
scores, candidate order, and candidate capacity remain unchanged.

## Focused commands

```bash
make patch080-corrective-regression-smoke
make sprint13-ordered-two-pop-role-task-value-smoke
make sprint13-score-null-authority-smoke
make public-docs-check
make planning-docs-check
```

Expected banners:

```text
patch080-corrective-regression-smoke: ok ...
sprint13-ordered-two-pop-role-task-value-smoke: ok ... decision=defer ...
sprint13-score-null-authority-smoke: ok ... rejections=50 ...
```

## Complete local validation

```bash
make fix-perms
make normalize-perms
make clean
make
make samples
make test
make validation-smoke
make shellcheck-smoke
make docker-build
make docker-test
make docker-validation-smoke
make sprint12-external-natural-acquisition-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
make sprint13-p081-acceptance-smoke
```

## Ordered two-pop authority

The authority covers all 30 ordered distinct pairs among:

```text
rdi rsi rdx rcx r8 r9
```

It requires exact pattern 21, semantic class `arg_control`, stack delta 24,
score 95, two ordered registers, the exact control mask, and semantic-exact
evidence. Duplicate registers, `rsp`, and `r10` controls remain outside the
family.

The pilot's result is negative for a new runtime representation because existing
`stack_pop_order` facts already answer all frozen tasks. The exact multi-pop
family itself is not removed or downgraded.

## Score/null authority

The authority freezes 25 exact-pattern rows, 14 numeric scores, 11 null scores,
and three private role facets with null score. Each pattern cell is mutated and
must be rejected by two independent gates.

## Failure expectations

- Any foreign replacement deleted during recovery is a blocker.
- Git pathspec magic affecting an unrelated path is a blocker.
- An unrelated tracked or untracked change lost during recovery is a blocker.
- Git-less permission normalization must authenticate its manifest before
  executing source helpers.
- Already-state exit 3 requires the exact branch and no nonignored untracked
  state.
- Docker verification must bind candidate tree, context-authority digest, and
  source-manifest digest.
- Absolute paths in portable checksum authorities are rejected.
- Candidate 4,097 must return exit 6 before stdout.
- Malformed inputs must emit no partial stdout.

## Acceptance

Patch 081 is accepted only after complete native, Docker, parity, source,
delivery, capacity, malformed-input, documentation, and independent Lane A
validation agree on one exact candidate tree.
