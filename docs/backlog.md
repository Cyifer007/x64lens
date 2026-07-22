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

- Sprint 9 completed current candidate provenance and external decoder-gap
  reconciliation. Under the current roadmap, decoder-backed runtime validity is
  conditional Sprint 14 ablation work, and frozen coverage reconciliation
  belongs to Sprint 17.
- Schema `0.2.0`, report identity, command identity, and
  completeness/truncation fields are implemented in Patch 040. Campaign and
  benchmark artifacts retain target digests externally; Patch 041 completes
  raw, exact-suffix, and semantic-exact per-candidate provenance.
- High-resolution diagnostic measurement begins in Sprint 11. Frozen corpus, normalized baseline definitions, preview measurement, and publication-grade trials belong to Sprints 15 through 17.
- SARIF, CI policy gates, and enterprise export formats remain Sprint 19 work.

### Sprint 9: evidence provenance and schema transition — complete

- [x] Fixed-size command-level analysis summary.
- [x] Analysis completeness, candidate capacity, truncation, dropped-count knowledge, and region-progress fields.
- [x] Top-level report type and command identity.
- [x] Schema `0.2.0`, migration notes, and retained representative final-shape
  `0.1.0` compatibility gate.
- [x] `gadgets` and `analyze` shared-report parity with distinct command identity.
- [x] Candidate evidence side-car record.
- [x] Raw-candidate, exact-suffix, and semantic-exact evidence tiers;
  decoder-validated and semantic-decoded remain reserved future layers.
- [x] Controlled and selected-system decoder-gap measurement harness with
  hashes, commands, raw artifacts, timing/RSS smoke facts, and categorized
  boundary/canonicalization differences.
- [x] Immutable campaign inputs, signal-safe publication, child-process cleanup, external-parser integrity, and portable archive policy.
- [x] Embedded-decoder decision procedure and evidence requirements.
- [x] Decoder-free, single-worker reference profile with candidate-scoped decoder and deterministic parallelism ablation gates.
- [x] Sprint 9 architecture, contract, public-boundary, release, roadmap, and validation closeout.
- Deferred beyond Sprint 9: a target digest inside the runtime report remains optional if later required by the final provenance contract; campaign and benchmark artifacts already retain target hashes externally.

### Sprint 10: primitive expansion — complete

- [x] First ordered multi-pop argument-control family with conservative fallback.
- [x] Exact `stack_pop_order` plus machine-readable `clobbers` and
  `side_effects` fields for current reports.
- [x] Separate five-candidate fixture, JSON parity, and unscored-family gate.
- [ ] Additional selected multi-pop families only when their effects remain
  unambiguous.
- [x] First conservative register-transfer family with explicit source,
  destination, destination clobber, stack, and `register_write` facts. Patch 047.
- [ ] Additional register-transfer forms remain evidence-gated follow-up work; they are not required for Sprint 10 closure.
- [x] First narrow qword base-plus-zero memory-read and memory-write patterns.
- [x] Memory-dereference facts and destination clobbers for the represented domain.
- [x] Controlled fixture for every implemented Sprint 10 semantic rule.
- [x] Complete current-family effect and clobber facts, including implicit return stack reads, syscall `rcx`/`r11` clobbers, and the `leave`-driven `rbp` overwrite.
- [x] Machine-readable fixture coverage table and per-family false-positive boundaries.
- [x] First reviewed score entries after effect validation: ordered two-pop 95 and positive aligned stack adjustment 35. Register transfer and memory remain unscored pending controllability facts.

### Sprint 11: diagnostic benchmark foundation

- [x] High-resolution standard-library runner with monotonic nanosecond timing,
  accurately scoped Linux `wait4` CPU/max-RSS capture, retained runner/spec identity,
  hashed tool/target retention, write-sealed execution copies, final artifact
  reconciliation, failed-row retention, process-group cleanup, and
  transactional result publication.
