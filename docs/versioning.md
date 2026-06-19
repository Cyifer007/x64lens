# Versioning Plan

## Tool version

The executable has a semantic tool version:

```text
0.1.0-dev
```

Before `1.0.0`, breaking changes are allowed but must be documented.

## Schema version

The JSON output has a separate schema version:

```text
0.1.0
```

Breaking JSON shape changes require a schema version change.

## Release tags

Sprint tags:

```text
v0.1.0-sprint1
v0.1.0-sprint2
v0.1.0-sprint3
v0.1.0-sprint4
v0.1.0-sprint5
v0.1.0-sprint6
```

Public release candidates:

```text
v0.1.0-rc1
v0.1.0
```

## Changelog rules

Every sprint retrospective should update `CHANGELOG.md` under `Unreleased`.

## Local Sprint 6 checkpoint tag

The first integrated checkpoint uses the annotated tag `v0.1.0-dev`. Create it only after Patch 023 is committed and the working tree is clean:

```bash
make checkpoint-tag-help
git status --short
git tag -a v0.1.0-dev   -m "x64lens v0.1.0-dev integrated checkpoint"
git show --stat --decorate v0.1.0-dev
git rev-parse v0.1.0-dev^{}
git rev-parse HEAD
```

The final two commit identifiers should match. The tag remains local until `git push origin v0.1.0-dev` is run explicitly.
