# Mitigation Detection Model

## Purpose

Mitigation reporting is an evidence layer. x64lens reports static indicators and the evidence used to derive them. It does not treat one indicator as a vulnerability, a proof of safety, or an exploitability verdict.

## Current implemented baseline

| Signal | Static evidence | Confidence | Status |
|---|---|---|---|
| NX stack enabled | `PT_GNU_STACK` exists without `PF_X` | High | Implemented |
| Executable stack | `PT_GNU_STACK` exists with `PF_X` | High | Implemented as NX disabled |
| NX stack unknown | `PT_GNU_STACK` absent | Explicit unknown | Implemented |
| PIE indicator | ELF type `ET_DYN` | High for common PIE executables, but shared objects also use `ET_DYN` | Implemented |
| No RELRO | no `PT_GNU_RELRO` | High after the program-header table is parsed completely | Implemented |
| Partial RELRO | `PT_GNU_RELRO` present without bounded bind-now evidence | High for represented loader metadata | Implemented |
| Full RELRO | `PT_GNU_RELRO` plus bounded bind-now evidence from `DT_BIND_NOW`, `DT_FLAGS`, or `DT_FLAGS_1` | High for represented loader metadata | Implemented |
| RWX load segment | `PT_LOAD` has `PF_W` and `PF_X` | High | Implemented |
| Dynamic linking | `PT_DYNAMIC` present | High | Implemented |
| Bind now indicator | bounded `PT_DYNAMIC` scan finds `DT_BIND_NOW`, `DT_FLAGS & DF_BIND_NOW`, or `DT_FLAGS_1 & DF_1_NOW` | High for represented dynamic-table evidence | Implemented |
| Dynamic entry count | bounded number of `Elf64_Dyn` entries inspected, including `DT_NULL` when seen | High within the checked file-backed table | Implemented |
| Dynamic terminator | bounded `PT_DYNAMIC` scan sees `DT_NULL` before the checked table ends | High for represented table termination | Implemented |
| Executable region | `PT_LOAD` has `PF_X` | High | Implemented |

## Sprint 8 mitigation depth

Patch 030 implements the first bounded `PT_DYNAMIC` evidence view. Patch 031 uses that view to split RELRO into no, partial, and full states while preserving the underlying bind-now and dynamic-table facts as separate evidence fields.

| Signal | Planned evidence | Reporting rule |
|---|---|---|
| No RELRO | no `PT_GNU_RELRO` | Report `none` in JSON and `RELRO: not found` in text after the program-header table is parsed completely. |
| Partial RELRO | `PT_GNU_RELRO` without immediate binding evidence | Report `partial`; preserve bind-now as `no` or `not applicable` according to dynamic-table evidence. |
| Full RELRO | `PT_GNU_RELRO` plus `DT_BIND_NOW`, `DF_BIND_NOW`, or equivalent validated evidence | Report `full`; preserve the bind-now evidence path separately. |
| Canary indicator | validated import, symbol, or relocation evidence for stack-check routines | Report indicator presence, not complete stack protection. |
| Stripped indicator | absent or limited symbol-table evidence | Report as a metadata indicator with confidence. |
| Section label | section range containing a region or candidate | Annotation only; never replace program-header mapping authority. |
| CET/IBT indicator | validated GNU property notes and supported instruction evidence | Planned after core Sprint 8 work if bounded parsing and fixtures are ready. |

## Evidence and confidence

Future schema output should separate state from evidence:

```json
{
  "relro": "full",
  "canary": "present",
  "evidence": {
    "relro": ["PT_GNU_RELRO", "DF_BIND_NOW"],
    "canary": ["__stack_chk_fail"]
  }
}
```

Missing evidence should produce `unknown` when the parser cannot justify a negative. A completed search with no relevant evidence may produce an explicit negative when the detection model defines one.

## Interpretation rules

- NX constrains injected-code strategies but does not prevent code reuse.
- PIE changes address predictability but does not guarantee secrecy.
- RELRO constrains selected relocation targets but does not remove memory corruption.
- Canary indicators suggest stack-protector linkage but do not prove every vulnerable function is protected.
- CET/IBT indicators do not prove complete control-flow integrity.
- Useful primitives do not imply an exploitable vulnerability.

Preferred wording:

```text
The binary exposes static facts and primitive evidence consistent with selected exploit-strategy constraints, assuming an independent vulnerability and required runtime conditions.
```

## Controlled fixtures

Mitigation validation should use dedicated builds rather than the scanner-only gadget fixture:

- non-PIE with NX stack,
- PIE with stack protector and full RELRO,
- executable stack,
- no RELRO,
- partial RELRO,
- full RELRO,
- bind-now through `DT_BIND_NOW`, `DT_FLAGS`, and `DT_FLAGS_1`,
- malformed dynamic-table range and entry-size cases,
- canary-present and canary-absent variants,
- static and dynamic linkage where practical.

The hand-authored static gadget fixture may correctly report:

```text
NX stack: unknown
RELRO: not found
Dynamic linking: no
Bind now: not applicable
Dynamic entries: 0x0000000000000000
Dynamic terminator: not applicable
```

It is a deterministic code-byte fixture, not a mitigation fixture.

## Parser-safety dependency

Dynamic, symbol, string, relocation, section, and GNU property parsing must use validated ranges and bounded iteration. Sprint 7 hostile-input infrastructure precedes Sprint 8 mitigation depth for this reason.

## Comparison plan

Mitigation output should be compared against controlled linker commands and selected external tools:

- `readelf -h -l -d -s -n`,
- optional `checksec`,
- optional `rabin2 -I`.

Disagreements should be investigated by evidence source rather than resolved by copying another tool's label.

## Deterministic mitigation oracle

`make mitigation-matrix-smoke` is the authoritative controlled truth table for the implemented baseline. After Patch 031, 17 valid layouts isolate ELF type, GNU stack state, no/partial/full RELRO states, dynamic linking, bind-now evidence, load permissions, split mappings, executable-region counts, overlapping executable regions, and combined evidence. Eleven malformed layouts verify consistent fail-closed behavior across relevant command paths, including dynamic-table range, entry-size, and duplicate-`PT_DYNAMIC` rejection. The oracle validates current facts only; it does not add canary, GNU property, or exploitability conclusions.
