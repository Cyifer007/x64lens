# Versioning Plan

## Independent versions

x64lens maintains two independent version lines:

```text
tool version:   0.1.0-dev
schema version: 0.2.0
```

Tool behavior can change while preserving the schema. Machine-readable contract changes require an explicit schema decision.

## Release sequence

| Milestone | Version | Status |
|---|---|---|
| Integrated development checkpoint | `v0.1.0-dev` | Completed after Sprint 6 Patch 023. Local unless explicitly pushed. |
| Research preview candidate | `v0.1.0-rc1` | Planned after Sprint 12 release gates. |
| First research release | `v0.1.0` | Planned after Sprint 18 release gates. |

## Checkpoint tag verification

```bash
git status --short
git show --stat --decorate v0.1.0-dev
git rev-parse v0.1.0-dev^{}
git rev-parse HEAD
```

The commit identifiers should match when verifying the original checkpoint commit. Later development naturally moves `HEAD` beyond the tag.

A normal branch push does not publish a tag. Publish a release tag explicitly only after its release checklist passes.

## Schema timeline

- `0.1.0`: retained representative final-shape historical target, mitigation,
  count, primitive, gadget, score, and limitations snapshot validated through a
  versioned compatibility schema.
- `0.2.0`: current Sprint 9 report and command identity plus bounded analysis-completeness contract.
- `0.2.x`: compatible per-candidate provenance, validator, and evidence additions through the first research release.

The tool version remains `0.1.0-dev`; advancing the schema does not move the checkpoint tag. Do not introduce another breaking schema before `v0.1.0` unless a release-blocking correctness issue requires a documented migration and affected experiment restart.


## Historical schema compatibility

`schemas/x64lens-report.schema.json` names the current schema. The historical
`0.1.0` schema and representative final-shape report are preserved under
versioned file names. `make schema-compat-smoke` verifies those retained
artifacts while current producer validation requires schema `0.2.0` and command
identity. This is not a guarantee that every intermediate pre-release `0.1.0`
emission can be reconstructed or validated.

Schema version is part of benchmark provenance. Data from `0.1.0` and `0.2.0`
must not be merged without an explicit normalization procedure.

## Changelog rules

- Maintain exactly one `Unreleased` section.
- Record public behavior, schema, CLI, benchmark, contract, and release changes.
- Sprint retrospectives should state contract drift and update the changelog.
- Historical implementation notes may remain, but current status must appear first.

## Release tag rules

Before `v0.1.0-rc1` or `v0.1.0`:

1. working tree is clean,
2. native and Docker validation pass,
3. public documentation and planning checks pass,
4. schema and tool versions match documentation,
5. release artifacts and checksums verify,
6. benchmark and corpus identifiers are frozen,
7. tag message describes the release gate,
8. tag points to the validated commit.

See [`research-release-plan.md`](research-release-plan.md) and [`design/schema-evolution.md`](design/schema-evolution.md).


## Patch 041 schema compatibility note

Patch 041 remains schema `0.2.0`. Candidate evidence is optional in the formal
schema so initial Patch 040 reports stay valid, while current-producer tests
require it explicitly. This is a compatible addition within the `0.2.x` line,
not a redefinition of existing fields or counts.
