# Sprint 12 Patch 077 Validation

## Purpose

Historical implementation candidate. Patch 077 was a Sprint 12 reconciliation
candidate, but its review required the Patch 078 closeout
correction and Sprint 13 entry candidate. Patch 077 preserved the Patch 076
private textrel/RPATH/RUNPATH implementation and corrected the application,
recovery, custody, permission, comparator, parity, Docker-build, and evidence
boundaries then known to block acceptance.

## Source boundary

Patch 077 changes no tracked analyzer source under `src/`, no NASM ABI include,
and no public JSON schema. The runtime binary produced from the candidate is
therefore expected to preserve Patch 076 analysis behavior exactly. Fresh build
and parity evidence are still required because acceptance is tied to the exact
candidate source and environment.

## Focused corrective gate

```bash
make patch076-corrective-regression-smoke
```

Expected result:

```text
patch076-corrective-regression-smoke: ok ...
```

The gate covers:

- patch-path replacement after forward and reverse dry runs;
- descriptor-bound recovery and no-replace publication;
- symlinked ancestors, destination/root replacement, final-byte mutation, and
  foreign-replacement cleanup;
- retained-inode permission rollback under unrelated directory churn;
- custody cleanup substitution and unrelated ancestor churn;
- all eleven deterministic private failure-prefix snapshots;
- nonzero GNU `readelf` exit rejection in both dynamic-metadata oracles;
- Git-independent parity source custody, no-replace publication, and mount
  isolation; and
- generalized dynamic-string labels after the Patch 064/065 parser evolution.

## Private dynamic-metadata gates

```bash
make sprint12-dynamic-metadata-layout-smoke
make sprint12-textrel-smoke
make sprint12-search-path-smoke
make sprint12-textrel-readelf-oracle
make sprint12-search-path-readelf-oracle
```

Expected retained boundaries:

```text
dynamic context bytes:       9904
private context bytes:      13064
mixed carrier capacity:        64
search record capacity:        64
search value-byte capacity:  4096
public fields added:             0
```

The textrel matrix retains 24 fixtures. The search-path matrix retains 36
fixtures and 144 public command outcomes. Eligible external matches require a
successful `readelf -dW` process; valid-looking output from a nonzero process is
not agreement evidence.

## Native and Docker validation

```bash
make clean
make
make samples
make test
make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make docker-build
make docker-test
make docker-validation-smoke
```

Docker targets must leave the host native `build/` tree unchanged. A clean
native rebuild after Docker remains a useful independent check, but it is not a
repair for host contamination because Patch 077 removes that contamination
path.

## Private parity and acquisition

```bash
ROLE_PROPERTY_EXTERNAL_NATURAL_RESULT_DIR=./.local/p077-results/external-natural \
  make sprint12-external-natural-acquisition-smoke

ROLE_PROPERTY_PARITY_RESULT_DIR=./.local/p077-results/role-property-parity \
  make sprint12-role-property-environment-parity-smoke

DYNAMIC_METADATA_PARITY_RESULT_DIR=./.local/p077-results/dynamic-metadata-parity \
  make sprint12-dynamic-metadata-environment-parity-smoke
```

The dynamic parity harness derives one Git-less source authority from the exact
staged index. Native and container binaries are built independently from
separate copies. The container receives authenticated source and fixtures
read-only plus one empty writable result root. It never receives the live
repository or completed native result plane.

## Final closeout-candidate aggregate

```bash
make sprint12-p077-acceptance-smoke
```

Expected final banner:

```text
sprint12-p077-acceptance-smoke: ok sprint=12 status=closeout-candidate textrel=private rpath=private runpath=private public-fields-added=0 next-sprint=13
```

This banner authorized the Patch 077 closeout candidate for independent
acceptance. It did not by itself activate Sprint 13 or authorize a release tag,
and later review required the Patch 078 correction.

## Failure interpretation

- Exit `5` remains malformed input with no partial stdout.
- Exit `6` remains unsupported/capacity failure with no partial stdout.
- Private records retained on those paths are deterministic parse-prefix facts,
  not complete negative mitigation conclusions.
- Docker socket or missing-tool failures are environment/toolchain failures.
- Native and Docker mismatches are product or build-origin evidence until
  reconciled; they must not be mixed into one stratum.

## Handoff

Patch 077 did not complete acceptance. Patch 078 corrected its remaining
blockers, but Patch 078 was superseded by the Patch 079 corrective and private
task-value candidate, which was superseded by Patch 080; Patch 080's review
required Patch 081. Patches 081 through 086 did not complete acceptance; Patch 087 is
the current exact-source
implementation candidate. See the
[Patch 087 validation record](sprint-13-patch-087-validation.md); complete
acceptance remains pending against that exact candidate.
