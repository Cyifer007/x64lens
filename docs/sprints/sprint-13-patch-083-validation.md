# Sprint 13 Patch 083 Validation

## Status

Implementation candidate. Cloud-supported static, corrective, documentation,
source-recovery, package-application, and natural-campaign self-tests are
required before delivery. Fresh native, Docker, producer, natural-campaign, and
parity acceptance remains environment-specific.

## Purpose

Patch 083 corrects the localized Patch 082 transaction, corpus-oracle, Docker,
producer-custody, source-recovery, and loose-delivery findings. It also adds the
outcome-blind natural positive-coordinate campaign selected by the strategic
audit.

Patch 083 changes no file under `src/`, `include/`, or `schemas/`.

```text
public fields added:     0
semantic changes:        0
score changes:           0
schema:                  0.2.0
candidate capacity:      4096
reference workers:       1
```

## Focused native commands

```bash
make patch082-corrective-regression-smoke
make sprint13-natural-coordinate-campaign-smoke
make patch081-corrective-regression-smoke
make public-docs-check
make planning-docs-check
```

Expected banners include:

```text
patch082-corrective-regression-smoke: ok ...
sprint13-natural-coordinate-campaign-smoke: ok ... cells=9 ... controls=108 ...
```

## Producer authority

A retained producer execution must bind all three independent builds to the
exact candidate tree:

```bash
candidate_tree=$(git write-tree)
S13_EXPECTED_CANDIDATE_TREE="$candidate_tree" \
S13_PRODUCER_RESULT_DIR=/absolute/absent/result \
  make sprint13-producer-authority-smoke
```

The manifest verifies exact modes for the analyzer (`0555`) and retained data
members (`0444`). A foreign source manifest or a mode-mutated analyzer is a
blocking failure.

## Docker correction

```bash
make docker-build
make docker-run-root-smoke
make docker-test
make native-docker-json-parity-smoke
make docker-validation-smoke
```

The image runs as a non-root user. `/work` remains the authenticated source
plane. Mutable builds use ``${HOME}/x64lens-run``, and the dynamic smoke
recreates and executes within that root twice before revalidating `/work`.

## Natural coordinate campaign

The complete campaign requires installed ROPgadget, Ropper, ropr, GNU readelf,
dpkg-query, and the freshly built analyzer:

```bash
S13_NATURAL_COORDINATE_RESULT_DIR=/absolute/absent/result \
  make sprint13-natural-coordinate-campaign
```

A complete environment supplies twelve targets and 48 target/tool processes.
The result retains the complete eligible pool, deterministic selection freeze,
selected target snapshots, readelf facts, tool identities, commands, native
stdout/stderr, normalized relations, nine cell dispositions, and 108 controls.
Unavailable strata are terminal and are never replaced after outcomes.

## Complete acceptance

```bash
make fix-perms
make normalize-perms
make clean
make
make samples
make test
make validation-smoke
make shellcheck-smoke
make docker-validation-smoke
S13_NATURAL_COORDINATE_RESULT_DIR=/absolute/absent/result \
S13_PRODUCER_RESULT_DIR=/absolute/absent/producer \
S13_EXPECTED_CANDIDATE_TREE=$(git write-tree) \
  make sprint13-p083-acceptance-smoke
```

## Failure expectations

- A same-tree but different base commit is rejected.
- Patch-path parent or file rebinding after check-only validation is rejected.
- A post-effect status-write failure restores the exact prior state.
- Multiple `.PHONY` declarations are parsed as one authority set.
- Candidate recovery succeeds under umask `0777` with canonical final modes and
  no staging residue.
- A foreign producer tree or mode-mutated analyzer is rejected.
- Docker validation cannot recreate a run root beneath `/`.
- Natural target selection cannot reroll after tool outcomes.
- Candidate 4097 still exits 6 before stdout; malformed input emits no partial
  report.

## Acceptance banner

```text
sprint13-p083-acceptance-smoke: ok patch=83 sprint12=closed sprint13=active natural-coordinate-campaign=complete public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```
