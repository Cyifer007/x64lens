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

## Sprint 7 hostile-input evidence limits

- The deterministic mutation catalog covers reviewed field and range cases, not all possible ELF64 structures or execution paths.
- A passing 29-case campaign is regression evidence, not a proof of memory safety or complete parser coverage.
- Compiler-generated seed bytes can vary across environments; the recorded seed SHA-256 must accompany interpretation.
- Timeout success on small controlled inputs does not establish worst-case complexity for every future metadata table.
- The 4096/4097 capacity fixtures prove exact-boundary completeness and fail-closed overflow behavior, not scalability beyond that boundary.

## Sprint 7 mitigation-oracle limits

The controlled matrix reduces dependence on compiler-generated mitigation defaults, but it covers only selected program-header and dynamic-table combinations. `ET_DYN` remains a static PIE indicator, RELRO is split into no, partial, and full states only for represented `PT_GNU_RELRO` and bind-now evidence, and passing the matrix does not prove memory safety or complete mitigation detection. Overlapping executable segments are characterized under the current region model rather than deduplicated.

## Patch 032 canary indicator threat

The canary field is based on exact dynamic string-table evidence for `__stack_chk_fail`. This may miss statically linked or stripped cases where equivalent protection evidence exists elsewhere, and it may indicate linkage without proving every relevant function was protected. Treat it as a triage indicator only.

Patch 033 stripped indicator threat

The stripped field is based on bounded section-header evidence for `SHT_SYMTAB`. It can describe represented section-table metadata, but it does not prove complete symbol recovery, source availability, or runtime loader behavior. Section headers remain outside executable-region authority.

## Patch 034 section-label threat

Section labels are derived from optional section-header metadata. They can improve readability, but they are not loader authority and may be absent, stale, stripped, or intentionally misleading in adversarial binaries. Claims based on Patch 034 should describe labels as annotations over loader-derived regions and scanner-derived candidates.

## Sprint 8 Patch 036 evidence-hardening note

Historical-review probes found that development smoke evidence can be misleading if invalid benchmark inputs, impossible metric values, mixed TSV aggregation, symlink target sizes, or lossy JSON escaping are accepted without validation. Patch 036 hardens those development gates, but publication claims still require the planned fixed corpus, higher-resolution runner, normalized baseline definitions, and schema/provenance transition before results are interpreted as research evidence.


## Comparator tooling threat

Patch 037 adds automated `readelf` checks and optional `checksec`/`rabin2`
comparison capture. These reduce manual-review drift but do not eliminate tool
version variance, different hardening-label semantics, or coverage-definition
differences across binary-analysis tools.
