# ADR 0035: Bounded Memory-Effect Side-Car and Authenticated Public Overlay

## Status

Accepted for the Sprint 10 Patch 049 implementation candidate. Authoritative native and Docker acceptance remains required.

## Context

Sprint 10 requires narrowly justified memory-read and memory-write primitives, explicit operand effects, controlled fixtures, and independent score decisions. The existing 112-byte `gadget_record` has no unused space large enough to represent durable address semantics without overloading raw scanner facts or changing the candidate stride.

Patch 048 also exposed two artifact-boundary weaknesses: generated fixture executables entered the tracked source state, and the public textual-content gate could exclude its own checker. A clean final tree was therefore insufficient unless the distributed final-file archive was authenticated and checked as a complete object.

## Decision

Patch 049 adds a dense 16-byte `memory_effect_record[]` keyed by candidate index. The record contains a packed descriptor and signed displacement. It represents:

- read or write direction,
- base register,
- optional index register,
- scale,
- displacement and known state,
- value register,
- access width,
- dereference state.

The first promoted families are limited to exact qword, base-plus-zero, no-index forms:

```text
REX.W + 89 /r + ModRM.mod=00 + ret   mov [base], value; ret
REX.W + 8b /r + ModRM.mod=00 + ret   mov value, [base]; ret
```

The matcher rejects SIB, RIP-relative, displacement-bearing, `rsp`-valued, `rsp`-destination, and 32-bit forms. Unsupported forms retain the strongest previously justified suffix, normally bare `ret`.

The public distribution artifact is a final-file overlay with a top-level authenticated manifest. Verification binds the caller-supplied outer SHA-256 to the archive, applies the ZIP metadata policy, scans every eligible text member including the checker itself, and reconciles every final path, digest, size, mode, and declared deletion. Local unified diffs remain application artifacts rather than public release artifacts.

## Consequences

- `gadget_record` remains 112 bytes.
- `candidate_evidence_record` remains 48 bytes.
- `memory_effect_record` is 16 bytes.
- Candidate capacity remains 4,096.
- The fixed command arena increases from 655,360 to 720,896 bytes.
- Schema remains `0.2.0`; memory fields are compatible additions.
- Memory candidates remain semantic-exact and decoder-unvalidated.
- Memory candidates remain unscored until a separately reviewed policy exists.
- No decoder, interpreter, helper process, thread runtime, or shared-library dependency is added.
- Generated fixture binaries are ignored and removed from tracked source.

## Rejected alternatives

### Expand `gadget_record`

Rejected because it changes the scanner-owned stride and increases every candidate record for facts needed only by memory-capable candidates.

### Encode memory semantics only in pattern IDs

Rejected because reporters and future decoder adapters need explicit operand facts, and pattern IDs are not a durable address-effect model.

### Add SIB, displacement, and RIP-relative forms immediately

Rejected because their operand model and false-positive surface are materially broader. They require additional controlled fixtures and validation before promotion.

### Make a decoder mandatory

Rejected because exact bounded forms are sufficient for this step and a mandatory decoder would alter the dependency and deployment profile without measured justification.

## Validation

Patch 049 requires:

```bash
make sprint10-memory-smoke
make json-effect-consistency-smoke
make schema-compat-smoke
make public-artifact-content-smoke
make public-overlay-verification-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

The final public overlay additionally requires:

```bash
PUBLIC_BUNDLE=/path/to/public-overlay.zip \
PUBLIC_BUNDLE_SHA256=<sha256> \
make public-overlay-verify
```

See the [Patch 049 validation plan](../sprints/sprint-10-patch-049-validation.md) and the [primitive effect model](../design/primitive-effect-model.md).
