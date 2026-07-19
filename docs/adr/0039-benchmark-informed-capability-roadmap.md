# ADR 0039: Benchmark-Informed Capability Sequencing and Roadmap Expansion

## Status

Accepted for Sprint 10 Patch 053.

## Context

The original eighteen-sprint roadmap moved directly from Sprint 10 primitive
expansion into corpus construction, high-resolution measurement, and a fixed
comparative campaign. The Patch 049 capability audit showed that this sequence
would freeze several material uncertainties too early:

- executable-region overlap semantics are not yet frozen;
- PIE executables and shared objects still share one coarse `ET_DYN` label;
- CET IBT and SHSTK property evidence is not implemented;
- selected ELF program-header validity relationships remain unreported;
- generic single-pop and Linux syscall-register roles need an explicit release
  decision;
- optional decoder and concurrency profiles have not been measured;
- task-equivalent coverage definitions across baseline tools are not frozen.

Waiting until every capability is complete before measuring would create a
different risk: development would proceed without evidence about where x64lens
is already competitive, where output scope differs, and which implementation
costs dominate. Running the final campaign now would also be unsound because
capability and measurement definitions would still change afterward.

## Decision

Use two distinct measurement phases.

### Diagnostic measurement

Begin in Sprint 11 with a provisional, reproducible corpus and a
high-resolution runner. Diagnostic results may:

- identify runtime, CPU, RSS, output-size, and coverage bottlenecks;
- compare task definitions and expose unsupported families;
- guide implementation priorities;
- reject weak performance assumptions early;
- trigger a documented capability or methodology change.

Diagnostic results are development evidence. They are not merged into the
publication campaign and do not support final superiority claims.

### Confirmatory measurement

Freeze corpus membership, tool versions, commands, schema, task definitions,
runner version, cache policy, and environment strata in Sprint 15. Run the
preview campaign in Sprint 16 and the publication-grade comparative campaign in
Sprint 17. Any affected change after freeze creates a new campaign identifier
or requires a complete rerun.

### Roadmap expansion

Replace the canonical eighteen-sprint roadmap with a twenty-two-sprint
roadmap:

- Sprint 11: diagnostic benchmark foundation and provisional corpus;
- Sprint 12: loader and mitigation precision;
- Sprint 13: semantic capability completion;
- Sprint 14: optional decoder and deterministic concurrency ablations;
- Sprint 15: corpus, schema, method, and baseline freeze;
- Sprint 16: high-resolution pilot and `v0.1.0-rc1`;
- Sprint 17: publication comparative campaign;
- Sprint 18: mitigation-aware defensive triage;
- Sprint 19: automation and schema stabilization;
- Sprint 20: infrastructure case study;
- Sprint 21: replication and paper freeze;
- Sprint 22: `v0.1.0` release.

The dependency-free, decoder-free, one-worker analyzer remains the reference
profile. Optional profiles must preserve reference facts and receive separate
binary, dependency, worker-count, timing, CPU, RSS, and output-identity rows.

## Consequences

### Positive

- Measurement begins early enough to redirect development.
- The final experiment is not contaminated by later capability changes.
- Capability expansion is tied to explicit evidence gaps rather than feature
  counting.
- The project retains enough time for loader precision, mitigation evidence,
  semantic completion, and conditional profile experiments.
- Air-gapped, incident-response, minimal-container, and CI/CD deployment
  properties remain first-class measured variables.

### Costs

- The first research release moves from Sprint 18 to Sprint 22.
- More planning and validation artifacts must remain synchronized.
- Diagnostic and confirmatory datasets require strict separation.
- A capability added after Sprint 15 may require campaign restart rather than
  an incremental result update.

## Rejected alternatives

### Freeze the final benchmark suite immediately

Rejected because current capability and task definitions are still changing.
The results would measure a transient design and would need to be rerun after
material corrections.

### Delay all measurement until feature completion

Rejected because the project would optimize and expand without evidence about
cost, coverage, or baseline task differences.

### Expand toward complete industry-tool parity before measurement

Rejected because general decoding, JOP/COP/SROP, chain generation, symbolic
execution, other architectures, and other file formats would dissolve the
bounded research contribution and compromise the dependency-light reference
profile.

## Validation

```bash
make research-stage-gates-smoke
make planning-docs-check
make public-docs-check
make validation-smoke
```

See:

- [`../design/benchmark-and-capability-stage-gates.md`](../design/benchmark-and-capability-stage-gates.md)
- [`../roadmap-22-sprints.md`](../roadmap-22-sprints.md)
- [`../sprints/sprint-10-patch-053-validation.md`](../sprints/sprint-10-patch-053-validation.md)
