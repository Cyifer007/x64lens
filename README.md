# x64lens

**x64lens is an assembly-first ELF64 x86_64 binary analysis tool that identifies exploit-relevant code primitives, classifies their semantic usefulness, evaluates mitigation context, and produces reproducible reports for offensive research, defensive triage, and binary hardening assessment.**

> Status: Sprint 3 in progress. Sprints 1 and 2 are complete. Patch 008 begins the raw gadget scanner with fixed-capacity candidate records, `ret` and `ret imm16` discovery, bounded backward byte windows, and the initial `gadgets` command path.
>
> Current version: `0.1.0-dev`
>
> Output schema version: `0.1.0`

## Why this project exists

x64lens starts from a narrow but deliberate premise: build the hot path of binary exploitability analysis from the assembly layer upward. The initial target is not a full replacement for ROPgadget, Ropper, radare2, Ghidra, angr, or other mature frameworks. Instead, the goal is to build a focused, transparent, fast, and research-measurable analyzer that performs:

1. ELF64 x86_64 parsing.
2. Executable region discovery.
3. Gadget candidate scanning.
4. Semantic primitive classification.
5. Mitigation-aware exploitability interpretation.
6. Reproducible text and JSON reporting.
7. Benchmark comparisons against existing tooling.

The design intentionally separates the **speed-first scanning engine** from the **semantic exploitability value layer**.

## Research framing

The project evaluates whether a dependency-light, assembly-first analyzer can improve static binary exploitability triage for network-facing infrastructure software, secure build validation, and binary hardening assessment.

Primary research questions:

1. **Performance:** Can an assembly-first ELF64 x86_64 gadget discovery engine outperform existing ROP gadget tooling in runtime and memory efficiency while maintaining comparable gadget discovery coverage?
2. **Semantic value:** Can semantic primitive classification and mitigation-aware scoring provide more actionable binary exploitability triage than raw gadget enumeration alone?
3. **Enterprise adoption:** Can a static, dependency-light, assembly-first binary analyzer be integrated into CI/CD or vulnerability management workflows to help prioritize binaries based on hardening posture and exploit primitive availability?

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

## Explicit non-goals for the initial research prototype

The first implementation phase does **not** attempt to provide:

- Full exploit generation.
- Payload generation.
- Remote target interaction.
- Malware deployment or execution.
- A full x86_64 instruction decoder.
- Symbolic execution.
- Multi-architecture support.
- Dynamic tracing.
- Automatic vulnerability discovery.

Those may become future research directions, but they are not part of the initial implementation contract.

## Tool name decision

The name `x64lens` is intentionally narrow for the first major phase. The tool begins as a lens into x86_64 ELF binaries. If the project later grows into a multi-architecture platform, architecture-specific engines can be added under the same repository, or the project can later adopt a broader umbrella name. For now, `x64lens` keeps the initial research contribution precise, searchable, and technically honest.

See [`docs/adr/0001-tool-name.md`](docs/adr/0001-tool-name.md).

## Current CLI contract

Planned early commands:

```bash
x64lens info <file>
x64lens mitigations <file>
x64lens gadgets [--max-depth N] <file>
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

### Run the current implementation

```bash
./build/x64lens version
./build/x64lens help
make samples
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info /bin/ls
./build/x64lens mitigations ./tests/bin/minimal_nopie
./build/x64lens mitigations ./tests/bin/minimal_pie_canary
./build/x64lens gadgets ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
```

The `info` command maps the target read-only, validates ELF64 x86_64 identity, and prints basic ELF header metadata. The `mitigations` command builds on that path by parsing program headers, identifying executable `PT_LOAD + PF_X` regions, and reporting baseline mitigation indicators such as PIE, NX stack, RELRO presence, RWX load segments, and dynamic linking. The Sprint 3 `gadgets` command scans executable regions for raw `ret` and `ret imm16` candidates and reports bounded byte windows. Semantic classification remains Sprint 4 work.

### Run tests

```bash
make test
```

## Docker and devcontainer workflow

The preferred daily development environment is WSL2 Ubuntu 24.04. Docker is the reproducibility layer for reviewer setup, CI smoke checks, and future benchmark harness validation.

Build the development image:

```bash
make docker-build
```

Open a shell without creating root-owned files in the bind-mounted repository:

```bash
make docker-shell
```

Run the full container smoke test:

```bash
make docker-test
```

If `make clean` fails with `Permission denied` under `build/`, a Docker container was likely run as root against the bind-mounted repository. Repair local generated artifact ownership with:

```bash
sudo chown -R "$(id -u):$(id -g)" build tests/bin tests/toy-src
make clean
```

See [`docs/troubleshooting.md`](docs/troubleshooting.md).

## Development cadence

This project follows a two-week sprint cadence during the initial research and implementation phase.

1. Sprint 1: repository, build system, CLI skeleton, file mapping, ELF64 validation, and basic `info` reporting.
2. Sprint 2: program headers, executable regions, and basic mitigations. Complete and locally validated.
3. Sprint 3: raw gadget candidate scanner and initial candidate storage. In progress with a fixed candidate buffer bridge before the arena allocator.
4. Sprint 4: semantic primitive classifier and primitive coverage summary.
5. Sprint 5: scoring, JSON output, benchmark harness, comparison tooling.
6. Sprint 6: final analyzer, documentation, benchmark results, research paper outline.

See [`docs/sprints/`](docs/sprints/).

## Example target output

Current `info` output is ELF metadata focused:

```text
x64lens 0.1.0-dev
Target: ./tests/bin/minimal_nopie

Format:
  Type: ELF64
  Endian: little
  Machine: x86_64
  ELF Type: ET_EXEC
  Entry: 0x0000000000401050
  Program header offset: 0x0000000000000040
  Program header entry size: 0x0000000000000038
  Program header count: 0x000000000000000d
  Section header offset: 0x0000000000003640
  Section header entry size: 0x0000000000000040
  Section header count: 0x000000000000001f
  File size: 0x0000000000003e00
```

Current `mitigations` output is program-header and loader-mapping focused:

```text
x64lens 0.1.0-dev
Target: ./tests/bin/minimal_nopie

Mitigations:
  PIE: disabled
  NX stack: enabled
  RELRO: present
  RWX load segment: no
  Dynamic linking: yes
  Program header count: 0x000000000000000d
  LOAD segments: 0x0000000000000004
  Executable LOAD regions: 0x0000000000000001

Executable regions:
  - VA 0x0000000000401000, file offset 0x0000000000001000, file size 0x0000000000000161, mem size 0x0000000000000161, perms R-X
```

Current Sprint 3 `gadgets` output is raw candidate focused:

```text
x64lens 0.1.0-dev
Target: ./tests/bin/gadgets

Raw gadget candidates:
  Max depth: 0x0000000000000008
  Candidate capacity: 0x0000000000001000
  Candidate count: ...
  ret count: ...
  ret imm16 count: ...
  - VA ..., file offset ..., window start ..., len ..., terminator: ret, bytes: ...
```

Primitive coverage, scoring, mitigation-aware interpretation, and JSON output are later sprint targets.

## Ethics and safety

x64lens is intended for educational research, defensive binary triage, secure build validation, and authorized reverse engineering. It does not include exploit delivery, payload generation, remote scanning, or unauthorized target interaction.

See [`docs/ethics-and-safety.md`](docs/ethics-and-safety.md).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
