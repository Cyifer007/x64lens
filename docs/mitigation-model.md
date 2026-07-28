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
| Canary indicator present | bounded `DT_STRTAB`/`DT_STRSZ` scan finds exact null-terminated `__stack_chk_fail` | Medium, indicator only | Implemented in Patch 032 |
| Canary indicator absent | bounded dynamic string table was scanned and exact `__stack_chk_fail` was not found | Medium, only for represented dynamic-string metadata | Implemented in Patch 032 |
| Canary indicator unknown | no bounded dynamic string-table evidence was available | Explicit unknown | Implemented in Patch 032 |
| Stripped indicator not stripped | validated section-header table contains `SHT_SYMTAB` | Medium, metadata indicator only | Implemented in Patch 033 |
| Stripped indicator stripped | validated section-header table is present and contains no `SHT_SYMTAB` | Medium, metadata indicator only | Implemented in Patch 033 |
| Stripped indicator unknown | no bounded section-table evidence was available | Explicit unknown | Implemented in Patch 033 |
| Executable region | `PT_LOAD` has `PF_X` | High | Implemented |

## Sprint 8 mitigation depth

Patch 030 implements the first bounded `PT_DYNAMIC` evidence view. Patch 031 uses that view to split RELRO into no, partial, and full states while preserving the underlying bind-now and dynamic-table facts as separate evidence fields. Patch 032 uses bounded `DT_STRTAB` and `DT_STRSZ` evidence to add a canary indicator without claiming complete stack protection. Patch 033 adds a bounded section-header metadata indicator for stripped status while keeping program headers as executable-region authority.

| Signal | Planned evidence | Reporting rule |
|---|---|---|
| No RELRO | no `PT_GNU_RELRO` | Report `none` in JSON and `RELRO: not found` in text after the program-header table is parsed completely. |
| Partial RELRO | `PT_GNU_RELRO` without immediate binding evidence | Report `partial`; preserve bind-now as `no` or `not applicable` according to dynamic-table evidence. |
| Full RELRO | `PT_GNU_RELRO` plus `DT_BIND_NOW`, `DF_BIND_NOW`, or equivalent validated evidence | Report `full`; preserve the bind-now evidence path separately. |
| Canary indicator | bounded dynamic-string evidence for exact `__stack_chk_fail`; future symbol or relocation evidence may refine it | Report `unknown`, `absent`, or `present` as an indicator, not complete stack protection. |
| Stripped indicator | bounded section-header scan for `SHT_SYMTAB` | Report `unknown`, `stripped`, or `not_stripped` in JSON and `unknown`, `stripped`, or `not stripped` in text as metadata only. |
| Section label | section range containing a region or candidate | Annotation only; never replace program-header mapping authority. |
| CET/IBT/SHSTK private evidence | validated GNU property-note evidence with bounded parsing and controlled fixtures | Implemented and corrected through Patch 069; external diagnostic reconciliation is present, acceptance and native/container private-fact parity remain pending, and there is no public indicator. |

## Evidence and confidence

Future schema output should separate state from evidence:

```json
{
  "relro": "full",
  "canary": "present",
  "stripped": "not_stripped",
  "evidence": {
    "relro": ["PT_GNU_RELRO", "DF_BIND_NOW"],
    "canary": ["__stack_chk_fail"],
    "stripped": ["SHT_SYMTAB"]
  }
}
```

Missing evidence should produce `unknown` when the parser cannot justify a negative. A completed search with no relevant evidence may produce an explicit negative when the detection model defines one.

## Interpretation rules

- NX constrains injected-code strategies but does not prevent code reuse.
- PIE changes address predictability but does not guarantee secrecy.
- RELRO constrains selected relocation targets but does not remove memory corruption.
- Canary indicators suggest stack-protector linkage but do not prove every vulnerable function is protected.
- Stripped indicators summarize section-table symbol evidence and do not change loader mapping, executable-region, or gadget-scanning authority.
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
- stripped and not-stripped section-table variants,
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

