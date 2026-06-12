# Sprint 05 Patch 017 Validation Notes

## Status

Validated locally and in Docker.

Patch 017 adds the first scoring and JSON output path. The implementation validated after Docker became reachable in the WSL environment. An earlier `docker` command lookup failure was an environment availability issue, not a code or fixture failure, because the same `make docker-test` target passed after Docker integration was active.

## What changed

Patch 017 implements:

- initial `x64lens_scoring_apply` in `src/scoring.asm`,
- `GADGET_SCORE` population for classified exact suffix patterns,
- `GADGET_SUMMARY_SCORED_COUNT`,
- `gadgets --format json`,
- `--format` and `--max-depth` parsing in either order,
- initial JSON reporter in `src/report_json.asm`,
- decimal number rendering for JSON through `print_u64_dec`,
- expanded controlled gadget fixture coverage for `rcx`, `r8`, `r9`, and `rsp`,
- JSON parsing checks in `tests/run-tests.sh`,
- `make json-smoke`,
- scanner smoke benchmark `scored_candidate_count`,
- documentation and contract updates.

## Required validation commands

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

## Expected controlled fixture text signals

```text
Candidate count: 0x000000000000000b
ret count: 0x000000000000000a
ret imm16 count: 0x0000000000000001
Exact pattern count: 0x000000000000000b
Semantic primitive count: 0x000000000000000b
Scored candidate count: 0x000000000000000b
unknown_candidate count: 0x0000000000000000
arg_control count: 0x0000000000000006
syscall_num_control count: 0x0000000000000001
syscall_trigger count: 0x0000000000000001
stack_pivot count: 0x0000000000000002
alignment count: 0x0000000000000001
Register coverage: rax|rcx|rdx|rsi|rdi|rsp|r8|r9
```

Expected score signals:

```text
pattern: pop rdi; ret, semantic: arg_control, regs: rdi, stack delta: 0x0000000000000010, score: 90
pattern: pop rcx; ret, semantic: arg_control, regs: rcx, stack delta: 0x0000000000000010, score: 90
pattern: pop r8; ret, semantic: arg_control, regs: r8, stack delta: 0x0000000000000010, score: 90
pattern: pop r9; ret, semantic: arg_control, regs: r9, stack delta: 0x0000000000000010, score: 90
pattern: pop rax; ret, semantic: syscall_num_control, regs: rax, stack delta: 0x0000000000000010, score: 85
pattern: pop rsp; ret, semantic: stack_pivot, regs: rsp, stack delta: 0x0000000000000000, score: 70
pattern: leave; ret, semantic: stack_pivot, regs: rsp, stack delta: 0x0000000000000000, score: 75
pattern: syscall; ret, semantic: syscall_trigger, regs: none, stack delta: 0x0000000000000008, score: 85
pattern: ret imm16, semantic: alignment, regs: none, stack delta: 0x0000000000000018, score: 40
```

## Expected JSON signals

The JSON report should parse successfully and include:

```json
{
  "schema_version": "0.1.0",
  "tool": "x64lens",
  "tool_version": "0.1.0-dev",
  "counts": {
    "raw_candidate_count": 11,
    "exact_pattern_count": 11,
    "semantic_candidate_count": 11,
    "scored_candidate_count": 11
  }
}
```

The `pop rsp; ret` and `leave; ret` records should expose stack-pivot uncertainty:

```json
{
  "semantic_class": "stack_pivot",
  "controls": ["rsp"],
  "stack_delta": null,
  "stack_delta_known": false
}
```


## Observed validation result

The Patch 017 validation path completed successfully with these signals:

```text
make script-perms-check -> script-perms-check: ok
make scaffold-check -> scaffold-check: ok
make diagrams-check -> diagrams-check: ok
make clean && make -> build/x64lens linked
make samples -> controlled binaries rebuilt
make test -> tests: ok
make docker-test -> tests: ok after Docker became reachable
make validate-gadget-fixture -> validate-gadget-fixture: ok
make semantic-smoke -> validate-gadget-fixture: ok
make json-smoke -> json-smoke: ok
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke -> scanner-smoke benchmark complete
```

Controlled fixture text output confirmed 11 raw candidates, 11 exact patterns, 11 semantic primitives, 11 scored candidates, six argument-control primitives, two stack-pivot primitives, one syscall-number primitive, one syscall-trigger primitive, one alignment primitive, and register coverage for `rax|rcx|rdx|rsi|rdi|rsp|r8|r9`.

Controlled fixture JSON output parsed successfully in both supported flag orders:

```bash
x64lens gadgets --format json --max-depth 4 ./tests/bin/gadgets
x64lens gadgets --max-depth 4 --format json ./tests/bin/gadgets
```

The JSON reports included `schema_version`, `tool`, `tool_version`, `target`, `mitigations`, separated `counts`, `primitive_coverage`, `gadgets`, and `limitations`. The `pop rsp; ret` and `leave; ret` records represented unknown stack deltas as `null` with `stack_delta_known:false`.

## Failure triage

- If build fails, inspect `src/report_json.asm`, `src/scoring.asm`, and `src/main.asm` first.
- If text counts are wrong, inspect `tests/toy-src/gadgets.S`, `patterns.asm`, `classifier.asm`, and `scoring.asm` in that order.
- If JSON does not parse, inspect comma placement in `src/report_json.asm`.
- If JSON counts differ from text counts, inspect `GADGET_SUMMARY_*` offsets in `include/structs.inc` and the reporter field mapping.
