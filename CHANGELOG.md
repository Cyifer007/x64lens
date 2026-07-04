# Changelog

All notable public changes to x64lens are documented in this file.

The project follows semantic versioning once the first public release is cut.

## Unreleased

### Added

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
- Exclude private local agent workspaces from permission normalization, Docker build context filtering, Git ignore gaps, and patch-bundle hygiene.
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

- Prevent newline-bearing section names from splitting executable-region and gadget candidate text lines.
- Prevent overlapping non-executable section headers from labeling executable gadget offsets.
- Preserve the half-open range interpretation for zero-length dynamic string-table evidence at a load endpoint.
- Promote the zero-sized dynamic string-table and over-cap string-table review cases into the permanent mitigation oracle.
- Close the Patch 030 dynamic malformed oracle gap by covering `gadgets` text and JSON callers as well as `mitigations` and integrated `analyze`.
- Classify the Patch 028 Docker Buildx metadata failure as an environment defect after Docker validation passed outside the restricted filesystem sandbox.
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
- Documented Sprint 1 closeout with actual WSL2 and Docker validation output.

### Changed

- `make test`, JSON smoke, system smoke, and benchmark targets now perform clearer prerequisite checks before running.
- README startup instructions now distinguish required build tools, required validation tools, and optional baseline tools.
- Public documentation is now separated from local-only private project context.
- Local-only planning/context files are expected under `.local/project-context/` and excluded by `.gitignore`.
- Makefile scaffold checks now validate only public repository structure.
- Sprint planning now treats Sprint 5 as scoring, JSON, benchmark comparison, and classifier fixture hardening rather than additional raw scanner breadth.

### Fixed

- Prevented Docker bind-mounted development sessions from creating root-owned build artifacts by running Docker shells/tests with the caller's UID/GID.
- Added `.dockerignore` to keep local context, generated artifacts, `.git/`, and private/course files out of Docker build contexts.
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
