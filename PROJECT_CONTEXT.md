# x64lens Project Context

This file is the high-density project context document intended for upload into ChatGPT project context. It should be kept current at every sprint checkpoint.

## One-sentence definition

`x64lens` is an assembly-first ELF64 x86_64 binary analysis tool that identifies exploit-relevant code primitives, classifies their semantic usefulness, evaluates mitigation context, and produces reproducible reports for offensive research, defensive triage, and binary hardening assessment.

## Course integration

The project is now intentionally shared across two Summer 2026 courses with different deliverables:

- **CSC-732 Assembly Language:** tool development, NASM implementation, ELF64 parsing, executable region analysis, gadget scanning, semantic classification, sprint check-ins, and final technical demo.
- **CSC-773 Advanced Network Security and Mobile Communications:** research paper, IEEE-style evaluation, advanced cyberinfrastructure framing, benchmark methodology, and publication-ready results.

The unified research framing is:

> Can static binary exploitability analysis improve prioritization of network-exposed services and infrastructure software?

## Research questions

- **RQ1, performance:** Can an assembly-first ELF64 x86_64 gadget discovery engine outperform existing ROP gadget tooling in runtime and memory efficiency while maintaining comparable gadget discovery coverage?
- **RQ2, semantic value:** Can semantic primitive classification and mitigation-aware scoring provide more actionable binary exploitability triage than raw gadget enumeration alone?
- **RQ3, enterprise adoption:** Can a static, dependency-light, assembly-first binary analyzer be integrated into enterprise CI/CD or vulnerability management workflows to help prioritize binaries based on hardening posture and exploit primitive availability?

## Development strategy

The project follows the hybrid path:

- **Path 1 is the engine:** fast assembly-first ELF64 parsing and gadget candidate scanning.
- **Path 2 is the value layer:** semantic primitive classification, mitigation-aware interpretation, scoring, JSON output, and benchmarkable research claims.

## Sprint cadence

The project uses two-week sprint checkpoints:

1. Repository, build system, CLI skeleton, file mapping, ELF64 validation.
2. Program headers, executable region mapping, NX/PIE/RWX/RELRO baseline reporting.
3. Raw gadget candidate scanner, `--max-depth`, initial arena allocator.
4. Semantic classification, primitive coverage, register bitmaps.
5. Scoring, JSON output, benchmark harness, comparison tooling.
6. Final analyzer, documentation, benchmark results, IEEE paper scaffold, future roadmap.

## Non-negotiable contracts

- Code and documentation are equal deliverables.
- Every assembly source and config file must contain human-readable comments explaining purpose and intent.
- Every implementation step must include test steps and next steps.
- Public research claims must be measured, not assumed.
- The parser must treat target binaries as untrusted input.
- The semester version must not generate payloads, exploit targets, scan networks, or perform unauthorized actions.
- JSON output must remain schema-versioned.
- CLI commands, flags, and exit codes must remain stable once released.

## Architecture summary

```text
CLI -> file mapping -> ELF64 parser -> executable region mapper -> scanner -> pattern matcher -> semantic classifier -> scoring -> report emitters -> benchmark artifacts
```

Program headers are authoritative for executable runtime mappings. Section headers are secondary labels for human-readable output.

## Current implementation state

The repository is in Sprint 1 scaffold state. Existing commands are:

```bash
x64lens help
x64lens version
x64lens info <file>
```

The `info` command is currently a stub and will be replaced with file mapping and ELF64 validation.

## Primary environment recommendation

Use WSL2 Ubuntu 24.04 plus VS Code Remote WSL for daily Windows development, Docker/devcontainer for reproducibility, GitHub Actions for CI, and a native Ubuntu 24.04 system or clean VM for final publication benchmarks.

## Files to keep uploaded as project context

Minimum project context bundle:

- `PROJECT_CONTEXT.md`
- `PROJECT_STATE.md`
- `docs/contracts/development-contract.md`
- `docs/contracts/research-contract.md`
- `docs/contracts/context-persistence-contract.md`
- `docs/architecture.md`
- `docs/csc-773-integration.md`
- `docs/sprints/sprint-01-plan.md`

Refresh these after every sprint or major architecture decision.