- [x] Provisional reproducible corpus with hashes, build commands, and licenses.
- [x] Timer-floor samples, below-floor labels, warmup retention, alternating
  order, and explicit warm/uncontrolled cache policy.
- [x] Truthful initial task authority: gadget JSON and analyze JSON are current
  command-identity parity conditions; scanner-only cost is explicitly
  unavailable rather than inferred from report timing.
- [ ] Add a scanner-only condition only through a reviewed instrumentation seam
  when diagnostic evidence justifies it.
- [x] Initial planned baseline task records for ROPgadget, Ropper, and ropr.
- [x] Patch 057 runner/corpus integrity correction: execution-sealed target
  inputs, exact workspace/member closure, checked cleanup, safe clean path, and
  non-root oracle parity.
- [ ] Baseline adapters, normalized task definitions, and version locks.
- [ ] Provisional corpus diagnostic campaign and development gap register.
- [x] Diagnostic rows isolated from future frozen campaigns.

### Sprint 12: loader and mitigation precision

- [ ] PIE executable versus shared-object distinction.
- [ ] Bounded CET IBT and SHSTK GNU-property evidence.
- [ ] Overlapping executable-region scan/count policy.
- [ ] `p_align`, congruence, virtual-range, and executable-entrypoint behavior.
- [ ] Explicit ELF extended-numbering support or stable unsupported result.
- [ ] Deterministic malformed and mitigation fixtures for every new parser path.

### Sprint 13: semantic capability completion

- [ ] Generic exact-pop semantic decision for all 16 GPRs.
- [ ] Linux syscall `r10` argument-role decision.
- [ ] Score/null policy freeze for every release-facing family.
- [ ] Only measured bounded family additions with complete effects and fixtures.
- [ ] Diagnostic restart for any changed task definition.

### Sprint 14: optional profile ablations

- [ ] Candidate-scoped decoder profile when a measured gap justifies it.
- [ ] Target-level concurrency baseline.
- [ ] Candidate-validation worker profile with deterministic output.
- [ ] Region-worker experiment only after overlap and global-capacity rules are fixed.
- [ ] Separate dependency, binary-size, CPU, RSS, wall-time, output-hash, and cleanup evidence.

### Sprint 15: campaign freeze

- [ ] Final corpus manifest, licenses, hashes, and regeneration.
- [ ] Frozen schema/extractor, runner, baselines, commands, task definitions, and environment strata.
- [ ] Coverage-definition reconciliation specification.
- [ ] Campaign identifier and restart procedure.

### Sprint 16: preview campaign

- [ ] Frozen pilot across every condition.
- [ ] Raw rows and generated preview summaries.
- [ ] `v0.1.0-rc1` release rehearsal and checksummed artifacts.

### Sprint 17: publication comparative campaign

- [ ] Publication-grade repeated trials.
- [ ] Coverage-definition reconciliation.
- [ ] Raw result, summary, table, and figure freeze.

### Sprint 18: mitigation-aware triage

- [ ] Binary-level triage record separate from per-candidate score.
- [ ] Fact, heuristic, evidence, confidence, and limitation separation.
- [ ] Representative primitive selection and contradictory-evidence fixtures.

### Sprint 19: automation and schema stabilization

- [ ] Release-facing schema compatibility freeze.
- [ ] Optional CI policy semantics and stable policy exit codes.
- [ ] SARIF feasibility as a report adapter.

### Sprint 20: infrastructure case study

- [ ] Public network-facing target set and predefined analyst tasks.
- [ ] Reproducible case-study evidence and limitations.

### Sprint 21: replication and paper freeze

- [ ] Independent clean-environment rehearsal.
- [ ] Claim-to-evidence matrix and generated paper figures/tables.
- [ ] Release-candidate artifact validation.

### Sprint 22: first research release

- [ ] `v0.1.0` release.
- [ ] Checksummed source, binary, corpus, benchmark, case-study, and reproduction artifacts.
- [ ] Final paper and submission package.
- [ ] Extended research retrospective and post-release backlog.

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

