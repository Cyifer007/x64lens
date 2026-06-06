# ADR 0003: Program Headers First

## Status

Accepted.

## Decision

Use program headers as the authoritative executable memory model.

## Rationale

The loader maps segments, not sections. Exploitability analysis should therefore prioritize `PT_LOAD` segments and permission flags.

## Consequences

Section headers will be used for labels and human readability, not as the first source of truth for runtime mapping.
