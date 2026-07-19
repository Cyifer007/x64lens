# ADR 0032: Ordered Multi-Pop Foundation

## Status

Accepted for Sprint 10 Patch 046.

Related documentation: the
[Primitive Effect Model](../design/primitive-effect-model.md), the
[Sprint 10 Plan](../sprints/sprint-10-plan.md), the
[Patch 046 Validation Plan](../sprints/sprint-10-patch-046-validation.md), and
the [canonical roadmap](../roadmap-22-sprints.md).

## Context

Sprint 10 expands primitive coverage after Sprint 9 established report identity,
analysis completeness, candidate provenance, and a decoder-free reference
profile. The first expansion must prove that x64lens can represent ordered
multi-instruction effects without increasing the fixed analysis arena, inferring
semantics in reporters, or making external decoding a runtime dependency.

A register bitmap is sufficient to answer which registers are controlled, but it
cannot represent instruction order. Order matters for multi-pop suffixes because
stack values are consumed sequentially. The existing 112-byte `gadget_record`
had an unused final eight-byte tail, so a new allocation or record-size increase
was not required.

## Decision

1. Reuse the reserved final eight bytes of `gadget_record` for exact-pattern
   structural facts:

   ```text
   pattern_register_count
   pattern_register_order
   ```

   Register IDs are packed as four-bit values in execution order, least-
   significant nibble first.

2. Introduce one generic exact family:

   ```text
   pop <arg-register>; pop <arg-register>; ret
   ```

   Patch 046 recognizes only two distinct registers from the System V argument
   set `rdi`, `rsi`, `rdx`, `rcx`, `r8`, and `r9`.

3. Unsupported or duplicate two-pop prefixes do not receive the generic family.
   They fall back to the strongest existing single-pop suffix ending at the same
   return terminator.

4. `patterns.asm` owns exact byte recognition and ordered register metadata.
   `classifier.asm` independently validates those facts before assigning
   `arg_control`, the controlled-register bitmap, a 24-byte stack delta, and the
   represented `stack_read` side effect.

5. Text and JSON reporters render internal facts only. JSON adds compatible
   optional fields:

   ```text
   stack_pop_order
   clobbers
   side_effects
   ```

   Current-producer validation requires these fields, while the formal schema
   continues to accept earlier schema `0.2.0` reports that predate them.

6. Multi-pop candidates remain unscored in Patch 046. A score is added only
   after an independent review defines how added register control, stack cost,
   order, clobbers, and memory effects interact.
   Patch 051 later satisfies that gate and calibrates the current score to 95.

7. The historical 11-candidate fixture remains unchanged. A separate Sprint 10
   fixture proves the new family and conservative fallback behavior.

## Consequences

- `GADGET_RECORD_SIZE`, candidate capacity, and the 655,360-byte combined
  analysis arena remain unchanged.
- The default analyzer remains single-worker, statically linked, and free of a
  mandatory decoder or user-space runtime dependency.
- Ordered exact facts and unordered semantic coverage no longer need to be
  conflated.
- Future register-transfer and memory families can reuse the explicit effect
  model instead of adding formatter-specific interpretations.
- The generic family intentionally underclaims: exact suffix evidence still does
  not establish full instruction-sequence validity from every retained window
  start.

## Rejected alternatives

### Increase `gadget_record` size

Rejected for this step because the existing reserved tail is sufficient. A
larger stride would increase the fixed arena and change the current memory
contract without adding analytical value.

### Store order only in JSON

Rejected because reporters must not invent analysis facts. Order belongs in the
record pipeline before output.

### Decode the entire executable image

Rejected as a default-runtime requirement. Candidate-scoped decoder validation
remains an optional, separately measured future profile.

### Score multi-pop immediately

Rejected because a larger controlled-register set does not by itself define a
sound utility score. Scoring remains a downstream, evidence-backed policy.

## Follow-on

Patch 047 preserves this ordered-pop model, adds complete common-validator
coverage for all single-pop metadata entries, and introduces the separate exact
register-transfer relation documented in ADR 0033.
