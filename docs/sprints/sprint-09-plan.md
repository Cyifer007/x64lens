# Sprint 09 Plan

## Status

Candidate extended-semester sprint.

## Sprint goal

Build a compiler and hardening matrix corpus for research evaluation.

## Planned deliverables

- [ ] Generate fixture binaries across compiler flags.
- [ ] Include PIE and non-PIE variants.
- [ ] Include stack-protector variants.
- [ ] Include RELRO variants.
- [ ] Include static and dynamic linking where practical.
- [ ] Document all build commands in the corpus manifest.
- [ ] Add benchmark metadata fields for compiler and hardening profile.

## Acceptance criteria

- [ ] Corpus can be regenerated from source.
- [ ] Manifest captures build commands and expected hardening signals.
- [ ] Benchmark scripts can run across the matrix without manual path edits.
