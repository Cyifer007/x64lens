# Backlog

## Completed checkpoints

### Sprints 1 through 3

- [x] Read-only file mapping, ELF64 x86_64 validation, and `info` reporting.
- [x] Program-header analysis, executable `PT_LOAD + PF_X` regions, and baseline mitigation reporting.
- [x] Raw `ret` and `ret imm16` candidate discovery with bounded `--max-depth` windows.
- [x] Arena-backed candidate storage.
- [x] Exact suffix pattern recognition.
- [x] Controlled fixture and scanner smoke validation.

### Sprints 4 through 6

- [x] Conservative semantic classification with unknown preservation.
- [x] Controlled-register coverage and stack-delta facts.
- [x] Heuristic scoring in a separate module.
- [x] Schema-versioned JSON generated from internal records.
- [x] System-binary and Docker validation.
- [x] Baseline comparison smoke harness for ROPgadget, Ropper, and ropr.
- [x] Development dependency diagnostics and onboarding.
- [x] Integrated `analyze` text and JSON command.
- [x] Composable single-banner text report.
- [x] Repeatable checkpoint demo and local `v0.1.0-dev` tag guidance.
- [x] Public-documentation hygiene checks.
- [x] Patch 024 roadmap, release-gate, provenance, schema, and Sprint 7 through 18 planning.
- [x] Patch 025 deterministic hostile-input and candidate-capacity regression gates.
- [x] Sprint 7 hostile-input, mitigation-oracle, checked-arithmetic, and closeout gates.

## Completed Sprint 7 tranche

### Sprint 7: hostile-input hardening

- [x] Deterministic mutation smoke harness.
- [x] Stable signal, timeout, exit-code, elapsed-time, and output-size capture.
- [x] Regression-fixture policy and reserved minimized-corpus path.
- [x] First minimized parser regression fixture for invalid ELF64 section-header stride.
- [x] No additional non-synthetic stable parser defect required a new committed regression fixture during Sprint 7 closeout.
- [x] Shared bounded-table iteration rules or helpers.
- [x] Central checked arithmetic for multiplication, addition, counts, and end offsets.
- [x] Initial program-header, section-header, executable-segment, and boundary range mutations.
- [x] Exact ELF64 section-header entry-size validation.
- [x] Explicit candidate-capacity failure behavior with no partial output.
- [x] `make malformed-smoke`, `make capacity-smoke`, and Docker validation integration.

## Active next tranche

### Sprint 8: mitigation and metadata depth

- [x] Bounded dynamic-section parsing for `PT_DYNAMIC`, bind-now evidence, dynamic-entry count, and `DT_NULL` terminator state. Implemented in Patch 030.
- [x] Full versus partial RELRO. Implemented in Patch 031 with no, partial, and full states.
- [x] Canary indicators. Implemented in Patch 032 as bounded dynamic-string evidence.
- [x] Stripped-status indicators. Implemented in Patch 033 as bounded section-table metadata.
- [x] Section labels as annotations. Implemented and hardened in Patches 034-036.
- [x] Automated `readelf` comparison. Implemented as `make readelf-comparison-smoke` in Patch 037.
- [x] Optional `checksec` and `rabin2 -I` comparison. Implemented as `make optional-tool-comparison-smoke` in Patch 037.
- [x] Controlled mitigation fixtures. Mitigation matrix coverage expanded through Sprint 8.


## Deferred historical-review findings

The historical review also produced items that remain intentionally deferred to
later sprints rather than Patch 037:

- Decoder-backed candidate validity and coverage reconciliation remain Sprint 9
  and Sprint 13 work.
- Schema `0.2.0`, report identity, target digests, command identity, and
  completeness/truncation fields remain Sprint 9 work.
- Publication-grade benchmarking, high-resolution timing, frozen corpus, and
  normalized baseline definitions remain Sprint 12 and Sprint 13 work.
- SARIF, CI policy gates, and enterprise export formats remain Sprint 15 work.