`make mitigation-matrix-smoke` is the authoritative controlled truth table for the implemented baseline. After Patch 034, 24 valid layouts isolate ELF type, GNU stack state, no/partial/full RELRO states, dynamic linking, bind-now evidence, canary-present and canary-absent indicators, zero-length dynamic string-table negative evidence including the exact endpoint case, stripped and not-stripped section-table indicators, section-label fixture behavior, load permissions, split mappings, executable-region counts, overlapping executable regions, and combined evidence. Fourteen malformed layouts verify consistent fail-closed behavior across relevant command paths, including dynamic-table range, entry-size, duplicate-`PT_DYNAMIC`, duplicate `DT_STRTAB`, duplicate `DT_STRSZ`, and invalid dynamic string-table references. One unsupported layout verifies the dynamic string-table scan cap. The oracle validates current facts only; canary and stripped states are represented as indicators, section labels are annotations, and none of those facts prove complete hardening, GNU property state, or exploitability conclusions.

## Sprint 8 Patch 034 section labels

Section labels are optional annotations emitted after loader-derived executable regions and scanner-derived candidates already exist. They improve readability for analyst triage but do not change PIE, NX, RELRO, canary, stripped, RWX, executable-region, candidate, semantic, or score conclusions.


## Patch 053 pre-corpus review items

Patch 053 must refine or explicitly defer three mitigation/mapping questions
before expected corpus facts are frozen:

1. `ET_DYN` alone is not sufficient to distinguish a PIE executable from a shared object; any refined field requires bounded evidence and controlled fixtures.
2. CET/IBT/SHSTK reporting requires bounded GNU property-note parsing and must remain evidence-qualified rather than inferred from one instruction or tool label.
3. Overlapping executable `PT_LOAD` ranges require defined region and count semantics so scanner work, completeness, and benchmark denominators are not ambiguous.

Until those rules are implemented, current fields retain their documented indicator scope and limitations.

## Patch 053 mitigation gate ownership

Sprint 12 owns the release-facing mitigation precision work identified by the
capability review:

- distinguish PIE executables from shared objects using bounded evidence;
- add bounded GNU property-note indicators for x86 IBT and SHSTK;
- define overlapping executable-segment scan and count semantics;
- validate or explicitly reject unsupported program-header alignment,
  congruence, virtual-range, entrypoint, and extended-numbering states.

These additions remain indicators and loader facts. They do not prove complete
control-flow integrity, runtime ASLR, safety, or exploitability.

## Sprint 12 Patch 062 loader precondition

Mitigation evidence now depends on the shared ordinary program-header validity gate. Invalid alignment, load congruence, virtual-range overflow, or a nonzero entrypoint outside executable `PT_LOAD` memory is malformed input and cannot produce mitigation output. Structurally valid ELF64 extended-numbering input is explicitly unsupported at this boundary rather than being misinterpreted as ordinary PHDR/SHDR counts. Patch 062 adds no PIE-versus-DSO or CET fact; those remain later Sprint 12 evidence paths.

## Sprint 12 Patch 063 overlap-provenance boundary

Patch 063 does not change a mitigation state. It retains original executable
PHDR identity and per-candidate dense contributor provenance so later overlap
normalization cannot silently corrupt executable-region counts or mapping
lineage. PIE-versus-DSO and GNU-property IBT/SHSTK evidence remain separate
Sprint 12 gates.

## Sprint 12 Patch 064 internal role evidence

Patch 064 does not change the public `PIE indicator`. It adds bounded internal
facts for ELF type, entrypoint, `PT_INTERP`, `DT_FLAGS_1 & DF_1_PIE`, and
validated `DT_SONAME` string evidence, then classifies the evidence as unknown,
executable-like, shared-object-like, ambiguous, or contradictory. `ET_DYN`
alone remains unknown in this internal lattice. A raw SONAME tag or index is not
role evidence until it resolves to a bounded, nonempty, in-range,
NUL-terminated string. Patch 065 further requires the bounded `PT_INTERP` path
to contain a non-NUL byte, have no interior NUL, and end in a terminal NUL, and
validates every `DT_SONAME` carrier.

