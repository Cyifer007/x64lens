# Sprint 11 Patch 058 Validation

## Status

Implementation candidate; empirical acceptance is pending.

## Purpose

The Patch 058 implementation candidate supplies the task-normalized ROPgadget,
Ropper, and ropr adapter foundation while addressing Patch 057 runner, corpus,
oracle, and evidence-integrity findings.

No analyzer assembly, CLI, JSON schema, semantic class, score, candidate
capacity, command-arena size, decoder policy, or worker policy changes.

## Changed public implementation surface

```text
benchmarks/scripts/diagnostic-runner.py
benchmarks/scripts/build-provisional-corpus.py
benchmarks/scripts/baseline-output-adapter.py
benchmarks/specs/sprint11-reference-diagnostic.json
benchmarks/task-definitions/sprint11-diagnostic-tasks.json
tools/diagnostic-runner-smoke.py
tools/provisional-corpus-smoke.py
tools/diagnostic-task-definitions-smoke.py
tools/baseline-output-adapter-smoke.py
tests/fixtures/baseline-adapters/*.txt
Makefile
```

## Focused adapter validation

```bash
make diagnostic-task-definitions-smoke
make baseline-output-adapter-smoke
```

Expected results:

```text
diagnostic-task-definitions-smoke: ok tasks=3 implemented=2 unavailable=1 baselines=3 baseline_adapters=3 relation_authorities=4 implemented_relations=3 unavailable_relations=1 frozen=false
baseline-output-adapter-smoke: ok tools=3 controlled_records=15 exact_relation_precision=1.000 exact_relation_recall=1.000 adversarial_cases=20 generic_counts=0
```

The adapter smoke must exercise:

- exact supplied-command reconciliation for each baseline;
- executable, target, retained version-output file and declared version text,
  native-output, and adapter authentication, including deterministic late-mutation
  rejection;
- bounded stdout and stderr rejection plus line, record-count, instruction-count, and 64-bit address limits;
- deterministic normalized output;
- native duplicate preservation and separate unique counts;
- exact `pop rdi; ret` normalization for represented ROPgadget, Ropper, and
  ropr syntax;
- rejection of invalid UTF-8, uncategorized lines, non-return records, stale
  identity, unsafe links, and pre-existing output paths;
- absence of an unlabeled `gadget_count` field; and
- explicit rejection of decoder-backed native records as a substitute for raw executable-byte evidence.

The smoke uses controlled native-output fixtures. It does not pin and execute a
supported real version of every baseline, and the standalone adapter does not
consume a runner row, campaign manifest, child outcome, or capture record. Those
limits keep parser validation separate from end-to-end campaign provenance.

## Focused runner validation

```bash
make diagnostic-tools-check
make diagnostic-runner-smoke
make sprint11-diagnostic-reference-smoke
```

The runner smoke retains the Patch 055 and Patch 057 success, failure, timeout,
process cleanup, target-nonexecution, source-mutation, and transactional
publication probes. Patch 058 additionally requires:

- parent-side bounded stdout/stderr capture;
- a durable `output_limit` failure row with the exact configured prefix;
- future capture-path symbolic links to remain untouched;
- cleanup of an owned staging object renamed away from its original pathname;
- preservation of an unrelated replacement at the original stage pathname; and
- correct committed-state detection when interruption follows no-replace
  publication.

## Focused corpus validation

```bash
make corpus-tools-check
make provisional-corpus-smoke
```

The 24-target, two-build reproducibility matrix remains mandatory. Patch 058
adds proof that:

- later verification enforces retained target-output and compiler-log limits;
- early interruption before ordinary compiler activity leaves no staging tree;
- stage substitution cleans the owned tree and preserves the replacement;
- post-publication interruption reports a committed result; and
- every negative probe checks its own requested corpus identifier.

## Full native acceptance

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make diagnostic-task-definitions-smoke
make baseline-output-adapter-smoke
make diagnostic-runner-smoke
make provisional-corpus-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

The complete native gate must preserve:

```text
candidate capacity: 4096
candidate 4097: exit 6 before stdout
malformed parse failure: no partial stdout
schema: 0.2.0
command arena: 819200 bytes
```

## Container and parity acceptance

```bash
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

The baseline adapter fixture gate and corpus smoke must pass under the configured
non-root container user. Optional baseline executables may remain absent during
normal validation; a diagnostic campaign condition is admitted only when its
tool executable and declared version text are present with retained version
output and the campaign binds them to the corresponding runner row.

## Artifact acceptance

The final-file public overlay must pass:

```bash
BUNDLE=/path/to/public-overlay.zip make patch-bundle-hygiene
PUBLIC_BUNDLE=/path/to/public-overlay.zip make public-bundle-content-check
PUBLIC_BUNDLE=/path/to/public-overlay.zip \
PUBLIC_BUNDLE_SHA256=<sha256> \
  make public-overlay-verify
```

Evidence archives must preserve executable and read-only modes. Extracted
archive modes are compared with the source evidence tree before the archive is
accepted.

## Expected next step

After Patch 058 is accepted, Patch 059 may correct campaign binding and establish
the stage-zero measurement plane while preserving normalized and native baseline
discrepancies. Planned Patch 060 runs the provisional corpus diagnostic campaign,
generates task-scoped development summaries, and builds the engineering gap
register that directs Sprints 12 through 14. Planned Patch 061 closes Sprint 11.
