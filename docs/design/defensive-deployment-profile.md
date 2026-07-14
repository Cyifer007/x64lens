# Defensive Deployment Profile

## Purpose

x64lens is intended to remain useful in constrained defensive environments, not
only in offensive research workstations. This profile records the product
properties that must remain measurable while primitive coverage expands.

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
- suitable for offline, air-gapped, minimal-container, CI/CD, and incident-
  response staging.

The core profile is the product baseline. Optional research tools, external
comparators, and development validators do not become runtime dependencies.

## Defensive operating goals

### Air-gapped analysis

A released core binary should execute without package installation, network
access, Python, a decoder framework, or a supporting service. Source builds may
require the documented toolchain, but target analysis must remain self-contained.

### Incident response and malware triage

The analyzer should be easy to stage on a constrained host and should avoid
unnecessary helper processes, imports, writable target mappings, or persistent
state. This produces a low-observable dependency and process surface. It is not
a guarantee of invisibility, anti-forensic behavior, or evasion of malware
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

A future decoder should consume only retained candidate windows after the fast
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

This profile must preserve raw, exact, semantic-exact, unknown, decoder-valid,
semantic-decoded, and scored populations independently. It must not decode the
whole image merely because a decoder is available.

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
- meaningful wall-time improvement on defined target classes;
- acceptable peak-RSS and startup-cost growth.

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
