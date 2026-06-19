# Sprint 10 Plan

## Status

Planned.

## Sprint goal

Expand semantic primitive coverage without collapsing suffix evidence, decoded validity, side effects, or score meaning.

## Planned deliverables

- [ ] Add selected multi-pop patterns with ordered controlled-register facts.
- [ ] Add conservative register-transfer patterns where source and destination are unambiguous.
- [ ] Add narrowly scoped memory-read and memory-write patterns only when operand semantics are justified.
- [ ] Populate controlled and clobbered register bitmaps.
- [ ] Add memory side-effect and dereference facts.
- [ ] Add known/unknown stack-delta representation for expanded patterns.
- [ ] Add controlled source fixtures and expected disassembly for every new pattern family.
- [ ] Add score entries only after semantic and side-effect facts are validated.
- [ ] Add fixture coverage table and per-family false-positive notes.

## Acceptance criteria

- [ ] Every semantic mapping has a controlled fixture.
- [ ] Ambiguous patterns remain `unknown_candidate`.
- [ ] Exact suffix recognition and semantic promotion remain separate operations.
- [ ] Clobber and memory effects are visible in text and JSON.
- [ ] Score changes are documented and tested independently from classification.
- [ ] New metrics preserve provenance and schema `0.2.x` compatibility.

## Out of scope

- JOP, COP, or SROP coverage.
- Symbolic execution.
- Exploit-chain generation.
- Unbounded pattern enumeration.

## Handoff

Sprint 11 builds a reproducible compiler and hardening corpus that exercises the expanded semantic and mitigation model.
