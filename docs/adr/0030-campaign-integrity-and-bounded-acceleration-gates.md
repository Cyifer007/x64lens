# ADR 0030: Campaign Integrity and Bounded Acceleration Gates

## Status

Accepted for Sprint 9 Patch 044.

## Context

Sprint 9 established report identity, complete-analysis state, candidate
provenance, and an external decoder-gap campaign. Patch 043 validation found no
analyzer defect, but it did find acceptance-blocking defects in the research
harness and release boundary: a signal window could hide the only recognized
campaign tree, interrupted measurements could leave child process groups alive,
prefixed objdump mnemonics could corrupt sequence evidence, ZIP local headers
could contradict clean central metadata, malformed ZIP64 fields could be
accepted, and a synthetic public-boundary fixture violated identifier policy.

The same review also showed an important product direction. The byte scanner
found every reviewed canonical return terminator, while many raw candidates
were intentionally unaligned and some canonical return-ending sequences were
outside the exact-pattern catalog. That evidence supports a bounded hybrid
rather than replacing the core with whole-binary decoding.

## Decision

1. Patch 044 is a corrective hardening patch. Sprint 9 closeout moves to Patch
   045 so these safety fixes retain a focused acceptance gate.
2. Campaign publication recovers from observable filesystem state and blocks
   handled signals while rollback or process-group reaping is in progress.
3. Every measured child runs in a separate process session and is killed and
   reaped on timeout or any propagated interruption.
4. Objdump remains an external research oracle. Prefix normalization and
   predecessor barriers are validated by adversarial fixtures; they never feed
   runtime facts.
5. Public ZIP policy reconciles bounded local-header and central-directory
   metadata before extraction and applies strict semantics to recognized extra
   fields, including ZIP64.
6. The default analyzer remains single-threaded, freestanding, and
   dependency-free.
7. A future decoder, if approved, is candidate-scoped: the byte-oriented scanner first
   finds bounded terminator windows, then an optional adapter validates only
   possible starts inside retained windows. Decoder facts remain side-cars.
8. Parallel execution is evidence-gated and optional. A future profile may
   parallelize independent candidate validation or executable-region/chunk
   work only with deterministic merge order, bounded aggregate storage, and
   explicit RSS/latency measurements. The default remains one worker.

## Why not decode the entire executable image

Whole-image decoding would duplicate loader and scanning work, increase the
binary/dependency surface, and make the reference profile incur costs for
assurance that many defensive invocations may not request. Candidate-scoped
validation keeps raw discovery independently measurable while allowing full-
sequence validity, operand, clobber, and memory-effect facts to be added where
they are most valuable.

## Why not force multithreading now

Current smoke targets often have one executable load region and complete very
quickly. Thread/process creation, per-worker arenas, merge state, and boundary
overlap can cost more than they save while increasing RSS and nondeterminism.
The project does not yet have the frozen corpus and high-resolution benchmark
infrastructure needed to choose a threshold honestly. Sprint 12 and Sprint 13
will measure single-worker, candidate-validation-parallel, and region/chunk
profiles before any product default changes.

## Consequences

- Patch 044 changes research/release tooling and documentation, not analyzer
  assembly, public records, or schema.
- Air-gapped and incident-response deployments retain a single static analyzer
  with no decoder or threading runtime dependency.
- CI/CD keeps deterministic order, bounded storage, stable exits, and
  no-partial-output behavior.
- Optional future assurance and acceleration remain possible without rewriting
  the scanner or collapsing evidence tiers.
- Sprint 9 cannot close until Patch 044 passes authoritative native and Docker
  validation and Patch 045 completes the broader closeout audit.
