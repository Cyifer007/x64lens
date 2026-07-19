# Project Charter

## Project name

`x64lens`

## Project statement

x64lens is an assembly-first ELF64 x86_64 binary analysis tool that identifies exploit-relevant code primitives, classifies their semantic usefulness, evaluates mitigation context, and produces reproducible reports for offensive research, defensive triage, and binary hardening assessment.

## Mission

Build a long-term, maintainable, research-grade binary exploitability analysis platform that starts with a tightly scoped NASM-based ELF64 x86_64 analyzer and grows through measured, documented capabilities.

## Public research model

The public repository is the engineering and research artifact. It should be understandable without private course logistics, private planning notes, or tool-assisted development context. Public documentation should explain what the tool does, how it is built, how it is evaluated, and how others can reproduce results.

Private planning notes, local sprint state, and course-specific coordination files belong in ignored local-only context files under `.local/project-context/`.

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
- infrastructure software risk prioritization,
- JSON output for automation,
- SARIF output in a future release.

## Initial research questions

### RQ1

How do runtime, memory cost, and explicitly defined return-oriented coverage
compare between a bounded assembly-first ELF64 x86_64 analysis profile and
established gadget tools, and what residual coverage gaps remain?

### RQ2

Can semantic primitive classification and mitigation-aware scoring provide more actionable binary exploitability triage than raw gadget enumeration alone?

### RQ3

Can a static, dependency-light, assembly-first binary analyzer be integrated into enterprise CI/CD or vulnerability management workflows to help prioritize binaries based on hardening posture and exploit primitive availability?

## Cyberinfrastructure bridge

The strongest infrastructure-oriented framing is:

> Can static binary exploitability analysis improve prioritization of network-exposed services and infrastructure software?

Possible target domains:

- network-facing Linux services,
- cloud-hosted infrastructure services,
- network appliances,
- embedded Linux devices,
- exposed service prioritization,
- supply-chain binary review,
- hardening validation.

AI-based future work may include analyst summarization, corpus triage, or semantic clustering, but AI is not part of the initial implementation contract.


## Current release path

The project uses evidence-based milestone gates:

- `v0.1.0-dev`: integrated development checkpoint, complete through Sprint 6.
- `v0.1.0-rc1`: research preview candidate after parser hardening, mitigation depth, provenance-aware output, reproducible corpus construction, and high-resolution benchmark infrastructure.
- `v0.1.0`: first research release after comparative experiments, an operational case study, replication rehearsal, and paper claim audit.

The canonical implementation plan is `docs/roadmap-22-sprints.md`.

## Initial implementation deliverables

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

## Non-goals for the initial implementation phase

- Full exploit generation.
- Payload generation.
- Remote scanning.
- Malware execution.
- Symbolic execution.
- Full x86_64 decoding.
- Multi-architecture support.
- Automatic vulnerability discovery.

## Success criteria

The initial project succeeds if another technical user can clone the repository, build the tool, run the documented tests, analyze simple ELF64 binaries, inspect JSON output, reproduce benchmark commands, and understand the roadmap without private context.

## Defensive deployment constraint

The default product profile should remain suitable for air-gapped analysis, constrained incident response, minimal CI/CD runners, and defensive malware triage. Dependency count, binary size, startup cost, max RSS, helper-process count, deterministic output, and failure behavior are product characteristics to preserve and measure.

Future decoding should prefer validation of retained candidate windows over mandatory whole-image decoding. Future parallelism should be optional and evidence-gated. Neither enhancement may erase the dependency-free one-worker reference profile or weaken provenance, capacity, or malformed-input contracts.

## Sprint 10 memory-effect constraint

Memory semantics expand only through bounded exact families and explicit internal facts. Patch 049 adds no runtime dependency and preserves the decoder-free one-worker reference profile. Broader address forms, score changes, and performance claims remain evidence-gated.


## Pre-freeze architecture review

Before Sprint 15 freezes the reproducible campaign, Sprints 12 and 13 resolve
or explicitly defer the PIE-versus-DSO interpretation, CET/IBT/SHSTK property
evidence, overlapping executable-segment semantics, and release-facing score
policy identified by the Patch 053 review. Sprint 11 diagnostic evidence may
reprioritize this work; it does not freeze the corpus.

The review does not make full decoding, JOP/COP/SROP, exploit generation, or default multithreading hidden requirements for the first release. Those remain evidence-gated scope decisions.


## Benchmark-informed release sequencing

Diagnostic benchmarking begins before feature freeze so runtime, RSS, output-scope, and coverage evidence can redirect development. Those provisional rows are development evidence only. Corpus, schema, runner, tools, commands, and task definitions freeze in Sprint 15; the preview and publication campaigns follow in Sprints 16 and 17. The first research release is scheduled for Sprint 22 after triage, automation, case-study, and replication gates.

## Current implementation stage

Sprints 1 through 10 are complete after Patch 054. Sprint 11 begins diagnostic measurement with a provisional corpus and mutable method so performance, resource, coverage, and task-definition evidence can redirect the implementation before campaign freeze. Sprint 15 freezes the confirmatory method; Sprint 16 produces the preview campaign, Sprint 17 runs publication-grade comparative trials, and Sprint 22 is the first research-release gate.
