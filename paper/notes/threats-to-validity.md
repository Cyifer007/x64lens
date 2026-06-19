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
