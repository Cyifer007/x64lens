# Gadget Scoring Model

## Status

Patch 017 implements the first conservative scoring pass in `src/scoring.asm`.

Scoring now consumes internal fields populated by the scanner, exact pattern matcher, and semantic classifier:

- `GADGET_PATTERN_ID`,
- `GADGET_SEMANTIC_CLASS`,
- `GADGET_REGS_CONTROLLED`,
- `GADGET_STACK_DELTA`,
- `GADGET_SIDE_EFFECT_FLAGS`.

The text reporter renders `score: <n>` for each candidate. The JSON reporter emits numeric scores for scored candidates and `null` for unscored candidates.

## Formula

The long-term model remains:

```text
score = semantic_base
      + rare_primitive_bonus
      - clobber_penalty
      - memory_deref_penalty
      - stack_delta_penalty
      - bad_byte_penalty
      - uncertain_decode_penalty
```

Patch 017 implements a fixed first-pass table rather than the full formula. The fixed table already includes a small uncertainty penalty because the current classifier is exact-suffix based, not decoder-backed.

## Patch 017 implemented scores

| Pattern | Semantic class | Score | Rationale |
|---|---|---:|---|
| `pop rdi; ret` | `arg_control` | 90 | High-value argument-register control, exact suffix only. |
| `pop rsi; ret` | `arg_control` | 90 | High-value argument-register control, exact suffix only. |
| `pop rdx; ret` | `arg_control` | 90 | High-value argument-register control, exact suffix only. |
| `pop rcx; ret` | `arg_control` | 90 | Useful argument-register control, exact suffix only. |
| `pop r8; ret` | `arg_control` | 90 | Useful argument-register control, exact suffix only. |
| `pop r9; ret` | `arg_control` | 90 | Useful argument-register control, exact suffix only. |
| `pop rax; ret` | `syscall_num_control` | 85 | Useful syscall-number setup, exact suffix only. |
| `syscall; ret` | `syscall_trigger` | 85 | Useful syscall trigger, exact suffix only. |
| `leave; ret` | `stack_pivot` | 75 | Stack pivot with input-dependent stack delta. |
| `pop rsp; ret` | `stack_pivot` | 70 | Direct stack-pointer overwrite with higher uncertainty. |
| `ret` | `alignment` | 45 | Alignment or chain-spacing utility. |
| `ret imm16` | `alignment` | 40 | Alignment/stack adjustment with extra side effect. |

Unsupported exact patterns and `unknown_candidate` records remain unscored with score `0` internally and `null` in JSON.

## Scoring constraints

- Score only records with justified semantic classes.
- Keep `unknown_candidate` unscored.
- Preserve `scored_candidate_count` separately from raw, exact, semantic, and unknown counts.
- Preserve limitations in JSON output.
- Do not claim exploitability from score alone.

## Research warning

The scoring model is heuristic until validated through benchmark and analyst-utility experiments. A score means “relative utility under the current model,” not “this binary is exploitable.”

## Future scoring work

Later sprints should add:

- bad-byte penalties,
- clobber penalties,
- memory dereference penalties,
- full decoder confidence adjustments,
- mitigation-aware score interpretation,
- score calibration against baseline tools and controlled exploit-development exercises.


## Analyze command scoring boundary

`analyze` does not introduce a separate scoring model. It reports the same candidate scores produced for `gadgets`, using the same internal records and score values. This keeps score interpretation stable across command names.
