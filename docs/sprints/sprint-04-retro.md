# Sprint 04 Retrospective

## Status

Complete.

## Dates

Start: 2026-06-10
End: 2026-06-10

## Sprint goal

Turn Sprint 3 raw candidates and exact suffix patterns into semantic exploit primitive facts without broadening scanner scope or making unsupported exploitability claims.

## Summary

Sprint 4 successfully added the first semantic classifier layer to `x64lens`. The tool now consumes exact pattern IDs produced by `patterns.asm` and populates semantic fields in internal gadget records before text reporting. This preserves the key architecture boundary:

```text
scanner -> exact pattern matcher -> semantic classifier -> future scoring -> reporters
```

Patch 015 moved the project from raw byte-window reporting into first-pass primitive coverage while staying conservative about what exact suffix matching can prove.

## Completed deliverables

- [x] Implemented `x64lens_classifier_apply_exact` in `src/classifier.asm`.
- [x] Called the classifier from `src/gadgets.asm` after exact pattern matching and before reporting.
- [x] Mapped supported exact pattern IDs into semantic classes.
- [x] Populated controlled-register bitmaps for supported register-control patterns.
- [x] Populated stack deltas for `ret`, `ret imm16`, and pop-ret patterns.
- [x] Added minimal side-effect flags for stack reads, stack pivots, syscall trigger, and `ret imm16`.
- [x] Extended `gadget_summary` with semantic primitive count, unknown count, per-class counts, and register coverage.
- [x] Added text output for semantic class, controlled registers, and stack delta.
- [x] Updated fixture validation and `make semantic-smoke`.
- [x] Updated scanner smoke benchmark columns for semantic primitive and unknown counts.
- [x] Updated semantic taxonomy, scoring-model notes, validation plan, and roadmap/context files.

## Implemented classifier mapping

| Exact pattern | Semantic class | Controlled registers | Stack delta |
|---|---|---:|---:|
| `ret` | `alignment` | none | 8 |
| `ret imm16` | `alignment` | none | `8 + imm16` |
| `pop rdi; ret` | `arg_control` | `rdi` | 16 |
| `pop rsi; ret` | `arg_control` | `rsi` | 16 |
| `pop rdx; ret` | `arg_control` | `rdx` | 16 |
| `pop rcx; ret` | `arg_control` | `rcx` | 16 |
| `pop r8; ret` | `arg_control` | `r8` | 16 |
| `pop r9; ret` | `arg_control` | `r9` | 16 |
| `pop rax; ret` | `syscall_num_control` | `rax` | 16 |
| `syscall; ret` | `syscall_trigger` | none | 8 |
| `leave; ret` | `stack_pivot` | `rsp` | unknown sentinel `0` |
| `pop rsp; ret` | `stack_pivot` | `rsp` | unknown sentinel `0` |
| unsupported exact pattern | `unknown_candidate` | none | unknown sentinel `0` |

## Validation evidence

User-provided terminal output confirmed:

```text
make script-perms-check -> script-perms-check: ok
make scaffold-check -> scaffold-check: ok
make diagrams-check -> diagrams-check: ok
make test -> tests: ok
make docker-test -> tests: ok
make validate-gadget-fixture -> validate-gadget-fixture: ok
make semantic-smoke -> validate-gadget-fixture: ok
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke -> scanner-smoke benchmark complete
```

Controlled fixture output confirmed:

```text
Candidate count: 0x0000000000000007
Exact pattern count: 0x0000000000000007
Semantic primitive count: 0x0000000000000007
unknown_candidate count: 0x0000000000000000
arg_control count: 0x0000000000000003
syscall_num_control count: 0x0000000000000001
syscall_trigger count: 0x0000000000000001
stack_pivot count: 0x0000000000000001
alignment count: 0x0000000000000001
Register coverage: rax|rdx|rsi|rdi|rsp
```

Real-binary `/bin/ls` smoke output confirmed that semantic summaries run on a non-fixture binary and that stack-pivot candidates contribute `rsp` register coverage:

```text
Candidate count: 0x00000000000002c7
Semantic primitive count: 0x000000000000026a
unknown_candidate count: 0x000000000000005d
stack_pivot count: 0x0000000000000006
Register coverage: rsp
```

## Bugs or issues found

No Sprint 4 blocking implementation bugs were identified from the supplied validation output.

Two non-blocking issues should be tracked:

1. **Packaging hygiene:** user-created whole-repository zip snapshots can include `.git/`, `build/`, `tests/bin/`, and generated benchmark results. These are ignored by Git and should not be included in clean patch or release bundles.
2. **Unknown stack delta rendering:** `STACK_DELTA_UNKNOWN` is encoded as `0`, so text output currently prints `stack delta: 0x0000000000000000` for pivots. This is test-expected for Patch 015, but Sprint 5 JSON should add an explicit `stack_delta_known` or `stack_delta_kind` field, and text output can later render `unknown` for pivots.

## Contract review

- **Development contract:** followed. Scanner, pattern matcher, semantic classifier, scoring, and reporting remain separate. Scoring and JSON were not forced into Sprint 4.
- **Parser safety contract:** followed. The classifier consumes previously validated records; the only direct mapped-file read is the `ret imm16` immediate after scanner bounds validation.
- **Internal-facts-before-output rule:** followed. Semantic facts are stored in `gadget_record` and `gadget_summary` before text rendering.
- **Metric-boundary contract:** followed. Raw candidate counts, exact pattern counts, semantic primitive counts, unknown counts, and future scored counts remain separate.
- **Output contract:** followed for text output. The tool reports primitive availability and does not claim exploitability.
- **Research contract:** followed. Smoke benchmark evidence is preserved as development evidence, not publication-grade performance proof.
- **Context persistence contract:** followed. Sprint state, backlog, validation notes, roadmap, and local context were updated.

## Known limitations after Sprint 4

- The classifier is exact-suffix based and not a full x86_64 decoder.
- Pattern labels describe recognized suffixes, not necessarily full decoded instruction windows.
- `alignment` counts on real binaries may include unaligned byte-pattern candidates.
- Scoring is not implemented.
- JSON output is not implemented.
- `analyze <file>` orchestration is not implemented.
- Candidate storage remains bounded.
- The controlled fixture does not yet exercise every implemented mapping, such as `pop rcx; ret`, `pop r8; ret`, `pop r9; ret`, and `pop rsp; ret`.

## Next sprint recommendation

Begin Sprint 5 with scoring and JSON, but first add a small semantic fixture expansion or validation task so all currently implemented semantic mappings are exercised before score values become visible. Then implement score fields and JSON from internal records only.
