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

Sprints 1 through 11 are complete. Sprint 12 remains the active acceptance
authority. Patch 081 was not accepted; Patch 082 is the current artifact-backed
implementation candidate, pending full local execution and independent
acceptance. Patch 080 supplied the private register-role side-car but did not
complete acceptance; it was superseded by Patch 081. Patch 074 was a superseded closeout
candidate. Sprint 11 established and
hardened the diagnostic runner, provisional corpus, normalized task definitions,
comparison evidence, generated summaries, and gap register while preserving the
unchanged dependency-free reference binary. The measurements did not resolve
x64lens single-run latency on the selected small targets and did not establish a
common cross-tool gadget population. Sprint 12 implemented or explicitly
deferred bounded loader validity, overlap/provenance, PIE-versus-DSO identity,
and GNU-property evidence. Patch 075 introduced private bounded `DT_TEXTREL` / `DF_TEXTREL` evidence.
Patch 076 added distinct bounded private `DT_RPATH` and `DT_RUNPATH` evidence
without adding public role/property or mitigation fields, but its review
required Patch 077. Patch 077 then required Patch 078, whose review required the
Patch 079 corrective and private task-value candidate, whose review required
Patch 080; Patch 080 was superseded by Patch 081. Sprint 13 remains planned and
activates only after complete Patch 082 acceptance. Sprint 15
freezes the confirmatory method; Sprint 16 produces the preview campaign,
Sprint 17 runs publication-grade trials, and Sprint 22 is the first research-
release gate.

## Sprint 12 loader-precision checkpoint

Patch 062 strengthens the bounded assembly-first parser without adding a runtime dependency or broadening offensive capability. Loader facts now reject invalid PHDR alignment, congruence, virtual ranges, and executable entrypoints before analysis. Structurally valid extended numbering is reported as unsupported rather than guessed. This supports defensive trustworthiness while preserving the dependency-free reference profile.


## Sprint 12 continuation checkpoint

Patch 076 preserves the dependency-free one-worker reference profile, program-
header executable authority, 4,096-candidate fail-closed behavior, and schema
`0.2.0`. Private role/property, text-relocation, and RPATH/RUNPATH evidence
remains outside public reports, and the role/property policy remains `defer`.
Patch 078 required the Patch 079 corrective and private task-value candidate,
which was superseded by Patch 080; Patch 080 was superseded by Patch 081. Patch
081 was not accepted and is superseded by Patch 082. Sprint 13 remains an entry
candidate and becomes active only after complete Patch 082 acceptance, without a
release tag or confirmatory campaign freeze.

## Sprint 12 Patch 077 historical checkpoint

Patch 077 was a loader/mitigation reconciliation candidate. It
preserved the dependency-free, decoder-free, one-worker reference analyzer and
added no public mitigation field, but its review required the Patch 078
correction below.

## Sprint 13 Patch 078 checkpoint

Patch 078 preserves the dependency-free, decoder-free, one-worker reference
analyzer and adds no public field or score. It corrects the Patch 077 acceptance
blockers and freezes a private exact-pop role decision so the next task-value
experiment can be scoped without broadening the runtime prematurely. Patch 079
owns deterministically presentation-ordered task-value qualification before any
runtime-semantic, public-field,
or score projection.

## Historical Sprint 13 Patch 079 checkpoint

The Patch 079 candidate retained the assembly-first, dependency-light reference
profile while adding no public analysis capability. It corrects source, Docker,
parity, recovery, transaction, and delivery evidence paths and records a
preregistered task-value result for private register-role facets. Its review
required Patch 080; the result was policy input, not a claim of exploitability
or complete gadget coverage.

## Historical Sprint 13 Patch 080 implementation stage

Patch 080 corrected the Patch 079
evidence and custody defects and adds a private bounded register-role side-car.
It was superseded by Patch 081. The public analyzer contract remains unchanged.

## Historical Sprint 13 Patch 081 stage

Patch 081 was not accepted. It records a declarative, test-only ordered-pair
authority and retains the complete score/null partition without changing runtime
output, semantic classes, scores, capacity, or schema `0.2.0`. Its validation
findings were accepted as correction inputs to Patch 082.

## Patch 082 evidence-integrity checkpoint

Patch 082 preserves the assembly-first product scope while strengthening the
reproduction surface. It implements a policy gate that requires three
independent analyzer builds, separates Docker source custody from mutable build
output, and adds a controlled coordinate method-discrimination preflight over
six targets and 18 modeled cell observations. Full retained three-build
execution, natural comparison evidence, and independent acceptance remain
pending. These are evidence and delivery improvements, not new public analysis
capabilities.
