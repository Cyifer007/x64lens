# Sprint 12 Patch 062 Validation

## Status

Historical record for the exact Patch 062 source. Its 27-fixture/108-execution
banner applies only to that source boundary. Patch 063 expands the same PHDR
gate to 33 fixtures and 132 executions, and Patch 064 expands it to 49 fixtures
and 196 executions. Patch 064 did not pass validation, Patch 065 required a
further correction, Patch 066 required Patch 067, Patch 067 required Patch 068,
Patch 068 required Patch 069, and Patch 069 required Patch 070. Patch 070 was
rejected after acceptance validation. Patches 070, 071, 072, and 073 were not
accepted at their respective first returned review boundaries. Patch 073
delivered the first custody/isolation correction and policy deferral. Patch 074
was a superseded Sprint 12 closeout candidate. Patch 075 introduced bounded
private static text-relocation evidence, and Patch 076 implemented distinct
private `DT_RPATH` and `DT_RUNPATH` carrier/value evidence. Patch 076's review
required the Patch 077 correction. Patch 078 then became the Sprint 13 entry
candidate, and its review required the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080. Use the
[Patch 089 validation record](sprint-13-patch-089-validation.md) for current
validation expectations.
See [ADR 0048](../adr/0048-phdr-validity-and-extended-numbering-boundary.md)
for the Patch 062 design boundary, the
[Patch 063 validation record](sprint-12-patch-063-validation.md) for the first
intermediate source boundary, and the
[Patch 064 validation record](sprint-12-patch-064-validation.md) for that
intermediate source boundary. The
[Patch 065 validation record](sprint-12-patch-065-validation.md) preserves the
next historical boundary, and the
[Patch 066 validation plan](sprint-12-patch-066-validation.md) preserves the
next intervening candidate boundary, and the
[Patch 067 validation plan](sprint-12-patch-067-validation.md) preserves the
next historical candidate boundary, and the
[Patch 068 validation plan](sprint-12-patch-068-validation.md) preserves the
next historical candidate boundary, and the
[Patch 069 validation plan](sprint-12-patch-069-validation.md) preserves the
next historical candidate boundary, and the
[Patch 070 validation record](sprint-12-patch-070-validation.md) records the
rejected candidate, and the
[Patch 073 validation record](sprint-12-patch-073-validation.md) preserves the
first custody/isolation correction and policy-deferral boundary.

## Scope

Patch 062 opens Sprint 12 with ordinary program-header validity, explicit ELF64 extended-numbering outcomes, and Patch 061 transaction and rollback-destination identity corrections. It changes no CLI syntax or command set, schema, candidate record, score, capacity, arena, decoder, worker, or runtime dependency.

## Source precondition

Patch 062 is defined against Patch 061 closeout commit `1a337b3525e8bdd3cc9007959cd2450185133868`. Verify that repository identity before using this validation record.

## Focused commands

```bash
make patch061-corrective-regression-smoke
make diagnostic-runner-smoke
make diagnostic-transaction-smoke
make provisional-corpus-smoke
make sprint12-phdr-validity-smoke
make research-stage-gates-smoke
make planning-docs-check
```

Historical Patch 062 analyzer oracle:

```text
sprint12-phdr-validity-smoke: ok cases=27 executions=108 ordinary_valid=5 ordinary_malformed=7 extended_unsupported=3 extended_malformed=12
```

The 27 compiler-independent ELF64 fixtures cover:

- `p_align` zero, one, and page alignment;
- entrypoint at executable range start and final included byte;
- zero entrypoint;
- non-power-of-two alignment;
- offset/virtual congruence mismatch;
- virtual-end overflow;
- entrypoint at an exclusive end, in a gap, in a non-executable load, or with no PHDR;
- valid `PN_XNUM`, extended section count, and `SHN_XINDEX` structures;
- reserved ordinary section count/index encodings;
- missing, truncated, wrong-size, non-null, under-reserved, overflowing, and out-of-range extended-numbering structures.

Every case is exercised through `info`, `mitigations`, `gadgets --format json`, and `analyze --format json`. Malformed and unsupported cases require empty stdout plus the exact stable diagnostic.

## Full native validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test
make sprint12-phdr-validity-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

## Docker and parity validation

Discover the active Docker authority first. Native Ubuntu Docker and Docker Desktop are separate environment strata.

```bash
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

## Acceptance

- Every ordinary PHDR rule produces the documented valid or malformed result.
- Structurally valid extended numbering returns exit 6 with no stdout.
- Malformed extended numbering returns exit 5 with no stdout.
- Program headers remain executable authority.
- Candidate 4097 still returns exit 6 before stdout.
- Malformed-input campaigns remain signal-free, bounded, and free of partial stdout.
- Native and Docker facts agree in separately identified environment strata.
- Diagnostic evidence remains development-only and is not merged into Sprint 15-frozen evidence.
