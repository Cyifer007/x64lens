# Sprint 08 Plan

## Status

Candidate extended-semester sprint.

## Sprint goal

Expand primitive coverage beyond the initial exact patterns while preserving conservative classification.

## Planned deliverables

- [ ] Add multi-pop exact patterns.
- [ ] Add basic register-transfer exact patterns where safe.
- [ ] Add limited memory-read and memory-write templates only when operand semantics are clear.
- [ ] Add side-effect flags for multi-register clobbering.
- [ ] Expand controlled fixture corpus.
- [ ] Add fixture coverage table for every recognized pattern.

## Acceptance criteria

- [ ] Classifier remains conservative.
- [ ] Unknown or ambiguous windows remain `unknown_candidate`.
- [ ] Primitive coverage reports distinguish exact, inferred, and unknown candidates.
- [ ] New patterns are validated against controlled fixtures and disassembly.
