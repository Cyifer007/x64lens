# Sprint 10 Plan

## Status

Active. Patch 046 establishes the ordered multi-pop and effect-fact foundation.

## Sprint goal

Expand semantic primitive coverage without collapsing suffix evidence, decoded
validity, side effects, score meaning, or the defensive deployment profile.

## Planned deliverables

- [x] Add the first selected multi-pop family with ordered controlled-register facts. Patch 046 recognizes two distinct System V argument-register pops before `ret`.
- [ ] Add conservative register-transfer patterns where source and destination
  are unambiguous.
- [ ] Add narrowly scoped memory-read and memory-write patterns only when
  operand semantics are justified.
- [ ] Complete controlled and clobbered register modeling. Patch 046 preserves
  controlled sets and exposes an empty clobber set; later families must
  populate justified clobbers.
- [ ] Complete side-effect modeling. Patch 046 exposes stack-read, pivot,
  syscall, and `ret imm16` facts; memory dereference facts remain open.
- [x] Add known/unknown stack-delta representation for the first expanded
  family.
- [x] Add a separate controlled source fixture and expected disassembly for the
  first new family, including an objdump-backed instruction-order oracle.
- [ ] Complete the fixture coverage table and per-family false-positive notes.
  Patch 046 documents conservative fallback; later families remain open.
- [ ] Add score entries only after semantic and side-effect facts are validated.
  Multi-pop remains deliberately unscored in Patch 046.
- [ ] Preserve candidate-index provenance and schema `0.2.x` compatibility.

## Patch 046 entry boundary

Patch 046 adds one conservative exact family:

```text
pop <arg-register>; pop <arg-register>; ret
```

The two registers must be distinct members of `rdi`, `rsi`, `rdx`, `rcx`,
`r8`, and `r9`. Unsupported or duplicate pairs fall back to the strongest
existing single-pop suffix. The implementation reuses reserved bytes in the
112-byte `gadget_record`, so candidate capacity and the fixed analysis arena do
not grow.

Patch 046 also adds compatible candidate fields for exact pop order, clobbers,
and represented side effects. It does not add memory primitives, register
transfers, decoder validation, parallel execution, or a new score rule.

## Recommended patch sequence

1. Patch 046: ordered two-pop foundation and effect-field contract.
2. Add conservative register-transfer patterns with explicit source,
   destination, controlled, and clobbered facts.
3. Add narrowly justified memory-read/write families and dereference facts.
4. Review scoring only after each semantic family and its effects pass fixtures.
5. Close Sprint 10 with corpus-facing fixture coverage and Sprint 11 handoff.

## Entry criteria from Sprint 9

- Schema `0.2.0` identity, completeness, and provenance gates pass.
- `gadgets` and `analyze` remain command-only parity matches.
- Capacity and malformed-input paths remain fail-closed with no partial output.
- The decoder-free one-worker core remains the reference profile.
- External disassembly is comparator evidence, not runtime authority.

## Acceptance criteria

- [ ] Every semantic mapping has a controlled fixture.
- [ ] Ambiguous patterns remain `unknown_candidate`.
- [ ] Exact suffix recognition and semantic promotion remain separate.
- [ ] Controlled, clobbered, stack, and memory effects are visible in records,
  text, and JSON when implemented.
- [ ] Score changes are documented and tested independently from classification.
- [ ] New metrics preserve provenance and schema `0.2.x` compatibility.
- [ ] No new mandatory runtime dependency is introduced.
- [ ] One-worker output remains deterministic and bounded.

## Decoder and parallelism boundary

Sprint 10 may mark which retained windows are eligible for future candidate-
scoped validation, but it does not make a decoder mandatory. It may add no
parallel default. New families must first be correct and deterministic in the
core profile.

## Out of scope

- JOP, COP, or SROP coverage.
- Symbolic execution.
- Exploit-chain generation.
- Unbounded pattern enumeration.
- Whole-image decoder integration.
- Default in-process multithreading.

## Handoff

Sprint 11 builds a reproducible compiler and hardening corpus that exercises the
expanded semantic and mitigation model. Sprints 12 and 13 measure optional
candidate-validation and worker profiles.
