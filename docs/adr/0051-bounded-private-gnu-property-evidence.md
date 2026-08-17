# ADR 0051: Bounded Private GNU-Property Evidence

## Status

Accepted fact-acquisition architecture. The original Patch 065 implementation
did not pass validation. Patch 066 corrected its parser and evidence-boundary
findings, Patch 067 added private layout attestation, Patch 068 introduced an
intermediate diagnostic matrix, and Patch 069 added authenticated external
reconciliation. Patch 071 supplied the first development-evidence correction.
Patches 070, 071, 072, and 073 were not accepted at their respective first
returned review boundaries. Patch 073 delivered the first custody/isolation
correction and the non-reinterpretive policy deferral. Patch 074 was the
superseded Sprint 12 closeout candidate. Patch 075 introduced bounded private
static text-relocation evidence. Patch 076 preserved that private prefix without
changing this GNU-property runtime boundary and implemented distinct private
`DT_RPATH` and `DT_RUNPATH` carrier/value evidence, but its review required the
Patch 077 correction. Patch 078 then became the Sprint 13 entry candidate,
and its review required the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080. Current validation expectations are in the
[Patch 089 validation record](../sprints/sprint-13-patch-089-validation.md).

## Context

The current mitigation model reserves x86 IBT and SHSTK indicators until GNU
property notes can be parsed through bounded, hostile-input-safe evidence.
`PT_NOTE` and `PT_GNU_PROPERTY` can describe the same physical bytes, distinct
notes may overlap, and duplicate feature records may agree or conflict. Treating
one program header or one external-tool label as authoritative would lose
provenance and could overstate control-flow protection.

Patch 064 also introduced a private PIE/DSO role lattice. Patch 065 corrected the
Patch 064 build and parser errors, restored the summary-only classifier boundary,
authenticated corpus repair before mutation, and prevented permission
normalization from following links into generated evidence before inserting the
new metadata parser. Patch 066 carries those role corrections forward.

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
- increments the private overlap fact and rejects every non-identical physical
  carrier overlap as malformed before property facts reach a reporter;
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

The fixed caps are 32 canonical carriers, 64 original contributors, 32 retained
recognized notes, 256 scanned note headers, 256 property entries, a 65,536-byte
property descriptor, and a 1 MiB carrier span. Canonical note-name,
note-descriptor, property, and tail padding bytes must be zero.

The fixed command-lifetime property context is 3,160 bytes. The internal
`phdr_summary` grows from 200 to 264 bytes. Neither value is a measured RSS
result.

## Public-output boundary

Patch 065 does not add a public text or JSON report field, change schema `0.2.0`,
change the historical `mitigations.pie` indicator, alter candidate counts,
semantic classes, or scores, or publish IBT/SHSTK indicators. Controlled inputs
that differ only in private feature facts must produce byte-identical public text
and JSON. The new facts remain private until positive, negative, unknown,
duplicate, conflicting, and malformed controlled cases, the separate
natural/metamorphic diagnostic matrix, bounded external ELF reconciliation, and
native/container private-fact parity justify a separate public-policy decision.

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
- Partial carrier overlap remains observable as a failure fact and is rejected
  before any property state reaches a reporter.
- Conflicting feature records produce private contradictory states rather than
  being silently collapsed or treated as parser errors.
- Public mitigation language remains conservative until a later gate.
- The dependency-free, decoder-free, one-worker runtime profile is preserved.
- Patch 069 added authenticated external reconciliation without changing public
  report fields. Patch 079 preserved those fields and was superseded by Patch
  080, which was superseded by Patch 081. Patch 073 executed the public-policy
  gate as `defer`. Patches 081 through 088 did not complete acceptance; Patch 089 is
  the current exact-source
  implementation candidate, and any future public field requires a new separately
  reviewed decision.
