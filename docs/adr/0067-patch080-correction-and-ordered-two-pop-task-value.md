# ADR 0067: Patch 080 Correction and Ordered Two-Pop Task-Value Decision

## Status

Proposed by Patch 081; acceptance remains subject to exact-source native,
Docker, parity, delivery, and independent validation.

## Context

Patch 080 added a private candidate-index role side-car and retained three
qualified single-pop role facets without changing public output or scores. Its
acceptance boundary remained incomplete because patch recovery, Git-less source
authentication, Docker provenance binding, already-state application checks,
loose helper identity, and evidence closure required correction.

An ordered two-pop role-tuple pilot was selected as the smallest next Sprint 13
experiment because the existing exact multi-pop family already retains ordered
registers through `stack_pop_order`, semantic-exact provenance, controlled-
register masks, stack delta, effects, and score 95. A new runtime tuple record
is justified only if it adds independently demonstrated task value.

## Decision

Patch 081:

1. corrects the complete Patch 080 acceptance finding set;
2. updates tracked public documentation to the Patch 081 chronology and
   preserved contract boundaries;
3. records `docs/sprints/sprint-12-retro.md`;
4. records all 30 ordered pairs over the six System V argument registers in a
   test-only manifest;
5. records 12 positive development tasks, 12 negative/permutation controls,
   and six confirmation-labeled tasks;
6. serializes the same authority three times and confirms byte-identical output;
7. toggles every one of the 25 exact-pattern score/null rows and compares each
   result with two distinct static fixtures; and
8. adds no runtime record, public field, semantic class, score, schema,
   capacity, dependency, or worker change.

## Ordered tuple result

The test-only manifest records all 30 ordered pairs and declares existing and
proposed correctness with zero incremental gains across 24 development and six
confirmation-labeled tasks. The smoke validates the pair structure, source-
contract literals, declared outcomes, and unchanged public boundary; it does
not execute an independent task consumer.

The decision is therefore:

```text
defer_new_runtime_tuple_representation
```

This is a policy deferral, not confirmatory measured task-value evidence. The
current multi-pop family and its existing `stack_pop_order` facts are preserved
unchanged.

## Score/null result

The release-facing exact-pattern partition remains:

```text
patterns:             25
scored:               14
null:                 11
private role facets:   3, all score-null
```

Each authority-row score is toggled once. Two distinct static-fixture
comparisons—the exact-pattern catalog and controlled-report score columns—
reject all 25 toggles, yielding 50 deterministic check failures. A separate
role-policy check retains the three private facets as null. Existing scores and
nulls are retained; this authority does not execute the runtime scorer.

## Preserved boundaries

- File-backed `PT_LOAD + PF_X` ranges remain executable authority.
- Raw, exact-suffix, semantic-exact, unknown, decoder-backed, and scored facts
  remain distinct.
- Candidate capacity remains 4,096.
- Candidate 4,097 returns exit code 6 before stdout.
- Malformed parser failures emit no partial stdout.
- Target files remain read-only and are never executed.
- The reference runtime remains dependency-free, decoder-free, one-worker,
  bounded, and deterministic.
- Public schema remains `0.2.0`.

## Consequences

Patch 081 removes one proposed runtime-state expansion from the near-term
roadmap. Later Sprint 13 work should select another bounded family or consumer
only when it demonstrates incremental task value and retains separate semantic,
public, and score decisions.

## Patch 082 superseding validation note

Patch 081 review found that this ADR's tuple and score/null policy conclusions
were not yet producer-backed. Patch 082 preserves the conclusions but replaces
the static acceptance path with three independently built analyzer generations.
ADR 0068 owns that correction and the controlled coordinate preflight.
