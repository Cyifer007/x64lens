# Sprint 13 Patch 078 Validation

## Status

Historical candidate. Patch 078 was superseded by the Patch 079 corrective and
private task-value candidate; Patch 079's review required Patch 080, whose
review required Patch 081. Patch 081 remains pending complete acceptance.

## Purpose

Patch 078 corrects the acceptance blockers found in the Patch 077 source and
delivery while freezing the first Sprint 13 register-role decision. It changes
no analyzer runtime source, NASM include, public JSON schema, report field,
semantic class, or score.

## Exact behavior under test

### Corrective surface

- repository-root and Git-directory rebinding during patch application and
  rollback is rejected;
- permission normalization binds the repository before index inventory and
  rolls back through retained inodes;
- expected nonzero/empty gadget and analyze outcomes are not parsed as JSON;
- parity publication fails when the caller-visible parent is replaced;
- delivery and recovery cleanup preserve a final foreign replacement;
- a wrong patch digest reaches the digest authority and fails there;
- Patch 070 source custody works in an exact Git-less source tree;
- Docker context membership equals the authenticated staged Git tree;
- packaged and loose helper identities agree.

### Register-role authority

The authority must account for all 16 exact single-pop patterns and preserve
these additive facets:

```text
generic register control: 15
System V call arguments:    6
Linux syscall arguments:    6
Linux syscall arg4:       r10
System V call arg4:       rcx
syscall number:           rax
stack pivot:              rsp
```

No public field or score changes are allowed by Patch 078.

## Focused commands

```bash
python3 tools/patch077-corrective-regression-smoke.py
python3 tools/sprint13-register-role-decision-smoke.py \
  --authority benchmarks/task-definitions/sprint13-register-role-decision-v1.json
python3 tools/sprint12-closeout-smoke.py
python3 tools/sprint12-continuation-smoke.py
```

Expected banners:

```text
patch077-corrective-regression-smoke: ok ...
sprint13-register-role-decision-smoke: ok roles=16 ... r10_syscall_arg4=1 ...
sprint12-closeout-smoke: ok sprint=12 patches=17 ... next_patch=79
sprint12-continuation-smoke: ok ... patch=78 ... next_patch=79
```

## Complete local validation

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
make sprint13-p078-acceptance-smoke
```

The Docker build must be created from the exact Git-less staged-tree context.
The final image must contain no undeclared ignored, generated, local, or Git
metadata member.

## Preserved failure contracts

- candidate 4,097 returns exit code 6 before stdout;
- malformed input emits no partial stdout;
- target mappings remain read-only and target bytes are never executed;
- nonzero external comparator exits are ineligible even when output looks
  syntactically plausible;
- private textrel/RPATH/RUNPATH failure snapshots retain only deterministic
  parse-prefix facts;
- no task, timing, coverage, or publication claim follows from this patch.

## Acceptance

Patch 078 did not complete acceptance. Its review required Patch 079 to correct
the remaining Docker, Git-less
custody, independent-build parity, recovery, patch-transaction, and loose-
delivery findings. Patch 079 also ran the non-causal, deterministically
presentation-ordered register-role task-value
gate: `generic_control`, `sysv_call_arguments`, and
`linux_syscall_arguments` qualify only as private task-value evidence, while
`syscall_number` and `stack_pivot` remain deferred. Patch 080 subsequently
retained the three qualified facets privately and deferred public-field and score
projection. Any future behavior change restarts every affected diagnostic task
identity.
