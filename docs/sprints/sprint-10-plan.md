# Sprint 10 Plan

## Status

Next implementation tranche after Sprint 9 closeout.

## Sprint goal

Expand semantic primitive coverage without collapsing suffix evidence, decoded
validity, side effects, score meaning, or the defensive deployment profile.

## Planned deliverables

- [ ] Add selected multi-pop patterns with ordered controlled-register facts.
- [ ] Add conservative register-transfer patterns where source and destination
  are unambiguous.
- [ ] Add narrowly scoped memory-read and memory-write patterns only when
  operand semantics are justified.
- [ ] Populate controlled and clobbered register bitmaps.
- [ ] Add memory side-effect and dereference facts.
- [ ] Add known/unknown stack-delta representation for expanded patterns.
- [ ] Add controlled source fixtures and expected disassembly for every new
  pattern family.
- [ ] Add a fixture coverage table and per-family false-positive notes.
- [ ] Add score entries only after semantic and side-effect facts are validated.
- [ ] Preserve candidate-index provenance and schema `0.2.x` compatibility.

## Entry criteria from Sprint 9

- Schema `0.2.0` identity, completeness, and provenance gates pass.
- `gadgets` and `analyze` remain command-only parity matches.
- Capacity and malformed-input paths remain fail-closed with no partial output.
- The decoder-free one-worker core remains the reference profile.
- External disassembly is comparator evidence, not runtime authority.

## Acceptance criteria

- [ ] Every semantic mapping has a controlled fixture.
- [ ] Ambiguous patterns remain `unknown_candidate`.
- [ ] Exact suffix recognition and semantic promotion remain separate.
- [ ] Controlled, clobbered, stack, and memory effects are visible in records,
  text, and JSON when implemented.
- [ ] Score changes are documented and tested independently from classification.
- [ ] New metrics preserve provenance and schema `0.2.x` compatibility.
- [ ] No new mandatory runtime dependency is introduced.
- [ ] One-worker output remains deterministic and bounded.

## Decoder and parallelism boundary

Sprint 10 may mark which retained windows are eligible for future candidate-
scoped validation, but it does not make a decoder mandatory. It may add no
parallel default. New families must first be correct and deterministic in the
core profile.

## Out of scope

- JOP, COP, or SROP coverage.
- Symbolic execution.
- Exploit-chain generation.
- Unbounded pattern enumeration.
- Whole-image decoder integration.
- Default in-process multithreading.

## Handoff

Sprint 11 builds a reproducible compiler and hardening corpus that exercises the
expanded semantic and mitigation model. Sprints 12 and 13 measure optional
candidate-validation and worker profiles.
