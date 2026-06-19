# Sprint 12 Plan

## Status

Planned research preview gate.

## Sprint goal

Replace smoke-level timing with higher-resolution measurement, run a pilot comparison campaign, and prepare the `v0.1.0-rc1` research preview candidate.

## Planned deliverables

- [ ] Add a benchmark runner using monotonic nanosecond timing and per-child resource usage.
- [ ] Avoid zero-valued measurements through batching or larger targets when single-run duration is below the timer floor.
- [ ] Capture wall time, user CPU, system CPU, max RSS, output bytes, exit status, and target/tool hashes.
- [ ] Record warmup policy, randomized tool order, cache condition, and host metadata.
- [ ] Separate raw scanner, gadget JSON, and end-to-end `analyze` benchmark modes.
- [ ] Generate summaries from raw rows only.
- [ ] Run a pilot campaign across the frozen preview corpus and all available baselines.
- [ ] Rehearse source, binary, checksum, reproduction, and benchmark-smoke artifacts.
- [ ] Tag `v0.1.0-rc1` only if every preview gate passes.

## Acceptance criteria

- [ ] Small-target measurements are above the documented resolution floor or are reported as batched measurements.
- [ ] Per-run resource data is preserved.
- [ ] Tool order and environment metadata are recorded.
- [ ] Historical rows from different hosts are not merged silently.
- [ ] Parser safety, mitigation, provenance, schema, corpus, and release-preview gates pass.
- [ ] Preview documentation states remaining semantic and decoder limitations.

## Handoff

Sprint 13 runs the publication-grade comparative campaign using the frozen methodology, schema, corpus, and baseline versions.
