# ADR 0065: Patch 078 Correction and Register-Role Task Value

## Status

Proposed by Patch 079; acceptance requires `make sprint13-p079-acceptance-smoke` and the independent non-documentation review lane.

## Context

Patch 078 froze an additive private role lattice for all sixteen exact single-pop register patterns. Review preserved that role model but identified acceptance defects in the surrounding source, Docker, parity, recovery, permission, patch-transaction, and delivery authorities. The same review also confirmed that a role label is not enough to justify runtime semantic promotion or a score change. The project therefore needs one corrective patch and one preregistered task-value decision before any role reaches the classifier or public report.

The implementation must preserve these boundaries:

- file-backed `PT_LOAD + PF_X` ranges remain executable authority;
- exact suffix evidence remains distinct from decoded sequence validity;
- existing raw, exact, semantic-exact, unknown, scored, and future decoder-backed facts keep their current meanings;
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

Each stratum uses eight development tasks and four untouched confirmation tasks. Current public semantic facts and the additive private role facets are presented through a deterministic A/B label permutation. The project makes no human double-blind claim.

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

The syscall-number and stack-pivot strata retain their existing semantic treatment because they do not demonstrate the required incremental confirmation gain. Passing task strata remain private, additive, and unscored. A later LC-08B policy decision owns runtime semantic projection, public output, and score/null treatment.

## Consequences

- Patch 079 adds no CLI command or flag.
- Tool version remains `0.1.0-dev`.
- Schema remains `0.2.0`.
- Public report fields and report bytes remain unchanged.
- Existing scores remain unchanged.
- `rcx` remains System V call argument 4; `r10` remains Linux syscall argument 4 in the private role authority.
- A qualified private facet is evidence for a later policy decision, not a runtime class, decoded-validity fact, exploitability statement, or release claim.
- Any later classifier or task-definition change starts a distinct diagnostic campaign identity.

## Validation

Focused validation:

```bash
make patch078-corrective-regression-smoke
make sprint13-register-role-decision-smoke
make sprint13-register-role-task-value-smoke
```

Complete local acceptance:

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
