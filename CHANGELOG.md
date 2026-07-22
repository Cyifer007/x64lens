# Changelog

All notable public changes to x64lens are documented in this file.

The project follows semantic versioning once the first public release is cut.

## Unreleased

### Added

- Sprint 11 Patch 057 diagnostic-integrity correction: non-executable target
  memfds sealed against execute-mode changes, verified staging cleanup, exact
  compiler-workspace and published-member closure, and a manifest-derived safe
  corpus clean path.
- Regression coverage for direct target-execution attempts, mode-locked staging
  trees, undeclared compiler side files, Make clean-path overrides, and non-root
  checksum mutation probes.
- ADR 0043 and the Patch 057 validation record.

- Sprint 11 Patch 056 manifest-driven provisional corpus generation over one project-authored freestanding source: GCC and Clang, `O0` and `O2`, requested non-PIE/PIE/shared roles, and minimal/hardened profiles produce 24 ignored diagnostic ELF targets.
- `make corpus-tools-check`, `make provisional-corpus-build`, `make provisional-corpus-verify`, `make provisional-corpus-smoke`, and `make clean-provisional-corpus`.
- Transactional no-replace corpus publication with source/license/builder snapshots, exact command and tool identity, forced resolved-linker selection, bounded log capture, bounded ELF generation facts, fixed-environment enforcement, late reauthentication, exact checksums, normalized metadata, subreaper cleanup, and regenerated-checksum semantic tamper rejection.
- ADR 0042, the provisional corpus guide, and the Patch 056 validation record.

- Sprint 11 Patch 055 standard-library high-resolution diagnostic runner with hashed retained inputs, write-sealed Linux `memfd` execution copies, final artifact-identity reconciliation, monotonic nanosecond timing, accurately scoped Linux `wait4` resource capture, timer-floor evidence, subreaper cleanup for same-group and escaped descendants, failed-row retention, and transactional no-replace publication.
- Machine-readable Sprint 11 task definitions and a controlled reference specification that measure truthful gadget/analyze JSON command conditions while marking scanner-only cost unavailable.
- `make diagnostic-runner-smoke`, `make diagnostic-task-definitions-smoke`, `make sprint11-diagnostic-reference-smoke`, `make bench-diagnostic-smoke`, ADR 0041, and the Patch 055 validation record.
- `make patch054-corrective-regression-smoke`, path-specific stale-roadmap checks, source-linked Sprint 10 reference-profile validation, independent canonical-report count reconciliation, and data-driven closeout success output.

- Sprint 10 Patch 054 closeout contract, retrospective, ADR 0040, and validation record.
- `make research-roadmap-consistency-smoke` and `make sprint10-closeout-smoke` for machine-checked roadmap chronology, completed Sprint 10 state, and Sprint 11 diagnostic entry.
- Public-content regressions for execution-handoff wording and a co-located
  package-manifest release rule.

- Sprint 10 Patch 053 benchmark-informed diagnostic, capability-hardening, campaign-freeze, preview, publication, operational, and release stage gates.
- A canonical twenty-two-sprint roadmap, Sprint 19 through Sprint 22 plans, machine-readable research-stage authority, and manifest-relative checksum verification.
- ADR 0039, the benchmark/capability stage-gate design, and the Patch 053 validation record.

- Sprint 10 Patch 052 internal memory-sidecar reconciliation, numeric score-policy mutation gates, strict ShellCheck availability, and zero-immediate return regressions.
- ADR 0038 and the Patch 052 validation record.

- Sprint 10 Patch 051 candidate-index architectural-effect side-car, one-per-pattern fixture, exact-pattern catalog, centralized fixture suite, fail-fast gate, and three-contract reconciliation.
- Machine-readable GPR, flag, control-flow, stack-source, and effect-model-completeness facts for all 25 exact patterns.

- Sprint 10 Patch 050 completed side-effect and clobber facts for every currently supported return-ending semantic family, including implicit return stack reads, `syscall` clobbers for `rcx`/`r11`, and the `leave`-driven `rbp` overwrite.
- `make sprint10-family-coverage-smoke`, a machine-readable 11-family fixture/effect/fallback/score-disposition table, and per-family false-positive documentation.
- ADR 0036 and the Patch 050 validation record.

- Sprint 10 Patch 049 exact qword base-plus-zero memory-write and memory-read recognition with structured candidate-index memory effects, conservative fallback, and no score assignment.
- A 12-candidate memory/fallback fixture, `make sprint10-memory-smoke`, and an objdump-backed memory disassembly oracle.
- Authenticated public final-file overlay verification that binds the outer SHA-256, ZIP metadata policy, textual-content policy, and exact internal path/hash/size/mode manifest.
- ADR 0035 and the Patch 049 validation record.

- Sprint 10 Patch 048 exact `add rsp, positive-aligned-imm8; ret` recognition with known total stack delta, explicit `stack_adjust` and `flags_write` effects, conservative fallback, and no score assignment.
- A seven-candidate stack-adjust/fallback fixture, `make sprint10-stack-adjust-smoke`, and an objdump-backed stack-adjust disassembly oracle.
- Bounded public textual-content validation for repository files and public ZIP members, including `.patch` and `.diff` payloads, as a separate gate from metadata-only ZIP safety.
- ADR 0034 and the Patch 048 validation record.

- Sprint 10 Patch 047 exact register-direct `mov r64,r64; ret` recognition with explicit source/destination, destination clobber, `register_write`, and known return stack-delta facts.
- A ten-candidate transfer/fallback fixture, `make sprint10-register-transfer-smoke`, and an objdump-backed transfer disassembly oracle.
- `make json-effect-consistency-smoke`, covering all 16 single-pop metadata relations and mixed legacy/REX two-pop order with contradiction rejection.
- ADR 0033 and the Patch 047 validation record.

