# Semantic Primitive Taxonomy

The semantic taxonomy is one of the most important research components in x64lens.

| Class | Meaning |
| ----- | ------- |
| `arg_control` | Controls ABI argument registers such as `rdi`, `rsi`, `rdx`, `rcx`, `r8`, `r9` |
| `syscall_num_control` | Controls `rax` for Linux syscall number setup |
| `syscall_trigger` | Provides `syscall` instruction path |
| `stack_pivot` | Changes `rsp` or uses `leave; ret` style pivot |
| `memory_write` | Writes controlled register data into memory |
| `memory_read` | Reads from memory into register |
| `reg_transfer` | Moves or exchanges register values |
| `alignment` | Simple `ret` or padding useful for stack alignment |
| `clobber_heavy` | Useful but destroys many registers or stack values |
| `unknown_candidate` | Ret-terminated sequence not classified yet |

## Initial x86_64 pattern table

| Pattern | Bytes |
| ------- | ----- |
| `ret` | `c3` |
| `ret imm16` | `c2 xx xx` |
| `pop rax; ret` | `58 c3` |
| `pop rcx; ret` | `59 c3` |
| `pop rdx; ret` | `5a c3` |
| `pop rbx; ret` | `5b c3` |
| `pop rsp; ret` | `5c c3` |
| `pop rbp; ret` | `5d c3` |
| `pop rsi; ret` | `5e c3` |
| `pop rdi; ret` | `5f c3` |
| `pop r8; ret` through `pop r15; ret` | `41 58 c3` through `41 5f c3` |
| `syscall` | `0f 05` |
| `leave; ret` | `c9 c3` |
| `nop; ret` | `90 c3` |

## Future expansion

The taxonomy should eventually account for:

- side effects,
- clobbered registers,
- memory dereferences,
- stack delta,
- bad byte constraints,
- CET/IBT impact,
- JOP/COP/SROP primitives,
- multi-instruction semantic equivalence.


## Sprint 3 raw candidate and exact pattern layer

Sprint 3 intentionally stops before semantic classification. The `gadgets` command currently reports raw terminator-centered byte windows and exact byte-template pattern labels with these fields:

- terminator virtual address,
- terminator file offset,
- bounded byte-window start,
- byte-window length,
- terminator type,
- exact pattern label,
- raw bytes.

Patch 011 adds exact `PATTERN_*` IDs for simple templates such as `pop rdi; ret`, `leave; ret`, and `syscall; ret`. All Sprint 3 candidates still use `SEM_UNKNOWN_CANDIDATE` internally. Sprint 4 will map exact pattern IDs into semantic classes such as `arg_control`, `syscall_trigger`, and `stack_pivot`.

## Sprint 4 classifier mapping target

Sprint 4 should translate exact pattern IDs into semantic facts conservatively:

| Exact pattern family | Semantic class | Controlled registers | Initial stack delta model |
| -------------------- | -------------- | -------------------- | ------------------------- |
| `ret` | `alignment` | none | 8 |
| `ret imm16` | `alignment` | none | `8 + imm16` later, unknown until immediate extraction is modeled |
| `pop rdi; ret` | `arg_control` | `rdi` | 16 |
| `pop rsi; ret` | `arg_control` | `rsi` | 16 |
| `pop rdx; ret` | `arg_control` | `rdx` | 16 |
| `pop rcx; ret` | `arg_control` | `rcx` | 16 |
| `pop r8; ret` | `arg_control` | `r8` | 16 |
| `pop r9; ret` | `arg_control` | `r9` | 16 |
| `pop rax; ret` | `syscall_num_control` | `rax` | 16 |
| `pop rsp; ret` | `stack_pivot` | `rsp` | special case |
| `leave; ret` | `stack_pivot` | `rsp`, `rbp` relationship | special case |
| `syscall; ret` | `syscall_trigger` | none | 8 after syscall path returns, but syscall behavior is runtime-dependent |

## Suffix pattern warning

Sprint 3 pattern labels are exact suffix labels, not full decoded instruction sequences. A raw candidate window can include extra bytes before the recognized suffix. The classifier must therefore treat `PATTERN_*` as a trusted exact suffix ID, but it must not assume the whole raw window is decoded unless a future decoder record says so.

## Conservative classification rule

When a candidate does not match a supported exact pattern, or when the supported pattern is ambiguous under the current model, leave the semantic class as `unknown_candidate`. Overclassification is worse than underclassification because it corrupts primitive coverage metrics and later scoring.
