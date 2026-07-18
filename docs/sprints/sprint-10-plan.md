# Sprint 10 Plan

## Status

Active. Patches 046 through 048 establish ordered multi-pop, exact register-transfer, and exact positive aligned stack-adjust effects. Patch 049 adds the first bounded qword memory read/write families through a fixed candidate-index side-car and hardens authenticated public final-file distribution.

Related documentation: [ADR 0032](../adr/0032-ordered-multi-pop-foundation.md),
[ADR 0033](../adr/0033-exact-register-transfer-effects.md), the
[Primitive Effect Model](../design/primitive-effect-model.md), the
[Patch 047 Validation Plan](sprint-10-patch-047-validation.md), the
[Patch 048 Validation Plan](sprint-10-patch-048-validation.md), the
[Patch 049 Validation Plan](sprint-10-patch-049-validation.md),
[ADR 0035](../adr/0035-bounded-memory-effect-sidecar-and-authenticated-public-overlay.md), and the [canonical roadmap](../roadmap-18-sprints.md).

## Sprint goal

Expand semantic primitive coverage without collapsing suffix evidence, decoded
validity, side effects, score meaning, or the defensive deployment profile.

## Planned deliverables

- [x] Add the first selected multi-pop family with ordered controlled-register facts. Patch 046 recognizes two distinct System V argument-register pops before `ret`.
- [x] Add the first conservative register-transfer family with unambiguous
  source and destination roles. Patch 047 recognizes distinct non-`rsp`
  register-direct 64-bit moves before `ret`.
- [x] Add the first narrowly scoped memory-read and memory-write patterns. Patch 049 recognizes only qword base-plus-zero, no-index `mov` forms with explicit direction, base, value register, width, dereference, and known zero displacement.
- [x] Complete controlled and clobbered register modeling for implemented Sprint 10 families. Patch 049 memory writes clobber no GPR; memory reads clobber the destination register; neither infers external control.
- [ ] Complete side-effect modeling. Patch 046 exposes stack-read, pivot,
  syscall, and `ret imm16` facts; Patch 047 adds `register_write`; Patch 048
  adds `stack_adjust` and `flags_write`; Patch 049 adds explicit `memory_read`, `memory_write`, and dereference facts.
- [x] Add known/unknown stack-delta representation for the first expanded
  family.
- [x] Add a separate controlled source fixture and expected disassembly for the
  first new family, including an objdump-backed instruction-order oracle.
- [ ] Complete the fixture coverage table and per-family false-positive notes.
  Patch 046 documents conservative fallback; later families remain open.
- [ ] Add score entries only after semantic and side-effect facts are validated.
  Multi-pop remains deliberately unscored in Patch 046.
- [x] Preserve candidate-index provenance and schema `0.2.x` compatibility for the Patch 046 and Patch 047 additions.

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
2. Patch 047: add the first exact register-transfer family and harden all
   single-pop effect relations.
3. Patch 048: correct transfer/reporting and public-artifact gates, add the first exact positive aligned stack-adjust family, and harden bare-return and terminator relationships.
4. Patch 049: add a fixed memory-effect side-car, promote only base-plus-zero qword moves, remove generated tracked fixtures, and authenticate the final-file public overlay.
5. Review scoring only after each semantic family and its effects pass fixtures.
6. Close Sprint 10 with corpus-facing fixture coverage, broader per-family false-positive notes, and Sprint 11 handoff.

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

## Patch 047 boundary

Patch 047 recognizes exact `mov r64,r64; ret` register-direct suffixes with
explicit source, destination, destination-clobber, `register_write`, and known
return stack-delta facts. The family remains unscored. It excludes self moves,
`rsp`, memory operands, and 32-bit forms and preserves their strongest existing
fallback.

The patch also adds common-validator regression coverage for all 16 single-pop
patterns and mixed legacy/REX multi-pop order so per-candidate contradictions
cannot hide behind aggregate coverage.

## Patch 048 boundary

Patch 048 recognizes only `48 83 c4 imm8 c3` with a positive nonzero eight-byte-aligned immediate. It records alignment semantics, total stack delta, `stack_adjust`, and `flags_write`, while leaving the family unscored. Unsupported arithmetic forms remain bare-return fallbacks.

The same patch corrects the missing JSON object delimiters, strengthens common exact-pattern and return-effect validation, supports retained objdump transcripts in the transfer oracle, and adds bounded textual-content inspection for public source ZIPs. It does not add memory semantics, a decoder, a worker runtime, or per-candidate storage.

## Patch 049 boundary

Patch 049 recognizes only exact `REX.W + 89/8b + ModRM.mod=00 + ret` forms whose memory operand uses one non-special base register, no SIB, no index, no displacement, and qword width. It excludes RIP-relative, `rsp`/`r12` SIB, `rbp`/`r13` displacement-required, displacement-bearing, `rsp`-valued, and 32-bit forms.

Memory facts are materialized after exact matching and classification into a 16-byte dense side-car keyed by candidate index. The raw candidate record and evidence record remain unchanged. The fixed arena grows by 64 KiB at maximum capacity; candidate capacity remains 4,096. The family remains unscored and decoder-unvalidated.

Patch 049 also establishes authenticated public final-file overlays as the release-safe patch distribution form. Local unified diffs remain valid application artifacts but are not the public release surface because deleted lines may retain text absent from the final tree.
