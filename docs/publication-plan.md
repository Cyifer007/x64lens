# Publication Plan

## Candidate paper title

x64lens: An Assembly-First Semantic Gadget and Exploitability Analyzer for ELF64 x86_64 Binaries

## Target paper shape

IEEE-style 5 to 6 page paper.

## Sections

1. Introduction.
2. Related work.
3. Design.
4. Evaluation methodology.
5. Results.
6. Discussion and threats to validity.
7. Future work.
8. Conclusion.

## Core contribution statement

x64lens contributes an assembly-first implementation and evaluation framework for ELF64 x86_64 gadget discovery, semantic primitive classification, and mitigation-aware exploitability reporting.

## Required artifacts

- Public repository.
- Release tag.
- Benchmark corpus manifest.
- Benchmark scripts.
- Raw benchmark results.
- Summary tables.
- Reproduction commands.
- IEEE paper source.


## Research paper role

The repository should preserve all experimental setup details needed to reproduce a publication-quality paper:

- corpus manifest,
- target binary source/build commands,
- tool versions,
- benchmark commands,
- platform details,
- raw results,
- summary tables,
- limitations,
- threats to validity.

## Paper framing

The paper should frame `x64lens` as a mitigation-oriented solution for advanced cyberinfrastructure defense:

> Static binary exploitability analysis can enrich prioritization of network-facing infrastructure software by measuring hardening posture, gadget primitive availability, semantic exploit primitive coverage, and tool runtime/memory cost.

## Reviewer-risk sections to include

The paper should include explicit short sections or paragraphs for:

- assembly-first design rationale,
- parser safety and malformed-input validation,
- exact pattern matching limitations,
- raw/exact/semantic metric separation,
- baseline comparison methodology,
- threats to validity,
- architecture and format scope limitations,
- future decoder and multi-architecture work.

## Paper claim discipline

Do not claim that x64lens is faster, more accurate, or more useful until repeated benchmark data supports that claim. Frame early results as evidence for a bounded prototype, not as universal superiority over mature tools.
