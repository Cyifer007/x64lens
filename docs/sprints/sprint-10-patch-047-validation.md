# Sprint 10 Patch 047 Validation

## Status

Rejected as delivered. Patch 048 is the current corrective implementation
candidate.

## Scope

Patch 047 combines the Patch 046 validation correction with the next bounded
Sprint 10 family:

- enforce per-candidate single-pop pattern/order/control consistency in common
  JSON validation;
- add regression coverage for all 16 single-pop patterns and mixed legacy/REX
  two-pop order;
- add exact register-direct `mov r64,r64; ret` recognition;
- expose source, destination, destination clobber, stack delta, and
  `register_write` side-effect facts;
- preserve the 112-byte candidate record, 655,360-byte arena, 4,096-candidate
  capacity, tool version `0.1.0-dev`, and schema version `0.2.0`;
- reconcile public documentation with the Patch 046 effect and validation
  contracts.

Related documentation: [ADR 0033](../adr/0033-exact-register-transfer-effects.md),
the [Primitive Effect Model](../design/primitive-effect-model.md), the
[Semantic Taxonomy](../semantic-taxonomy.md), the
[Architecture](../architecture.md), the [JSON Schema Contract](../json-schema.md),
the [Sprint 10 Plan](sprint-10-plan.md), and the
[canonical roadmap](../roadmap-18-sprints.md).

## Controlled register-transfer fixture

`tests/toy-src/gadgets_sprint10_transfer.S` contains ten return-terminated
sequences:

- four supported register-direct 64-bit transfers;
- one self move;
- two `rsp`-participating forms;
- one memory write;
- one 32-bit register move;
- one memory read.

Expected report facts:

```text
raw candidates:        10
exact patterns:        10
semantic candidates:   10
unknown candidates:     0
scored candidates:      6
register transfers:     4
ret fallbacks:           6
```

Each transfer must report:

```text
semantic_class: reg_transfer
controls: []
register_transfer: {source, destination}
clobbers: [destination]
side_effects: [register_write]
stack_delta: 8
stack_delta_known: true
score: null
full_sequence_valid: null
```

The six excluded forms remain exact `ret` alignment fallbacks under the current
strongest-suffix policy.

## Required native validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make clean
make
make samples
make test
make sprint10-primitive-smoke
make sprint10-register-transfer-smoke
make json-effect-consistency-smoke
make schema-compat-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

Expected focused banners:

```text
sprint10-register-transfer-smoke: ok candidates=10 transfers=4 fallback=6 scored=6
json-effect-consistency-smoke: ok single_pop=16 single_pop_rejections=16 mixed_multi_pop=4 mixed_rejections=4
```

## Direct report validation

```bash
./build/x64lens gadgets --format json --max-depth 4 \
  ./tests/bin/gadgets_sprint10_transfer > /tmp/x64lens-p047-gadgets.json

./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/gadgets_sprint10_transfer > /tmp/x64lens-p047-analyze.json

python3 tools/validate-json-report.py \
  --mode sprint10-transfer-fixture \
  --require-schema 0.2.0 \
  --expected-command gadgets \
  --require-provenance \
  --require-sprint10-effects \
  --require-sprint10-transfer \
  /tmp/x64lens-p047-gadgets.json

python3 tools/validate-report-parity.py \
  /tmp/x64lens-p047-gadgets.json \
  /tmp/x64lens-p047-analyze.json
```

## Capacity and failure invariants

Patch 047 must not change the established boundary:

- 4,096 candidates produce a complete report;
- the 4,097th candidate returns exit code `6`;
- stdout remains empty on overflow;
- stderr remains `error: unsupported binary feature\n`;
- malformed input emits no partial report.

## Docker validation

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

A Docker-client metadata write failure is classified separately from product
behavior only after the complete matrix passes in a valid writable Docker
configuration.

## Acceptance criteria

- The common validator rejects inconsistent single-pop controls.
- All 16 single-pop positive relations and four mixed two-pop positive relations
  validate, and their contradictory mutations fail.
- The transfer fixture produces exactly four transfer candidates and six
  conservative fallbacks.
- Source/destination roles match exact bytes for both opcode directions and REX
  extensions.
- No transfer involving `rsp`, memory, a self move, or a 32-bit operand is
  promoted.
- `gadgets` and `analyze` differ only by command identity.
- Candidate records, arena size, capacity, CLI, versions, and runtime dependency
  surface remain unchanged.
- Native, strict ShellCheck, and qualified Docker aggregates pass.
