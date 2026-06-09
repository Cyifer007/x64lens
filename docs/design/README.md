# Design Planning Documents

This directory captures design rationale that is larger than a single sprint but smaller than the whole architecture document.

These documents exist to make reviewer-facing tradeoffs explicit before they become hidden assumptions in the codebase.

## Current documents

| Document | Purpose |
|---|---|
| `nasm-rationale.md` | Explains why the first engine is written in NASM and how that claim should be evaluated. |
| `decoder-roadmap.md` | Defines the boundary between raw scanning, exact suffix matching, semantic classification, and future decoding. |
| `metric-boundaries.md` | Separates raw candidate count, exact pattern count, semantic primitive count, and scored gadget count. |
| `parser-safety-and-fuzzing.md` | Defines parser safety invariants and the future malformed-input smoke/fuzz plan. |
| `contributor-maintainability.md` | Captures maintainability practices for a NASM-heavy public repository. |

## Design rule

A design note may introduce a future seam, but it must not imply that a future feature already exists. The public repository must remain clear about the difference between implemented behavior, planned behavior, and research hypotheses.
