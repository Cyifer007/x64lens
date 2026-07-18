# Primitive Effect Model

## Purpose

Sprint 10 expands semantic coverage by representing what an exact suffix does,
not merely by assigning it a label. This document defines the current ordered
register, clobber, stack, and side-effect facts that pattern, classifier,
scoring, and reporting modules share.

Related documentation: [ADR 0032](../adr/0032-ordered-multi-pop-foundation.md),
[ADR 0033](../adr/0033-exact-register-transfer-effects.md),
[ADR 0034](../adr/0034-bounded-stack-adjust-and-public-artifact-content-policy.md),
the
[Sprint 10 Plan](../sprints/sprint-10-plan.md), the
[Patch 047 Validation Plan](../sprints/sprint-10-patch-047-validation.md), the
[Patch 048 Validation Plan](../sprints/sprint-10-patch-048-validation.md), and
the [canonical roadmap](../roadmap-18-sprints.md).

## Fact layers

```text
raw candidate window
  -> exact pattern and ordered structural facts
  -> conservative semantic class
  -> controlled/clobbered/stack/side-effect facts
  -> optional score
  -> text and JSON adapters
```

Each layer remains independently visible. Exact suffix recognition does not
prove full-window decode validity, and semantic facts do not imply a score.

## Ordered control and register coverage

Two different representations are required:

- `stack_pop_order` records exact pop order for the recognized suffix.
- `controls` records the unordered set of registers controlled by the semantic
  rule.

For example:

```text
pop rdi; pop rsi; ret
```

produces:

```json
"stack_pop_order": ["rdi", "rsi"],
"controls": ["rsi", "rdi"]
```

The `controls` array follows canonical bitmap order; `stack_pop_order` preserves
execution order. Consumers must not treat array order in `controls` as execution
order.

## Current Patch 046 family

Patch 046 recognizes exactly two distinct System V argument-register pops before
`ret`. Supported registers are:

```text
rdi rsi rdx rcx r8 r9
```

The family is represented as:

```text
pattern: pop reg; pop reg; ret
semantic_class: arg_control
stack_delta: 24
side_effects: [stack_read]
score: null
```

A duplicate pair, or a pair with either pop outside the supported argument-
register set, does not receive the generic family. The strongest existing
single-pop suffix immediately before `ret` remains available. This preserves a
justified suffix fact without overpromoting the longer byte sequence.

## Clobber facts

`clobbers` is a separate register set from `controls`.

- A controlled register receives a stack-sourced value under the represented
  primitive model; who controls that value is external runtime context.
- A clobbered register is modified without a justified controlled value.

Patch 046 introduces the machine-readable field. Patch 047 populates the
destination register as a clobber for an exact register transfer because that
register is overwritten without independent evidence that the source value is
externally controlled. Future memory families must define clobbers before
semantic promotion.

## Side-effect facts

Current represented side-effect identifiers are:

| Identifier | Meaning |
|---|---|
| `stack_read` | The suffix consumes one or more values from the stack. |
| `stack_pivot` | The suffix makes subsequent stack state input-dependent. |
| `syscall` | The suffix executes the `syscall` instruction. |
| `ret_imm16` | The return applies the encoded immediate stack adjustment. |
| `register_write` | The suffix writes a represented destination register. |
| `stack_adjust` | The suffix changes the stack pointer by a represented constant amount. |
| `flags_write` | The suffix modifies condition-code flags; flags are outside the general-purpose-register clobber bitmap. |

These are modeled facts, not an exhaustive microarchitectural description.
Unknown or unmodeled effects must not be inferred by reporters.

Patch 050 completes the current return-ending effect baseline:

- every supported semantic `ret` or `ret imm16` candidate includes
  `stack_read` for the consumed return address;
- `syscall; ret` includes `syscall`, `register_write`, and `stack_read`, with
  `rcx` and `r11` recorded as architectural clobbers;
- `leave; ret` includes `stack_pivot`, `register_write`, and `stack_read`, with
  `rbp` recorded as a clobber and unknown stack delta;
- memory and transfer effects remain additive to the final return stack read.

A historical same-schema report may lack these strengthened effects and remain
consumable. Current producer validation requires the completed relationships.

## Stack delta

Known stack deltas are expressed in bytes. Patch 046 adds:

```text
two pops + ret = 8 + 8 + 8 = 24 bytes
```

Input-dependent pivots continue to use the existing unknown representation.