- [x] Keep external tools as validators until measured gaps justify an embedded decoder; Sprint 9 retains a decoder-free default.
- [x] Preserve raw scanner metrics independently from decoder-backed metrics.
- [x] Define decoder licensing, dependency, RSS, latency, and failure-mode gates before integration; quantitative ablation remains future work.

### Metrics and scoring

- [ ] Keep raw-candidate, exact-pattern, semantic-candidate, decoder-validated, semantic-decoded, unknown-candidate, and scored-candidate counts distinct.
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

Patch 036 resolves the immediate historical-review hardening items: byte-safe JSON for target paths and bounded section labels, file-offset plus virtual-address agreement for labels, Docker `.env` context exclusion, benchmark artifact sanity checks, JSON coverage-register validation, per-run temporary directories, and robust missing-tool install hints. Remaining industry-comparison work stays in Sprint 9 and Sprints 11-17: provenance schema `0.2.0`, decoder-gap measurement, high-resolution benchmarks, pinned baseline environments, and normalized coverage definitions.

## Sprint 8 closeout update

Sprint 8 is closed after Patch 039. Completed work includes bounded dynamic
metadata, RELRO refinement, canary and stripped indicators, section-label
annotations, hostile metadata hardening, byte-safe JSON rendering, automated
`readelf` comparison, optional `checksec` / `rabin2 -I` comparison helpers,
Docker context hygiene, benchmark-integrity gates, and final optional-helper
argument validation.

At that checkpoint, Sprint 9 became the next active tranche. New semantic
primitive families remained deferred until Sprint 9 established report identity,
provenance, candidate completeness, truncation state, and schema `0.2.0`
transition rules.

Patch 039 resolves the remaining Patch 037/Patch 038 validation follow-ups:

- direct optional comparator helpers no longer false-pass on reversed arguments,
- benchmark-integrity smoke directly covers non-finite RSS values,
- strict shell lint policy is documented as an optional clean gate.


## Sprint 8 closeout correction disposition

Patch 039 closed the Patch 038 closeout blockers. Patches 040-041 supply schema `0.2.0`, report identity, completeness, parity, and candidate provenance. Patches 042-043 add decoder-gap evidence, immutable snapshots, and the decoder-free default. Patch 044 corrects the remaining campaign, parser, archive, and public-fixture defects. At that checkpoint, Patch 045 remained as the public architecture, contract, release-boundary, roadmap, and validation closeout.


## Sprint 9 Patch 040 backlog update

Patch 040 completes the command-level report envelope: schema `0.2.0`, report
and command identity, explicit complete-success facts, retained representative
final-shape `0.1.0` compatibility, and focused schema/parity validation. It preserves the existing
4096/4097 capacity contract and does not emit partial reports.

The next backlog priority is the candidate evidence side-car. It must be keyed
by candidate index, preserve existing raw-candidate/exact-pattern/
semantic-candidate/unknown-candidate/scored-candidate counts,
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

At that checkpoint, the remaining Sprint 9 decision was interpretive: review
the controlled and selected-system campaign evidence and choose among deferring
decoder embedding, retaining optional external verification, or approving an
isolated adapter. Runtime target-digest work remains a separate compatible
decision unless a later corpus contract establishes a machine-consumer need
that external manifests cannot satisfy.

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

Patch 045 completed the Sprint 9 closeout by reviewing architecture and
contracts, reconciling the public roadmap and release boundary, recording the
defensive deployment profile, and publishing the retrospective without adding
primitive breadth.

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

- Docker-environment qualification guidance: Patch 045 closeout;
- optional decoder and concurrency implementation: then-current Sprints 12/13
  measurement gate;
- primitive-family expansion: Sprint 10;
- publication-grade claims: then-current Sprints 12 and 13 plan.

## Sprint 9 closeout decisions