- Sprint 10 Patch 046 ordered two-pop argument-control recognition for two
  distinct System V argument registers, with exact execution order retained in
  the existing fixed-size gadget record.
- Machine-readable `stack_pop_order`, `clobbers`, and `side_effects` candidate
  fields, current-producer validation, a five-candidate Sprint 10 fixture, and
  `make sprint10-primitive-smoke`.
- ADR 0032, the primitive-effect model, and the Patch 046 validation record.

- Sprint 9 Patch 045 closeout validation, retrospective, ADR 0031, and the
  defensive deployment profile for air-gapped, incident-response, minimal-
  container, and CI/CD operation.
- `make sprint-closeout-smoke`, which requires strict shell lint before the
  complete native aggregate can close a sprint.
- A direct Linux home-path public-document regression alongside the existing
  Windows, WSL, and macOS cases.

- Sprint 9 Patch 044 adversarial regressions for post-rename signal rollback, measured-child process-group cleanup, 27 reviewed objdump prefix/return forms, local/central ZIP metadata reconciliation, strict ZIP64 semantics, production-wrapper archive replay, and synthetic public-boundary fixtures.
- ADR 0030 and the candidate-scoped decoder/parallelism design gate.
- Sprint 9 Patch 044 validation record; Sprint 9 closeout moves to Patch 045.

- Sprint 9 Patch 043 immutable decoder-gap target snapshots, signal-safe
  transactional result publication, objdump parser diagnostics and barrier
  hardening, and archive metadata/path portability enforcement.
- `make public-docs-hygiene-smoke` and `make decoder-gap-hardening-smoke` for
  timestamped transfer-name rejection, snapshot provenance, parser fixtures,
  and eight signal-interruption publication states.
- ADR 0029 records the decoder-free default runtime and optional future decoder
  adapter boundary.

- Sprint 9 Patch 042 controlled and selected-system decoder-gap evidence
  generation through GNU objdump without adding a runtime decoder dependency.
- `make decoder-gap-smoke`, `make decoder-gap-campaign`, a controlled expected-
  fact specification, an embedded-decoder decision gate, ADR 0028, and Patch
  042 validation documentation.
- Decoder-gap artifacts that preserve analyzer, validator, external-tool, and
  target identity; SHA-256 hashes; exact commands; raw reports and disassembly;
  smoke timing/RSS; boundary disagreements; duplicate/canonicalization facts;
  and unsupported canonical sequences.
- A metadata-only Python ZIP policy shared by the public bundle checker and its
  regression smoke.

- Sprint 9 Patch 041 candidate-index evidence side-car for raw, exact-suffix,
  and semantic-exact provenance.
- Per-candidate JSON evidence kind, validator identity, matched suffix range,
  semantic source, and explicit unknown full-sequence validity.
- Formal Draft 2020-12 schema compatibility validation using the development-only
  `python3-jsonschema` dependency.
- Root-independent patch-bundle hygiene regression fixtures and focused current
  JSON validation in malformed, mitigation, and section-label harnesses.

- Sprint 9 Patch 040 fixed-size analysis-summary record for report type, command identity, selected maximum depth, candidate capacity/count, truncation, dropped-count knowledge, executable-region progress, and complete-analysis state.
- JSON schema `0.2.0`, historical schema `0.1.0` snapshot, representative compatibility fixtures, `make schema-compat-smoke`, ADR 0026, and Patch 040 validation documentation.
- Text and JSON report identity/completeness output shared by `gadgets` and `analyze`.

- Sprint 8 Patch 039 closeout-correction validation record and ADR 0025.
- Sprint 8 Patch 038 closeout validation record, Sprint 8 retrospective, ADR 0024, and roadmap handoff to Sprint 9.
- Optional comparator helper identity validation covering both `<target> <tool>` and `<tool> <target>` invocation order.
- Benchmark-integrity smoke coverage for non-finite RSS metrics.

