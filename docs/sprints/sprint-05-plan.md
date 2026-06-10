# Sprint 05 Plan

## Status

Planned.

## Sprint goal

Add scoring, JSON output, and research-grade comparison scaffolding after semantic classification exists.

Sprint 5 should begin only after Sprint 4 produces stable semantic primitive records. Patch 015 validation satisfies that prerequisite. Scoring and JSON should be generated from internal facts, not from text output. Benchmark work should transition from development smoke tests toward reproducible research measurements.

## Planned deliverables

- [ ] Add or update a controlled semantic fixture that exercises `pop rcx; ret`, `pop r8; ret`, `pop r9; ret`, and `pop rsp; ret` before scores are exposed.
- [ ] Add explicit unknown stack-delta handling for JSON, and consider text output rendering for pivot records.
- [ ] Implement initial `scoring.asm` routine over semantic records.
- [ ] Populate `GADGET_SCORE` for exact classified patterns.
- [ ] Add explicit uncertainty or raw-pattern penalties where the scanner has not performed full decoding.
- [ ] Implement initial JSON output for `analyze` or `gadgets --format json`.
- [ ] Ensure JSON includes `schema_version`, `tool`, `tool_version`, `target`, `mitigations`, `primitive_coverage`, `gadgets`, and `limitations`.
- [ ] Add schema validation helper if practical.
- [ ] Expand benchmark harness beyond scanner smoke.
- [ ] Add ROPgadget comparison script wiring.
- [ ] Add Ropper comparison script wiring.
- [ ] Add ropr comparison script wiring if available.
- [ ] Record baseline tool versions in benchmark metadata.
- [ ] Add corpus manifest hash or manifest checksum capture.
- [ ] Update `docs/benchmark-methodology.md` with exact commands and result fields.

## Acceptance criteria

- [ ] `make clean && make && make test` succeeds.
- [ ] `make docker-test` succeeds.
- [ ] Text output still works for `info`, `mitigations`, and `gadgets`.
- [ ] JSON output is syntactically valid for at least one controlled fixture.
- [ ] Scores are present only for semantic records that the classifier can justify.
- [ ] Benchmark scripts emit raw results plus metadata sidecars.
- [ ] No performance superiority claims are made without measured comparison data.
- [ ] Sprint 5 retrospective is written.

## Suggested validation commands

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --format json ./tests/bin/gadgets > /tmp/x64lens-gadgets.json
python3 -m json.tool /tmp/x64lens-gadgets.json >/dev/null
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
```

## Design constraints

- JSON must be generated from internal records.
- Schema version and tool version must remain separate.
- Score values are hypotheses until validated.
- Benchmark scripts must preserve raw data and metadata.
- The text reporter must remain human-readable and not become the machine integration layer.

## Stretch goals

- Add `make json-smoke`.
- Add `make benchmark-baselines-smoke`.
- Add first benchmark summary script output that computes median and max RSS from TSV.

## Patch 14 reviewer-readiness additions

Sprint 5 JSON and scoring work should include limitations by design:

- JSON must include `limitations`,
- JSON should separate raw, exact, semantic, unknown, and scored counts,
- scores must be omitted or clearly neutral for `unknown_candidate`,
- benchmark scripts must record output size so printing cost is visible,
- comparison tooling must record baseline versions and exact commands.


## Sprint 5 entry conditions

Sprint 5 may begin after Patch 015 is committed and the Sprint 4 closeout/context patch is applied. The semantic classifier is stable enough for initial scoring and JSON, but score values should remain explicitly heuristic.

The recommended implementation order is:

1. add fixture coverage for currently unexercised semantic mappings,
2. define score fields and sentinel behavior for `unknown_candidate`,
3. add JSON object shape and `limitations`,
4. add schema validation smoke test,
5. expand benchmark metadata and baseline wiring.
