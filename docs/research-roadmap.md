# Research Roadmap

## Stage 1: CSC-732 foundation

Build a working NASM-first ELF64 x86_64 analyzer.

Primary outcome: functional scaffold and semester-grade tool.

## Stage 2: benchmarkable scanner

Compare x64lens against ROPgadget, Ropper, and ropr.

Primary outcome: reproducible performance and coverage data.

## Stage 3: semantic primitive scoring

Move beyond raw gadget counts into semantic utility.

Possible research question:

> Can semantic gadget usefulness be measured more accurately through side-effect and primitive-coverage analysis than through raw gadget count?

## Stage 4: mitigation-aware exploitability modeling

Connect NX, PIE, RELRO, canaries, RWX segments, CET, and IBT to plausible exploit strategy constraints.

Possible research question:

> How do modern mitigations change the practical usefulness of available gadget sets?

## Stage 5: compiler and hardening comparison

Evaluate how compiler flags and hardening profiles change semantic primitive availability.

Variables:

- GCC vs Clang,
- `-O0`, `-O1`, `-O2`, `-O3`, `-Os`,
- PIE vs non-PIE,
- stack protector variants,
- partial vs full RELRO,
- CET flags,
- LTO,
- static vs dynamic linking.

## Stage 6: network infrastructure triage

Connect the tool to network-facing infrastructure and operational security.

Possible research question:

> Can static binary exploitability analysis improve prioritization of network-exposed services and infrastructure software?

## Stage 7: dissertation-scale work

Potential dissertation directions:

- semantic exploitability scoring,
- binary hardening effectiveness metrics,
- architecture-specific primitive modeling,
- AI-assisted analyst interpretation over deterministic low-level facts,
- network appliance binary triage,
- firmware-scale exploitability modeling,
- CET/IBT impact on code-reuse exploitability.