- Sprint 8 Patch 037 automated `readelf` comparison smoke, optional `checksec`/`rabin2 -I` comparison smoke, benchmark-integrity smoke, Docker context hygiene smoke, and ADR 0023.
- Optional analysis-tool inventory checks for `checksec`, `rabin2`, `strace`, and `shellcheck`.
- Sprint 8 Patch 036 historical-findings hardening validation record and ADR 0022.
- Byte-safe JSON escaping for target paths and bounded section-label strings.
- Benchmark smoke input and metric-domain validation for run count, maximum depth, timing, RSS, and summary artifact selection.
- Sprint 8 Patch 035 section-label hardening smoke target for hostile section names, non-executable overlap, and ambiguous executable overlap.
- ADR 0021 and Patch 035 validation documentation for section-label rendering and ambiguity hardening.
- Sprint 8 Patch 034 section-label annotations for executable regions and gadget candidates using bounded section-name metadata.
- ADR 0020 and Patch 034 validation documentation for section labels as analyst annotations, not loader authority.
- Sprint 8 Patch 033 stripped-status indicator reporting using a bounded section-header scan for `SHT_SYMTAB` evidence.
- Sprint 8 Patch 033 mitigation-oracle expansion for stripped, not-stripped, zero-length dynamic string-table, duplicate `DT_STRTAB`, duplicate `DT_STRSZ`, and dynamic string-table scan-cap cases.
- ADR 0019 and Patch 033 validation documentation for section-derived metadata and strict dynamic singleton policy.
- Sprint 8 Patch 032 canary indicator reporting using a bounded dynamic string-table scan for exact `__stack_chk_fail` evidence.
- Sprint 8 Patch 032 mitigation-oracle expansion for canary-present/canary-absent fixtures, valid non-`DT_NULL` dynamic-table coverage, invalid dynamic string-table references, and direct `gadgets --format json` matrix coverage.
- `make clean-results` for removing ignored local validation and benchmark result artifacts before release packaging or broad text review.
- ADR 0018 and Patch 032 validation documentation for canary indicator semantics and bounded dynamic-string scanning.
- Sprint 8 Patch 031 RELRO refinement that reports no, partial, and full RELRO by combining `PT_GNU_RELRO` with bounded bind-now evidence.
- Sprint 8 Patch 031 mitigation-oracle expansion to full-RELRO valid fixtures, duplicate-`PT_DYNAMIC` malformed coverage, and gadget command-path dynamic malformed coverage.
- ADR 0017 and Patch 031 validation documentation for RELRO evidence semantics and duplicate dynamic-table policy.
- Sprint 8 Patch 030 bounded `PT_DYNAMIC` table view for bind-now evidence, dynamic-entry count, and dynamic terminator state.
- Sprint 8 Patch 030 mitigation-oracle expansion covering `DT_BIND_NOW`, `DT_FLAGS`, `DT_FLAGS_1`, and malformed dynamic-table range and entry-size cases.
- ADR 0016 and Patch 030 validation documentation for the bounded dynamic-table parser seam.
- Sprint 7 Patch 029 closeout validation record and Sprint 7 retrospective.
- Sprint 7-to-Sprint 8 handoff documentation that preserves parser-safety gates before mitigation-depth work begins.
- Sprint 7 Patch 028 shared checked parser arithmetic helpers for unsigned multiplication, unsigned addition, offset-plus-length end validation, table extents, and bounded per-entry table offsets.
- Sprint 7 Patch 028 table-end overflow regression coverage in the malformed-input runner, core regression suite, and mitigation matrix.
- ADR 0015 and Patch 028 validation documentation for the checked parser-arithmetic layer.
- Sprint 7 Patch 026 deterministic mitigation oracle with 11 controlled valid ELF64 layouts and five malformed program-header layouts.
- `make mitigation-matrix-smoke`, generated SHA-256-addressed JSON evidence, ADR 0014, mitigation fixture-matrix documentation, and Patch 026 validation plan.
- Sprint 7 Patch 027 validation plan for the mitigation-oracle expectation correction.
- `make help` as a stable discovery surface for the principal development and validation targets.

- Sprint 7 Patch 025 deterministic malformed-ELF mutation runner with 29 fixed cases, per-case timeout and signal capture, seed SHA-256 recording, and TSV/metadata artifacts.
- `make malformed-smoke`, `make fuzz-mutated-elf-smoke`, `make capacity-smoke`, and `make docker-validation-smoke`.
- Controlled 4096/4097 candidate-boundary fixtures and validator for explicit `EXIT_UNSUPPORTED` behavior without partial output.
- ADR 0013, malformed-input test documentation, regression-promotion policy, first minimized parser regression fixture, and Patch 025 validation plan.
- Canonical eighteen-sprint roadmap covering Sprints 7 through 18.
- Research preview and first-release evidence gates for `v0.1.0-rc1` and `v0.1.0`.
- Evidence provenance and schema evolution design plans.
- Detailed Sprint 7 through Sprint 18 implementation plans.
- ADR 0012 for roadmap expansion and evidence-based release gates.
- `make planning-docs-check` and a repository planning-document consistency validator.
- Sprint 6 Patch 024 validation and closeout planning documentation.

### Changed

- The development container and environment checker now include Clang only for provisional corpus regeneration; the x64lens runtime dependency surface is unchanged.
- Generated provisional corpus trees are ignored, excluded from Docker contexts, and rejected from ordinary public source bundles.

- Close Sprint 10 and activate Sprint 11 as the diagnostic benchmark foundation while retaining Sprint 15 as the campaign-freeze boundary.
- Reconcile the canonical twenty-two-sprint roadmap, release milestones, publication plan, versioning, and active sprint plans with the machine-readable stage authority.

- Separate diagnostic benchmark evidence from the frozen preview and publication campaigns; Sprint 11 measures early, Sprint 15 freezes the campaign, and Sprints 16-17 run confirmatory work.
- Expand the canonical roadmap from eighteen to twenty-two sprints so loader/mitigation precision, semantic completion, and optional decoder/concurrency ablations occur before campaign freeze.
- Keep the dependency-free decoder-free one-worker analyzer as the reference profile while treating broader families and acceleration as measured conditional profiles.

- Advance Sprint 10 through the Patch 052 corrective candidate while preserving the 112-byte raw record, 24-byte architectural-effect side-car, 4,096-candidate capacity, 819,200-byte fixed arena, dependency-free runtime, tool version `0.1.0-dev`, and schema `0.2.0`.
- Treat NASM number-overflow warnings as build failures and make strict ShellCheck mode reject a missing executable.

- Advance Sprint 10 through Patch 051 while preserving the 112-byte raw candidate record, 4,096-candidate capacity, dependency-free one-worker runtime, tool version `0.1.0-dev`, and schema `0.2.0`.
- Increase the fixed command arena from 720,896 to 819,200 bytes for a 24-byte-per-candidate architectural-effect side-car; this is allocation arithmetic, not measured maximum RSS.
- Score ordered two-pop argument control at 95 and positive aligned stack adjustment at 35 only after validating semantic and architectural facts; transfer and memory remain unscored.

