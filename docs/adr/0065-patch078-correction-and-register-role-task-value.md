# ADR 0065: Patch 079 Correction of Patch 078 and Register-Role Task Value

## Status

Historical Patch 079 implementation decision. Patch 079 did not complete
acceptance; it was superseded by Patch 080, and Patch 080 by Patch 081. Patch 081
was not accepted; Patch 082 is the current artifact-backed implementation
candidate, pending independent exact-source acceptance.

## Context

Patch 078 froze an additive private role lattice for all sixteen exact single-pop
register patterns. Acceptance validation preserved that role model but required
a corrective patch for defects in the surrounding source, Docker,
parity, recovery, permission, patch-transaction, and delivery authorities. Patch
079 was that corrective and private task-value candidate and was superseded by
Patch 080. The validation findings also confirmed that a role label is not enough to
justify runtime semantic promotion or a score change.

The implementation must preserve these boundaries:

- file-backed `PT_LOAD + PF_X` ranges remain executable authority;
- raw candidate, exact-suffix, semantic-exact, unknown, future decoder-backed,
  and scored facts remain distinct;
- candidate 4,097 returns exit code 6 before stdout;
- malformed input emits no partial report;
- the reference runtime remains dependency-free, decoder-free, deterministic, and one-worker;
- private role decisions do not imply public fields, score changes, or exploitability.

## Decision

### Correct the Patch 078 acceptance surface

Patch 079 makes the following development and delivery corrections without changing runtime analyzer modules, ABI includes, or schemas:

1. Docker source is generated from one frozen staged Git tree. The source tree, manifest, and transport Dockerfile are derived from that same snapshot.
2. Root, directory, file, mode, byte, Git-object, topology, and exact-membership custody are verified through retained descriptors.
3. Docker build recipes are fail-fast and cannot continue to a stale tag after context or image reconstruction fails.
4. Git-less validation may normalize only manifest-declared tracked modes; generated validation outputs remain outside that transaction.
5. Native/container role-property parity uses separately built binaries, an immutable image identity, an authenticated candidate-tree label, read-only held-out inputs, and one dedicated container result root. The completed native plane and live repository are not mounted into the container.
6. Patch apply and rollback recover when the mutating operation completes its Git effect and then raises.
7. Candidate-source recovery preserves a foreign descendant replacement rather than deleting it during failure cleanup.
8. The loose delivery and preferred package carry byte-identical canonical helpers and complete checksum/custody records.

### Execute five independent task-value strata

Patch 079 evaluates these strata independently:

1. generic single-register control;
2. System V call-argument roles;
3. Linux syscall-argument roles;
4. Linux syscall-number control;
5. stack-pivot roles.

Each stratum used eight development tasks and four confirmation-labeled tasks.
Patch 080 later found query reuse across those partitions and replaced the task
authority. Current public semantic facts and the additive private role facets
were presented in deterministic order as non-causal display metadata, not as a
human-blinding method.

A stratum qualifies only when it has:

- at least two incremental gains among eight development tasks;
- zero regressions;
- zero incorrect promotions;
- four of four correct confirmation tasks; and
- at least one incremental gain among the four confirmation tasks.

Results are never pooled across strata.

### Retain the result as private policy input

The task-value result qualifies:

- generic register control;
- System V call-argument roles; and
- Linux syscall-argument roles.

The `syscall_number` and `stack_pivot` strata remain deferred by the Patch 079
task gate because they do not demonstrate the required incremental confirmation
gain. Passing task strata remain private, diagnostic, unfrozen, additive,
unscored, non-confirmatory, and publication-ineligible. Patch 080 subsequently
retained the three qualified facets privately while deferring public projection
and score/null changes.

## Consequences

- Patch 079 adds no CLI command or flag.
- Tool version remains `0.1.0-dev`.
- Schema remains `0.2.0`.
- Public report fields and report bytes remain unchanged.
- Existing scores remain unchanged.
- `rcx` remains System V call argument 4; `r10` remains Linux syscall argument 4
  in the private role evidence.
- A qualified private facet was evidence for the separate Patch 080 policy
  decision, not a runtime class, decoded-validity fact, exploitability statement,
  or release claim.
- Any later classifier or task-definition change starts a distinct diagnostic campaign identity.
- No performance, peak-RSS, coverage-superiority, enforcement, exploitability,
  stealth, or universal-deployment claim follows from Patch 079.

## Validation

Focused validation:

```bash
make patch078-corrective-regression-smoke
make sprint13-register-role-decision-smoke
make sprint13-register-role-task-value-smoke
```

Historical Patch 079 acceptance boundary:

```bash
make clean
make
make samples
make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make docker-build
make docker-test
make docker-validation-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
make sprint13-p079-acceptance-smoke
```

The expected focused task-value banner reports five strata, sixty tasks, three qualified strata, two deferred strata, zero regressions, zero incorrect promotions, zero public fields, zero score changes, and no schema change.
