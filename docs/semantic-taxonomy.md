# Semantic Primitive Taxonomy

The semantic taxonomy is one of the most important research components in x64lens. It defines how raw gadget candidates become useful exploit-primitive facts without overstating what the current scanner can prove.

## Semantic classes

| Class | Meaning | Sprint 4 status |
| ----- | ------- | --------------- |
| `arg_control` | Controls ABI argument registers such as `rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9`. | Implemented for exact supported pop patterns. |
| `syscall_num_control` | Controls `rax` for Linux syscall number setup. | Implemented for `pop rax; ret`. |
| `syscall_trigger` | Provides `syscall` instruction path. | Implemented for `syscall; ret`. |
| `stack_pivot` | Changes `rsp` or uses `leave; ret` style pivot. | Implemented for `leave; ret` and `pop rsp; ret`. |
| `memory_write` | Writes controlled register data into memory. | Future work. |
| `memory_read` | Reads from memory into register. | Future work. |
| `reg_transfer` | Moves or exchanges register values. | Future work. |
| `alignment` | Simple `ret` or `ret imm16` suffix useful for stack alignment or stack adjustment. | Implemented. |
| `clobber_heavy` | Useful but destroys many registers or stack values. | Future work. |
| `unknown_candidate` | Ret-terminated sequence not classified yet. | Preserved deliberately. |

## Initial x86_64 pattern table

| Pattern | Bytes | Sprint 4 classifier behavior |
| ------- | ----- | ---------------------------- |
| `ret` | `c3` | `alignment`, stack delta `8` |
| `ret imm16` | `c2 xx xx` | `alignment`, stack delta `8 + imm16` |
| `pop rax; ret` | `58 c3` | `syscall_num_control`, controls `rax`, stack delta `16` |
| `pop rcx; ret` | `59 c3` | `arg_control`, controls `rcx`, stack delta `16` |
| `pop rdx; ret` | `5a c3` | `arg_control`, controls `rdx`, stack delta `16` |
| `pop rbx; ret` | `5b c3` | exact pattern only, semantic remains `unknown_candidate` |
| `pop rsp; ret` | `5c c3` | `stack_pivot`, controls `rsp`, stack delta unknown |
| `pop rbp; ret` | `5d c3` | exact pattern only, semantic remains `unknown_candidate` |
| `pop rsi; ret` | `5e c3` | `arg_control`, controls `rsi`, stack delta `16` |
| `pop rdi; ret` | `5f c3` | `arg_control`, controls `rdi`, stack delta `16` |
| `pop r8; ret` | `41 58 c3` | `arg_control`, controls `r8`, stack delta `16` |
| `pop r9; ret` | `41 59 c3` | `arg_control`, controls `r9`, stack delta `16` |
| `pop r10; ret` through `pop r15; ret` | `41 5a c3` through `41 5f c3` | exact pattern only, semantic remains `unknown_candidate` until syscall-argument and callee-saved models are added |
| `syscall; ret` | `0f 05 c3` | `syscall_trigger`, stack delta `8` after syscall path returns |
| `leave; ret` | `c9 c3` | `stack_pivot`, controls `rsp`, stack delta unknown |

## Sprint 4 implemented semantic layer

Patch 015 adds `x64lens_classifier_apply_exact` in `src/classifier.asm`. The classifier runs after `patterns.asm` and before text reporting:

```text
scanner.asm -> patterns.asm -> classifier.asm -> report_text.asm
```

The classifier populates these existing `gadget_record` fields:

- `GADGET_SEMANTIC_CLASS`,
- `GADGET_REGS_CONTROLLED`,
- `GADGET_STACK_DELTA`,
- `GADGET_SIDE_EFFECT_FLAGS`.

It also extends `gadget_summary` with:

- `Semantic primitive count`,
- `unknown_candidate count`,
- per-class counts for implemented classes,
- register coverage bitmap.

The controlled fixture currently validates seven candidates:

| Pattern | Semantic class | Register facts | Stack delta |
| ------- | -------------- | -------------- | ----------- |
| `pop rdi; ret` | `arg_control` | `rdi` | `16` |
| `pop rsi; ret` | `arg_control` | `rsi` | `16` |
| `pop rdx; ret` | `arg_control` | `rdx` | `16` |
| `pop rax; ret` | `syscall_num_control` | `rax` | `16` |
| `leave; ret` | `stack_pivot` | `rsp` | unknown, encoded as `0` |
| `syscall; ret` | `syscall_trigger` | none | `8` |
| `ret imm16` | `alignment` | none | `8 + imm16` |

## Suffix pattern warning

Pattern labels are exact suffix labels, not full decoded instruction sequences. A raw candidate window can include extra bytes before the recognized suffix. The classifier may therefore treat `PATTERN_*` as trusted exact suffix evidence, but it must not assume the whole raw window has been decoded unless a future decoder record says so.

## Conservative classification rule

When a candidate does not match a supported semantic mapping, leave the semantic class as `unknown_candidate`. Overclassification is worse than underclassification because it corrupts primitive coverage metrics and later scoring.

Classifier rules:

- map only recognized `PATTERN_*` IDs to semantic classes,
- preserve `unknown_candidate`,
- separate suffix labels from full-window semantics,
- report primitive coverage separately from raw candidate counts,
- score only after semantic facts have been populated,
- avoid exploitability verdicts entirely.

## Future expansion

The taxonomy should eventually account for:

- side effects,
- clobbered registers,
- memory dereferences,
- richer stack delta modeling,
- bad byte constraints,
- CET/IBT impact,
- JOP/COP/SROP primitives,
- multi-instruction semantic equivalence,
- future decoder-backed validation.


## Sprint 5 fixture coverage

Patch 017 expands the controlled gadget fixture so the regression suite now exercises the implemented mappings for `pop rcx; ret`, `pop r8; ret`, `pop r9; ret`, and `pop rsp; ret` in addition to the earlier `rdi`, `rsi`, `rdx`, `rax`, `leave`, `syscall`, and `ret imm16` cases.

The semantic taxonomy remains separate from scoring. A semantic class explains the primitive type. A score is a later heuristic utility value assigned by `scoring.asm`.


## Analyze command semantic boundary

`analyze` reuses the same semantic classes as `gadgets`. It does not add new primitive meanings or infer exploitability. Unsupported or ambiguous candidates must continue to remain `unknown_candidate`.
