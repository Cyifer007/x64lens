# Sprint 13 Patch 079 Validation

## Status

Patch 078's review required a smallest corrective patch. Patch 079 is the
resulting corrective and private task-value candidate, pending the complete
documented Patch 079 acceptance gate against the exact committed source.

## Scope

Patch 079 is the smallest cohesive correction for the Patch 078 acceptance
findings and the first Sprint 13 task-value gate. It changes development,
validation, Docker, recovery, custody, permission, transaction,
benchmark-authority, and documentation files. It changes no tracked path under
`src/`, `include/`, or `schemas/`.

The patch:

- makes exact Git-less Docker source and transport construction single-snapshot and descriptor-bound;
- makes Docker build failure transparent and prevents stale-image continuation;
- supports tracked-only permission normalization in an authenticated Git-less validation copy;
- rebuilds native and container parity binaries independently;
- binds container parity to an immutable image identity and exact candidate tree;
- preserves foreign recovery descendants during failed cleanup;
- recovers exact Git state when patch apply or rollback performs its effect and then raises;
- executes five independent preregistered register-role task-value strata; and
- retains all role-task decisions as private, additive, unscored policy input.

## Preserved contracts

```text
program-header executable authority: file-backed PT_LOAD + PF_X
candidate capacity:                  4096
candidate 4097:                      exit 6 before stdout
malformed parser failure:            no partial stdout
report schema:                       0.2.0
reference profile:                   dependency-free, decoder-free, one worker
public fields added:                 0
score changes:                       0
target execution:                    never
```

## Focused gates

```bash
python3 -m py_compile \
  tools/gitless-source-manifest.py \
  tools/git-patch-transaction.py \
  tools/normalize-tracked-permissions.py \
  tools/recover-candidate-source.py \
  tools/sprint12-role-property-environment-parity-smoke.py \
  tools/patch078-corrective-regression-smoke.py \
  tools/sprint13-register-role-task-value-smoke.py

make patch078-corrective-regression-smoke
make sprint13-register-role-decision-smoke
make sprint13-register-role-task-value-smoke
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
make schema-compat-smoke
```

Expected task-value result:

```text
strata:                     5
tasks:                     60
development tasks:         40
confirmation tasks:        20
qualified strata:           3
deferred strata:            2
regressions:                 0
incorrect promotions:       0
public fields added:         0
score changes:               0
schema changed:              0
```

Qualified private facets:

```text
generic_control
sysv_call_arguments
linux_syscall_arguments
```

Deferred task-value strata:

```text
syscall_number
stack_pivot
```

The five strata are independent and cannot be pooled. The `confirmation tasks`
label names the untouched partition in this private gate; the resulting evidence
remains diagnostic, unfrozen, non-confirmatory, and publication-ineligible.
Within the private role evidence, `rcx` is System V call argument 4 and `r10` is
Linux syscall argument 4.

## Complete acceptance gates

```bash
make fix-perms
make clean
make
make samples
make test
make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make docker-build
make docker-source-custody-smoke
make docker-test
make docker-validation-smoke
make sprint12-external-natural-acquisition-smoke
make sprint12-role-property-environment-parity-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
make sprint13-p079-acceptance-smoke
```

The Docker build must use a fresh tag and must report an immutable image ID and candidate-tree label. The role/property parity plane must contain independently built native and container analyzer/probe identities. A same-host logic replay or a container execution of host-built bytes does not satisfy this gate.

## Failure interpretation

- A Docker context/build failure followed by inspection or execution of an existing tag is a product failure.
- Extra generated files in a writable validation copy do not become source authority and must remain outside tracked-only normalization.
- A source root, directory, file, hardlink, mode, byte, Git object, or membership mismatch is a custody failure.
- A patch-transaction failure is acceptable only when the exact prior Git tree is restored.
- A foreign recovery descendant must be preserved as fail-closed residue.
- Task-value strata are evaluated separately. No aggregate total can rescue a failed stratum.
- A qualified task-value stratum does not authorize runtime projection, public output, or scoring.

Raw candidate facts, exact-suffix facts, semantic-exact facts, unknown facts,
future decoder-backed facts, and scored facts remain distinct. A qualified
private facet does not authorize promotion between them. Patch 079 supports no
performance, peak-RSS, coverage-superiority, enforcement, exploitability,
stealth, or universal-deployment claim.

## Expected candidate-aggregate banner

```text
sprint13-p079-acceptance-smoke: ok patch=79 sprint12=closed sprint13=active qualified-private-facets=3 deferred-facets=2 public-fields-added=0 score-changes=0
```

This banner is an aggregate result, not independent acceptance or chronology
authority. Sprint 12 closes and Sprint 13 becomes active only after the complete
Patch 079 acceptance boundary passes against the exact committed candidate.
