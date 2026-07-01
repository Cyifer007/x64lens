# Sprint 07 Retrospective

## Summary

Sprint 7 hardened x64lens before expanding the parser attack surface. The sprint began with deterministic hostile-input coverage and ended with shared checked table arithmetic, a deterministic mitigation oracle, explicit capacity behavior, and clearer public/private documentation hygiene.

The sprint did not attempt to add new gadget primitives or a decoder. That restraint was correct. Parser safety, bounded storage, and loader-fact stability are prerequisites for the mitigation-depth and metadata work planned for Sprint 8.

## Delivered outcomes

- Deterministic malformed-input smoke coverage with bounded execution and per-case evidence.
- First committed minimized malformed regression fixture.
- Exact candidate-capacity boundary fixtures for 4096 records and 4097-candidate overflow.
- Deterministic mitigation oracle for controlled ELF64 loader layouts.
- Corrected mitigation oracle expectation for zero executable regions.
- Shared checked arithmetic helpers for table extents, offset-plus-length validation, and per-entry table offsets.
- Program-header and section-header table-end overflow coverage.
- Public-documentation, planning-document, Docker, and patch-bundle hygiene improvements.

## Validation posture

Sprint 7 closes with the following gates expected to pass natively and in Docker where Docker is available:

```bash
make test
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

The accepted baseline includes 31 deterministic malformed-smoke cases, 28 malformed cases, 11 valid mitigation-matrix cases, seven malformed mitigation-matrix cases, and exact candidate-capacity handling at 4096 and 4097 candidates.

## Contract review

No product-facing contract drift was accepted.

- CLI syntax remains unchanged.
- Tool version remains `0.1.0-dev`.
- JSON schema remains `0.1.0`.
- Raw, exact, semantic, unknown, validated, and scored metric boundaries remain separate.
- Program headers remain authoritative for runtime executable mappings.
- Bounded storage still fails closed rather than silently truncating.
- Malformed parse failures must not emit partial stdout.

## What changed in project discipline

Sprint 7 made validation broader and less cleanup-sensitive. Generated malformed and mitigation artifacts remain ignored, public documentation checks avoid ignored result artifacts, and patch-bundle hygiene rejects private or generated state.


## Lessons

- A failing validation aggregate can be good evidence. Patch 026 correctly failed when the mitigation oracle expected stale text.
- Parser arithmetic should be shared and explicitly checked. Repeated local arithmetic in parser modules is too easy to get wrong.
- Smoke benchmarks are useful for regressions and tool plumbing, but they are not publication-grade performance evidence.
- Public documentation must not depend on whether ignored validation results happen to exist locally.

## Sprint 8 handoff

Sprint 8 should start with bounded mitigation metadata rather than primitive expansion. The recommended order is:

1. bounded `PT_DYNAMIC` discovery,
2. full versus partial RELRO evidence,
3. canary indicators with explicit confidence wording,
4. stripped and section-label annotations,
5. malformed coverage for every newly reachable table or string view.

The Sprint 7 gates should remain mandatory for every Sprint 8 parser change.
