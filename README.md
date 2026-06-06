# x64lens

**x64lens is an assembly-first ELF64 x86_64 binary analysis tool that identifies exploit-relevant code primitives, classifies their semantic usefulness, evaluates mitigation context, and produces reproducible reports for offensive research, defensive triage, and binary hardening assessment.**

> Status: research scaffold, CSC-732 tool-development foundation and CSC-773 IEEE research-paper foundation.
>
> Current version: `0.1.0-dev`
>
> Output schema version: `0.1.0`

## Why this project exists

x64lens starts from a narrow but deliberate premise: build the hot path of binary exploitability analysis from the assembly layer upward. The first semester target is not a full replacement for ROPgadget, Ropper, radare2, Ghidra, angr, or other mature frameworks. Instead, the goal is to build a focused, transparent, fast, and research-measurable analyzer that performs:

1. ELF64 x86_64 parsing.
2. Executable region discovery.
3. Gadget candidate scanning.
4. Semantic primitive classification.
5. Mitigation-aware exploitability interpretation.
6. Reproducible text and JSON reporting.
7. Benchmark comparisons against existing tooling.

The design intentionally separates the **speed-first scanning engine** from the **semantic exploitability value layer**.



## Course deliverable split

This repository supports one unified project across two courses:

- **CSC-732 Assembly Language:** implementation deliverable. The focus is NASM, ELF64 parsing, executable region analysis, gadget scanning, semantic primitive classification, testing, and technical demonstration.
- **CSC-773 Advanced Network Security and Mobile Communications:** research deliverable. The focus is an IEEE-style 5 to 6 page paper that identifies a cyberinfrastructure security issue, develops a mitigation-oriented solution, and evaluates that solution through testing, benchmarking, and analysis.

The CSC-773 framing is:

> Static binary exploitability analysis for network-facing cyberinfrastructure and infrastructure software.

The tool-development work and paper-development work share the same technical core but produce different course artifacts.

## Project context persistence

Future chat sessions should load the project context files before making architecture or implementation decisions:

- [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md)
- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`docs/contracts/development-contract.md`](docs/contracts/development-contract.md)
- [`docs/contracts/research-contract.md`](docs/contracts/research-contract.md)
- [`docs/contracts/context-persistence-contract.md`](docs/contracts/context-persistence-contract.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/csc-773-integration.md`](docs/csc-773-integration.md)

These files are part of the project, not side notes. They are updated as the implementation evolves.

## Research questions

### RQ1: performance

Can an assembly-first ELF64 x86_64 gadget discovery engine outperform existing ROP gadget tooling in runtime and memory efficiency while maintaining comparable gadget discovery coverage?

### RQ2: semantic value

Can semantic primitive classification and mitigation-aware scoring provide more actionable binary exploitability triage than raw gadget enumeration alone?

### RQ3: enterprise adoption

Can a static, dependency-light, assembly-first binary analyzer be integrated into enterprise CI/CD or vulnerability management workflows to help prioritize binaries based on hardening posture and exploit primitive availability?

## Initial scope

Version `0.1.x` targets:

- ELF64.
- x86_64.
- Linux.
- Static local binary analysis.
- NASM-first implementation.
- Pattern-based gadget discovery.
- Human-readable and JSON output.
- Controlled benchmark comparisons.

## Explicit non-goals for the first semester

The first semester does **not** attempt to provide:

- Full exploit generation.
- Payload generation.
- Remote target interaction.
- Malware deployment or execution.
- A full x86_64 instruction decoder.
- Symbolic execution.
- Multi-architecture support.
- Dynamic tracing.
- Automatic vulnerability discovery.

Those may become future research directions, but they are not Sprint 1 through Sprint 6 deliverables.

## Tool name decision

The name `x64lens` is intentionally narrow for the first major phase. The tool begins as a lens into x86_64 ELF binaries. If the project later grows into a multi-architecture platform, architecture-specific engines can be added under the same repository, or the project can later adopt a broader umbrella name. For now, `x64lens` keeps the initial research contribution precise, searchable, and technically honest.

See [`docs/adr/0001-tool-name.md`](docs/adr/0001-tool-name.md).

## Current CLI contract

Planned early commands:

```bash
x64lens info <file>
x64lens mitigations <file>
x64lens gadgets <file>
x64lens analyze <file>
x64lens bench <file>
x64lens version
```

Planned early global flags:

```bash
--format text|json
--max-depth <N>
--badbytes <hex-list>
--quiet
--verbose
--no-color
--schema-version
```

See [`docs/cli-contract.md`](docs/cli-contract.md).

## Build

### Requirements

- Linux x86_64.
- `make`.
- `nasm`.
- GNU `ld` from binutils.
- `gcc`, only for test corpus compilation.

### Build command

```bash
make
```

### Run the current scaffold

```bash
./build/x64lens version
./build/x64lens help
./build/x64lens info ./tests/toy-src/minimal.c
```

The initial `info` command is scaffolded. Sprint 1 implements file mapping and ELF64 validation.

### Run tests

```bash
make test
```

## Development cadence

This project follows a two-week sprint cadence during CSC-732 and feeds the CSC-773 IEEE-format research paper deliverable.

1. Sprint 1: repository, build system, CLI skeleton, file mapping, ELF64 validation.
2. Sprint 2: program headers, executable regions, basic mitigations.
3. Sprint 3: raw gadget candidate scanner and initial arena allocator.
4. Sprint 4: semantic primitive classifier and primitive coverage summary.
5. Sprint 5: scoring, JSON output, benchmark harness, comparison tooling.
6. Sprint 6: final analyzer, documentation, benchmark results, research paper outline.

See [`docs/sprints/`](docs/sprints/).

## Example target output

```text
x64lens 0.1.0
Target: ./toy

Format:
  Type: ELF64
  Endian: little
  Machine: x86_64
  Entry: 0x401050

Executable regions:
  [0] VA 0x401000-0x402000, file offset 0x1000-0x2000, perms R-X

Mitigations:
  NX stack: enabled
  PIE: disabled
  RELRO: partial
  Canary indicator: not found
  RWX load segment: no

Primitive coverage:
  rdi control: yes, 3 candidates
  rsi control: yes, 2 candidates
  rdx control: no
  rax control: yes, 1 candidate
  syscall trigger: no
  stack pivot: yes, 1 candidate

Interpretation:
  NX blocks direct stack shellcode under normal conditions.
  PIE is disabled, so static code addresses are more stable.
  Direct syscall-oriented ROP appears incomplete because no syscall trigger was found.
  ret2libc-style analysis may be plausible if RIP control exists and libc/base information is available.
```

## Ethics and safety

x64lens is intended for educational research, defensive binary triage, secure build validation, and authorized reverse engineering. It does not include exploit delivery, payload generation, remote scanning, or unauthorized target interaction.

See [`docs/ethics-and-safety.md`](docs/ethics-and-safety.md).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
