# Sprint 04 Patch 015 Validation Notes

## Status

Pending local validation.

Patch 015 adds the first semantic classifier pass. The implementation should be validated locally in WSL2 and in Docker before commit.

## What changed

Patch 015 implements:

- `x64lens_classifier_apply_exact` in `src/classifier.asm`,
- classifier invocation from `src/gadgets.asm`,
- semantic summary fields in `include/structs.inc`,
- semantic text output in `src/report_text.asm`,
- semantic checks in `tests/run-tests.sh`,
- semantic checks in `tools/validate-gadget-fixture.sh`,
- `make semantic-smoke`,
- semantic columns in `benchmarks/scripts/bench-scanner-smoke.sh`.

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
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 /bin/ls | head -n 80
```

## Expected controlled fixture output signals

```text
Candidate count: 0x0000000000000007
Exact pattern count: 0x0000000000000007
Semantic primitive count: 0x0000000000000007
unknown_candidate count: 0x0000000000000000
arg_control count: 0x0000000000000003
syscall_num_control count: 0x0000000000000001
syscall_trigger count: 0x0000000000000001
stack_pivot count: 0x0000000000000001
alignment count: 0x0000000000000001
Register coverage: rax|rdx|rsi|rdi|rsp
```

Expected candidate-level semantic facts:

```text
pattern: pop rdi; ret, semantic: arg_control, regs: rdi, stack delta: 0x0000000000000010
pattern: pop rsi; ret, semantic: arg_control, regs: rsi, stack delta: 0x0000000000000010
pattern: pop rdx; ret, semantic: arg_control, regs: rdx, stack delta: 0x0000000000000010
pattern: pop rax; ret, semantic: syscall_num_control, regs: rax, stack delta: 0x0000000000000010
pattern: leave; ret, semantic: stack_pivot, regs: rsp, stack delta: 0x0000000000000000
pattern: syscall; ret, semantic: syscall_trigger, regs: none, stack delta: 0x0000000000000008
pattern: ret imm16, semantic: alignment, regs: none, stack delta: 0x0000000000000018
```

## Acceptance decision

Patch 015 should not be considered complete until:

- local `make test` passes,
- Docker `make docker-test` passes,
- `make validate-gadget-fixture` passes,
- `make semantic-smoke` passes,
- the generated benchmark TSV includes `semantic_primitive_count` and `unknown_candidate_count` columns.

## Known limitations

- This is still exact-suffix based classification, not full instruction decoding.
- Unsupported exact patterns remain `unknown_candidate`.
- Scores remain unset.
- JSON output is still future work.
- No exploitability verdict is emitted.