### Sprint 9: evidence provenance and schema transition

- [ ] Candidate evidence side-car record.
- [ ] Raw, exact, semantic-exact, decoder-valid, and semantic-decoded evidence tiers.
- [ ] Analysis completeness and truncation fields.
- [ ] Top-level report identity.
- [ ] Schema `0.2.0` and migration notes.
- [ ] Decoder-gap measurement and embedded-decoder decision gate.

### Sprint 10: primitive expansion

- [ ] Multi-pop patterns.
- [ ] Conservative register-transfer patterns.
- [ ] Narrow memory-read and memory-write patterns.
- [ ] Clobber and memory side-effect facts.
- [ ] Controlled fixture for every new semantic rule.
- [ ] Score entries only after semantic validation.

### Sprint 11: reproducible corpus

- [ ] Compiler, optimization, linkage, and hardening matrix.
- [ ] Target/source/tool hashes and exact build commands.
- [ ] Manifest validator and regeneration workflow.
- [ ] Fixed preview corpus membership.
- [ ] Redistribution and license records for larger targets.

### Sprint 12: high-resolution benchmark preview

- [ ] Nanosecond-resolution timing.
- [ ] Per-child CPU and max RSS capture.
- [ ] Batching or larger-target policy for sub-resolution runs.
- [ ] Randomized tool order and warmup policy.
- [ ] Pilot comparison campaign.
- [ ] `v0.1.0-rc1` preview release dry run.

## Extended research tranche

### Sprint 13

- [ ] Publication-grade comparative benchmark campaign.
- [ ] Coverage-definition reconciliation.
- [ ] Raw result freeze and generated summaries.

### Sprint 14

- [ ] Mitigation-aware binary triage model.
- [ ] Fact, heuristic, and limitation separation.
- [ ] Evidence-backed representative primitive selection.

### Sprint 15

- [ ] Schema and automation stabilization.
- [ ] Optional CI policy modes with stable exit semantics.
- [ ] SARIF feasibility as a report adapter.

### Sprint 16

- [ ] Public network-facing infrastructure case study.
- [ ] Defined analyst tasks and utility criteria.
- [ ] Reproducible case-study artifacts.

### Sprint 17

- [ ] Replication package and paper freeze.
- [ ] Claim-to-evidence matrix.
- [ ] Clean-environment reproduction rehearsal.

### Sprint 18

- [ ] `v0.1.0` release.
- [ ] Checksummed source and binary artifacts.
- [ ] Final paper and submission package.
- [ ] Extended research retrospective.

## Cross-cutting backlog

### Parser and safety

- [x] Preserve read-only target mappings and non-executable internal arenas in the current architecture.
- [x] Enforce explicit bounded candidate-record capacity without silent truncation.
- [ ] Add explicit resource limits for every future file-derived table and count.
- [x] Add shared checked table arithmetic before dynamic-section parsing. Patch 028 centralized checked multiplication, addition, table extents, and per-entry offsets in `src/bounds.asm` and routed ELF/PHDR parsing through those helpers.
- [x] Define crash minimization and corpus promotion rules for deterministic mutation results.
- [ ] Exercise and document regression minimization on the first stable parser defect.
- [ ] Evaluate coverage-guided fuzzing only after deterministic smoke coverage is mature.

### Decoder and validity

- [ ] Keep external tools as validators until measured gaps justify an embedded decoder.
- [ ] Preserve raw scanner metrics independently from decoder-backed metrics.
- [ ] Document decoder licensing, dependencies, and performance cost before integration.

### Metrics and scoring

- [ ] Keep raw, exact, semantic, validated, unknown, and scored counts distinct.
- [ ] Add bad-byte, clobber, dereference, and uncertainty adjustments only after facts exist.
- [ ] Keep binary-level triage separate from per-gadget score.

### Benchmark and research

- [ ] Preserve optional baseline status and exact versions in every comparison artifact.
- [ ] Capture target and tool SHA-256 hashes.
- [ ] Never aggregate historical runs from different hosts without explicit stratification.
- [ ] Keep smoke evidence separate from publication evidence.
- [ ] Generate tables and figures from raw data.

