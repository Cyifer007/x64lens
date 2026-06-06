# CSC-773 Integration Plan

## Purpose

This document explains how `x64lens` fits CSC-773 Advanced Network Security and Mobile Communications while preserving CSC-732 as the implementation-heavy assembly course deliverable.

## CSC-773 requirement mapping

The CSC-773 project requires independent research on cybersecurity issues in advanced cyberinfrastructure, development of a solution to mitigate security risks, and an evaluation through analysis, simulation, and/or testing. The final paper must use the IEEE conference template and be 5 to 6 pages.

`x64lens` maps to that requirement as follows:

| CSC-773 requirement | x64lens mapping |
|---|---|
| Advanced cyberinfrastructure | Network-facing Linux services, ISP infrastructure software, network appliances, cloud-hosted services, IoT/embedded Linux binaries |
| Critical cybersecurity issue | Defenders often prioritize vulnerabilities by CVSS/severity while ignoring binary hardening posture and exploit primitive availability |
| Solution | Static assembly-first binary analyzer that reports hardening metadata, executable regions, gadget primitives, semantic primitive coverage, and exploitability-oriented interpretation |
| Evaluation | Benchmark runtime, memory, throughput, gadget coverage, semantic primitive coverage, and mitigation-report accuracy against existing tools |
| Research output | IEEE-style paper using reproducible commands, controlled corpus, and measurable results |

## Proposed CSC-773 paper framing

**Working title:**

> x64lens: Assembly-First Semantic Binary Exploitability Triage for Network-Facing Cyberinfrastructure

**Core problem:**

Vulnerability management and infrastructure defense often rely on vulnerability severity, asset exposure, and patch status. Those signals are necessary but incomplete. For native binaries exposed through advanced cyberinfrastructure, defenders also need to understand whether the binary exposes useful exploitation primitives and whether hardening controls meaningfully constrain plausible exploit paths.

**Proposed solution:**

Build and evaluate `x64lens`, a static ELF64 x86_64 analyzer that performs fast executable-region scanning, semantic gadget classification, mitigation-aware interpretation, and reproducible reporting.

## Refined research questions

- **RQ1:** Can an assembly-first ELF64 x86_64 gadget discovery engine outperform existing ROP gadget tooling in runtime and memory efficiency while maintaining comparable gadget discovery coverage?
- **RQ2:** Can semantic primitive classification and mitigation-aware scoring provide more actionable binary exploitability triage than raw gadget enumeration alone?
- **RQ3:** Can a static, dependency-light, assembly-first binary analyzer be integrated into enterprise CI/CD or vulnerability management workflows to help prioritize binaries based on hardening posture and exploit primitive availability?

## Cyberinfrastructure target set

The first paper should not require proprietary ISP binaries. Use public, reproducible targets that represent infrastructure software:

- OpenSSH client/server binaries where available.
- nginx or Apache httpd if installed or built in the corpus.
- curl/libcurl command-line binary.
- BusyBox for embedded-style Linux utilities.
- FFmpeg as a large, performance-sensitive native binary stress target.
- Coreutils as baseline system utilities.
- Controlled toy binaries compiled with hardening flag matrices.

## AI and quantum positioning

Dr. Begian encouraged considering AI-based vulnerability research and AI-based attack detection. For the first paper, AI should be framed as a future extension rather than forced into the implementation unless time permits.

Plausible future AI extensions:

- AI-assisted interpretation of `x64lens` JSON reports.
- Semantic clustering of binaries by primitive coverage profile.
- Natural-language explanations for defenders and vulnerability managers.
- AI-assisted corpus triage and anomaly discovery across infrastructure binaries.

Quantum computing should not be forced into the first paper unless the paper pivots toward cryptographic infrastructure, post-quantum firmware integrity, or quantum-accelerated vulnerability research. For this semester, the stronger paper is conventional, measurable, and technically deep.

## Deliverable split

| Deliverable | Course | Repository location |
|---|---|---|
| NASM implementation | CSC-732 | `src/`, `include/`, `tests/` |
| Sprint plans and retrospectives | CSC-732 | `docs/sprints/` |
| Benchmark harness | Both | `benchmarks/`, `tools/` |
| IEEE paper | CSC-773 | `paper/ieee/` |
| Research methodology | CSC-773 | `docs/benchmark-methodology.md`, `paper/notes/` |
| Publication roadmap | Both | `docs/publication-plan.md`, `docs/research-roadmap.md` |

## Evaluation plan

The CSC-773 paper should include:

- tool versions,
- exact commands,
- CPU/RAM/platform,
- reproducible corpus manifest,
- repeated runs,
- median runtime,
- p95 runtime,
- max RSS,
- throughput in MiB/s,
- gadget count comparison,
- semantic primitive count comparison,
- threats to validity.
