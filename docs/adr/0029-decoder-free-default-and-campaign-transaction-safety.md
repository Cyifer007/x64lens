# ADR 0029: Decoder-Free Default and Campaign Transaction Safety

## Status

Accepted for Sprint 9 Patch 043.

## Context

Sprint 9 introduced candidate provenance, complete-analysis state, schema
`0.2.0`, and an external decoder-gap campaign. Review of the first selected-
system campaign found no analyzer-runtime defect, but it did find defects in the
research harness: a mutable-target identity race, interruption-unsafe result
replacement, incomplete ZIP metadata policy, and objdump parsing that hid
prefixed returns or crossed control-flow barriers.

The project must also decide whether full x86_64 decoding becomes a mandatory
runtime dependency. That decision affects the primary operational properties of
x64lens: a freestanding NASM executable, direct syscalls, low startup and memory
cost, deterministic bounded storage, simple air-gapped deployment, and minimal
CI/CD integration friction.

## Decision

The default x64lens runtime remains decoder-free and dependency-free.

A future decoder may be added only as an optional verification profile or
adapter. Decoder-backed facts must extend candidate-index side-car evidence and
must not replace raw, exact-suffix, semantic-exact, unknown, or scored facts.
The core analyzer remains independently buildable and measurable without the
adapter.

Patch 043 also makes decoder-gap evidence transactional and byte-bound:

- each target is copied to a verified read-only campaign snapshot;
- x64lens and objdump analyze that same snapshot;
- manifests identify the analyzed snapshot and its source relationship;
- publication preserves either the prior recognized result or one complete new
  result across ordinary failures, `SIGINT`, and `SIGTERM`;
- objdump parsing normalizes known instruction prefixes, retains diagnostics,
  and treats invalid bytes and control transfers as sequence barriers.

## Evidence

The reviewed six-target development campaign observed no canonical return
terminator that was absent from x64lens raw discovery. It did observe many
x64lens byte candidates that were not canonical instruction boundaries. Those
are expected under the byte-oriented scanner and remain validity-unknown rather
than being silently discarded.

The same campaign recorded a peak RSS of 264 KiB for x64lens and approximately
4.4 to 4.6 MiB for GNU objdump on the selected targets. These are development
measurements from one environment, not publication-grade performance results.
They are sufficient to show that making a general decoder mandatory would risk
removing an operational property that the research is explicitly designed to
evaluate.

Patch 043's corrected campaign must be rerun before final Sprint 9 acceptance.
The decision does not depend on exact count equality. It depends on the absence
of a demonstrated release-blocking coverage gap that outweighs dependency,
license, binary-size, RSS, latency, and hostile-input costs.

## Consequences

Positive consequences:

- the core remains suitable for minimal, offline, incident-response, and CI/CD
  environments;
- raw scanner cost remains independently measurable;
- decoder disagreement remains visible as evidence instead of rewriting
  history;
- a future verifier can improve assurance without imposing its costs on every
  invocation.

Tradeoffs:

- current full-sequence validity remains unknown unless external validation is
  performed;
- byte-oriented candidates include unaligned observations;
- broader canonical gadget coverage remains a measured future capability, not
  a current claim;
- optional verification will require a separate build/runtime identity and
  benchmark stratum.

## Rejected alternatives

### Mandatory linked decoder in the default binary

Rejected because the reviewed evidence does not show a canonical-return
coverage failure that justifies changing the default dependency and resource
contract.

### Remove raw candidates that disagree with objdump

Rejected because objdump is an external comparison source, not loader or
scanner authority, and because removing observations would collapse raw and
validated metrics.

### Implement a broad custom decoder immediately

Rejected because it would create substantial maintenance and hostile-input
surface before a quantified claim or user task requires it.

## Revisit gate

Reconsider an optional linked or internal decoder only after a fixed-corpus
campaign demonstrates a material user-facing validity or semantic-coverage gap,
and only when licensing, malformed-input handling, binary-size, runtime, and RSS
ablation evidence are available.

## Patch 044 correction note

Authoritative Patch 043 validation confirmed the decoder-free default and
immutable target binding, but found that the first transaction/parser
implementation did not satisfy every claimed interruption and normalization
case. Patch 044 supersedes those mechanics with observable-state rollback,
measured-child process-group cleanup, the complete reviewed prefix/return
fixture, and bounded local/central ZIP reconciliation. ADR 0030 governs those
corrections and the candidate-scoped decoder/parallelism refinement.
