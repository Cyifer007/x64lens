# Sprint 05 Retrospective

## Sprint status

Sprint 5 is complete after Patch 021.

## Sprint goal

Sprint 5 added the first scoring layer, schema-versioned JSON output, validation hardening, system-binary smoke coverage, baseline comparison smoke scaffolding, onboarding documentation, and development toolchain checks.

## Completed work

- Added initial heuristic gadget scoring from internal semantic facts.
- Added `gadgets --format json` with schema-versioned report structure.
- Preserved separate raw, exact-pattern, semantic, unknown, and scored-count metrics.
- Added JSON validation through `tools/validate-json-report.py`.
- Added system-binary smoke validation across installed ELF64 binaries.
- Added patch-bundle hygiene checks for public source bundles.
- Added baseline smoke benchmarking for x64lens, ROPgadget, Ropper, and ropr when available.
- Added benchmark summarization for generated TSV files.
- Added onboarding documentation and dependency diagnostics.
- Hardened Docker dependency parity and prevented stale-image validation after Dockerfile changes.
- Clarified ropr installation requirements and moved ropr into a rustup-stable optional baseline path.

## Validation evidence

The Sprint 5 validation posture now includes:

```text
make test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
make system-smoke
make validation-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make docker-test
BUNDLE=/path/to/patch.zip make patch-bundle-hygiene
```

Expected success indicators include:

```text
tests: ok
validate-gadget-fixture: ok
json-smoke: ok
system-binary-smoke: ok
validation-smoke: ok
baseline-smoke benchmark complete
patch-bundle-hygiene: ok
```

## Design decisions confirmed

### Scoring remains heuristic

Scores are ranking hints for triage. They are not exploitability verdicts. The current model intentionally scores exact, conservative semantic facts and leaves uncertain candidates explicit.

### JSON is generated from internal records

Machine-readable output is generated from candidate records and summary fields, not scraped from human-readable text.

### Baseline tooling is optional

ROPgadget, Ropper, and ropr are comparison baselines, not runtime dependencies. The repository can build and validate without them. Benchmark claims require recording which baseline tools were present, their versions, exact commands, target hashes, and environment metadata.

### Docker is a reproducibility layer

WSL2/native Ubuntu remains the preferred daily development path. Docker is used for repeatable build/test checks and reviewer setup. Final publication benchmarks should still run on a stable documented host or clean VM.

## Known limitations at closeout

- The scanner is still pattern/suffix based and is not a full x86_64 decoder.
- Baseline smoke benchmarks are development evidence only.
- Current benchmark output does not yet normalize gadget definitions across tools.
- ropr availability depends on a current Rust/Cargo toolchain.
- Full RELRO, canary, dynamic-table hardening, and deeper mitigation confidence remain future work.
- JSON output is useful for downstream tooling but not yet integrated into SARIF, CI annotations, or vulnerability management workflows.

## Sprint 6 handoff

Sprint 6 should be a checkpoint and integration sprint. The recommended goals are:

1. Freeze and document the current CLI, JSON, scoring, validation, and benchmark-smoke state.
2. Add `analyze` as an integrated text report if it can be done without destabilizing existing commands.
3. Improve report interpretation while preserving conservative language.
4. Prepare a professor/reviewer demo path using controlled fixtures and a small system-binary corpus.
5. Update paper notes with current evidence, limitations, and next benchmark requirements.

Sprint 6 should avoid large architecture changes unless they directly stabilize the current pipeline.
