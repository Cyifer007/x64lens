# Sprint 13 Patch 081 Validation

## Status

Implementation candidate pending complete exact-source native, Docker, parity,
delivery, documentation, and independent validation.

## Purpose

Patch 081 corrects the Patch 080 transaction, recovery, Git-less custody,
Docker-provenance, already-state, helper-identity, and evidence-seal findings.
It also records the Sprint 12 retrospective, adds a test-only ordered two-pop
role-tuple manifest, and retains the complete score/null partition through
static-fixture comparisons.

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

The test-only manifest declares existing and proposed correctness with zero
incremental gains across 24 development and six confirmation-labeled tasks.
The smoke validates the 30-pair structure, source-contract literals, declared
outcomes, and unchanged public boundary; it does not execute an independent
task consumer. The resulting policy decision defers a new runtime
representation. The exact multi-pop family itself is not removed or downgraded.

## Score/null authority

The authority retains 25 exact-pattern rows, 14 numeric scores, 11 null scores,
and three private role facets with null score. Each authority-row score is
toggled and compared with two distinct static fixtures: the exact-pattern
catalog and controlled-report score columns. The 25 toggles yield 50
deterministic check failures. A separate role-policy check retains the three
private facets as null; this authority does not execute the runtime scorer.

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
delivery, capacity, malformed-input, documentation, and independent exact-source
validation agree on one candidate tree.

## Review outcome and Patch 082 handoff

Patch 081 was not accepted as the final exact-source candidate. Follow-up
validation confirmed no analyzer-runtime defect, but required correction for
ordinary extraction modes, loose helper identity, Git-less manifest/root
pairing, Docker source/build separation, nested Make authority isolation, and
producer-blind tuple/score gates. Patch 082 owns those corrections. Historical
P081 static-fixture outcomes remain policy evidence and are not represented as
independent producer execution.
