# ADR 0067: Patch 080 Correction and Ordered Two-Pop Task-Value Decision

## Status

Proposed by Patch 081; acceptance remains subject to exact-source native,
Docker, parity, delivery, and independent Lane A validation.

## Context

Patch 080 added a private candidate-index role side-car and retained three
qualified single-pop role facets without changing public output or scores. Its
review confirmed the runtime role model but found defects in patch recovery,
Git-less source authentication, Docker provenance binding, already-state
application checks, loose helper identity, and evidence closure.

The strategic review selected an ordered two-pop role-tuple pilot as the
smallest next Sprint 13 experiment. The existing exact multi-pop family already
retains ordered registers through `stack_pop_order`, semantic-exact provenance,
controlled-register masks, stack delta, effects, and score 95. A new runtime
tuple record is justified only if it adds independent task value.

## Decision

Patch 081:

1. corrects the complete Patch 080 acceptance finding set;
2. applies the accepted public-Markdown final-file corrections;
3. records `docs/sprints/sprint-12-retro.md`;
4. freezes all 30 ordered pairs over the six System V argument registers;
5. evaluates 12 positive development tasks, 12 negative/permutation controls,
   and six untouched confirmation tasks;
6. runs three byte-identical authority generations;
7. mutates every one of the 25 exact-pattern score/null cells through two
   independent gates; and
8. adds no runtime record, public field, semantic class, score, schema,
   capacity, dependency, or worker change.

## Ordered tuple result

The structural authority passes all 30 ordered pairs and all out-of-family
controls. Existing exact facts answer every frozen task. The proposed convenience
representation produces zero incremental development or confirmation gains.

The decision is therefore:

```text
defer_new_runtime_tuple_representation
```

This is a successful negative result. Existing `stack_pop_order` and related
facts remain sufficient for the represented task. The current multi-pop family
is preserved unchanged.

## Score/null result

The release-facing exact-pattern partition remains:

```text
patterns:             25
scored:               14
null:                 11
private role facets:   3, all score-null
```

Every pattern cell is mutated once. Both the catalog-policy gate and controlled
report/effect gate reject all 25 mutations, for 50 independent rejections.
Existing scores and nulls are retained.

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
