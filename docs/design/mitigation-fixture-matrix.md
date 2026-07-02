# Mitigation Fixture Matrix

## Purpose

This document defines the controlled ELF64 layouts used by `tools/mitigation-matrix-smoke.py`. The matrix is a behavioral oracle for loader-level mitigation facts. It is not a catalog of exploitability outcomes.

After Patch 033, the matrix contains 23 valid layouts, 14 malformed layouts, and one unsupported fail-closed layout. The valid side includes no, partial, and full RELRO states, bounded dynamic-table cases, canary-present/canary-absent indicator fixtures, zero-length dynamic string-table negative evidence, and stripped/not-stripped section-table fixtures. The malformed side includes duplicate-`PT_DYNAMIC`, duplicate `DT_STRTAB`, duplicate `DT_STRSZ`, invalid dynamic string-table evidence, and dynamic malformed coverage for scanner callers as well as mitigation and integrated analysis callers. The unsupported side covers dynamic string tables above the current bounded scan cap.

## Valid cases

| Case | ELF type | Program-header evidence | Required interpretation |
| --- | --- | --- | --- |
| `exec-no-stack` | `ET_EXEC` | one RX `PT_LOAD` | PIE disabled, NX unknown, one executable region |
| `dyn-no-stack` | `ET_DYN` | one RX `PT_LOAD` | PIE enabled, NX unknown |
| `nx-stack` | `ET_EXEC` | RX `PT_LOAD`, RW `PT_GNU_STACK` | NX enabled |
| `executable-stack` | `ET_EXEC` | RX `PT_LOAD`, RWX `PT_GNU_STACK` | NX disabled |
| `relro` | `ET_EXEC` | RX `PT_LOAD`, `PT_GNU_RELRO` | partial RELRO |
| `dynamic` | `ET_EXEC` | RX `PT_LOAD`, `PT_DYNAMIC` with `DT_NULL` | dynamic linking yes, bind-now no, dynamic terminator yes |
| `dynamic-no-null-bounded` | `ET_EXEC` | RX `PT_LOAD`, bounded `PT_DYNAMIC` without `DT_NULL` | dynamic linking yes, bind-now no, dynamic terminator no |
| `dynamic-bind-now-tag` | `ET_EXEC` | RX `PT_LOAD`, `PT_DYNAMIC` with `DT_BIND_NOW` and `DT_NULL` | bind-now yes through tag evidence |
| `dynamic-flags-bind-now` | `ET_EXEC` | RX `PT_LOAD`, `PT_DYNAMIC` with `DT_FLAGS & DF_BIND_NOW` and `DT_NULL` | bind-now yes through `DT_FLAGS` evidence |
| `dynamic-flags-1-now` | `ET_EXEC` | RX `PT_LOAD`, `PT_DYNAMIC` with `DT_FLAGS_1 & DF_1_NOW` and `DT_NULL` | bind-now yes through `DT_FLAGS_1` evidence |
| `full-relro-bind-now-tag` | `ET_EXEC` | RX `PT_LOAD`, `PT_GNU_RELRO`, `PT_DYNAMIC` with `DT_BIND_NOW` and `DT_NULL` | full RELRO through tag evidence |
| `full-relro-flags-bind-now` | `ET_EXEC` | RX `PT_LOAD`, `PT_GNU_RELRO`, `PT_DYNAMIC` with `DT_FLAGS & DF_BIND_NOW` and `DT_NULL` | full RELRO through `DT_FLAGS` evidence |
| `full-relro-flags-1-now` | `ET_EXEC` | RX `PT_LOAD`, `PT_GNU_RELRO`, `PT_DYNAMIC` with `DT_FLAGS_1 & DF_1_NOW` and `DT_NULL` | full RELRO through `DT_FLAGS_1` evidence |
| `rwx-load` | `ET_EXEC` | RWX `PT_LOAD` | RWX load yes, one executable region |
| `non-executable-load` | `ET_EXEC` | RW `PT_LOAD` | zero executable regions and exact text `none discovered from PT_LOAD + PF_X` |
| `split-rx-rw-loads` | `ET_EXEC` | separate RX and RW `PT_LOAD` entries | two loads, one executable region, no RWX load |
| `overlapping-loads-characterized` | `ET_EXEC` | two overlapping RX `PT_LOAD` entries | two executable-region records under the current model |
| `combined-hardening-evidence` | `ET_DYN` | RX and RW loads, RW stack, RELRO, dynamic with `DT_NULL` | PIE and NX enabled, partial RELRO, dynamic yes, bind-now no, no RWX load |
| `dynamic-string-canary-absent` | `ET_EXEC` | RX `PT_LOAD`, dynamic `DT_STRTAB` and `DT_STRSZ` pointing to a bounded string table without `__stack_chk_fail` | canary indicator absent |
| `dynamic-string-canary-present` | `ET_EXEC` | RX `PT_LOAD`, dynamic `DT_STRTAB` and `DT_STRSZ` pointing to a bounded string table containing exact `__stack_chk_fail\0` | canary indicator present |
| `dynamic-string-zero-size-absent` | `ET_EXEC` | RX `PT_LOAD`, dynamic `DT_STRTAB` and zero `DT_STRSZ` pointing to a validated string table | canary indicator absent from completed zero-length search |
| `section-table-without-symtab-stripped` | `ET_EXEC` | RX `PT_LOAD`, validated section table without `SHT_SYMTAB` | stripped indicator `stripped` |
| `section-table-with-symtab-not-stripped` | `ET_EXEC` | RX `PT_LOAD`, validated section table with `SHT_SYMTAB` | stripped indicator `not_stripped` |

