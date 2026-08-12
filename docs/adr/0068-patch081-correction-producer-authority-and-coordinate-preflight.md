# ADR 0068: Patch 081 Correction, Producer Authority, and Coordinate Preflight

## Status

Implemented by Patch 082. The full retained three-build run and complete
exact-source native, Docker, parity, delivery, and independent validation remain
pending.

## Context

Patch 081 preserved analyzer behavior while recording the Sprint 12
retrospective and two policy authorities. Patch 081 was not accepted; its
validation findings were accepted as correction inputs to Patch 082. Those
findings reported no analyzer-runtime defect. Ordinary ZIP extraction did not
preserve the modes required by package custody, Docker validation placed build
outputs inside the authenticated source root, nested Make invocations could
overwrite caller-selected authority files, three loose helper names collided
with historical bytes, and the tuple and score/null gates did not consume
independently built analyzer output.

The ordered-two-pop deferral and current score/null partition remain policy
decisions, contingent on producer-backed validation. Patch 082 also implements
a bounded controlled coordinate method-discrimination gate. A named role
consumer and deployment-envelope work require further contract freeze.

## Decision

Patch 082:

1. requires Git-less source manifests and authority roots to be supplied as an
   authenticated pair;
2. preserves `/work` as the pristine Docker source plane and performs mutable
   builds under a separate ephemeral run root;
3. strips recursive Make authority propagation from isolated regressions;
4. uses portable `0755` directory and `0644`/`0755` file modes consistently in
   package and custody authorities;
5. uses Patch-scoped loose helper names rather than generic historical names;
6. implements a gate that, when run locally, builds three independent analyzers
   from one authenticated source tree and makes the ordered-pair and score/null
   gates consume their retained reports;
7. retains the ordered tuple decision as `defer` and all score values/nulls
   unchanged; and
8. adds a controlled source-valid coordinate preflight with six deterministic
   ELF targets, eight positive oracle cases, four mutation rejections, four
   semantic negatives, and two modeled controlled-target observations in each
   of nine tool-label-by-role cells (18 cell observations total).

The coordinate preflight discriminates the controlled method only. It does not
execute the named external tools, claim that a natural external-tool run emits
the modeled coordinate, or authorize comparative coverage interpretation.

## Preserved boundaries

- Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable
  authority.
- Scanner, exact matcher, classifier, side-cars, scoring, and reporting remain
  separate.
- Raw, exact-suffix, semantic-exact, unknown, future decoder-backed, and scored
  facts remain distinct.
- Candidate capacity remains 4,096; candidate 4,097 fails with exit code 6
  before stdout.
- Malformed parser paths emit no partial report.
- No runtime record, public field, semantic class, score, schema, dependency,
  or worker default changes.
- The reference runtime remains dependency-free, decoder-free, one-worker,
  bounded, deterministic, read-only with respect to targets, and never executes
  a target.

## Consequences

When fully executed and retained, the producer-backed gates can detect a real
scorer or ordered-pop regression that static fixtures alone would miss. Docker
validation can mutate build outputs without invalidating its own source
authority. Package custody works after the documented ordinary extraction path.
The controlled coordinate preflight supplies controlled positive and negative
oracle discrimination, while natural baseline qualification remains an
explicit later diagnostic gate.