- Advance Sprint 10 through the Patch 050 candidate while preserving the 112-byte candidate record, 48-byte evidence record, 16-byte memory-effect record, 4,096-candidate capacity, 720,896-byte fixed arena, dependency-free runtime, tool version `0.1.0-dev`, and schema version `0.2.0`.
- Treat the transfer fixture as a cross-family fixture: four transfers, one memory write, one memory read, and four true return fallbacks.
- Keep Patch 046 compatibility separate from the stronger Patch 050 current-producer effect contract.
- Establish Patch 050 as the committed first-pass foundation for Patch 051 reconciliation; reserve Patch 052 for Patch 051 findings, Patch 053 for architecture/capability reassessment, and Patch 054 for Sprint 10 closeout.

- Advance Sprint 10 through the Patch 049 candidate while preserving the 112-byte candidate record, 4,096-candidate capacity, dependency-free runtime, tool version `0.1.0-dev`, and schema version `0.2.0`.
- Add a 16-byte dense memory-effect side-car and increase the fixed command arena from 655,360 to 720,896 bytes without changing candidate capacity.
- Require the public textual-content checker to inspect its own source and require authenticated final-file overlays to reconcile every distributed member.
- Treat local unified diffs as application artifacts and public final-file overlays as the release-safe distribution surface.

- Advance Sprint 10 through the Patch 048 candidate while preserving the 112-byte candidate record, then-current 655,360-byte arena, 4,096-candidate capacity, decoder-free one-worker runtime, tool version `0.1.0-dev`, and schema version `0.2.0`.
- Require current-producer validation to reconcile exact terminators, bare-return controls and stack facts, stack-adjust immediates, side effects, and known deltas.
- Distinguish public ZIP metadata safety from bounded public textual-content review; final-file public overlays may pass both gates while local application packages remain outside the public release boundary.

- Advance Sprint 10 through Patch 047 while preserving the 112-byte candidate record, 655,360-byte arena, 4,096-candidate capacity, dependency-free runtime, tool version `0.1.0-dev`, and schema version `0.2.0`.
- Require current-producer validation to reconcile single-pop pattern, exact order, semantic controls, and score facts per candidate.
- Keep register-transfer candidates unscored and preserve `controls` as independent control evidence rather than treating every value transfer as external control.

- Close Sprint 9 and advance Sprint 10 as the next implementation tranche.
- Preserve the dependency-free one-worker analyzer as the reference profile;
  candidate-scoped decoding and parallelism remain optional ablations to be
  measured separately.
- Separate archive policy outcomes from optional exact diagnostic wording and
  require the complete Docker matrix before metadata-path write failures are
  classified as environment-specific.
- Reconcile onboarding, schema, metric, release, publication, architecture,
  and roadmap documentation with the completed Sprint 9 state.

- Keep the default analyzer single-worker, freestanding, and decoder-free while defining an optional candidate-scoped decoder and evidence-gated parallel profiles.
- Make decoder-gap publication recover from observable filesystem state and reap measured child sessions on every interruption.
- Reconcile raw local ZIP headers with central-directory records before any public bundle is accepted.

- Bind every decoder-gap comparison to one immutable target snapshot analyzed
  by both x64lens and GNU objdump.
- Keep the default analyzer freestanding and decoder-free; decoder-backed facts
  remain an optional additive evidence profile subject to a later fixed-corpus
  decision gate.
- Make public archive policy independent of root depth, raw/effective ZIP-name
  ambiguity, recognized extra metadata, Windows path portability, and common
  ZIP-container suffixes.

- Make the controlled decoder-gap reconciliation part of native and Docker
  aggregate validation while keeping the host-dependent system campaign a
  separate evidence command.
- Define historical schema compatibility as the retained representative final-
  shape `0.1.0` snapshot rather than every intermediate pre-release emission.
- Align Ubuntu setup instructions with the required development-only
  `python3-jsonschema` dependency.

- Keep schema `0.2.0` backward-compatible with Patch 040 reports while requiring
  candidate provenance for current producer validation.
- Group benchmark summaries by tool name, tool version, schema version, command,
  and target so incompatible evidence is not merged.
- Make capacity stderr checks byte-exact, assert exact-capacity `gadgets`/`analyze` parity with complete provenance, and make bundle generated-path checks independent of archive-root prefix.

- Advance current machine-readable output from schema `0.1.0` to `0.2.0` while keeping tool version `0.1.0-dev` and the checkpoint tag unchanged.
- Require current `gadgets` and `analyze` JSON validation to name the expected command and preserve shared report facts.
- Keep candidate-capacity overflow fail-closed with exit code `6` and empty stdout; schema completeness fields describe successful reports and do not enable partial output.

