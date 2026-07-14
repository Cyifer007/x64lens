# ADR 0031: Sprint 9 Closeout and Defensive Deployment Profile

## Status

Accepted for Sprint 9 Patch 045.

## Context

Sprint 9 introduced report and command identity, explicit complete-analysis
state, schema `0.2.0`, per-candidate provenance, external decoder-gap evidence,
immutable campaign inputs, transaction-safe publication, external-parser
hardening, and portable archive validation.

The remaining closeout work is to correct the strict shell-lint defect, remove
documentation drift, reconcile release and roadmap language, and state the
product properties that future primitive, decoder, and acceleration work must
preserve.

## Decision

1. Sprint 9 closes with Patch 045 after the native closeout gate and qualified
   Docker validation pass.
2. The default runtime remains freestanding, statically linked, decoder-free,
   and single-worker.
3. A future decoder is candidate-scoped and optional. It augments the evidence
   side-car and never replaces raw discovery or exact/semantic-exact facts.
4. Parallel execution is an experimental profile until deterministic output,
   global capacity, cleanup, wall-time, peak-RSS, startup, and binary-size gates
   pass on a fixed corpus.
5. Sprint 10 expands primitive coverage in deterministic one-worker operation.
   Decoder and parallel ablations are measured in Sprints 12 and 13.
6. Public documentation describes repository facts and reproducible behavior.
   Local operational state and transfer history remain outside public artifacts.
7. Docker Buildx activity-path failures that disappear with a writable Buildx
   configuration are environment defects, not analyzer failures. The repository
   documents a generic qualified invocation but does not hide the distinction.
8. Archive-policy regression tests treat allow/reject outcome as the stable
   contract. Exact diagnostic text is stable only when a test explicitly names
   it as an output contract.

## Consequences

- Air-gapped, minimal-container, incident-response, and CI/CD use retain a
  self-contained default analyzer.
- Decoder-backed validity can improve confidence without forcing whole-image
  decoding or mandatory dependencies.
- Parallelism cannot silently trade low RSS or deterministic output for speed.
- Sprint 10 receives a clean evidence-aware primitive-expansion boundary.
- Publication claims remain deferred until the fixed corpus and benchmark
  methodology support them.
