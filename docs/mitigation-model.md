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


## Sprint 2 validation status

Sprint 2 validation confirmed the implemented baseline against controlled toy binaries and `/bin/ls` using `readelf -h` and `readelf -l` side-by-side review. The most important validation points were:

- `minimal_nopie` reports PIE disabled and NX stack enabled.
- `minimal_pie_canary` reports PIE enabled and NX stack enabled.
- `minimal_execstack` reports NX stack disabled, matching `GNU_STACK RWE`.
- All tested targets reported one executable `PT_LOAD + PF_X` region, matching the executable `LOAD` segment in `readelf -l`.
- Baseline RELRO is currently reported only from `PT_GNU_RELRO` presence. Full RELRO remains future work.

## Sprint 3 fixture note: `tests/bin/gadgets`

The hand-authored static gadget fixture may report:

```text
NX stack: unknown
RELRO: not found
Dynamic linking: no
```

This is expected for the current fixture. It is linked with `-nostdlib -static -no-pie` and exists to provide deterministic executable bytes for scanner validation, not to exercise dynamic-linker hardening metadata. If `PT_GNU_STACK` is absent, x64lens correctly reports NX stack as `unknown` rather than guessing. If `PT_GNU_RELRO` and `PT_DYNAMIC` are absent, x64lens correctly reports baseline RELRO as `not found` and dynamic linking as `no`.

Controlled mitigation states are validated with the `minimal_nopie`, `minimal_pie_canary`, and `minimal_execstack` fixtures instead.