- Treat Patch 039 as the final Sprint 8 closeout correction after Patch 038 validation found missing non-finite-RSS fixture files and strict-shellcheck cleanup work.
- Harden optional `checksec` and `rabin2` direct helper argument parsing so reversed arguments cannot compare the wrong file and still pass.
- Close Sprint 8 and mark Sprint 9 as the next implementation tranche.
- Include benchmark-integrity, automated readelf comparison, and optional tool comparison in the native validation aggregate.
- Move remaining Makefile smoke outputs to per-run temporary directories.
- Require section-label file-offset and virtual-address evidence to agree before annotating executable regions or candidates.
- Exclude `.env` and `.env.*` files from the Docker build context while preserving a future `.env.example` allowlist.
- Make `bench-summary` refuse mixed benchmark TSV aggregation by default and make `bench-summary-latest` select the newest nonempty TSV artifact.
- Use per-run temporary directories for core and system-binary smoke outputs.
- Render section labels in text through a bounded single-line-safe printer while preserving JSON section strings.
- Assign section labels only from unique file-backed allocated executable sections so non-executable or ambiguous section metadata cannot capture candidate annotations.
- Replace process-global section-label helper state with stack-local annotation context.
- Treat zero-length dynamic string tables whose pointer is exactly at the end of a file-backed load as valid completed negative canary evidence.
- Keep current reports emitting `mitigations.stripped` while allowing same-version schema validation for older `0.1.0-dev` JSON reports that omit it.
- Treat duplicate `DT_STRTAB` and duplicate `DT_STRSZ` entries as malformed dynamic metadata so canary evidence is not order-dependent.
- Extend mitigation text and JSON output with a compatible `stripped` indicator while preserving program headers as executable-region authority.
- Tighten JSON Schema required fields and mitigation conditionals so external consumers receive the same core invariants enforced by the bundled validator.
- Refine RELRO text and JSON output from presence-only reporting to `not found`, `partial`, or `full` while preserving schema version `0.1.0`.
- Reject duplicate `PT_DYNAMIC` program headers as malformed to avoid ambiguous dynamic-entry and terminator semantics.
- Extend mitigation text and JSON output with compatible dynamic-table fields while preserving schema version `0.1.0`.
- Tighten planning-document validation by replacing the Patch 029 advisory placeholder with enforced Sprint 8 Patch 030 checks.
- Mark Sprint 7 complete and define Sprint 8 as the next mitigation-depth sprint while preserving the checked parser-arithmetic and mitigation-oracle gates as entry criteria.
- Mark Sprint 7 as closed after Patch 028 acceptance and move Sprint 8 to the next active implementation tranche.
- Update planning validation to accept the Sprint 7 closed state while keeping the hostile-input, mitigation-oracle, and checked-arithmetic gates discoverable.
- Route ELF64 program-header and section-header table validation through shared checked table-extent helpers.
- Route program-header entry derivation through a bounded per-entry helper before forming pointers.
- Expand the mitigation-matrix malformed case count from five to seven after adding table-end overflow probes.
- Make public-documentation hygiene scan tracked and untracked public files while ignoring generated `tests/results/` evidence.
- Exclude non-source workspace state from permission normalization, Docker build context filtering, Git-ignore coverage, and patch-bundle hygiene.
- Reject invalid file-backed `PT_LOAD` ranges during shared ELF64 validation so `info`, `mitigations`, and `analyze` fail consistently.
- Include the mitigation matrix in native and Docker aggregate validation.
- Make planning validation distinguish all 18 sprint plans from the 12 forward plans.
- Sequence the shared checked-arithmetic refactor after the mitigation oracle so behavior remains fixed during parser changes.
- Move the shared checked-arithmetic refactor to Patch 028 after reserving Patch 027 for the oracle correction.

- Require the fixed 64-byte ELF64 section-header entry size whenever the section-header count is nonzero.
- Include malformed-input and capacity checks in the aggregate validation gate and CI workflow.
- Expand public-documentation hygiene checks for local temporary paths and host-specific prompts.
- Expand patch-bundle hygiene checks for generated malformed-test results and the capacity fixture binary.
- Reordered near-term work so hostile-input safety and mitigation accuracy precede primitive expansion.
- Replaced the twelve-sprint roadmap as the canonical plan while retaining a compatibility document.
- Defined schema `0.2.0` as the planned provenance and completeness transition.
- Refined benchmark methodology for nanosecond timing, per-child resource use, corpus freezes, and campaign separation.
- Updated release, publication, architecture, mitigation, scoring, semantic, and validation documentation for the post-checkpoint plan.
- Updated the README to describe the validated Sprint 6 checkpoint and current release path.
- Extended CI and the release dry-run workflow with repository contract and aggregate validation checks.

### Fixed

- Corrected the Patch 055 diagnostic runner's resource-scope wording, explicit publication-eligibility requirement, spawn-window signal cleanup, immutable execution-input handling, and final retained-artifact reconciliation.
- Excluded root-level patch-application artifacts and Windows alternate-data-stream copies from source tracking, Docker contexts, and ordinary public bundles.
- Hardened the Patch 056 corpus process lifecycle against post-spawn signal leakage and escaped `setsid` descendants; the smoke now covers both cleanup paths and cannot leave a live builder or helper during temporary-tree cleanup.

- Correct contradictory Sprint 11 through Sprint 13 ownership left in active public prose after the Patch 053 roadmap transition.
- Reject private execution-handoff narration in public repository content while retaining generic platform and reproducibility guidance.
- Require every checksum-listed complete-package manifest to be present beside
  its release inventory and verifiable independently of the caller's working
  directory.

- Correct the Patch 052 memory-effect reconciliation harness to use `GADGET_SUMMARY_RECORD_SIZE` at both allocation sites.
- Make delivery checksum verification resolve sibling-relative entries from the manifest directory rather than the caller current directory.
- Correct Patch 052 chronology, schema-optionality, fixture-count, navigation, public-boundary, and unsupported-performance wording.

- Preserve the full 64-bit syscall architectural-effect descriptor during stores and scoring comparisons.
- Accept valid `ret imm16 0` candidates with total stack delta 8.
- Render text side-effect lists with comma-space separators.
- Reject contradictory, reserved-bit, displacement-bearing, base-mismatched, and wrong-index memory side-car records.
- Require maintained score values to agree across semantic-family and exact-pattern contracts.

- Reconcile the Patch 050 family-effect, exact-pattern, fixture, and score contracts in one Patch 051 architecture.
- Prevent fixture, exact-pattern, and semantic-family contracts from drifting through a dedicated reconciliation gate.

- Prevent Sprint 10 multi-command Make recipes from masking an intermediate validator failure by enabling fail-fast shell semantics.
- Reconcile the transfer fixture and direct validator with Patch 049 memory promotion and corrected scored/fallback counts.
- Isolate authenticated-overlay stale-manifest rejection with a benign same-size payload mutation so the regression reaches the internal manifest layer instead of failing earlier content policy.

