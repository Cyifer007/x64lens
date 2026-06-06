# x64lens build contract
#
# Purpose:
#   Build the NASM assembly sources into ELF64 object files and link them
#   into the `build/x64lens` executable. This Makefile is intentionally
#   boring and explicit because it is part of the reproducibility story for
#   CSC-732, CSC-773, and future publication work.
#
# Design notes:
#   - NASM emits ELF64 objects.
#   - GNU ld links directly, without libc.
#   - gcc is used only for compiling toy corpus binaries under tests/.
#   - `make scaffold-check` verifies repository structure before deeper work.

PROJECT      := x64lens
VERSION      := 0.1.0-dev
SCHEMA       := 0.1.0
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

.PHONY: all clean test samples bench-smoke check-tools scaffold-check print-vars docker-build docker-shell diagrams-check

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
	cp tests/toy-src/gadgets tests/bin/ 2>/dev/null || true

test: all samples
	bash tests/run-tests.sh

bench-smoke: all
	bash benchmarks/scripts/bench-x64lens.sh ./$(TARGET) ./$(TARGET)

scaffold-check:
	@echo "Checking required scaffold paths..."
	@test -f README.md
	@test -f PROJECT_CONTEXT.md
	@test -f PROJECT_STATE.md
	@test -f Makefile
	@test -f src/main.asm
	@test -f include/constants.inc
	@test -f docs/project-charter.md
	@test -f docs/contracts/development-contract.md
	@test -f docs/contracts/context-persistence-contract.md
	@test -f docs/csc-773-integration.md
	@test -f docs/environment.md
	@test -f docs/visualization.md
	@echo "scaffold-check: ok"

diagrams-check:
	@test -f docs/diagrams/architecture-flow.mmd
	@test -f docs/diagrams/info-command-flow.mmd
	@test -f docs/diagrams/module-graph.dot
	@echo "diagrams-check: ok"

docker-build:
	docker build -t x64lens-dev .

docker-shell:
	docker run --rm -it -v "$(PWD)":/work x64lens-dev bash

print-vars:
	@echo PROJECT=$(PROJECT)
	@echo VERSION=$(VERSION)
	@echo SCHEMA=$(SCHEMA)
	@echo ASM_SRCS=$(ASM_SRCS)
	@echo OBJS=$(OBJS)

clean:
	rm -rf $(BUILD_DIR)
	$(MAKE) -C tests/toy-src clean || true
