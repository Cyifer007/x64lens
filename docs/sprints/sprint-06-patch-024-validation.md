# Sprint 06 Patch 024 Validation Plan

## Purpose

Patch 024 performs the post-checkpoint planning and architecture review required before hostile-input and mitigation hardening begins. It changes planning, documentation, repository checks, and CI contract validation. It does not change scanner, classifier, scoring, mitigation, or JSON runtime behavior.

## Scope under validation

- canonical eighteen-sprint roadmap,
- Sprint 7 through Sprint 12 reassessment,
- Sprint 13 through Sprint 18 plans,
- research preview and first-release evidence gates,
- parser-safety and mitigation-hardening sequence,
- evidence provenance and decoder decision seams,
- primitive-expansion constraints,
- schema `0.2.0` transition criteria,
- higher-resolution benchmark methodology,
- corpus, release, replication, and publication milestones,
- automated structural planning-document validation.

## Required local checks

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make clean
make
make samples
make test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
make analyze-smoke
make system-smoke
make validation-smoke
```

Docker remains a separate reproducibility check:

```bash
make docker-available-check
make docker-test
```

Patch bundle hygiene:

```bash
BUNDLE=/path/to/024_x64lens_sprint6_roadmap_architecture_review_patch.zip \
  make patch-bundle-hygiene
```

## Structural assertions

`make planning-docs-check` must verify:

- the canonical roadmap and release plan exist,
- Sprint 7 through Sprint 18 plans exist,
- each future sprint plan has explicit status and goal sections,
- the twelve-sprint compatibility document is marked superseded,
- evidence provenance and schema evolution plans exist,
- README points to the canonical roadmap,
- research preview and first-release gates are documented.

## Contract assertions

- Public documentation is written as repository documentation for technical readers.
- No private planning dialogue, local archive history, user-specific paths, or conversational wording is present.
- Program headers remain authoritative for runtime mapping.
- Raw, exact, semantic, validated, unknown, and scored facts remain distinct.
- An exact suffix observation is not represented as decoder proof.
- Scores remain heuristic and are not exploitability verdicts.
- Benchmark smoke evidence is not represented as publication evidence.
- Schema changes occur only through an explicit documented gate.
- Release milestones require evidence, not calendar completion alone.

## Expected behavior preservation

Because Patch 024 is planning-focused, the controlled fixture should retain the validated Sprint 6 values:

| Field | Expected |
|---|---:|
| raw candidate count | 11 |
| exact pattern count | 11 |
| semantic candidate count | 11 |
| unknown candidate count | 0 |
| scored candidate count | 11 |

`analyze` text output must retain one version banner and one target banner. Fixture JSON must remain valid under schema `0.1.0`.

## Acceptance decision

Patch 024 is accepted when the structural, documentation, native, fixture, JSON, analyze, system-binary, and bundle-hygiene checks pass without runtime-regression evidence.

After acceptance, Sprint 7 begins with deterministic hostile-input mutation testing, regression-corpus preservation, and shared bounded parser helpers. Mitigation expansion follows after that safety baseline is established.
