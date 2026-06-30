# ADR 0014: Deterministic Mitigation Oracle Before Parser Refactoring

## Status

Accepted for Sprint 7 Patch 026.

## Context

The mitigation pipeline derives PIE, NX stack, RELRO, dynamic-linking, RWX-load, load-count, and executable-region facts from ELF64 program headers. The implementation is small, but the interaction among `ET_DYN`, `PT_GNU_STACK`, `PT_GNU_RELRO`, `PT_DYNAMIC`, and `PT_LOAD` flags creates a behavior surface that should not be protected only by a few compiler-dependent toy binaries.

Sprint 7 is also scheduled to consolidate overflow-sensitive parser arithmetic. Performing that refactor before the expected mitigation behavior is fixed would make it harder to distinguish a safety improvement from accidental inference drift.

## Decision

The repository will maintain a deterministic mitigation oracle composed of controlled ELF64 images generated in a temporary directory. The matrix covers:

- `ET_EXEC` and `ET_DYN`,
- missing, non-executable, and executable `PT_GNU_STACK`,
- `PT_GNU_RELRO`,
- `PT_DYNAMIC`,
- RX, RW, and RWX `PT_LOAD` segments,
- split code and data mappings,
- executable-region counts,
- overlapping executable segments as characterized current behavior,
- a combined hardening-evidence case.

For every valid case, the harness verifies the exact mitigation-summary and executable-region lines, absence of stderr, successful exit status, syntactically valid integrated JSON, and agreement between the text facts and the JSON mitigation object.

Five malformed program-header cases are exercised through `info`, `mitigations`, and `analyze`. Every command must return `EXIT_MALFORMED_ELF`, emit no stdout, and emit the stable malformed-ELF diagnostic exactly once.

ELF64 validation will reject invalid file-backed `PT_LOAD` ranges before any command reports target metadata. This preserves command-path consistency while the later shared-arithmetic refactor remains independently reviewable.

`make mitigation-matrix-smoke` is included in native and Docker aggregate validation.

## Consequences

### Positive

- Mitigation semantics become regression-tested independently of compiler defaults.
- Parser hardening can be reviewed against a fixed behavioral oracle.
- `info`, `mitigations`, and `analyze` agree on malformed file-backed load ranges.
- Generated fixtures remain temporary, while compact SHA-256-addressed evidence is retained locally.
- Overlapping load behavior is documented as characterized behavior rather than silently treated as deduplicated regions.

### Costs and limits

- The matrix proves behavior only for the represented combinations.
- `ET_DYN` remains a static PIE indicator and does not distinguish every shared-object case.
- RELRO presence does not yet distinguish partial from full RELRO.
- Passing the matrix is not a proof of parser memory safety.
- The fixture builder must evolve when the mitigation model gains new evidence classes.

## Follow-on work

Patch 027 corrects the oracle zero-region text expectation without changing runtime output. Patch 028 consolidates checked addition, multiplication, table-extent, and offset-plus-length validation while preserving this oracle and expanding malformed table-end overflow coverage. Later mitigation work should add GNU property notes, stack-canary evidence, and richer RELRO distinctions only with corresponding fixture rows and output-contract updates.
