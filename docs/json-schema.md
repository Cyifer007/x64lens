# JSON Schema Contract

## Purpose

JSON is the machine-consumer contract for automation, benchmark extraction,
vulnerability-management enrichment, future CI policies, and reproducible
research. It is generated from internal records, never by scraping
human-readable output.

## Current versions

```text
tool version:   0.1.0-dev
schema version: 0.2.0
```

Tool and schema versions are independent. Patch 040 intentionally advances the
schema while retaining the tool development version.

## Report producers

```bash
x64lens gadgets --format json [--max-depth N] <file>
x64lens analyze --format json [--max-depth N] <file>
```

Both commands use the same record-backed pipeline and JSON adapter. Schema
`0.2.0` distinguishes the producing command without creating a second report
implementation.

## Schema `0.2.0` shape

Required top-level fields:

```json
{
  "schema_version": "0.2.0",
  "tool": "x64lens",
  "tool_version": "0.1.0-dev",
  "report_type": "analysis",
  "command": "gadgets",
  "analysis": {},
  "target": {},
  "mitigations": {},
  "counts": {},
  "primitive_coverage": {},
  "gadgets": [],
  "limitations": []
}
```

`command` is `gadgets` or `analyze`.

## Analysis completeness object

Current reports require:

```json
{
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
```

Field rules:

- `candidate_count <= candidate_capacity`.
- `candidate_count == counts.raw_candidate_count`.
- `regions_scanned <= regions_total`.
- When `candidate_dropped_count_known` is false, the dropped count is `null`.
- Truncated analysis is not complete.
- Complete analysis is not truncated, has known dropped count zero, and scans
  every executable region.
- Current producer output is complete-success output only.

The scanner still stops at the 4097th candidate and returns exit code `6` before
report emission. That path produces no text or JSON report, so no dropped count
is guessed.

## Existing field rules

- Virtual addresses and file offsets are fixed-width hexadecimal strings.
- Sizes, counts, known stack deltas, and scores are JSON numbers.
- Unknown stack deltas use `null` with `stack_delta_known: false`.
- Unknown or unscored scores use `null`.
- Booleans are JSON booleans.
- Unknown mitigation facts use `null` or an explicit enumerated state.
- `limitations` is non-empty because candidate recognition remains heuristic.
- Semantic and score fields come from classifier and scoring records.
- `mitigations.relro` is `none`, `partial`, or `full`.
- `mitigations.canary` is `unknown`, `absent`, or `present`.
- `mitigations.stripped`, when present in historical reports, is `unknown`,
  `stripped`, or `not_stripped`; current reports emit it.
- Optional gadget `section` values are strings or `null` and remain annotations.

## Count separation

Schema `0.2.0` preserves the historical meanings of:

```text
raw_candidate_count
ret_count
ret_imm16_count
exact_pattern_count
semantic_candidate_count
unknown_candidate_count
scored_candidate_count
```

The `analysis` object explains completion; it does not redefine these counts.
Future decoder-validity metrics will be additive.

## Current limitations

- The scanner is byte-oriented and is not a full x86_64 decoder.
- Pattern labels describe exact suffix evidence, not complete decoded windows.
- Per-candidate evidence side-car fields are not yet emitted.
- CET and IBT indicators are not complete.
- Canary and stripped values are evidence-qualified indicators.
- Scores are heuristic and are not exploitability verdicts.

## Validation

Controlled `gadgets` report:

```bash
./build/x64lens gadgets --format json --max-depth 4 \
  ./tests/bin/gadgets > /tmp/x64lens-gadgets.json
python3 tools/validate-json-report.py \
  --mode fixture --require-schema 0.2.0 --expected-command gadgets \
  /tmp/x64lens-gadgets.json
```

Integrated `analyze` report:

```bash
./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/gadgets > /tmp/x64lens-analysis.json
python3 tools/validate-json-report.py \
  --mode fixture --require-schema 0.2.0 --expected-command analyze \
  /tmp/x64lens-analysis.json
```

Historical and current compatibility:

```bash
make schema-compat-smoke
```

The validator checks identity, completeness, count relationships, primitive
coverage, candidate fields, score ranges, unknown stack-delta representation,
mitigation conditionals, and limitations.

## Historical schema `0.1.0`

Schema `0.1.0` remains available at:

```text
schemas/x64lens-report-0.1.0.schema.json
tests/expected/x64lens-report-0.1.0.json
```

The bundled validator accepts representative `0.1.0` reports when invoked with
`--require-schema 0.1.0`. Command identity cannot be required from that version
because the fields did not exist.

The current schema remains:

```text
schemas/x64lens-report.schema.json
```

## Compatibility rule

- Historical `0.1.0` reports remain consumable through the versioned schema and
  validator path.
- Current producer output must validate as `0.2.0` with the expected command.
- Compatible future additions should remain in `0.2.x`.
- Required-field removal, incompatible type changes, or semantic redefinition
  requires a documented breaking version.
- Benchmark campaigns must not merge incompatible schema versions without
  explicit normalization.

## Remaining Sprint 9 provenance work

Schema `0.2.0` establishes the report envelope but does not yet emit
per-candidate evidence. A later Sprint 9 patch will add evidence kind, validator
identity, and decoder-validity state from a side-car record keyed by candidate
index.

## Change checklist

Every schema change requires updates to:

1. `include/constants.inc`,
2. schema files,
3. `src/report_json.asm`,
4. `tools/validate-json-report.py`,
5. controlled JSON fixtures,
6. benchmark extractors,
7. this document,
8. `CHANGELOG.md`,
9. migration notes,
10. both `gadgets` and `analyze` validation.
