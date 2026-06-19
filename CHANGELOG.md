# Changelog

All notable public changes to x64lens will be documented in this file.

The project follows semantic versioning once the first public release is cut.

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


## Unreleased

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

## [0.1.0-dev] - Unreleased

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
