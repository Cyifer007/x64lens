# ADR 0021: Section-label rendering and ambiguity hardening

## Status

Accepted for Sprint 8 Patch 035.

## Context

Patch 034 added optional section labels for executable regions and gadget candidates. Validation showed that the first implementation had three hardening gaps:

- text reports printed bounded section names directly, so a valid section name containing a newline could split a candidate line,
- overlapping non-executable section headers could capture an executable offset if they appeared earlier than the real executable section,
- the section-label helper used process-global state even though the current CLI is single-target and serial.

None of those gaps changed loader authority, scanner ranges, candidate counts, semantic classes, or scores. They were still worth fixing because section labels are intended to make reports clearer on hostile inputs, not less readable.

## Decision

Patch 035 hardens section labels as follows:

- Text reports render section names through a bounded text-safe printer. Printable ASCII bytes are emitted directly except backslash. Backslash is escaped as `\\`; control bytes, DEL, and high-bit bytes are escaped as `\xNN`.
- Section labels are assigned only from file-backed sections that carry both `SHF_ALLOC` and `SHF_EXECINSTR`.
- If multiple executable allocated sections overlap the same file offset, the record remains unlabeled instead of selecting a first match.
- Section-label helper state is stack-local to the annotation call rather than process-global.
- `make section-label-smoke` creates deterministic hostile section-name fixtures and is part of the aggregate validation gate.

## Consequences

Text output keeps one logical line per region or candidate even when section names are adversarial. JSON output still carries the bounded section-name string as machine-readable data, with normal JSON escaping.

The overlap policy is conservative. It may omit labels from deliberately ambiguous section tables, but it does not guess. Program headers remain the only executable-region authority, and section labels remain optional annotations.
