# ADR 0010: Add `analyze` as the Sprint 6 Integrated Checkpoint Command

## Status

Accepted.

## Context

Sprints 1 through 5 produced separate, validated command slices:

- `info` for ELF64 metadata,
- `mitigations` for program-header and loader-facing mitigation facts,
- `gadgets` for raw candidates, exact suffix patterns, semantic classes, stack deltas, scoring, and JSON output,
- validation smoke targets for fixtures, JSON, system binaries, Docker, and optional baselines.

The next useful checkpoint is a single command that demonstrates the current product direction without waiting for later mitigation-hardening or full-decoder work. The command must not duplicate scanner, classifier, scoring, or JSON logic.

## Decision

Add `analyze [--format text|json] [--max-depth N] <file>` in Sprint 6 Patch 022.

The command runs the current validated pipeline once:

```text
file map -> ELF64 validation -> program-header analysis -> executable regions -> scanner -> exact patterns -> semantic classifier -> scoring -> text or JSON report
```

Text output initially reuses the established `info`, `mitigations`, and `gadgets` section emitters. JSON output reuses the existing schema-backed gadget JSON report because it already includes target metadata, mitigation facts, separated counts, primitive coverage, scored candidates, and limitations.

## Rationale

This creates a real checkpoint product without weakening scope discipline:

- The command is useful for demos and defensive triage workflows.
- The implementation reuses internal records instead of creating a parallel pipeline.
- Existing JSON validation and system-binary smoke infrastructure can validate it immediately.
- Later mitigation hardening can improve facts consumed by `analyze` without changing the command boundary.

## Consequences

Positive consequences:

- The project now has a coherent end-to-end command for the `0.1.0-dev` checkpoint.
- The defensive triage story becomes easier to explain.
- Sprint 7 hardening can target facts that already flow into a product-facing command.

Tradeoffs:

- Text output repeats existing section headers because it reuses stable section renderers.
- JSON output does not yet include a dedicated top-level `command` or `report_type` field.
- The command remains a static triage report, not an exploitability verdict.

## Follow-up

- Polish text output in a later output-focused patch.
- Consider adding a report-type field in a future schema revision.
- Keep baseline gadget benchmarks on `gadgets --format json` unless the benchmark question is explicitly end-to-end triage cost.
