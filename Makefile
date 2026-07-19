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
#   - gcc is used only for compiling toy corpus binaries under tests/.
#   - `make scaffold-check` verifies repository structure before deeper work.

PROJECT      := x64lens
VERSION      := 0.1.0-dev
SCHEMA       := 0.2.0
DOCKER_IMAGE ?= x64lens-dev
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
PUBLIC_BUNDLE ?=
PUBLIC_BUNDLE_SHA256 ?=
INTERNAL_TEST_BUILD_DIR := $(BUILD_DIR)/tests
MEMORY_EFFECT_RECONCILIATION_OBJ := $(INTERNAL_TEST_BUILD_DIR)/memory-effect-reconciliation.o
MEMORY_EFFECT_RECONCILIATION_BIN := $(INTERNAL_TEST_BUILD_DIR)/memory-effect-reconciliation

NASM         ?= nasm
LD           ?= ld
CC           ?= gcc

ASMFLAGS     := -f elf64 -g -F dwarf -Werror=number-overflow -I$(INC_DIR)/
LDFLAGS      :=

ASM_SRCS     := $(wildcard $(SRC_DIR)/*.asm)
OBJS         := $(patsubst $(SRC_DIR)/%.asm,$(BUILD_DIR)/%.o,$(ASM_SRCS))

.DEFAULT_GOAL := all

.PHONY: help all clean test samples bench-smoke bench-scanner-smoke bench-baselines-smoke bench-diagnostic-smoke bench-summary bench-summary-latest checkpoint-demo checkpoint-tag-help public-docs-check public-artifact-content-smoke public-bundle-content-check public-overlay-verify public-overlay-verification-smoke planning-docs-check research-stage-gates-smoke research-roadmap-consistency-smoke sprint10-closeout-smoke patch054-corrective-regression-smoke diagnostic-runner-smoke diagnostic-task-definitions-smoke sprint11-diagnostic-reference-smoke checksum-manifest-path-smoke scanner-smoke validate-gadget-fixture arena-smoke pattern-smoke semantic-smoke json-smoke schema-compat-smoke analyze-smoke system-smoke capacity-smoke malformed-smoke fuzz-mutated-elf-smoke mitigation-matrix-smoke section-label-smoke readelf-comparison-smoke optional-tool-comparison-smoke benchmark-integrity-smoke patch-bundle-hygiene-smoke sprint10-primitive-smoke sprint10-register-transfer-smoke sprint10-stack-adjust-smoke sprint10-memory-smoke sprint10-family-coverage-smoke sprint10-architectural-effects-smoke sprint10-fixture-gate-smoke sprint10-contract-reconciliation-smoke sprint10-score-policy-smoke memory-effect-reconciliation-smoke shellcheck-contract-smoke json-effect-consistency-smoke public-docs-hygiene-smoke decoder-gap-hardening-smoke decoder-gap-smoke decoder-gap-campaign shellcheck-smoke docker-context-hygiene-smoke native-docker-json-parity-smoke validation-smoke sprint-closeout-smoke clean-results check-tools build-tools-check sample-tools-check dev-tools-check diagnostic-tools-check baseline-tools-check analysis-tools-check full-tools-check doctor install-dev-deps-ubuntu install-baseline-tools-user install-rustup-user install-ropr-user scaffold-check script-perms-check patch-bundle-hygiene print-vars docker-available-check docker-build docker-shell docker-test docker-validation-smoke ownership-check fix-perms normalize-perms diagrams-check

help:
	@echo "x64lens development targets"
	@echo "  make                     Build x64lens"
	@echo "  make samples             Build controlled test fixtures"
	@echo "  make test                Run the core regression suite"
	@echo "  make validation-smoke    Run the complete native validation aggregate"
	@echo "  make sprint-closeout-smoke  Require strict shell lint, then run validation-smoke"
	@echo "  make mitigation-matrix-smoke  Run the deterministic mitigation oracle"
	@echo "  make section-label-smoke  Run section-label annotation hardening probes"
	@echo "  make readelf-comparison-smoke  Compare metadata and loader facts against readelf"
	@echo "  make optional-tool-comparison-smoke  Run optional checksec/rabin2 comparison helpers"
	@echo "  make benchmark-integrity-smoke  Validate benchmark TSV input hygiene"
	@echo "  make diagnostic-tools-check  Validate only build, sample, and standard-library runner tools"
	@echo "  make diagnostic-runner-smoke  Validate high-resolution runner provenance, timing, and failure retention"
	@echo "  make diagnostic-task-definitions-smoke  Validate truthful Sprint 11 task scopes"
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
	sudo apt install -y nasm binutils gcc gdb make python3 python3-jsonschema python3-venv python3-pip pipx time git curl ca-certificates unzip zip
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

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.asm | $(BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(TARGET): $(OBJS)
	$(LD) $(LDFLAGS) -o $@ $(OBJS)

$(INTERNAL_TEST_BUILD_DIR):
	mkdir -p $(INTERNAL_TEST_BUILD_DIR)

$(MEMORY_EFFECT_RECONCILIATION_OBJ): tests/internal/memory-effect-reconciliation.asm | $(INTERNAL_TEST_BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(MEMORY_EFFECT_RECONCILIATION_BIN): $(MEMORY_EFFECT_RECONCILIATION_OBJ) $(BUILD_DIR)/candidate_effect.o
	$(LD) $(LDFLAGS) -o $@ $^

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
sprint-closeout-smoke:
	@command -v "$(SHELLCHECK)" >/dev/null 2>&1 || { \
		echo "error: sprint-closeout-smoke requires $(SHELLCHECK)" >&2; \
		exit 127; \
	}
	@SHELLCHECK_STRICT=1 $(MAKE) --no-print-directory shellcheck-smoke
	@$(MAKE) --no-print-directory validation-smoke
	@echo "sprint-closeout-smoke: ok"

# Local pre-commit validation bundle. Docker remains a separate reproducibility
# check because Docker Desktop/Engine availability is environment-dependent.
validation-smoke: script-perms-check scaffold-check diagrams-check public-docs-check public-docs-hygiene-smoke public-artifact-content-smoke public-overlay-verification-smoke planning-docs-check research-stage-gates-smoke research-roadmap-consistency-smoke sprint10-closeout-smoke patch054-corrective-regression-smoke diagnostic-runner-smoke diagnostic-task-definitions-smoke sprint11-diagnostic-reference-smoke checksum-manifest-path-smoke benchmark-integrity-smoke patch-bundle-hygiene-smoke schema-compat-smoke decoder-gap-hardening-smoke decoder-gap-smoke test validate-gadget-fixture semantic-smoke sprint10-primitive-smoke sprint10-register-transfer-smoke sprint10-stack-adjust-smoke sprint10-memory-smoke sprint10-family-coverage-smoke sprint10-architectural-effects-smoke sprint10-fixture-gate-smoke sprint10-contract-reconciliation-smoke sprint10-score-policy-smoke memory-effect-reconciliation-smoke shellcheck-contract-smoke json-effect-consistency-smoke json-smoke analyze-smoke system-smoke capacity-smoke malformed-smoke mitigation-matrix-smoke section-label-smoke readelf-comparison-smoke optional-tool-comparison-smoke
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

patch054-corrective-regression-smoke:
	python3 tools/patch054-corrective-regression-smoke.py

diagnostic-runner-smoke:
	python3 tools/diagnostic-runner-smoke.py

diagnostic-task-definitions-smoke:
	python3 tools/diagnostic-task-definitions-smoke.py

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
	@test -x tools/shellcheck-contract-smoke.py
	@test -f tests/internal/memory-effect-reconciliation.asm
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
	@test -x tools/patch054-corrective-regression-smoke.py
	@test -x tools/diagnostic-runner-smoke.py
	@test -x tools/diagnostic-task-definitions-smoke.py
	@test -x tools/sprint11-diagnostic-reference-smoke.py
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
	@test -f benchmarks/specs/sprint11-reference-diagnostic.json
	@test -f benchmarks/task-definitions/sprint11-diagnostic-tasks.json
	@test -f docs/design/diagnostic-benchmark-task-definitions.md
	@test -f docs/adr/0041-sprint11-diagnostic-runner-foundation.md
	@test -f docs/sprints/sprint-11-patch-055-validation.md
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
	@command -v docker >/dev/null 2>&1 || { \
		echo "error: docker command was not found. Enable Docker Desktop WSL integration or install Docker Engine."; \
		exit 127; \
	}
	@docker info >/dev/null 2>&1 || { \
		echo "error: Docker is installed but not reachable. Start Docker Desktop/Engine and retry."; \
		exit 127; \
	}
	@echo "docker-available-check: ok"

docker-build: docker-available-check
	docker build -t $(DOCKER_IMAGE) .

# Use the caller's numeric UID/GID when bind-mounting the repository.
# This prevents root-owned build artifacts when Docker Desktop or Docker
# Engine runs container processes as root by default. HOME=/tmp avoids
# tools trying to write into a missing or unwritable home directory when
# Docker receives a numeric user id.
docker-shell: docker-available-check
	docker run --rm -it --user "$$(id -u):$$(id -g)" -e HOME=/tmp -v "$(PWD)":/work -w /work $(DOCKER_IMAGE) bash

# Reproducible smoke test inside Docker without leaving root-owned files.
# docker-test depends on docker-build so Dockerfile dependency changes are not
# accidentally tested against a stale local image. Docker layer caching keeps
# repeat runs fast once the image is current.
docker-test: docker-build
	docker run --rm --user "$$(id -u):$$(id -g)" -e HOME=/tmp -v "$(PWD)":/work -w /work $(DOCKER_IMAGE) bash -lc 'make clean && make && make test'

native-docker-json-parity-smoke: docker-build all samples
	bash tools/native-docker-json-parity-smoke.sh "$(DOCKER_IMAGE)" ./$(TARGET)

docker-context-hygiene-smoke: docker-available-check
	bash tools/docker-context-hygiene-smoke.sh "$(DOCKER_IMAGE)-context-hygiene"

# Full native-equivalent validation inside the reproducible container,
# including deterministic malformed-input and candidate-capacity smoke tests.
docker-validation-smoke: docker-build docker-context-hygiene-smoke
	docker run --rm --user "$$(id -u):$$(id -g)" -e HOME=/tmp -v "$(PWD)":/work -w /work $(DOCKER_IMAGE) bash -lc 'make clean && make && make validation-smoke'

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

# Normalize local file permissions after extracting patch bundles on Linux/WSL.
# Some ZIP tools preserve permissive archive modes such as 0666/0777. Git only
# tracks the executable bit, but local world-writable source files are noisy and
# should be corrected before development continues. This target avoids .git,
# build outputs, generated test binaries, and local-only project context.
normalize-perms:
	@echo "Normalizing local repository file permissions..."
	@find . \
		-path ./.git -prune -o \
		-path ./.local -prune -o \
		-path ./.codex -prune -o \
		-path ./.agents -prune -o \
		-path ./build -prune -o \
		-path ./tests/bin -prune -o \
		-type d -exec chmod 755 {} +
	@find . \
		-path ./.git -prune -o \
		-path ./.local -prune -o \
		-path ./.codex -prune -o \
		-path ./.agents -prune -o \
		-path ./build -prune -o \
		-path ./tests/bin -prune -o \
		-type f -exec chmod 644 {} +
	@chmod 755 tests/run-tests.sh tools/*.sh tools/*.py benchmarks/scripts/*.sh benchmarks/scripts/*.py 2>/dev/null || true
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
