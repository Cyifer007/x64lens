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

NASM         ?= nasm
LD           ?= ld
CC           ?= gcc

ASMFLAGS     := -f elf64 -g -F dwarf -I$(INC_DIR)/
LDFLAGS      :=

ASM_SRCS     := $(wildcard $(SRC_DIR)/*.asm)
OBJS         := $(patsubst $(SRC_DIR)/%.asm,$(BUILD_DIR)/%.o,$(ASM_SRCS))

.PHONY: all clean test samples bench-smoke bench-scanner-smoke bench-baselines-smoke bench-summary scanner-smoke validate-gadget-fixture arena-smoke pattern-smoke semantic-smoke json-smoke system-smoke validation-smoke check-tools build-tools-check sample-tools-check dev-tools-check baseline-tools-check full-tools-check doctor install-dev-deps-ubuntu install-baseline-tools-user install-rustup-user install-ropr-user scaffold-check script-perms-check patch-bundle-hygiene print-vars docker-available-check docker-build docker-shell docker-test ownership-check fix-perms normalize-perms diagrams-check

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

# Real-binary smoke target. This runs the current pipeline against installed
# system ELF64 binaries and validates shape/invariants rather than brittle,
# distribution-specific candidate counts.
system-smoke: dev-tools-check all
	bash tools/system-binary-smoke.sh ./$(TARGET)

# Local pre-commit validation bundle. Docker remains a separate reproducibility
# check because Docker Desktop/Engine availability is environment-dependent.
validation-smoke: script-perms-check scaffold-check diagrams-check test validate-gadget-fixture semantic-smoke json-smoke system-smoke
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

print-vars:
	@echo PROJECT=$(PROJECT)
	@echo VERSION=$(VERSION)
	@echo SCHEMA=$(SCHEMA)
	@echo ASM_SRCS=$(ASM_SRCS)
	@echo OBJS=$(OBJS)

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
		-path ./build -prune -o \
		-path ./tests/bin -prune -o \
		-type d -exec chmod 755 {} +
	@find . \
		-path ./.git -prune -o \
		-path ./.local -prune -o \
		-path ./build -prune -o \
		-path ./tests/bin -prune -o \
		-type f -exec chmod 644 {} +
	@chmod 755 tests/run-tests.sh tools/*.sh tools/*.py benchmarks/scripts/*.sh benchmarks/scripts/*.py 2>/dev/null || true
	@echo "normalize-perms: done"

clean:
	rm -rf $(BUILD_DIR)
	rm -rf tests/bin
	$(MAKE) -C tests/toy-src clean || true
