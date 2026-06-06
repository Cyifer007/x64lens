# Mitigation Detection Model

| Mitigation | Static detection strategy | Confidence |
| ---------- | ------------------------- | ---------- |
| NX stack | `PT_GNU_STACK` exists and lacks executable flag | High |
| Executable stack | `PT_GNU_STACK` executable | High |
| PIE | ELF type `ET_DYN` for executable | High |
| RELRO | `PT_GNU_RELRO` present | High |
| Full RELRO | `PT_GNU_RELRO` plus `BIND_NOW` or `DF_BIND_NOW` dynamic info | Medium-high |
| Canary indicator | `__stack_chk_fail` import or symbol reference | Medium |
| RWX segment | Any `PT_LOAD` with write and execute flags | High |
| Stripped | missing or limited symbol table | Medium |
| Dynamic linking | `PT_DYNAMIC` present | High |

## Interpretation rule

Mitigations should be connected to exploit strategy constraints, not treated as standalone final verdicts.

Preferred wording:

```text
This binary exposes primitives consistent with certain exploit strategies, assuming an independent vulnerability and necessary runtime conditions.
```
