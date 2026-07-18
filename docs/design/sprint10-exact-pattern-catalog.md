# Sprint 10 Exact-Pattern and Architectural-Effect Catalog

## Purpose

This document accompanies
`tests/expected/sprint10-exact-pattern-catalog.json` and the controlled
`gadgets_sprint10_effects.S` fixture. It records one current contract for each
exact pattern ID without confusing exact suffix recognition with complete
instruction decoding.

## Reference profile

```text
exact pattern IDs:                 25
gadget_record:                    112 bytes
candidate_evidence_record:         48 bytes
memory_effect_record:              16 bytes
candidate_effect_record:           24 bytes
candidate capacity:              4096
fixed command arena:           819200 bytes
runtime decoder:                    no
runtime worker default:             one
```

The arena value is fixed allocation arithmetic, not measured max RSS.

## Catalog populations

```text
exact patterns:       25
semantic exact:       17
exact-only unknown:    8
scored:               14
complete effect model: 23
partial effect model:   2
```

The partial models are:

- `pop rsp; ret`, because its two stack reads use different stack bases; and
- `syscall; ret`, because kernel-mediated state is outside static suffix
  analysis.

## Effect model

The side-car records:

- GPRs read and written;
- represented condition flags read and written;
- return and syscall control-flow effects;
- stack source base;
- bounded stack-read/write counts;
- first stack-read offset and stride when representable; and
- whether the represented model is complete for the exact suffix.

Memory address/value operands remain in `memory_effect_record`. Candidate
validity provenance remains in `candidate_evidence_record`.

## Exact-only single-pop rule

`pop rbx/rbp/r10/r11/r12/r13/r14/r15; ret` remains
`unknown_candidate` under the current semantic taxonomy. The exact register and
stack effects are nevertheless deterministic and are emitted through the
architectural-effect side-car. This does not imply a utility class or score.

## Validation

```bash
make sprint10-architectural-effects-smoke
make sprint10-family-coverage-smoke
make sprint10-contract-reconciliation-smoke
make json-effect-consistency-smoke
make schema-compat-smoke
```

The disassembly fixture is an independent development oracle. GNU objdump does
not become runtime mapping, classification, or reporting authority.
