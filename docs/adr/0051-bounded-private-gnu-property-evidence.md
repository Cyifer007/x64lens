# ADR 0051: Bounded Private GNU-Property Evidence

## Status

Accepted for Sprint 12 Patch 065.

## Context

The current mitigation model reserves x86 IBT and SHSTK indicators until GNU
property notes can be parsed through bounded, hostile-input-safe evidence.
`PT_NOTE` and `PT_GNU_PROPERTY` can describe the same physical bytes, distinct
notes may overlap, and duplicate feature records may agree or conflict. Treating
one program header or one external-tool label as authoritative would lose
provenance and could overstate control-flow protection.

Patch 064 also introduced a private PIE/DSO role lattice. Review found two build
errors, incomplete `PT_INTERP` and `DT_SONAME` validation, a classifier that
re-read mapped ELF bytes, corpus mode-repair races, symlink-following permission
normalization, and an interrupted private-overlay directory-inventory gap. Those
correctness issues must be closed before another metadata parser becomes an
evidence authority.

## Decision

Add a bounded private GNU-property evidence module with this pipeline:

```text
validated program headers
  -> canonical exact physical carrier views
  -> original PHDR contributor records
  -> bounded ELF note records
  -> bounded 8-byte-aligned GNU property records
  -> private x86 FEATURE_1 AND facts
  -> private IBT and SHSTK states
```

The implementation:

- accepts file-backed `PT_NOTE` and `PT_GNU_PROPERTY` carriers;
- canonicalizes only exact duplicate offset/size ranges;
- retains every original PHDR index and type as a contributor;
- records partial carrier overlap instead of merging it;
- requires bounded ELF note headers, names, descriptors, alignment, and padding;
- preserves the carrier note-alignment policy: represented `PT_NOTE` streams
  use four- or eight-byte alignment, while ELF64 `PT_GNU_PROPERTY` requires
  native eight-byte alignment;
- interprets only owner `GNU\0`, note type `NT_GNU_PROPERTY_TYPE_0`, and the
  represented `GNU_PROPERTY_X86_FEATURE_1_AND` property;
- preserves unknown property types and unknown feature bits as bounded facts;
- distinguishes unknown, absent, present, and contradictory IBT/SHSTK states;
- rejects malformed recognized records before public output;
- returns stable unsupported status when explicit caps are exceeded.

The fixed command-lifetime property context is 3,160 bytes. The internal
`phdr_summary` grows from 200 to 264 bytes. Neither value is a measured RSS
result.

## Public-output boundary

Patch 065 does not change text output, JSON schema `0.2.0`, the historical PIE
indicator, candidate counts, semantic classes, or scores. The new facts remain
private until positive, negative, unknown, duplicate, conflicting, malformed,
and held-out system cases justify a separate public-policy decision.

## Module boundary

`gnu_property.asm` may consume validated file-backed carriers and populate the
private property context and bounded summary facts. It must not map files,
select executable regions, scan candidates, classify gadgets, score, or format
reports.

`binary_role.asm` consumes only completed summary facts. It must not read the
mapped ELF header or dynamic/string bytes.

## Consequences

- Program headers remain loader and executable-region authority.
- Exact duplicate physical carriers do not double-count one note.
- Original PHDR provenance is not lost through canonicalization.
- Partial overlap and conflicting feature records remain visible.
- Public mitigation language remains conservative until a later gate.
- The dependency-free, decoder-free, one-worker runtime profile is preserved.
- Native and Docker validation must prove identical facts and unchanged public
  output before Patch 065 is accepted.