Every valid case must pass these command paths:

```bash
./build/x64lens mitigations <fixture>
./build/x64lens analyze --format json --max-depth 4 <fixture>
./build/x64lens gadgets --format json --max-depth 4 <fixture>
```

The text path is checked against exact mitigation-summary and executable-region lines, including bind-now, dynamic-entry count, dynamic terminator state, canary indicator state, and stripped indicator state. When no `PT_LOAD + PF_X` region exists, the required region line is `  none discovered from PT_LOAD + PF_X`. The integrated path must produce a JSON object, expose the matching mitigation values, and emit no stderr. The direct `gadgets --format json` path is also checked for valid cases to keep the JSON emitter covered outside the integrated `analyze` command path.

## Malformed cases

| Case | Defect | Required result |
| --- | --- | --- |
| `wrong-phentsize` | `e_phentsize` is not 56 | exit 5 |
| `truncated-program-header-table` | declared table is one byte beyond EOF | exit 5 |
| `program-header-offset-out-of-file` | `e_phoff` starts beyond EOF | exit 5 |
| `program-header-table-addition-overflow` | declared program-header table extent wraps unsigned 64-bit arithmetic | exit 5 |
| `section-header-table-addition-overflow` | declared section-header table extent wraps unsigned 64-bit arithmetic | exit 5 |
| `load-file-range-out-of-file` | `p_offset + p_filesz` exceeds file size | exit 5 |
| `load-file-range-addition-overflow` | declared load range wraps unsigned 64-bit arithmetic | exit 5 |
| `dynamic-filesz-greater-than-memsz` | dynamic segment file size exceeds memory size | exit 5 |
| `dynamic-file-range-out-of-file` | dynamic file-backed range exceeds EOF | exit 5 |
| `dynamic-entry-size-unaligned` | dynamic file size is not a multiple of 16-byte `Elf64_Dyn` records | exit 5 |
| `multiple-pt-dynamic` | more than one `PT_DYNAMIC` program header is present | exit 5 |
| `dynamic-strtab-unmapped` | `DT_STRTAB` and `DT_STRSZ` claim a dynamic string table that does not resolve to a file-backed `PT_LOAD` range | exit 5 |
| `duplicate-dt-strtab` | dynamic table contains more than one `DT_STRTAB` entry | exit 5 |
| `duplicate-dt-strsz` | dynamic table contains more than one `DT_STRSZ` entry | exit 5 |

Most malformed cases are exercised through:

```text
info
mitigations
analyze --format json --max-depth 4
```

Dynamic-table malformed cases are exercised through `mitigations`, `analyze --format json --max-depth 4`, `gadgets --max-depth 4`, and `gadgets --format json --max-depth 4`, because each of those paths consumes `x64lens_phdr_analyze`. `info` intentionally reports ELF header facts and does not parse `PT_DYNAMIC`.

The required failure contract is:

- exit code `5`,
- empty stdout,
- stderr equal to `error: malformed or truncated ELF` followed by one newline,
- no signal,
- no timeout.

## Evidence artifact

Unsupported fail-closed cases use exit code `6`, empty stdout, and the stable unsupported-feature diagnostic. Patch 033 uses this path for a dynamic string table larger than the current bounded scan cap.

A successful run writes one ignored JSON artifact under:

```text
tests/results/mitigation-matrix/
```

The artifact records the harness version, artifact schema version, analyzed binary path, seed path and SHA-256, fixture hashes, expected mitigation and region lines, expected JSON mitigation values, direct gadgets JSON exit codes, command exit codes, case counts, and per-case results. Generated ELF fixtures are removed when the run finishes.

## Interpretation boundary

The matrix validates deterministic static facts. It does not establish that a binary is exploitable, safe, network reachable, or protected at runtime. The overlapping-load case records current region semantics and must not be described as deduplication support. Canary rows record symbol evidence only; they do not prove every function is stack-protected. Stripped rows record section-table symbol evidence only; they do not affect runtime mapping authority or candidate discovery.
