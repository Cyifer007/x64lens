# Sprint 13 Patch 082 Validation

## Status

Implementation candidate pending complete exact-source native, Docker, parity,
delivery, and independent validation.

## Purpose

Patch 082 corrects the remaining Patch 081 delivery, Docker, nested-authority,
source-root, and producer-oracle findings. It also executes a bounded controlled
positive-coordinate preflight. It changes no analyzer assembly, include file,
public schema, semantic class, score, candidate capacity, or output field.

## Focused commands

```bash
make patch081-corrective-regression-smoke
make sprint13-positive-coordinate-anchor-smoke
make sprint13-producer-authority-smoke
make public-docs-check
make planning-docs-check
```

Expected banners include:

```text
patch081-corrective-regression-smoke: ok ...
sprint13-positive-coordinate-anchor-smoke: ok ... cells=9 qualified_cells=9 ...
sprint13-producer-authority-smoke: ok generations=3 ... producer_backed=1 ...
sprint13-ordered-two-pop-role-task-value-smoke: ok ... producer_pair_checks=90 ...
sprint13-score-null-authority-smoke: ok ... producer_rejections=75 ...
```

## Producer authority

Three distinct build roots are materialized from one authenticated Git or
Git-less source tree. Each root independently runs:

```text
make clean
make -j1
make -j1 samples
```

Each resulting analyzer processes the 25-pattern score/effect fixture and the
30-pair ordered-pop fixture. The retained reports, binaries, fixtures, source
tree, and build logs are hash-bound. Normalized facts must agree across all
three generations. Score mutation or ordered-pop reordering must be rejected by
producer output, not merely by static catalogs.

## Coordinate preflight

The controlled preflight generates six deterministic ELF64 objects, two for
each of `ET_EXEC`, PIE-intended `ET_DYN`, and shared-object `ET_DYN`. Each object
contains one executable `pop rdi; ret` at a file offset whose mapped virtual
address is distinct. The gate requires:

```text
8 positive oracle cases
4 one-field mutation rejections
4 semantic negative cases
9 baseline-by-role cells
2 distinct controlled targets per cell
18 cell-anchor observations from 6 unique controlled targets
```

This is controlled diagnostic evidence. A fresh authenticated natural campaign
is still required before any comparative coverage claim.

## Complete local validation

```bash
make fix-perms
make normalize-perms
make clean
make
make samples
make test
make validation-smoke
make shellcheck-smoke
make docker-build
make docker-test
make docker-validation-smoke
make sprint12-external-natural-acquisition-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
make sprint13-p082-acceptance-smoke
```

## Failure expectations

- Git-less manifest/root mismatches fail closed.
- Docker build outputs never change the pristine source authority.
- Nested Make invocations cannot overwrite caller-selected authority files.
- Ordinary extraction must satisfy package custody without a special mode flag.
- Loose helpers must use Patch-scoped names and match package bytes.
- Producer score or tuple mutations must fail.
- Candidate 4,097 returns exit code 6 before stdout.
- Malformed inputs emit no partial stdout.

## Acceptance

Patch 082 is accepted only when native, Docker, parity, source, package,
capacity, malformed-input, documentation, and independent exact-source evidence
agree on one candidate tree.