- The default runtime remains a static, dependency-free, single-worker analyzer.
- Candidate-scoped decoder validation is the preferred future experiment; whole-image mandatory decoding is not approved.
- Target-level concurrency is the safest early throughput option. Candidate-validation and region-level concurrency require deterministic merge, global-capacity, RSS, and no-partial-output proofs.
- Docker-environment failures are classified separately from product failures only when the complete Docker validation passes in a qualified environment.
- Sprint 10 must not redefine raw, exact-suffix, semantic-exact, unknown,
  provenance, completeness, or score metrics while adding new primitive families.

### Patch 047 validation follow-up

- [x] Reject single-pop `controls` values that disagree with exact pattern and `stack_pop_order` facts.
- [x] Exercise all 16 single-pop metadata entries and mixed legacy/REX two-pop order.
- [x] Remove unmeasured resource language from the decoder-ablation roadmap.

### Patch 048 validation and stack-adjust update

- [x] Define the missing JSON object delimiters required by register-transfer output.
- [x] Reject exact-pattern/terminator, bare-return control, and bare-return stack contradictions in common validation.
- [x] Add exact positive aligned `add rsp, imm8; ret` recognition with known total stack delta.
- [x] Record `stack_adjust` and arithmetic `flags_write` effects without growing the candidate record or arena.
- [x] Add controlled positive and fallback fixtures plus an independent objdump oracle.
- [x] Add bounded public ZIP textual-content validation separate from metadata-only archive safety.
- [x] Define the bounded memory-effect record before promoting memory read/write families.
- [x] Select bounded memory effects for Patch 049 rather than another register-only family.

## Sprint 10 Patch 049 backlog update

Patch 049 establishes the first structured memory-effect side-car and bounded qword base-plus-zero read/write families. Remaining Sprint 10 work is not generic pattern-count expansion. It is a closeout review of fixture coverage, false-positive boundaries, schema compatibility, score deferral, and Sprint 11 corpus requirements. Displacement, SIB/index, RIP-relative, and broader memory families remain deferred until exact operand semantics and fixtures are ready.


## Sprint 10 Patch 050 backlog update

Patch 050 completes current-family side-effect and clobber facts, reconciles the transfer fixture with Patch 049 cross-family memory promotion, makes multi-command fixture recipes fail fast, isolates stale internal-manifest verification, and adds the maintained family coverage/false-positive table. It adds no primitive family and no score.

Before Sprint 11 begins, Patch 053 must perform the planned architecture and capability reassessment. Required review items include:

- [ ] distinguish PIE executables from shared objects without overstating `ET_DYN`;
- [ ] add or explicitly defer bounded GNU property evidence for CET/IBT/SHSTK;
- [ ] define count semantics for overlapping executable `PT_LOAD` ranges;
- [ ] review all current-family score candidates using completed effect facts;
- [ ] reconcile the capability snapshot with the pre-`v0.1.0` release scope;
- [x] identify which capability gaps must precede the Sprint 15 campaign freeze
  and which remain post-release.

Patch 052 is reserved for Patch 051 review corrections; Patch 054 closes Sprint 10 after the Patch 053 capability reassessment or carries its smallest required correction. Broader displacement, SIB/index, RIP-relative, decoder, JOP/COP/SROP, and default parallel work remains deferred unless the evidence-based roadmap review changes scope.

## Sprint 10 Patch 051 backlog update

Patch 051 reconciles the committed Patch 050 foundation with the architectural-
effect side-car, one-per-pattern coverage, centralized fixture runner, and
selective scores. Remaining Sprint 10 sequence:

- Patch 052: resolve Patch 051 findings;
- Patch 053: architecture and capability reassessment;
- Patch 054: Sprint 10 closeout.

The reassessment still owns PIE-versus-DSO evidence, CET/IBT/SHSTK property
evidence, overlapping executable-segment semantics, and pre-release capability
priorities.


## Sprint 10 Patch 052 corrective update

