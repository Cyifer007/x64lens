# ADR 0066: Patch 079 Correction and Private Register-Role Side-Car

## Status

Accepted as the historical Patch 080 implementation decision. Patch 080 was
superseded by Patch 081, and Patches 081 through 087 did not complete
acceptance. Patch 089 is the current implementation candidate pending complete
exact-source acceptance.

## Context

Patch 079 established useful private register-role task evidence, but its review
found acceptance defects in patch recovery, Git-less permission custody, Docker
image identity, parity build execution, and the task-value oracle. The original
task authority reused development queries in the confirmation partition, the
presentation permutation did not affect the decision, and the ABI oracle did
not reject an invalid System V argument-three reassignment.

The existing runtime already preserves exact single-pop patterns and
architectural effects for all 16 GPRs. The missing release-facing decision is
contextual role, not byte discovery or decoded validity.

## Decision

Patch 080 corrects the complete Patch 079 acceptance finding set and adds one
private, dense, candidate-indexed register-role side-car:

```text
candidate_role_record[4096]
  role_mask: 8 bytes
```

The mask can represent:

- generic non-`rsp` register control;
- System V call argument positions 1 through 6; and
- Linux syscall argument positions 1 through 6.

The distinctions are additive. In particular:

```text
System V call argument 4:     rcx
Linux syscall argument 4:     r10
System V/Linux argument 3:    rdx
```

`rsp` remains a stack-pivot role rather than generic register control. `rax`
retains its existing syscall-number semantic class and score; the new
generic-control facet is private only.

The side-car is materialized after exact-pattern and architectural-effect
reconciliation and before scoring. Scoring and reporters do not receive the
side-car in Patch 080.

## Corrected task-value authority

The replacement task authority contains five independent strata, 60 total query
tuples, and no query reuse between development and confirmation partitions.
Profile answers are generated from the complete role authority before oracle
scoring. Deterministic presentation order is retained only as reproducible
display metadata; it is explicitly non-causal and carries no human-blinding
claim.

Three strata qualify as private policy input:

- generic register control;
- System V call arguments; and
- Linux syscall arguments.

Syscall-number and stack-pivot task strata remain deferred under their existing
public semantics and scores.

## LC-08B policy decision

Patch 080 accepts the three qualified facets only in the private runtime
side-car. It defers public text/JSON projection and retains existing score values
while leaving newly represented private facets unscored.

Therefore Patch 080 changes none of the following:

- semantic class;
- public text output;
- public JSON fields;
- schema `0.2.0`;
- candidate count or order;
- candidate capacity or overflow behavior;
- score values or `null` policy; or
- evidence tier or full-sequence-validity state.

## Storage consequence

The fixed command arena increases by exactly 32,768 bytes:

```text
candidate_role_record:       8 bytes
candidate capacity:       4096
candidate-role slice:    32768 bytes
combined command arena: 884736 bytes
```

This is a fixed allocation fact, not measured RSS or performance evidence.

## Preserved boundaries

- File-backed `PT_LOAD + PF_X` ranges remain executable authority.
- Raw, exact-suffix, semantic-exact, unknown, future decoder-backed, and scored
  facts remain distinct.
- Candidate 4,097 still returns exit code 6 before stdout.
- Malformed parser failures still emit no partial stdout.
- Target files remain read-only and are never executed.
- The reference analyzer remains dependency-free, decoder-free, one-worker,
  bounded, and deterministic.

## Consequences

Patch 081 records a test-only ordered two-pop manifest whose declared outcomes
produce zero incremental gains and therefore defer a redundant runtime tuple.
The static authority is policy input, not confirmatory measured task-value
evidence, and Patch 080 private-role qualification remains insufficient
authority for public output or score changes.
