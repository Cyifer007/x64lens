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
| `alignment` | Return or stack-adjustment suffix with alignment/spacing utility. | Implemented for `ret` and `ret imm16`. |
| `memory_write` | Writes data to memory with known operand roles. | Planned. |
| `memory_read` | Reads memory into a register with known operand roles. | Planned. |
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
- exact register-direct `mov r64,r64; ret` suffixes under the Patch 047 restrictions.

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

Planned bounded families:

- selected multi-pop sequences,
- additional unambiguous register transfers beyond the Patch 047 foundation,
- narrowly defined memory read/write templates.

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
score: unscored
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
side effects: register_write
score: unscored
```

Memory forms, 32-bit moves, self moves, and `rsp` participation are not promoted.
This is conservative semantic-exact evidence, not decoder validation of an
arbitrary backward window.
