# Sprint 13 Patch 082 Validation

## Status

Historical implementation candidate; not accepted and superseded by Patch 083.
A later exact-source P082 run completed the retained three-build producer gate
and a separate diagnostic campaign, but the complete native, Docker, parity,
delivery, and independent acceptance boundary did not complete.

## Purpose

Patch 082 corrected the remaining Patch 081 delivery, Docker, nested-authority,
source-root, and producer-oracle findings. It also implements a bounded
controlled coordinate method-discrimination preflight. It changes no analyzer assembly, include file,
public schema, semantic class, score, candidate capacity, or output field.

```text
public fields added:         0
semantic changes:            0
score changes:               0
schema:                      0.2.0
P082 diagnostic campaign:    completed; 0/60 eligible x64lens timings, 0/9 positive cells
P082 acceptance:             not accepted; superseded by P083
```

## Evidence-state vocabulary

- **Artifact-backed** means the Patch 082 tree contains the implemented gate
  definitions and controlled inputs. It does not mean that the full gate set
  has been executed and retained.
- **Cloud-validated** applies only to an explicitly named retained cloud check.
  It is not inferred for Patch 082 from the presence of implementation
  artifacts and does not close the deferred WSL2 checks.
- **Later exact-source evidence** completed the three-build producer gate and a
  separate P082 diagnostic campaign. Docker and exact native/container parity
  remained blocked or incomplete.
- **Accepted** applies here to the Patch 081 findings used as correction inputs,
  not to Patch 081 or Patch 082 as a product checkpoint.
- **Historical handoff** applied to the distinct P083 natural campaign and P083
  exact-source review, not to historical P082 acceptance. Later corrections
  superseded that candidate; P089 is current.

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

The `positive-coordinate-anchor` target name and the `qualified_cells` banner
field are retained command-contract labels. Here they count controlled
method-discrimination cells only; they do not establish natural anchors or
comparative qualification.

## Producer authority

A complete retained local execution materializes three distinct build roots
from one authenticated Git or Git-less source tree. Each root then independently
runs:

```text
make clean
make -j1
make -j1 samples
```

Each resulting analyzer is required to process the 25-pattern score/effect fixture and the
30-pair ordered-pop fixture. The retained reports, binaries, fixtures, source
tree, and build logs are hash-bound. Normalized facts must agree across all
three generations. Score mutation or ordered-pop reordering must be rejected by
producer output, not merely by static catalogs. A later exact-source P082 run
completed all three builds, 90 producer-backed pair observations, and the
complete score/null authority. P083 requires a new run bound to its own tree.

## Coordinate preflight

The controlled preflight generates six deterministic ELF64 targets, two for
each of `ET_EXEC`, PIE-intended `ET_DYN`, and shared-object `ET_DYN`. Each object
contains one executable `pop rdi; ret` at a file offset whose mapped virtual
address is distinct. The gate requires:

```text
8 positive oracle cases
4 one-field mutation rejections
4 semantic negative cases
9 tool-label-by-role cells
2 modeled controlled-target observations per cell
18 cell observations from 6 unique controlled targets
```

This is a controlled method-discrimination gate. The named external tools are
matrix labels and are not executed by the preflight; its observations are not
natural anchors. A fresh authenticated natural campaign is still required
before any comparative coverage claim.

## Historical complete gate

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

Patch 082 was not accepted. Its later three-build and diagnostic-campaign
evidence did not substitute for the incomplete native, Docker, parity, source,
package, delivery, documentation, and independent exact-source boundary. Its
returned findings are correction inputs to Patch 083.
