# Sprint 11 Patch 060 Validation

## Purpose

Validate the remaining Patch 059 evidence-integrity corrections and the
authenticated provisional 30-condition campaign, generated task summaries, and
engineering gap register without changing analyzer behavior or promoting
diagnostic evidence into release claims.

## Source boundary

Patch 060 is based on the accepted Patch 059 source. It changes external
benchmark, corpus, normalization, calibration, closure, validation, planning,
and documentation surfaces only.

The analyzer contract remains:

```text
tool version: 0.1.0-dev
schema version: 0.2.0
candidate capacity: 4096
command arena: 819200 bytes
reference profile: dependency-free, decoder-free, one worker
```

Candidate 4097 must still return exit code `6` before stdout. Malformed parse
failures must not emit partial stdout.

## Focused commands

```bash
make script-perms-check
make diagnostic-task-definitions-smoke
make baseline-output-adapter-smoke
make diagnostic-runner-smoke
make diagnostic-transaction-smoke
make provisional-corpus-smoke
make sprint11-measurement-plane-smoke
make patch059-corrective-regression-smoke
make sprint11-campaign-plan-smoke
make sprint11-p060-campaign-smoke
```

Expected focused banners include:

```text
patch059-corrective-regression-smoke: ok components=7

sprint11-measurement-plane-smoke: ok targets=3 runner_rows=12
relation_artifacts=12 runtime_closures=4 coordinate_roles=3
calibrated_tools=2 mismatch_controls=1 adversarial_cases=3
source_drift=1 forged_relations=1 generic_counts=0

sprint11-p060-campaign-smoke: ok conditions=30 native_rows=30
relations=24 runtime_closures=5 coordinate_qualified=1 gap_register=1
unavailable_tools=0 generic_counts=0
```

## Real provisional campaign

Build or reauthenticate the corpus and analyzer, then run:

```bash
make provisional-corpus-verify
make bench-sprint11-provisional-campaign
```

Installed pinned baselines are passed automatically. Missing baselines remain
explicit unavailable conditions. They must not be replaced by a different
version or synthetic output in retained diagnostic evidence.

The result must contain:

```text
manifest.json
condition-accounting.tsv
condition-accounting.json
runner-results/<campaign>-native/rows.tsv
relations/*.json
runtime-closures/*.json
coordinate/status.json or coordinate/address-coordinate-calibration.json
summaries/task-summary.tsv
summaries/task-summary.json
summaries/task-summary.md
engineering-gap-register.json
engineering-gap-register.md
SHA256SUMS.txt
```

Acceptance requires exactly 30 accounted conditions, every native row retained,
24 relation artifacts when all four tools execute successfully, task-path
runtime closure, explicit coordinate status, no generic gadget count, generated
summaries, and a diagnostic gap register. Missing tools and below-floor rows are
valid recorded states, not successful comparative measurements.

## Corrective adversarial requirements

Validation must reject:

- baseline version commands that differ from task authority;
- symlinked ancestors in artifact paths;
- normalized relation fields that cannot be reproduced from retained native
  rows;
- runtime-closure provenance derived from a mutated source entrypoint instead
  of the retained execution snapshot;
- runner or corpus publication of a substituted foreign stage;
- post-rename durability or authentication failures reported as success;
- rollback removal of a substituted directory;
- caller-dependent or incomplete delivery checksum paths.

## Complete acceptance matrix

```bash
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

## Evidence interpretation

Patch 060 is mutable diagnostic evidence only. Task summaries may report wall,
CPU, RSS, output, result, and normalized relation facts under exact task scope.
They must not claim causality from the six-target screen or support preview,
publication, superiority, or analyst-utility conclusions.

## Next step

After Lane A acceptance and Markdown reconciliation, Patch 061 closes Sprint 11
and hands the evidence-backed priorities to Sprint 12. It should not implement
Sprint 12 loader or mitigation changes inside the closeout patch.
