# Sprint 12 Patch 062 Validation

## Scope

Patch 062 opens Sprint 12 with ordinary program-header validity, explicit ELF64 extended-numbering outcomes, and the smallest confirmed Patch 061 diagnostic/private transaction corrections. It changes no analyzer command, schema, candidate record, score, capacity, arena, decoder, worker, or runtime dependency.

## Source precondition

Apply only to the exact Patch 061 base identified by the delivery source record. The complete Git patch and public final-file overlay are mutually exclusive tracked-source application paths.

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

Expected new analyzer oracle:

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
