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

## Completed Sprint 8 tranche

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
- Schema `0.2.0`, report identity, command identity, and
  completeness/truncation fields are implemented in Patch 040. Target digests
  remain Sprint 9 work; Patch 041 completes raw, exact-suffix, and semantic-exact per-candidate provenance.
- Publication-grade benchmarking, high-resolution timing, frozen corpus, and
  normalized baseline definitions remain Sprint 12 and Sprint 13 work.
- SARIF, CI policy gates, and enterprise export formats remain Sprint 15 work.

### Sprint 9: evidence provenance and schema transition

- [x] Fixed-size command-level analysis summary.
- [x] Analysis completeness, candidate capacity, truncation, dropped-count knowledge, and region-progress fields.
- [x] Top-level report type and command identity.
- [x] Schema `0.2.0`, migration notes, and retained representative final-shape
  `0.1.0` compatibility gate.
- [x] `gadgets` and `analyze` shared-report parity with distinct command identity.
- [ ] Target digest and additional run identity where the final provenance contract requires them.
- [x] Candidate evidence side-car record.
- [x] Raw, exact, and semantic-exact candidate evidence tiers; decoder-valid and semantic-decoded remain pending measured decoder work.
- [x] Controlled and selected-system decoder-gap measurement harness with
  hashes, commands, raw artifacts, timing/RSS smoke facts, and categorized
  boundary/canonicalization differences.
- [x] Embedded-decoder decision procedure and evidence requirements.
- [x] Authoritative decoder decision after local campaign review: keep the default runtime decoder-free and reserve a future decoder for an optional evidence adapter.

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

## Sprint 8 closeout update

Sprint 8 is closed after Patch 039. Completed work includes bounded dynamic
metadata, RELRO refinement, canary and stripped indicators, section-label
annotations, hostile metadata hardening, byte-safe JSON rendering, automated
`readelf` comparison, optional `checksec` / `rabin2 -I` comparison helpers,
Docker context hygiene, benchmark-integrity gates, and final optional-helper
argument validation.

The next active tranche is Sprint 9. Do not add new semantic primitive families
until Sprint 9 has established report identity, provenance, candidate
completeness, truncation state, and schema `0.2.0` transition rules.

Patch 039 resolves the remaining Patch 037/Patch 038 validation follow-ups:

- direct optional comparator helpers no longer false-pass on reversed arguments,
- benchmark-integrity smoke directly covers non-finite RSS values,
- strict shell lint policy is documented as an optional clean gate.


## Sprint 8 closeout correction disposition

Patch 039 closed the Patch 038 closeout blockers. Patches 040-041 supply schema `0.2.0`, report identity, completeness, parity, and candidate provenance. Patches 042-043 add decoder-gap evidence, immutable snapshots, and the decoder-free default. Patch 044 corrects the remaining campaign, parser, archive, and public-fixture defects. Remaining Sprint 9 work is the Patch 045 closeout audit and context/environment refresh.


## Sprint 9 Patch 040 backlog update

Patch 040 completes the command-level report envelope: schema `0.2.0`, report
and command identity, explicit complete-success facts, retained representative
final-shape `0.1.0` compatibility, and focused schema/parity validation. It preserves the existing
4096/4097 capacity contract and does not emit partial reports.

The next backlog priority is the candidate evidence side-car. It must be keyed
by candidate index, preserve existing raw/exact/semantic/unknown/scored counts,
and expose exact-suffix versus semantic-exact provenance without embedding
variable-length decoder state in `gadget_record`. Decoder-gap measurement and
target digest policy follow that evidence foundation.


## Sprint 9 Patch 041 backlog update

Patch 041 completes the initial candidate provenance side-car and per-candidate
JSON evidence for raw, exact-suffix, and semantic-exact facts. It also closes
Patch 040 validation findings in nested-call ABI conformance, the formal-schema/semantic
validator split, bundle-path hygiene, exact capacity diagnostic oracle, focused
JSON harness coverage, benchmark identity grouping, and repository-facing
wording.

Remaining Sprint 9 work is authoritative decoder-gap campaign review, the
embedded-decoder decision record, and any narrowly justified target-identity
refinement. Broad primitive expansion remains deferred to Sprint 10.


## Sprint 9 Patch 042 backlog update

Patch 042 closes the Patch 041 public-bundle validation defect with one
root-independent ZIP policy shared by the checker and regression smoke. It also
adds the controlled and selected-system decoder-gap campaign without changing
runtime analysis or report facts. The campaign preserves analyzer, validator,
objdump, and target identity; SHA-256 hashes; exact commands; raw JSON and
disassembly; smoke timing/RSS; duplicate/canonicalization facts; boundary
disagreements; and unsupported canonical sequences.

The remaining Sprint 9 decision is interpretive rather than another measurement
surface: review the authoritative local campaign and record whether decoder
embedding is deferred, exposed only as optional external verification, or
approved behind an isolated adapter. Target digest work should be added to the
runtime report only if that review or the later corpus contract demonstrates a
machine-consumer need that cannot be satisfied by external manifests.

## Sprint 9 Patch 043 backlog update

Patch 043 closes the reviewed decoder-gap campaign integrity and public artifact
boundary defects. The default runtime remains freestanding and decoder-free.
Future decoder work is optional and must use side-car facts, preserve raw
metrics, and justify its dependency, license, binary-size, latency, RSS, and
hostile-input costs through fixed-corpus evidence.

Patch 044 is the corrective campaign and release-boundary hardening patch. It
closes the post-rename signal race, measured-child cleanup, objdump prefix and
barrier parsing, local/central ZIP metadata, ZIP64 semantics, production-wrapper
coverage, and public negative-fixture defects.

Sprint 9 has one remaining planned patch: Patch 045 closeout. It reviews
architecture and contracts, refreshes private project context, inspects
development configuration and Docker Buildx behavior, reconciles the roadmap,
and publishes the Sprint 9 retrospective without adding primitive breadth.

## Sprint 9 Patch 044 backlog update

Completed in Patch 044:

- observable-state rollback across post-rename `SIGINT` and `SIGTERM` windows;
- measured process-group kill/reap on timeout or interruption;
- reviewed objdump prefix/near-return normalization and control-flow barriers;
- metadata-only local/central ZIP reconciliation and strict recognized extras;
- production shell-wrapper replay for every archive smoke case;
- synthetic public-boundary fixtures and broader path/copy/case detection;
- candidate-scoped decoder and evidence-gated parallelism design constraints.

Deferred with explicit classification:

- private 40-file context and orchestration/configuration refresh: Patch 045;
- Docker Buildx host-state remediation: Patch 045 environment review;
- optional decoder and concurrency implementation: measured Sprint 12/13 gate;
- primitive-family expansion: Sprint 10;
- publication-grade claims: Sprints 12 and 13.
