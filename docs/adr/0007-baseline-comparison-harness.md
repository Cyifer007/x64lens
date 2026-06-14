# ADR 0007: Baseline Comparison Harness

## Status

Accepted for Sprint 5 Patch 019.

## Context

The project now emits scored, schema-versioned gadget JSON and has validation coverage for controlled fixtures and installed system binaries. The next research need is comparison scaffolding against existing gadget tools without turning development smoke data into unsupported publication claims.

The research contract requires any performance, memory, coverage, or analyst-usefulness claim to preserve tool versions, schema version when output is involved, corpus manifest, exact command, run count, environment metadata, raw results, and summary statistics.

## Decision

Add a baseline comparison smoke harness before starting research-grade benchmark runs.

The harness will:

- run `x64lens gadgets --format json --max-depth <N>` against controlled and system targets,
- optionally run ROPgadget, Ropper, and ropr when installed,
- skip missing optional baseline tools by default,
- support `REQUIRE_BASELINES=1` when a strict environment is expected,
- write raw TSV rows under `benchmarks/results/`,
- write metadata sidecars with tool versions, host metadata, and corpus-manifest hash,
- keep x64lens count extraction based on JSON output rather than text scraping,
- treat the result as development smoke evidence, not publication evidence.

## Rationale

This keeps the project moving toward RQ1 without broadening implementation scope or creating unsupported claims. It also makes missing baseline tools an explicit environment fact instead of a hard failure during normal development.

## Consequences

Positive:

- Baseline comparison wiring becomes reproducible.
- Optional tools can be introduced incrementally.
- Raw result preservation starts before the final benchmark sprint.
- x64lens count extraction uses the stable JSON integration layer.

Tradeoffs:

- Smoke rows are not yet fair publication benchmarks.
- Baseline tool output counts are not normalized yet.
- Tool definitions still need careful mapping before coverage claims.

## Future work

- Normalize baseline gadget counts with documented parser rules.
- Add explicit baseline tool install notes.
- Expand corpus tiers beyond fixtures and common system binaries.
- Run repeated publication trials after the scanner, classifier, scoring, and output contracts stabilize.
