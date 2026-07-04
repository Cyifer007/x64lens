# ADR 0020: Section-label annotations without loader authority

## Status

Accepted for Sprint 8 Patch 034.

## Context

x64lens now has a bounded section-header metadata seam for stripped-status reporting. The next useful analyst-facing layer is to label executable regions and gadget candidates with nearby section names when a safe section-name table is available.

Section headers are not loader authority. A stripped binary can remove or alter section metadata while program headers still define the runtime mapping. x64lens must therefore keep `PT_LOAD + PF_X` as the only source of executable-region truth and treat section names as optional annotations.

## Decision

Patch 034 adds bounded section-label annotations for executable regions and gadget candidates.

- A validated section-header table is required before any section entry is inspected.
- A bounded `e_shstrndx` string table is required before names are emitted.
- Section names must be non-empty and null-terminated inside the bounded string table.
- `SHT_NULL`, `SHT_NOBITS`, zero-sized sections, and file-range-invalid sections are skipped for labels.
- Labels are attached only after loader-derived regions and scanner-derived candidates already exist.
- Labels never create, delete, resize, reorder, or score executable regions or candidates.

Patch 034 also clarifies compatibility for the additive `stripped` JSON field: current reports emit it, but the schema and validator accept older same-version `0.1.0-dev` reports that do not contain it.

## Consequences

Human and JSON reports become easier to triage because `.text` and future section names can be associated with region and candidate records. The output remains conservative: missing or unsafe section-name evidence yields unlabeled records rather than guessed labels.

The section-label seam prepares Sprint 9 evidence-provenance work, where annotations can be marked as loader-derived, section-derived, dynamic-derived, exact-pattern-derived, or classifier-derived.
