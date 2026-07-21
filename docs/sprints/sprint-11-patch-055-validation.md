# Sprint 11 Patch 055 Validation

## Status

Implementation candidate for the first Sprint 11 diagnostic benchmark tranche.

## Purpose

Patch 055 adds the high-resolution diagnostic runner foundation, initial task-
scope authority, and the smallest durable corrections for two Patch 054
validation false negatives. It changes no analyzer assembly, CLI field, schema,
semantic class, score, candidate capacity, decoder policy, or worker policy.

## Files and boundaries under test

```text
benchmarks/scripts/diagnostic-runner.py
  external standard-library process measurement and artifact publication

benchmarks/specs/sprint11-reference-diagnostic.json
  provisional x64lens gadget/analyze JSON conditions

benchmarks/task-definitions/sprint11-diagnostic-tasks.json
  machine-readable task status and comparison boundary

tools/research-roadmap-consistency-smoke.py
  broad and path-specific chronology rejection

tools/sprint10-closeout-smoke.py
  source-, fixture-, and summary-linked Sprint 10 reconciliation
```

The x64lens binary remains the unchanged dependency-free reference profile.

## Focused validation

```bash
make diagnostic-tools-check
make patch054-corrective-regression-smoke
make diagnostic-task-definitions-smoke
make diagnostic-runner-smoke
make sprint11-diagnostic-reference-smoke
make research-roadmap-consistency-smoke
make sprint10-closeout-smoke
```

Expected focused results:

```text
patch054-corrective-regression-smoke: ok roadmap_cases=7 closeout_cases=3
diagnostic-task-definitions-smoke: ok tasks=3 implemented=2 unavailable=1 baselines=3 frozen=false
diagnostic-runner-smoke: ok success_rows=6 failure_rows=2 overwrite_rejected=1 descendants_cleaned=1 invalid_specs_rejected=2 source_mutations_rejected=1 unsafe_artifacts_rejected=1
sprint11-diagnostic-reference-smoke: ok rows=8 warmup=2 measured=6 parity_pairs=4
research-roadmap-consistency-smoke: ok documents=28 milestones=5 forbidden_patterns=9 path_claims=7 completed_sprints=10 active_sprint=11
sprint10-closeout-smoke: ok sprint=10 patches=9 families=11 exact_patterns=25 semantic=17 exact_only=8 scored=14 model_complete=23 model_partial=2 fixture_groups=5 next_sprint=11
```

## Runner contract checks

The diagnostic runner smoke must prove:

- retained runner, exact campaign specification, tool, target, and timer-probe
  files match their source SHA-256 values;
- tools, targets, and timer probes execute through write-sealed Linux `memfd`
  copies whose identities match the retained files;
- the diagnostic platform check executes an explicitly requested `MFD_EXEC`
  memfd where supported and preserves an older-kernel `EINVAL` fallback;
- version output contains the declared tool version;
- timer-floor probes preserve every sample;
- warmup rows are retained but excluded from the primary measured set;
- alternating order reverses the second measured round;
- each child uses isolated home, temporary, cache, configuration, and data
  roots under its retained work directory;
- process stdout and stderr sizes and hashes match retained artifacts;
- transient retained-file mutation cannot change the bytes consumed by a
  measured child, and persistent version, timer, or prior-row artifact mutation
  rejects publication;
- schema `0.2.0` count extraction occurs after timing;
- a nonzero exit and a timeout both remain in `rows.tsv`;
- timeout cleanup terminates and reaps a descendant that escapes the measured process group;
- failed campaigns publish complete evidence and return the configured failure
  status;
- an existing campaign directory cannot be overwritten;
- a diagnostic specification cannot opt into frozen or publication-eligible evidence;
- reserved locale, path, home, temporary, and XDG environment keys cannot be
  overridden by a condition;
- mutation of the source specification during execution fails before publication;
- omission of the required `publication_eligible:false` declaration rejects the
  specification;
- a symlink or other non-regular file in the result tree rejects publication;
- no staging directory remains after success or failure.

The measured-child integrity tests do not model a concurrent external writer
with the same user identity. Run the campaign in an unshared workspace and
reauthenticate retained evidence before any later promotion.

## Reference diagnostic command

After a clean build and fixture generation:

```bash
make bench-diagnostic-smoke
```

A stable local identifier may be supplied when reproducibility requires it:

```bash
DIAGNOSTIC_CAMPAIGN_ID=s11-p055-reference-001 \
  make bench-diagnostic-smoke
```

The resulting ignored campaign tree contains:

```text
manifest.json
rows.tsv
timer-floor.json
inputs/tools/
inputs/targets/
inputs/versions/
outputs/
```

This reference command measures only the two truthful implemented JSON command
conditions. It does not claim scanner-only timing or baseline comparability.

## Aggregate validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make public-docs-check
make planning-docs-check
make clean
make
make samples
make test
make diagnostic-runner-smoke
make diagnostic-task-definitions-smoke
make sprint11-diagnostic-reference-smoke
make patch054-corrective-regression-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

Container validation remains a separate reproducibility condition:

```bash
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

## Acceptance criteria

- Every focused and aggregate gate exits 0.
- The diagnostic tool check requires only the assembler/linker, sample compiler,
  Make, and Python standard library; unrelated comparison tools do not gate the
  reference campaign.
- A clean NASM build and controlled fixture build pass before the reference
  campaign is run.
- Diagnostic rows are explicitly mutable, unfrozen, and not publication
  eligible.
- Failed rows are retained and neither same-group nor escaped descendants survive cleanup.
- Commands and artifact paths remain resolvable after transactional publication.
- The two Patch 054 false-negative probes now fail for the intended reason.
- Source record definitions, Makefile versions, canonical JSON, catalogs, and
  closeout summaries agree.
- Existing capacity, malformed-input, no-partial-output, schema, and native/
  container parity contracts remain unchanged.

## Deferred Sprint 11 work

- provisional GCC and Clang corpus generation;
- baseline adapter and version-lock implementation;
- development summary statistics;
- capability and performance gap register;
- any reviewed scanner-only instrumentation or batching profile.
