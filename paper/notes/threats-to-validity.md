# Threats to Validity

- Gadget definitions differ between tools.
- Some Python tools use native libraries, so language-level comparisons can be misleading.
- Full disassembly tools may intentionally perform more work than x64lens.
- Small binaries may be dominated by process startup and output formatting.
- Disk cache state affects runtime measurements.
- Corpus selection may bias results.
- Pattern-based scanning may undercount complex gadgets.
- Handwritten assembly may contain implementation errors that distort performance or correctness.
- Enterprise integration claims require real workflow testing beyond toy benchmarks.

## Sprint 6 checkpoint additions

- `analyze` composes existing analysis facts and does not add independent detection capability.
- Exact suffix patterns can label unaligned byte streams and are not full decoding.
- Very short smoke runs can round to zero at the current timer resolution.
- Historical benchmark artifacts from different hosts must not be pooled without stratification.
- The body-only text report seam assumes the current single-threaded process model.


## Post-checkpoint evidence controls

- Candidate capacity and analysis completeness must be explicit before large-target count claims.
- Raw byte candidates, exact suffix observations, semantic classifications, and decoder-validated candidates must not be compared as though they are identical populations.
- Schema and corpus versions must be frozen before the publication benchmark campaign.
- Tool order, timer resolution, per-child resource capture, and host state can materially affect performance results.
- Mitigation indicators derived from incomplete metadata must expose uncertainty rather than a guessed negative.
- Operational triage conclusions require a documented analyst workflow and cannot be inferred from toy fixtures alone.
