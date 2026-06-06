# CLI Contract

## Stability level

The CLI is experimental until version `1.0.0`, but every breaking change must be documented in `CHANGELOG.md`.

## Command model

```bash
x64lens <command> [options] <file>
```

## Initial commands

| Command | Purpose | Sprint target |
| ------- | ------- | ------------- |
| `info <file>` | Parse and print ELF64 metadata | Sprint 1 |
| `mitigations <file>` | Print hardening and mitigation metadata | Sprint 2 |
| `gadgets <file>` | Print gadget candidates and classified gadgets | Sprint 3 to 4 |
| `analyze <file>` | Full semantic analysis report | Sprint 4 to 6 |
| `bench <file>` | Benchmark x64lens against local target | Sprint 5 |
| `version` | Print tool version | Sprint 1 |
| `help` | Print usage | Sprint 1 |

## Initial global flags

| Flag | Meaning | Sprint target |
| ---- | ------- | ------------- |
| `--format text|json` | Select output format | Sprint 4 to 5 |
| `--max-depth <N>` | Maximum bytes or instruction window before terminator | Sprint 3 |
| `--badbytes <hex-list>` | Mark gadgets whose addresses contain bad bytes | Sprint 4 to 5 |
| `--quiet` | Minimal output | Sprint 5 |
| `--verbose` | More diagnostic output | Sprint 2 |
| `--no-color` | Disable color output | Sprint 5 |
| `--schema-version` | Print JSON schema version | Sprint 5 |

## Exit codes

| Exit code | Meaning |
| --------: | ------- |
| 0 | Analysis completed |
| 1 | General error |
| 2 | Invalid CLI usage |
| 3 | File open/read/map error |
| 4 | Not an ELF64 x86_64 binary |
| 5 | Malformed or truncated ELF |
| 6 | Unsupported binary feature |
| 7 | Internal bounds or safety failure |

## Command examples

```bash
x64lens info ./toy
x64lens mitigations ./toy
x64lens gadgets --max-depth 8 ./toy
x64lens analyze --format json ./toy > report.json
x64lens bench ./toy
x64lens version
```

## Output stability

Human-readable text output may change before `1.0.0`. JSON output must include `schema_version` and should remain backward-compatible within the same schema major version.
