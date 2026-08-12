# Sprint 13 Patch 083 Validation

## Status

Implementation candidate with artifact-backed corrective and natural-campaign
gate definitions. Exact-source native, Docker, producer, natural-campaign,
parity, delivery, documentation, and independent acceptance remain pending
against one Patch 083 candidate tree. Environment-specific unavailability is
blocked evidence, not acceptance.

## Purpose

Patch 083 corrects the localized Patch 082 transaction, corpus-oracle, Docker,
producer-custody, source-recovery, and loose-delivery findings. It also adds the
outcome-blind natural positive-coordinate campaign selected as the next bounded
diagnostic gate.

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
expected_candidate_tree=39671c27342a1c093de2e37806e58bdf209677d2
test "$(git write-tree)" = "$expected_candidate_tree"
S13_EXPECTED_CANDIDATE_TREE="$expected_candidate_tree" \
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

A complete retained run requires all four analyzer/baseline executables and
supplies twelve targets and 48 target/tool executions. Missing role strata are
explicit selection shortfalls, and a missing executable blocks launch rather
than becoming retained campaign evidence. The result retains the complete
eligible pool, deterministic selection freeze,
selected target snapshots, readelf facts, tool identities, commands, native
stdout/stderr, normalized relations, nine cell dispositions, and 108 controls.
After selection, nonzero exits, parse failures, empty relations, unavailable
observations, ambiguous coordinates, and mismatches are terminal; selected
targets are never replaced or rerolled after outcomes.

## Candidate gate aggregate

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
expected_candidate_tree=39671c27342a1c093de2e37806e58bdf209677d2
test "$(git write-tree)" = "$expected_candidate_tree"
S13_NATURAL_COORDINATE_RESULT_DIR=/absolute/absent/result \
S13_PRODUCER_RESULT_DIR=/absolute/absent/producer \
S13_EXPECTED_CANDIDATE_TREE="$expected_candidate_tree" \
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

## Candidate aggregate banner

```text
sprint13-p083-acceptance-smoke: ok patch=83 sprint12=closed sprint13=active natural-coordinate-campaign=complete public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

Within this banner, `complete` means that the fixed 12-target, 48-execution
denominator, nine cell dispositions, and 108 controls are accounted for. It
does not mean comparison-qualified, confirmatory, frozen, publication-eligible,
or independently accepted. A successful aggregate is necessary but not
sufficient: it does not by itself close Sprint 12, activate Sprint 13, or
replace independent exact-source review.

## Patch 084 handoff

Patch 084 is conditional on the independent exact-source P083 result. If review
returns corrections, P084 carries only the smallest corrective tranche. If P083
is accepted, P084 may begin separately reviewed reconciliation of the retained
natural-coordinate terminal states and freeze a named ABI-role consumer/
equivalence contract. Neither branch authorizes a public-field, semantic, score,
schema, capacity, decoder, concurrency, comparative-coverage, performance, or
exploitability change.