## Scoring boundary

The scoring engine consumes evidence-qualified semantic facts but remains an
independent module. The first multi-pop family intentionally has `score: null`. A later
score rule must consider at least:

- number and role of controlled registers;
- execution order;
- known stack cost;
- clobbers;
- memory dereferences;
- evidence kind and decode confidence.

No reporter or validator may invent a score from the pattern name.

## Future extension rules

Register-transfer and memory families must:

1. retain exact pattern identity separately from semantic class;
2. populate source, destination, controlled, and clobbered facts explicitly;
3. represent memory read/write and dereference uncertainty;
4. keep unknown stack effects explicit;
5. add controlled fixtures before promotion;
6. preserve schema `0.2.x` compatibility or declare a version transition;
7. remain deterministic in the dependency-free one-worker profile.

## Patch 047 register-transfer family

Patch 047 recognizes exact register-direct 64-bit moves ending in `ret`:

```text
REX.W + 89 /r + ModRM.mod=3 + ret
REX.W + 8b /r + ModRM.mod=3 + ret
```

The compact pattern metadata stores destination then source. JSON emits:

```json
"register_transfer": {
  "source": "rax",
  "destination": "rdi"
},
"controls": [],
"clobbers": ["rdi"],
"side_effects": ["stack_read", "register_write"],
"stack_delta": 8,
"score": null
```

The empty `controls` array is deliberate. A register transfer relates two
register values but does not establish who controls the source at runtime.
Self moves, `rsp` participation, memory operands, and 32-bit moves remain
conservative `ret` fallbacks.

## Patch 048 stack-adjust family

Patch 048 recognizes the exact suffix:

```text
48 83 c4 imm8 c3    add rsp, imm8; ret
```

Promotion is limited to positive, nonzero, eight-byte-aligned immediates. The candidate reports no controlled or general-purpose-register clobber facts, a known total stack delta of `imm8 + 8`, and these side effects:

```json
"side_effects": ["stack_read", "stack_adjust", "flags_write"]
```

`stack_adjust` records the explicit stack-pointer movement. `flags_write` records that integer addition modifies condition flags. Condition flags are not members of the current general-purpose-register clobber bitmap, so the separate effect prevents a false implication that the suffix has no other represented architectural effects.

The family remains unscored. Zero, negative, unaligned, wrong-register, subtraction, and memory forms retain the strongest existing fallback. Full-sequence validity remains unknown until decoder-backed evidence exists.

## Patch 049 bounded memory-effect family

Patch 049 adds a dense 16-byte `memory_effect_record[]` keyed by candidate index. The side-car records direction, base, optional index, scale, signed displacement, displacement-known state, value register, width, and dereference state without changing the 112-byte raw candidate record.

The first exact families are restricted to qword, base-plus-zero, no-index moves:

```text
mov [base], value; ret
mov value, [base]; ret
```

For a memory write, `controls` and GPR `clobbers` remain empty, stack delta is 8, and the side effect is `memory_write`. For a memory read, `controls` remains empty, the destination register is a clobber, stack delta is 8, and side effects are `memory_read` plus `register_write`. Neither relation proves that the address or memory contents are externally controlled.

SIB, RIP-relative, displacement-bearing, `rsp`-valued, `rsp`-destination, and 32-bit forms remain conservative fallbacks. Future displacement or indexed families must reuse the same side-car fields and add exact fixtures rather than infer missing address facts in reporters.

Memory candidates remain unscored. A score requires reviewed dereference, address-control, clobber, and uncertainty factors.


## Patch 050 cross-family and score boundary

The transfer fixture now deliberately spans three semantic families:

```text
4 register transfers
1 bounded memory write
1 bounded memory read
4 bare-return fallbacks
```

This is a fixture-quality rule rather than a new runtime feature. A candidate is
validated according to its strongest implemented exact family, even when the
fixture was originally introduced for a narrower family.

All new Sprint 10 families remain unscored. The completed effect model supplies
the facts needed for a later score review, but it does not itself establish
relative utility. The Patch 051 architecture/capability review must decide
whether stack cost, clobbers, dereference risk, flag writes, and evidence
uncertainty justify score entries before Sprint 10 closes.

The authoritative human-readable family matrix is
[`sprint10-family-coverage.md`](sprint10-family-coverage.md); the corresponding
machine-readable gate is `tests/expected/sprint10-family-coverage.json`.
