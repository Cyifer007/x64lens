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

At the Patch 046 boundary, the first two-pop argument-control family was
intentionally unscored. It provides
more controlled registers than a single-pop primitive, but it also consumes more
stack and introduces order-sensitive effects. Assigning a score before clobber,
memory, decoder-confidence, and comparative-utility policy is defined would
collapse semantic evidence into an unsupported ranking.

Patch 046 therefore permits:

```text
semantic_class = arg_control
score = null
```

This was a deliberate model state, not a missing reporter value. Patch 051
later supplies the required validation and calibrates the current score to 95.

## Sprint 10 Patch 047 score decision

The first `reg_transfer` family remains unscored. Its usefulness depends on the
source value, destination role, chain context, clobber cost, and future decoder
confidence. Patch 047 adds those structural facts without assigning an
unsupported utility value. Any later score requires a documented table entry or
factor rule plus fixture updates.

## Sprint 10 Patch 048 score decision

At the Patch 048 boundary, the first positive aligned `add rsp, imm8; ret`
family was unscored. Utility depends on adjustment size, chain layout, alignment
needs, condition-flag effects, surrounding candidate validity, and future bad-
byte or decoder evidence. Patch 048 records the exact immediate-derived stack
delta and explicit `stack_adjust`/`flags_write` effects without inferring a
utility rank; Patch 051 later calibrates the current score to 35.

That later score required an explicit rule and fixture update. Existing `ret`
and `ret imm16` scores were not reused because the new family performs
additional arithmetic and has a different chain effect.


## Sprint 10 Patch 050 score decision

Patch 050 assigns no new score. Patch 051 adds two reviewed entries after architectural-effect validation: ordered multi-pop argument control scores 95 and positive aligned stack adjustment scores 35. Register-transfer, memory-read, and memory-write candidates remain semantic-exact but unscored.

Any future score must continue to define and test at least:

- stack-cost and ordering effects;
- GPR and flag clobbers;
- memory dereference and address-control uncertainty;
- evidence source and future decoder confidence;
- task-specific defensive utility;
- versioning or migration behavior for existing score values.

At the Patch 050 boundary, `score: null` was correct for all new Sprint 10
families. Patch 051 supersedes that state for ordered two-pop and positive
aligned stack adjustment; register-transfer and memory families remain null.

## Sprint 10 Patch 051 calibrated entries

Patch 051 adds two explicit score entries after semantic and architectural-effect
validation:

| Pattern family | Semantic class | Score |
|---|---|---:|
| ordered two-pop argument control | `arg_control` | 95 |
| positive aligned `add rsp, imm8; ret` | `alignment` | 35 |

The scorer validates pattern identity, semantic class, controls, clobbers,
ordered metadata, stack delta, coarse effects, and the architectural-effect
record before assigning either value. An inconsistent record fails closed with
an internal bounds error rather than receiving a score.

Register-transfer and memory read/write families remain unscored because the
current model does not represent source-value control, address control, or
memory-content control. The values remain relative utility hypotheses and are
not exploitability probabilities or binary-level risk scores.


## Sprint 10 Patch 052 score-policy gate

Patch 052 does not recalibrate any score. It makes the existing numeric policy
machine-checkable across the semantic-family and exact-pattern authorities. A
mutation from ordered multi-pop 95 to 94 or stack adjustment 35 to 34 must fail
both reconciliation gates.

The scoring engine also compares full-width architectural descriptors through a
register, preventing immediate-width truncation from allowing an invalid record
to retain a score. Register-transfer and memory families remain unscored.

## Sprint 10 Patch 053 score-freeze decision

Patch 053 adds no score. Sprint 11 diagnostic measurements may expose where score
or family definitions need revision, but they are not score-calibration evidence
by themselves. Sprint 13 owns the release-facing score/null policy decision, and
Sprint 15 freezes that policy with the confirmatory campaign.

A score change after the Sprint 15 freeze requires a new campaign identifier or
complete rerun of every affected condition. Register-transfer and memory-family
scores remain `null` until their required controllability and uncertainty facts
exist.
