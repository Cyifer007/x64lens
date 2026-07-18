# NASM Implementation Rationale

## Purpose

x64lens begins as an assembly-first ELF64 x86_64 analyzer. That choice is intentional, but it is also one of the most likely reviewer questions. This document defines the rationale, limits, and evaluation burden for the NASM implementation.

## Recommended public framing

The strongest claim is not that assembly is automatically faster than every other implementation language.

The stronger, testable claim is:

```text
A dependency-light, assembly-first ELF64 analyzer can produce reproducible,
mitigation-aware semantic primitive reports with a small runtime dependency
surface.
```

This keeps the project measurable and avoids unsupported language-superiority claims.

## Why NASM for the first engine

| Reason | Design value |
|---|---|
| Direct Linux syscall path | Makes file mapping, output, and process exit behavior explicit. |
| Small dependency surface | Avoids pulling a large runtime framework into the first research artifact. |
| Transparent data movement | Helps the project remain explainable as an assembly-language systems artifact. |
| Low-level performance control | Allows benchmarkable control over allocation, scanning, and output behavior. |
| Course alignment | Matches the low-level ELF64 x86_64 Linux focus of the initial implementation. |

## What NASM does not prove by itself

NASM does not automatically prove:

- better coverage than decoder-backed tools,
- better analyst value than existing tools,
- memory safety on malformed inputs,
- maintainability for outside contributors,
- portability across architectures.

Those are research questions and engineering risks. They must be handled through validation, documentation, comparison, and disciplined scope.

## Reviewer concerns and planned responses

| Concern | Response path |
|---|---|
| Why not C, Rust, or Go? | Treat NASM as the evaluated design choice, not as assumed superiority. Optional later C/Rust reference scanners may be used as ablation baselines. |
| Is assembly safe for untrusted binary parsing? | Enforce explicit range checks, malformed input tests, mutation smoke tests, no SIGSEGV/SIGBUS acceptance criteria, and conservative failure codes. |
| Is it maintainable? | Keep modules narrow, comment public routines, document register conventions, preserve tests, and publish contributor guides. |
| Is it portable? | State ELF64 x86_64 Linux as the initial target. Treat ARM64, PE, Mach-O, and other formats as future engines, not near-term rewrites. |
| Is it faster only because it does less? | Benchmark separate work units: raw scanning, exact pattern matching, semantic classification, output generation, and full report generation. |

## Paper language guidance

Use cautious language:

```text
We evaluate whether an assembly-first design can reduce runtime and memory overhead for a bounded ELF64 x86_64 analysis task.
```

Avoid unsupported language:

```text
Assembly eliminates nearly all overhead.
```

The second statement is too broad. Runtime is still affected by page faults, disk cache, output volume, memory bandwidth, syscall overhead, and differences in what baseline tools compute.

## Implementation consequence

The codebase should keep the assembly engine small and measurable. Higher-level research value should come from semantic classification, mitigation context, reporting contracts, and reproducible comparison, not from raw implementation language identity alone.
