# Semantic Primitive Taxonomy

## Purpose

The taxonomy defines when a byte-level candidate can be promoted into an exploit-relevant primitive fact. The model is conservative because overclassification corrupts coverage metrics, score interpretation, and later defensive triage.

## Current classes

| Class | Meaning | Current status |
|---|---|---|
| `arg_control` | Controls supported System V argument registers. | Implemented for exact single-pop argument suffixes and the Patch 046 two-distinct-argument-pop family. |
| `syscall_num_control` | Controls `rax` for Linux syscall-number setup. | Implemented for `pop rax; ret`. |
| `syscall_trigger` | Provides a `syscall; ret` suffix. | Implemented. |
| `stack_pivot` | Makes `rsp` input-dependent or derives it through a pivot sequence. | Implemented for `pop rsp; ret` and `leave; ret`. |
| `alignment` | Return or exact bounded stack-adjustment suffix with alignment/spacing utility. | Implemented for `ret`, `ret imm16`, and the Patch 048 positive aligned `add rsp, imm8; ret` family. |
| `memory_write` | Writes a qword register value to a represented base-plus-zero memory address. | Implemented for the Patch 049 exact bounded family; Patch 050 completes return-stack effects. |
| `memory_read` | Reads a qword from a represented base-plus-zero memory address into a register. | Implemented for the Patch 049 exact bounded family; Patch 050 completes return-stack effects. |
| `reg_transfer` | Transfers a value between known registers with explicit source and destination roles. | Implemented for the Patch 047 exact register-direct 64-bit move family. |
| `clobber_heavy` | Potentially useful sequence with substantial side effects. | Planned as a qualifier or class after side-effect modeling. |
| `unknown_candidate` | Candidate without a justified semantic mapping. | Implemented and deliberately preserved. |

## Current exact patterns

The matcher recognizes:

- `ret`,
- `ret imm16`,
- `pop rax` through `pop r15` followed by `ret`,
- `leave; ret`,
- `syscall; ret`,
- `pop <arg-register>; pop <arg-register>; ret` for two distinct supported System V argument registers,
- exact register-direct `mov r64,r64; ret` suffixes under the Patch 047
  restrictions,
- exact `add rsp, imm8; ret` suffixes with a positive, nonzero,
  eight-byte-aligned immediate under the Patch 048 restrictions,
- exact qword base-plus-zero memory reads and writes followed by `ret` under the Patch 049 restrictions.

Only the currently documented subset receives semantic promotion. For example, `pop rbx; ret`, `pop rbp; ret`, and several extended-register patterns remain exact observations but may remain `unknown_candidate` until their semantic role and score policy are defined.

## Evidence boundary

A pattern label describes the exact suffix ending at the terminator. It does not prove that the full backward byte window is one decoded instruction sequence.

Current evidence flow:

```text
raw candidate
  -> exact suffix
  -> semantic-exact rule or unknown_candidate
```

Future flow:

```text
raw candidate
  -> exact suffix
  -> optional decoder record
  -> semantic-exact or semantic-decoded rule
```

Reports must preserve the evidence source.

## Conservative promotion rule

Promote a candidate only when the available evidence justifies:

- primitive class,
- controlled registers,
- clobbered registers where relevant,
- stack effect or explicit uncertainty,
- memory effect where relevant,
- side-effect flags.

Otherwise preserve `unknown_candidate`.

## Stack-delta rules

- `ret`: known delta `8`.
- supported `add rsp, imm8; ret`: known delta `imm8 + 8` for positive aligned immediates.
- `ret imm16`: known delta `8 + imm16` only when the terminator bytes are the intended suffix evidence.
- `pop reg; ret`: known suffix delta `16` for supported non-pivot registers.
- `pop rsp; ret` and `leave; ret`: input-dependent, represented as unknown.

Schema output must distinguish a known zero from an unknown value.

## Sprint 10 expansion gate

Every new family requires:

1. controlled source fixture,
2. expected disassembly,
3. evidence kind,
4. semantic mapping,
5. control and clobber facts,
6. stack and memory effects,
7. text and JSON validation,
8. false-positive notes,
9. independent score decision.

Further bounded expansion, if retained after the Patch 053 capability
reassessment, may include:

- additional multi-pop sequences beyond the current two-argument-register domain,
- additional unambiguous register-transfer forms,
- broader memory addressing only after index, scale, displacement, width, role, and uncertainty facts remain explicit.

JOP, COP, SROP, symbolic equivalence, and broad instruction-sequence reasoning remain outside the pre-`v0.1.0` core unless the research scope changes.

## Metric rule

Do not treat these as interchangeable:

```text
raw candidate
exact pattern
semantic-exact candidate
decoder-validated candidate
semantic-decoded candidate
scored candidate
```

See [`design/metric-boundaries.md`](design/metric-boundaries.md) and [`design/evidence-provenance-model.md`](design/evidence-provenance-model.md).

## Exploitability rule

Primitive availability does not establish vulnerability or exploitability. Any strategy interpretation assumes an independent vulnerability, reachable control, required disclosures, and relevant runtime conditions.

