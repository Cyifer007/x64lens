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
| `gadgets [--format text|json] [--max-depth N] <file>` | Print raw, exact-pattern, semantic, scored gadget facts with report identity and completion state | Implemented; JSON schema `0.2.0` |
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

Silent truncation is not permitted. Schema `0.2.0` now defines completeness and truncation fields for successful reports, but it does not enable partial output. A future partial-analysis mode must implement truthful scanner progress and dropped-count semantics before it can change the fail-closed behavior.

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

Human-readable text output may change before `1.0.0`. Current JSON output must include `schema_version`, `tool`, `tool_version`, `report_type`, `command`, `analysis`, `target`, and `limitations`. Compatible additions should remain within the `0.2.x` line; the retained representative final-shape `0.1.0` snapshot uses the versioned compatibility schema.

## Current `mitigations` behavior

The `mitigations` command reports loader-level static indicators derived from
ELF type and program headers. After Patch 032 it also reports bounded `PT_DYNAMIC` facts, derives the current RELRO state from those facts, and emits an evidence-qualified canary indicator:

- dynamic linking presence,
- no, partial, or full RELRO state,
- bind-now evidence,
- dynamic-entry count,
- dynamic terminator state,
- canary indicator `unknown`, `absent`, or `present`.

The canary field is a bounded dynamic-string indicator. `present` means exact null-terminated `__stack_chk_fail` evidence was found in a validated dynamic string table. It does not prove every function is stack-protected.

These are static indicators, not exploitability or safety verdicts.

## Current `gadgets` behavior

The `gadgets` command emits the current staged analysis pipeline:

1. raw return-terminated candidate windows,
2. exact suffix pattern labels,
3. conservative semantic primitive classes,
4. controlled-register coverage,
5. stack-delta facts,
6. heuristic score values,
7. per-candidate raw/exact/semantic evidence provenance,
8. report and command identity plus complete-analysis facts,
9. limitations in JSON output.

Important interpretation details:

- `--max-depth` limits the bytes considered before the terminator, not necessarily the total printed byte count when the terminator itself is included.
- `pattern: pop rdi; ret` means the suffix immediately before the terminator matches `5f c3`.
- Pattern labels are not proof that the entire printed byte window is a fully decoded instruction sequence.
- Score values are heuristic relative-utility values, not exploitability verdicts.
- JSON output is generated from internal records, not from text output.

## Current `analyze` behavior

The `analyze` command is the Sprint 6 checkpoint command. It runs the same internal record pipeline as `gadgets`, while also exposing target metadata and mitigation facts in one command path.

Text output uses composable body-only wrappers around the established `info`, `mitigations`, and `gadgets` section emitters, which preserves one top-level banner without duplicating report logic. JSON output uses the same schema-backed report adapter as `gadgets --format json`. Schema `0.2.0` identifies the producing command as `analyze` while preserving the same target, mitigation, candidate, primitive, score, completion, and limitation facts. Reporter changes must preserve scanner, classifier, scoring, and metric meanings.

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

## Sprint 8 Patch 033 stripped-status update

Patch 033 reports stripped status as an evidence-qualified mitigation metadata field. Text uses `Stripped indicator: unknown`, `stripped`, or `not stripped`; JSON uses `mitigations.stripped` values `unknown`, `stripped`, or `not_stripped`. The section-header scan is bounded and never selects executable regions or candidate scan ranges. Duplicate `DT_STRTAB` and `DT_STRSZ` dynamic entries fail closed as malformed input so canary evidence is not order-dependent.

## Sprint 8 Patch 034 section-label update

Patch 034 may emit section labels for executable regions and gadget candidates when a bounded section-name table is available. Text output uses `section: <name>` annotations. JSON gadget records may include `section` as a string or `null`. These labels are optional metadata and must not be interpreted as runtime mapping authority.


## Sprint 9 Patch 040 report identity and completeness

Successful `gadgets` and `analyze` reports now identify:

```text
Report type: analysis
Command: gadgets | analyze
Complete: yes
Candidate truncated: no
Candidate dropped count: 0
Regions scanned: <N>
Regions total: <N>
```

JSON schema `0.2.0` exposes the same state through top-level `report_type`,
`command`, and `analysis` fields. For the same target and options, `gadgets` and
`analyze` JSON share the same analysis facts and differ only in command identity.

`complete` describes bounded candidate enumeration over loader-derived
executable regions. It is not decoder validation. Candidate-arena overflow
continues to return exit code `6` with empty stdout, so Patch 040 does not emit or
invent an incomplete report for that path.

Representative final-shape schema `0.1.0` output remains consumable through the
versioned schema and validator compatibility path. Intermediate pre-release
`0.1.0` emissions are not covered by that guarantee.


## Sprint 9 Patch 041 candidate provenance

Current JSON candidates include an `evidence` object derived from a dense
candidate-index side-car. It records raw-candidate presence, exact-suffix
presence and range, semantic evidence source, validator identity, and
full-sequence-validity state. Current exact-pattern reports use
`full_sequence_valid: null`; the CLI does not imply decoder validation.

Text output remains unchanged in Patch 041. The provenance extension is
machine-readable and backward-compatible within schema `0.2.0`.

## Sprint 9 closeout

Patch 045 changes no command, flag, exit code, or output field. The default CLI remains decoder-free and single-worker. Any future decoder or worker control must be introduced as an explicit profile or option with documented identity, compatibility, failure semantics, and benchmark separation; it must not silently alter existing command meaning.

## Sprint 10 Patch 047 gadget-effect behavior

The CLI syntax and exit codes are unchanged. `gadgets` and `analyze` may now
report exact `mov r64,r64; ret` register-transfer candidates with explicit
source/destination, clobber, stack, and side-effect facts. Unsupported transfer
forms retain the strongest existing suffix interpretation.

## Sprint 10 Patch 048 stack-adjust behavior

`gadgets` and `analyze` may report exact `add rsp, imm8; ret` suffixes when the immediate is positive, nonzero, and eight-byte aligned. At the Patch 048 boundary, these candidates were semantic-exact alignment facts with known total stack delta, `stack_adjust` and `flags_write` effects, and no score. Unsupported arithmetic forms remain bare-return fallbacks. CLI syntax, exit codes, capacity behavior, and schema version remain unchanged.

## Sprint 10 Patch 049 memory-effect reporting

The CLI syntax and exit codes do not change. Current `gadgets` and `analyze` reports may include structured `memory_access` facts for the restricted exact qword base-plus-zero memory families. The field does not imply decoded full-window validity or external control of the address or memory contents.


## Sprint 10 Patch 050 effect-completion note

Current `gadgets` and `analyze` reports record `stack_read` for every supported semantic candidate ending in `ret` or `ret imm16`. `syscall; ret` records `rcx` and `r11` clobbers, `leave; ret` records an `rbp` clobber, and transfer/memory-read candidates retain destination clobbers. This changes represented effect detail, not CLI syntax, exit codes, candidate counts, or schema version.

## Sprint 10 Patch 051 architectural-effect and score behavior

Current `gadgets` and `analyze` reports include candidate-index architectural
effects for represented GPR, flag, control-flow, and stack-source facts. Ordered
two-pop argument control scores 95 and positive aligned stack adjustment scores
35 only after semantic and architectural facts validate. Register-transfer and
memory candidates remain unscored. CLI syntax, exit codes, capacity behavior,
and schema version remain unchanged.
