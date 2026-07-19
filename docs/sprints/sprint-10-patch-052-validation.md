# Sprint 10 Patch 052 Validation

## Scope

Patch 052 corrects the Patch 051 architectural-effect and validation findings.
It adds no primitive family, decoder, worker mode, dynamic runtime dependency,
or schema-version transition.

Related documentation:

- [ADR 0038](../adr/0038-patch051-corrective-effect-and-gate-hardening.md)
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

Patch generation uses committed Patch 051 commit:

```text
0ff475bb6ee2850fd43ef455472f20f2e302e558
```

The `v0.1.0-dev` tag remains pinned to:

```text
3d54275beb5207d23100d34541970ddc8bcbcead
```

## Preserved record invariants

```text
gadget_record:                    112 bytes
candidate_evidence_record:         48 bytes
memory_effect_record:              16 bytes
candidate_effect_record:           24 bytes
candidate capacity:              4096
analysis arena:                819200 bytes
tool version:              0.1.0-dev
schema version:                  0.2.0
```

## Focused corrective gates

```bash
make memory-effect-reconciliation-smoke
make sprint10-score-policy-smoke
make shellcheck-contract-smoke
make sprint10-architectural-effects-smoke
make json-effect-consistency-smoke
make sprint10-contract-reconciliation-smoke
```

Expected stable results:

```text
memory-effect-reconciliation-smoke: ok cases=7 accepted=2 rejected=5
sprint10-score-policy-smoke: ok mutations=2 gates=2 checks=4
shellcheck-contract-smoke: ok strict_missing=reject advisory_missing=skip
```

The one-per-pattern fixture includes a valid zero-immediate return:

```text
bytes: c2 00 00
stack delta: 8
score: 40
```

The syscall candidate must preserve all represented flag-read names:

```text
cf, pf, af, zf, sf, tf, if, df, of
```

Text side-effect lists use comma-space separators. Register sets retain the
pipe separator.

## Complete native matrix

```bash
make normalize-perms
make script-perms-check
make ownership-check
make scaffold-check
make diagrams-check
make public-docs-check
make public-docs-hygiene-smoke
make public-artifact-content-smoke
make planning-docs-check
make clean
make
make samples
make test
make validate-gadget-fixture
make semantic-smoke
make sprint10-primitive-smoke
make sprint10-register-transfer-smoke
make sprint10-stack-adjust-smoke
make sprint10-memory-smoke
make sprint10-family-coverage-smoke
make sprint10-architectural-effects-smoke
make sprint10-fixture-gate-smoke
make sprint10-contract-reconciliation-smoke
make sprint10-score-policy-smoke
make memory-effect-reconciliation-smoke
make shellcheck-contract-smoke
make json-effect-consistency-smoke
make schema-compat-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
make benchmark-integrity-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

## Docker matrix

Container acceptance requires the complete build, test, context-hygiene,
aggregate-validation, and native/container byte-parity paths to pass.

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

## Acceptance rules

- NASM emits no number-overflow warning; the warning class is fatal.
- `ret imm16 0` succeeds in text and JSON and retains stack delta 8.
- Syscall effects retain the complete represented flag mask and score only when
  the complete expected descriptor agrees.
- Text side-effect lists use comma-space separators.
- Direction conflicts, reserved bits, nonzero displacement, base mismatch, and
  wrong-index memory records return the internal bounds status.
- Ordered multi-pop score 95 and stack-adjust score 35 are enforced by both
  family and exact-pattern contract gates.
- Transfer and memory families remain unscored.
- Candidate 4097 returns exit 6 before stdout.
- Malformed inputs emit no partial report.
- Native and qualified Docker facts agree without semantic normalization; the 12 controlled report pairs are byte-identical.
- No new runtime dependency or worker default is introduced.

## Handoff

Patch 053 performs the architecture and capability reassessment. Patch 054
closes Sprint 10 after the reassessment is reconciled.