Patch 052 corrects the Patch 051 effect and gate findings without expanding the
primitive catalog. Full-width syscall descriptors, the zero-immediate return
boundary, contracted text separators, canonical memory side-car reconciliation,
numeric score-policy mutation gates, and strict-lint availability are permanent
validation surfaces. Patch 053 remains the architecture/capability reassessment;
Patch 054 remains Sprint 10 closeout.


## Sprint 10 Patch 053 roadmap reassessment update

Patch 053 corrects the Patch 052 internal-harness symbol, reconciles public
documentation with the Patch 052 contracts, adds manifest-relative checksum
verification, and establishes the twenty-two-sprint benchmark-informed roadmap.
Sprint 11 begins diagnostic measurement without freezing the publication
corpus. Sprints 12 through 14 close loader, mitigation, semantic, and
optional-profile decisions; Sprint 15 freezes the campaign. Patch 054 remains
Sprint 10 closeout.

## Sprint 10 Patch 054 closeout update

Patch 054 closes Sprint 10 without adding another primitive family. The sprint now has maintained semantic-family, exact-pattern, fixture-suite, effect-completeness, false-positive, and score-policy authorities. The default analyzer remains bounded, dependency-free, decoder-free, and one-worker.

Sprint 11 is the active diagnostic benchmark foundation. Its provisional corpus and measurement method may redirect implementation. The confirmatory campaign freezes in Sprint 15; preview, publication, operational, replication, and release work follows through Sprint 22.

Deferred capability work remains evidence-gated:

- broader register-transfer and memory-address forms;
- candidate-scoped decoder validation;
- deterministic concurrency profiles;
- JOP, COP, SROP, symbolic execution, chain generation, other formats, and other architectures.


## Sprint 11 Patch 055 update

Patch 055 establishes the diagnostic runner and task-scope foundation without
changing the analyzer runtime. Every campaign is explicitly mutable diagnostic
evidence, retains hashed inputs, executes write-sealed byte-identical copies,
retains failed rows, measures a timer floor, reconciles captured artifacts after
the final child, and publishes complete result trees without replacing an
existing identity.

The patch also closes two Patch 054 validation false negatives. Roadmap
chronology now includes seven path-specific stale-phrase regressions. Sprint 10
closeout counts are reconciled against the independent one-per-pattern report,
and record sizes, capacity, arena size, tool/schema versions, and optional-
profile defaults are read from maintained source authorities. Success output is
derived from observed values.

Remaining Sprint 11 priorities are corpus generation, baseline adapters,
development summaries, and the Sprint 12-14 engineering gap register.

## Sprint 11 Patch 056 update

Patch 056 completes the first provisional-corpus regeneration surface:

- [x] project-authored freestanding source and Apache-2.0 license binding;
- [x] 24-target GCC/Clang, `O0`/`O2`, role, and hardening matrix;
- [x] exact command, source, builder, tool, environment, output, and hash records;
- [x] bounded ELF generation checks without target execution;
- [x] two-build byte/mode/mtime reproducibility;
- [x] interruption cleanup, semantic tamper rejection, and no-replace publication;
- [x] generated-corpus Git, Docker, and public-bundle exclusion.

Remaining Sprint 11 priorities are normalized baseline adapters, corpus-backed
diagnostic rows, development summaries, coverage-definition inputs, and the
Sprint 12-14 engineering gap register.

## Sprint 11 Patch 057 update

Patch 057 resolves the confirmed diagnostic-integrity defects before expanding
comparison scope:

- target memfds require a kernel-enforced no-execute creation policy and
  execution seal;
- runner and corpus staging cleanup is checked and mode-robust;
- compiler metadata commands leave an empty workspace and build commands may
  leave only the named bounded output;
- corpus verification requires the exact expected files and directories;
- `clean-provisional-corpus` is phony and removes only the fully verified,
  specification-derived corpus below its output root; and
- checksum-regeneration probes run under non-root permissions.

Normalized baseline adapters move to Patch 058. Development summaries and the
engineering gap register move to Patch 059, followed by Sprint 11 closeout in
Patch 060 unless later evidence requires another corrective boundary.
