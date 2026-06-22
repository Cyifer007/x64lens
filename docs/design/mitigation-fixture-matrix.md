# Mitigation Fixture Matrix

## Purpose

This document defines the controlled ELF64 layouts used by `tools/mitigation-matrix-smoke.py`. The matrix is a behavioral oracle for loader-level mitigation facts. It is not a catalog of exploitability outcomes.

## Valid cases

| Case | ELF type | Program-header evidence | Required interpretation |
| --- | --- | --- | --- |
| `exec-no-stack` | `ET_EXEC` | one RX `PT_LOAD` | PIE disabled, NX unknown, one executable region |
| `dyn-no-stack` | `ET_DYN` | one RX `PT_LOAD` | PIE enabled, NX unknown |
| `nx-stack` | `ET_EXEC` | RX `PT_LOAD`, RW `PT_GNU_STACK` | NX enabled |
| `executable-stack` | `ET_EXEC` | RX `PT_LOAD`, RWX `PT_GNU_STACK` | NX disabled |
| `relro` | `ET_EXEC` | RX `PT_LOAD`, `PT_GNU_RELRO` | RELRO present |
| `dynamic` | `ET_EXEC` | RX `PT_LOAD`, `PT_DYNAMIC` | dynamic linking yes |
| `rwx-load` | `ET_EXEC` | RWX `PT_LOAD` | RWX load yes, one executable region |
| `non-executable-load` | `ET_EXEC` | RW `PT_LOAD` | no executable regions |
| `split-rx-rw-loads` | `ET_EXEC` | separate RX and RW `PT_LOAD` entries | two loads, one executable region, no RWX load |
| `overlapping-loads-characterized` | `ET_EXEC` | two overlapping RX `PT_LOAD` entries | two executable-region records under the current model |
| `combined-hardening-evidence` | `ET_DYN` | RX and RW loads, RW stack, RELRO, dynamic | PIE and NX enabled, RELRO present, dynamic yes, no RWX load |

Every valid case must pass both of these command paths:

```bash
./build/x64lens mitigations <fixture>
./build/x64lens analyze --format json --max-depth 4 <fixture>
```

The text path is checked against exact mitigation-summary and executable-region lines. The integrated path must produce a JSON object, expose the matching mitigation values, and emit no stderr.

## Malformed cases

| Case | Defect | Required result |
| --- | --- | --- |
| `wrong-phentsize` | `e_phentsize` is not 56 | exit 5 |
| `truncated-program-header-table` | declared table is one byte beyond EOF | exit 5 |
| `program-header-offset-out-of-file` | `e_phoff` starts beyond EOF | exit 5 |
| `load-file-range-out-of-file` | `p_offset + p_filesz` exceeds file size | exit 5 |
| `load-file-range-addition-overflow` | declared load range wraps unsigned 64-bit arithmetic | exit 5 |

Each malformed case is exercised through:

```text
info
mitigations
analyze --format json --max-depth 4
```

The required failure contract is:

- exit code `5`,
- empty stdout,
- stderr equal to `error: malformed or truncated ELF` followed by one newline,
- no signal,
- no timeout.

## Evidence artifact

A successful run writes one ignored JSON artifact under:

```text
tests/results/mitigation-matrix/
```

The artifact records the harness version, artifact schema version, analyzed binary path, seed path and SHA-256, fixture hashes, expected mitigation and region lines, command exit codes, case counts, and per-case results. Generated ELF fixtures are removed when the run finishes.

## Interpretation boundary

The matrix validates deterministic static facts. It does not establish that a binary is exploitable, safe, network reachable, or protected at runtime. The overlapping-load case records current region semantics and must not be described as deduplication support.
