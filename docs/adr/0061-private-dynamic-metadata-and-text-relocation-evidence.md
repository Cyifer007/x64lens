# ADR 0061: Private Dynamic Metadata and Text-Relocation Evidence

## Status

Historical design record for the Sprint 12 Patch 075 implementation candidate.
Its review required the Patch 076 corrective pass. Patch 076 preserved the
bounded private text-relocation side-car and extended it with distinct private
RPATH/RUNPATH evidence, but its review required the Patch 077 correction, whose
review required the Patch 078 closeout correction, whose review required the current Patch 079 corrective and task-value candidate and Sprint 13 entry
candidate. Public projection remains deferred.

## Context

The loader and mitigation review identified two bounded dynamic-table tranches
that improve hardening analysis without requiring a decoder: text-relocation
evidence and distinct runtime search-path evidence. Patch 075 introduced the
first tranche, and Patch 076 preserved and extended it. The implementation must preserve
program headers as runtime mapping
authority, avoid reporter inference, retain duplicate and contradiction facts,
and keep private development evidence outside schema `0.2.0`.

## Decision

Add `src/dynamic_metadata.asm` as a private side-car module. The existing
3,160-byte GNU-property context remains at offset zero. A 2,128-byte dynamic
context follows it, producing a 5,288-byte composite private metadata buffer.
The new context retains at most 64 represented `DT_TEXTREL` and `DT_FLAGS`
carriers. Each record stores the tag, dynamic-table index, checked file offset,
and raw value.

A complete bounded `PT_DYNAMIC` table yields one private text-relocation state:

- `unknown` when complete negative evidence is unavailable;
- `absent` when the table terminates and no carrier indicates text relocation;
- `present` when `DT_TEXTREL` or consistent `DF_TEXTREL` evidence is present;
- `contradictory` when duplicate `DT_FLAGS` carriers disagree specifically on
  the `DF_TEXTREL` bit.

Duplicate full values and text-relocation semantic disagreement remain separate
facts. Unrelated `DT_FLAGS` bit differences do not manufacture a text-relocation
contradiction. On `mitigations`, `gadgets`, and `analyze`, carrier 65 returns
exit code 6 with empty stdout. The `info` command does not parse `PT_DYNAMIC`.

## Boundaries

The side-car does not map files, resolve paths, parse sections, scan candidates,
classify gadgets, score records, or format reports. It adds no CLI option, text
field, JSON field, schema revision, PIE reinterpretation, or runtime-CET claim.
Section headers remain bounded metadata and annotations; executable selection
continues to use file-backed `PT_LOAD + PF_X` ranges.

## Consequences

Patch 076 extended the same bounded side-car with separate `DT_RPATH` and
`DT_RUNPATH` carrier/value evidence while preserving the Patch 075 prefix. The
two families remain distinct and are not collapsed into one security label.
Public projection still requires a later explicit policy and compatibility
gate. Patch 078 preserves these private facts without making that policy
decision and adds no public field.
