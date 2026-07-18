# Defensive Deployment Profile

## Purpose

x64lens uses a freestanding, bounded analyzer core for constrained defensive
environments. This profile separates implemented core properties, development
evidence, current limitations, and the gates for future decoder and parallel
profiles.

## Core profile

The default analyzer profile remains:

- a freestanding ELF64 x86_64 executable implemented in NASM;
- statically linked, with no mandatory interpreter or shared-library dependency;
- direct-syscall based for mapping, output, cleanup, and process exit;
- read-only with respect to the analyzed target;
- bounded by explicit record, region, table, and candidate capacities;
- deterministic for identical input bytes and options;
- single-worker until a parallel profile passes the acceleration gate;
- decoder-free until an optional validation profile passes the decoder gate;
- designed to support offline, air-gapped, minimal-container, CI/CD, and incident-
  response staging.

The dependency-free, decoder-free, one-worker core profile is the product and
measurement reference baseline. Optional research tools, external comparators,
and development validators do not become runtime dependencies.

## Evidence status

The core-profile properties above describe the current implementation. `make
schema-compat-smoke`, `make validation-smoke`, and `make sprint-closeout-smoke`
exercise the current report, provenance, and closeout contracts. Decoder-gap
timing and RSS are development smoke evidence, not publication-grade performance
or operational-effectiveness results.

The candidate-validation and parallel sections below describe future optional
profiles, not current runtime modes. The current runtime report identifies its
command, schema, and bounded completion state but does not embed a target digest;
campaign and benchmark manifests retain target hashes separately.

## Defensive operating goals

### Air-gapped analysis

A released core binary should execute without package installation, network
access, Python, a decoder framework, or a supporting service. Source builds may
require the documented toolchain, but target analysis must remain self-contained.

### Incident response and malware triage

The analyzer should be easy to stage on a constrained host and should avoid
unnecessary helper processes, imports, writable target mappings, or persistent
state. This limits its dependency and helper-process surface; it does not make
analyzer execution invisible or provide anti-forensic behavior or evasion of
anti-analysis controls.

### CI/CD integration

The core path should preserve stable exit codes, deterministic schema-versioned
JSON, bounded memory behavior, no partial output on malformed or capacity
failure, and reproducible artifact identity. Optional profiles must never make
the core path nondeterministic.

### Resource efficiency

Runtime, CPU, peak RSS, startup cost, output size, and binary size are separate
metrics. A feature is not accepted merely because it improves one metric while
silently increasing another.

## Optional candidate-validation profile

A future decoder should consume only retained candidate windows after the bounded
byte scan, exact suffix matcher, and semantic-exact classifier have completed:

```text
loader-authoritative executable regions
  -> byte-oriented terminator scan
  -> bounded candidate windows
  -> exact suffix recognition
  -> semantic-exact classification
  -> optional candidate-scoped validation
  -> decoder evidence side-car
  -> optional semantic-decoded classification
```

This profile must preserve raw-candidate, exact-suffix, semantic-exact,
unknown-candidate, decoder-validated, semantic-decoded, and scored populations
independently. It must not decode the whole image merely because a decoder is
available.

Approval requires a fixed-corpus ablation showing that the validity or coverage
benefit justifies dependency, license, binary-size, latency, peak-RSS, and
hostile-input costs. The decoder-free core remains independently buildable and
measurable.

## Optional parallel profile

The first preferred concurrency seam is candidate validation after the raw
candidate array is stable. Target-level parallelism outside the analyzer is the
lowest-risk throughput option for corpus and CI workflows.

Any in-process worker profile must prove:

- byte-identical output to one-worker execution;
- stable ordering and candidate indices;
- one global capacity decision;
- bounded worker count, stack use, and private state;
- complete cleanup after failure or interruption;
- no malformed-input deadlock or partial report;
- meaningful wall-time improvement on defined target classes, with aggregate
  child-CPU reported separately;
- acceptable peak-RSS, startup-cost, and binary-size growth.

Region or chunk parallelism requires explicit overlap, deduplication, and stable
merge rules before implementation.

## Measurement schedule

Sprint 10 expands exact and semantic coverage in the core profile. Sprint 11
freezes a reproducible corpus. Sprint 12 builds the high-resolution runner and
pilot ablations. Sprint 13 performs fixed comparative and profile-level
measurement. No decoder or worker profile becomes the default before those
gates produce reproducible evidence.

## Claim boundary

The project may describe the core as dependency-light, bounded, and designed for
low-footprint defensive deployment. Performance, memory superiority, comparable
coverage, anti-analysis resilience, or operational usefulness remain hypotheses
until the relevant corpus, baselines, commands, and repeated measurements exist.

## Sprint 10 Patch 046 resource preservation

The first primitive expansion reuses eight reserved bytes already present in
each 112-byte candidate record. It does not increase the candidate record
stride, side-car size, 4,096-record capacity, or 655,360-byte combined analysis
arena. No decoder, worker library, helper process, or user-space runtime
library is added.

This is an architectural preservation result, not a measured performance claim.
Sprint 12 and Sprint 13 remain responsible for wall-time, CPU, RSS, binary-size,
and optional-profile ablations.

## Patch 049 fixed memory-effect allocation

Patch 049 adds 65,536 bytes to the fixed command arena for a dense memory-effect side-car while preserving 4,096 candidate slots and adding no mandatory runtime dependency or helper process. This is a bounded implementation property. Operational RSS and latency effects remain measurement questions for the fixed corpus and benchmark stages.

## Patch 051 fixed architectural-effect allocation

Patch 051 adds a 24-byte architectural-effect record for each of 4,096
candidate slots, increasing the fixed command arena to 819,200 bytes. It adds no
decoder, shared-library import, helper process, worker thread, or user-space
runtime dependency. These are fixed-allocation, dependency, import, and helper-
process surface facts; they are not measured RSS or speed results and do not
imply invisibility or guaranteed anti-analysis evasion.
