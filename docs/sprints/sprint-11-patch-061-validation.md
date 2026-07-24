# Sprint 11 Patch 061 Validation

## Purpose

Patch 061 corrects the remaining Sprint 11 transaction, campaign-accounting,
coordinate, runtime-closure, and private-rollback findings; records the
below-floor measurement policy; and closes the diagnostic benchmark sprint.
It changes no analyzer behavior or public JSON schema.

## Focused commands

```bash
make diagnostic-task-definitions-smoke
make diagnostic-runner-smoke
make diagnostic-transaction-smoke
make provisional-corpus-smoke
make runtime-closure-venv-smoke
make sprint11-below-floor-policy-smoke
make sprint11-campaign-plan-smoke
make sprint11-measurement-plane-smoke
make sprint11-p060-campaign-smoke
make sprint11-closeout-smoke
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
make planning-docs-check
```

Expected closeout result:

```text
sprint11-closeout-smoke: ok sprint=11 patches=7 corpus_targets=24 planned_conditions=30 baseline_adapters=3 relation_authorities=4 selected_priorities=3 next_sprint=12
```

## Transaction requirements

- Input and output path ancestors are opened without following symbolic links.
- A staging object is identified by its creation-time device and inode.
- Cleanup refuses to remove an object whose identity no longer matches.
- Publication authenticates the committed object and preserves an unrelated
  replacement.
- An early signal, repeated interruption, post-rename failure, or foreign-stage
  substitution leaves either the prior result, one complete new result, or an
  explicit failure without deleting unrelated state.

## Campaign requirements

- The official ROPgadget 7.7 version banner is accepted without editing the
  tracked authority.
- All 30 conditions are accounted for.
- Native execution and comparison qualification remain separate states.
- Below-floor successful rows are counted and retained correctly.
- Coordinate qualification requires positive role-controlled evidence.
- Python console entrypoints retain isolated-environment interpreter context.
- Runtime-closure and relation artifacts contain no stale staging paths.
- Every imported generator is bound in the campaign manifest.
- Recursive `gadget_count` keys are rejected.
- Summary and gap-register generation remain deterministic and derived from raw
  retained evidence.

## Analyzer no-regression requirements

```bash
make clean
make
make samples
make test
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

The 4,096-candidate complete report and 4,097th-candidate exit `6` behavior must
remain unchanged. Malformed parse failures must emit no partial stdout.

## Container and parity requirements

```bash
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

A Docker engine or metadata-path limitation is an environment result only when
a complete qualified rerun succeeds.

## Corrected all-tools campaign

With the exact pinned baselines installed:

```bash
REQUIRE_BASELINES=1 make baseline-tools-check
campaign="s11-p061-local-$(date -u +%Y%m%dT%H%M%SZ)"
S11_P060_CAMPAIGN_ID="$campaign" \
REQUIRE_BASELINES=1 \
make bench-sprint11-provisional-campaign
```

Acceptance requires:

- 30 accounted and executed conditions;
- 24 normalized relation artifacts;
- five complete task-path runtime closures;
- explicit coordinate state for all three target roles;
- no silently discarded failure;
- a valid checksum inventory;
- diagnostic, unfrozen, publication-ineligible identity.

A lack of positive anchors may correctly leave address intersections blocked. It
must not be reported as qualified calibration.

## Evidence classification

Patch 061 and its campaign remain diagnostic development evidence. They do not
support preview or publication claims about speed, RSS, coverage, superiority,
or defensive usefulness.
