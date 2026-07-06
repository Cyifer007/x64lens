# ADR 0024: Sprint 8 closeout and optional-helper hardening

## Status

Accepted.

## Context

Sprint 8 added bounded dynamic metadata, RELRO refinement, canary and stripped
indicators, section-label annotations, hostile section-label hardening,
benchmark-integrity gates, Docker context hygiene, automated `readelf`
comparison, and optional `checksec` / `rabin2 -I` comparison helpers.

The final Patch 037 validation found that the optional direct comparison helper
scripts could silently compare the wrong file when invoked with the analyzer
binary and target arguments reversed. The same validation also found that the
benchmark-integrity smoke target did not directly cover non-finite RSS values,
and that advisory shell lint had not yet been promoted into a strict clean gate.

## Decision

Patch 038 closes Sprint 8 by hardening the optional direct helper scripts and
promoting the evidence gaps into executable or documented closeout gates:

- `tools/compare-checksec.sh` and `tools/compare-rabin2.sh` accept both
  `<target> <tool>` and `<tool> <target>` order, but require exactly one
  argument to identify as the x64lens analyzer and exactly one argument to be
  the analyzed target. Argument inference must not execute the target binary.
- The helpers print an explicit `tool=` / `target=` identity line before
  comparison output so logs can be audited for target identity.
- `tools/benchmark-integrity-smoke.py` covers non-finite `wall_s` and
  non-finite `maxrss_kb` values directly.
- Strict shell lint is treated as a useful optional gate. Intentional literal
  install-hint snippets and ordered bundle-hygiene boundary patterns are
  documented where they otherwise look suspicious to shell lint.
- Sprint 8 is closed only after public planning, validation, and retrospective
  documents point to Sprint 9 as the next implementation tranche.

## Consequences

The optional comparison helpers remain review aids, not runtime dependencies
or authoritative mitigation oracles. Their corrected argument validation makes
manual comparison output trustworthy enough for local review, while normal
validation still passes when optional tools are absent.

Sprint 9 can now begin from a cleaner boundary: parser safety, mitigation
indicators, section-label annotations, and comparison smoke gates are complete;
provenance, completeness, schema `0.2.0`, decoder-gap measurement, and
publication-grade benchmark methodology remain future work.
