# ADR 0048: Program-header validity and extended-numbering boundary

## Status

Accepted for Sprint 12 Patch 062.

## Context

Sprint 11 diagnostic work identified loader precision as the first release-facing capability risk. The existing ELF validator bounded program-header table bytes and file-backed `PT_LOAD` ranges, but it did not define all ordinary `p_align`, offset/virtual-address congruence, virtual-range, or executable-entrypoint outcomes. ELF64 extended-numbering sentinels could also be consumed as ordinary values by future paths unless they were detected before table iteration.

The reference analyzer must remain bounded, dependency-free, decoder-free, and program-header authoritative. Section headers may not become runtime mapping authority merely because ELF extended numbering stores replacement counts in section-header entry zero.

## Decision

Patch 062 introduces one shared ordinary program-header validator used by both ELF identity validation and command-level PHDR analysis.

For every ordinary program-header table, it requires:

- a complete program-header table with fixed 56-byte entries;
- `p_align` equal to zero, one, or a power of two;
- `PT_LOAD.p_filesz <= p_memsz`;
- a bounded file-backed `PT_LOAD` range;
- a non-wrapping `p_vaddr + p_memsz` exclusive end;
- `p_offset` and `p_vaddr` congruence modulo `p_align` when `p_align > 1`; and
- a nonzero ELF entrypoint inside the half-open memory range of at least one executable `PT_LOAD` segment.

A zero entrypoint remains an explicit no-entry value. An entrypoint at the exclusive end, in a gap, in a non-executable load, or without any program header is malformed.

Patch 062 also recognizes:

- `e_phnum == PN_XNUM`;
- `e_shnum == 0` with a nonzero section-table offset; and
- `e_shstrndx == SHN_XINDEX`.

It validates the fixed ELF64 section-header-zero carrier, the resolved table extent, the reserved-domain value, and the represented index range. Structurally valid extended-numbering inputs return the stable unsupported-feature status. Contradictory, truncated, overflowing, reserved-without-sentinel, or out-of-range encodings return the stable malformed-ELF status. Neither path emits partial stdout.

## Consequences

- Program headers remain executable-region and loader authority.
- Section-header zero is read only as the ABI-defined carrier for extended counts/indexes.
- Extended-numbering support is explicit rather than accidental, but full iteration over extended tables remains deferred.
- All four public analysis command paths share the same fail-closed identity gate.
- Existing CLI syntax, JSON schema `0.2.0`, candidate capacity, arena size, semantic classes, scores, decoder policy, worker policy, and runtime dependency surface remain unchanged.
- Overlapping executable segment semantics, PIE-versus-DSO identity, and GNU-property CET evidence remain later Sprint 12 patches.
