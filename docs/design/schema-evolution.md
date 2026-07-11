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
- `make schema-compat-smoke` accepts retained representative final-shape reports
  from both versions and rejects inconsistent `0.2.0` states.
- The historical snapshot policy does not guarantee every intermediate
  pre-release `0.1.0` emission; historical reports are not rewritten in place.
- Benchmark rows from incompatible schemas are not aggregated without explicit
  normalization.

## Remaining Sprint 9 additions

Patch 041 implements the optional per-candidate `evidence` object and requires it
for current-producer validation. Patch 042 adds external decoder-gap artifacts
without changing the `0.2.0` runtime report.

Remaining work is to review the controlled and selected-system campaign,
classify boundary and coverage disagreements, and record the embedded-decoder
decision. A future decoder must augment raw and exact facts through side-car
records rather than replace them.

Target digests are recorded in Patch 042 comparison manifests. Adding a digest
to the runtime report remains a separate compatible `0.2.x` decision after the
runtime hashing source, cost, and validation rules are fixed.

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


## Sprint 9 Patch 041 compatible provenance extension

Patch 041 keeps `schema_version` at `0.2.0`. The formal schema adds an optional
candidate `evidence` object so initial Patch 040 reports remain valid. Current
producer validation requires evidence on every candidate with
`--require-provenance`.

This separates two compatibility questions:

- **Can a schema `0.2.0` consumer read an earlier report?** Yes; the Patch 040
  fixture remains formally valid.
- **Does a report satisfy the current producer contract?** Only when every
  candidate carries internally consistent provenance.

Draft 2020-12 validation is authoritative for structural constraints. The
bundled semantic validator remains authoritative for relationships that compare
sibling properties or arrays, such as count equality, coverage agreement, and
suffix-range reconciliation.
