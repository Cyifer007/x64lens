# Sprint 10 Patch 046 Validation

## Status

Accepted Sprint 10 entry foundation. Patch 047 was rejected as delivered; Patch
048 is the current corrective implementation candidate.

## Purpose

Patch 046 begins Sprint 10 with one bounded primitive family and one explicit
record-model extension. It also reconciles public documentation with the
validated Sprint 9 closeout state.

Related documentation: the [Sprint 10 Plan](sprint-10-plan.md),
[ADR 0032](../adr/0032-ordered-multi-pop-foundation.md), the
[Primitive Effect Model](../design/primitive-effect-model.md), and the
[canonical roadmap](../roadmap-18-sprints.md).

The implementation adds ordered two-pop argument-control evidence, explicit
clobber and side-effect output fields, a separate controlled fixture, and
current-producer validation. It does not add a decoder, worker runtime, memory
primitive, register-transfer primitive, or score rule.

## Source boundary

Patch 046 starts from the accepted Patch 045 source state. Acceptance covers the
complete public tree and depends only on repository-visible source, fixtures,
and reproducible validation.

## Required invariants

- Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable
  authority.
- Scanner, matcher, classifier, evidence, scoring, and reporting modules remain
  separate.
- Exact suffix evidence remains distinct from full instruction-sequence
  validity.
- `GADGET_RECORD_SIZE` remains 112 bytes.
- `ANALYSIS_RECORD_ARENA_BYTES` remains 655,360 bytes.
- Candidate capacity remains 4,096 records.
- Multi-pop candidates are semantic but unscored.
- Capacity and malformed-input failures emit no partial stdout.
- Schema remains `0.2.0`; new effect fields are compatible additions.
- `gadgets` and `analyze` differ only by command identity for the same target and
  options.
- No mandatory runtime dependency or parallel default is introduced.

## Controlled fixture

`tests/toy-src/gadgets_sprint10.S` contains five return terminators:

| Sequence | Expected result |
|---|---|
| `pop rdi; pop rsi; ret` | ordered multi-pop `arg_control`, unscored |
| `pop r8; pop r9; ret` | ordered multi-pop `arg_control`, unscored |
| `pop rdx; pop rcx; ret` | ordered multi-pop `arg_control`, unscored |
| `pop rdi; pop rdi; ret` | conservative `pop rdi; ret` fallback |
| `pop rbx; pop rdi; ret` | conservative `pop rdi; ret` fallback |

Expected aggregate facts:

```text
raw candidates:       5
exact patterns:       5
semantic candidates:  5
unknown candidates:   0
scored candidates:    2
multi-pop candidates: 3
fallback candidates:  2
```

## Static and contract commands

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make schema-compat-smoke
git diff --check
```

Expected schema result:

```text
schema-compat-smoke: ok legacy=0.1.0 patch040=0.2.0 current=0.2.0 formal_rejections=13 semantic_rejections=12
```

## Native commands

```bash
make clean
make
make samples
make test
make validate-gadget-fixture
make sprint10-primitive-smoke
make json-smoke
make analyze-smoke
make system-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
make section-label-smoke
make benchmark-integrity-smoke
make patch-bundle-hygiene-smoke
make decoder-gap-hardening-smoke
make decoder-gap-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

Expected fixture and new-family results:

```text
validate-sprint10-disassembly: ok instructions=15
sprint10-primitive-smoke: ok candidates=5 multi_pop=3 fallback=2 scored=2
```

## Focused JSON checks

For every Patch 046 current-producer report:

- `stack_pop_order` is present;
- `clobbers` is present;
- `side_effects` is present;
- single-pop order agrees with the pattern and exact suffix bytes;
- multi-pop order agrees with the exact suffix bytes;
- multi-pop controls cover the same register set as the ordered pops;
- multi-pop stack delta is 24;
- multi-pop score is `null`;
- clobbers remain empty until a supported rule populates them;
- represented side effects match classifier facts exactly.

## Docker commands

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Docker acceptance requires the complete sequence in a qualified environment;
an environment-only failure does not establish Patch acceptance.

## Failure expectations

- An internal contradiction in ordered pattern metadata returns exit code `7`
  through the established cleanup path.
- The 4,097th raw candidate returns exit code `6`, emits zero stdout bytes, and
  prints the stable unsupported-feature diagnostic.
- Malformed ELF inputs retain their documented nonzero status and no-partial-
  output behavior.

## Acceptance record

Patch 046 was accepted as the Sprint 10 entry foundation under the native,
strict ShellCheck, focused Sprint 10, capacity, malformed-input, parity, and
qualified Docker gates recorded above. Later primitive families retain their
own acceptance gates.

## Follow-on validation

Patch 047 added common single-pop relation checks and a separate
register-transfer fixture but was rejected as delivered. Patch 048 carries that
family forward after correcting its reporter and validation defects. Patch 046
remains the historical ordered multi-pop foundation; current acceptance runs the
Patch 048 gates.
