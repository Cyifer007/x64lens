# JSON Schema Contract

## Purpose

The JSON output is the enterprise and research integration layer. Text output is for humans. JSON output is for automation, CI/CD, benchmark processing, vulnerability management enrichment, and future dashboards.

## Versioning

The report must include:

```json
{
  "schema_version": "0.1.0",
  "tool": "x64lens",
  "tool_version": "0.1.0-dev"
}
```

Schema version and tool version are separate. Tool behavior can change without breaking the schema. Schema changes must be tracked in `CHANGELOG.md`.

## Draft report shape

```json
{
  "schema_version": "0.1.0",
  "tool": "x64lens",
  "tool_version": "0.1.0-dev",
  "target": {
    "path": "./toy",
    "format": "ELF64",
    "arch": "x86_64",
    "file_size": 16072,
    "entry": "0x401050"
  },
  "mitigations": {
    "nx_stack": true,
    "pie": false,
    "relro": "partial",
    "canary_indicator": false,
    "rwx_load_segment": false
  },
  "primitive_coverage": {
    "rdi_control": true,
    "rsi_control": true,
    "rdx_control": false,
    "rax_control": true,
    "syscall_trigger": false,
    "stack_pivot": true
  },
  "gadgets": [
    {
      "va": "0x40118a",
      "file_offset": "0x118a",
      "bytes": "5fc3",
      "asm": "pop rdi; ret",
      "semantic_class": "arg_control",
      "controls": ["rdi"],
      "stack_delta": 16,
      "score": 95
    }
  ],
  "limitations": [
    "Pattern-based scanner, not full x86_64 decoder",
    "Canary detection is import/symbol based and may be incomplete",
    "Exploitability interpretation assumes an independent memory corruption primitive"
  ]
}
```

## JSON design rules

- Hex addresses are strings.
- Numeric sizes and counts are JSON numbers.
- Booleans are true booleans, not strings.
- Unknown values should use `null` or explicit strings such as `"unknown"`, but not empty strings.
- Every report must include `limitations`.
- Every report must include `schema_version`.
- Future SARIF output must be generated from internal analysis records, not from text output.

## Future count fields

Future JSON reports should expose distinct counters for raw, exact, semantic, unknown, and scored candidates. This avoids ambiguity in automation and benchmark processing.

Candidate future shape:

```json
"summary": {
  "raw_candidate_count": 0,
  "exact_pattern_count": 0,
  "semantic_candidate_count": 0,
  "unknown_candidate_count": 0,
  "scored_candidate_count": 0
}
```

Do not expose a single ambiguous `gadget_count` field without defining what it means.
