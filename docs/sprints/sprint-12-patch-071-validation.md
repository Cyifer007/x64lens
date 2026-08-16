# Sprint 12 Patch 071 Validation

## Status

Historical first corrective implementation candidate after Patch 070 review.
Patch 071 is limited to nested cleanup identity, exact batch-oracle semantics,
streaming output limits, and recursive source/evidence delivery custody. It
performs no external-natural acquisition and changes no runtime analyzer or
public schema behavior. Follow-up validation required the remaining Patch 072
correction, so Patch 071 was not accepted at its first returned review boundary.
Patches 070, 072, and 073 likewise were not accepted at their first returned
review boundaries. Patch 073 delivered the first custody/isolation correction
and policy deferral. Patch 074 was a superseded Sprint 12 closeout candidate.
Patch 075 introduced bounded private static text-relocation evidence, and Patch
076 implemented distinct private `DT_RPATH` and `DT_RUNPATH` carrier/value
evidence. Patch 076 was superseded by Patch 077. Patch 077's review required
Patch 078, whose review required the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080.
Current validation expectations are in the
[Patch 087 validation record](sprint-13-patch-087-validation.md).

## Source precondition

Patch 071 applies to the exact committed Patch 070 source:

```text
HEAD:   ac26a3c39923f05cbfc14bcb332ad5952174fbaa
parent: 3bd8a8cea0529b72d19dd3c79b48c16f7943fed7
base tree: d4db4b3e0879d9d7591d324ec7f39ab980834268
```

The worktree and index must be clean before application.

## Corrected behavior

- Every nested cleanup member receives an identity-bound two-stage quarantine.
- Late regular-file and directory replacements survive and force cleanup
  failure.
- Cleanup is destructive rather than transactional rollback; later failure can
  leave authenticated members removed or directory modes changed under
  quarantine.
- The batch authority is version 2 and includes one complete expected record for
  each of 27 cases.
- Each child stream is capped while being read; the runner retains no more than
  4,097 bytes for a 4,096-byte limit.
- The batch summary is derived from verified records rather than fixed prose.
- Recursive delivery manifests authenticate regular files by canonical relative
  path, SHA-256, byte size, and mode plus exact implied-directory membership.
  They reject missing, extra, symbolic-link, special, unsafe, undeclared empty-
  directory, mode-changed, size-changed, or hash-changed members.
- Source delivery must be generated from the exact Git candidate tree, exclude
  ignored private/generated state, and then pass manifest verification.

## Focused validation

```bash
make script-perms-check
make scaffold-check
make patch070-corrective-regression-smoke
make sprint12-batch-transaction-smoke
git diff --check
```

Expected focused banners:

```text
sprint12-batch-transaction-smoke: ok cases=27 executions=81 stable_hashes=81 successful_batches=3 failed_batches=16 failure_index_0=8 failure_index_1=4 failure_index_2=4 signals=8 stage_residue=0 survivors=0 fd_growth=0 timing_claims=0

patch070-corrective-regression-smoke: ok cleanup_success=1 file_replacement=1 directory_replacement=1 authority_mutations=4 case_mismatch=1 streaming_cap=1 delivery_extra=1 delivery_missing=1 delivery_empty_directory=1 delivery_symlink=1 source_custody=1
```

The `survivors=0` field covers tracked signal-case child survival. It does not
claim that every possible descendant in a process group was reaped.

A delivery tree is authenticated with:

```bash
python3 tools/verify-delivery-custody.py \
  --verify \
  --root /path/to/extracted-delivery \
  --manifest /path/to/extracted-delivery/DELIVERY_CUSTODY_MANIFEST.json
```

## Complete native validation

```bash
make clean
make
make samples
make test
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make section-label-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
make system-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make sprint-closeout-smoke
```

## Docker validation

```bash
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

Docker evidence must name the exact daemon and context. Docker Desktop and a
native Ubuntu daemon are separate environment strata.

## Unchanged product contracts

- tool version `0.1.0-dev`;
- JSON schema `0.2.0`;
- program-header executable authority;
- candidate capacity 4,096 and candidate-4,097 exit 6 before stdout;
- malformed-input no-partial-output behavior;
- raw, exact-suffix, semantic-exact, unknown, future decoder-backed, and scored
  distinctions;
- read-only targets and no target execution;
- dependency-free, decoder-free, one-worker reference runtime;
- no new role-derived PIE/DSO field or IBT/SHSTK field; the existing coarse
  `mitigations.pie` field remains unchanged.

## Interpretation

At this historical boundary, passing the listed gates would have established
the first corrected development and delivery transaction boundary. Follow-up
validation identified narrower prerequisites addressed by Patch 072. Patch
072's returned review rejected acceptance; the
[Patch 073 validation record](sprint-12-patch-073-validation.md) preserves the
first custody/isolation correction and policy-deferral boundary, while the
[Patch 074 validation record](sprint-12-patch-074-validation.md) preserves the
superseded closeout-candidate boundary. Current validation expectations are in
the [Patch 087 validation record](sprint-13-patch-087-validation.md). None of
these historical boundaries validates arbitrary external-
natural objects,
proves runtime CET enforcement, authorizes public mitigation fields, establishes
single-run latency, or produces publication evidence by itself.
