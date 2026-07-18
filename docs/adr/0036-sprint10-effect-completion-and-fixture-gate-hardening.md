# ADR 0036: Sprint 10 Effect Completion and Fixture-Gate Hardening

## Status

Accepted for Sprint 10 Patch 050.

## Context

Patches 046 through 049 added ordered two-pop, register-transfer, stack-adjust,
and bounded qword memory families. The Patch 049 review found no analyzer defect,
but it exposed two acceptance weaknesses:

1. the transfer fixture still expected two memory forms to remain `ret`
   fallbacks after Patch 049 promoted them into the memory families; and
2. the corresponding multi-command Make recipe could continue after a failed
   specialty validator and later report success.

The same review period also showed that current side-effect facts were not
complete across older supported families. In particular, every represented
return-ending suffix consumes a return address, `syscall` overwrites `rcx` and
`r11`, and `leave` overwrites `rbp` before the retained return.

## Decision

Patch 050 completes the current exact-family effect contract without adding a
new primitive family.

- Every supported semantic candidate ending in `ret` or `ret imm16` records
  `stack_read`.
- `syscall; ret` records `rcx` and `r11` as clobbers plus `syscall`,
  `register_write`, and `stack_read` effects.
- `leave; ret` records `rbp` as a clobber plus `stack_pivot`,
  `register_write`, and `stack_read`; its stack delta remains unknown.
- Transfer, stack-adjust, and memory fixtures use the completed effect facts.
- `memory_effect.asm` reconciles the same completed memory-family masks before materializing structured operands, so classifier and side-car contracts cannot drift silently.
- The transfer fixture treats its exact memory load/store forms as cross-family
  memory promotions and retains only four true `ret` fallbacks.
- Sprint 10 multi-command Make recipes execute with fail-fast shell semantics.
- A machine-readable family-coverage table records fixtures, effects,
  conservative fallback boundaries, and score disposition for every current
  family.
- The authenticated-overlay smoke isolates stale internal-manifest rejection
  from textual-content rejection.

The current Sprint 10 families remain unscored. Score calibration is deferred
until the planned architecture/capability review can evaluate stack cost,
clobbers, dereference risk, flag effects, and evidence uncertainty together.

## Consequences

### Positive

- Candidate effects are internally consistent across historical and Sprint 10
  families.
- A fixture cannot silently move into another semantic family without updating
  its direct oracle.
- Make target success now means every command in the recipe succeeded.
- The fixed candidate record, evidence record, memory-effect record, candidate
  capacity, and arena size remain unchanged.
- No runtime decoder, thread runtime, helper process, interpreter, or shared
  library is introduced.

### Tradeoffs

- Existing same-schema Patch 046 reports remain consumable but do not satisfy
  the stronger Patch 050 current-producer effect contract.
- The family table adds one more maintained contract surface.
- New-family scoring remains intentionally incomplete until evidence supports a
  defensible policy.

## Rejected alternatives

### Add another primitive family in Patch 050

Rejected because the current fixture and effect contracts required correction
before further breadth.

### Retroactively require Patch 046 fixtures to contain Patch 050 effects

Rejected because schema compatibility and current-producer conformance are
separate questions. Historical compatible reports must remain readable without
being rewritten.

### Infer effects in reporters

Rejected because reporters render internal facts and must not recreate
classification policy.

### Assign placeholder scores to close the Sprint 10 checklist

Rejected because a numeric score without a reviewed utility model would
collapse semantic facts into an unsupported exploitability proxy.
