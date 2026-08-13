# Sprint 13 Patch 084 Validation

## Status

Historical implementation candidate. Patch 084 did not complete exact-source
acceptance; Patch 085 carries the bounded corrective and evidence-authority
tranche. The commands below are retained as historical candidate gates, not as
evidence that the P084 aggregate executed or passed.

## Scope

Patch 084 corrects the Patch 083 source, transaction, recovery, Docker, natural-campaign, and delivery findings. It freezes a private 36-query ABI-role contract and a lifecycle/denominator continuity authority. It changes no runtime analyzer source, include contract, schema, public field, semantic class, score, candidate capacity, decoder profile, or worker policy.

## Source preconditions

```text
branch: main
base HEAD: 64193f4979d68b30af25d17ef934bf6a4e89b76e
base tree: 1369bf61a5381adb129198db316f20e281a91c07
tracked state: clean
```

The committed base tracks one generated ordered-pair binary in conflict with
the tracked-source boundary. Patch 084 removes it from tracked source and
reserves its path for generated output.

## Focused validation

```bash
make patch083-corrective-regression-smoke
make sprint13-natural-coordinate-campaign-smoke
make sprint13-abi-role-query-contract-smoke
make sprint13-lifecycle-denominator-smoke
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
```

Expected focused banners include:

```text
patch083-corrective-regression-smoke: ok ...
sprint13-natural-coordinate-campaign-smoke: ok ...
sprint13-abi-role-query-smoke: ok queries=36 development=24 confirmation=12 ...
sprint13-lifecycle-denominator-smoke: ok roots=20 leaves=30 aliases=29 ...
```

## Native validation

```bash
make fix-perms
make normalize-perms
make clean
make
make samples
make test
make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

The fresh analyzer is required for the 96-command ABI-role closure gate that
confirms unchanged public text and JSON:

```bash
mkdir -p .local/p084-results
S13_EXPECTED_CANDIDATE_TREE=178f1d1c93a5a05fba5a77af2c378e63e5dc017b \
S13_ABI_ROLE_RESULT_DIR=./.local/p084-results/abi-role-closure \
  make sprint13-abi-role-query-smoke
```

## Natural campaign

The campaign retains terminal states even when comparison qualification fails:

```bash
mkdir -p .local/p084-results
S13_EXPECTED_CANDIDATE_TREE=178f1d1c93a5a05fba5a77af2c378e63e5dc017b \
S13_NATURAL_COORDINATE_RESULT_DIR=./.local/p084-results/natural-structural \
  make sprint13-natural-coordinate-campaign-structural
```

This requires twelve selected targets, 48 tool executions, nine terminal cell
dispositions, and 108 controls. The retained P083 result has zero qualified,
five insufficient, and four unavailable cells. Structural completion does not
require nine qualified cells and authorizes no comparative claim.

The stricter historical comparison-qualification entry point remains:

```bash
mkdir -p .local/p084-results
S13_EXPECTED_CANDIDATE_TREE=178f1d1c93a5a05fba5a77af2c378e63e5dc017b \
S13_NATURAL_COORDINATE_RESULT_DIR=./.local/p084-results/natural-qualified \
  make sprint13-natural-coordinate-campaign
```

That command fails after retaining the result unless all nine cells qualify.

## Docker and parity validation

```bash
S13_EXPECTED_CANDIDATE_TREE=178f1d1c93a5a05fba5a77af2c378e63e5dc017b make docker-build
make docker-run-root-smoke
make docker-source-custody-smoke
make docker-test
make docker-validation-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
```

The immutable source plane must remain root-owned and unwritable to the runtime user. Mutable work remains beneath the separate run root.

## Historical candidate aggregate

```bash
mkdir -p .local/p084-results
S13_EXPECTED_CANDIDATE_TREE=178f1d1c93a5a05fba5a77af2c378e63e5dc017b \
S13_ABI_ROLE_RESULT_DIR=./.local/p084-results/abi-role-acceptance \
S13_NATURAL_COORDINATE_RESULT_DIR=./.local/p084-results/natural-acceptance \
S13_PRODUCER_RESULT_DIR=./.local/p084-results/producer-acceptance \
  make sprint13-p084-acceptance-smoke
```

Historical candidate banner (not observed by this record):

```text
sprint13-p084-acceptance-smoke: ok patch=84 sprint12=closed sprint13=active natural-coordinate-campaign=terminal-diagnostic abi-role-queries=36 public-closures=96 lifecycle-prefix=preserved public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

## Failure expectations

- A generated toy binary cannot re-enter tracked source unnoticed.
- Campaign authority mutations, foreign source trees, and comparison-incomplete results fail their corresponding gates.
- Post-effect patch-path parent or leaf replacement prevents success publication.
- Corrupt same-size source members leave no owned recovery residue.
- A Docker context built from a tree other than the expected candidate is rejected before publication.
- The runtime user cannot write authenticated `/work` source.
- Candidate 4097 still exits 6 before stdout; malformed parser failures emit no partial report.

## Evidence classification

Patch 084 did not complete these native, Docker, parity, campaign, delivery, and
independent gates. Static and corrective checks alone do not establish product
acceptance. Its retained diagnostic terminal states remain publication-ineligible.
