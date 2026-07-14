# Semantic Primitive Taxonomy

## Purpose

The taxonomy defines when a byte-level candidate can be promoted into an exploit-relevant primitive fact. The model is conservative because overclassification corrupts coverage metrics, score interpretation, and later defensive triage.

## Current classes

| Class | Meaning | Current status |
|---|---|---|
| `arg_control` | Controls supported System V argument registers. | Implemented for exact `pop rdi/rsi/rdx/rcx/r8/r9; ret` suffixes. |
| `syscall_num_control` | Controls `rax` for Linux syscall-number setup. | Implemented for `pop rax; ret`. |
| `syscall_trigger` | Provides a `syscall; ret` suffix. | Implemented. |
| `stack_pivot` | Makes `rsp` input-dependent or derives it through a pivot sequence. | Implemented for `pop rsp; ret` and `leave; ret`. |
| `alignment` | Return or stack-adjustment suffix with alignment/spacing utility. | Implemented for `ret` and `ret imm16`. |
| `memory_write` | Writes data to memory with known operand roles. | Planned. |
| `memory_read` | Reads memory into a register with known operand roles. | Planned. |
| `reg_transfer` | Moves or exchanges values between known registers. | Planned. |
| `clobber_heavy` | Potentially useful sequence with substantial side effects. | Planned as a qualifier or class after side-effect modeling. |
| `unknown_candidate` | Candidate without a justified semantic mapping. | Implemented and deliberately preserved. |

## Current exact patterns

The matcher recognizes:

- `ret`,
- `ret imm16`,
- `pop rax` through `pop r15` followed by `ret`,
- `leave; ret`,
- `syscall; ret`.

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
- unambiguous register transfers,
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
