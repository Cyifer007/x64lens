# JSON Schema Contract

## Purpose

JSON is the machine-consumer contract for automation, benchmark extraction, vulnerability-management enrichment, future CI policies, and reproducible research. It is generated from internal records, never by scraping human-readable output.

## Current versions

```text
tool version:   0.1.0-dev
schema version: 0.1.0
```

Tool and schema versions are independent. A tool release can preserve the schema. A schema change must be documented and validated across every command that emits it.

## Current report producers

```bash
x64lens gadgets --format json [--max-depth N] <file>
x64lens analyze --format json [--max-depth N] <file>
```

Both commands currently emit the same record-backed analysis shape. `analyze` is an integrated command, but it does not create a second JSON implementation.

## Schema `0.1.0` shape

Required top-level fields:

```json
{
  "schema_version": "0.1.0",
  "tool": "x64lens",
  "tool_version": "0.1.0-dev",
  "target": {},
  "limitations": []
}
```

Current report sections:

- `target`,
- `mitigations`,
- `counts`,
- `primitive_coverage`,
- `gadgets`,
- `limitations`.

## Current field rules

- Virtual addresses and file offsets are fixed-width hexadecimal strings.
- Sizes, counts, known stack deltas, and scores are JSON numbers.
- Unknown stack deltas use `null` with `stack_delta_known: false`.
- Unknown or unscored scores use `null`.
- Booleans are JSON booleans.
- Unknown mitigation facts use `null` or an explicit enumerated state.
- `limitations` is non-empty when the analysis is heuristic or incomplete.
- Semantic and score fields come from classifier and scoring records.
- Patch 030 mitigation fields `bind_now`, `dynamic_entry_count`, and `dynamic_terminated` are optional compatible fields in schema `0.1.0`; non-dynamic binaries use `null`, `0`, and `null` respectively.

## Count separation

Schema `0.1.0` preserves:

```text
raw_candidate_count
ret_count
ret_imm16_count
exact_pattern_count
semantic_candidate_count
unknown_candidate_count
scored_candidate_count
```

The report must not collapse these into one generic gadget count.

## Current limitations

- The scanner is byte-oriented and not a full x86_64 decoder.
- Pattern labels describe exact suffix evidence, not complete decoded windows.
- Baseline RELRO does not yet distinguish partial from full RELRO.
- Bind-now evidence is reported separately and is not yet collapsed into full RELRO.
- Canary, stripped, CET, and IBT indicators are not yet complete.
- Candidate completeness and truncation are not represented in schema `0.1.0`.
- Scores are heuristic and are not exploitability verdicts.

## Validation

Controlled fixture:

```bash
./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/gadgets > /tmp/x64lens-analysis.json
python3 -m json.tool /tmp/x64lens-analysis.json >/dev/null
python3 tools/validate-json-report.py \
  --mode fixture /tmp/x64lens-analysis.json
```

System binary:

```bash
./build/x64lens analyze --format json --max-depth 4 \
  /bin/ls > /tmp/x64lens-ls.json
python3 tools/validate-json-report.py \
  --mode system /tmp/x64lens-ls.json
```

The validator checks required fields, count relationships, primitive coverage shape, candidate fields, score ranges, unknown stack-delta representation, mitigation optional-field types, non-dynamic dynamic-table nullability rules, and limitations.

## Planned schema `0.2.0`

Schema `0.2.0` is planned for Sprint 9. The transition is triggered by new durable concepts, not by command naming alone.

Planned concepts:

- top-level `report_type` or command identity,
- analysis completeness,
- candidate capacity and truncation,
- evidence provenance,
- decoder validation state,
- mitigation evidence and confidence,
- additional provenance-aware counts.

Illustrative shape:

```json
{
  "schema_version": "0.2.0",
  "report_type": "analysis",
  "analysis": {
    "complete": true,
    "candidate_capacity": 4096,
    "candidate_truncated": false,
    "regions_scanned": 1,
    "regions_total": 1
  },
  "gadgets": [
    {
      "evidence": {
        "kind": "semantic_exact",
        "full_sequence_valid": null,
        "validator": "x64lens-exact-suffix"
      }
    }
  ]
}
```

The exact names are finalized before implementation. See [`design/schema-evolution.md`](design/schema-evolution.md) and [`design/evidence-provenance-model.md`](design/evidence-provenance-model.md).

## Compatibility rule

- Compatible optional mitigation fields may be added while `0.1.0` remains active.
- Evidence provenance or changed count meaning requires `0.2.0`.
- Required-field removal, incompatible type changes, or semantic redefinition requires a documented breaking version.
- Benchmark campaigns must not merge rows from incompatible schema versions without explicit normalization.

## Change checklist

Every schema change requires updates to:

1. `include/constants.inc`,
2. `schemas/x64lens-report.schema.json`,
3. `src/report_json.asm`,
4. `tools/validate-json-report.py`,
5. controlled JSON fixtures,
6. benchmark extractors,
7. this document,
8. `CHANGELOG.md`,
9. migration notes,
10. both `gadgets` and `analyze` validation.
