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


## Sprint 3 raw candidate layer

Sprint 3 intentionally stops before semantic classification. The `gadgets` command currently reports raw terminator-centered byte windows with these fields:

- terminator virtual address,
- terminator file offset,
- bounded byte-window start,
- byte-window length,
- terminator type,
- raw bytes.

All Sprint 3 candidates use `SEM_UNKNOWN_CANDIDATE` internally. Sprint 4 will map raw byte windows into semantic classes such as `arg_control`, `syscall_trigger`, and `stack_pivot`.
