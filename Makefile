# x64lens build contract
#
# Purpose:
#   Build the NASM assembly sources into ELF64 object files and link them
#   into the `build/x64lens` executable. This Makefile is intentionally
#   boring and explicit because it is part of the reproducibility story for
#   public research, publication artifacts, and future enterprise adoption.
#
# Design notes:
#   - NASM emits ELF64 objects.
#   - GNU ld links directly, without libc.
#   - gcc builds controlled test fixtures; GCC and Clang build the ignored
#     provisional diagnostic corpus through an external standard-library tool.
#   - `make scaffold-check` verifies repository structure before deeper work.

PROJECT      := x64lens
VERSION      := 0.1.0-dev
SCHEMA       := 0.2.0
DOCKER_IMAGE ?= x64lens-dev
DOCKER       ?= docker
DOCKER_IMAGE_AUTHORITY ?= $(abspath .local/docker-image-authority.json)
BUILD_DIR    := build
SRC_DIR      := src
INC_DIR      := include
TARGET       := $(BUILD_DIR)/$(PROJECT)
DEMO_TARGET  ?= ./tests/bin/gadgets
MALFORMED_SEED ?= ./tests/bin/minimal_nopie
MALFORMED_TIMEOUT ?= 2
MALFORMED_RESULTS_DIR ?= ./tests/results/malformed
MITIGATION_MATRIX_RESULTS_DIR ?= ./tests/results/mitigation-matrix
SECTION_LABEL_RESULTS_DIR ?= ./tests/results/section-label
READELF_COMPARISON_RESULTS_DIR ?= ./tests/results/readelf-comparison
OPTIONAL_TOOL_COMPARISON_RESULTS_DIR ?= ./tests/results/optional-tool-comparison
BENCHMARK_INTEGRITY_RESULTS_DIR ?= ./tests/results/benchmark-integrity
DECODER_GAP_RESULTS_DIR ?= ./tests/results/decoder-gap
DIAGNOSTIC_RESULTS_DIR ?= ./benchmarks/results/diagnostic
DIAGNOSTIC_SPEC ?= ./benchmarks/specs/sprint11-reference-diagnostic.json
DIAGNOSTIC_CAMPAIGN_ID ?=
S11_P060_PLAN ?= ./benchmarks/task-definitions/sprint11-p060-campaign-plan.json
S11_P060_TASK_AUTHORITY ?= ./benchmarks/task-definitions/sprint11-diagnostic-tasks.json
S11_P060_RESULTS_ROOT ?= ./benchmarks/results/diagnostic
S11_P060_CAMPAIGN_ID ?=
PROVISIONAL_CORPUS_ROOT ?= ./benchmarks/corpus/generated
PROVISIONAL_CORPUS_SPEC ?= ./benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json
PROVISIONAL_CORPUS_ID ?= s11-p056-provisional-v1
PROVISIONAL_CORPUS_PATH ?= $(PROVISIONAL_CORPUS_ROOT)/$(PROVISIONAL_CORPUS_ID)
PUBLIC_BUNDLE ?=
PUBLIC_BUNDLE_SHA256 ?=
INTERNAL_TEST_BUILD_DIR := $(BUILD_DIR)/tests
MEMORY_EFFECT_RECONCILIATION_OBJ := $(INTERNAL_TEST_BUILD_DIR)/memory-effect-reconciliation.o
MEMORY_EFFECT_RECONCILIATION_BIN := $(INTERNAL_TEST_BUILD_DIR)/memory-effect-reconciliation
CANDIDATE_MAPPING_RECONCILIATION_OBJ := $(INTERNAL_TEST_BUILD_DIR)/candidate-mapping-reconciliation.o
CANDIDATE_MAPPING_RECONCILIATION_BIN := $(INTERNAL_TEST_BUILD_DIR)/candidate-mapping-reconciliation
BINARY_ROLE_RECONCILIATION_OBJ := $(INTERNAL_TEST_BUILD_DIR)/binary-role-reconciliation.o
BINARY_ROLE_RECONCILIATION_BIN := $(INTERNAL_TEST_BUILD_DIR)/binary-role-reconciliation
GNU_PROPERTY_RECONCILIATION_OBJ := $(INTERNAL_TEST_BUILD_DIR)/gnu-property-reconciliation.o
GNU_PROPERTY_RECONCILIATION_BIN := $(INTERNAL_TEST_BUILD_DIR)/gnu-property-reconciliation
ROLE_PROPERTY_LAYOUT_AUTHORITY_OBJ := $(INTERNAL_TEST_BUILD_DIR)/role-property-layout-authority.o
ROLE_PROPERTY_LAYOUT_RECONCILIATION_OBJ := $(INTERNAL_TEST_BUILD_DIR)/role-property-layout-reconciliation.o
ROLE_PROPERTY_LAYOUT_RECONCILIATION_BIN := $(INTERNAL_TEST_BUILD_DIR)/role-property-layout-reconciliation
DYNAMIC_METADATA_LAYOUT_AUTHORITY_OBJ := $(INTERNAL_TEST_BUILD_DIR)/dynamic-metadata-layout-authority.o
DYNAMIC_METADATA_LAYOUT_RECONCILIATION_OBJ := $(INTERNAL_TEST_BUILD_DIR)/dynamic-metadata-layout-reconciliation.o
DYNAMIC_METADATA_LAYOUT_RECONCILIATION_BIN := $(INTERNAL_TEST_BUILD_DIR)/dynamic-metadata-layout-reconciliation
ROLE_PROPERTY_FACT_PROBE_OBJ := $(INTERNAL_TEST_BUILD_DIR)/role-property-fact-probe.o
ROLE_PROPERTY_FACT_PROBE_BIN := $(INTERNAL_TEST_BUILD_DIR)/role-property-fact-probe
DYNAMIC_METADATA_FACT_PROBE_OBJ := $(INTERNAL_TEST_BUILD_DIR)/dynamic-metadata-fact-probe.o
DYNAMIC_METADATA_FACT_PROBE_BIN := $(INTERNAL_TEST_BUILD_DIR)/dynamic-metadata-fact-probe
REGISTER_ROLE_FACET_RECONCILIATION_OBJ := $(INTERNAL_TEST_BUILD_DIR)/register-role-facet-reconciliation.o
REGISTER_ROLE_FACET_RECONCILIATION_BIN := $(INTERNAL_TEST_BUILD_DIR)/register-role-facet-reconciliation
TEXTREL_AUTHORITY := ./benchmarks/task-definitions/sprint12-textrel-private-evidence-v1.json
SEARCH_PATH_AUTHORITY := ./benchmarks/task-definitions/sprint12-search-path-private-evidence-v1.json
ROLE_PROPERTY_HELDOUT_AUTHORITY := ./benchmarks/task-definitions/sprint12-role-property-heldout-v1.json
ROLE_PROPERTY_READELF_AUTHORITY := ./benchmarks/task-definitions/sprint12-role-property-readelf-v1.json
ROLE_PROPERTY_BATCH_AUTHORITY := ./benchmarks/task-definitions/sprint12-batch-transaction-pilot-v3.json
ROLE_PROPERTY_EXTERNAL_NATURAL_AUTHORITY := ./benchmarks/task-definitions/sprint12-external-natural-acquisition-v1.json
ROLE_PROPERTY_PUBLIC_POLICY_AUTHORITY := ./benchmarks/task-definitions/sprint12-role-property-public-policy-v1.json
MITIGATION_COMPETITIVE_GAP_AUTHORITY := ./benchmarks/task-definitions/sprint12-mitigation-competitive-gap-v1.json
ROLE_PROPERTY_EXTERNAL_NATURAL_RESULT_DIR ?=
ROLE_PROPERTY_PARITY_RESULT_DIR ?=
DYNAMIC_METADATA_PARITY_RESULT_DIR ?=
S13_PRODUCER_RESULT_DIR ?=
S13_COORDINATE_RESULT_DIR ?=
ROLE_PROPERTY_PUBLIC_SCHEMA := ./schemas/x64lens-report.schema.json

NASM         ?= nasm
LD           ?= ld
CC           ?= gcc
READELF      ?= readelf
DPKG_QUERY   ?= dpkg-query

ASMFLAGS     := -f elf64 -g -F dwarf -Werror=number-overflow -I$(INC_DIR)/
LDFLAGS      :=

