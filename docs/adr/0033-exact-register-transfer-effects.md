# ADR 0033: Exact Register-Transfer Effects

## Status

Accepted for Sprint 10 Patch 047.

## Context

Patch 046 established ordered two-pop facts without enlarging the fixed
candidate arena. Sprint 10 next requires a conservative register-transfer
family, but the implementation must not infer external control, decode memory
operands, change score meaning, or add a runtime dependency.

The existing 112-byte `gadget_record` has an eight-byte exact-pattern metadata
tail. Reusing that bounded space avoids a record-size increase and preserves the
4,096-candidate arena contract.

## Decision

Recognize the exact suffix:

```text
REX.W + (89 /r | 8b /r) + ModRM.mod=3 + ret
```

only when:

- source and destination are distinct 64-bit general-purpose registers;
- neither operand is `rsp`;
- the ModRM form is register-direct;
- the suffix ends immediately at the retained return terminator.

The exact matcher stores destination then source as canonical four-bit register
identifiers in the existing pattern-owned metadata. The classifier promotes the
candidate to `reg_transfer`, records the destination as clobbered, records a
known eight-byte return stack delta, and emits `register_write` as the represented
side effect. It leaves `controls` empty because an exact move does not establish
who controls the source register at runtime.

Self moves, stack-pointer participation, memory operands, 32-bit moves, and
unsupported encodings fall back to the strongest previously supported suffix.
They are not promoted to the new family.

Patch 047 does not assign a score to register-transfer candidates. Scoring is a
separate policy and requires evidence about source usefulness, destination
importance, clobbers, and chain context.

## Consequences

- `gadget_record` remains 112 bytes.
- The analysis arena remains 655,360 bytes.
- Candidate capacity remains 4,096 records.
- The runtime remains freestanding, decoder-free, single-worker, and without a
  new mandatory dependency.
- Schema `0.2.0` gains compatible optional fields; current-producer validation
  requires them while earlier `0.2.0` reports remain consumable.
- Exact suffix evidence remains distinct from full instruction-sequence
  validity.

## Rejected alternatives

### Treat the destination as independently controlled

Rejected. The move transfers the source value, but static suffix evidence does
not prove that the source is externally controlled.

### Recognize memory forms in the same patch

Rejected. Memory reads and writes require explicit base, index, displacement,
width, dereference direction, fault exposure, and clobber facts.

### Grow every candidate record

Rejected. The existing bounded metadata tail is sufficient; record growth would
enlarge the fixed arena or reduce candidate capacity.

### Score the family immediately

Rejected. A score before effect facts and representative use cases are reviewed
would collapse classification into policy.

## Validation

Patch 047 requires:

```bash
make sprint10-register-transfer-smoke
make json-effect-consistency-smoke
make schema-compat-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

The controlled fixture covers accepted legacy and extended-register transfers
plus self, `rsp`, memory, and 32-bit fallback cases. `gadgets` and `analyze` must
remain command-only parity matches.

## Related documents

- [`../design/primitive-effect-model.md`](../design/primitive-effect-model.md)
- [`../semantic-taxonomy.md`](../semantic-taxonomy.md)
- [`../sprints/sprint-10-plan.md`](../sprints/sprint-10-plan.md)
- [`../sprints/sprint-10-patch-047-validation.md`](../sprints/sprint-10-patch-047-validation.md)
- [`../design/evidence-provenance-model.md`](../design/evidence-provenance-model.md)
- [`../architecture.md`](../architecture.md)
- [`../json-schema.md`](../json-schema.md)
- [`../roadmap-18-sprints.md`](../roadmap-18-sprints.md)
