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

.PHONY: all clean test samples bench-smoke check-tools scaffold-check print-vars docker-build docker-shell docker-test ownership-check fix-perms normalize-perms diagrams-check

all: check-tools $(TARGET)

check-tools:
	@command -v $(NASM) >/dev/null 2>&1 || { echo "error: nasm is required"; exit 127; }
	@command -v $(LD) >/dev/null 2>&1 || { echo "error: ld is required"; exit 127; }

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.asm | $(BUILD_DIR)
	$(NASM) $(ASMFLAGS) $< -o $@

$(TARGET): $(OBJS)
	$(LD) $(LDFLAGS) -o $@ $(OBJS)

samples:
	$(MAKE) -C tests/toy-src
	mkdir -p tests/bin
	cp tests/toy-src/minimal_nopie tests/bin/ 2>/dev/null || true
	cp tests/toy-src/minimal_pie_canary tests/bin/ 2>/dev/null || true
	cp tests/toy-src/minimal_execstack tests/bin/ 2>/dev/null || true
	cp tests/toy-src/gadgets tests/bin/ 2>/dev/null || true

test: all samples
	bash tests/run-tests.sh

bench-smoke: all
	bash benchmarks/scripts/bench-x64lens.sh ./$(TARGET) ./$(TARGET)

scaffold-check:
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
	@echo "scaffold-check: ok"

diagrams-check:
	@test -f docs/diagrams/architecture-flow.mmd
	@test -f docs/diagrams/info-command-flow.mmd
	@test -f docs/diagrams/module-graph.dot
	@echo "diagrams-check: ok"

docker-build:
	docker build -t $(DOCKER_IMAGE) .

# Use the caller's numeric UID/GID when bind-mounting the repository.
# This prevents root-owned build artifacts when Docker Desktop or Docker
# Engine runs container processes as root by default. HOME=/tmp avoids
# tools trying to write into a missing or unwritable home directory when
# Docker receives a numeric user id.
docker-shell:
	docker run --rm -it --user "$$(id -u):$$(id -g)" -e HOME=/tmp -v "$(PWD)":/work -w /work $(DOCKER_IMAGE) bash

# Reproducible smoke test inside Docker without leaving root-owned files.
# Run `make docker-build` first after Dockerfile or dependency changes.
docker-test:
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
	@chmod 755 tests/run-tests.sh tools/*.sh benchmarks/scripts/*.sh 2>/dev/null || true
	@echo "normalize-perms: done"

clean:
	rm -rf $(BUILD_DIR)
	rm -rf tests/bin
	$(MAKE) -C tests/toy-src clean || true
