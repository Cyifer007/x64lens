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
