# Versioning Plan

## Independent versions

x64lens maintains two independent version lines:

```text
tool version:   0.1.0-dev
schema version: 0.1.0
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

- `0.1.0`: current target, mitigation, count, primitive, gadget, score, and limitations report.
- `0.2.0`: planned Sprint 9 provenance, report identity, completeness, and truncation contract.
- `0.2.x`: backward-compatible clarifications and optional fields through the first research release.

Do not introduce another breaking schema before `v0.1.0` unless a release-blocking correctness issue requires a documented migration and affected experiment restart.

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
