# Research Contract

## Research discipline

The project must preserve a clean evidence trail from implementation to benchmark to paper.

## Required evidence for claims

Any claim about performance, memory use, coverage, or analyst usefulness must include:

- tool version,
- schema version if output is involved,
- baseline tool version,
- corpus manifest,
- exact command,
- run count,
- environment metadata,
- raw results,
- summary statistics.

## Publication posture

The project should be written so that a reader can reproduce results without private binaries, private emails, or hidden assumptions.

## Faculty review vs peer review

Faculty review is valuable technical feedback and course evaluation. External peer review occurs through a conference, workshop, journal, or formal program committee.

## Threats to validity

Every paper draft must include limitations and threats to validity.

## Ethics

The research must avoid unauthorized targets, payload generation, and exploit delivery automation in the semester scope.

## Reviewer-preview rule

When a design critique identifies a likely peer-review objection, convert the objection into one of:

- an explicit limitation,
- a validation task,
- a benchmark metric,
- a roadmap item,
- an ADR,
- a paper threats-to-validity note.

Do not respond by broadening scope unless the current research question requires it.

## Campaign freeze rule

Publication-grade experiments require a frozen corpus, tool versions, commands, schema, benchmark runner, and environment stratum. A method change after freeze creates a new campaign identifier or requires a complete rerun of affected conditions.

## Provenance rule

Candidate coverage claims must identify the evidence layer being measured: raw, exact suffix, semantic exact, decoder validated, semantic decoded, unknown, or scored. A generic gadget count is insufficient for cross-tool claims.

## Release evidence rule

Research preview and final release claims must satisfy the gates in `docs/research-release-plan.md`. Smoke results demonstrate plumbing and regression stability, not universal performance or coverage.

## Sprint 9 report-completeness evidence rule

Research artifacts that consume schema `0.2.0` must preserve report type,
command identity, maximum depth, candidate capacity/count, truncation,
dropped-count knowledge, and executable-region progress. `analysis.complete`
means bounded enumeration completed over the loader-derived executable regions.
It is not decoder-validity or complete gadget-coverage evidence.

Failed capacity runs must remain failed rows or validation outcomes; they must
not be reclassified as emitted truncated reports.
