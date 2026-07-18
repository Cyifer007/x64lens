# Sprint 10 Patch 050 Validation

## Purpose

Patch 050 completes current-family side-effect facts, corrects cross-family
fixture expectations, makes Sprint 10 fixture recipes fail fast, isolates the
stale-manifest regression, and adds a machine-readable family coverage table.
It adds no new primitive family, runtime dependency, or score.

## Source assumptions

Validation must establish the actual repository root, branch, HEAD, parent,
worktree, remote state, and checkpoint tag before interpreting results. The
expected Patch 049 base is recorded in the patch delivery metadata; a current
local observation supersedes a stale remote-tracking reference.

## Focused gates

```bash
make sprint10-family-coverage-smoke
make json-effect-consistency-smoke
make public-overlay-verification-smoke
make sprint10-primitive-smoke
make sprint10-register-transfer-smoke
make sprint10-stack-adjust-smoke
make sprint10-memory-smoke
make schema-compat-smoke
```

Expected focused banners:

```text
sprint10-family-coverage-smoke: ok families=11 fixtures=4 cross_family_promotions=2 fail_fast_recipes=7 scored_policy=explicit false_positive_notes=complete
json-effect-consistency-smoke: ok single_pop=16 single_pop_rejections=16 mixed_multi_pop=4 mixed_rejections=4 bare_ret_rejections=4 current_families=3 current_family_rejections=5 stack_adjust=2 stack_adjust_rejections=4 memory=2 memory_rejections=12
public-overlay-verification-smoke: ok cases=5 accepted=1 rejected=4
sprint10-register-transfer-smoke: ok candidates=10 transfers=4 memory_write=1 memory_read=1 fallback=4 scored=4
```

## Current-family effects

Validation must confirm:

- every supported semantic `ret`/`ret imm16` candidate includes `stack_read`;
- `ret imm16` also includes `ret_imm16` and `stack_adjust`;
- `syscall; ret` clobbers `rcx` and `r11` and includes `syscall` plus
  `register_write`;
- `leave; ret` controls `rsp`, clobbers `rbp`, remains stack-delta unknown, and
  includes `stack_pivot` plus `register_write`;
- transfer, stack-adjust, memory-read, and memory-write candidates include the
  completed return effect;
- current Sprint 10 families remain unscored.

## Cross-family transfer fixture

The transfer fixture contains:

```text
4 register transfers
1 memory write
1 memory read
4 bare-ret fallbacks
10 total candidates
4 scored candidates
```

The direct JSON validator must fail if the old six-fallback/six-scored contract
is restored. The Make recipe must stop immediately when any validator fails.

## Compatibility boundary

The formal schema remains `0.2.0`. Retained Patch 040 and Patch 046 reports
remain consumable. Patch 046 compatibility validation does not retroactively
require the stronger Patch 050 current-producer side-effect contract.

## Runtime regression gates

```bash
make clean
make
make samples
make test
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
```

Candidate 4097 must still return exit 6 with empty stdout and exact stable
stderr. Malformed input must remain signal-free, bounded, and no-partial-output.

## Docker gate

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

A Buildx metadata failure outside the repository is an environment condition
only after the same product path passes with an isolated writable Buildx
configuration.

## Acceptance

Patch 050 is acceptable when:

- focused family/effect, overlay, and schema gates pass;
- native and qualified Docker aggregates pass;
- runtime record sizes, 4,096-candidate capacity, and 720,896-byte arena remain
  unchanged;
- no mandatory decoder, thread runtime, helper process, interpreter, or shared
  library appears;
- public source and final distribution artifacts pass the release-boundary
  checks and external checksums.
