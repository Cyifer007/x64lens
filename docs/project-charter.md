# Project Charter

## Project name

`x64lens`

## Project statement

x64lens is an assembly-first ELF64 x86_64 binary analysis tool that identifies exploit-relevant code primitives, classifies their semantic usefulness, evaluates mitigation context, and produces reproducible reports for offensive research, defensive triage, and binary hardening assessment.

## Mission

Build a long-term, maintainable, research-grade binary exploitability analysis platform that starts with a tightly scoped NASM-based ELF64 x86_64 analyzer and grows through measured, documented capabilities.



## Unified CSC-732 and CSC-773 project model

This project now intentionally joins CSC-732 and CSC-773 into one semester-long research and development effort with distinct deliverables.

- CSC-732 evaluates the assembly implementation and technical sprint progress.
- CSC-773 evaluates the independent research paper, solution framing, evaluation methodology, and IEEE-format presentation.

The shared technical artifact is `x64lens`. The CSC-773 paper frames that artifact as a mitigation-oriented solution for prioritizing exploitability risk in advanced cyberinfrastructure.

## Course alignment

CSC-732 focuses on assembly language programming as it applies to reverse engineering and binary exploitation, specifically 64-bit x86 in a Linux environment. The syllabus also lists ELF/PE formats, NASM, GDB, Radare2, objdump, function calling conventions, system calls, shellcode, position-independent code, GOT/PLT, and CPU security extensions as relevant topics. x64lens directly targets those areas.

## Research alignment

The project is designed to support publication-quality work through:

- reproducible benchmark design,
- stable tool versioning,
- stable output schema versioning,
- controlled corpus documentation,
- clear metrics,
- explicit threats to validity,
- comparison against existing tools,
- documented semantic definitions.

## Enterprise alignment

The project is designed to eventually support:

- CI/CD binary hardening gates,
- vulnerability management enrichment,
- supply-chain binary review,
- network-facing service triage,
- ISP and infrastructure software risk prioritization,
- JSON output for automation,
- SARIF output in a future release.

## Initial research questions

### RQ1

Can an assembly-first ELF64 x86_64 gadget discovery engine outperform existing ROP gadget tooling in runtime and memory efficiency while maintaining comparable gadget discovery coverage?

### RQ2

Can semantic primitive classification and mitigation-aware scoring provide more actionable binary exploitability triage than raw gadget enumeration alone?

### RQ3

Can a static, dependency-light, assembly-first binary analyzer be integrated into enterprise CI/CD or vulnerability management workflows to help prioritize binaries based on hardening posture and exploit primitive availability?

## CSC-773 bridge

Advanced Network Security and Mobile Communications can use the tool through the following framing:

> Can static binary exploitability analysis improve prioritization of network-exposed services and infrastructure software?

Possible target domains:

- ISP edge services,
- network appliances,
- Linux daemons,
- embedded network devices,
- exposed service prioritization,
- supply-chain binary review,
- hardening validation.

AI-based future work may include analyst summarization, corpus triage, or semantic clustering, but AI is not part of the Sprint 1 through Sprint 6 implementation contract.

## Semester deliverables

1. A buildable NASM-first CLI scaffold.
2. ELF64 x86_64 validation.
3. Program header parsing and executable region mapping.
4. Baseline mitigation reporting.
5. Pattern-based gadget scanning.
6. Semantic primitive classification.
7. Primitive coverage summary.
8. Text and JSON output.
9. Benchmark harness.
10. Comparison against existing tools.
11. Final documentation and research roadmap.

## Long-term deliverables

- Full or pluggable x86_64 decoder.
- JOP/COP/SROP primitive analysis.
- CET/IBT-aware classification.
- Multi-architecture engines.
- PE and Mach-O support.
- SARIF output.
- Ghidra/radare2 interoperability.
- Public benchmark corpus.
- Peer-reviewed publication.
- Dissertation-level exploitability modeling.

## Non-goals for the first semester

- Full exploit generation.
- Payload generation.
- Remote scanning.
- Malware execution.
- Symbolic execution.
- Full x86_64 decoding.
- Multi-architecture support.
- Automatic vulnerability discovery.

## Success criteria

The semester project succeeds if another technical user can clone the repository, build the tool, run the documented tests, analyze simple ELF64 binaries, inspect JSON output, reproduce benchmark commands, and understand the roadmap without private context.
