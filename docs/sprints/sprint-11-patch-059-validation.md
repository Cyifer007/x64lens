# Sprint 11 Patch 059 Validation

## Patch goal

Correct the remaining Patch 058 diagnostic transaction and adapter-binding
failures, then establish the stage-zero measurement plane required before a
corpus-wide comparison or engineering gap register is generated.

Patch 059 does not change analyzer assembly, CLI behavior, schema `0.2.0`,
semantic classes, scores, record sizes, candidate capacity, command arena,
decoder policy, or worker policy.

## Implemented surfaces

- campaign-bound baseline normalization;
- exact baseline version evidence and raw-line limits before ANSI handling;
- native `retq` preservation with explicit canonical `ret` relation text;
- matched x64lens relation extraction with virtual and file-offset coordinates;
- bounded runtime-closure manifests;
- role-specific address-coordinate calibration;
- corrected six-target, 24-comparison plus six-control campaign plan;
- runner and corpus transaction ownership hardening;
- duplicate corpus-tool record rejection;
- durable regression coverage for each changed failure path.

## Focused commands

```bash
make script-perms-check
make scaffold-check
make diagnostic-task-definitions-smoke
make baseline-output-adapter-smoke
make diagnostic-runner-smoke
make diagnostic-transaction-smoke
make provisional-corpus-smoke
make sprint11-measurement-plane-smoke
make sprint11-campaign-plan-smoke
make public-docs-check
make planning-docs-check
git diff --check
```

## Expected focused results

```text
diagnostic-task-definitions-smoke: ok
  tasks=3
  implemented=2
  unavailable=1
  baselines=3
  baseline_adapters=3
  relation_authorities=4
  implemented_relations=3
  unavailable_relations=1
  x64lens_relation=1
  runtime_closure=1
  coordinate_roles=3
  exact_command_probe=1
  frozen=false

baseline-output-adapter-smoke: ok
  tools=3
  controlled_records=15
  exact_relation_precision=1.000
  exact_relation_recall=1.000
  adversarial_cases=7
  runner_binding=1
  raw_line_bound=1
  exact_version=1
  retq_canonicalized=1
  generic_counts=0

diagnostic-transaction-smoke: ok
  future_paths=2
  stage_identity=1
  publish_substitution=1
  post_rename_error=1
  partial_create=1
  early_stage_signal=1
  interruption_cleanup=2

provisional-corpus-smoke: ok
  targets=24
  rebuilds=2
  invalid_specs=8
  tamper_cases=5
  interruption_cleanup=3
  capture_limits=1
  retained_limits=2
  clean_guards=1
  make_clean_guards=1
  membership_rejections=1
  stage_substitution=1
  early_signals=1
  post_publish_commit=1
  publish_substitution=1
  duplicate_tool_records=1

sprint11-measurement-plane-smoke: ok
  targets=3
  runner_rows=12
  relation_artifacts=12
  runtime_closures=4
  coordinate_roles=3
  calibrated_tools=2
  mismatch_controls=1
  adversarial_cases=2
  generic_counts=0

sprint11-campaign-plan-smoke: ok
  targets=6
  comparative_conditions=24
  analyze_controls=6
  total_conditions=30
  coordinate_roles=3
  closure_tools=4
  generic_counts=0
  frozen=false
```

The diagnostic-runner banner also retains target nonexecution, bounded output,
child cleanup, stage substitution, future-stream symlink, and post-publication
commit probes.

## Full native acceptance

```bash
make normalize-perms
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

Acceptance requires unchanged analyzer behavior:

```text
candidate capacity: 4096
candidate 4097: exit 6 before stdout
malformed parse failure: no partial stdout
tool version: 0.1.0-dev
schema version: 0.2.0
command arena: 819200 bytes
```

## Docker and parity acceptance

```bash
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

A known read-only Buildx metadata-path failure is an environment classification
only when the complete qualified writable-metadata rerun passes. The default
failure and qualified rerun must both be retained.

## Optional baseline validation

When pinned ROPgadget, Ropper, and ropr executables are available, validate:

- exact version output and command identity;
- one campaign-bound normalization artifact per measured row;
- runtime closure for each exact tool identity;
- native-output retention and duplicate metrics;
- role-specific address-coordinate calibration;
- no unlabeled cross-tool gadget count.

Absence of optional baseline tools does not invalidate the stage-zero
implementation, but it prevents the 30-condition campaign from running.

## Evidence classification

All Patch 059 rows and derived artifacts remain diagnostic development evidence:

```text
evidence_class: diagnostic
frozen: false
publication_eligible: false
```

They cannot support release-facing performance, memory, coverage, or superiority
claims and cannot be relabeled into the Sprint 15-frozen dataset.

## Known limitations

- The baseline parsers normalize represented text; they do not decode target
  bytes.
- Runtime closure may be partial.
- Address coordinates may remain ambiguous, mismatch, or insufficient.
- The stage-zero smoke uses controlled fake baseline tools.
- Corpus-wide summaries and the engineering gap register remain the next
  implementation tranche.
- A hostile same-UID baseline is outside the object-nonexecution guarantee.

## Handoff

On acceptance, the next patch runs the authenticated 30-condition provisional
diagnostic plan where baseline tools are available, generates task-scoped
summaries from preserved raw rows and relation artifacts, and writes the
engineering gap register that directs Sprints 12 through 14. Sprint 11 closeout
follows that campaign rather than sharing the same patch.
