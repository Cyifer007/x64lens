# Gadget Scoring Model

## Initial formula

```text
score = semantic_base
      + rare_primitive_bonus
      - clobber_penalty
      - memory_deref_penalty
      - stack_delta_penalty
      - bad_byte_penalty
      - uncertain_decode_penalty
```

## Initial base scores

| Gadget type | Initial score |
| ----------- | ------------: |
| `pop rdi; ret` | 95 |
| `pop rsi; ret` | 95 |
| `pop rdx; ret` | 95 |
| `pop rax; ret` | 90 |
| `syscall; ret` | 90 |
| `leave; ret` | 80 |
| `pop rsp; ret` | 75 |
| `ret` | 50 |
| multi-pop gadget | 60 to 85 depending on side effects |
| memory write gadget | 70 to 95 depending on controllability |

## Research warning

The scoring model is heuristic until validated. It should be treated as a research hypothesis, not ground truth.
