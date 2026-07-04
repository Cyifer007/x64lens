# Schema Evolution Plan

## Purpose

The JSON schema is a public automation contract. This plan defines when schema `0.1.0` should change and how the repository should prevent feature work from causing accidental compatibility drift.

## Current schema

Schema `0.1.0` represents the first record-backed gadget and integrated analysis report. It includes target metadata, baseline mitigations, compatible optional dynamic-table mitigation fields, separated counts, primitive coverage, candidate records, scores, and limitations.

## Compatibility classes

### Patch-compatible change

A `0.1.x` change may:

- clarify descriptions,
- tighten validators without rejecting previously valid intended reports,
- add optional limitation strings,
- add optional mitigation properties that do not change existing field meaning.

### Minor schema change

A `0.2.0` change is required when the report adds or changes a durable concept such as:

- top-level report identity,
- evidence provenance,
- candidate truncation or completeness state,
- decoder validation facts,
- mitigation evidence and confidence,
- normalized corpus or benchmark provenance fields,
- a changed meaning for an existing count.

### Breaking schema change

A new major schema version is required when required fields are removed or renamed, types change incompatibly, or existing meanings are redefined.

The project is pre-1.0, but version discipline still matters because benchmark scripts and external users consume the output.

## Planned transition

The planned schema `0.2.0` transition is the explicit provenance and completeness gate.

- Keep `0.1.0` through Sprint 8 for compatible mitigation additions.
- Introduce `0.2.0` in Sprint 9 with evidence provenance, report identity, and truncation/completeness facts.
- Freeze the `0.2.x` shape before the Sprint 13 publication benchmark campaign.
- Avoid another breaking change before `v0.1.0` unless a release-blocking correctness defect is found.

## Planned `0.2.0` additions

Candidate top-level additions:

```json
{
  "report_type": "analysis",
  "analysis": {
    "complete": true,
    "candidate_capacity": 4096,
    "candidate_truncated": false,
    "regions_scanned": 1,
    "regions_total": 1
  }
}
```

Candidate per-record additions:

```json
{
  "evidence": {
    "kind": "semantic_exact",
    "full_sequence_valid": null,
    "validator": "x64lens-exact-suffix"
  }
}
```

Candidate mitigation additions:

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

Exact field names remain subject to implementation review. The conceptual boundary is fixed before coding begins.

## Change procedure

Every schema change requires:

1. update `include/constants.inc`,
2. update `schemas/x64lens-report.schema.json`,
3. update `docs/json-schema.md`,
4. update validators and fixtures,
5. update `CHANGELOG.md`,
6. add compatibility tests,
7. update benchmark extractors,
8. document migration notes,
9. verify both `gadgets` and `analyze` output.

## Schema freeze rule

Once publication benchmark data is collected, schema changes that affect extraction require either:

- regenerating the complete campaign, or
- preserving a versioned extractor for the earlier schema and treating datasets separately.

Mixed-schema rows must not be aggregated without explicit normalization.

## Sprint 8 Patch 034 compatibility note

Patch 034 keeps schema `0.1.0` while adding optional gadget `section` annotations and relaxing `mitigations.stripped` to optional in the schema and bundled validator. Current x64lens reports still emit `mitigations.stripped`; the relaxation exists so older same-version development reports remain readable. Schema `0.2.0` remains reserved for durable provenance and completeness-state fields rather than this compatible annotation.
