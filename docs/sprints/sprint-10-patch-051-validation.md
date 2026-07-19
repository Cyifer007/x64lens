# Sprint 10 Patch 051 Validation

## Scope

Patch 051 reconciles the completed Patch 050 semantic-family contract with a
candidate-index architectural-effect side-car, centralized fail-fast fixture
orchestration, one-per-pattern coverage, and selective score calibration.

It does not add another primitive family, decoder, worker mode, dynamic runtime
dependency, or schema-version transition.

Related documentation:

- [ADR 0037](../adr/0037-architectural-effects-and-contract-reconciliation.md)
- [Architecture](../architecture.md)
- [Primitive Effect Model](../design/primitive-effect-model.md)
- [Family Coverage Table](../design/sprint10-family-coverage.md)
- [Exact-Pattern Catalog](../design/sprint10-exact-pattern-catalog.md)
- [Scoring Model](../scoring-model.md)
- [Output Contract](../contracts/output-contract.md)
- [JSON Schema Guide](../json-schema.md)
- [Sprint 10 Plan](sprint-10-plan.md)
- [Validation Plan](../validation-plan.md)

## Source base

Patch generation uses committed Patch 050 commit:

```text
4b18dd714af50b69a3b777be65821e2f87a1ea9a
```

The `v0.1.0-dev` tag remains pinned to:

```text
3d54275beb5207d23100d34541970ddc8bcbcead
```

## Record invariants

```text
gadget_record:                    112 bytes
candidate_evidence_record:         48 bytes
memory_effect_record:              16 bytes
candidate_effect_record:           24 bytes
candidate capacity:              4096
analysis arena:                819200 bytes
```

## Focused expected results

```text
json-effect-consistency-smoke: ok positive_reports=6 single_pop_rejections=16 multi_rejections=3 bare_ret_rejections=4 current_family_rejections=6 stack_adjust_rejections=4 memory_rejections=6 architectural_effect_rejections=8

schema-compat-smoke: ok legacy=0.1.0 patch040=0.2.0 patch046=0.2.0 current=0.2.0 transfer=0.2.0 stack_adjust=0.2.0 memory=0.2.0 effects=0.2.0 formal_rejections=17 semantic_rejections=35

sprint10-family-coverage-smoke: ok families=11 fixtures=4 cross_family_promotions=2 fail_fast_recipes=7 scored_policy=explicit false_positive_notes=complete

sprint10-contract-reconciliation-smoke: ok semantic_families=11 exact_patterns=25 fixture_groups=5 semantic=17 exact_only=8 scored=14 model_complete=23 model_partial=2

sprint10-fixture-gate-smoke: ok failed_validator=7 later_steps=0
```

The family-coverage banner counts four family-specific Sprint 10 fixture
expectations. The centralized suite adds the one-per-pattern architectural-
effect fixture as its fifth group.

The one-per-pattern fixture must report:

```text
raw candidates:       25
exact patterns:       25
semantic candidates:  17
unknown candidates:    8
scored candidates:    14
```

## Complete local matrix

```bash
make normalize-perms
make script-perms-check
make ownership-check
make scaffold-check
make diagrams-check
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make clean
make
make samples
make test
make validate-gadget-fixture
make sprint10-primitive-smoke
make sprint10-register-transfer-smoke
make sprint10-stack-adjust-smoke
make sprint10-memory-smoke
make sprint10-architectural-effects-smoke
make sprint10-fixture-gate-smoke
make sprint10-family-coverage-smoke
make sprint10-contract-reconciliation-smoke
make json-effect-consistency-smoke
make schema-compat-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
make benchmark-integrity-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

Docker validation must classify the known Buildx metadata condition separately
from product behavior, then run the complete qualified aggregate when required.

## Acceptance rules

- All 25 pattern IDs produce the expected effect model.
- `gadgets` and `analyze` remain command-only parity matches.
- Multi-pop score is 95 and stack-adjust score is 35 only after exact effect
  validation.
- Transfer and memory families remain unscored.
- Candidate 4097 returns exit 6 with empty stdout and the exact diagnostic.
- Malformed inputs produce no partial report.
- Native and Docker JSON facts agree without semantic normalization.
- No new runtime dependency or worker default is introduced.


## Validation result and Patch 052 handoff

Patch 051 native and qualified Docker validation exposed four corrective
defects: truncated syscall flag descriptors, rejection of `ret imm16 0`, the
wrong text effect separator, and permissive memory side-car reconciliation. It
also showed that numeric score values were not cross-checked by both maintained
contract gates and that strict ShellCheck mode did not independently reject a
missing executable. Patch 052 owns those corrections and the corresponding
regressions.