ASM_SRCS     := $(wildcard $(SRC_DIR)/*.asm)
OBJS         := $(patsubst $(SRC_DIR)/%.asm,$(BUILD_DIR)/%.o,$(ASM_SRCS))

.DEFAULT_GOAL := all

.PHONY: sprint13-producer-authority-smoke sprint13-positive-coordinate-anchor-smoke patch081-corrective-regression-smoke sprint13-p082-acceptance-smoke

.PHONY: help all clean test samples bench-smoke bench-scanner-smoke bench-baselines-smoke bench-diagnostic-smoke bench-sprint11-provisional-campaign bench-summary bench-summary-latest checkpoint-demo checkpoint-tag-help public-docs-check public-artifact-content-smoke public-bundle-content-check public-overlay-verify public-overlay-verification-smoke planning-docs-check research-stage-gates-smoke research-roadmap-consistency-smoke sprint10-closeout-smoke sprint11-closeout-smoke sprint12-closeout-smoke sprint12-phdr-validity-smoke sprint12-overlap-provenance-smoke sprint12-overlap-decision-smoke sprint12-binary-role-smoke sprint12-gnu-property-oracle-smoke sprint12-gnu-property-smoke sprint12-role-property-layout-smoke sprint12-dynamic-metadata-layout-smoke sprint12-role-property-metamorphic-smoke sprint12-role-property-heldout-smoke sprint12-role-property-readelf-smoke sprint12-batch-transaction-smoke patch070-corrective-regression-smoke patch069-corrective-regression-smoke patch068-corrective-regression-smoke patch067-corrective-regression-smoke patch066-corrective-regression-smoke patch065-corrective-regression-smoke patch064-corrective-regression-smoke patch063-corrective-regression-smoke patch062-corrective-regression-smoke patch061-corrective-regression-smoke patch054-corrective-regression-smoke patch059-corrective-regression-smoke diagnostic-runner-smoke diagnostic-transaction-smoke runtime-closure-venv-smoke sprint11-below-floor-policy-smoke diagnostic-task-definitions-smoke baseline-output-adapter-smoke sprint11-measurement-plane-smoke sprint11-campaign-plan-smoke sprint11-p060-campaign-smoke sprint11-diagnostic-reference-smoke provisional-corpus-smoke provisional-corpus-ready provisional-corpus-repair-modes clean-provisional-corpus checksum-manifest-path-smoke scanner-smoke validate-gadget-fixture arena-smoke pattern-smoke semantic-smoke json-smoke schema-compat-smoke analyze-smoke system-smoke capacity-smoke malformed-smoke fuzz-mutated-elf-smoke mitigation-matrix-smoke section-label-smoke readelf-comparison-smoke optional-tool-comparison-smoke benchmark-integrity-smoke patch-bundle-hygiene-smoke sprint10-primitive-smoke sprint10-register-transfer-smoke sprint10-stack-adjust-smoke sprint10-memory-smoke sprint10-family-coverage-smoke sprint10-architectural-effects-smoke sprint10-fixture-gate-smoke sprint10-contract-reconciliation-smoke sprint10-score-policy-smoke memory-effect-reconciliation-smoke shellcheck-contract-smoke json-effect-consistency-smoke public-docs-hygiene-smoke decoder-gap-hardening-smoke decoder-gap-smoke decoder-gap-campaign shellcheck-smoke docker-context-hygiene-smoke native-docker-json-parity-smoke validation-smoke sprint-closeout-smoke clean-results check-tools build-tools-check sample-tools-check dev-tools-check diagnostic-tools-check corpus-tools-check baseline-tools-check analysis-tools-check full-tools-check doctor install-dev-deps-ubuntu install-baseline-tools-user install-rustup-user install-ropr-user scaffold-check script-perms-check patch-bundle-hygiene print-vars docker-available-check docker-build docker-shell docker-test docker-validation-smoke ownership-check fix-perms normalize-perms diagrams-check sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-p072-acceptance-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke sprint12-p073-acceptance-smoke sprint12-p074-acceptance-smoke sprint12-p075-acceptance-smoke sprint12-dynamic-metadata-layout-smoke sprint12-textrel-readelf-oracle sprint12-textrel-smoke sprint12-continuation-smoke patch075-corrective-regression-smoke patch074-corrective-regression-smoke patch073-corrective-regression-smoke patch072-corrective-regression-smoke patch071-corrective-regression-smoke sprint12-search-path-readelf-oracle sprint12-search-path-smoke sprint12-dynamic-metadata-environment-parity-smoke sprint12-p076-acceptance-smoke sprint12-p077-acceptance-smoke patch076-corrective-regression-smoke patch077-corrective-regression-smoke patch078-corrective-regression-smoke sprint13-register-role-decision-smoke sprint13-register-role-task-value-smoke sprint13-p078-acceptance-smoke sprint13-p079-acceptance-smoke sprint13-p080-acceptance-smoke sprint13-p081-acceptance-smoke sprint13-role-facet-smoke sprint13-role-policy-smoke sprint13-ordered-two-pop-role-task-value-smoke sprint13-score-null-authority-smoke patch079-corrective-regression-smoke patch080-corrective-regression-smoke docker-source-custody-smoke docker-image-authority-smoke

help:
	@echo "x64lens development targets"
	@echo "  make                     Build x64lens"
	@echo "  make samples             Build controlled test fixtures"
	@echo "  make test                Run the core regression suite"
	@echo "  make validation-smoke    Run the complete native validation aggregate"
	@echo "  make sprint-closeout-smoke  Require strict shell lint, then run validation-smoke"
	@echo "  make mitigation-matrix-smoke  Run the deterministic mitigation oracle"
	@echo "  make sprint12-phdr-validity-smoke  Validate PHDR policy and extended numbering"
	@echo "  make sprint12-overlap-provenance-smoke  Validate original-PHDR and dense contributor provenance"
	@echo "  make sprint12-overlap-decision-smoke  Validate the measured normalization deferral authority"
	@echo "  make sprint12-binary-role-smoke  Validate the private PIE/DSO role-evidence lattice"
	@echo "  make sprint12-gnu-property-oracle-smoke  Validate the independent GNU-property byte oracle"
	@echo "  make sprint12-gnu-property-smoke  Validate bounded private x86 IBT/SHSTK GNU-property facts"
	@echo "  make sprint12-role-property-layout-smoke  Reconcile the private fact-probe NASM/C layout ABI"
	@echo "  make sprint12-dynamic-metadata-layout-smoke  Reconcile the private dynamic-metadata NASM/C layout ABI"
	@echo "  make sprint12-textrel-readelf-oracle  Validate the independent DT_TEXTREL/DF_TEXTREL fixture oracle"
	@echo "  make sprint12-textrel-smoke  Validate the private text-relocation side-car against analyzer/probe/readelf"
	@echo "  make sprint12-search-path-readelf-oracle  Validate distinct RPATH/RUNPATH fixture dispositions"
	@echo "  make sprint12-search-path-smoke  Validate exact private RPATH/RUNPATH carrier/value evidence"
	@echo "  make sprint12-dynamic-metadata-environment-parity-smoke  Prove complete native/container dynamic-sidecar parity"
	@echo "  make patch076-corrective-regression-smoke  Regress Patch 076 application, recovery, custody, oracle, parity, and permission defects"
	@echo "  make sprint12-p077-acceptance-smoke  Run the final Sprint 12 reconciliation and closeout-candidate aggregate"
	@echo "  make sprint12-role-property-metamorphic-smoke  Run the 28-object private role/property preflight"
	@echo "  make sprint12-role-property-heldout-smoke  Run the authenticated 96-object private fact confirmation"
	@echo "  make sprint12-role-property-readelf-smoke  Reconcile eligible private facts against retained readelf output"
	@echo "  make patch073-corrective-regression-smoke  Regress Patch 073 custody, parity, freeze, permission, and authority defects"
	@echo "  make patch072-corrective-regression-smoke  Regress Patch 072 cleanup, freeze, custody, parity-isolation, and policy defects"
	@echo "  make patch071-corrective-regression-smoke  Regress remaining Patch 071 cleanup, process, authority, and custody defects"
	@echo "  make sprint12-external-natural-acquisition-smoke  Acquire outcome-blind installed-package role/property evidence"
	@echo "  make sprint12-role-property-environment-parity-smoke  Prove retained, write-isolated native/container private-fact parity"
	@echo "  make sprint12-role-property-public-policy-smoke  Execute the non-reinterpretive role/property policy gate"
	@echo "  make sprint12-closeout-smoke  Reconcile Sprint 12 closeout and the Sprint 13 handoff"
	@echo "  make sprint13-register-role-decision-smoke  Validate all 16 exact-pop ABI role decisions"
	@echo "  make sprint13-register-role-task-value-smoke  Validate the corrected 60-query private task-value gate"
	@echo "  make sprint13-role-facet-smoke  Execute the private 8-byte role-sidecar ABI authority"
	@echo "  make sprint13-role-policy-smoke  Validate the nine-cell private/public/score LC-08B decision"
	@echo "  make sprint13-ordered-two-pop-role-task-value-smoke  Validate the 30-pair zero-gain tuple pilot"
	@echo "  make sprint13-score-null-authority-smoke  Mutation-test all 25 score/null cells"
	@echo "  make patch080-corrective-regression-smoke  Regress Patch 080 transaction, Git-less, Docker provenance, and checksum findings"
	@echo "  make patch079-corrective-regression-smoke  Regress Patch 079 transaction, Git-less, Docker, parity, and oracle findings"
	@echo "  make sprint13-p080-acceptance-smoke  Run complete Patch 080 native, Docker, parity, policy, and strict-lint acceptance"
	@echo "  make sprint13-p081-acceptance-smoke  Run complete Patch 081 correction, tuple/score authorities, native, Docker, parity, and strict-lint acceptance"
	@echo "  make sprint12-p074-acceptance-smoke  Run the complete Sprint 12 closeout acceptance aggregate"
	@echo "  make sprint12-mitigation-competitive-gap-smoke  Validate the bounded mitigation capability gap and next tranche"
	@echo "  make sprint12-p073-acceptance-smoke  Run Patch 073 native, acquisition, parity, and policy gates"
	@echo "  make sprint12-p072-acceptance-smoke  Run Patch 072 native, external-natural, and parity gates"
	@echo "  make sprint12-batch-transaction-smoke  Validate whole-batch transaction and signal semantics"
	@echo "  make patch070-corrective-regression-smoke  Regress Patch 070 cleanup, batch-oracle, output-cap, and custody findings"
	@echo "  make patch069-corrective-regression-smoke  Regress Patch 069 corpus, authority, comparator, package, and Make findings"
	@echo "  make patch067-corrective-regression-smoke  Regress Patch 067 corpus, package, Make, and ABI findings"
	@echo "  make patch066-corrective-regression-smoke  Regress Patch 066 corpus, oracle, and ABI findings"
	@echo "  make patch065-corrective-regression-smoke  Regress Patch 065 parser, corpus, harness, and oracle findings"
	@echo "  make patch064-corrective-regression-smoke  Regress Patch 064 parser, corpus, permission, and delivery findings"
	@echo "  make patch063-corrective-regression-smoke  Regress Patch 063 corpus and fixture findings"
	@echo "  make patch062-corrective-regression-smoke  Regress Patch 062 parser, transaction, and Make findings"
	@echo "  make patch061-corrective-regression-smoke  Regress Patch 061 integrity findings"
	@echo "  make section-label-smoke  Run section-label annotation hardening probes"
	@echo "  make readelf-comparison-smoke  Compare metadata and loader facts against readelf"
	@echo "  make optional-tool-comparison-smoke  Run optional checksec/rabin2 comparison helpers"
	@echo "  make benchmark-integrity-smoke  Validate benchmark TSV input hygiene"
	@echo "  make diagnostic-tools-check  Validate only build, sample, and standard-library runner tools"
	@echo "  make diagnostic-runner-smoke  Validate high-resolution runner provenance, timing, and failure retention"
	@echo "  make diagnostic-task-definitions-smoke  Validate truthful Sprint 11 task scopes"
	@echo "  make baseline-output-adapter-smoke  Validate bounded task-normalized ROPgadget/Ropper/ropr adapters"
	@echo "  make diagnostic-transaction-smoke  Validate runner stage ownership, future paths, and interruption cleanup"
	@echo "  make sprint11-measurement-plane-smoke  Validate matched relations, runtime closure, and address calibration"
	@echo "  make sprint11-campaign-plan-smoke  Validate the 30-condition provisional diagnostic plan"
	@echo "  make sprint11-p060-campaign-smoke  Execute the complete controlled 30-condition campaign plane"
	@echo "  make patch059-corrective-regression-smoke  Re-run all Patch 059 evidence-integrity corrections"
	@echo "  make bench-sprint11-provisional-campaign  Execute the available-tool Patch 060 diagnostic campaign"
	@echo "  make provisional-corpus-build  Build the ignored 24-target GCC/Clang diagnostic corpus"
	@echo "  make provisional-corpus-verify  Reauthenticate the generated provisional corpus"
	@echo "  make provisional-corpus-ready  Build a missing corpus or repair authenticated mode-only drift, then verify it"
	@echo "  make provisional-corpus-repair-modes  Repair mode-only drift in authenticated generated corpus evidence"
	@echo "  make provisional-corpus-smoke  Prove two-build reproducibility, integrity, and cleanup"
	@echo "  make clean-provisional-corpus  Remove only the generated Patch 056 corpus"
	@echo "  make sprint11-diagnostic-reference-smoke  Validate controlled diagnostic rows and command parity"
	@echo "  make patch054-corrective-regression-smoke  Reject Patch 054 checker false negatives"
	@echo "  make patch-bundle-hygiene-smoke  Reconcile local/central ZIP metadata and private paths"
	@echo "  make public-docs-hygiene-smoke  Reject private transfer names and host paths"
	@echo "  make public-artifact-content-smoke  Reject private text recoverable from distributed patches"
	@echo "  PUBLIC_BUNDLE=/path/to/public.zip make public-bundle-content-check"
	@echo "  PUBLIC_BUNDLE=/path/to/public.zip PUBLIC_BUNDLE_SHA256=<sha256> make public-overlay-verify"
	@echo "  make public-overlay-verification-smoke  Test authenticated overlay verification and self-tamper rejection"
	@echo "  make research-stage-gates-smoke  Validate diagnostic/freeze/release sequencing and capability gates"
	@echo "  make checksum-manifest-path-smoke  Verify checksum entries resolve from the manifest directory"
	@echo "  make decoder-gap-hardening-smoke  Test parser, child cleanup, snapshots, and rollback"
	@echo "  make decoder-gap-smoke  Validate controlled external decoder reconciliation"
	@echo "  make decoder-gap-campaign  Measure controlled and selected-system decoder gaps"
	@echo "  make schema-compat-smoke  Validate schema 0.1.0 compatibility and 0.2.0 invariants"
	@echo "  make sprint10-primitive-smoke  Validate ordered two-pop primitive facts and fallback"
	@echo "  make sprint10-register-transfer-smoke  Validate exact register-transfer facts and fallback"
	@echo "  make sprint10-stack-adjust-smoke  Validate exact positive aligned stack-adjust facts and fallback"
	@echo "  make sprint10-memory-smoke  Validate bounded qword memory read/write facts and fallback"
	@echo "  make sprint10-family-coverage-smoke  Validate the 11 semantic-family contracts"
	@echo "  make sprint10-architectural-effects-smoke  Validate one candidate for all 25 exact patterns"
	@echo "  make sprint10-fixture-gate-smoke  Prove fixture validation stops before later steps"
	@echo "  make sprint10-contract-reconciliation-smoke  Reconcile family, pattern, and fixture contracts"
	@echo "  make sprint10-score-policy-smoke  Reject numeric score-policy drift across both contract gates"
	@echo "  make memory-effect-reconciliation-smoke  Reject contradictory dense memory side-car records"
	@echo "  make shellcheck-contract-smoke  Validate strict/advisory missing-ShellCheck behavior"
	@echo "  make json-effect-consistency-smoke  Validate pop, return, transfer, stack, and memory effect relations"
	@echo "  make shellcheck-smoke  Run shellcheck when installed"
	@echo "  make docker-context-hygiene-smoke  Verify .env files stay out of Docker images"
	@echo "  make native-docker-json-parity-smoke  Compare 12 controlled native/container JSON reports byte-for-byte"
	@echo "  make analysis-tools-check  Inventory optional analysis/comparison tools"
	@echo "  make malformed-smoke     Run deterministic malformed-input smoke"
	@echo "  make fuzz-mutated-elf-smoke  Compatibility alias for malformed smoke"
	@echo "  make capacity-smoke      Validate exact and overflow candidate capacity"
	@echo "  make checkpoint-demo     Run the integrated checkpoint demonstration"
	@echo "  make bench-scanner-smoke Run scanner benchmark smoke measurements"
	@echo "  make bench-baselines-smoke  Compare optional baseline tools"
	@echo "  make bench-diagnostic-smoke  Run the provisional Sprint 11 x64lens diagnostic conditions"
	@echo "  make bench-summary-latest  Summarize newest non-empty benchmark artifact"
	@echo "  make bench-summary     Summarize one benchmark artifact by default"
	@echo "  make docker-build        Build the development image"
	@echo "  make docker-test         Run the core suite in Docker"
	@echo "  make docker-validation-smoke  Run complete validation in Docker"
	@echo "  make clean-results       Remove ignored local validation and benchmark results"
	@echo "  make doctor              Report required and optional tool availability"
	@echo "  make print-vars          Print reproducibility variables"

all: check-tools $(TARGET)

# Build-only dependency check. This intentionally checks only the tools needed
# to assemble and link x64lens. Broader development checks are available through
# dev-tools-check, validation-smoke, and doctor.
check-tools: build-tools-check

build-tools-check:
	bash tools/check-dev-tools.sh --build

sample-tools-check:
	bash tools/check-dev-tools.sh --samples

dev-tools-check:
	bash tools/check-dev-tools.sh --dev

diagnostic-tools-check:
	bash tools/check-dev-tools.sh --diagnostic

corpus-tools-check:
	bash tools/check-dev-tools.sh --corpus

baseline-tools-check:
	bash tools/check-dev-tools.sh --baselines

analysis-tools-check:
	bash tools/check-dev-tools.sh --analysis

full-tools-check:
	REQUIRE_BASELINES=1 bash tools/check-dev-tools.sh --all

doctor:
	bash tools/check-dev-tools.sh --doctor

install-dev-deps-ubuntu:
	sudo apt update
	sudo apt install -y nasm binutils gcc clang gdb make python3 python3-jsonschema python3-venv python3-pip pipx time git curl ca-certificates unzip zip
	@echo "Optional analysis/comparison tools: sudo apt install -y checksec radare2 strace shellcheck"
	python3 -m pipx ensurepath 2>/dev/null || pipx ensurepath 2>/dev/null || true

install-baseline-tools-user:
	bash tools/check-dev-tools.sh --dev
	command -v pipx >/dev/null 2>&1 || { echo "error: pipx is required. Run make install-dev-deps-ubuntu first."; exit 127; }
	pipx install ROPGadget || pipx upgrade ROPGadget
	pipx install ropper || pipx upgrade ropper
	@bash tools/install-ropr-user.sh || { \
		echo "warning: ropr was not installed. ROPgadget and ropper are enough for baseline smoke comparisons."; \
		echo "warning: run 'make install-rustup-user' and then 'make install-ropr-user' when ropr is needed."; \
		true; \
	}
	@bash tools/check-dev-tools.sh --baselines

install-rustup-user:
	@echo "Installing or updating user-local Rust stable toolchain through rustup..."
	@command -v curl >/dev/null 2>&1 || { echo "error: curl is required. Run make install-dev-deps-ubuntu first."; exit 127; }
	@if ! command -v rustup >/dev/null 2>&1; then \
		curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal; \
	fi
	@. "$$HOME/.cargo/env" 2>/dev/null || true; rustup install stable; rustup default stable
	@echo 'rustup stable toolchain installed. Restart the shell or run: . "$$HOME/.cargo/env"'

install-ropr-user:
	bash tools/install-ropr-user.sh

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.asm $(wildcard $(INC_DIR)/*.inc) | $(BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(TARGET): $(OBJS)
	$(LD) $(LDFLAGS) -o $@ $(OBJS)

$(INTERNAL_TEST_BUILD_DIR):
	mkdir -p $(INTERNAL_TEST_BUILD_DIR)

$(MEMORY_EFFECT_RECONCILIATION_OBJ): tests/internal/memory-effect-reconciliation.asm | $(INTERNAL_TEST_BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(MEMORY_EFFECT_RECONCILIATION_BIN): $(MEMORY_EFFECT_RECONCILIATION_OBJ) $(BUILD_DIR)/candidate_effect.o
	$(LD) $(LDFLAGS) -o $@ $^

$(REGISTER_ROLE_FACET_RECONCILIATION_OBJ): tests/internal/register-role-facet-reconciliation.asm | $(INTERNAL_TEST_BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(REGISTER_ROLE_FACET_RECONCILIATION_BIN): $(REGISTER_ROLE_FACET_RECONCILIATION_OBJ) $(BUILD_DIR)/candidate_role.o
	$(LD) $(LDFLAGS) -o $@ $^

$(CANDIDATE_MAPPING_RECONCILIATION_OBJ): tests/internal/candidate-mapping-reconciliation.asm | $(INTERNAL_TEST_BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(CANDIDATE_MAPPING_RECONCILIATION_BIN): $(CANDIDATE_MAPPING_RECONCILIATION_OBJ) $(BUILD_DIR)/candidate_mapping.o $(BUILD_DIR)/regions.o
	$(LD) $(LDFLAGS) -o $@ $^

$(BINARY_ROLE_RECONCILIATION_OBJ): tests/internal/binary-role-reconciliation.asm | $(INTERNAL_TEST_BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(BINARY_ROLE_RECONCILIATION_BIN): $(BINARY_ROLE_RECONCILIATION_OBJ) $(BUILD_DIR)/binary_role.o $(BUILD_DIR)/phdr.o $(BUILD_DIR)/gnu_property.o $(BUILD_DIR)/dynamic_metadata.o $(BUILD_DIR)/regions.o $(BUILD_DIR)/bounds.o
	$(LD) $(LDFLAGS) -o $@ $^

$(GNU_PROPERTY_RECONCILIATION_OBJ): tests/internal/gnu-property-reconciliation.c | $(INTERNAL_TEST_BUILD_DIR)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -fno-pie -c $< -o $@

$(GNU_PROPERTY_RECONCILIATION_BIN): $(GNU_PROPERTY_RECONCILIATION_OBJ) $(BUILD_DIR)/gnu_property.o $(BUILD_DIR)/bounds.o
	$(CC) -no-pie -o $@ $^

$(ROLE_PROPERTY_LAYOUT_AUTHORITY_OBJ): tests/internal/role-property-layout-authority.asm include/structs.inc | $(INTERNAL_TEST_BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(ROLE_PROPERTY_LAYOUT_RECONCILIATION_OBJ): tests/internal/role-property-layout-reconciliation.c tests/internal/role-property-layout.h | $(INTERNAL_TEST_BUILD_DIR)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -fno-pie -Itests/internal -c $< -o $@

$(ROLE_PROPERTY_LAYOUT_RECONCILIATION_BIN): $(ROLE_PROPERTY_LAYOUT_RECONCILIATION_OBJ) $(ROLE_PROPERTY_LAYOUT_AUTHORITY_OBJ)
	$(CC) -no-pie -o $@ $^

$(DYNAMIC_METADATA_LAYOUT_AUTHORITY_OBJ): tests/internal/dynamic-metadata-layout-authority.asm include/structs.inc | $(INTERNAL_TEST_BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(DYNAMIC_METADATA_LAYOUT_RECONCILIATION_OBJ): tests/internal/dynamic-metadata-layout-reconciliation.c tests/internal/dynamic-metadata-layout.h | $(INTERNAL_TEST_BUILD_DIR)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -fno-pie -Itests/internal -c $< -o $@

$(DYNAMIC_METADATA_LAYOUT_RECONCILIATION_BIN): $(DYNAMIC_METADATA_LAYOUT_RECONCILIATION_OBJ) $(DYNAMIC_METADATA_LAYOUT_AUTHORITY_OBJ)
	$(CC) -no-pie -o $@ $^

$(ROLE_PROPERTY_FACT_PROBE_OBJ): tests/internal/role-property-fact-probe.c tests/internal/role-property-layout.h tests/internal/dynamic-metadata-layout.h | $(INTERNAL_TEST_BUILD_DIR)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -fno-pie -Itests/internal -c $< -o $@

$(ROLE_PROPERTY_FACT_PROBE_BIN): $(ROLE_PROPERTY_FACT_PROBE_OBJ) $(ROLE_PROPERTY_LAYOUT_AUTHORITY_OBJ) $(DYNAMIC_METADATA_LAYOUT_AUTHORITY_OBJ) $(BUILD_DIR)/elf64.o $(BUILD_DIR)/phdr.o $(BUILD_DIR)/gnu_property.o $(BUILD_DIR)/dynamic_metadata.o $(BUILD_DIR)/binary_role.o $(BUILD_DIR)/regions.o $(BUILD_DIR)/bounds.o
	$(CC) -no-pie -o $@ $^

$(DYNAMIC_METADATA_FACT_PROBE_OBJ): tests/internal/dynamic-metadata-fact-probe.c tests/internal/role-property-layout.h tests/internal/dynamic-metadata-layout.h | $(INTERNAL_TEST_BUILD_DIR)
	$(CC) -std=c11 -O2 -Wall -Wextra -Werror -fno-pie -Itests/internal -c $< -o $@

$(DYNAMIC_METADATA_FACT_PROBE_BIN): $(DYNAMIC_METADATA_FACT_PROBE_OBJ) $(ROLE_PROPERTY_LAYOUT_AUTHORITY_OBJ) $(DYNAMIC_METADATA_LAYOUT_AUTHORITY_OBJ) $(BUILD_DIR)/elf64.o $(BUILD_DIR)/phdr.o $(BUILD_DIR)/gnu_property.o $(BUILD_DIR)/dynamic_metadata.o $(BUILD_DIR)/regions.o $(BUILD_DIR)/bounds.o
	$(CC) -no-pie -o $@ $^

samples: sample-tools-check
	$(MAKE) -C tests/toy-src
	mkdir -p tests/bin
	cp tests/toy-src/minimal_nopie tests/bin/ 2>/dev/null || true
	cp tests/toy-src/minimal_pie_canary tests/bin/ 2>/dev/null || true
	cp tests/toy-src/minimal_execstack tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets_sprint10 tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets_sprint10_transfer tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets_sprint10_stack_adjust tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets_sprint10_memory tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets_sprint10_effects tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets_sprint13_ordered_pairs tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets_capacity_exact tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets_capacity tests/bin/ 2>/dev/null || true

test: dev-tools-check all samples
	bash tests/run-tests.sh

# Scanner and exact-pattern correctness smoke test for the hand-authored
# gadget fixture. This target is intentionally separate from `make test` so
# reviewers can run the more explanatory objdump-backed check on demand.
validate-gadget-fixture: all samples
	bash tools/validate-gadget-fixture.sh ./$(TARGET) ./tests/bin/gadgets

scanner-smoke: validate-gadget-fixture

# Sprint 3 Phase D pattern smoke target. It verifies that the pattern matcher
# labels the controlled fixture. Sprint 4 semantic checks are now included in
# validate-gadget-fixture, so this remains a compatibility alias.
pattern-smoke: validate-gadget-fixture

# Sprint 4/5 semantic smoke target. It validates classifier and score facts for
# the known gadget fixture without broadening scan coverage.
semantic-smoke: validate-gadget-fixture


# Sprint 5 JSON smoke target. This verifies that machine-readable gadget output
# parses as JSON and satisfies the report invariants checked by the repository
# validator. The fixture mode asserts exact expected semantic and score facts.
json-smoke: dev-tools-check all samples
	@set -eu; tmp="$$(mktemp -d "$${TMPDIR:-/tmp}/x64lens-json-smoke.XXXXXX")"; \
	trap 'rm -rf "$$tmp"' EXIT; \
	./$(TARGET) gadgets --format json --max-depth 4 ./tests/bin/gadgets > "$$tmp/x64lens-json-smoke.json"; \
	python3 -m json.tool "$$tmp/x64lens-json-smoke.json" >/dev/null; \
	python3 tools/validate-json-report.py --mode fixture --require-schema 0.2.0 --expected-command gadgets --require-provenance --require-sprint10-effects --require-sprint10-transfer --require-sprint10-memory --require-sprint10-architectural-effects "$$tmp/x64lens-json-smoke.json" >/dev/null; \
	./$(TARGET) gadgets --max-depth 4 --format json ./tests/bin/gadgets > "$$tmp/x64lens-json-smoke-order2.json"; \
	python3 tools/validate-json-report.py --mode fixture --require-schema 0.2.0 --expected-command gadgets --require-provenance --require-sprint10-effects --require-sprint10-transfer --require-sprint10-memory --require-sprint10-architectural-effects "$$tmp/x64lens-json-smoke-order2.json" >/dev/null; \
	echo "json-smoke: ok"



# Sprint 10 Patch 046 entry gate. The historical fixture remains unchanged;
# this separate source proves ordered two-pop facts, conservative fallback,
# current-producer JSON effects, and gadgets/analyze command-only parity.
sprint10-primitive-smoke: dev-tools-check all samples
	@set -eu; python3 tools/sprint10-fixture-smoke.py --binary ./$(TARGET) --family ordered_multi_pop

# Sprint 10 register-transfer and cross-family memory gate.
sprint10-register-transfer-smoke: dev-tools-check all samples
	@set -eu; python3 tools/sprint10-fixture-smoke.py --binary ./$(TARGET) --family register_transfer

# Sprint 10 positive aligned stack-adjust gate.
sprint10-stack-adjust-smoke: dev-tools-check all samples
	@set -eu; python3 tools/sprint10-fixture-smoke.py --binary ./$(TARGET) --family stack_adjust

# Sprint 10 bounded qword memory-effect gate.
sprint10-memory-smoke: dev-tools-check all samples
	@set -eu; python3 tools/sprint10-fixture-smoke.py --binary ./$(TARGET) --family memory

# One-per-pattern architectural-effect gate.
sprint10-architectural-effects-smoke: dev-tools-check all samples
	@set -eu; python3 tools/sprint10-fixture-smoke.py --binary ./$(TARGET) --family exact_pattern_effects

# Negative orchestration proof: a failing specialty validator must prevent all later steps.
sprint10-fixture-gate-smoke:
	@python3 tools/sprint10-fixture-gate-smoke.py

# Semantic-family, exact-pattern, and fixture-suite reconciliation.
sprint10-contract-reconciliation-smoke:
	@python3 tools/sprint10-contract-reconciliation-smoke.py

# Score-policy authority must agree across semantic-family and exact-pattern gates.
sprint10-score-policy-smoke:
	@python3 tools/sprint10-score-policy-smoke.py

# Internal record-level regression for dense memory side-car reconciliation.
memory-effect-reconciliation-smoke: build-tools-check $(MEMORY_EFFECT_RECONCILIATION_BIN)
	@$(MEMORY_EFFECT_RECONCILIATION_BIN)

# Missing ShellCheck is advisory normally but a hard failure in strict mode.
shellcheck-contract-smoke:
	@python3 tools/shellcheck-contract-smoke.py

# Eleven semantic-family contracts remain independently reviewable.
sprint10-family-coverage-smoke:
	@python3 tools/sprint10-family-coverage-smoke.py

json-effect-consistency-smoke:
	@python3 tools/json-effect-consistency-smoke.py

# Sprint 9 schema transition gate. This target keeps a representative 0.1.0
# report consumable and proves that inconsistent 0.2.0 identity/completeness
# states fail closed in the bundled standard-library validator.
schema-compat-smoke:
	python3 tools/schema-compat-smoke.py

# Sprint 6 integrated analyze smoke target. This verifies that analyze combines
# target metadata, mitigation facts, raw candidates, semantic facts, scoring,
# and JSON report shape without changing the underlying scanner contract.
analyze-smoke: dev-tools-check all samples
	@set -eu; tmp="$$(mktemp -d "$${TMPDIR:-/tmp}/x64lens-analyze-smoke.XXXXXX")"; \
	trap 'rm -rf "$$tmp"' EXIT; \
	./$(TARGET) analyze --max-depth 4 ./tests/bin/gadgets > "$$tmp/x64lens-analyze-smoke.txt"; \
	grep -q "Format:" "$$tmp/x64lens-analyze-smoke.txt"; \
	grep -q "Mitigations:" "$$tmp/x64lens-analyze-smoke.txt"; \
	grep -q "Analysis:" "$$tmp/x64lens-analyze-smoke.txt"; \
	grep -q "Command: analyze" "$$tmp/x64lens-analyze-smoke.txt"; \
	grep -q "Complete: yes" "$$tmp/x64lens-analyze-smoke.txt"; \
	grep -q "Candidate truncated: no" "$$tmp/x64lens-analyze-smoke.txt"; \
	grep -q "Raw gadget candidates:" "$$tmp/x64lens-analyze-smoke.txt"; \
	grep -q "Candidate count: 0x000000000000000b" "$$tmp/x64lens-analyze-smoke.txt"; \
	grep -q "Scored candidate count: 0x000000000000000b" "$$tmp/x64lens-analyze-smoke.txt"; \
	./$(TARGET) analyze --format json --max-depth 4 ./tests/bin/gadgets > "$$tmp/x64lens-analyze-smoke.json"; \
	python3 tools/validate-json-report.py --mode fixture --require-schema 0.2.0 --expected-command analyze --require-provenance --require-sprint10-effects --require-sprint10-transfer --require-sprint10-memory --require-sprint10-architectural-effects "$$tmp/x64lens-analyze-smoke.json" >/dev/null; \
	./$(TARGET) analyze --max-depth 4 --format json ./tests/bin/gadgets > "$$tmp/x64lens-analyze-smoke-order2.json"; \
	python3 tools/validate-json-report.py --mode fixture --require-schema 0.2.0 --expected-command analyze --require-provenance --require-sprint10-effects --require-sprint10-transfer --require-sprint10-memory --require-sprint10-architectural-effects "$$tmp/x64lens-analyze-smoke-order2.json" >/dev/null; \
	./$(TARGET) gadgets --format json --max-depth 4 ./tests/bin/gadgets > "$$tmp/x64lens-gadgets-parity.json"; \
	python3 tools/validate-report-parity.py "$$tmp/x64lens-gadgets-parity.json" "$$tmp/x64lens-analyze-smoke.json" >/dev/null; \
	echo "analyze-smoke: ok"

# Real-binary smoke target. This runs the current pipeline against installed
# system ELF64 binaries and validates shape/invariants rather than brittle,
# distribution-specific candidate counts.
system-smoke: dev-tools-check all
	bash tools/system-binary-smoke.sh ./$(TARGET)

# Explicit candidate-capacity regression. Controlled fixtures exercise exactly
# 4096 records and a 4097th candidate. The exact boundary must remain complete;
# overflow must fail with EXIT_UNSUPPORTED and emit no partial report.
capacity-smoke: dev-tools-check all samples
	bash tools/validate-capacity-fixture.sh ./$(TARGET) ./tests/bin/gadgets_capacity ./tests/bin/gadgets_capacity_exact

# Deterministic hostile-input regression campaign. Generated mutations are
# temporary by default; compact TSV and metadata artifacts are written under
# tests/results/malformed/ for local inspection and remain ignored by Git.
malformed-smoke: dev-tools-check all samples
	python3 tools/malformed-elf-smoke.py \
		--binary ./$(TARGET) \
		--seed "$(MALFORMED_SEED)" \
		--timeout "$(MALFORMED_TIMEOUT)" \
		--results-dir "$(MALFORMED_RESULTS_DIR)"

# Compatibility alias retained for the parser-safety plan terminology. The
# first Sprint 7 campaign is deterministic mutation smoke, not coverage-guided
# fuzzing.
fuzz-mutated-elf-smoke: malformed-smoke

# Sprint 12 ordinary loader-validity and extended-numbering oracle. The
# compiler-independent fixtures exercise p_align, PT_LOAD congruence, virtual
# range overflow, executable-entrypoint containment, and explicit structurally
# valid unsupported outcomes for ELF64 extended numbering.
sprint12-phdr-validity-smoke: dev-tools-check all
	python3 tools/sprint12-phdr-validity-smoke.py --analyzer ./$(TARGET)

# Internal fact-first PIE/DSO role lattice. The harness exercises bounded
# PT_INTERP, DT_FLAGS_1, and DT_SONAME acquisition without changing public
# output or treating ET_DYN alone as a resolved executable role.
sprint12-binary-role-smoke: build-tools-check $(BINARY_ROLE_RECONCILIATION_BIN)
	./$(BINARY_ROLE_RECONCILIATION_BIN)

# Private bounded GNU property-note facts. The independent Python oracle can run
# before a NASM build; the full C/assembly gate then proves implementation facts,
# malformed behavior, and byte-identical public output.
sprint12-gnu-property-oracle-smoke:
	python3 tools/sprint12-gnu-property-smoke.py --oracle-only

sprint12-gnu-property-smoke: dev-tools-check all $(GNU_PROPERTY_RECONCILIATION_BIN)
	python3 tools/sprint12-gnu-property-smoke.py \
		--analyzer ./$(TARGET) \
		--internal-harness ./$(GNU_PROPERTY_RECONCILIATION_BIN)

# The private fact probe crosses the C/NASM boundary. Reconcile every consumed
# record offset and size before using the probe as evidence for a held-out corpus.
sprint12-role-property-layout-smoke: build-tools-check $(ROLE_PROPERTY_LAYOUT_RECONCILIATION_BIN)
	./$(ROLE_PROPERTY_LAYOUT_RECONCILIATION_BIN)

sprint12-dynamic-metadata-layout-smoke: build-tools-check $(DYNAMIC_METADATA_LAYOUT_RECONCILIATION_BIN)
	./$(DYNAMIC_METADATA_LAYOUT_RECONCILIATION_BIN)

sprint12-textrel-readelf-oracle:
	python3 tools/sprint12-textrel-matrix-smoke.py --authority "$(TEXTREL_AUTHORITY)" --oracle-only --readelf "$$(command -v $(READELF))"

sprint12-textrel-smoke: dev-tools-check all $(DYNAMIC_METADATA_FACT_PROBE_BIN)
	python3 tools/sprint12-textrel-matrix-smoke.py \
		--authority "$(TEXTREL_AUTHORITY)" \
		--analyzer ./$(TARGET) \
		--fact-probe ./$(DYNAMIC_METADATA_FACT_PROBE_BIN) \
		--schema "$(ROLE_PROPERTY_PUBLIC_SCHEMA)" \
		--readelf "$$(command -v $(READELF))"

# Patch 076 keeps RPATH and RUNPATH as separate private carrier/value families.
sprint12-search-path-readelf-oracle:
	python3 tools/sprint12-search-path-matrix-smoke.py \
		--authority "$(SEARCH_PATH_AUTHORITY)" \
		--readelf "$$(command -v $(READELF))" \
		--oracle-only

sprint12-search-path-smoke: dev-tools-check all $(DYNAMIC_METADATA_FACT_PROBE_BIN)
	python3 tools/sprint12-search-path-matrix-smoke.py \
		--authority "$(SEARCH_PATH_AUTHORITY)" \
		--analyzer ./$(TARGET) \
		--fact-probe ./$(DYNAMIC_METADATA_FACT_PROBE_BIN) \
		--schema "$(ROLE_PROPERTY_PUBLIC_SCHEMA)" \
		--readelf "$$(command -v $(READELF))"

# Patch 066 held-out preflight. This crosses three internal role constructions
# with four GNU-property states under canonical and exact-dual carrier encodings,
# then exercises four single-axis mutants. It changes no public schema or policy.
sprint12-role-property-metamorphic-smoke: dev-tools-check all $(ROLE_PROPERTY_FACT_PROBE_BIN)
	python3 tools/sprint12-role-property-metamorphic-smoke.py \
		--analyzer ./$(TARGET) \
		--fact-probe ./$(ROLE_PROPERTY_FACT_PROBE_BIN)

# Patch 068 held-out confirmation. Natural compiler/linker outputs and synthetic
# metamorphic objects close independently and remain private diagnostic facts.
sprint12-role-property-heldout-smoke: corpus-tools-check provisional-corpus-ready all $(ROLE_PROPERTY_FACT_PROBE_BIN)
	python3 tools/sprint12-role-property-heldout-smoke.py \
		--authority "$(ROLE_PROPERTY_HELDOUT_AUTHORITY)" \
		--analyzer ./$(TARGET) \
		--schema "$(ROLE_PROPERTY_PUBLIC_SCHEMA)" \
		--provisional-corpus "$(PROVISIONAL_CORPUS_PATH)" \
		--fact-probe ./$(ROLE_PROPERTY_FACT_PROBE_BIN)


# Patch 069 comparator reconciliation. The held-out result is regenerated under
# its authenticated authority, then every object receives retained readelf
# header, program-header, dynamic, and note evidence. Ambiguous or unavailable
# fields stay explicit and do not become runtime authority or public policy.
sprint12-role-property-readelf-smoke: corpus-tools-check provisional-corpus-ready all $(ROLE_PROPERTY_FACT_PROBE_BIN)
	@set -eu; \
	work="$$(mktemp -d)"; \
	work_identity="$$(python3 tools/remove-owned-tree.py --identify "$$work")"; \
	cleanup() { python3 tools/remove-owned-tree.py --remove "$$work" --identity "$$work_identity"; }; \
	trap cleanup EXIT HUP INT TERM; \
	python3 tools/sprint12-role-property-heldout-smoke.py \
		--authority "$(ROLE_PROPERTY_HELDOUT_AUTHORITY)" \
		--analyzer ./$(TARGET) \
		--schema "$(ROLE_PROPERTY_PUBLIC_SCHEMA)" \
		--provisional-corpus "$(PROVISIONAL_CORPUS_PATH)" \
		--fact-probe ./$(ROLE_PROPERTY_FACT_PROBE_BIN) \
		--result-dir "$$work/heldout"; \
	python3 tools/sprint12-role-property-readelf-smoke.py \
		--authority "$(ROLE_PROPERTY_READELF_AUTHORITY)" \
		--heldout-result "$$work/heldout" \
		--readelf "$$(command -v $(READELF))" \
		--result-dir "$$work/readelf"

# Patch 072 external-natural acquisition. Installed package source lineages and
# bytewise path selection are frozen before analyzer, probe, or readelf outcomes.
# This host-specific diagnostic gate remains separate from generic validation.
sprint12-external-natural-acquisition-smoke: dev-tools-check all $(ROLE_PROPERTY_FACT_PROBE_BIN)
	@command -v $(DPKG_QUERY) >/dev/null || { echo "error: dpkg-query is required for external-natural acquisition"; exit 2; }
	@set -eu; \
	result_dir="$(ROLE_PROPERTY_EXTERNAL_NATURAL_RESULT_DIR)"; \
	if [ -z "$$result_dir" ]; then \
		result_dir="./tests/results/sprint12-external-natural-$$(date -u +%Y%m%dT%H%M%SZ)-$$$$"; \
	fi; \
	mkdir -p "$$(dirname "$$result_dir")"; \
	python3 tools/sprint12-external-natural-acquisition-smoke.py \
		--authority "$(ROLE_PROPERTY_EXTERNAL_NATURAL_AUTHORITY)" \
		--analyzer ./$(TARGET) \
		--schema "$(ROLE_PROPERTY_PUBLIC_SCHEMA)" \
		--fact-probe ./$(ROLE_PROPERTY_FACT_PROBE_BIN) \
		--readelf "$$(command -v $(READELF))" \
		--dpkg-query "$$(command -v $(DPKG_QUERY))" \
		--result-dir "$$result_dir"; \
	echo "external-natural retained result: $$result_dir"

# Native/container private-fact parity from one exact Git-less source tree.
# Native and container binaries are built independently; the container receives
# no live repository, host analyzer/probe, source snapshot, or native result.
sprint12-role-property-environment-parity-smoke: corpus-tools-check provisional-corpus-ready docker-build
	@set -eu; \
	result_dir="$(ROLE_PROPERTY_PARITY_RESULT_DIR)"; \
	if [ -z "$$result_dir" ]; then \
		result_dir="./tests/results/sprint12-role-property-parity-$$(date -u +%Y%m%dT%H%M%SZ)-$$$$"; \
	fi; \
	mkdir -p "$$(dirname "$$result_dir")"; \
	python3 tools/docker-image-authority.py verify --path "$(DOCKER_IMAGE_AUTHORITY)" --docker "$(DOCKER)"; \
	image_id="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field image_id)"; \
	python3 tools/sprint12-role-property-environment-parity-smoke.py run \
		--repo . \
		--heldout-authority "$(ROLE_PROPERTY_HELDOUT_AUTHORITY)" \
		--provisional-corpus "$(PROVISIONAL_CORPUS_PATH)" \
		--schema "$(ROLE_PROPERTY_PUBLIC_SCHEMA)" \
		--docker-image "$$image_id" \
		--result-dir "$$result_dir"; \
	echo "native/container parity retained result: $$result_dir"

# Patch 076 extends private parity to the complete textrel/RPATH/RUNPATH side-car.
# The container builds its own binaries from authenticated source, receives the
# held-out fixtures read-only, and never sees the completed native result plane.
sprint12-dynamic-metadata-environment-parity-smoke: dev-tools-check docker-build
	@set -eu; \
	result_dir="$(DYNAMIC_METADATA_PARITY_RESULT_DIR)"; \
	if [ -z "$$result_dir" ]; then \
		result_dir="./tests/results/sprint12-dynamic-metadata-parity-$$(date -u +%Y%m%dT%H%M%SZ)-$$$$"; \
	fi; \
	mkdir -p "$$(dirname "$$result_dir")"; \
	python3 tools/docker-image-authority.py verify --path "$(DOCKER_IMAGE_AUTHORITY)" --docker "$(DOCKER)"; \
	image_id="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field image_id)"; \
	python3 tools/sprint12-dynamic-metadata-environment-parity-smoke.py run \
		--repo . \
		--authority "$(SEARCH_PATH_AUTHORITY)" \
		--analyzer ./$(TARGET) \
		--fact-probe ./$(DYNAMIC_METADATA_FACT_PROBE_BIN) \
		--schema "$(ROLE_PROPERTY_PUBLIC_SCHEMA)" \
		--docker-image "$$image_id" \
		--result-dir "$$result_dir"; \
	echo "dynamic-metadata native/container parity retained result: $$result_dir"


# Full Patch 072 acceptance keeps package-specific acquisition and Docker parity
# outside the portable native aggregate while making the required local gate explicit.
sprint12-p072-acceptance-smoke: validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke
	@echo "sprint12-p072-acceptance-smoke: ok"

# Patch 073 executes the public-policy decision without reinterpreting the
# existing coarse PIE field or exposing private role/property facts.
sprint12-role-property-public-policy-smoke:
	python3 tools/sprint12-role-property-public-policy-smoke.py \
		--authority "$(ROLE_PROPERTY_PUBLIC_POLICY_AUTHORITY)"

sprint12-mitigation-competitive-gap-smoke:
	python3 tools/sprint12-mitigation-competitive-gap-smoke.py \
		--authority "$(MITIGATION_COMPETITIVE_GAP_AUTHORITY)"

# Complete Patch 073 acceptance includes the portable native aggregate, the
# retained external-natural stratum, corrected native/container parity, and the
# non-reinterpretive policy decision.
sprint12-p073-acceptance-smoke: validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke
	@echo "sprint12-p073-acceptance-smoke: ok decision=defer public-fields-added=0"

# Patch 074 remains a historical closeout candidate whose authority is now
# explicitly superseded by the active Patch 075 continuation. Retain the target
# for exact historical replay; it is not the current acceptance gate.
sprint12-p074-acceptance-smoke: validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke

patch075-corrective-regression-smoke:
	python3 tools/patch075-corrective-regression-smoke.py

patch076-corrective-regression-smoke:
	python3 tools/patch076-corrective-regression-smoke.py

patch077-corrective-regression-smoke:
	python3 tools/patch077-corrective-regression-smoke.py

patch078-corrective-regression-smoke:
	python3 tools/patch078-corrective-regression-smoke.py

sprint13-register-role-decision-smoke:
	python3 tools/sprint13-register-role-decision-smoke.py \
		--authority ./benchmarks/task-definitions/sprint13-register-role-decision-v1.json

sprint13-role-facet-smoke: build-tools-check $(REGISTER_ROLE_FACET_RECONCILIATION_BIN)
	@$(REGISTER_ROLE_FACET_RECONCILIATION_BIN)

sprint13-register-role-task-value-smoke:
	python3 tools/sprint13-register-role-task-value-smoke.py \
		--authority ./benchmarks/task-definitions/sprint13-register-role-task-value-v2.json \
		--role-authority ./benchmarks/task-definitions/sprint13-register-role-decision-v1.json \
		--expected ./tests/expected/sprint13-register-role-task-value-v2.json

sprint13-role-policy-smoke:
	python3 tools/sprint13-role-policy-smoke.py \
		--authority ./benchmarks/task-definitions/sprint13-register-role-policy-v1.json \
		--expected ./tests/expected/sprint13-register-role-policy.json

patch079-corrective-regression-smoke:
	python3 tools/patch079-corrective-regression-smoke.py

patch074-corrective-regression-smoke:
	python3 tools/patch074-corrective-regression-smoke.py

sprint12-continuation-smoke:
	python3 tools/sprint12-continuation-smoke.py

# Patch 075 remains the historical text-relocation acceptance aggregate. Patch
# 076 supersedes it after extending the same private context with distinct
# RPATH/RUNPATH evidence. Retain this target for exact P075 replay.
sprint12-p075-acceptance-smoke: validation-smoke docker-validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-dynamic-metadata-environment-parity-smoke
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint12-p075-acceptance-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@echo "sprint12-p075-acceptance-smoke: ok sprint=12 status=active textrel=private public-fields-added=0"

# Patch 076 is the current Sprint 12 gate: all P075 corrections, strict textrel
# authority, distinct bounded RPATH/RUNPATH evidence, both private parity planes,
# complete native/Docker validation, and unchanged public schema 0.2.0.
sprint12-p076-acceptance-smoke: validation-smoke docker-validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-dynamic-metadata-environment-parity-smoke
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint12-p076-acceptance-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@echo "sprint12-p076-acceptance-smoke: ok sprint=12 status=active textrel=private rpath=private runpath=private public-fields-added=0"

# Patch 077 is the final Sprint 12 reconciliation candidate. It adds no
# analyzer field or parser family; it requires the corrected application,
# recovery, custody, oracle, and parity transactions plus all native/Docker and
# private-fact authorities before Sprint 12 may close.
sprint12-p077-acceptance-smoke: validation-smoke docker-validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-dynamic-metadata-environment-parity-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint12-p077-acceptance-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@echo "sprint12-p077-acceptance-smoke: ok sprint=12 status=closeout-candidate textrel=private rpath=private runpath=private public-fields-added=0 next-sprint=13"

# Patch 078 carries the final P077 corrections and opens Sprint 13 with an
# additive register-role decision over existing exact/effect facts.  Runtime
# semantic projection and score changes remain blocked on the blinded task-value
# gate, so schema 0.2.0 and public output remain unchanged.
sprint13-p078-acceptance-smoke: validation-smoke docker-validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-dynamic-metadata-environment-parity-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke sprint13-register-role-decision-smoke
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint13-p078-acceptance-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@echo "sprint13-p078-acceptance-smoke: ok patch=78 sprint12=closeout-corrected sprint13=entry-candidate roles=16 r10=syscall-arg4 public-fields-added=0 score-changes=0"

# Patch 079 closes the P078 acceptance blockers and records five diagnostic
# role-task strata. Patch 080 supersedes the original task oracle because P079
# reused confirmation queries and its presentation permutation was non-causal.
sprint13-p079-acceptance-smoke: validation-smoke docker-validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-dynamic-metadata-environment-parity-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke sprint13-register-role-decision-smoke sprint13-register-role-task-value-smoke
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint13-p079-acceptance-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@echo "sprint13-p079-acceptance-smoke: ok patch=79 sprint12=closed sprint13=active qualified-private-facets=3 deferred-facets=2 public-fields-added=0 score-changes=0"

# Patch 080 corrects the complete P079 transaction, Git-less, immutable-image,
# parity-build, and task-oracle finding set. It materializes three qualified
# register-role facets in a private additive side-car. Public output, semantic
# classes, scores, schema 0.2.0, capacity, and deterministic ordering remain
# unchanged.
sprint13-p080-acceptance-smoke: validation-smoke docker-validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-dynamic-metadata-environment-parity-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke sprint13-register-role-decision-smoke sprint13-register-role-task-value-smoke sprint13-role-facet-smoke sprint13-role-policy-smoke patch079-corrective-regression-smoke docker-image-authority-smoke
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint13-p080-acceptance-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@echo "sprint13-p080-acceptance-smoke: ok patch=80 sprint12=closed sprint13=active private-role-facets=3 public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0"


# Patch 081 corrects the complete P080 delivery, transaction, Git-less custody,
# immutable-image, and evidence-seal finding set. It executes a test-only
# ordered two-pop role-tuple task-value pilot and a complete score/null mutation
# authority. Both decisions preserve current runtime records, public output,
# semantic classes, scores, schema 0.2.0, capacity, and deterministic ordering.
# Patch 082 replaces producer-blind P081 gates with three independently built
# analyzer generations from one exact authenticated source tree.  The two
# historical policy names remain entry points, but both consume the same
# producer manifest and therefore execute only once in an aggregate Make DAG.
sprint13-producer-authority-smoke: build-tools-check
	@set -eu; \
	result_dir="$(S13_PRODUCER_RESULT_DIR)"; \
	temporary_root=""; \
	cleanup() { \
		if [ -n "$$temporary_root" ]; then \
			python3 tools/remove-owned-tree.py --remove "$$temporary_root" --identity "$$temporary_identity"; \
			temporary_root=""; \
		fi; \
	}; \
	trap cleanup EXIT; \
	trap 'exit 129' HUP; \
	trap 'exit 130' INT; \
	trap 'exit 143' TERM; \
	if [ -z "$$result_dir" ]; then \
		temporary_root="$$(mktemp -d "$${TMPDIR:-/tmp}/x64lens-p082-producer.XXXXXX")"; \
		temporary_identity="$$(python3 tools/remove-owned-tree.py --identify "$$temporary_root")"; \
		result_dir="$$temporary_root/result"; \
	fi; \
	python3 tools/sprint13-producer-authority-smoke.py run --repo . --result-dir "$$result_dir"; \
	python3 tools/sprint13-ordered-two-pop-role-task-value-smoke.py \
		--authority ./benchmarks/task-definitions/sprint13-ordered-two-pop-role-task-value-v2.json \
		--expected ./tests/expected/sprint13-ordered-two-pop-role-task-value-v2.json \
		--producer-manifest "$$result_dir/manifest.json"; \
	python3 tools/sprint13-score-null-authority-smoke.py \
		--authority ./benchmarks/task-definitions/sprint13-score-null-authority-v2.json \
		--expected ./tests/expected/sprint13-score-null-authority-v2.json \
		--producer-manifest "$$result_dir/manifest.json"; \
	if [ -z "$$temporary_root" ]; then echo "producer authority retained result: $$result_dir"; fi

sprint13-ordered-two-pop-role-task-value-smoke: sprint13-producer-authority-smoke
	@echo "sprint13-ordered-two-pop-role-task-value-smoke: producer-backed aggregate passed"

sprint13-score-null-authority-smoke: sprint13-producer-authority-smoke
	@echo "sprint13-score-null-authority-smoke: producer-backed aggregate passed"

sprint13-positive-coordinate-anchor-smoke:
	@set -eu; \
	args=""; \
	if [ -n "$(S13_COORDINATE_RESULT_DIR)" ]; then args="--result-dir $(S13_COORDINATE_RESULT_DIR)"; fi; \
	python3 tools/sprint13-positive-coordinate-anchor-smoke.py \
		--authority ./benchmarks/task-definitions/sprint13-positive-coordinate-anchor-v1.json \
		--expected ./tests/expected/sprint13-positive-coordinate-anchor-v1.json $$args

patch081-corrective-regression-smoke:
	python3 tools/patch081-corrective-regression-smoke.py

patch080-corrective-regression-smoke:
	python3 tools/patch080-corrective-regression-smoke.py

sprint13-p081-acceptance-smoke: validation-smoke docker-validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-dynamic-metadata-environment-parity-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke sprint13-register-role-decision-smoke sprint13-register-role-task-value-smoke sprint13-role-facet-smoke sprint13-role-policy-smoke sprint13-ordered-two-pop-role-task-value-smoke sprint13-score-null-authority-smoke patch080-corrective-regression-smoke docker-image-authority-smoke
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint13-p081-acceptance-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@echo "sprint13-p081-acceptance-smoke: ok patch=81 sprint12=retrospective-recorded sprint13=active tuple-decision=defer score-null=retained public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0"

# Patch 082 closes the remaining P081 Docker, authority-isolation, producer-
# oracle, extraction-mode, and loose-delivery findings.  The controlled
# coordinate preflight qualifies mechanics only; natural comparison remains a
# separate diagnostic campaign.
sprint13-p082-acceptance-smoke: validation-smoke docker-validation-smoke sprint12-external-natural-acquisition-smoke sprint12-role-property-environment-parity-smoke sprint12-dynamic-metadata-environment-parity-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke sprint13-producer-authority-smoke sprint13-positive-coordinate-anchor-smoke patch081-corrective-regression-smoke docker-image-authority-smoke
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint13-p082-acceptance-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@echo "sprint13-p082-acceptance-smoke: ok patch=82 sprint12=closed sprint13=active producer-generations=3 coordinate-preflight=qualified natural-coordinate-campaign=required public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0"

# Patch 070 prerequisite pilot. This validates complete-or-absent batch
# publication, exact failure positions, cleanup, and signal semantics without
# dividing batch time into a synthetic single-run latency.
sprint12-batch-transaction-smoke:
	python3 tools/sprint12-batch-transaction-smoke.py \
		--authority "$(ROLE_PROPERTY_BATCH_AUTHORITY)"

sprint12-overlap-decision-smoke:
	python3 tools/sprint12-overlap-decision-smoke.py

# Deterministic mitigation truth table. Controlled valid ELF64 layouts lock
# expected loader-level facts and bounded dynamic-table evidence. Malformed
# program-header and dynamic-table cases must fail closed across the command
# paths that parse the relevant table.
mitigation-matrix-smoke: dev-tools-check all samples
	python3 tools/mitigation-matrix-smoke.py \
		--binary ./$(TARGET) \
		--seed "$(MALFORMED_SEED)" \
		--timeout "$(MALFORMED_TIMEOUT)" \
		--results-dir "$(MITIGATION_MATRIX_RESULTS_DIR)"

# Focused section-label hardening probes. These fixtures keep section headers
# subordinate to program-header authority while exercising hostile annotation
# cases that are too specialized for the hand-authored gadget fixture.
section-label-smoke: dev-tools-check all
	python3 tools/section-label-smoke.py \
		--binary ./$(TARGET) \
		--timeout "$(MALFORMED_TIMEOUT)" \
		--results-dir "$(SECTION_LABEL_RESULTS_DIR)"

readelf-comparison-smoke: dev-tools-check all samples
	python3 tools/readelf-comparison-smoke.py \
		--binary ./$(TARGET) \
		--timeout "$(MALFORMED_TIMEOUT)" \
		--results-dir "$(READELF_COMPARISON_RESULTS_DIR)"

optional-tool-comparison-smoke: dev-tools-check all samples
	python3 tools/optional-mitigation-comparison-smoke.py \
		--binary ./$(TARGET) \
		--timeout "$(MALFORMED_TIMEOUT)" \
		--results-dir "$(OPTIONAL_TOOL_COMPARISON_RESULTS_DIR)"

benchmark-integrity-smoke:
	python3 tools/benchmark-integrity-smoke.py \
		--summarizer benchmarks/scripts/summarize.py \
		--results-dir "$(BENCHMARK_INTEGRITY_RESULTS_DIR)"

# Exercise bundle-path matching independently from a release artifact. The
# synthetic cases place generated files beneath multiple archive roots so the
# hygiene contract cannot accidentally depend on a single ZIP layout.
patch-bundle-hygiene-smoke:
	python3 tools/patch-bundle-hygiene-smoke.py

public-docs-hygiene-smoke:
	bash tools/public-docs-hygiene-smoke.sh

public-artifact-content-smoke:
	python3 tools/public-artifact-content-smoke.py

public-bundle-content-check:
	@test -n "$(PUBLIC_BUNDLE)" || { echo "error: set PUBLIC_BUNDLE=/path/to/public.zip"; exit 2; }
	python3 tools/check-public-content.py --zip "$(PUBLIC_BUNDLE)"

public-overlay-verify:
	@test -n "$(PUBLIC_BUNDLE)" || { echo "error: set PUBLIC_BUNDLE=/path/to/public.zip"; exit 2; }
	@test -n "$(PUBLIC_BUNDLE_SHA256)" || { echo "error: set PUBLIC_BUNDLE_SHA256=<expected-sha256>"; exit 2; }
	python3 tools/verify-public-overlay.py --bundle "$(PUBLIC_BUNDLE)" --expected-sha256 "$(PUBLIC_BUNDLE_SHA256)"

public-overlay-verification-smoke:
	python3 tools/public-overlay-verification-smoke.py

decoder-gap-hardening-smoke:
	python3 tools/decoder-gap-hardening-smoke.py

# Sprint 9 controlled decoder-gap gate. GNU objdump is an external comparison
# source only: it does not become runtime mapping authority or alter x64lens
# candidate/classification records. Generated artifacts remain ignored.
decoder-gap-smoke: dev-tools-check all samples
	python3 tools/decoder-gap-smoke.py \
		--binary ./$(TARGET) \
		--max-depth 4 \
		--controlled-only \
		--results-dir "$(DECODER_GAP_RESULTS_DIR)"

# Broader development evidence over the controlled fixture and selected system
# binaries. Exact counts are not asserted for host-provided targets.
decoder-gap-campaign: dev-tools-check all samples
	python3 tools/decoder-gap-smoke.py \
		--binary ./$(TARGET) \
		--max-depth 4 \
		--results-dir "$(DECODER_GAP_RESULTS_DIR)"

SHELLCHECK ?= shellcheck

shellcheck-smoke:
	@if command -v "$(SHELLCHECK)" >/dev/null 2>&1; then \
		if "$(SHELLCHECK)" tests/run-tests.sh tools/*.sh benchmarks/scripts/*.sh; then \
			echo "shellcheck-smoke: ok"; \
		elif [ "$${SHELLCHECK_STRICT:-0}" = "1" ]; then \
			exit 1; \
		else \
			echo "shellcheck-smoke: advisory findings present (set SHELLCHECK_STRICT=1 to fail)"; \
		fi; \
	elif [ "$${SHELLCHECK_STRICT:-0}" = "1" ]; then \
		echo "error: SHELLCHECK_STRICT=1 requires $(SHELLCHECK)" >&2; \
		exit 127; \
	else \
		echo "shellcheck-smoke: skipped ($(SHELLCHECK) not installed)"; \
	fi

# Sprint closeout gate. Normal development keeps ShellCheck optional, but a
# sprint cannot close unless strict lint is available and the complete native
# aggregate passes. Docker remains a separate reproducibility gate.
sprint-closeout-smoke: sprint11-closeout-smoke sprint12-closeout-smoke sprint12-continuation-smoke sprint13-register-role-decision-smoke sprint13-register-role-task-value-smoke sprint13-role-facet-smoke sprint13-role-policy-smoke patch079-corrective-regression-smoke patch078-corrective-regression-smoke patch077-corrective-regression-smoke patch076-corrective-regression-smoke patch075-corrective-regression-smoke patch074-corrective-regression-smoke patch073-corrective-regression-smoke
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint-closeout-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@$(MAKE) --no-print-directory validation-smoke
	@echo "sprint-closeout-smoke: ok"

# Local pre-commit validation bundle. Docker remains a separate reproducibility
# check because Docker Desktop/Engine availability is environment-dependent.
validation-smoke: script-perms-check sprint13-positive-coordinate-anchor-smoke patch081-corrective-regression-smoke scaffold-check diagrams-check public-docs-check public-docs-hygiene-smoke public-artifact-content-smoke public-overlay-verification-smoke planning-docs-check research-stage-gates-smoke research-roadmap-consistency-smoke sprint10-closeout-smoke sprint11-closeout-smoke sprint12-closeout-smoke sprint12-continuation-smoke sprint13-register-role-decision-smoke sprint13-register-role-task-value-smoke sprint13-role-facet-smoke sprint13-role-policy-smoke sprint13-ordered-two-pop-role-task-value-smoke sprint13-score-null-authority-smoke patch080-corrective-regression-smoke patch079-corrective-regression-smoke patch078-corrective-regression-smoke patch077-corrective-regression-smoke patch076-corrective-regression-smoke patch075-corrective-regression-smoke patch074-corrective-regression-smoke patch073-corrective-regression-smoke patch072-corrective-regression-smoke patch071-corrective-regression-smoke patch070-corrective-regression-smoke patch069-corrective-regression-smoke patch068-corrective-regression-smoke patch067-corrective-regression-smoke patch066-corrective-regression-smoke patch065-corrective-regression-smoke patch064-corrective-regression-smoke patch063-corrective-regression-smoke patch062-corrective-regression-smoke patch061-corrective-regression-smoke patch054-corrective-regression-smoke patch059-corrective-regression-smoke diagnostic-runner-smoke diagnostic-transaction-smoke runtime-closure-venv-smoke sprint11-below-floor-policy-smoke diagnostic-task-definitions-smoke baseline-output-adapter-smoke sprint11-measurement-plane-smoke sprint11-campaign-plan-smoke sprint11-p060-campaign-smoke sprint11-diagnostic-reference-smoke provisional-corpus-smoke checksum-manifest-path-smoke benchmark-integrity-smoke patch-bundle-hygiene-smoke schema-compat-smoke decoder-gap-hardening-smoke decoder-gap-smoke test validate-gadget-fixture semantic-smoke sprint10-primitive-smoke sprint10-register-transfer-smoke sprint10-stack-adjust-smoke sprint10-memory-smoke sprint10-family-coverage-smoke sprint10-architectural-effects-smoke sprint10-fixture-gate-smoke sprint10-contract-reconciliation-smoke sprint10-score-policy-smoke memory-effect-reconciliation-smoke shellcheck-contract-smoke json-effect-consistency-smoke json-smoke analyze-smoke system-smoke capacity-smoke malformed-smoke sprint12-phdr-validity-smoke sprint12-overlap-provenance-smoke sprint12-overlap-decision-smoke sprint12-binary-role-smoke sprint12-gnu-property-oracle-smoke sprint12-gnu-property-smoke sprint12-role-property-layout-smoke sprint12-dynamic-metadata-layout-smoke sprint12-textrel-smoke sprint12-search-path-smoke sprint12-role-property-metamorphic-smoke sprint12-role-property-heldout-smoke sprint12-role-property-readelf-smoke sprint12-batch-transaction-smoke sprint12-role-property-public-policy-smoke sprint12-mitigation-competitive-gap-smoke sprint12-textrel-readelf-oracle sprint12-search-path-readelf-oracle mitigation-matrix-smoke section-label-smoke readelf-comparison-smoke optional-tool-comparison-smoke
	@echo "validation-smoke: ok"

# Arena smoke target. It exercises the gadgets command path after candidate
# storage moved from static .bss memory to an mmap-backed arena. The expected
# counts follow the current controlled gadget fixture.
arena-smoke: all samples
	@set -eu; tmp="$$(mktemp -d "$${TMPDIR:-/tmp}/x64lens-arena-smoke.XXXXXX")"; \
	trap 'rm -rf "$$tmp"' EXIT; \
	./$(TARGET) gadgets --max-depth 4 ./tests/bin/gadgets > "$$tmp/x64lens-arena-smoke.txt"; \
	grep -q "Candidate capacity: 0x0000000000001000" "$$tmp/x64lens-arena-smoke.txt"; \
	grep -q "Candidate count: 0x000000000000000b" "$$tmp/x64lens-arena-smoke.txt"; \
	grep -q "ret imm16 count: 0x0000000000000001" "$$tmp/x64lens-arena-smoke.txt"; \
	grep -q "Exact pattern count: 0x000000000000000b" "$$tmp/x64lens-arena-smoke.txt"; \
	grep -q "Scored candidate count: 0x000000000000000b" "$$tmp/x64lens-arena-smoke.txt"; \
	echo "arena-smoke: ok"

# First Sprint 3 scanner benchmark smoke target. This records repeated runs,
# elapsed time, max RSS, exit code, candidate counts, and output size in
# benchmarks/results/. It is development evidence, not a publication claim.
bench-scanner-smoke: dev-tools-check all samples
	bash benchmarks/scripts/bench-scanner-smoke.sh ./$(TARGET)

bench-smoke: bench-scanner-smoke

# Sprint 5 Patch 019 baseline-comparison smoke target. Optional baseline
# tools are skipped when absent; set REQUIRE_BASELINES=1 to require at least
# one of ROPgadget, ropper, or ropr. Results are development evidence only.
bench-baselines-smoke: dev-tools-check baseline-tools-check all samples
	bash benchmarks/scripts/bench-baselines-smoke.sh ./$(TARGET)

# Sprint 11 diagnostic reference campaign. This target writes ignored mutable
# development evidence and deliberately excludes the unavailable scanner-only
# condition. Set DIAGNOSTIC_CAMPAIGN_ID to choose a stable local identity.
bench-diagnostic-smoke: diagnostic-tools-check all samples
	@set -eu; campaign="$(DIAGNOSTIC_CAMPAIGN_ID)"; \
	if [ -z "$$campaign" ]; then campaign="s11-p055-reference-$$(date -u +%Y%m%dT%H%M%S%NZ)"; fi; \
	python3 benchmarks/scripts/diagnostic-runner.py \
		--spec "$(DIAGNOSTIC_SPEC)" \
		--output-root "$(DIAGNOSTIC_RESULTS_DIR)" \
		--campaign-id "$$campaign"

# Sprint 11 Patch 060 authenticated provisional campaign.  Missing optional
# baselines remain explicit unavailable conditions rather than blocking the
# diagnostic x64lens rows or being replaced with synthetic evidence.
bench-sprint11-provisional-campaign: diagnostic-tools-check all provisional-corpus-ready
	@set -eu; \
	campaign="$(S11_P060_CAMPAIGN_ID)"; \
	if [ -z "$$campaign" ]; then campaign="s11-p060-provisional-$$(date -u +%Y%m%dT%H%M%S%NZ)"; fi; \
	set --; \
	if command -v ROPgadget >/dev/null 2>&1; then set -- "$$@" --ropgadget "$$(command -v ROPgadget)"; fi; \
	if command -v ropper >/dev/null 2>&1; then set -- "$$@" --ropper "$$(command -v ropper)"; fi; \
	if command -v ropr >/dev/null 2>&1; then set -- "$$@" --ropr "$$(command -v ropr)"; fi; \
	python3 benchmarks/scripts/sprint11-provisional-campaign.py \
		--plan "$(S11_P060_PLAN)" \
		--task-authority "$(S11_P060_TASK_AUTHORITY)" \
		--corpus-result "$(PROVISIONAL_CORPUS_PATH)" \
		--output-root "$(S11_P060_RESULTS_ROOT)" \
		--campaign-id "$$campaign" \
		--x64lens "./$(TARGET)" "$$@"

# Sprint 11 Patch 056 provisional corpus. Generated targets and retained build
# evidence remain ignored development artifacts. Publication uses no-replace
# semantics; regeneration therefore requires an explicit clean step or a new ID.
provisional-corpus-build: corpus-tools-check
	python3 benchmarks/scripts/build-provisional-corpus.py \
		--spec "$(PROVISIONAL_CORPUS_SPEC)" \
		--output-root "$(PROVISIONAL_CORPUS_ROOT)"

provisional-corpus-verify: corpus-tools-check
	@test -d "$(PROVISIONAL_CORPUS_PATH)" || { \
		echo "error: generated corpus not found: $(PROVISIONAL_CORPUS_PATH)" >&2; \
		echo "hint: run 'make provisional-corpus-build'" >&2; \
		exit 2; \
	}
	python3 benchmarks/scripts/build-provisional-corpus.py \
		--verify "$(PROVISIONAL_CORPUS_PATH)"

provisional-corpus-ready: corpus-tools-check
	@set -eu; \
	if [ ! -d "$(PROVISIONAL_CORPUS_PATH)" ]; then \
		$(MAKE) --no-print-directory provisional-corpus-build; \
	elif ! $(MAKE) --no-print-directory provisional-corpus-verify; then \
		echo "provisional-corpus-ready: attempting authenticated mode-only repair" >&2; \
		$(MAKE) --no-print-directory provisional-corpus-repair-modes; \
	fi; \
	$(MAKE) --no-print-directory provisional-corpus-verify

provisional-corpus-repair-modes: corpus-tools-check
	python3 benchmarks/scripts/build-provisional-corpus.py \
		--repair-modes "$(PROVISIONAL_CORPUS_PATH)"

provisional-corpus-smoke: corpus-tools-check
	python3 tools/provisional-corpus-smoke.py

clean-provisional-corpus:
	python3 benchmarks/scripts/build-provisional-corpus.py \
		--spec "$(PROVISIONAL_CORPUS_SPEC)" \
		--clean-output-root "$(PROVISIONAL_CORPUS_ROOT)"

checkpoint-demo: dev-tools-check all samples
	bash tools/demo-checkpoint.sh ./$(TARGET) "$(DEMO_TARGET)"

# Summarize only the newest baseline smoke artifact. This avoids accidentally
# combining separate development environments or historical runs.
bench-summary-latest:
	@file=""; \
	for candidate in $$(ls -1t benchmarks/results/baseline-smoke-*.tsv benchmarks/results/*.tsv 2>/dev/null | awk '!seen[$$0]++'); do \
		if [ "$$(wc -l < "$$candidate")" -gt 1 ]; then file="$$candidate"; break; fi; \
	done; \
	if [ -z "$$file" ]; then \
		echo "error: no non-empty benchmark TSV files found under benchmarks/results"; \
		exit 1; \
	fi; \
	echo "benchmark artifact: $$file"; \
	python3 benchmarks/scripts/summarize.py "$$file"

checkpoint-tag-help:
	@echo "Create the local annotated checkpoint tag only after Patch 023 is committed:"
	@echo "  git status --short"
	@echo "  git tag -a v0.1.0-dev -m 'x64lens v0.1.0-dev integrated checkpoint'"
	@echo "  git show --stat --decorate v0.1.0-dev"
	@echo "  git rev-parse v0.1.0-dev^{}"
	@echo "  git rev-parse HEAD"
	@echo "A normal git push does not publish the tag."

public-docs-check:
	bash tools/check-public-docs.sh

planning-docs-check:
	bash tools/check-planning-docs.sh

research-stage-gates-smoke:
	python3 tools/research-stage-gates-smoke.py

research-roadmap-consistency-smoke:
	python3 tools/research-roadmap-consistency-smoke.py

sprint10-closeout-smoke:
	python3 tools/sprint10-closeout-smoke.py

sprint11-closeout-smoke:
	python3 tools/sprint11-closeout-smoke.py

# Patch 074 machine-checks the Sprint 12 closeout state, preserves the public
# role/property deferral, and activates the bounded Sprint 13 semantic tranche.
sprint12-closeout-smoke:
	python3 tools/sprint12-closeout-smoke.py

patch054-corrective-regression-smoke:
	python3 tools/patch054-corrective-regression-smoke.py

diagnostic-runner-smoke:
	python3 tools/diagnostic-runner-smoke.py

diagnostic-transaction-smoke:
	python3 tools/diagnostic-transaction-smoke.py

runtime-closure-venv-smoke:
	python3 tools/runtime-closure-venv-smoke.py

sprint11-below-floor-policy-smoke:
	python3 tools/sprint11-below-floor-policy-smoke.py

diagnostic-task-definitions-smoke:
	python3 tools/diagnostic-task-definitions-smoke.py

baseline-output-adapter-smoke:
	python3 tools/baseline-output-adapter-smoke.py

sprint11-measurement-plane-smoke: corpus-tools-check
	python3 tools/sprint11-measurement-plane-smoke.py

sprint11-campaign-plan-smoke:
	python3 tools/sprint11-campaign-plan-smoke.py

# Patch 059 correction rollup.  The component gates remain independently
# invokable, while this authority prevents later validation matrices from
# accepting only a subset of the reviewed integrity corrections.
patch059-corrective-regression-smoke: script-perms-check diagnostic-task-definitions-smoke baseline-output-adapter-smoke diagnostic-runner-smoke diagnostic-transaction-smoke provisional-corpus-smoke sprint11-measurement-plane-smoke
	@echo "patch059-corrective-regression-smoke: ok components=7"

# Patch 067 review corrections. These probes close the corpus mutation boundary,
# caller-visible ancestor binding, rollback retry, stale displaced-root oracle,
# layout-authority dependency, and executable ABI-source oracle.
# Patch 068 review corrections. These probes bind semantic verification to
# retained descriptors, require signal-safe rollback and directory metadata
# continuity, consume every held-out authority, retain all private fact vectors,
# reject public leaks, and require production assembly include dependencies.
# Patch 071 corrects the Patch 070 member-cleanup, batch-authority, streaming
# output-limit, and recursive delivery-custody defects without changing runtime
# analyzer or schema behavior.
patch070-corrective-regression-smoke: sprint12-batch-transaction-smoke
	python3 tools/patch070-corrective-regression-smoke.py

patch073-corrective-regression-smoke:
	python3 tools/patch073-corrective-regression-smoke.py

patch072-corrective-regression-smoke:
	python3 tools/patch072-corrective-regression-smoke.py

patch071-corrective-regression-smoke: sprint12-batch-transaction-smoke
	python3 tools/patch071-corrective-regression-smoke.py

patch069-corrective-regression-smoke: patch068-corrective-regression-smoke sprint12-batch-transaction-smoke
	python3 tools/patch069-corrective-regression-smoke.py

patch068-corrective-regression-smoke: corpus-tools-check provisional-corpus-ready all $(ROLE_PROPERTY_FACT_PROBE_BIN)
	python3 tools/patch068-corrective-regression-smoke.py

patch067-corrective-regression-smoke:
	python3 tools/patch067-corrective-regression-smoke.py

# Patch 064 review corrections. These probes reject unencodable assembly forms,
# require complete role-carrier validation, authenticate every non-mode corpus
# fact before repair, prevent hard-link chmod redirection, and keep permission
# normalization from following links into generated evidence trees.
patch066-corrective-regression-smoke:
	python3 tools/patch066-corrective-regression-smoke.py

patch065-corrective-regression-smoke:
	python3 tools/patch065-corrective-regression-smoke.py

patch064-corrective-regression-smoke:
	python3 tools/patch064-corrective-regression-smoke.py

# Patch 063 review corrections. These probes retain the corpus root descriptor
# through authenticated mode repair, reject ownership drift, and preserve the
# canonical SHT_NULL section-zero fixture contract.
patch063-corrective-regression-smoke:
	python3 tools/patch063-corrective-regression-smoke.py

# Patch 062 review corrections. These probes cover clean aggregate corpus
# readiness, authenticated cleanup, output-root continuity, and failure-lifetime
# descriptor ownership.
patch062-corrective-regression-smoke: corpus-tools-check
	python3 tools/patch062-corrective-regression-smoke.py

# Sprint 12 Patch 063 internal overlap-provenance seam. The harness validates
# original PHDR indexes and dense contributor masks without changing reports.
sprint12-overlap-provenance-smoke: build-tools-check $(CANDIDATE_MAPPING_RECONCILIATION_BIN)
	$(CANDIDATE_MAPPING_RECONCILIATION_BIN)

# Patch 061 review corrections. These probes preserve foreign replacements,
# bind specification bytes through consumption, reject output-root symlink
# ancestors before side effects, and fail closed on post-commit substitution.
patch061-corrective-regression-smoke:
	python3 tools/patch061-corrective-regression-smoke.py

# Patch 060 controlled all-tools oracle.  The real analyzer and provisional
# corpus are paired with tool-compatible baseline probes so host package
# availability cannot hide a broken 30-condition derivation path.
sprint11-p060-campaign-smoke: provisional-corpus-ready all
	python3 tools/sprint11-p060-campaign-smoke.py

sprint11-diagnostic-reference-smoke: diagnostic-tools-check all samples
	python3 tools/sprint11-diagnostic-reference-smoke.py

checksum-manifest-path-smoke:
	python3 tools/checksum-manifest-path-smoke.py

bench-summary:
	@files="$$(ls benchmarks/results/*.tsv 2>/dev/null || true)"; \
	if [ -z "$$files" ]; then \
		echo "error: no benchmark TSV files found under benchmarks/results"; \
		exit 1; \
	fi; \
	count="$$(printf '%s\n' $$files | wc -l | tr -d ' ')"; \
	if [ "$$count" -gt 1 ] && [ "$${ALLOW_MIXED_BENCH_SUMMARY:-0}" != "1" ]; then \
		echo "error: refusing to summarize $$count benchmark TSV files without ALLOW_MIXED_BENCH_SUMMARY=1"; \
		echo "hint: use 'make bench-summary-latest' for the newest non-empty artifact"; \
		exit 1; \
	fi; \
	python3 benchmarks/scripts/summarize.py $$files

script-perms-check:
	@echo "Checking shell helper executable bits..."
	@test -x tests/run-tests.sh
	@test -x benchmarks/scripts/bench-ropgadget.sh
	@test -x benchmarks/scripts/bench-ropper.sh
	@test -x benchmarks/scripts/bench-ropr.sh
	@test -x benchmarks/scripts/bench-scanner-smoke.sh
	@test -x benchmarks/scripts/bench-baselines-smoke.sh
	@test -x benchmarks/scripts/summarize.py
	@test -x benchmarks/scripts/diagnostic-runner.py
	@test -x benchmarks/scripts/build-provisional-corpus.py
	@test -x benchmarks/scripts/baseline-output-adapter.py
	@test -f benchmarks/scripts/diagnostic_artifact.py
	@test ! -x benchmarks/scripts/diagnostic_artifact.py
	@test -x benchmarks/scripts/x64lens-relation-extractor.py
	@test -x benchmarks/scripts/runtime-closure-manifest.py
	@test -x benchmarks/scripts/address-coordinate-calibrator.py
	@test -x benchmarks/scripts/sprint11-provisional-campaign.py
	@test -x benchmarks/scripts/bench-x64lens.sh
	@test -x tools/benchmark-integrity-smoke.py
	@test -x tools/patch-bundle-hygiene-smoke.py
	@test -x tools/check-patch-bundle-hygiene.py
	@test -x tools/decoder-gap-smoke.py
	@test -x tools/decoder-gap-hardening-smoke.py
	@test -x tools/compare-checksec.sh
	@test -x tools/compare-objdump.sh
	@test -x tools/compare-rabin2.sh
	@test -x tools/compare-readelf.sh
	@test -x tools/compare-ropgadget.sh
	@test -x tools/docker-context-hygiene-smoke.sh
	@test -x tools/native-docker-json-parity-smoke.sh
	@test -x tools/make-release-artifacts.sh
	@test -x tools/optional-mitigation-comparison-smoke.py
	@test -x tools/readelf-comparison-smoke.py
	@test -x tools/validate-gadget-fixture.sh
	@test -x tools/validate-json-report.py
	@test -x tools/validate-sprint10-disassembly.py
	@test -x tools/validate-sprint10-transfer-disassembly.py
	@test -x tools/validate-sprint10-stack-adjust-disassembly.py
	@test -x tools/validate-sprint10-memory-disassembly.py
	@test -x tools/validate-sprint10-effects-disassembly.py
	@test -x tools/sprint10-fixture-smoke.py
	@test -x tools/sprint10-fixture-gate-smoke.py
	@test -x tools/sprint10-contract-reconciliation-smoke.py
	@test -x tools/sprint10-score-policy-smoke.py
	@test -x tools/patch067-corrective-regression-smoke.py
	@test -x tools/patch066-corrective-regression-smoke.py
	@test -x tools/patch065-corrective-regression-smoke.py
	@test -x tools/sprint12-role-property-metamorphic-smoke.py
	@test -x tools/sprint12-role-property-heldout-smoke.py
	@test -x tools/sprint12-role-property-readelf-smoke.py
	@test -x tools/patch068-corrective-regression-smoke.py
	@test -x tools/patch070-corrective-regression-smoke.py
	@test -x tools/patch069-corrective-regression-smoke.py
	@test -x tools/remove-owned-tree.py
	@test -x tools/verify-delivery-custody.py
	@test -x tools/sprint12-batch-transaction-smoke.py
	@test -x tools/patch072-corrective-regression-smoke.py
	@test -x tools/patch071-corrective-regression-smoke.py
	@test -x tools/sprint12-external-natural-acquisition-smoke.py
	@test -x tools/sprint12-role-property-environment-parity-smoke.py
	@test -x tools/sprint12-role-property-public-policy-smoke.py
	@test -x tools/sprint12-mitigation-competitive-gap-smoke.py
	@test -x tools/sprint12-textrel-matrix-smoke.py
	@test -x tools/sprint12-search-path-matrix-smoke.py
	@test -x tools/sprint12-dynamic-metadata-environment-parity-smoke.py
	@test -x tools/patch075-corrective-regression-smoke.py
	@test -x tools/patch076-corrective-regression-smoke.py
	@test -x tools/git-patch-transaction.py
	@test -x tools/gitless-source-manifest.py
	@test -x tools/patch077-corrective-regression-smoke.py
	@test -x tools/patch078-corrective-regression-smoke.py
	@test -x tools/sprint13-register-role-decision-smoke.py
	@test -x tools/sprint13-register-role-task-value-smoke.py
	@test -x tools/sprint13-role-policy-smoke.py
	@test -x tools/patch079-corrective-regression-smoke.py
	@test -x tools/docker-image-authority.py
	@test -x tools/sprint12-continuation-smoke.py
	@test -x tools/patch074-corrective-regression-smoke.py
	@test -x tools/recover-candidate-source.py
	@test -f benchmarks/task-definitions/sprint12-role-property-public-policy-v1.json
	@test -f benchmarks/task-definitions/sprint13-register-role-decision-v1.json
	@test -f benchmarks/task-definitions/sprint13-register-role-task-value-v1.json
	@test -f tests/expected/sprint13-register-role-task-value.json
	@test -f docs/adr/0065-patch078-correction-and-register-role-task-value.md
	@test -f docs/adr/0066-patch079-correction-and-private-register-role-sidecar.md
	@test -f docs/sprints/sprint-13-patch-080-validation.md
	@test -f docs/sprints/sprint-13-patch-079-validation.md
	@test -f benchmarks/task-definitions/sprint12-mitigation-competitive-gap-v1.json
	@test -f benchmarks/task-definitions/sprint12-role-property-heldout-v1.json
	@test -x tools/shellcheck-contract-smoke.py
	@test -f tests/internal/memory-effect-reconciliation.asm
	@test -f tests/internal/candidate-mapping-reconciliation.asm
	@test -f tests/internal/binary-role-reconciliation.asm
	@test -x tools/json-effect-consistency-smoke.py
	@test -x tools/sprint10-family-coverage-smoke.py
	@test -x tools/validate-report-parity.py
	@test -x tools/schema-compat-smoke.py
	@test -x tools/system-binary-smoke.sh
	@test -x tools/check-patch-bundle-hygiene.sh
	@test -x tools/check-dev-tools.sh
	@test -x tools/install-ropr-user.sh
	@test -x tools/demo-checkpoint.sh
	@test -x tools/check-public-docs.sh
	@test -x tools/check-public-content.py
	@test -x tools/public-docs-hygiene-smoke.sh
	@test -x tools/public-artifact-content-smoke.py
	@test -x tools/verify-public-overlay.py
	@test -x tools/public-overlay-verification-smoke.py
	@test -x tools/research-stage-gates-smoke.py
	@test -x tools/research-roadmap-consistency-smoke.py
	@test -x tools/sprint10-closeout-smoke.py
	@test -x tools/sprint11-closeout-smoke.py
	@test -x tools/sprint12-closeout-smoke.py
	@test -x tools/patch054-corrective-regression-smoke.py
	@test -x tools/patch061-corrective-regression-smoke.py
	@test -x tools/patch062-corrective-regression-smoke.py
	@test -x tools/patch063-corrective-regression-smoke.py
	@test -f docs/adr/0049-executable-overlap-provenance-seam.md
	@test -f docs/sprints/sprint-12-patch-063-validation.md
	@test -x tools/diagnostic-runner-smoke.py
	@test -x tools/runtime-closure-venv-smoke.py
	@test -x tools/sprint11-below-floor-policy-smoke.py
	@test -x tools/diagnostic-transaction-smoke.py
	@test -x tools/diagnostic-task-definitions-smoke.py
	@test -x tools/baseline-output-adapter-smoke.py
	@test -x tools/sprint11-measurement-plane-smoke.py
	@test -x tools/sprint11-campaign-plan-smoke.py
	@test -x tools/sprint11-p060-campaign-smoke.py
	@test -x tools/sprint11-diagnostic-reference-smoke.py
	@test -x tools/provisional-corpus-smoke.py
	@test -x tools/sprint12-phdr-validity-smoke.py
	@test -x tools/sprint12-overlap-decision-smoke.py
	@test -f benchmarks/task-definitions/sprint12-overlap-normalization-decision.json
	@test -f src/binary_role.asm
	@test -f docs/adr/0050-fact-first-binary-role-lattice.md
	@test -f docs/sprints/sprint-12-patch-064-validation.md
	@test -x tools/verify-checksum-manifest.py
	@test -x tools/checksum-manifest-path-smoke.py
	@test -x tools/check-planning-docs.sh
	@test -x tools/malformed-elf-smoke.py
	@test -x tools/fuzz-mutated-elf-smoke.sh
	@test -x tools/validate-capacity-fixture.sh
	@test -x tools/mitigation-matrix-smoke.py
	@test -x tools/section-label-smoke.py
	@echo "script-perms-check: ok"

scaffold-check: script-perms-check
	@echo "Checking required scaffold paths..."
	@test -f README.md
	@test -f Makefile
	@test -f src/main.asm
	@test -f src/analysis_summary.asm
	@test -f src/candidate_evidence.asm
	@test -f src/memory_effect.asm
	@test -f src/candidate_effect.asm
	@test -f src/candidate_role.asm
	@test -f tests/internal/register-role-facet-reconciliation.asm
	@test -f benchmarks/task-definitions/sprint13-register-role-task-value-v2.json
	@test -f benchmarks/task-definitions/sprint13-register-role-policy-v1.json
	@test -f tests/expected/sprint13-register-role-task-value-v2.json
	@test -f tests/expected/sprint13-register-role-policy.json
	@test -f tools/docker-image-authority.py
	@test -f tools/patch079-corrective-regression-smoke.py
	@test -f tools/sprint13-role-policy-smoke.py
	@test -f include/constants.inc
	@test -f docs/project-charter.md
	@test -f docs/contracts/development-contract.md
	@test -f docs/contracts/research-contract.md
	@test -f docs/contracts/output-contract.md
	@test -f docs/contracts/release-contract.md
	@test -f docs/environment.md
	@test -f docs/visualization.md
	@test -f docs/troubleshooting.md
	@test -f docs/onboarding.md
	@test -f docs/demo.md
	@test -f docs/benchmark-smoke-interpretation.md
	@test -f docs/adr/0011-composable-text-report-sections.md
	@test -f docs/adr/0012-roadmap-expansion-and-research-release-gates.md
	@test -f docs/adr/0013-deterministic-hostile-input-regression-harness.md
	@test -f docs/adr/0014-deterministic-mitigation-oracle.md
	@test -f docs/adr/0015-shared-checked-parser-arithmetic.md
	@test -f docs/adr/0016-bounded-dynamic-table-view.md
	@test -f docs/adr/0017-relro-refinement-and-duplicate-dynamic-policy.md
	@test -f docs/adr/0018-canary-indicator-and-dynamic-string-scan.md
	@test -f docs/adr/0019-stripped-indicator-and-dynamic-singleton-policy.md
	@test -f docs/adr/0020-section-label-annotations.md
	@test -f docs/adr/0021-section-label-rendering-and-ambiguity.md
	@test -f docs/adr/0022-historical-findings-hardening.md
	@test -f docs/adr/0023-comparator-and-benchmark-integrity-gates.md
	@test -f docs/adr/0024-sprint8-closeout-and-helper-hardening.md
	@test -f docs/adr/0025-sprint8-closeout-correction.md
	@test -f docs/adr/0026-report-identity-and-analysis-completeness.md
	@test -f docs/adr/0027-candidate-evidence-sidecar-and-contract-hardening.md
	@test -f docs/design/mitigation-fixture-matrix.md
	@test -f docs/sprints/sprint-07-patch-026-validation.md
	@test -f docs/sprints/sprint-07-patch-027-validation.md
	@test -f docs/sprints/sprint-07-patch-028-validation.md
	@test -f docs/sprints/sprint-07-patch-029-validation.md
	@test -f docs/sprints/sprint-07-retro.md
	@test -f tests/malformed/README.md
	@test -f tests/malformed/regressions/README.md
	@test -f tests/malformed/regressions/elf64-shentsize-63.bin
	@test -f docs/roadmap-18-sprints.md
	@test -f docs/roadmap-22-sprints.md
	@test -f docs/adr/0039-benchmark-informed-capability-roadmap.md
	@test -f docs/adr/0040-sprint10-closeout-and-diagnostic-benchmark-entry.md
	@test -f docs/design/benchmark-and-capability-stage-gates.md
	@test -f docs/sprints/sprint-10-patch-053-validation.md
	@test -f docs/sprints/sprint-10-patch-054-validation.md
	@test -f docs/sprints/sprint-10-retro.md
	@test -f tests/expected/research-stage-gates.json
	@test -f tests/expected/sprint10-closeout.json
	@test -f tests/expected/sprint11-closeout.json
	@test -f benchmarks/specs/sprint11-reference-diagnostic.json
	@test -f benchmarks/task-definitions/sprint11-diagnostic-tasks.json
	@test -f benchmarks/task-definitions/sprint11-p059-campaign-plan.json
	@test -f benchmarks/scripts/diagnostic_artifact.py
	@test ! -x benchmarks/scripts/diagnostic_artifact.py
	@test -f benchmarks/scripts/x64lens-relation-extractor.py
	@test -f benchmarks/scripts/runtime-closure-manifest.py
	@test -f benchmarks/scripts/address-coordinate-calibrator.py
	@test -f tests/fixtures/baseline-adapters/ropgadget-valid.txt
	@test -f tests/fixtures/baseline-adapters/ropper-valid.txt
	@test -f tests/fixtures/baseline-adapters/ropr-valid.txt
	@test -f docs/design/diagnostic-benchmark-task-definitions.md
	@test -f docs/adr/0041-sprint11-diagnostic-runner-foundation.md
	@test -f docs/sprints/sprint-11-patch-055-validation.md
	@test -f benchmarks/corpus/README.md
	@test -f benchmarks/corpus/sources/sprint11-provisional-control-flow.c
	@test -f benchmarks/corpus/specs/sprint11-provisional-corpus-v1.json
	@test -f docs/adr/0042-provisional-corpus-provenance-and-regeneration.md
	@test -f docs/adr/0043-sprint11-diagnostic-integrity-correction.md
	@test -f docs/adr/0044-task-normalized-baseline-adapters-and-diagnostic-integrity.md
	@test -f docs/adr/0045-measurement-plane-and-transaction-integrity.md
	@test -f docs/adr/0046-authenticated-provisional-campaign-and-gap-register.md
	@test -f docs/adr/0047-sprint11-closeout-and-diagnostic-method-refinement.md
	@test -f docs/adr/0048-phdr-validity-and-extended-numbering-boundary.md
	@test -f tests/internal/role-property-layout-authority.asm
	@test -f tests/internal/role-property-layout.h
	@test -f tests/internal/role-property-layout-reconciliation.c
	@test -f tests/internal/role-property-fact-probe.c
	@test -f tests/internal/dynamic-metadata-layout-authority.asm
	@test -f tests/internal/dynamic-metadata-layout.h
	@test -f tests/internal/dynamic-metadata-layout-reconciliation.c
	@test -f tests/internal/dynamic-metadata-fact-probe.c
	@test -f benchmarks/task-definitions/sprint12-textrel-private-evidence-v1.json
	@test -f benchmarks/task-definitions/sprint12-search-path-private-evidence-v1.json
	@test -f docs/adr/0052-role-property-metamorphic-preflight.md
	@test -f docs/adr/0053-corpus-custody-and-private-layout-attestation.md
	@test -f docs/sprints/sprint-12-patch-066-validation.md
	@test -f docs/sprints/sprint-12-patch-067-validation.md
	@test -f docs/sprints/sprint-12-patch-068-validation.md
	@test -f docs/adr/0054-private-role-property-diagnostic-matrix.md
	@test -f docs/adr/0055-authenticated-role-property-readelf-reconciliation.md
	@test -f docs/sprints/sprint-12-patch-069-validation.md
	@test -f docs/adr/0056-whole-batch-transaction-and-external-evidence-custody.md
	@test -f docs/sprints/sprint-12-patch-070-validation.md
	@test -f docs/adr/0057-identity-bound-cleanup-outcome-complete-batch-and-delivery-custody.md
	@test -f docs/sprints/sprint-12-patch-071-validation.md
	@test -f docs/adr/0058-outcome-blind-external-natural-acquisition-and-environment-parity.md
	@test -f docs/sprints/sprint-12-patch-072-validation.md
	@test -f benchmarks/task-definitions/sprint12-role-property-readelf-v1.json
	@test -f benchmarks/task-definitions/sprint12-batch-transaction-pilot-v2.json
	@test -f benchmarks/task-definitions/sprint12-batch-transaction-pilot-v3.json
	@test -f benchmarks/task-definitions/sprint12-external-natural-acquisition-v1.json
	@test -f docs/sprints/sprint-11-patch-056-validation.md
	@test -f docs/sprints/sprint-11-patch-057-validation.md
	@test -f docs/sprints/sprint-11-patch-058-validation.md
	@test -f docs/sprints/sprint-11-patch-059-validation.md
	@test -f docs/sprints/sprint-11-patch-060-validation.md
	@test -f docs/sprints/sprint-11-patch-061-validation.md
	@test -f docs/sprints/sprint-12-patch-062-validation.md
	@test -f docs/sprints/sprint-11-retro.md
	@test -f docs/sprints/sprint-11-diagnostic-campaign-guide.md
	@test -f docs/research-release-plan.md
	@test -f docs/design/evidence-provenance-model.md
	@test -f docs/design/schema-evolution.md
	@test -f docs/sprints/sprint-09-patch-040-validation.md
	@test -f docs/sprints/sprint-09-patch-041-validation.md
	@test -f schemas/x64lens-report-0.1.0.schema.json
	@test -f schemas/x64lens-report.schema.json
	@test -f tests/expected/x64lens-report-0.1.0.json
	@test -f tests/expected/x64lens-report-0.2.0.json
	@test -f tests/expected/x64lens-report-0.2.0-p040.json
	@test -f tests/expected/x64lens-report-sprint10-stack-adjust-0.2.0.json
	@test -f tests/expected/x64lens-report-sprint10-memory-0.2.0.json
	@test -f tests/toy-src/gadgets_sprint10_memory.S
	@test -f tests/toy-src/gadgets_sprint10_effects.S
	@test -f tests/expected/sprint10-family-coverage.json
	@test -f tests/expected/sprint10-exact-pattern-catalog.json
	@test -f tests/expected/sprint10-fixture-suite.json
	@test -f tests/expected/x64lens-report-sprint10-effects-0.2.0.json
	@test -f tools/validate-report-parity.py
	@test -f tools/patch-bundle-hygiene-smoke.py
	@test -f tools/check-patch-bundle-hygiene.py
	@test -f tools/decoder-gap-smoke.py
	@test -f tools/decoder-gap-hardening-smoke.py
	@test -f tools/public-docs-hygiene-smoke.sh
	@test -f tools/check-public-content.py
	@test -f tools/public-artifact-content-smoke.py
	@test -f tools/verify-public-overlay.py
	@test -f tools/public-overlay-verification-smoke.py
	@test -f tests/expected/decoder-gap-controlled.json
	@test -f docs/design/decoder-gap-decision-gate.md
	@test -f docs/design/sprint10-family-coverage.md
	@test -f docs/sprints/sprint-09-patch-042-validation.md
	@test -f docs/adr/0028-decoder-gap-evidence-and-portable-bundle-policy.md
	@test -f docs/adr/0029-decoder-free-default-and-campaign-transaction-safety.md
	@test -f docs/adr/0030-campaign-integrity-and-bounded-acceleration-gates.md
	@test -f docs/adr/0031-sprint9-closeout-and-defensive-deployment-profile.md
	@test -f docs/adr/0036-sprint10-effect-completion-and-fixture-gate-hardening.md
	@test -f docs/adr/0037-architectural-effects-and-contract-reconciliation.md
	@test -f docs/design/sprint10-exact-pattern-catalog.md
	@test -f docs/sprints/sprint-10-patch-051-validation.md
	@test -f docs/design/candidate-scoped-decoder-and-parallelism.md
	@test -f docs/design/defensive-deployment-profile.md
	@test -f docs/sprints/sprint-09-patch-044-validation.md
	@test -f docs/sprints/sprint-09-patch-045-validation.md
	@test -f docs/sprints/sprint-09-retro.md
	@test -f docs/sprints/sprint-09-patch-043-validation.md
	@test -f docs/sprints/sprint-10-patch-050-validation.md
	@echo "scaffold-check: ok"

diagrams-check:
	@test -f docs/diagrams/architecture-flow.mmd
	@test -f docs/diagrams/info-command-flow.mmd
	@test -f docs/diagrams/module-graph.dot
	@echo "diagrams-check: ok"

patch-bundle-hygiene:
	@test -n "$(BUNDLE)" || { echo "error: set BUNDLE=/path/to/patch.zip"; exit 2; }
	bash tools/check-patch-bundle-hygiene.sh "$(BUNDLE)"

docker-available-check:
	@command -v "$(DOCKER)" >/dev/null 2>&1 || { \
		echo "error: Docker command was not found. Enable Docker Desktop WSL integration or install Docker Engine."; \
		exit 127; \
	}
	@"$(DOCKER)" info >/dev/null 2>&1 || { \
		echo "error: Docker is installed but not reachable. Start Docker Desktop/Engine and retry."; \
		exit 127; \
	}
	@echo "docker-available-check: ok"

# Build only from an exact staged-index context. Ignored, untracked, generated,
# and private files never enter source/. The immutable image ID and candidate
# tree are published to an ignored authority; downstream targets never resolve
# the mutable repository tag again.
docker-build: docker-available-check
	@set -eu; \
	work="$$(mktemp -d "$${TMPDIR:-/tmp}/x64lens-docker-exact.XXXXXX")"; \
	context="$$work/context"; \
	trap 'rm -rf "$$work"' EXIT; \
	python3 tools/gitless-source-manifest.py create-context --repo . --context "$$context"; \
	tree="$$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["candidate_tree"])' "$$context/context-authority.json")"; \
	context_sha="$$(sha256sum "$$context/context-authority.json" | awk '{print $$1}')"; \
	source_sha="$$(sha256sum "$$context/source-manifest.json" | awk '{print $$1}')"; \
	"$(DOCKER)" build \
		--build-arg X64LENS_CANDIDATE_TREE="$$tree" \
		--build-arg X64LENS_CONTEXT_AUTHORITY_SHA256="$$context_sha" \
		--build-arg X64LENS_SOURCE_MANIFEST_SHA256="$$source_sha" \
		--label org.x64lens.candidate-tree="$$tree" \
		--label org.x64lens.context-authority-sha256="$$context_sha" \
		--label org.x64lens.source-manifest-sha256="$$source_sha" \
		-f "$$context/Dockerfile.transport" -t "$(DOCKER_IMAGE)" "$$context"; \
	python3 tools/docker-image-authority.py record \
		--path "$(DOCKER_IMAGE_AUTHORITY)" --docker "$(DOCKER)" \
		--tag "$(DOCKER_IMAGE)" --candidate-tree "$$tree" \
		--context-authority "$$context/context-authority.json"; \
	python3 tools/docker-image-authority.py verify --path "$(DOCKER_IMAGE_AUTHORITY)" --docker "$(DOCKER)"; \
	image_id="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field image_id)"; \
	"$(DOCKER)" run --rm -e HOME=/tmp -e X64LENS_CANDIDATE_TREE="$$tree" "$$image_id" \
		python3 /work/tools/gitless-source-manifest.py verify \
		--root /work --manifest /x64lens-source-manifest.json; \
	echo "docker-build: ok tree=$$tree image_id=$$image_id exact_context=1 immutable_authority=1"

docker-image-authority-smoke: docker-build
	@python3 tools/docker-image-authority.py verify --path "$(DOCKER_IMAGE_AUTHORITY)" --docker "$(DOCKER)"

docker-source-custody-smoke: docker-build
	@set -eu; \
	python3 tools/docker-image-authority.py verify --path "$(DOCKER_IMAGE_AUTHORITY)" --docker "$(DOCKER)"; \
	image_id="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field image_id)"; \
	tree="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field candidate_tree)"; \
	"$(DOCKER)" run --rm -e HOME=/tmp -e X64LENS_CANDIDATE_TREE="$$tree" "$$image_id" \
		python3 /work/tools/gitless-source-manifest.py verify \
		--root /work --manifest /x64lens-source-manifest.json

# Use the caller's numeric UID/GID when bind-mounting the repository. This
# interactive convenience target is not an acceptance path.
docker-shell: docker-available-check
	"$(DOCKER)" run --rm -it --user "$$(id -u):$$(id -g)" -e HOME=/tmp -v "$(PWD)":/work -w /work $(DOCKER_IMAGE) bash

# Reproducible tests preserve /work as the exact authenticated source plane.
# Generated objects and fixtures live in a distinct ephemeral run tree, while
# Git-less source-custody gates continue to verify the paired /work manifest.
docker-test: docker-build
	@set -eu; \
	python3 tools/docker-image-authority.py verify --path "$(DOCKER_IMAGE_AUTHORITY)" --docker "$(DOCKER)"; \
	image_id="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field image_id)"; \
	tree="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field candidate_tree)"; \
	"$(DOCKER)" run --rm -e HOME=/tmp -e X64LENS_CANDIDATE_TREE="$$tree" \
		-e X64LENS_SOURCE_MANIFEST=/x64lens-source-manifest.json \
		-e X64LENS_SOURCE_AUTHORITY_ROOT=/work "$$image_id" \
		bash -lc 'set -euo pipefail; run=/x64lens-run; rm -rf "$$run"; mkdir "$$run"; cp -a /work/. "$$run"/; chmod -R u+w "$$run"; cd "$$run"; make clean; make; make test; python3 /work/tools/gitless-source-manifest.py verify --root /work --manifest /x64lens-source-manifest.json'

native-docker-json-parity-smoke: docker-build all samples
	@set -eu; \
	image_id="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field image_id)"; \
	bash tools/native-docker-json-parity-smoke.sh "$$image_id" ./$(TARGET)

docker-context-hygiene-smoke: docker-available-check
	bash tools/docker-context-hygiene-smoke.sh "$(DOCKER_IMAGE)-context-hygiene"

# Full native-equivalent validation preserves the authenticated /work plane and
# performs all mutable build/test work in one separate ephemeral run tree.
docker-validation-smoke: docker-build docker-context-hygiene-smoke docker-source-custody-smoke
	@set -eu; \
	python3 tools/docker-image-authority.py verify --path "$(DOCKER_IMAGE_AUTHORITY)" --docker "$(DOCKER)"; \
	image_id="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field image_id)"; \
	tree="$$(python3 tools/docker-image-authority.py get --path "$(DOCKER_IMAGE_AUTHORITY)" --field candidate_tree)"; \
	"$(DOCKER)" run --rm -e HOME=/tmp -e X64LENS_CANDIDATE_TREE="$$tree" \
		-e X64LENS_SOURCE_MANIFEST=/x64lens-source-manifest.json \
		-e X64LENS_SOURCE_AUTHORITY_ROOT=/work "$$image_id" \
		bash -lc 'set -euo pipefail; run=/x64lens-run; rm -rf "$$run"; mkdir "$$run"; cp -a /work/. "$$run"/; chmod -R u+w "$$run"; cd "$$run"; make clean; make; make validation-smoke; python3 /work/tools/gitless-source-manifest.py verify --root /work --manifest /x64lens-source-manifest.json'

print-vars:
	@echo PROJECT=$(PROJECT)
	@echo VERSION=$(VERSION)
	@echo SCHEMA=$(SCHEMA)
	@echo ASM_SRCS=$(ASM_SRCS)
	@echo OBJS=$(OBJS)
	@echo MALFORMED_SEED=$(MALFORMED_SEED)
	@echo MALFORMED_TIMEOUT=$(MALFORMED_TIMEOUT)
	@echo MALFORMED_RESULTS_DIR=$(MALFORMED_RESULTS_DIR)
	@echo MITIGATION_MATRIX_RESULTS_DIR=$(MITIGATION_MATRIX_RESULTS_DIR)
	@echo SECTION_LABEL_RESULTS_DIR=$(SECTION_LABEL_RESULTS_DIR)
	@echo READELF_COMPARISON_RESULTS_DIR=$(READELF_COMPARISON_RESULTS_DIR)
	@echo OPTIONAL_TOOL_COMPARISON_RESULTS_DIR=$(OPTIONAL_TOOL_COMPARISON_RESULTS_DIR)
	@echo BENCHMARK_INTEGRITY_RESULTS_DIR=$(BENCHMARK_INTEGRITY_RESULTS_DIR)
	@echo DECODER_GAP_RESULTS_DIR=$(DECODER_GAP_RESULTS_DIR)
	@echo DIAGNOSTIC_RESULTS_DIR=$(DIAGNOSTIC_RESULTS_DIR)
	@echo DIAGNOSTIC_SPEC=$(DIAGNOSTIC_SPEC)
	@echo DIAGNOSTIC_CAMPAIGN_ID=$(DIAGNOSTIC_CAMPAIGN_ID)
	@echo PROVISIONAL_CORPUS_ROOT=$(PROVISIONAL_CORPUS_ROOT)
	@echo PROVISIONAL_CORPUS_SPEC=$(PROVISIONAL_CORPUS_SPEC)
	@echo PROVISIONAL_CORPUS_ID=$(PROVISIONAL_CORPUS_ID)
	@echo PROVISIONAL_CORPUS_PATH=$(PROVISIONAL_CORPUS_PATH)
	@echo ROLE_PROPERTY_HELDOUT_AUTHORITY=$(ROLE_PROPERTY_HELDOUT_AUTHORITY)
	@echo ROLE_PROPERTY_READELF_AUTHORITY=$(ROLE_PROPERTY_READELF_AUTHORITY)
	@echo ROLE_PROPERTY_BATCH_AUTHORITY=$(ROLE_PROPERTY_BATCH_AUTHORITY)
	@echo ROLE_PROPERTY_EXTERNAL_NATURAL_AUTHORITY=$(ROLE_PROPERTY_EXTERNAL_NATURAL_AUTHORITY)
	@echo PUBLIC_BUNDLE=$(PUBLIC_BUNDLE)
	@echo PUBLIC_BUNDLE_SHA256=$(PUBLIC_BUNDLE_SHA256)

ownership-check:
	@echo "Checking generated artifact ownership..."
	@bad="$$(find $(BUILD_DIR) tests/bin tests/toy-src -xdev \( -type f -o -type d \) ! -user "$$(id -u)" 2>/dev/null | head -n 20)"; \
	if [ -n "$$bad" ]; then \
		echo "error: generated files exist that are not owned by the current user:"; \
		echo "$$bad"; \
		echo ""; \
		echo "Most likely cause: Docker was run as root against a bind-mounted repo."; \
		echo "Fix once from WSL/Linux:"; \
		echo "  sudo chown -R $$(id -u):$$(id -g) build tests/bin tests/toy-src"; \
		echo "Then use: make docker-shell or make docker-test"; \
		exit 1; \
	else \
		echo "ownership-check: ok"; \
	fi

# Convenience target for local development machines. This intentionally
# touches only generated artifact locations and the toy-source directory
# where generated sample binaries are produced. It does not chown .git.
fix-perms:
	@echo "Repairing ownership of generated local artifacts..."
	@sudo chown -R "$$(id -u):$$(id -g)" $(BUILD_DIR) tests/bin tests/toy-src 2>/dev/null || true
	@echo "fix-perms: done"

# Normalize only Git-tracked file and parent-directory modes. The helper
# preflights every tracked pathname before mutation, touches no ignored or
# untracked object, and rolls back all changed modes if any chmod fails.
normalize-perms:
	@echo "Normalizing Git-tracked repository permissions..."
	@python3 tools/normalize-tracked-permissions.py --repo .
	@echo "normalize-perms: done"

clean:
	rm -rf $(BUILD_DIR)
	rm -rf tests/bin
	$(MAKE) -C tests/toy-src clean || true

clean-results:
	rm -rf tests/results benchmarks/results
	mkdir -p benchmarks/results
	touch benchmarks/results/.gitkeep
	@echo "clean-results: ok"