- Remove two tracked generated Sprint 10 ELF fixtures and ignore generated multi-pop, transfer, stack-adjust, and memory fixture binaries.
- Close the public-content checker self-exclusion that allowed a tampered checker member to evade the content gate.
- Reconcile Patch 046 through Patch 049 chronology, taxonomy navigation, and fixed-arena wording in public documentation.

- Define the compact JSON object delimiters required by register-transfer rendering.
- Reject exact-pattern/terminator contradictions, bare `ret` records with controls or arbitrary stack deltas, and inconsistent stack-adjust records in common current-producer validation.
- Allow the Sprint 10 transfer disassembly oracle to consume a retained objdump transcript as documented by the validation interface.
- Prevent public source archives from passing content review when textual patch or diff members retain prohibited deleted or added workflow narration.

- Rewrite the UNC-path public-document regex so strict ShellCheck no longer
  reports `SC1003` while the functional rejection remains enforced.
- Remove the duplicated Patch 043 changelog block.

- Preserve a recognized decoder-gap result across the post-rename signal window.
- Prevent interrupted GNU-time/analyzer measurements from leaving child process groups alive.
- Normalize reviewed GNU objdump prefix and near-return variants and stop canonical sequences at prefixed control transfers.
- Reject contradictory local ZIP names, flags, extras, malformed ZIP64 values, zero-width UID/GID metadata, invalid NTFS metadata, and duplicate recognized extra fields.
- Remove transfer-artifact basenames from tracked public-boundary smoke fixtures and detect broader copy, case, and platform-specific path variants.

- Prevent inter-target mutation from making campaign manifests certify bytes
  different from those actually analyzed.
- Restore or preserve a complete recognized decoder-gap result across `SIGINT`,
  `SIGTERM`, and ordinary publication failures.
- Parse prefixed return instructions and stop canonical predecessor walks at
  invalid-byte and control-transfer barriers.
- Reject timestamped transfer-artifact names from public documentation
  and correct strict shell lint in the archive-check wrapper.

- Reject unsafe or non-public ZIP members under zero-root, one-root, and
  arbitrary archive layouts, including version-control metadata, non-source
  workspace state, environment files, secrets, symlinks, case collisions,
  generated outputs, and nested archives.
- Prevent decoder-gap evidence regeneration from deleting an unrelated existing
  directory by requiring the tool's own manifest before replacement.

- Correct pre-existing System V stack alignment across identified nested-call
  frames in JSON/text reporting, numeric formatting, arena mapping, and output
  wrappers.
- Reconcile formal schema rules with the semantic validator for current
  completeness, mitigation, limitation, and provenance state.
- Reject primitive-coverage summaries that disagree with emitted semantic
  classes or controlled-register facts.

- Remove ambiguity between `gadgets` and `analyze` JSON producers by adding explicit command identity without duplicating the report implementation.
- Make successful report completeness explicit instead of requiring consumers to infer it from candidate counts and capacity.

- Add the missing benchmark-integrity non-finite RSS fixtures: `nan-rss.tsv`, `inf-rss.tsv`, and `neg-inf-rss.tsv`.
- Clean strict shell-helper lint for patch-bundle unsafe-path checks and intentional literal Markdown-backtick planning checks.
- Align Sprint 8 closeout planning and validation records with the accepted Patch 039 baseline.
- Reject non-finite benchmark summary values such as `nan`, `inf`, and `-inf`.
- Preserve JSON validity and byte fidelity for high-bit and control bytes in target paths and section labels.
- Reject benchmark smoke runs with non-positive `RUNS`, invalid `MAX_DEPTH`, nonnumeric timing/RSS fields, or negative timing/RSS values.
- Record dereferenced target sizes for benchmarked symlink paths.
- Reject JSON reports whose `primitive_coverage.registers` omits registers present in gadget control lists.
- Preserve missing-tool install hints when `PATH` is badly damaged.
- Reject `.env` and `.env.*` files in patch-bundle hygiene checks, except for a future `.env.example` sample.
- Prevent newline-bearing section names from splitting executable-region and gadget candidate text lines.
- Prevent overlapping non-executable section headers from labeling executable gadget offsets.
- Preserve the half-open range interpretation for zero-length dynamic string-table evidence at a load endpoint.
- Promote the zero-sized dynamic string-table and over-cap string-table review cases into the permanent mitigation oracle.
- Close the Patch 030 dynamic malformed oracle gap by covering `gadgets` text and JSON callers as well as `mitigations` and integrated `analyze`.
- Classify the Patch 028 Docker metadata-path failure as environment-specific only after the complete Docker validation matrix passed in a qualified environment.
- Correct the mitigation oracle zero-executable-region expectation to match the stable text reporter line, `none discovered from PT_LOAD + PF_X`.
- Reject malformed ELF64 files that previously used a nonzero but invalid section-header entry stride.
- Verify candidate-record exhaustion returns a stable unsupported-feature error instead of silently truncating analysis.


## [0.1.0-dev] - Sprint 06 Patch 023

### Added

- Repeatable checkpoint demonstration through `make checkpoint-demo`.
- `make bench-summary-latest`, `make checkpoint-tag-help`, and `make public-docs-check`.
- Composable body-only text reporter wrappers in `src/report_context.asm`.
- Checkpoint demo, benchmark interpretation, ADR, validation, retrospective, and paper-alignment documentation.

### Changed

- `analyze` text output emits one version and target banner while preserving all report sections.
- Sprint 6 planning and validation documentation reflects the integrated checkpoint.

## [0.1.0-dev] - Sprint 06 Patch 022

