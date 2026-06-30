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
SCHEMA       := 0.1.0
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

NASM         ?= nasm
LD           ?= ld
CC           ?= gcc

ASMFLAGS     := -f elf64 -g -F dwarf -I$(INC_DIR)/
LDFLAGS      :=

ASM_SRCS     := $(wildcard $(SRC_DIR)/*.asm)
OBJS         := $(patsubst $(SRC_DIR)/%.asm,$(BUILD_DIR)/%.o,$(ASM_SRCS))

.DEFAULT_GOAL := all

.PHONY: help all clean test samples bench-smoke bench-scanner-smoke bench-baselines-smoke bench-summary bench-summary-latest checkpoint-demo checkpoint-tag-help public-docs-check planning-docs-check scanner-smoke validate-gadget-fixture arena-smoke pattern-smoke semantic-smoke json-smoke analyze-smoke system-smoke capacity-smoke malformed-smoke fuzz-mutated-elf-smoke mitigation-matrix-smoke validation-smoke check-tools build-tools-check sample-tools-check dev-tools-check baseline-tools-check full-tools-check doctor install-dev-deps-ubuntu install-baseline-tools-user install-rustup-user install-ropr-user scaffold-check script-perms-check patch-bundle-hygiene print-vars docker-available-check docker-build docker-shell docker-test docker-validation-smoke ownership-check fix-perms normalize-perms diagrams-check

help:
	@echo "x64lens development targets"
	@echo "  make                     Build x64lens"
	@echo "  make samples             Build controlled test fixtures"
	@echo "  make test                Run the core regression suite"
	@echo "  make validation-smoke    Run the complete native validation aggregate"
	@echo "  make mitigation-matrix-smoke  Run the deterministic mitigation oracle"
	@echo "  make malformed-smoke     Run deterministic malformed-input smoke"
	@echo "  make fuzz-mutated-elf-smoke  Compatibility alias for malformed smoke"
	@echo "  make capacity-smoke      Validate exact and overflow candidate capacity"
	@echo "  make checkpoint-demo     Run the integrated checkpoint demonstration"
	@echo "  make bench-scanner-smoke Run scanner benchmark smoke measurements"
	@echo "  make bench-baselines-smoke  Compare optional baseline tools"
	@echo "  make docker-build        Build the development image"
	@echo "  make docker-test         Run the core suite in Docker"
	@echo "  make docker-validation-smoke  Run complete validation in Docker"
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

baseline-tools-check:
	bash tools/check-dev-tools.sh --baselines

full-tools-check:
	REQUIRE_BASELINES=1 bash tools/check-dev-tools.sh --all

doctor:
	bash tools/check-dev-tools.sh --doctor

install-dev-deps-ubuntu:
	sudo apt update
	sudo apt install -y nasm binutils gcc gdb make python3 python3-venv python3-pip pipx time git curl ca-certificates unzip zip
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

samples: sample-tools-check
	$(MAKE) -C tests/toy-src
	mkdir -p tests/bin
	cp tests/toy-src/minimal_nopie tests/bin/ 2>/dev/null || true
	cp tests/toy-src/minimal_pie_canary tests/bin/ 2>/dev/null || true
	cp tests/toy-src/minimal_execstack tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets tests/bin/ 2>/dev/null || true
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
	@./$(TARGET) gadgets --format json --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-json-smoke.json
	@python3 -m json.tool /tmp/x64lens-json-smoke.json >/dev/null
	@python3 tools/validate-json-report.py --mode fixture /tmp/x64lens-json-smoke.json >/dev/null
	@./$(TARGET) gadgets --max-depth 4 --format json ./tests/bin/gadgets > /tmp/x64lens-json-smoke-order2.json
	@python3 tools/validate-json-report.py --mode fixture /tmp/x64lens-json-smoke-order2.json >/dev/null
	@echo "json-smoke: ok"


# Sprint 6 integrated analyze smoke target. This verifies that analyze combines
# target metadata, mitigation facts, raw candidates, semantic facts, scoring,
# and JSON report shape without changing the underlying scanner contract.
analyze-smoke: dev-tools-check all samples
	@./$(TARGET) analyze --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-analyze-smoke.txt
	@grep -q "Format:" /tmp/x64lens-analyze-smoke.txt
	@grep -q "Mitigations:" /tmp/x64lens-analyze-smoke.txt
	@grep -q "Raw gadget candidates:" /tmp/x64lens-analyze-smoke.txt
	@grep -q "Candidate count: 0x000000000000000b" /tmp/x64lens-analyze-smoke.txt
	@grep -q "Scored candidate count: 0x000000000000000b" /tmp/x64lens-analyze-smoke.txt
	@./$(TARGET) analyze --format json --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-analyze-smoke.json
	@python3 tools/validate-json-report.py --mode fixture /tmp/x64lens-analyze-smoke.json >/dev/null
	@./$(TARGET) analyze --max-depth 4 --format json ./tests/bin/gadgets > /tmp/x64lens-analyze-smoke-order2.json
	@python3 tools/validate-json-report.py --mode fixture /tmp/x64lens-analyze-smoke-order2.json >/dev/null
	@echo "analyze-smoke: ok"

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
# expected loader-level facts before parser arithmetic is refactored. Five
# malformed program-header cases must fail identically across info,
# mitigations, and analyze.
mitigation-matrix-smoke: dev-tools-check all samples
	python3 tools/mitigation-matrix-smoke.py \
		--binary ./$(TARGET) \
		--seed "$(MALFORMED_SEED)" \
		--timeout "$(MALFORMED_TIMEOUT)" \
		--results-dir "$(MITIGATION_MATRIX_RESULTS_DIR)"

# Local pre-commit validation bundle. Docker remains a separate reproducibility
# check because Docker Desktop/Engine availability is environment-dependent.
validation-smoke: script-perms-check scaffold-check diagrams-check public-docs-check planning-docs-check test validate-gadget-fixture semantic-smoke json-smoke analyze-smoke system-smoke capacity-smoke malformed-smoke mitigation-matrix-smoke
	@echo "validation-smoke: ok"

# Arena smoke target. It exercises the gadgets command path after candidate
# storage moved from static .bss memory to an mmap-backed arena. The expected
# counts follow the current controlled gadget fixture.
arena-smoke: all samples
	@./$(TARGET) gadgets --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-arena-smoke.txt
	@grep -q "Candidate capacity: 0x0000000000001000" /tmp/x64lens-arena-smoke.txt
	@grep -q "Candidate count: 0x000000000000000b" /tmp/x64lens-arena-smoke.txt
	@grep -q "ret imm16 count: 0x0000000000000001" /tmp/x64lens-arena-smoke.txt
	@grep -q "Exact pattern count: 0x000000000000000b" /tmp/x64lens-arena-smoke.txt
	@grep -q "Scored candidate count: 0x000000000000000b" /tmp/x64lens-arena-smoke.txt
	@echo "arena-smoke: ok"

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

checkpoint-demo: dev-tools-check all samples
	bash tools/demo-checkpoint.sh ./$(TARGET) "$(DEMO_TARGET)"

# Summarize only the newest baseline smoke artifact. This avoids accidentally
# combining separate development environments or historical runs.
bench-summary-latest:
	@file="$$(ls -1t benchmarks/results/baseline-smoke-*.tsv 2>/dev/null | head -n 1)"; \
	if [ -z "$$file" ]; then \
		file="$$(ls -1t benchmarks/results/*.tsv 2>/dev/null | head -n 1)"; \
	fi; \
	if [ -z "$$file" ]; then \
		echo "error: no benchmark TSV files found under benchmarks/results"; \
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

bench-summary:
	@files="$$(ls benchmarks/results/*.tsv 2>/dev/null || true)"; \
	if [ -z "$$files" ]; then \
		echo "error: no benchmark TSV files found under benchmarks/results"; \
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
	@test -x benchmarks/scripts/bench-x64lens.sh
	@test -x tools/compare-checksec.sh
	@test -x tools/compare-objdump.sh
	@test -x tools/compare-readelf.sh
	@test -x tools/compare-ropgadget.sh
	@test -x tools/make-release-artifacts.sh
	@test -x tools/validate-gadget-fixture.sh
	@test -x tools/validate-json-report.py
	@test -x tools/system-binary-smoke.sh
	@test -x tools/check-patch-bundle-hygiene.sh
	@test -x tools/check-dev-tools.sh
	@test -x tools/install-ropr-user.sh
	@test -x tools/demo-checkpoint.sh
	@test -x tools/check-public-docs.sh
	@test -x tools/check-planning-docs.sh
	@test -x tools/malformed-elf-smoke.py
	@test -x tools/fuzz-mutated-elf-smoke.sh
	@test -x tools/validate-capacity-fixture.sh
	@test -x tools/mitigation-matrix-smoke.py
	@echo "script-perms-check: ok"

scaffold-check: script-perms-check
	@echo "Checking required scaffold paths..."
	@test -f README.md
	@test -f Makefile
	@test -f src/main.asm
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
	@test -f docs/design/mitigation-fixture-matrix.md
	@test -f docs/sprints/sprint-07-patch-026-validation.md
	@test -f docs/sprints/sprint-07-patch-027-validation.md
	@test -f docs/sprints/sprint-07-patch-028-validation.md
	@test -f tests/malformed/README.md
	@test -f tests/malformed/regressions/README.md
	@test -f tests/malformed/regressions/elf64-shentsize-63.bin
	@test -f docs/roadmap-18-sprints.md
	@test -f docs/research-release-plan.md
	@test -f docs/design/evidence-provenance-model.md
	@test -f docs/design/schema-evolution.md
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

# Full native-equivalent validation inside the reproducible container,
# including deterministic malformed-input and candidate-capacity smoke tests.
docker-validation-smoke: docker-build
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
