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

Tool and schema versions are independent. Patch 040 intentionally advanced the
schema while retaining the tool development version. Patch 041 adds candidate
provenance compatibly within the `0.2.x` line.

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

## Candidate evidence object

Current Patch 041 producers emit an `evidence` object for every gadget record:

```json
{
  "kind": "semantic_exact",
  "raw_candidate": true,
  "exact_suffix": true,
  "semantic_source": "exact",
  "validator": "x64lens-exact-suffix",
  "matched_suffix_offset": 2,
  "matched_suffix_length": 2,
  "full_sequence_valid": null
}
```

Rules:

- `raw_candidate` is always true for an emitted candidate record.
- `exact_suffix` agrees with whether `pattern` is other than `unknown`.
- A known semantic class requires `semantic_source` to identify `exact` or a
  future implemented `decoded` source.
- Exact suffix offset and length are measured inside the retained `bytes`
  window and must end at its terminator.
- `full_sequence_valid` remains `null` for current exact-suffix evidence.
- `kind` identifies the strongest represented evidence layer without erasing
  weaker raw or exact facts.

The formal schema keeps this object optional so Patch 040 `0.2.0` reports remain
consumable. Current producer validation requires it through
`--require-provenance`.

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
- Per-candidate raw, exact-suffix, and semantic-exact provenance is emitted;
  decoder validity is not yet implemented.
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
  --require-provenance --require-sprint10-effects /tmp/x64lens-gadgets.json
```

Integrated `analyze` report:

```bash
./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/gadgets > /tmp/x64lens-analysis.json
python3 tools/validate-json-report.py \
  --mode fixture --require-schema 0.2.0 --expected-command analyze \
  --require-provenance --require-sprint10-effects /tmp/x64lens-analysis.json
