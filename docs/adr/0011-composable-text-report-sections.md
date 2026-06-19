
# ADR 0011: Composable Text Report Sections

## Status

Accepted for the Sprint 6 integrated checkpoint.

## Context

The focused `info`, `mitigations`, and `gadgets` commands each emit a complete version and target banner. Calling those complete reporters sequentially from `analyze` produced three repeated banners in one logical report.

Duplicating the section-formatting logic inside `analyze` would create two implementations of the same output contract and increase the risk of drift.

## Decision

Keep the focused reporters complete and add body-only wrappers through `src/report_context.asm`. `analyze` calls the complete information reporter once, then calls body-only mitigation and gadget reporters.

The wrappers set a short-lived process-local flag. `report_text.asm` checks that flag only around its banner block. All section rendering remains in the existing reporters.

## Consequences

- `analyze` emits one version line and one target line.
- Focused command output remains unchanged.
- Analysis records and JSON output remain unchanged.
- A future integrated command can reuse the same body-only seam.
- The current flag assumes the documented single-threaded execution model.
