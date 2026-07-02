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
