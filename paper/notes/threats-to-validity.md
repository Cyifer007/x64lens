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