### Release and publication

- [ ] Freeze corpus, baselines, schema, and benchmark methodology before the final campaign.
- [ ] Keep release artifacts separate from generated development state.
- [ ] Require public documentation, bundle hygiene, checksums, and clean-tag verification.
- [ ] Keep ARM64, PE, Mach-O, JOP/COP/SROP, and full decoder work out of `v0.1.0` unless evidence changes the scope.

## Local-only process boundary

Private course context and state tracking belong under `.local/project-context/` and remain excluded from public source bundles. Public backlog entries describe repository work and evidence only.

## Patch 026 and Patch 027 checkpoint

The deterministic mitigation oracle is implemented. Patch 027 corrects its stale zero-executable-region text expectation while preserving the explicit reporter wording and Make fail-fast behavior. Patch 028 implements the shared checked arithmetic and bounded table-view helper layer, then expands hostile-input coverage for table-end overflow. Regression minimization remains a standing policy for future parser defects. Patch 029 closes Sprint 7 and starts the Sprint 8 mitigation-depth tranche. Patch 030 implements the first bounded Sprint 8 metadata view for `PT_DYNAMIC` and expands the mitigation oracle to cover bind-now evidence plus dynamic-table malformed cases. Patch 031 uses that evidence for no, partial, and full RELRO reporting and adds duplicate-`PT_DYNAMIC` rejection.


## Sprint 8 entry backlog

Sprint 7 closed the hostile-input and checked-arithmetic foundation. The next backlog priority is bounded mitigation metadata:

- preserve the Patch 030 range-checked `PT_DYNAMIC` entries needed for RELRO and binding evidence,
- preserve the no, partial, and full RELRO split with controlled fixtures,
- add canary indicators as evidence-qualified signals, not proof of complete stack protection,
- add malformed coverage for every new table, count, offset, and string view,
- defer primitive expansion until mitigation-depth parsing preserves all Sprint 7 gates.

## Sprint 8 Patch 032 backlog update

Completed: first canary indicator, stripped-state indicator, JSON Schema tightening, permanent mitigation-matrix promotion of valid non-`DT_NULL` dynamic coverage, direct gadgets JSON coverage, invalid dynamic string-table malformed coverage, duplicate dynamic-string singleton rejection, string-table scan-cap coverage, and `make clean-results` hygiene. Remaining Sprint 8 work: optional external comparison helpers and validation-discovered defects.

## Sprint 8 Patch 033 backlog update

Patch 033 completes the stripped-status indicator and promotes duplicate dynamic-string singleton and dynamic string-table scan-cap review cases into the permanent mitigation oracle. Remaining Sprint 8 backlog should prioritize optional external comparison helpers before primitive expansion.

## Sprint 8 Patch 034 backlog update

Patch 034 completes the first section-label annotation pass. Patch 035 resolves the validation-discovered section-label defects. Remaining Sprint 8 work is paused for historical review before Sprint 9 evidence provenance; optional `readelf`, `checksec`, or `rabin2` comparison helpers remain useful later.


## Sprint 8 Patch 035 backlog update

Patch 035 hardens section-label rendering and overlap handling, adds a focused section-label smoke target, and removes process-global label-helper state. The next scheduled activity is the historical patch review pause before Sprint 9 begins.

## Sprint 8 Patch 036 backlog update

Patch 036 resolves the immediate historical-review hardening items: byte-safe JSON for target paths and bounded section labels, file-offset plus virtual-address agreement for labels, Docker `.env` context exclusion, benchmark artifact sanity checks, JSON coverage-register validation, per-run temporary directories, and robust missing-tool install hints. Remaining industry-comparison work stays in Sprint 9 and Sprint 12/13: provenance schema `0.2.0`, decoder-gap measurement, high-resolution benchmarks, pinned baseline environments, and normalized coverage definitions.
