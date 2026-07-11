# Schema Evolution Plan

## Purpose

The JSON schema is a public automation contract. This plan defines the current
schema transition and prevents feature work from causing accidental
compatibility drift.

## Current schemas

The current producer emits schema `0.2.0`. A versioned historical snapshot of
schema `0.1.0` remains available for representative compatibility validation.

Schema `0.1.0` contains target metadata, mitigation facts, separated counts,
primitive coverage, candidate records, scores, and limitations. It does not
identify the producing command or state analysis completeness.

Schema `0.2.0` adds durable report and command identity plus a bounded analysis
summary while preserving every existing count and candidate meaning.

## Compatibility classes

### Patch-compatible change

A `0.2.x` change may:

- clarify descriptions,
- strengthen cross-field validation without changing intended field meaning,
- add optional limitations,
- add optional evidence properties whose absence remains unambiguous.

### Minor schema change

A later minor change is required when the report adds another durable concept
that cannot be represented compatibly, such as a required provenance record,
required decoder state, or a changed count meaning.

### Breaking schema change

A new major schema version is required when required fields are removed or
renamed, types change incompatibly, or existing meanings are redefined.

The project is pre-1.0, but version discipline still matters because benchmark
scripts and external consumers use the output.

## Patch 040 transition to `0.2.0`

Patch 040 introduces these required top-level fields:

```json
{
  "schema_version": "0.2.0",
  "report_type": "analysis",
  "command": "gadgets",
  "analysis": {
    "complete": true,
    "max_depth": 4,
    "candidate_capacity": 4096,
    "candidate_count": 11,
    "candidate_truncated": false,
    "candidate_dropped_count": 0,
    "candidate_dropped_count_known": true,
    "regions_scanned": 1,
    "regions_total": 1
  }
}
```

`command` is `gadgets` or `analyze`. The shared report body remains generated
from one internal pipeline and one JSON adapter.

The `analysis` object follows these invariants:

- candidate count does not exceed candidate capacity,
- candidate count equals `counts.raw_candidate_count`,
- regions scanned does not exceed regions total,
- unknown dropped count is represented by `null` plus a false known flag,
- truncated analysis cannot be complete,
- complete analysis is not truncated, has known dropped count zero, and scanned
  every executable region.

Current producer output represents successful complete runs only. Candidate
capacity exhaustion still fails before report emission, so Patch 040 does not
claim a dropped count for that failure.

## Historical compatibility policy

- `schemas/x64lens-report-0.1.0.schema.json` is the historical schema snapshot.
- `schemas/x64lens-report.schema.json` is the current `0.2.0` schema.
- `tools/validate-json-report.py` accepts both versions.
- Current producer checks use `--require-schema 0.2.0` and
  `--expected-command`.
- `make schema-compat-smoke` accepts representative reports from both versions
  and rejects inconsistent `0.2.0` states.
- Historical reports are not rewritten in place.
- Benchmark rows from incompatible schemas are not aggregated without explicit
  normalization.

## Remaining Sprint 9 additions

Per-candidate provenance remains the next additive step. The intended shape is a
side-car-derived candidate `evidence` object, for example:

```json
{
  "evidence": {
    "kind": "semantic_exact",
    "full_sequence_valid": null,
    "validator": "x64lens-exact-suffix"
  }
}
```

Exact field names are finalized with the evidence record implementation. A
future decoder must augment raw and exact facts rather than replace them.

Target digests and richer mitigation evidence may also be added during Sprint 9
or a later compatible `0.2.x` patch after their data sources and validation
rules are fixed.

## Change procedure

Every schema change requires:

1. update `include/constants.inc`,
2. update current and historical schema handling as applicable,
3. update `src/report_json.asm`,
4. update `tools/validate-json-report.py`,
5. update controlled fixtures,
6. update benchmark extractors,
7. update `docs/json-schema.md`,
8. update `CHANGELOG.md`,
9. document migration behavior,
10. verify both `gadgets` and `analyze` output.

## Schema freeze rule

Once publication benchmark data is collected, schema changes that affect
extraction require either a complete rerun or a versioned extractor and separate
dataset. Mixed-schema rows must not be aggregated without explicit
normalization.

## Comparator artifacts

`readelf`, `checksec`, and `rabin2` outputs remain validation artifacts. They do
not become x64lens report fields or runtime truth sources through this schema
transition.
