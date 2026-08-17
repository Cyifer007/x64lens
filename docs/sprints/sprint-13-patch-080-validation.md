# Sprint 13 Patch 080 Validation

## Status

Historical implementation candidate. Patch 080 did not complete acceptance; its
review required Patch 081. Current requirements are recorded in the
[Patch 089 validation record](sprint-13-patch-089-validation.md).

## Purpose

Patch 080 corrects the Patch 079 transaction, Git-less source, immutable-image,
parity-build, task-oracle, and loose-delivery findings. It then materializes the
three qualified register-role facets in a private additive side-car without
changing public semantics, scores, or schema `0.2.0`.

## Exact implementation boundary

Patch 080 adds:

- descriptor-bound exact recovery for partial patch effects;
- complete Git-less manifest and caller-visible root reauthentication;
- rollback when final Git metadata reauthentication fails;
- immutable Docker image authority for all downstream consumers;
- executable isolated container build storage for parity binaries;
- a corrected 60-query task-value authority with disjoint development and confirmation tuples;
- a complete System V and Linux syscall ABI oracle;
- a 9-cell LC-08B private/public/score policy authority; and
- an 8-byte candidate-indexed private role record.

Patch 080 does not add a public field, semantic class, score, schema revision,
decoder, worker, or target-derived file open.

## Focused validation

```bash
python3 -m py_compile \
  tools/docker-image-authority.py \
  tools/git-patch-transaction.py \
  tools/normalize-tracked-permissions.py \
  tools/patch079-corrective-regression-smoke.py \
  tools/sprint13-register-role-decision-smoke.py \
  tools/sprint13-register-role-task-value-smoke.py \
  tools/sprint13-role-policy-smoke.py

make patch079-corrective-regression-smoke
make sprint13-register-role-decision-smoke
make sprint13-register-role-task-value-smoke
make sprint13-role-policy-smoke
make sprint13-role-facet-smoke
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
make schema-compat-smoke
```

Expected task and policy banners include:

```text
sprint13-register-role-task-value-smoke: ok version=2 strata=5 tasks=60 unique_queries=60 qualified=3 deferred=2 ... public_fields_added=0 score_changes=0 schema_changed=0
sprint13-role-policy-smoke: ok cells=9 private_runtime_accept=3 public_defer=3 score_null=3 role_record_bytes=8 role_arena_bytes=32768 analysis_arena_bytes=884736 ...
sprint13-role-facet-smoke: ok roles=16 generic_control=15 sysv_args=6 syscall_args=6 rcx_sysv_arg4=1 r10_syscall_arg4=1 ...
```

## Complete native validation

```bash
make fix-perms
make clean
make
make samples
make test
make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

The fresh NASM build is required because Patch 080 adds
`src/candidate_role.asm`, changes the command arena, and adds materializer calls
in `gadgets` and `analyze`.

## Docker and parity validation

```bash
make docker-build
make docker-image-authority-smoke
make docker-source-custody-smoke
make docker-test
make docker-validation-smoke
make sprint12-external-natural-acquisition-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
```

Every downstream Docker target consumes the immutable image ID recorded by
`tools/docker-image-authority.py`. Re-resolving the mutable tag after build is
not an accepted validation path.

## Capacity and malformed-input expectations

- Candidate 4,096 can still produce one complete report.
- Candidate 4,097 returns exit code 6 before text or JSON stdout.
- Malformed parser inputs retain their documented nonzero class and emit no partial stdout.
- The private role slice is allocated within the fixed command arena and does
  not change candidate capacity.

## Acceptance aggregate

```bash
make sprint13-p080-acceptance-smoke
```

Expected banner:

```text
sprint13-p080-acceptance-smoke: ok patch=80 sprint12=closed sprint13=active private-role-facets=3 public-fields-added=0 semantic-changes=0 score-changes=0 schema=0.2.0
```

The banner is valid only after all prerequisites complete against the exact
candidate source. It does not independently prove acceptance.

## Failure interpretation

- A partial patch effect that leaves the index or worktree dirty is a transaction failure.
- An incomplete Git-less manifest or caller-visible root replacement is a source-custody failure.
- A downstream Docker command that resolves a mutable tag instead of the
  recorded immutable image ID is an identity failure.
- A container parity build on a non-executable mount is a harness failure.
- Any development/confirmation query overlap, ABI reassignment, public
  projection, or score change is an oracle failure.
- Any output difference caused solely by the private role side-car is a product regression.

## Next step

Patch 081 records a test-only ordered two-pop manifest whose declared outcomes
produce zero incremental gains and therefore defer a redundant runtime tuple.
That authority is a policy input, not confirmatory measured task-value evidence.
Public role projection and score changes remain separate decisions.
