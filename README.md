# x64lens

**x64lens is an assembly-first ELF64 x86_64 binary analysis tool that identifies exploit-relevant code primitives, classifies their semantic usefulness, evaluates mitigation context, and produces reproducible reports for offensive research, defensive triage, and binary hardening assessment.**

> Status: Sprint 4 in progress. Patch 015 adds the first semantic classifier over Sprint 3 exact suffix pattern IDs. Sprints 1 through 3 are complete.
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

## Current implementation checkpoint

Patch 015 advances the implemented pipeline to the first semantic layer:

```text
ELF64 validation -> program-header analysis -> executable-region mapping -> raw gadget scanner -> exact suffix pattern matcher -> semantic classifier -> text reporting
```

The current `gadgets` command reports raw terminator-centered byte windows, exact suffix pattern labels, conservative semantic classes, controlled-register bitmaps, stack deltas, and primitive coverage counts. This is still not full instruction decoding and does not emit exploitability verdicts.

See [`docs/roadmap-12-sprints.md`](docs/roadmap-12-sprints.md) for the expanded semester roadmap.

## Reviewer-facing design posture

The current plan treats common reviewer objections as design inputs rather than late-stage surprises.

Key planning commitments:

- NASM is an evaluated implementation choice, not an assumed proof of superiority.
- Parser safety is a mandatory design constraint because the tool parses untrusted binaries.
- Exact suffix matching is a Sprint 3 stage, not a full instruction decoder.
- Raw candidate counts, exact pattern counts, semantic primitive counts, and scored gadget counts are separate metrics.
- External tools are comparison baselines first, not required runtime dependencies.
- ARM64, PE, Mach-O, full decoding, and embedded decoder support remain future seams, not near-term scope creep.

See the planning notes under [`docs/design/`](docs/design/) and [`docs/adr/0005-reviewer-readiness-and-future-seams.md`](docs/adr/0005-reviewer-readiness-and-future-seams.md).

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
make semantic-smoke
```

The `info` command maps the target read-only, validates ELF64 x86_64 identity, and prints basic ELF header metadata. The `mitigations` command builds on that path by parsing program headers, identifying executable `PT_LOAD + PF_X` regions, and reporting baseline mitigation indicators such as PIE, NX stack, RELRO presence, RWX load segments, and dynamic linking. The `gadgets` command scans executable regions for raw `ret` and `ret imm16` candidates, reports bounded byte windows, tags exact byte-template patterns such as `pop rdi; ret`, `leave; ret`, and `syscall; ret`, then maps supported exact patterns into first-pass semantic primitive classes.

### Run tests

```bash
make test
```

### Scanner fixture validation and smoke benchmark

Sprint 3 adds an explanatory fixture validator and a first scanner smoke benchmark. These are separate from `make test` so they can preserve richer evidence without slowing the default regression path.

```bash
make validate-gadget-fixture
make arena-smoke
make semantic-smoke
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
```

The fixture validator compares `x64lens gadgets` output for `tests/bin/gadgets` against `objdump -d -Mintel` and now validates first-pass semantic classifier facts. The smoke benchmark writes TSV results and metadata under `benchmarks/results/`, including raw candidate counts, exact pattern counts, semantic primitive counts, and unknown candidate counts. These generated results are ignored by Git unless intentionally promoted into a documented benchmark artifact.

The smoke benchmark is development evidence only. Do not use it as a publication claim without the full benchmark methodology, baseline tools, corpus manifest, repeated trials, and environment metadata.

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
3. Sprint 3: raw gadget candidate scanner, scanner smoke benchmark, arena-backed candidate storage, and exact byte-template pattern matching.
4. Sprint 4: semantic primitive classifier and primitive coverage summary. In progress through Patch 015.
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

Current Sprint 4 `gadgets` output keeps raw, exact, and semantic facts separate:

```text
x64lens 0.1.0-dev
Target: ./tests/bin/gadgets

Raw gadget candidates:
  Max depth: 0x0000000000000008
  Candidate capacity: 0x0000000000001000
  Candidate count: ...
  ret count: ...
  ret imm16 count: ...
  Exact pattern count: ...
  Semantic primitive count: ...
  unknown_candidate count: ...
  arg_control count: ...
  syscall_num_control count: ...
  syscall_trigger count: ...
  stack_pivot count: ...
  alignment count: ...
  Register coverage: rax|rdx|rsi|rdi|rsp
  - VA ..., file offset ..., window start ..., len ..., terminator: ret, pattern: pop rdi; ret, semantic: arg_control, regs: rdi, stack delta: 0x0000000000000010, bytes: ...
```

Pattern labels are still exact suffix labels, not full decoded instruction sequences. Semantic classification is conservative and scoring, mitigation-aware exploitability interpretation, and JSON output remain later sprint targets.

## Ethics and safety

x64lens is intended for educational research, defensive binary triage, secure build validation, and authorized reverse engineering. It does not include exploit delivery, payload generation, remote scanning, or unauthorized target interaction.

See [`docs/ethics-and-safety.md`](docs/ethics-and-safety.md).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).


## Sprint 3 arena allocator note

Sprint 3 Patch 010 introduces a small mmap-backed bump allocator for analysis records. The first consumer is the raw gadget candidate buffer used by `x64lens gadgets`. Candidate capacity remains bounded at 4096 records, but storage is now owned by a command-lifetime arena rather than a static `.bss` array. This keeps the scanner interface stable while preparing later sprints for larger internal records, JSON staging, and benchmark artifacts.


## Sprint 3 pattern matcher note

Sprint 3 Patch 011 adds exact byte-template pattern labels to raw gadget candidates. This is a pattern matching layer, not a semantic classifier. The matcher recognizes small suffix templates such as `pop rdi; ret`, `pop rsi; ret`, `pop rdx; ret`, `pop rax; ret`, `leave; ret`, `syscall; ret`, and `ret imm16`.

## Sprint 4 semantic classifier note

Sprint 4 Patch 015 adds the first classifier pass. `classifier.asm` consumes `PATTERN_*` IDs and populates semantic classes, controlled-register bitmaps, stack deltas, side-effect flags, per-class summary counts, and register coverage. Unsupported patterns remain `unknown_candidate`; scoring and JSON output remain future work.

## Patch 14 planning note

Patch 14 is a planning and documentation alignment patch. It does not change the scanner engine. It records reviewer-facing rationale and future seams for NASM implementation, parser safety, decoder integration, metric boundaries, contributor maintainability, and long-arc roadmap planning.
