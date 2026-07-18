# Sprint 10 Family Coverage and False-Positive Boundaries

## Purpose

This document is the human-readable companion to
`tests/expected/sprint10-family-coverage.json`. It records the controlled
fixture, represented effects, score policy, and conservative promotion boundary
for every currently implemented return-ending semantic family.

The table is a correctness and review surface. It is not a publication-grade
coverage comparison and does not imply full instruction-sequence validity.

## Reference profile

```text
tool version:                    0.1.0-dev
JSON schema:                     0.2.0
candidate capacity:              4096
gadget_record:                   112 bytes
candidate_evidence_record:        48 bytes
memory_effect_record:             16 bytes
combined analysis arena:      720896 bytes
mandatory runtime decoder:       no
mandatory runtime threads:       no
```

The arena size is a fixed allocation fact, not a measured maximum-RSS result.

## Implemented-family matrix

| Family | Fixture/gate | Effects | Clobbers | Score policy | Conservative boundary |
|---|---|---|---|---|---|
| `ret` | `tests/toy-src/gadgets.S`; `make validate-gadget-fixture` | `stack_read` | none | 45 | Exact return-byte suffix only; the retained backward window is not decoder-validated. |
| `ret imm16` | base gadget fixture | `stack_read`, `ret_imm16`, `stack_adjust` | none | 40 | Immediate-derived delta is exact suffix evidence; unaligned raw candidates remain possible. |
| single `pop` | base gadget fixture; `make json-effect-consistency-smoke` | `stack_read` | none | existing family-specific values | Only the exact final pop controls the named register. |
| `syscall; ret` | base gadget fixture | `stack_read`, `syscall`, `register_write` | `rcx`, `r11` | 85 | Does not imply a controlled syscall number, arguments, or safe return state. |
| `leave; ret` | base gadget fixture | `stack_read`, `stack_pivot`, `register_write` | `rbp` | 75 | Resulting stack delta is input-dependent and remains unknown. |
| `pop rsp; ret` | base gadget fixture | `stack_read`, `stack_pivot` | none | 70 | Exact suffix establishes a pivot relation, not a known numeric delta. |
| ordered two-pop | `gadgets_sprint10.S`; `make sprint10-primitive-smoke` | `stack_read` | none | unscored | Only distinct ordered pairs from `rdi/rsi/rdx/rcx/r8/r9`; unsupported pairs fall back. |
| register transfer | `gadgets_sprint10_transfer.S`; `make sprint10-register-transfer-smoke` | `stack_read`, `register_write` | destination | unscored | Only distinct 64-bit register-direct non-`rsp` moves; memory forms use the memory family. |
| stack adjustment | `gadgets_sprint10_stack_adjust.S`; `make sprint10-stack-adjust-smoke` | `stack_read`, `stack_adjust`, `flags_write` | none | unscored | Only positive, nonzero, eight-byte-aligned `imm8` additions to `rsp`. |
| memory write | `gadgets_sprint10_memory.S`; `make sprint10-memory-smoke` | `stack_read`, `memory_write` | none | unscored | Only qword base-plus-zero, no-index, no-displacement exact stores; address/value control is not inferred. |
| memory read | memory fixture | `stack_read`, `register_write`, `memory_read` | destination | unscored | Same bounded address domain; memory-content control is not inferred. |

## Cross-family fixture rule

A fixture is allowed to exercise more than one implemented family. The transfer
fixture intentionally contains one bounded memory write and one bounded memory
read. Those candidates must be validated as memory operations rather than
counted as transfer fallbacks.

This rule prevents a fixture written before a later family from becoming a
stale test oracle.

## Score boundary

The new Sprint 10 families remain unscored until a reviewed policy can account
for:

- stack consumption and ordering;
- destination clobbers;
- memory dereference and address uncertainty;
- flag modification;
- evidence kind and future decoder confidence;
- corpus-observed defensive utility.

`score: null` is therefore an intentional current fact, not missing output.

## Validation

```bash
make sprint10-family-coverage-smoke
make json-effect-consistency-smoke
make sprint10-primitive-smoke
make sprint10-register-transfer-smoke
make sprint10-stack-adjust-smoke
make sprint10-memory-smoke
```

The machine-readable table and all expected reports remain schema `0.2.0`
fixtures. Historical Patch 046 reports remain compatible, while current
producer output must satisfy the stronger completed-effect contract.