Duplicate or conflicting role carriers are contradictory rather than
first-wins or last-wins. Dynamic role tags use the existing bounded `PT_DYNAMIC`
view. No new public mitigation field is emitted; the Patch 068 candidate
carries the corrected role facts and separate GNU-property parser gate.

## Sprint 12 Patch 065 private GNU-property evidence

Patch 065 added bounded internal acquisition of x86 IBT and SHSTK GNU-property
facts; the Patch 068 candidate preserves the corrected alignment and overlap
boundaries without publishing a new mitigation field. Exact duplicate
`PT_NOTE`/`PT_GNU_PROPERTY` physical carriers share one canonical view, while
every original PHDR contributor remains retained. Recognized GNU property notes
produce private unknown, absent, present, or contradictory feature states.
No recognized feature record yields unknown; a missing bit in the OR aggregate
yields absent; a bit in the AND aggregate yields present; and a bit present in
OR but absent from AND yields contradictory. Unknown property types and feature
bits remain bounded facts. Malformed or truncated structures fail with exit 5
before stdout, while explicit cap exhaustion fails with exit 6 before stdout.

These facts do not prove runtime CET enforcement, full control-flow integrity,
safety, or exploitability. A later public-policy gate must preserve evidence,
unknowns, duplicates, conflicts, the separate natural/metamorphic diagnostic
matrix, bounded external reconciliation, and parity before changing text or JSON
output.


## Sprint 12 Patch 066 metamorphic evidence gate

Patch 066 adds no public mitigation indicator. Its 28-object controlled preflight
requires private role and IBT/SHSTK states to remain invariant across canonical
and exact-dual carrier encodings, preserves exact contributor differences, and
exercises unknown, conflicting, ordering, and role-contradiction mutants. This
is a development gate, not evidence of runtime CET enforcement.


## Sprint 12 Patch 067 private-fact attestation boundary

Patch 067 changes no public mitigation indicator. It attests the development
probe layout used to inspect private PIE/DSO and GNU-property states and
introduced corpus-custody and public-field-leakage oracle corrections.
Subsequent validation assigned the remaining gaps to Patch 068. Static
IBT/SHSTK property facts remain private evidence and do not establish runtime
CET enforcement. Layout reconciliation does not establish parser, classifier,
or analyzer behavior.

## Sprint 12 Patch 068 private-fact diagnostic agreement boundary

Patch 068 defines a private binary-role and GNU-property agreement gate over 48
held-out natural toolchain-produced objects and 48 controlled metamorphic
objects. The matrix keeps the two strata separate and exercises aliases,
conflicts, unknown bits, role contradictions, and malformed property layouts.
It remains diagnostic, unfrozen, publication-ineligible, and not prevalence
evidence. It does not add public PIE/DSO, IBT, or SHSTK fields and does not treat
static GNU properties as proof of runtime CET enforcement. A later policy gate
owns any compatible public `0.2.x` decision.

## Sprint 12 Patch 069 external evidence reconciliation

Patch 069 retains private binary-role and GNU-property facts and compares only
eligible represented fields against authenticated GNU `readelf -hW`, `-lW`,
`-dW`, and `-nW` output. Direct and reproducibly derived cells may be compared;
ambiguous, unavailable, corrupt, malformed, and inapplicable cells remain
explicit. The controlled diagnostic matrix records 1,224 eligible matches and
zero unexplained eligible mismatches without converting `readelf` into parser or
runtime authority.

No public PIE/DSO, IBT, or SHSTK field is added. Static properties remain
mitigation indicators and do not prove runtime CET enablement, complete control-
flow integrity, safety, or exploitability.
