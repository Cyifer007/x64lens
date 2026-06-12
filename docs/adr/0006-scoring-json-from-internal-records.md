# ADR 0006: Scoring and JSON Must Consume Internal Records

## Status

Accepted.

## Context

Sprint 5 adds the first heuristic score model and initial JSON output. The repository already separates raw candidate discovery, exact suffix pattern matching, and semantic classification. The next risk is allowing reporters, benchmark scripts, or JSON output to infer facts by scraping human-readable text.

That would make the repository brittle and would blur the difference between analysis facts and presentation.

## Decision

Scoring and JSON output must consume internal records directly:

```text
scanner -> gadget_record[]
patterns.asm -> GADGET_PATTERN_ID
classifier.asm -> semantic class, registers, stack delta, side effects
scoring.asm -> GADGET_SCORE and scored_candidate_count
report_text.asm/report_json.asm -> render only
```

Patch 017 implements JSON first for:

```bash
x64lens gadgets --format json [--max-depth N] <file>
```

The future `analyze` command must reuse the same record path rather than introducing duplicate scanning, classification, or scoring logic.

## Consequences

Positive:

- JSON and text output remain independent renderers.
- Benchmark scripts can eventually prefer JSON instead of parsing text.
- Future decoder records can be added without replacing the scanner.
- Future SARIF output can reuse the same fact model.

Tradeoffs:

- Assembly JSON generation is verbose.
- The first JSON path is intentionally narrow.
- Path string escaping is intentionally minimal but valid for normal CLI paths.
- Full schema validation remains a later environment/tooling task.

## Non-goals

This ADR does not implement:

- integrated `analyze` output,
- SARIF output,
- full x86_64 decoding,
- exploitability verdicts,
- score calibration against external tools.
