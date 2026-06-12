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