```

Historical and current compatibility:

```bash
make schema-compat-smoke
```

The formal Draft 2020-12 schemas validate representative historical and current
documents. The semantic validator checks identity, completeness, count
relationships, primitive coverage, candidate evidence, suffix ranges, score
ranges, unknown stack-delta representation, mitigation conditionals, and
limitations. `python3-jsonschema` is required only for development and CI
validation, not by the runtime binary.

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

- Retained representative final-shape `0.1.0` fixtures remain consumable through
  the versioned schema and validator path. This is a pre-release snapshot policy,
  not a promise that every intermediate report ever emitted under `0.1.0` still
  satisfies the final historical snapshot.
- Current producer output must validate as `0.2.0` with the expected command.
- Compatible future additions should remain in `0.2.x`.
- Required-field removal, incompatible type changes, or semantic redefinition
  requires a documented breaking version.
- Benchmark campaigns must not merge incompatible schema versions without
  explicit normalization.

## Sprint 9 provenance decision

Patch 041 emitted the current per-candidate provenance surface. Patches 042-045
recorded and hardened decoder-gap comparison provenance outside the runtime
report and retained the decoder-free core with candidate-scoped validation as
an optional future profile. A runtime target digest remains a separate compatible
`0.2.x` decision if later corpus or machine-consumer requirements justify its
source, cost, and validation rules. Decoder-validity fields remain reserved and
unknown until implemented evidence exists.

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

## Sprint 9 closeout status

Schema `0.2.0` is the current producer contract. It carries top-level report and command identity, an `analysis` completeness/capacity object, and per-candidate evidence. Current successful reports describe complete bounded enumeration; candidate-capacity exhaustion still fails before report emission.

Decoder-backed validity remains optional future evidence. It must be added compatibly within `0.2.x` when possible and must not redefine raw, exact, semantic-exact, unknown, or scored counts. Historical compatibility is limited to the retained representative final-shape `0.1.0` fixture and versioned validator path.

## Sprint 10 Patch 046 effect fields

Current producers emit these compatible candidate fields:

```json
{
  "stack_pop_order": ["rdi", "rsi"],
  "clobbers": [],
  "side_effects": ["stack_read"]
}
```

- `stack_pop_order` preserves exact execution order and is empty for patterns
  without represented pops.
- `controls` remains the unordered semantic register set.
- `clobbers` contains only explicitly modeled clobber facts.
- `side_effects` contains only classifier-produced facts.

The formal schema keeps the fields optional so Patch 040 and Patch 041 schema
`0.2.0` reports remain consumable. Current-producer validation requires all
three fields and checks their relationships to pattern bytes, semantic class,
controls, stack delta, evidence range, and score.

At the Patch 046 boundary, the first generic multi-pop family used pattern text
`pop reg; pop reg; ret`, stored the exact registers in `stack_pop_order`, had a
known stack delta of 24, and remained unscored. Patch 051 preserves those facts
while calibrating the current score to 95.

## Sprint 10 Patch 047 register-transfer fields

Current producer candidates include:

```json
"register_transfer": {
  "source": "rax",
  "destination": "rdi"
}
```

Non-transfer candidates use `null`. Transfer candidates use semantic class
`reg_transfer`, empty `controls`, destination-only `clobbers`,
`side_effects:["stack_read","register_write"]`, a known stack delta of eight, and `score:null`.
The formal schema keeps the field optional for earlier schema `0.2.0` reports;
current-producer validation requires it through `--require-sprint10-transfer`.

The common validator also enforces every single-pop pattern/order/control
relationship. Aggregate register coverage is not accepted as a substitute for
per-candidate consistency.

## Sprint 10 Patch 048 stack-adjust effects

Patch 048 keeps schema version `0.2.0`. The formal side-effect enumeration adds `stack_adjust` and `flags_write`. At the Patch 048 boundary, a promoted candidate used pattern `add rsp, imm8; ret`, semantic class `alignment`, empty controls/order/clobbers, a known total stack delta of immediate plus eight, and `score:null`. Patch 051 preserves those facts while calibrating the current score to 35.

The current semantic validator derives the immediate from the exact five-byte suffix and rejects unsupported immediates, wrong deltas, missing effects, contradictory terminator labels, and nonempty bare-return controls. The fields are compatible additions: retained Patch 040, Patch 046, and Patch 047 reports remain consumable under their documented producer requirements.

## Sprint 10 Patch 049 memory-access fields

Patch 049 keeps schema `0.2.0` and adds optional candidate `memory_access`:

```json
{
  "direction": "read",
  "base": "rdi",
  "index": null,
  "scale": 1,
  "displacement": 0,
  "displacement_known": true,
  "width_bytes": 8,
  "value_register": "rax",
  "dereference": true
}
```

Non-memory candidates emit `memory_access:null`. Current producer validation reconciles the object with the exact pattern, semantic class, clobber bitmap, side effects, stack delta, score, and coverage booleans. `full_sequence_valid` remains `null` because the family is semantic-exact rather than decoder-validated.


## Sprint 10 Patch 050 current-producer effect completion

Patch 050 keeps schema version `0.2.0` and adds no structural field. It strengthens current-producer semantic relationships:

- every supported semantic candidate ending in `ret` or `ret imm16` includes `stack_read`;
- `ret imm16` additionally includes `ret_imm16` and `stack_adjust`;
- `syscall; ret` clobbers `rcx` and `r11` and includes `syscall` plus `register_write`;
- `leave; ret` clobbers `rbp`, controls the pivot relation through `rsp`, and includes `stack_pivot` plus `register_write`;
- transfer, stack-adjust, memory-read, and memory-write effects include the final return stack read;
- the transfer fixture includes one memory read and one memory write under their own implemented family.

These are current-producer requirements enforced by the semantic validator. Retained Patch 040 and Patch 046 `0.2.0` reports remain structurally consumable and are not retroactively rewritten.

## Sprint 10 Patch 051 architectural effects

Current producer reports require `architectural_effects` for each candidate; the formal schema keeps the object optional only so retained earlier `0.2.0` reports remain consumable:

```json
{
  "registers_read": ["rsp"],
  "registers_written": ["rdi", "rsp"],
  "flags_read": [],
  "flags_written": [],
  "control_flow": ["return"],
  "stack_base": "entry_rsp",
  "stack_read_count": 2,
  "stack_write_count": 0,
  "first_stack_read_offset": 0,
  "stack_read_stride": 8,
  "stack_offsets_known": true,
  "model_complete": true
}
```

The formal schema keeps the object optional so earlier schema `0.2.0` reports
remain consumable. Current-producer validation requires it through
`--require-sprint10-architectural-effects` and reconciles it with exact pattern,
semantic class, memory operands, stack facts, coarse side effects, and score.

`model_complete:false` exposes a known representational boundary; it is not a
raw-scan truncation flag and does not alter `analysis.complete`.

Current ordered two-pop candidates use score 95 and positive aligned stack-
adjustment candidates use score 35 only when their architectural effects agree
with semantic facts. Register-transfer and memory candidates remain unscored.
See the [scoring model](scoring-model.md).


## Sprint 10 Patch 052 corrective relationships

Patch 052 keeps schema `0.2.0` and changes no field shape. Current-producer
validation additionally requires:

- full-width syscall flag masks;
- valid `ret imm16 0` with total stack delta 8;
- exact canonical memory descriptors keyed to the current candidate; and
- score values that agree with the maintained family and exact-pattern
  authorities.

These are correctness constraints on current reports, not a structural schema
transition.
