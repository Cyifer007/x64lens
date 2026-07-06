# Output Contract

## Text output

Text output is optimized for human readability. It may change before `1.0.0`, but major changes should be documented.

## JSON output

JSON output is optimized for tools and automation. It must be schema-versioned.

## Required JSON fields

Every JSON report must include:

- `schema_version`,
- `tool`,
- `tool_version`,
- `target`,
- `limitations`.

## Address formatting

Virtual addresses and file offsets are hex strings.

Example:

```json
"va": "0x000000000040118a"
```

## Count separation in output

Reports should separate:

- raw candidate count,
- exact pattern count,
- semantic primitive count,
- unknown candidate count,
- scored candidate count.

Do not infer semantic value from raw scanner output alone.

## Unknown values

Unknown machine-readable values should be represented explicitly:

- JSON unknown numeric values should use `null`, not `0`, when `0` would be ambiguous.
- JSON should pair ambiguous fields with explicit indicators when useful, such as `stack_delta_known`.
- Text output may keep stable legacy representations during early development, but JSON should prefer explicit machine-readable meaning.

## Limitations

Every JSON report should include limitations when the analysis is incomplete or heuristic.

## Exploitability wording

The tool may report primitive availability and plausible exploit strategy constraints. It must not state that a binary is exploitable without an independent vulnerability and runtime context.

## Public repository voice

Public output, documentation, comments, tests, and examples must be written as repository-facing project material. They must not reference private coordination context, attachment history, or tool-assisted workflow details. Public wording should describe repository facts, implementation decisions, validation evidence, and reproducible commands from the project perspective.


## Public validation transcript rule

Public validation snippets should use generic prompts and repository-relative paths where possible. Avoid committing personal hostnames, local usernames, local home-directory paths, private attachment names, or dialogue-style context. Prefer examples such as:

```text
$ make test
tests: ok
```

Use repository facts, reproducible commands, and observed technical outcomes instead of private workflow narration.

## Complete-report failure rule

When bounded storage or a parser precondition prevents a complete report, the command must fail before emitting text or JSON stdout. Silent truncation and syntactically incomplete JSON are prohibited. Candidate-arena exhaustion currently uses exit code `6` and the stable unsupported-feature diagnostic.

A future intentional partial-report mode must expose explicit machine-readable completeness and truncation state and follow the schema transition contract before release.

## Mitigation consistency rule

The same valid ELF64 program-header evidence must produce compatible mitigation facts in focused text output and integrated JSON. Patch 030 extends this rule to bounded `PT_DYNAMIC` facts: bind-now, dynamic-entry count, and dynamic terminator state must agree between focused mitigation text and integrated JSON. Patch 031 refines RELRO to no, partial, and full states: full RELRO requires `PT_GNU_RELRO` plus bounded bind-now evidence, partial RELRO requires `PT_GNU_RELRO` without bind-now evidence, and no RELRO requires no `PT_GNU_RELRO`. Malformed file-backed `PT_LOAD` and `PT_DYNAMIC` ranges, plus duplicate `PT_DYNAMIC` headers, must fail before any partial stdout is emitted. `info`, `mitigations`, `gadgets`, and `analyze` must return the stable malformed-ELF status and diagnostic for controlled matrix defects when the command path parses the relevant table.

## Canary indicator wording

Text output must use `Canary indicator:` rather than wording that implies complete stack protection. JSON `mitigations.canary` may be `unknown`, `absent`, or `present`. `unknown` is required when bounded metadata is unavailable. `present` means exact `__stack_chk_fail` evidence was found in a validated dynamic string table; it does not prove every function is protected.

## Sprint 8 Patch 033 stripped-status update

Patch 033 reports stripped status as an evidence-qualified mitigation metadata field. Text uses `Stripped indicator: unknown`, `stripped`, or `not stripped`; JSON uses `mitigations.stripped` values `unknown`, `stripped`, or `not_stripped`. The section-header scan is bounded and never selects executable regions or candidate scan ranges. Duplicate `DT_STRTAB` and `DT_STRSZ` dynamic entries fail closed as malformed input so canary evidence is not order-dependent.

## Sprint 8 Patch 034 section-label update

Patch 034 may emit section labels for executable regions and gadget candidates when a bounded section-name table is available. Text output uses `section: <name>` annotations. JSON gadget records may include `section` as a string or `null`. These labels are optional metadata and must not be interpreted as runtime mapping authority.


## Sprint 8 Patch 035 section-label rendering update

Text section labels are single-line-safe. Printable ASCII bytes are emitted directly except backslash; backslash is escaped as `\\`, and control bytes, DEL, and high-bit bytes are escaped as `\xNN`. JSON section fields remain strings or `null` and use byte-safe JSON escaping. Ambiguous overlapping executable section metadata must not force a label.

## Sprint 8 Patch 036 byte-safe JSON and label-agreement update

Patch 036 requires JSON report strings emitted by the NASM adapters to remain valid JSON for control bytes and high-bit bytes. Bounded section labels are emitted through byte-safe JSON escaping instead of raw byte emission. Section labels are omitted unless the section contains both the record file offset and the record virtual address. This preserves labels as optional metadata and keeps program headers as runtime mapping authority.

Benchmark smoke summaries are evidence artifacts, not report-schema artifacts. They must reject nonnumeric or negative metric fields before normal summarization, and mixed-artifact aggregation requires explicit opt-in.


## Comparator output boundary

`readelf`, `checksec`, and `rabin2` outputs are validation and review artifacts.
They do not change the x64lens JSON schema or text output contract. x64lens
continues to distinguish loader facts, section-derived annotations, raw
candidates, exact suffixes, semantic classes, unknowns, and scored facts.
