# CLI Contract

## Stability level

The CLI is experimental until version `1.0.0`, but every breaking change must be documented in `CHANGELOG.md`.

## Command model

```bash
x64lens <command> [options] <file>
```

## Implemented commands

| Command | Purpose | Status |
| ------- | ------- | ------ |
| `info <file>` | Parse and print ELF64 metadata | Implemented in Sprint 1 |
| `mitigations <file>` | Print hardening and mitigation metadata | Implemented in Sprint 2 |
| `gadgets [--format text|json] [--max-depth N] <file>` | Print raw, exact-pattern, semantic, scored gadget facts | Implemented; JSON schema `0.1.0` |
| `analyze [--format text|json] [--max-depth N] <file>` | Integrated checkpoint report with target metadata, mitigation facts, primitive coverage, scores, and limitations | Implemented in Sprint 6; composable text reporting completed in Patch 023 |
| `version` | Print tool and schema version | Implemented in Sprint 1 |
| `help` | Print usage | Implemented in Sprint 1 |

## Planned commands

| Command | Purpose | Sprint target |
| ------- | ------- | ------------- |
| `bench <file>` | Optional in-process benchmark command | Deferred until after `v0.1.0`; external scripts remain authoritative for research measurement |

## Implemented flags

| Flag | Meaning | Status |
| ---- | ------- | ------ |
| `--max-depth <N>` | Maximum bytes considered before a return terminator | Implemented in Sprint 3 |
| `--format text|json` | Select text or JSON output for `gadgets` and `analyze` | Implemented |

`--format` and `--max-depth` may be used together in either order for `gadgets` and `analyze`:

```bash
x64lens gadgets --format json --max-depth 4 ./tests/bin/gadgets
x64lens gadgets --max-depth 4 --format json ./tests/bin/gadgets
x64lens analyze --format json --max-depth 4 ./tests/bin/gadgets
x64lens analyze --max-depth 4 --format json ./tests/bin/gadgets
```

## Planned flags

| Flag | Meaning | Target |
| ---- | ------- | ------ |
| `--badbytes <hex-list>` | Mark gadgets whose addresses contain bad bytes | Future scoring refinement |
| `--quiet` | Minimal output | Future output refinement |
| `--verbose` | More diagnostic output | Future output refinement |
| `--no-color` | Disable color output | Future output refinement |
| `--schema-version` | Print JSON schema version directly | Future CLI refinement |

## Exit codes

| Exit code | Meaning |
| --------: | ------- |
| 0 | Analysis completed |
| 1 | General error |
| 2 | Invalid CLI usage |
| 3 | File open/read/map error |
| 4 | Not an ELF64 x86_64 binary |
| 5 | Malformed or truncated ELF |
| 6 | Unsupported binary feature or bounded analysis capacity exceeded before a complete report can be produced |
| 7 | Internal bounds or safety failure |

## Capacity failure contract

The current candidate arena stores 4096 records. When a target would require a 4097th record, `gadgets` and `analyze` return exit code `6` before report emission. This applies to text and JSON modes. Stdout remains empty and stderr contains the stable unsupported-feature diagnostic.

Silent truncation is not permitted. A future partial-analysis mode requires explicit completeness and truncation fields and a schema transition before it can change this behavior.

## Command examples

```bash
x64lens info ./toy
x64lens mitigations ./toy
x64lens gadgets ./toy
x64lens gadgets --max-depth 8 ./toy
x64lens gadgets --format json ./toy > report.json
x64lens gadgets --format json --max-depth 4 ./toy > gadgets.json
x64lens analyze ./toy
x64lens analyze --format json --max-depth 4 ./toy > analyze.json
x64lens version
```

## Output stability

Human-readable text output may change before `1.0.0`. JSON output must include `schema_version`, `tool_version`, `target`, and `limitations`, and should remain backward-compatible within the same schema major version.

## Current `gadgets` behavior

The `gadgets` command emits the current staged analysis pipeline:

1. raw return-terminated candidate windows,
2. exact suffix pattern labels,
3. conservative semantic primitive classes,
4. controlled-register coverage,
5. stack-delta facts,
6. heuristic score values,
7. limitations in JSON output.

Important interpretation details:

- `--max-depth` limits the bytes considered before the terminator, not necessarily the total printed byte count when the terminator itself is included.
- `pattern: pop rdi; ret` means the suffix immediately before the terminator matches `5f c3`.
- Pattern labels are not proof that the entire printed byte window is a fully decoded instruction sequence.
- Score values are heuristic relative-utility values, not exploitability verdicts.
- JSON output is generated from internal records, not from text output.

## Current `analyze` behavior

The `analyze` command is the Sprint 6 checkpoint command. It runs the same internal record pipeline as `gadgets`, while also exposing target metadata and mitigation facts in one command path.

Text output uses composable body-only wrappers around the established `info`, `mitigations`, and `gadgets` section emitters, which preserves one top-level banner without duplicating report logic. JSON output uses the same schema-backed report as `gadgets --format json`, because that report already contains the integrated target, mitigation, primitive, scoring, and limitation fields. This is the `0.1.0-dev` checkpoint contract and can evolve only through reporter-level changes that preserve scanner, classifier, scoring, and schema facts.

`analyze` must not be interpreted as an exploitability verdict. It is a static triage report.

## Reporting distinction rule

The CLI should keep analysis stages explicit in output and JSON:

- raw candidates,
- exact suffix patterns,
- semantic primitives,
- unknown candidates,
- scored candidates,
- mitigation indicators,
- limitations.

When a command emits partial or heuristic analysis, the output should say so. `analyze` does not imply full exploitability because that would require an independent vulnerability and runtime context, which are outside the current scope.

## Validation commands added in Patch 018

The following make targets are part of the development and validation workflow, not the end-user CLI:

```bash
make json-smoke
make system-smoke
make capacity-smoke
make malformed-smoke
make validation-smoke
make docker-available-check
make docker-validation-smoke
BUNDLE=/path/to/patch.zip make patch-bundle-hygiene
```

`system-smoke` exercises the implemented commands against installed ELF64 x86_64 system binaries. It validates output shape and count invariants instead of exact distro-specific gadget totals.


## Benchmark command deferral

The research benchmark harness remains under `benchmarks/scripts/` rather than inside the analyzer process. This keeps measurement orchestration, tool ordering, target manifests, raw-row preservation, and baseline execution independent from the implementation being measured. A future `bench` CLI command is not required for the first research release.
