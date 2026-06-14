# Sprint 05 Patch 019 Baseline Comparison Harness Validation Notes

## Status

Implementation candidate.

## Sprint goal

Add development-level baseline comparison scaffolding after scoring, JSON output, and validation hardening have landed.

Patch 019 is a benchmark-harness and documentation patch. It does not change the analyzer pipeline, scanner semantics, classifier behavior, score values, or JSON schema.

## What changes

Patch 019 adds:

- `benchmarks/scripts/bench-baselines-smoke.sh`, a smoke harness for x64lens and optional baseline tools.
- `make bench-baselines-smoke`.
- `benchmarks/scripts/summarize.py`, a standard-library TSV summarizer for benchmark rows.
- `make bench-summary`.
- ADR 0007 for the baseline comparison harness design.
- Documentation updates for Sprint 5 benchmark-scaffolding status.
- Public validation transcript sanitization in existing sprint retrospectives.

## Baseline smoke behavior

The baseline smoke harness always runs x64lens. It optionally runs these tools when available:

- ROPgadget,
- Ropper,
- ropr.

Missing optional baseline tools are recorded in metadata and skipped by default. Set `REQUIRE_BASELINES=1` when the environment is expected to contain at least one optional baseline tool.

The x64lens timed command is:

```bash
x64lens gadgets --format json --max-depth <N> <target>
```

The harness validates x64lens JSON output after each run and records raw, exact, semantic, unknown, and scored counts from JSON.

## Expected validation commands

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make clean
make
make samples
make test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
make system-smoke
make validation-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
python3 benchmarks/scripts/summarize.py benchmarks/results/baseline-smoke-*.tsv
```

Docker validation remains:

```bash
make docker-available-check
make docker-test
```

Patch bundle hygiene remains:

```bash
BUNDLE=/path/to/019_x64lens_sprint5_baseline_comparison_harness_patch.zip make patch-bundle-hygiene
```

## Expected success signals

```text
script-perms-check: ok
scaffold-check: ok
diagrams-check: ok
tests: ok
validate-gadget-fixture: ok
json-smoke: ok
system-binary-smoke: ok targets=<n> max_depth=4
validation-smoke: ok
baseline-smoke benchmark complete
```

The baseline smoke command should succeed even when optional baseline tools are absent. In that case, metadata should report:

```text
baseline_tools_available=none
```

## Result artifacts

Generated benchmark files are ignored by Git unless intentionally promoted as paper artifacts:

```text
benchmarks/results/baseline-smoke-<timestamp>.tsv
benchmarks/results/baseline-smoke-<timestamp>.meta
```

The TSV rows preserve development evidence. They are not publication claims until the benchmark methodology is fully applied with fixed corpus, baseline tool versions, repeated trials, and summary statistics.

## Acceptance criteria

- [ ] `make test` passes.
- [ ] `make json-smoke` passes.
- [ ] `make system-smoke` passes.
- [ ] `make validation-smoke` passes.
- [ ] `RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke` writes TSV and metadata files.
- [ ] Missing optional baseline tools are skipped without failing default validation.
- [ ] `REQUIRE_BASELINES=1 RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke` fails when no optional baseline tool is installed.
- [ ] `benchmarks/scripts/summarize.py` emits a summary table from generated TSV files.
- [ ] Public documentation contains no private coordination context, attachment history, or dialogue-style wording.

## Non-goals

Patch 019 does not normalize baseline gadget counts, claim performance superiority, add a full decoder, add canary detection, add full RELRO detection, or implement `analyze` orchestration.
