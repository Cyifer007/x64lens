# ADR 0040: Sprint 10 Closeout and Diagnostic Benchmark Entry

## Status

Accepted for Sprint 10 Patch 054.

## Context

Sprint 10 expanded the semantic-exact analysis surface through ordered multi-pop,
register-transfer, positive aligned stack-adjust, and bounded qword memory
families. It also added structured provenance, memory effects, architectural
effects, cross-family fixtures, explicit false-positive boundaries, and
validated score policy.

Patch 053 established a twenty-two-sprint research sequence in which diagnostic
measurement begins before capability freeze. Patch 054 adds closeout and
roadmap-consistency gates without changing analyzer behavior.

## Decision

1. Sprint 10 closes with Patch 054 after the native closeout gate, qualified
   container validation, artifact authentication, and public-document checks
   pass.
2. Patch 054 adds no primitive, score, schema field, record, decoder, or worker
   behavior. The Patch 052 analyzer remains the runtime reference inherited by
   the Patch 053 and Patch 054 planning layers.
3. Sprint 11 is the active diagnostic benchmark foundation. Its corpus and rows
   are provisional development evidence that may redirect implementation.
4. Sprint 15 freezes the confirmatory corpus, schema/extractor pair, runner,
   baseline versions, commands, task definitions, and environment strata.
5. Sprints 16 and 17 own the frozen preview and publication-grade campaigns.
6. The dependency-free, decoder-free, one-worker binary remains the reference
   profile. Decoder and concurrency variants remain separately identified,
   optional experimental conditions.
7. Public roadmap prose is checked against the machine-readable stage authority.
   Active documents may not retain contradictory ownership from superseded
   schedules.
8. Public content checks reject private execution-handoff wording while allowing
   generic platform and reproducibility documentation.
9. A release checksum inventory may name only co-located artifacts. A package
   manifest referenced by the inventory must be present beside it and included
   in final cross-artifact verification.

## Consequences

- Sprint 11 can measure early enough to expose performance, coverage, and task-
  definition problems before the publication method is frozen.
- Diagnostic results may invalidate or narrow a hypothesis without being treated
  as a failed project outcome.
- Capability work remains evidence-gated rather than driven by feature-count
  parity with general-purpose offensive frameworks.
- Fixed record sizes, candidate capacity, output semantics, and the no-partial-
  output failure contract remain stable across the Sprint 10 closeout.
- The public repository describes project state and reproducible evidence rather
  than private execution or transfer workflow.
