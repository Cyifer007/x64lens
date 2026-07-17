# ADR 0034: Bounded Stack Adjustment and Public Artifact Content Policy

## Status

Accepted for Sprint 10 Patch 048 validation.

## Context

Sprint 10 expands exact semantic coverage while preserving the dependency-free,
one-worker reference runtime. Patch 046 added ordered two-pop facts and Patch
047 added exact register-direct transfer facts. Review of the Patch 047
candidate identified two independent gaps:

1. the JSON reporter referenced compact object delimiters that were not defined;
2. repository-tree hygiene did not prevent deleted private-process wording from
   remaining recoverable inside a distributed unified diff.

The same review confirmed that register-transfer classification, capacity,
mapping, cleanup, and native/Docker fact parity behaved as designed after the
missing delimiters were supplied. The next forward primitive should therefore
reuse the existing record model rather than broaden parser, decoder, or worker
scope.

## Decision

### Correct the Patch 047 foundation

Patch 048 defines the missing compact JSON object delimiters and strengthens
candidate-level validation for exact terminator, bare-return control, and stack
facts. The register-transfer family remains otherwise unchanged.

### Add one exact stack-adjust family

The exact matcher recognizes this suffix:

```text
48 83 c4 imm8 c3    add rsp, imm8; ret
```

Promotion requires the sign-extended immediate to be:

- positive and nonzero;
- below `0x80`;
- divisible by eight.

The classifier records:

```text
semantic class: alignment
controls: none
clobbers: none
stack delta: imm8 + 8
stack delta known: yes
side effects: stack_adjust, flags_write
score: unscored
```

The `flags_write` effect records arithmetic condition-code modification; condition flags are outside the general-purpose-register clobber bitmap. Zero, negative, unaligned, wrong-register, subtraction, memory, and other forms
remain the strongest previously supported suffix, normally bare `ret`.

This family reuses existing pattern, semantic, stack-delta, side-effect, and
provenance fields. It adds no candidate-record field, no side-car allocation,
and no runtime dependency. The `gadget_record` remains 112 bytes, the evidence
record remains 48 bytes, the candidate capacity remains 4096, and the combined
analysis arena remains 655360 bytes.

### Separate metadata safety from content safety

Public ZIP acceptance has two independent gates:

1. the metadata-only archive policy validates paths, headers, file types,
   comments, extras, and portability without extraction;
2. the bounded public-content policy reads textual member payloads in memory and
   rejects private paths, host identities, attachment-history names, and
   private-process wording, including deleted lines in `.patch` and `.diff`
   members.

A final-file public overlay can pass both gates. A local application package may
contain the textual patch and private project context, but it is explicitly not
a public release bundle.

## Alternatives considered

### Grow the candidate record

Rejected. The new fact fits existing fixed fields. Growing every candidate
would increase fixed arena bytes or require a capacity change without adding a
new irreducible concept.

### Add a decoder-backed stack-adjust rule

Deferred. Exact suffix evidence is sufficient for the narrow current claim.
Full-sequence validity remains unknown and visible in candidate provenance.

### Recognize all `add rsp, imm8` values

Rejected. Negative, zero, and byte-granular adjustments have materially
different semantics and are easier to misinterpret. Broader treatment requires
separate taxonomy and score review.

### Treat metadata-only ZIP inspection as sufficient

Rejected. Safe member metadata does not constrain textual content inside a
valid public archive. Content inspection is a separate bounded release gate.

## Consequences

- Common positive aligned stack-adjust suffixes become machine-readable.
- Historical, multi-pop, and register-transfer fixtures remain unchanged.
- Stack-adjust candidates remain unscored until utility and side-effect policy
  are reviewed independently.
- The default analyzer remains freestanding, decoder-free, single-worker, and
  bounded.
- Public source overlays can be validated without distributing a textual patch
  that preserves deleted private-process wording.
- The local application package and public source overlay have distinct roles
  and must not be relabeled as one another.

## Validation

Required focused gates:

```bash
make sprint10-register-transfer-smoke
make sprint10-stack-adjust-smoke
make json-effect-consistency-smoke
make schema-compat-smoke
make public-artifact-content-smoke
PUBLIC_BUNDLE=/path/to/public-overlay.zip make public-bundle-content-check
```

The complete native and Docker aggregates remain required before acceptance.
