# Output Contract

## Text output

Text output is optimized for human readability. It may change before `1.0.0`, but major changes should be documented.

## JSON output

JSON output is optimized for tools and automation. It must be schema-versioned.

## Required fields

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
"va": "0x40118a"
```

## Limitations

Every output should include limitations when the analysis is incomplete or heuristic.

## Exploitability wording

The tool may report primitive availability and plausible exploit strategy constraints. It must not state that a binary is exploitable without an independent vulnerability and runtime context.
