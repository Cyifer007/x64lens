# ADR 0037: Architectural Effects and Contract Reconciliation

## Status

Accepted for Sprint 10 Patch 051 validation.

Related documentation:

- [Architecture](../architecture.md)
- [Primitive Effect Model](../design/primitive-effect-model.md)
- [Family Coverage Table](../design/sprint10-family-coverage.md)
- [Exact-Pattern Catalog](../design/sprint10-exact-pattern-catalog.md)
- [Scoring Model](../scoring-model.md)
- [Output Contract](../contracts/output-contract.md)
- [Patch 051 Validation](../sprints/sprint-10-patch-051-validation.md)

## Context

Patch 050 closed the coarse semantic-family effects and fixture-gate defects,
but the current exact catalog still needed one consistent representation for
architectural register, flag, control-flow, and stack-source effects. Patch 051
therefore reconciles three complementary contract surfaces:

1. coarse semantic-family effects and cross-family fixture reconciliation;
2. a dense candidate-index architectural-effect side-car and one-per-pattern
   fixture; and
3. centralized fail-fast fixture orchestration plus selective score calibration.

These surfaces share classifier, reporter, schema, fixture, and documentation
paths. One reconciled internal contract prevents their definitions from
diverging.

## Decision

Patch 051 preserves the Patch 050 semantic-family contract and adds a fixed-size
`candidate_effect_record[]` side-car keyed by candidate index.

```text
gadget_record[]
  raw, exact, semantic, coarse effect, and score facts

candidate_evidence_record[]
  raw/exact/semantic provenance

memory_effect_record[]
  structured memory operands and dereference facts

candidate_effect_record[]
  architectural GPR reads/writes, represented flags, control flow,
  stack-source facts, and model-completeness state
```

The new record is 24 bytes:

```text
registers_read       qword
registers_written    qword
descriptor           qword
```

At the fixed 4,096-candidate boundary, the command arena becomes 819,200 bytes.
The scanner-owned `gadget_record` remains 112 bytes and candidate capacity
remains 4,096.

The side-car is materialized after semantic and memory-effect classification
and before scoring. Scoring consumes validated semantic and architectural facts;
it does not infer effects from pattern labels.

Patch 051 calibrates only two newer families:

- ordered two-pop argument control: score 95;
- positive aligned `add rsp, imm8; ret`: score 35.

Register-transfer and memory families remain unscored because source-value,
address, and memory-content controllability are not represented.

Validation is split into complementary contracts:

1. eleven semantic-family contracts;
2. twenty-five exact-pattern contracts; and
3. five controlled fixture-suite groups.

A reconciliation gate proves that those views agree. All current report
validators require the richer architectural-effect object, while earlier
schema `0.2.0` reports remain structurally consumable.

## Consequences

### Positive

- Every current exact pattern has an explicit architectural-effect record.
- Exact-only single-pop forms retain deterministic effects without unsupported
  semantic promotion.
- `pop rsp; ret` and `syscall; ret` explicitly report partial effect models.
- The scoring engine validates the facts on which its scores depend.
- One fixture exercises every exact pattern ID.
- One fail-fast runner prevents a later command from masking a failed specialty
  validator.
- No decoder, shared library, helper process, or thread runtime is introduced.

### Tradeoffs

- The fixed command arena grows by 98,304 bytes.
- The formal schema retains an optional object for earlier `0.2.0`
  compatibility; current producers emit it for every candidate.
- Three complementary fixture contracts must remain synchronized.
- The richer model is still exact-suffix evidence, not decoded full-sequence
  validity.

## Rejected alternatives

### Maintain separate effect, fixture, and score contracts

Rejected because independent definitions across the classifier, scorer,
reporters, fixtures, and documentation would permit contract drift. One
reconciliation gate keeps the reviewed architecture authoritative.

### Grow `gadget_record`

Rejected because the scanner-owned record and capacity are stable contracts.
A dense side-car keeps discovery independent from richer effects.

### Infer architectural effects in reporters or validators

Rejected because output adapters must consume facts rather than become parallel
semantic engines.

### Score every newly represented family

Rejected because memory and transfer utility still lacks required
controllability and risk facts.

### Add a decoder or parallel default during reconciliation

Rejected because Patch 051 is an effect-contract merge. Decoder and worker
profiles remain separate measured conditions.
