# Sprint 04 Plan

## Status

Planned.

## Sprint goal

Turn Sprint 3 raw candidates and exact suffix patterns into semantic exploit primitive facts.

Sprint 4 should not expand scanning breadth first. The highest-value next step is to consume the existing `PATTERN_*` IDs and populate semantic records. This keeps the project aligned with the architecture boundary: scanner discovers byte windows, pattern matcher tags exact suffixes, classifier maps patterns to primitive meaning.

## Planned deliverables

- [ ] Implement first real `classifier.asm` routine.
- [ ] Call classifier from `gadgets.asm` after `patterns.asm` and before reporting.
- [ ] Map exact pattern IDs into semantic classes:
  - `ret` -> `alignment`
  - `ret imm16` -> `alignment` plus nonstandard stack adjustment note later
  - `pop rdi; ret`, `pop rsi; ret`, `pop rdx; ret`, `pop rcx; ret`, `pop r8; ret`, `pop r9; ret` -> `arg_control`
  - `pop rax; ret` -> `syscall_num_control`
  - `syscall; ret` -> `syscall_trigger`
  - `leave; ret` and `pop rsp; ret` -> `stack_pivot`
- [ ] Populate `GADGET_REGS_CONTROLLED` bitmap for exact pop patterns.
- [ ] Populate first stack-delta values for exact patterns.
- [ ] Populate first side-effect flags if a minimal flag model is added.
- [ ] Add primitive coverage summary record or extend an existing summary with explicit coverage fields.
- [ ] Add text output for semantic class and controlled registers.
- [ ] Add regression tests for semantic labels and register bitmap behavior.
- [ ] Update `docs/semantic-taxonomy.md` and `docs/scoring-model.md` based on actual classifier behavior.
- [ ] Update `docs/json-schema.md` only if JSON output is implemented in this sprint.

## Acceptance criteria

- [ ] `make clean && make && make test` succeeds.
- [ ] `make docker-test` succeeds.
- [ ] `make validate-gadget-fixture` succeeds.
- [ ] `x64lens gadgets --max-depth 4 ./tests/bin/gadgets` reports semantic classes for the known fixture patterns.
- [ ] Primitive coverage includes at least argument-register control, syscall-number control, syscall trigger, stack pivot, and alignment.
- [ ] No exploitability verdicts are emitted.
- [ ] Unknown byte windows remain `unknown_candidate` rather than being forced into incorrect classes.
- [ ] Sprint 4 retrospective is written.

## Suggested validation commands

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
make validate-gadget-fixture
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 /bin/ls | head -n 60
```

## Design constraints

- Preserve the scanner/pattern/classifier/scoring separation.
- Classifier must consume internal records, not parse text output.
- Do not score gadgets until semantic class and basic side effects are available.
- Do not claim a binary is exploitable.
- Prefer conservative `unknown_candidate` over overclassification.

## Stretch goals

These are useful only if the core classifier lands cleanly:

- Add `analyze <file>` as an alias or orchestration wrapper over mitigations plus gadgets plus primitive coverage.
- Add first JSON draft behind `--format json` for controlled internal use.
- Add a fixture that contains `pop r8; ret` through `pop r15; ret` to exercise REX-prefixed patterns.
