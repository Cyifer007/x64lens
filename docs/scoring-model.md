# Gadget Scoring Model

## Status

Scoring is **not implemented yet**. Sprint 4 Patch 015 adds the first semantic classifier layer so Sprint 5 can score from internal facts instead of from raw text or exact pattern labels alone.

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

## Sprint 4 classifier inputs now available

Patch 015 provides these scoring inputs in `gadget_record`:

- `GADGET_SEMANTIC_CLASS`,
- `GADGET_REGS_CONTROLLED`,
- `GADGET_STACK_DELTA`,
- `GADGET_SIDE_EFFECT_FLAGS`,
- semantic summary counts and register coverage in `gadget_summary`.

Scoring should consume these internal fields in Sprint 5. It must not infer score values by scraping text output or by treating all raw candidates as equivalent.

## Scoring constraints for Sprint 5

- Score only records with justified semantic classes.
- Keep `unknown_candidate` unscored or neutral.
- Apply uncertainty penalties because Sprint 4 classification is exact-suffix based, not full decoder based.
- Keep raw candidate count, exact pattern count, semantic primitive count, and scored candidate count separate.
- Do not claim exploitability from score alone.

## Research warning

The scoring model is heuristic until validated. It should be treated as a research hypothesis, not ground truth.


## Sprint 5 entry note

Patch 015 validation provides enough internal semantic facts to begin scoring, but score output must remain conservative. Sprint 5 should not assign high-confidence scores to `unknown_candidate`, ambiguous suffix-only windows, or stack-pivot records without preserving uncertainty. JSON should expose enough fields for consumers to distinguish raw candidates, exact suffix matches, semantic primitives, unknown candidates, and scored candidates.
