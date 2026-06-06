# ADR 0002: Hybrid Architecture

## Status

Accepted.

## Decision

Use a hybrid architecture:

1. Speed-first assembly scanning engine.
2. Semantic exploitability value layer.

## Rationale

A speed-only tool risks becoming a narrower duplicate of existing gadget scanners. A semantics-only tool risks becoming too abstract and hard to measure. The hybrid design creates both benchmarkable performance claims and deeper research value.

## Consequences

The scanner must stay modular and measurable. The semantic layer must operate on stored facts, not ad hoc printed strings.
