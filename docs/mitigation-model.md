# Mitigation Detection Model

## Sprint 2 implemented baseline

| Mitigation or signal | Static detection strategy | Confidence | Sprint 2 status |
| ---------- | ------------------------- | ---------- | --------------- |
| NX stack | `PT_GNU_STACK` exists and lacks `PF_X` | High | Implemented |
| Executable stack | `PT_GNU_STACK` exists and includes `PF_X` | High | Implemented as `NX stack: disabled` |
| PIE | ELF type `ET_DYN` | High for common PIE executable identification, but shared libraries are also `ET_DYN` | Implemented |
| RELRO baseline | `PT_GNU_RELRO` present | High for baseline RELRO presence | Implemented |
| RWX segment | Any `PT_LOAD` with both `PF_W` and `PF_X` | High | Implemented |
| Dynamic linking | `PT_DYNAMIC` present | High | Implemented |
| Executable region | `PT_LOAD` with `PF_X` | High | Implemented |

## Future mitigation work

| Mitigation | Static detection strategy | Confidence | Notes |
| ---------- | ------------------------- | ---------- | ----- |
| Full RELRO | `PT_GNU_RELRO` plus `BIND_NOW` or `DF_BIND_NOW` dynamic info | Medium-high | Requires dynamic-section parsing |
| Canary indicator | `__stack_chk_fail` import or symbol reference | Medium | Requires dynamic symbol or symbol-table parsing |
| Stripped | missing or limited symbol table | Medium | Requires section/symbol parsing |
| CET/IBT indicators | GNU property notes and relevant instruction/symbol patterns | Medium | Later research target |

## Interpretation rule

Mitigations should be connected to exploit strategy constraints, not treated as standalone final verdicts.

Preferred wording:

```text
This binary exposes primitives consistent with certain exploit strategies, assuming an independent vulnerability and necessary runtime conditions.
```

## Sprint 2 wording rule

Sprint 2 output reports loader-level facts and mitigation indicators only. It must not claim exploitability, vulnerability, or exploit success. Strategy interpretation begins later when primitive coverage and mitigation context can be evaluated together.
