# Sprint 05 Plan

## Status

In progress. Patch 017 implemented and validated the first scoring and JSON slice. Patch 018 is the Sprint 5 validation-hardening candidate.

## Sprint goal

Add scoring, JSON output, and research-grade comparison scaffolding after semantic classification exists.

Sprint 5 begins from the Sprint 4 classifier checkpoint. Scoring and JSON must be generated from internal facts, not from text output. Benchmark work should transition from development smoke tests toward reproducible research measurements without making premature performance claims.

## Patch 017 implementation scope

Patch 017 targets the first bounded Sprint 5 implementation slice:

- [x] Expand the controlled semantic fixture to exercise `pop rcx; ret`, `pop r8; ret`, `pop r9; ret`, and `pop rsp; ret`.
- [x] Implement initial `x64lens_scoring_apply` in `src/scoring.asm`.
- [x] Populate `GADGET_SCORE` for exact classified patterns.
- [x] Add `GADGET_SUMMARY_SCORED_COUNT` to the gadget summary model.
- [x] Keep `unknown_candidate` unscored.
- [x] Add explicit uncertainty-adjusted scores for exact-suffix patterns.
- [x] Implement initial `gadgets --format json` output.
- [x] Support `--format` and `--max-depth` together in either order.
- [x] Ensure JSON includes `schema_version`, `tool`, `tool_version`, `target`, `mitigations`, `counts`, `primitive_coverage`, `gadgets`, and `limitations`.
- [x] Represent unknown stack deltas as JSON `null` with `stack_delta_known: false`.
- [x] Add `make json-smoke`.
- [x] Add JSON parsing checks to `tests/run-tests.sh`.
- [x] Extend scanner smoke TSV output with `scored_candidate_count`.
- [x] Update CLI, JSON schema, scoring model, output contract, and documentation voice contract.


## Patch 018 validation-hardening scope

Patch 018 strengthens the validation process after Patch 017 scoring and JSON output validated successfully:

- [x] Add reusable JSON report validation through `tools/validate-json-report.py`.
- [x] Replace ad hoc JSON fixture assertions with the reusable validator.
- [x] Validate both supported `--format` and `--max-depth` flag orders in `make json-smoke`.
- [x] Add `make system-smoke` for real installed ELF64 x86_64 binaries.
- [x] Add `make validation-smoke` as a local pre-commit validation target.
- [x] Add `make docker-available-check` to separate Docker environment availability failures from code failures.
- [x] Add patch bundle hygiene validation for generated ZIPs.
- [x] Document Patch 017 validation evidence and Patch 018 validation expectations.

## Deferred Sprint 5 work

These remain Sprint 5 follow-up items after Patch 017 validates:

- [ ] Add schema validation through a dedicated JSON Schema validator if available in the environment.
- [ ] Expand benchmark harness beyond scanner smoke.
- [ ] Add ROPgadget comparison script wiring.
- [ ] Add Ropper comparison script wiring.
- [ ] Add ropr comparison script wiring if available.
- [ ] Record baseline tool versions in benchmark metadata.
- [ ] Add corpus manifest hash or manifest checksum capture.
- [ ] Update benchmark methodology with exact baseline commands once baseline tooling is exercised.
- [ ] Write Sprint 5 retrospective after validation.

## Acceptance criteria for Patch 017

- [x] `make normalize-perms` succeeds for Patch 017; rerun for Patch 018.
- [x] `make script-perms-check` succeeds for Patch 017; Patch 018 extends this check.
- [x] `make scaffold-check` succeeds for Patch 017; rerun for Patch 018.
- [x] `make diagrams-check` succeeds for Patch 017; rerun for Patch 018.
- [x] `make clean && make && make test` succeeds for Patch 017; rerun for Patch 018.
- [x] `make docker-test` succeeds for Patch 017 after Docker became reachable; rerun for Patch 018.
- [x] `make validate-gadget-fixture` succeeds for Patch 017; rerun for Patch 018.
- [x] `make semantic-smoke` succeeds for Patch 017; rerun for Patch 018.
- [x] `make json-smoke` succeeds for Patch 017; Patch 018 strengthens it with the reusable validator.
- [x] Text output still works for `info`, `mitigations`, and `gadgets`.
- [x] JSON output is syntactically valid for the controlled gadget fixture.
- [x] Scores are numeric only for classified/scored records and `null` for unscored JSON records.
- [x] No performance superiority claims are made without measured comparison data.

## Suggested validation commands

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make clean
make
make samples
make test
make docker-test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens gadgets --format json --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-gadgets.json
python3 -m json.tool /tmp/x64lens-gadgets.json >/dev/null
```

## Design constraints

- JSON must be generated from internal records.
- Schema version and tool version must remain separate.
- Score values are hypotheses until validated.
- Benchmark scripts must preserve raw data and metadata.
- The text reporter must remain human-readable and must not become the machine integration layer.
- Public documentation must be written as repository-facing project material, not private workflow notes.

## Patch 017 score table

| Pattern | Score |
|---|---:|
| `pop rdi; ret` | 90 |
| `pop rsi; ret` | 90 |
| `pop rdx; ret` | 90 |
| `pop rcx; ret` | 90 |
| `pop r8; ret` | 90 |
| `pop r9; ret` | 90 |
| `pop rax; ret` | 85 |
| `syscall; ret` | 85 |
| `leave; ret` | 75 |
| `pop rsp; ret` | 70 |
| `ret` | 45 |
| `ret imm16` | 40 |

These values include a small uncertainty penalty because the current implementation is exact-suffix based rather than full-decoder based.

## Additional Patch 018 acceptance criteria

- [ ] `make system-smoke` succeeds against at least one installed ELF64 x86_64 system binary.
- [ ] `make validation-smoke` succeeds locally.
- [ ] `make docker-available-check` gives a clear environment result.
- [ ] `BUNDLE=<patch.zip> make patch-bundle-hygiene` passes for the generated Patch 018 bundle.
- [ ] Public patch bundles exclude local-only context and generated artifacts; project context is distributed separately.
