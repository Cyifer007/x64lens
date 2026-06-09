# Sprint 07 Plan

## Status

Candidate extended-semester sprint.

## Sprint goal

Harden ELF metadata depth and mitigation accuracy after the initial analyzer pipeline exists.

## Planned deliverables

- [ ] Parse dynamic-section entries needed for full RELRO detection.
- [ ] Detect `BIND_NOW` or `DF_BIND_NOW` when present.
- [ ] Add canary indicator detection through dynamic symbol or symbol-table evidence.
- [ ] Add section-header labels for executable regions and candidate addresses.
- [ ] Automate selected `readelf` comparison checks.
- [ ] Add optional `checksec` comparison when available.
- [ ] Add optional `rabin2 -I` comparison when available.

## Acceptance criteria

- [ ] Existing `info`, `mitigations`, `gadgets`, and `analyze` behavior remains stable.
- [ ] Full RELRO and partial RELRO are distinguished when evidence is available.
- [ ] Canary output is clearly documented as an indicator, not a proof.
- [ ] Section labels improve reporting without replacing program headers as runtime authority.

## Patch 14 reviewer-readiness additions

Sprint 7 should become the first hardening sprint after the initial analyzer pipeline exists.

Add these tasks to the planned deliverables:

- [ ] Add deterministic malformed-input mutation smoke runner.
- [ ] Add regression fixtures for any parser crash discovered during mutation testing.
- [ ] Add script permission validation to scaffold checks.
- [ ] Preserve no SIGSEGV and no SIGBUS as explicit acceptance criteria.
- [ ] Keep dynamic-section and symbol-table parsing behind strict range checks.

Additional acceptance criteria:

- [ ] malformed-input smoke runner returns no crashes across the committed malformed corpus.
- [ ] every parser failure has a stable nonzero exit code.
- [ ] mutation outputs are ignored unless intentionally promoted as benchmark artifacts.
