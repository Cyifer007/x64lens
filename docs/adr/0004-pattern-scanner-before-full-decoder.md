# ADR 0004: Pattern Scanner Before Full Decoder

## Status

Accepted.

## Decision

Use a pattern-based scanner during the first semester instead of implementing a full x86_64 decoder.

## Rationale

A full decoder would dominate the semester and increase implementation risk. A pattern scanner is sufficient to build a working research scaffold and validate the semantic primitive model.

## Future migration path

The scanner must produce candidate windows that can later be passed to a full decoder. The classifier should evolve toward abstract instruction facts rather than raw byte-only assumptions.
