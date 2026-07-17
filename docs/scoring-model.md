# Scoring Model

## Purpose

The score is a bounded heuristic for relative candidate utility under the current semantic model. It is not a vulnerability severity, exploitability probability, or binary-level risk rating.

## Current model

Sprint 5 introduced a fixed table over supported semantic-exact patterns:

| Pattern | Semantic class | Score |
|---|---|---:|
| `pop rdi; ret` | `arg_control` | 90 |
| `pop rsi; ret` | `arg_control` | 90 |
| `pop rdx; ret` | `arg_control` | 90 |
| `pop rcx; ret` | `arg_control` | 90 |
| `pop r8; ret` | `arg_control` | 90 |
| `pop r9; ret` | `arg_control` | 90 |
| `pop rax; ret` | `syscall_num_control` | 85 |
| `syscall; ret` | `syscall_trigger` | 85 |
| `leave; ret` | `stack_pivot` | 75 |
| `pop rsp; ret` | `stack_pivot` | 70 |
| `ret` | `alignment` | 45 |
| `ret imm16` | `alignment` | 40 |

Unknown candidates and supported patterns without an explicit score entry remain unscored. The internal sentinel is `0`; JSON uses `null` for unscored records.

## Module boundary

```text
scanner -> pattern matcher -> classifier -> scoring -> reporter
```

`scoring.asm` consumes semantic facts. It does not discover bytes, decide semantic class, parse mitigations, or format output. `analyze` reuses the same scores as `gadgets`.

## Current constraints

- Score only justified semantic candidates.
- Preserve `scored_candidate_count` separately from semantic and raw counts.
- Keep unknown candidates unscored.
- Keep evidence provenance visible.
- Do not promote a score into an exploitability verdict.
- Do not assign mitigation-aware bonuses or penalties until mitigation evidence is complete enough to support them.

## Planned factor model

Later score evolution may use:

```text
candidate_score = semantic_base
                + rare_primitive_bonus
                - clobber_penalty
                - memory_dereference_penalty
                - stack_uncertainty_penalty
                - bad_byte_penalty
                - decode_uncertainty_penalty
```

Every factor requires a corresponding fact in internal records. A score rule must not infer facts from human-readable text or from absent metadata.

## Provenance interaction

Schema `0.2.0` exposes evidence kind alongside each current candidate. Any future
decoder-backed score interpretation must continue to distinguish:

- semantic-exact candidates;
- decoder-backed semantic candidates; and
- unknown candidates.

A decoder-backed candidate may receive a different uncertainty adjustment, but existing scores should not silently change. Any recalibration requires documented score-model versioning or explicit changelog notes and fixture updates.

## Primitive expansion interaction

Sprint 10 may add score entries only after:

1. exact or decoded evidence is validated,
2. controlled and clobbered registers are known,
3. memory effects are known when applicable,
4. stack delta is known or explicitly unknown,
5. a controlled fixture exists,
6. score rationale is documented.

## Binary-level triage separation

A future binary triage summary is not an aggregate candidate score. It may consider mitigation facts, primitive coverage, representative candidate quality, provenance, completeness, and limitations. That model belongs in a separate record and document.

## Validation and research

The current values are hypotheses. Calibration may use:

- controlled exploit-development exercises,
- analyst ranking agreement,
- decoder-backed side-effect validation,
- comparison against baseline gadget quality filters,
- mitigation-aware case studies.

Until validated, the correct wording is “relative utility under the current model.”

## Sprint 9 closeout constraint

Patch 045 does not recalibrate scores. A candidate-scoped decoder may later add an explicit uncertainty factor only after decoder evidence is represented and benchmarked. A parallel profile must produce identical scores and ordering to the one-worker reference. No throughput optimization may change scoring facts.

## Sprint 10 Patch 046 multi-pop status

The first two-pop argument-control family is intentionally unscored. It provides
more controlled registers than a single-pop primitive, but it also consumes more
stack and introduces order-sensitive effects. Assigning a score before clobber,
memory, decoder-confidence, and comparative-utility policy is defined would
collapse semantic evidence into an unsupported ranking.

Patch 046 therefore permits:

```text
semantic_class = arg_control
score = null
```

This is a deliberate model state, not a missing reporter value. A later score
entry requires separate fixtures and scoring-model validation.

## Sprint 10 Patch 047 score decision

The first `reg_transfer` family remains unscored. Its usefulness depends on the
source value, destination role, chain context, clobber cost, and future decoder
confidence. Patch 047 adds those structural facts without assigning an
unsupported utility value. Any later score requires a documented table entry or
factor rule plus fixture updates.

## Sprint 10 Patch 048 score decision

The first positive aligned `add rsp, imm8; ret` family remains unscored. Utility depends on adjustment size, chain layout, alignment needs, condition-flag effects, surrounding candidate validity, and future bad-byte or decoder evidence. Patch 048 records the exact immediate-derived stack delta and explicit `stack_adjust`/`flags_write` effects but does not infer a utility rank.

Any later score requires an explicit rule and fixture update. Existing `ret` and `ret imm16` scores are not reused because the new family performs additional arithmetic and has a different chain effect.