### Added
- Added `analyze [--format text|json] [--max-depth N] <file>` as the first integrated checkpoint command.
- Added `src/analyze.asm` to orchestrate ELF validation, mitigation analysis, executable region discovery, gadget scanning, exact pattern matching, semantic classification, scoring, and reporting through shared internal records.
- Added `make analyze-smoke` and expanded system-binary smoke validation to cover text and JSON `analyze` output.
- Added ADR 0010 and Sprint 6 Patch 022 validation documentation.

### Changed
- Updated help text, CLI contract, architecture diagrams, roadmap, validation plan, onboarding, and benchmark methodology for the integrated checkpoint command.
- Clarified that `analyze` is a static defensive triage report, not an exploitability verdict.


## [0.1.0-dev] - Sprint 05 Patch 021

### Added
- Added `tools/install-ropr-user.sh` to provide a clearer ropr installation path when Cargo is too old.
- Added `docs/sprints/sprint-05-patch-021-validation.md` and `docs/sprints/sprint-05-retro.md`.

### Changed
- Added `zip` and `unzip` to the Docker development image so Docker validation matches the local development dependency contract.
- Made `docker-test` rebuild the development image before running container validation.
- Scoped `REQUIRE_BASELINES=1` enforcement to baseline-aware checks instead of normal development checks.
- Updated onboarding and environment documentation to separate required development dependencies from optional Rust/ropr baseline setup.

### Fixed
- Fixed Docker validation failure caused by missing archive tools inside the container image.
- Fixed false `REQUIRE_BASELINES=1` failures when the variable propagated into `dev-tools-check`.
- Replaced the brittle `cargo install ropr` onboarding path with a rustup-aware helper and explicit remediation guidance.

## [0.1.0-dev] - Development history through Sprint 05 Patch 020

### Added

- Added Sprint 5 Patch 020 developer onboarding and dependency validation.
- Added `tools/check-dev-tools.sh` plus Make targets for build, sample, development, baseline, and full toolchain checks.
- Added explicit Ubuntu dependency bootstrap and optional baseline-tool installation guidance.
- Added `docs/onboarding.md` with a complete first-run checklist and Make target tour.
- Broadened baseline smoke defaults to include `/bin/sh`, `/usr/bin/env`, and `/usr/bin/printf` in addition to the controlled fixture, `/bin/ls`, and `/bin/cat`.
- Added Sprint 5 Patch 019 baseline comparison smoke harness.
- Added `benchmarks/scripts/bench-baselines-smoke.sh` and `make bench-baselines-smoke` for x64lens plus optional ROPgadget, Ropper, and ropr timing rows.
- Added a standard-library benchmark summarizer through `benchmarks/scripts/summarize.py` and `make bench-summary`.
- Added ADR 0007 for baseline comparison harness design.
- Sanitized public validation transcripts to avoid personal hostnames and local home-directory paths.
- Added Sprint 5 Patch 018 validation hardening.
- Added `tools/validate-json-report.py` for reusable JSON report contract validation.
- Added `tools/system-binary-smoke.sh` and `make system-smoke` for installed ELF64 x86_64 binary smoke coverage.
- Added `make validation-smoke` as a local pre-commit validation aggregate.
- Added `make docker-available-check` to distinguish Docker environment availability from implementation failures.
- Added `tools/check-patch-bundle-hygiene.sh` and `make patch-bundle-hygiene` to detect generated or local-only files in patch ZIPs.
- Strengthened `make json-smoke` to validate both supported `--format`/`--max-depth` flag orders with the reusable JSON validator.
- Added Sprint 5 Patch 017 scoring and JSON implementation candidate.
- Implemented `x64lens_scoring_apply` in `src/scoring.asm` for first-pass heuristic scores over classified exact suffix patterns.
- Added `Scored candidate count` and per-candidate `score` fields to gadget text output.
- Added `gadgets --format json` with schema-versioned JSON generated from internal records.
- Added JSON `counts`, `primitive_coverage`, per-gadget score fields, explicit stack-delta uncertainty, and `limitations`.
- Added `GADGET_SUMMARY_SCORED_COUNT` to the gadget summary model.
- Expanded the controlled gadget fixture to exercise `pop rcx; ret`, `pop r8; ret`, `pop r9; ret`, and `pop rsp; ret`.
- Added `make json-smoke` and JSON parsing checks in `tests/run-tests.sh`.
- Extended scanner smoke benchmark TSV output with `scored_candidate_count`.
- Added a public repository voice rule to documentation and output contracts.
- Closed Sprint 4 Patch 015 validation with local WSL2 and Docker evidence for the first semantic classifier pass.
- Added `x64lens_classifier_apply_exact` in `src/classifier.asm` to map supported exact suffix pattern IDs into conservative semantic primitive facts.
- Added semantic class, controlled-register bitmap, stack-delta, and side-effect population for supported exact suffix patterns.
- Added semantic summary counts, unknown candidate counts, per-class primitive counts, and register coverage to gadget text output.
- Added `make semantic-smoke` and expanded fixture validation to check semantic classifier facts.
- Extended scanner smoke TSV output with semantic primitive and unknown-candidate counts.
- Added reviewer-readiness design notes under `docs/design/`.
- Added ADR 0005 for reviewer readiness and future seams.
- Added NASM rationale documentation without claiming unsupported performance superiority.
- Added decoder roadmap documentation and the limits of exact suffix pattern matching.
- Added raw, exact, semantic, and scored metric boundary documentation.
- Added parser safety and mutation smoke/fuzzing plan for later hardening.
- Added contributor maintainability guidance for NASM-heavy development.
- Refined Sprint 4 through Sprint 12 planning around semantic classification, JSON, malformed-input safety, baseline comparison, and publication readiness.
- Restored executable permission intent for shell helper scripts and added a script permission check target.
- Closed Sprint 3 with validated raw gadget scanning, scanner smoke benchmarking, arena-backed candidate storage, exact suffix pattern matching, and updated Sprint 3 retrospective/context documentation.
- Added extended Sprint 7 through Sprint 12 roadmap and candidate sprint plans for mitigation hardening, primitive expansion, compiler/hardening corpus, research benchmarks, integrated analysis, and publication/release preparation.
- Added Sprint 3 Phase D exact pattern matching: `patterns.asm` now tags raw candidates with exact byte-template pattern IDs such as `pop rdi; ret`, `leave; ret`, `syscall; ret`, and `ret imm16` without performing semantic classification.
- Updated `gadgets` text output, fixture validation, scanner smoke benchmarking, and regression tests to preserve exact pattern counts.
- Added Sprint 3 Phase C arena allocator support: `src/arena.asm`, arena-backed raw gadget candidate storage for `x64lens gadgets`, and `make arena-smoke`.
- Updated scanner capacity handling so `scanner.asm` consumes caller-supplied candidate capacity from `gadget_summary`.
- Added Sprint 3 Phase B scanner validation and benchmark smoke tooling: `make validate-gadget-fixture`, `make bench-scanner-smoke`, `tools/validate-gadget-fixture.sh`, and `benchmarks/scripts/bench-scanner-smoke.sh`.
- Strengthened raw gadget scanner regression checks with exact expected fixture counts for `tests/bin/gadgets`.
- Documented that `NX stack: unknown` and `RELRO: not found` are expected for the static `tests/bin/gadgets` fixture because it is a scanner fixture, not a mitigation fixture.
- Began Sprint 3 with the `gadgets [--max-depth N] <file>` command path, fixed-capacity gadget candidate records, raw executable-region scanning, `ret` and `ret imm16` detection, bounded backward byte windows, and raw candidate text reporting.
- Added scanner regression coverage against `tests/bin/gadgets`, including custom `--max-depth` validation and invalid-input coverage through the `gadgets` command.
- Added `print_hex8` for deterministic raw byte-window rendering.
- Completed and validated the Sprint 2 `mitigations <file>` command path with program-header parsing, executable PT_LOAD + PF_X region discovery, PIE reporting, NX stack reporting, RWX segment reporting, PT_GNU_RELRO baseline RELRO reporting, and PT_DYNAMIC dynamic-linking reporting.
- Added `src/phdr.asm` program-header analysis and `src/regions.asm` executable-region record storage.
- Added Sprint 2 tests for PIE/non-PIE behavior, NX stack enabled/disabled behavior, malformed program-header rejection, and mitigation output smoke checks.
- Added a `minimal_execstack` toy binary variant to validate executable-stack detection.
- Implemented the Sprint 1 `info <file>` path with read-only file mapping, ELF64 x86_64 validation, basic ELF metadata reporting, and invalid-input regression tests.
- Added `src/info.asm` as the command orchestrator that preserves boundaries between file mapping, ELF validation, reporting, and cleanup.
- Added a mapped-file internal record layout in `include/structs.inc`.
- Added stable STDERR diagnostics for file, ELF identity, malformed ELF, unsupported, and bounds-related failures.
- Added fixed-width `print_hex64` formatting for deterministic metadata output.
- Added `make docker-test` for reproducible container smoke testing.
- Added `make ownership-check` and `make fix-perms` for diagnosing and repairing local generated artifact ownership issues.
- Added `make normalize-perms` for local permission hygiene after extracting patch bundles.
- Documented Sprint 1 closeout with native and container validation output.

