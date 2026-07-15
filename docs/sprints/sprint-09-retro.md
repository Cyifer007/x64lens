# Sprint 09 Retrospective

## Status

Closed by Patch 045 after closeout validation.

## Sprint goal recap

Sprint 9 made report identity, bounded analysis completion, candidate evidence,
and decoder uncertainty explicit before primitive expansion.

## Delivered outcomes

- Patch 040 introduced schema `0.2.0`, report and command identity, a fixed-size
  analysis summary, successful-analysis completeness, representative final-shape
  `0.1.0` compatibility, and `gadgets`/`analyze` parity.
- Patch 041 added the dense candidate-index evidence side-car, current per-
  candidate raw-candidate/exact-suffix/semantic-exact provenance, formal schema
  enforcement, and ABI and validation hardening.
- Patch 042 added root-independent public ZIP policy and controlled plus selected-
  system decoder-gap evidence without adding a runtime decoder.
- Patch 043 bound comparison evidence to immutable snapshots, hardened
  transactional publication and external disassembly parsing, and recorded the
  decoder-free default.
- Patch 044 corrected signal-window rollback, measured-child cleanup, reviewed
  prefix/return parsing, local/central ZIP reconciliation, ZIP64 semantics, and
  public negative-fixture provenance.
- Patch 045 corrected strict shell lint, removed closeout documentation drift,
  added a durable closeout gate, recorded the defensive deployment profile, and
  advanced Sprint 10.

## Architecture review

The sprint preserved the module boundary:

```text
mapping and bounds
  -> ELF and loader facts
  -> executable regions
  -> raw scanning
  -> exact recognition
  -> semantic classification
  -> evidence materialization
  -> scoring
  -> report summary
  -> text and JSON adapters
```

Program headers remain runtime authority. Section and dynamic metadata remain
bounded evidence. The raw candidate record was not overloaded with variable-
length decoder facts. Candidate provenance lives in a side-car keyed by stable
candidate index.

## Metric and schema review

Schema `0.2.0` is the current producer contract. It adds identity, bounded
completion, and candidate evidence without redefining historical raw, exact,
semantic, unknown, or scored counts.

`complete: true` means every loader-authoritative executable region was scanned
within the configured capacity. It does not mean every candidate was decoded or
proven useful. Capacity exhaustion still fails before report emission.

The retained schema `0.1.0` fixture represents the final historical shape. It is
not a guarantee for every intermediate pre-release emission that used the same
version string.

## Decoder decision

The reviewed development campaign found expected unaligned byte observations and
canonical sequences outside the current exact catalog. It did not justify a
mandatory whole-image decoder.

The preferred future path is candidate-scoped validation after the bounded
terminator scan and exact/semantic-exact stages. Decoder evidence must be
additive, independently measurable, and optional in the default deployment
profile.

## Parallelism decision

The analyzer remains single-worker. Target-level parallelism is already
available to external corpus orchestration. Candidate-validation parallelism is
the preferred first in-process seam because candidate order and loader facts are
stable before workers begin.

No worker profile becomes default until fixed-corpus evidence proves
deterministic output, bounded global capacity, complete cleanup, meaningful
wall-time benefit, and acceptable aggregate CPU, peak-RSS, startup-cost, and
binary-size growth.

## Defensive deployment review

The default core preserves the properties intended for air-gapped analysis,
minimal containers, incident-response staging, malware triage, and CI/CD: it is
statically linked, has no mandatory user-space runtime libraries or helper
processes, produces deterministic output, uses explicit capacities, and maps
targets read-only. Operational usefulness remains a later case-study question.

The project may describe this limited dependency and helper-process surface. It
must not claim invisibility, stealth, anti-analysis evasion, or guaranteed
resistance to anti-analysis controls.

See the [Defensive Deployment Profile](../design/defensive-deployment-profile.md).

## Validation lessons

- Validation and release tooling are part of the product evidence surface.
- Exact diagnostics should be separated from stable allow/reject outcomes unless
  wording is itself a contract.
- A normal aggregate may keep optional review tools advisory, but sprint closeout
  requires an explicit strict gate.
- Archive inspection must reconcile metadata before extraction.
- Development comparison evidence must remain distinct from analyzer facts and
  publication benchmarks.

## Release readiness

Sprint 9 satisfies the provenance and schema milestone required before the
research preview. The preview is not ready: Sprint 10 primitive coverage,
Sprint 11 corpus reproducibility, and Sprint 12 high-resolution benchmark and
artifact rehearsal remain open.

## Sprint 10 handoff

Sprint 10 expands primitive families under these entry conditions:

1. every new exact pattern has a controlled fixture;
2. semantic promotion remains separate from recognition;
3. controlled, clobbered, stack, and memory effects are explicit;
4. ambiguous candidates remain unknown;
5. score changes follow validated semantic facts;
6. schema `0.2.x` compatibility and provenance remain intact;
7. no mandatory decoder or parallel runtime is introduced as a shortcut.
