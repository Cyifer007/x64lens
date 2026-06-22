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

## Active next tranche

### Sprint 7: hostile-input hardening

- [x] Deterministic mutation smoke harness.
- [x] Stable signal, timeout, exit-code, elapsed-time, and output-size capture.
- [x] Regression-fixture policy and reserved minimized-corpus path.
- [x] First minimized parser regression fixture for invalid ELF64 section-header stride.
- [ ] Committed regression fixture for every newly discovered stable parser defect.
- [ ] Shared bounded-table iteration rules or helpers.
- [ ] Central checked arithmetic for multiplication, addition, counts, and end offsets.
- [x] Initial program-header, section-header, executable-segment, and boundary range mutations.
- [x] Exact ELF64 section-header entry-size validation.
- [x] Explicit candidate-capacity failure behavior with no partial output.
- [x] `make malformed-smoke`, `make capacity-smoke`, and Docker validation integration.

### Sprint 8: mitigation and metadata depth

- [ ] Bounded dynamic-section parsing.
- [ ] Full versus partial RELRO.
- [ ] Canary indicators.
- [ ] Stripped-status indicators.
- [ ] Section labels as annotations.
- [ ] Automated `readelf` comparison.
- [ ] Optional `checksec` and `rabin2 -I` comparison.
- [ ] Controlled mitigation fixtures.

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
- [ ] Add shared checked table arithmetic before dynamic-section parsing.
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

## Patch 026 checkpoint

The deterministic mitigation oracle is implemented. Shared checked arithmetic, bounded table views, regression minimization guidance, and provenance fields for promoted malformed fixtures remain Sprint 7 work. Mitigation-depth expansion remains scheduled after parser hardening.