## Sprint 9 closeout constraint

Sprint 10 expands this taxonomy from the semantic-exact evidence surface established in Sprint 9. Decoder-backed semantic promotion remains optional and must retain its evidence source. Parallel execution may change scheduling only; it may not change classification rules, candidate order, or unknown preservation.

## Sprint 10 Patch 046 ordered multi-pop rule

The generic multi-pop family is promoted only when both exact pops control
distinct registers in `rdi`, `rsi`, `rdx`, `rcx`, `r8`, or `r9`.

Reported facts:

```text
semantic class: arg_control
controlled registers: both popped registers
stack pop order: exact execution order
stack delta: 24 bytes
side effects: stack_read
clobbers: none represented
score at Patch 046 boundary: unscored
current score after Patch 051: 95
```

Duplicate pairs and pairs with either pop outside the supported argument-
register set are not promoted as the generic family. The strongest existing
single-pop suffix immediately before `ret`
remains available. This fallback is deliberate underclassification rather than
an attempt to describe unsupported preceding instructions.

## Sprint 10 Patch 047 register-transfer rule

The exact family is promoted only for distinct, non-`rsp`, register-direct
64-bit moves using opcode `89 /r` or `8b /r` under `REX.W`, immediately followed
by `ret`.

Reported facts:

```text
semantic class: reg_transfer
source/destination: exact operand roles
controlled registers: none independently asserted
clobbered registers: destination
stack delta: 8 bytes
side effects: stack_read, register_write
score: unscored
```

Memory forms, 32-bit moves, self moves, and `rsp` participation are not promoted.
This is conservative semantic-exact evidence, not decoder validation of an
arbitrary backward window.

## Sprint 10 Patch 048 stack-adjust rule

The `alignment` class now includes the exact positive aligned stack-adjust suffix `48 83 c4 imm8 c3`. Promotion requires `imm8` to be nonzero, positive under sign extension, and divisible by eight.

Reported facts:

```text
semantic class: alignment
controlled registers: none
clobbered general-purpose registers: none
stack delta: imm8 + 8 bytes
side effects: stack_read, stack_adjust, flags_write
score at Patch 048 boundary: unscored
current score after Patch 051: 35
```

Zero, negative, unaligned, wrong-register, subtraction, and memory forms are not promoted. Arithmetic flags are recorded as an effect rather than silently omitted. Exact-suffix evidence does not prove the complete backward window decodes from its earliest byte.

## Patch 049 memory promotion rule

A memory candidate is promoted only when exact bytes establish:

- qword width through `REX.W`;
- opcode `89 /r` or `8b /r`;
- register/memory direction;
- `ModRM.mod=00`;
- one represented base register;
- no SIB or index;
- known zero displacement;
- no `rsp` value or destination;
- immediate `ret` terminator.

Memory writes have no GPR clobber. Memory reads clobber only the value destination. Neither family infers control of the address or memory contents. Other forms preserve fallback semantics.


## Patch 050 effect-completion rule

Every currently supported semantic candidate that ends in `ret` or `ret imm16` records `stack_read` because the suffix consumes a return address. This is independent from whether the preceding operation is a pop, transfer, stack adjustment, syscall, pivot, memory read, or memory write.

Additional current facts:

- `syscall; ret` clobbers `rcx` and `r11` and records `syscall` plus `register_write`;
- `leave; ret` controls the pivot relationship through `rsp`, clobbers `rbp`, and retains unknown stack delta;
- a memory read clobbers its destination register; a memory write does not clobber a modeled GPR;
- exact family promotion follows the strongest implemented rule, so the transfer fixture's memory forms are memory candidates rather than stale transfer fallbacks.

The complete fixture, effect, score-disposition, and false-positive matrix is maintained in [`design/sprint10-family-coverage.md`](design/sprint10-family-coverage.md).

## Patch 051 architectural-effect and score rule

Every current exact pattern now has a candidate-index architectural-effect
record. Exact-only pops outside the supported semantic-role catalog remain
`unknown_candidate` but retain deterministic GPR and stack effects. The new
record does not create a semantic class and does not upgrade exact-suffix
provenance to decoder validity.

Ordered two-pop argument control is scored 95 after its exact order, controls,
stack cost, register writes, return control flow, and model-complete state
validate. Positive aligned stack adjustment is scored 35 after its immediate,
stack delta, condition-flag writes, return control flow, and complete effect
model validate. Register transfer and memory access remain unscored.

## Sprint 10 Patch 053 semantic capability gates

Patch 053 adds no primitive family. Sprint 13 must decide the release-facing
semantic treatment of the eight exact single-pop GPR forms that remain
`unknown_candidate` and the Linux syscall `r10` argument role. Diagnostic
coverage evidence may justify additional bounded ROP families, but only when
operand roles, effects, fixtures, false-positive boundaries, provenance, and
score/null policy fit the current record model.

Full disassembly, JOP, COP, SROP, symbolic execution, chain generation, other
architectures, and other file formats remain outside the first-release core.