### Changed

- `make test`, JSON smoke, system smoke, and benchmark targets now perform clearer prerequisite checks before running.
- README startup instructions now distinguish required build tools, required validation tools, and optional baseline tools.
- Public documentation and repository structure now exclude non-source workspace state.
- Makefile scaffold checks now validate only public repository structure.
- Sprint planning now treats Sprint 5 as scoring, JSON, benchmark comparison, and classifier fixture hardening rather than additional raw scanner breadth.

### Fixed

- Prevented Docker bind-mounted development sessions from creating root-owned build artifacts by running Docker shells/tests with the caller's UID/GID.
- Added `.dockerignore` to keep non-source workspace state, generated artifacts, and version-control metadata out of Docker build contexts.
- Added troubleshooting documentation for `make clean` permission failures caused by root-owned generated files.
- Consolidated duplicate `Unreleased` changelog sections introduced during rapid sprint patching.

## [0.1.0-dev] - Initial scaffold history

### Added

- Repository skeleton for an assembly-first ELF64 analysis research prototype.
- NASM build contract using `make`.
- CLI command contract for `info`, `mitigations`, `gadgets`, `analyze`, `bench`, and `version`.
- Documentation contracts for development, research, output, benchmark, and release discipline.
- Initial research questions RQ1, RQ2, and RQ3.
- Initial JSON schema draft.
- Sprint planning documents.
- Development environment plan for WSL2, Docker/devcontainer, remote development, and publication benchmarks.
- Visualization plan with Mermaid and Graphviz source diagrams.
- Human-readable comments across current assembly, config, script, and workflow scaffolding.
- `.devcontainer/devcontainer.json` for reproducible development environments.

### Completed

- Sprint 1: repository foundation, build system, Docker workflow, CLI skeleton, file mapping, ELF64 validation, and basic `info <file>` reporting.
- Sprint 2: program-header parsing, executable-region mapping, baseline mitigation reporting, readelf comparison workflow, and local/Docker validation.
- Sprint 3: raw scanner, scanner smoke benchmark, arena-backed candidate storage, and exact suffix pattern matching.
- Sprint 4: first-pass semantic classifier, semantic summary counts, controlled-register coverage, stack deltas, semantic smoke validation, and Sprint 4 closeout documentation.
