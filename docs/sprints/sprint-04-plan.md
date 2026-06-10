# Sprint 04 Plan

## Status

Complete. Patch 015 implemented and validated the first semantic classifier pass locally in WSL2 and in Docker.

## Sprint goal

Turn Sprint 3 raw candidates and exact suffix patterns into semantic exploit primitive facts.

Sprint 4 should not expand scanning breadth first. The highest-value next step is to consume the existing `PATTERN_*` IDs and populate semantic records. This keeps the project aligned with the architecture boundary: scanner discovers byte windows, pattern matcher tags exact suffixes, classifier maps patterns to primitive meaning.

## Planned deliverables

- [x] Implement first real `classifier.asm` routine.
- [x] Call classifier from `gadgets.asm` after `patterns.asm` and before reporting.
- [x] Map exact pattern IDs into semantic classes:
  - `ret` -> `alignment`
  - `ret imm16` -> `alignment` with `8 + imm16` stack adjustment
  - `pop rdi; ret`, `pop rsi; ret`, `pop rdx; ret`, `pop rcx; ret`, `pop r8; ret`, `pop r9; ret` -> `arg_control`
  - `pop rax; ret` -> `syscall_num_control`
  - `syscall; ret` -> `syscall_trigger`
  - `leave; ret` and `pop rsp; ret` -> `stack_pivot`
- [x] Populate `GADGET_REGS_CONTROLLED` bitmap for exact pop patterns.
- [x] Populate first stack-delta values for exact patterns.
- [x] Populate first side-effect flags if a minimal flag model is added.
- [x] Add primitive coverage summary record or extend an existing summary with explicit coverage fields.
- [x] Add text output for semantic class and controlled registers.
- [x] Add regression tests for semantic labels and register bitmap behavior.
- [x] Update `docs/semantic-taxonomy.md` and `docs/scoring-model.md` based on actual classifier behavior.
- [x] Leave `docs/json-schema.md` implementation status unchanged because JSON output is not implemented in Patch 015.

## Patch 015 implemented subset

Patch 015 implements the classifier subset without scoring or JSON. Validation expectations are tracked in `docs/sprints/sprint-04-patch-015-validation.md`.

Patch 015 implements:

- exact pattern to semantic class mapping,
- controlled-register bitmap population,
- stack delta for `ret`, `ret imm16`, and pop-ret patterns,
- minimal side-effect flags,
- semantic summary counts,
- register coverage summary,
- fixture validation and smoke target updates.

## Acceptance criteria

- [x] `make clean && make && make test` succeeds.
- [x] `make docker-test` succeeds.
- [x] `make validate-gadget-fixture` succeeds.
- [x] `x64lens gadgets --max-depth 4 ./tests/bin/gadgets` reports semantic classes for the known fixture patterns.
- [x] Primitive coverage includes at least argument-register control, syscall-number control, syscall trigger, stack pivot, and alignment.
- [x] No exploitability verdicts are emitted.
- [x] Unknown byte windows remain `unknown_candidate` rather than being forced into incorrect classes.
- [x] Sprint 4 retrospective is written.

## Suggested validation commands

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
make validate-gadget-fixture
make semantic-smoke
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

## Patch 14 reviewer-readiness additions

Sprint 4 must explicitly protect metric quality:

- preserve `unknown_candidate`,
- count raw candidates separately from semantic primitives,
- classify only exact patterns with clear evidence,
- avoid any score output unless scoring lands in Sprint 5,
- avoid any exploitability wording,
- document suffix-label limitations in the retrospective.

A successful Sprint 4 should make the tool more honest, not just more verbose.


## Closeout decision

Sprint 4 is complete after Patch 015 validation. The controlled fixture, Docker path, semantic smoke target, and `/bin/ls` real-binary spot check all succeeded. No additional required validation remains before committing Patch 015 and the Sprint 4 closeout documentation.

Optional follow-up coverage should move into Sprint 5 or Sprint 8 rather than extending Sprint 4:

- add a richer semantic fixture that covers `pop rcx; ret`, `pop r8; ret`, `pop r9; ret`, and `pop rsp; ret`,
- make unknown stack-delta rendering less ambiguous in JSON/text output,
- keep full decoding, full RELRO, canary detection, and section labels deferred to their planned future sprints.
