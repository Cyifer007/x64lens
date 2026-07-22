# x64lens

**x64lens is an assembly-first ELF64 x86_64 binary analysis tool that maps executable regions, discovers return-oriented candidate windows, classifies supported semantic primitives, evaluates mitigation context, assigns bounded heuristic scores, and produces reproducible text and JSON reports for defensive triage and authorized security research.**

> Status: Sprints 1 through 10 are complete after Patch 054. Sprint 10 delivered ordered multi-pop, register-transfer, stack-adjust, bounded qword memory, coarse and architectural effects, selective scoring, fixture reconciliation, and the benchmark-informed twenty-two-sprint roadmap. Sprint 11 is active as the diagnostic benchmark foundation; the confirmatory corpus and method remain unfrozen until Sprint 15.
>
> Tool version: `0.1.0-dev`
>
> JSON schema version: `0.2.0`
>
> Canonical roadmap: [`docs/roadmap-22-sprints.md`](docs/roadmap-22-sprints.md). Sprint 15 freezes the campaign, Sprint 16 produces the preview candidate, Sprint 17 runs the publication campaign, and Sprint 22 is the first research-release gate.

## Why this project exists

Most gadget tools emphasize enumeration for exploit development. x64lens studies a different question: can a dependency-light, assembly-first engine turn deterministic ELF and code-reuse facts into a bounded, reproducible, mitigation-aware report that is useful for defensive binary triage?

The project evaluates three research questions:

1. **Performance:** How do runtime, CPU cost, memory use, and throughput compare with established gadget tools under controlled conditions?
2. **Semantic value:** Does separating raw candidates, exact suffix observations, semantic primitives, unknown candidates, and scores provide more actionable evidence than a raw gadget dump?
3. **Operational use:** Can the resulting report support CI, vulnerability-management enrichment, or infrastructure-binary prioritization without claiming exploitability?

NASM is an implementation choice to evaluate, not a result. Performance and usefulness remain hypotheses until the fixed benchmark methodology and corpus support them.

## Current implemented pipeline

```text
read-only file mapping
  -> ELF64 x86_64 validation
  -> program-header analysis
  -> executable PT_LOAD + PF_X regions
  -> optional section-header metadata annotations
  -> raw ret and ret imm16 candidate windows
  -> exact suffix pattern IDs and ordered structural facts
  -> conservative semantic classes and explicit effects
  -> candidate-indexed raw, exact-suffix, and semantic-exact evidence
  -> candidate-indexed structured memory effects
  -> candidate-indexed architectural register, flag, control-flow, and stack-source effects
  -> heuristic scores
  -> command-owned report identity and complete-analysis summary
  -> text or JSON reporting
  -> integrated analyze report
```

Implemented commands:

```text
x64lens help
x64lens version
x64lens info <file>
x64lens mitigations <file>
x64lens gadgets [--format text|json] [--max-depth N] <file>
x64lens analyze [--format text|json] [--max-depth N] <file>
```

A `bench` CLI command is deferred until after `v0.1.0`. Research measurement remains under repository Make targets and scripts so orchestration stays independent from the analyzer being measured.

## Scope

The current `0.1.x` research line targets:

- Linux ELF64,
- x86_64,
- static local analysis,
- direct-syscall NASM core,
- program-header-authoritative executable mappings,
- pattern-based candidate discovery,
- conservative semantic classification,
- text and JSON output,
- reproducible comparison tooling.

The current line does not implement exploit generation, payload generation, remote interaction, symbolic execution, dynamic tracing, automatic vulnerability discovery, a mandatory full decoder, multi-architecture support, PE, or Mach-O.

## Important interpretation boundaries

- A **raw candidate** is a terminator-centered byte window.
- An **exact pattern** is a recognized suffix, not proof that the full window is one decoded instruction sequence.
- A **semantic primitive** is assigned only when the current classifier has a supported rule.
- An **unknown candidate** is preserved rather than overclassified.
- A **score** is relative utility under the current heuristic model, not exploitability.
- A successful schema `0.2.0` report states command identity and bounded enumeration completeness. Candidate-capacity exhaustion still fails before output; it is not silently converted into a partial report.
- Per-candidate `evidence` identifies raw, exact-suffix, and semantic-exact provenance; `full_sequence_valid` remains `null` until decoder evidence exists.
- A future **decoder-validated candidate** is one whose selected start decodes as a complete instruction sequence ending at the terminator; that evidence does not erase its raw or exact-suffix facts.
- A future **semantic-decoded candidate** is classified from decoded instruction and operand facts and remains distinct from a semantic-exact candidate.
- Current JSON reports include exact `stack_pop_order`, unordered semantic `controls`, explicit `clobbers`, coarse `side_effects`, `register_transfer`, structured `memory_access`, and `architectural_effects`. The formal schema keeps these additive fields optional for compatibility with retained earlier `0.2.0` reports; current-producer validation requires their presence and cross-field consistency, using `null` for inapplicable transfer or memory relations. The architectural side-car records represented GPR reads/writes, condition flags, return/syscall control flow, stack-source facts, and whether the exact-suffix model is complete. Ordered multi-pop candidates score 95 and positive aligned stack adjustments score 35 only after their semantic and architectural facts validate. Register-transfer and memory candidates remain unscored because source-value and address/content controllability are not represented. These remain semantic-exact facts; `full_sequence_valid` stays `null`.
- Analysis completeness is independent from decoder validity. `complete: true` means every loader-derived executable region was scanned within the current candidate capacity, not that every candidate is a decoder-validated instruction sequence.
- A mitigation result is a static indicator, not a final security verdict. The canary field is an indicator, not proof that every function is stack-protected. The stripped field and section labels are section-table metadata indicators, not runtime loader authority. Text section labels are escaped for single-line report stability, JSON labels are byte-safe escaped, and ambiguous or contradictory executable section metadata is left unlabeled.
- Exploitability requires an independent vulnerability and relevant runtime conditions.

See [`docs/design/metric-boundaries.md`](docs/design/metric-boundaries.md), [`docs/design/evidence-provenance-model.md`](docs/design/evidence-provenance-model.md), [`docs/design/sprint10-family-coverage.md`](docs/design/sprint10-family-coverage.md), [`docs/design/defensive-deployment-profile.md`](docs/design/defensive-deployment-profile.md), and [`docs/semantic-taxonomy.md`](docs/semantic-taxonomy.md).

## Quick start on Ubuntu 24.04

Install required development tools:

```bash
sudo apt update
sudo apt install -y nasm binutils gcc clang gdb make python3 python3-jsonschema python3-venv \
  python3-pip pipx time git curl ca-certificates unzip zip
pipx ensurepath
```

Repository helpers:

```bash
make install-dev-deps-ubuntu
make dev-tools-check
make doctor
```

Build and validate:

```bash
make clean
make
make samples
make test
make validation-smoke
make sprint10-closeout-smoke
make sprint-closeout-smoke
make patch-bundle-hygiene-smoke
make public-docs-hygiene-smoke
make public-artifact-content-smoke
make sprint10-primitive-smoke
make sprint10-register-transfer-smoke
make sprint10-stack-adjust-smoke
make sprint10-memory-smoke
make sprint10-family-coverage-smoke
make sprint10-architectural-effects-smoke
make sprint10-fixture-gate-smoke
make sprint10-contract-reconciliation-smoke
make json-effect-consistency-smoke
make public-overlay-verification-smoke
make research-stage-gates-smoke
make checksum-manifest-path-smoke
make decoder-gap-hardening-smoke
make decoder-gap-smoke
```

Run the checkpoint demo:

```bash
make checkpoint-demo
DEMO_TARGET=/bin/ls MAX_DEPTH=4 make checkpoint-demo
```

See [`docs/onboarding.md`](docs/onboarding.md) for the full Make target tour and [`docs/demo.md`](docs/demo.md) for the checkpoint demonstration.

## Optional baseline tools

ROPgadget, Ropper, and ropr are comparison baselines. They are not runtime dependencies.

```bash
make install-baseline-tools-user
make baseline-tools-check
```

Manual setup:

```bash
pipx install ROPGadget
pipx install ropper
make install-rustup-user
. "$HOME/.cargo/env"
make install-ropr-user
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
```

Ubuntu's apt-provided Cargo may be too old for the current ropr release. The rustup helper installs a current user-local stable toolchain.

## Example usage

```bash
./build/x64lens version
./build/x64lens info /bin/ls
./build/x64lens mitigations /bin/ls
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --max-depth 4 /bin/ls
```

Generate and validate JSON:

```bash
./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/gadgets > /tmp/x64lens-analysis.json
python3 -m json.tool /tmp/x64lens-analysis.json >/dev/null
python3 tools/validate-json-report.py \
  --mode fixture --require-schema 0.2.0 --expected-command analyze \
  --require-provenance --require-sprint10-effects \
  --require-sprint10-architectural-effects /tmp/x64lens-analysis.json
```

The same flags are accepted in either documented order:

```bash
./build/x64lens analyze --max-depth 4 --format json <file>
./build/x64lens analyze --format json --max-depth 4 <file>
```

## Validation surface

Core checks:

```bash
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make build-tools-check
make sample-tools-check
make dev-tools-check
make test
make validate-gadget-fixture
make semantic-smoke
make schema-compat-smoke
make sprint10-primitive-smoke
make json-smoke
make analyze-smoke
make system-smoke
make capacity-smoke
make malformed-smoke
make mitigation-matrix-smoke
make section-label-smoke
make patch-bundle-hygiene-smoke
make public-docs-hygiene-smoke
make decoder-gap-hardening-smoke
make decoder-gap-smoke
make validation-smoke
make docker-test
make docker-validation-smoke
```

`make validation-smoke` is the local aggregate. It includes deterministic malformed-input and candidate-capacity checks; all Sprint 10 fixture, effect, cross-family, score-disposition, and false-positive boundaries; local/central ZIP metadata and authenticated-overlay policy; public-document/content gates; decoder-gap transaction/process/parser hardening; and controlled decoder-gap checks. Docker remains a separate reproducibility check because engine availability is environment-dependent.

Hostile-input checks can also be run directly:

```bash
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
make section-label-smoke
make capacity-smoke
make docker-validation-smoke
```

The malformed-input runner records seed hashes, expected and observed exit codes, signals, timeout state, elapsed nanoseconds, and output sizes. Generated mutations are temporary by default. Compact result artifacts are written under `tests/results/malformed/` and remain ignored by Git. Patch 028 adds explicit program-header and section-header table-end wrap cases to keep checked arithmetic from regressing. Patch 030 preserves that baseline while adding dynamic-table malformed cases to the mitigation matrix. Patch 031 adds duplicate-`PT_DYNAMIC` rejection. Patch 032 keeps the malformed-smoke baseline unchanged while adding invalid dynamic string-table evidence to the mitigation matrix.


### Section-label hardening smoke

`make section-label-smoke` builds temporary ELF64 fixtures with controlled section-name metadata. It verifies that `.text` labels are preserved, newline-bearing section names are escaped in text output, high-bit section-name bytes remain JSON-safe, non-executable overlapping sections do not capture executable offsets, ambiguous overlapping executable sections remain unlabeled, and file-offset/virtual-address disagreement leaves records unlabeled. The target writes ignored JSON evidence under `tests/results/section-label/`.

The mitigation oracle creates controlled ELF64 program-header layouts independently of compiler defaults. It verifies exact loader-level mitigation and region facts, matching integrated JSON values, direct gadgets JSON values, and stable malformed failure behavior. Its ignored evidence is written under `tests/results/mitigation-matrix/`. Patch 034 expands the oracle to 24 valid cases, 14 malformed cases, and one unsupported fail-closed case; Patch 035 keeps those counts and adds a focused `section-label-smoke` harness; Patch 036 keeps the matrix counts while expanding the focused section-label harness to six cases. Coverage includes canary-present/canary-absent indicators, zero-length dynamic string-table negative evidence including the exact load-endpoint case, stripped and not-stripped section-table indicators, section-label fixture checks, valid non-`DT_NULL` dynamic tables, invalid dynamic string-table rejection, duplicate `DT_STRTAB` and `DT_STRSZ` rejection, over-cap string-table rejection, `DT_BIND_NOW`, `DT_FLAGS`, `DT_FLAGS_1`, full RELRO combinations, duplicate-`PT_DYNAMIC` rejection, and gadget command-path coverage for dynamic malformed inputs.

Patch bundle hygiene:

```bash
make patch-bundle-hygiene-smoke
BUNDLE=/path/to/patch.zip make patch-bundle-hygiene
```

The checker inspects ZIP metadata without extraction and applies the public/private boundary under any archive root. It rejects unsafe paths, private context, environment files, secrets, generated outputs, symlinks, case-colliding members, and nested archives while preserving explicit public placeholders such as `.env.example` and `benchmarks/results/.gitkeep`.

Decoder-gap development evidence:

```bash
make decoder-gap-smoke
make decoder-gap-campaign
```

The controlled smoke reconciles x64lens candidate provenance with GNU objdump on the hand-authored fixture. The broader campaign adds selected installed system binaries. Patches 043 and 044 snapshot each target before measurement so x64lens and objdump analyze identical immutable bytes, reap interrupted child process groups, normalize reviewed objdump prefix/return spellings, and publish result trees transactionally across failures and signals. Objdump remains external comparison evidence; it does not change loader authority, candidate records, semantic classes, or scores. The default runtime remains decoder-free and single-worker. A future decoder is candidate-scoped and optional, and any parallel profile must pass deterministic-output, global-capacity, cleanup, wall-time, aggregate CPU, peak-RSS, startup-cost, and binary-size gates before default use.

## Benchmark workflow

Legacy development smoke comparison:

```bash
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
```

Sprint 11 high-resolution runner validation and controlled diagnostic run:

```bash
make diagnostic-tools-check
make diagnostic-runner-smoke
make sprint11-diagnostic-reference-smoke
make diagnostic-task-definitions-smoke
make bench-diagnostic-smoke
```

The diagnostic runner retains and hashes its source, exact specification, tools, targets, and timer probe. Actual child execution uses write-sealed Linux `memfd` copies bound to those retained hashes; campaign-relative replay commands still resolve to byte-identical retained files. The runner records monotonic nanosecond wall time plus Linux `wait4` resource data for the selected child, preserves stdout/stderr and failed rows, rechecks retained artifact identities after the final child exits, measures a timer floor, counterbalances condition order, cleans same-group and escaped descendants, and publishes one complete ignored campaign tree. The `wait4` counters include descendants that the selected child already waited for, but exclude descendants reaped separately by the runner; maximum RSS is a maximum within that scope, not a process-tree sum. These rows remain mutable development evidence and are not publication results.

The current CLI has no report-suppressed scanner-only condition. Schema `0.2.0` JSON from `gadgets` and `analyze` also shares the same analysis body and differs by command identity. Patch 055 records those boundaries instead of relabeling report cost as scanner cost or claiming the two JSON commands perform independent workloads. Sprint 15 freezes the final method, Sprint 16 runs the preview pilot, and Sprint 17 owns the publication-grade campaign.

See [`docs/benchmark-methodology.md`](docs/benchmark-methodology.md), [`docs/design/diagnostic-benchmark-task-definitions.md`](docs/design/diagnostic-benchmark-task-definitions.md), and [`docs/benchmark-smoke-interpretation.md`](docs/benchmark-smoke-interpretation.md).

Sprint 11 provisional corpus regeneration:

```bash
make corpus-tools-check
make provisional-corpus-smoke
make provisional-corpus-build
make provisional-corpus-verify
```

Patch 056 tracks one project-authored freestanding C source and a versioned
24-target GCC/Clang matrix. Generated binaries remain ignored and are never
executed by the builder. Each result retains source, license, builder, tool,
command, environment, output, SHA-256, and bounded ELF-generation evidence,
then publishes through no-replace transactional semantics. The matrix is
explicitly diagnostic, unfrozen, and not publication eligible. Requested PIE
and shared roles remain build intents until Sprint 12 resolves loader identity.

See [`benchmarks/corpus/README.md`](benchmarks/corpus/README.md),
[ADR 0042](docs/adr/0042-provisional-corpus-provenance-and-regeneration.md), and
the [Patch 056 validation record](docs/sprints/sprint-11-patch-056-validation.md).

Patch 057 hardens that diagnostic foundation before baseline adapters are added.
Target snapshots supplied to measured tools now require Linux
`MFD_NOEXEC_SEAL` and an execution seal; unsupported kernels fail the runner
prerequisite instead of falling back to a mode-only claim. Corpus builds reject
undeclared compiler workspace members, verification enforces the exact retained
member set, staging cleanup is checked rather than ignored, and
`make clean-provisional-corpus` derives the only removable path from the corpus
specification and output root. These controls do not turn the runner into a
sandbox: a hostile measured program could copy input bytes elsewhere, so
diagnostic tools remain trusted measurement participants.

See [ADR 0043](docs/adr/0043-sprint11-diagnostic-integrity-correction.md) and
the [Patch 057 validation record](docs/sprints/sprint-11-patch-057-validation.md).

## Architecture

The core separation is mandatory:

```text
file mapping and bounds
  -> ELF and loader facts
  -> raw scanner
  -> exact pattern matcher and ordered structural facts
  -> semantic classifier and explicit effects
  -> candidate-indexed evidence provenance
  -> scoring
  -> report identity and completeness facts
  -> text/JSON adapters
```

Future decoder facts, mitigation evidence, and output adapters must be added through bounded views or side-car records. They must not replace raw candidate facts or duplicate the analysis pipeline.

See [`docs/design/primitive-effect-model.md`](docs/design/primitive-effect-model.md), [`docs/adr/0032-ordered-multi-pop-foundation.md`](docs/adr/0032-ordered-multi-pop-foundation.md), [`docs/adr/0033-exact-register-transfer-effects.md`](docs/adr/0033-exact-register-transfer-effects.md), [`docs/adr/0034-bounded-stack-adjust-and-public-artifact-content-policy.md`](docs/adr/0034-bounded-stack-adjust-and-public-artifact-content-policy.md), [`docs/design/defensive-deployment-profile.md`](docs/design/defensive-deployment-profile.md), [`docs/design/candidate-scoped-decoder-and-parallelism.md`](docs/design/candidate-scoped-decoder-and-parallelism.md), [`docs/architecture.md`](docs/architecture.md), [`docs/design/decoder-roadmap.md`](docs/design/decoder-roadmap.md), [`docs/adr/0012-roadmap-expansion-and-research-release-gates.md`](docs/adr/0012-roadmap-expansion-and-research-release-gates.md), [`docs/adr/0013-deterministic-hostile-input-regression-harness.md`](docs/adr/0013-deterministic-hostile-input-regression-harness.md), [`docs/adr/0016-bounded-dynamic-table-view.md`](docs/adr/0016-bounded-dynamic-table-view.md), and [`docs/adr/0022-historical-findings-hardening.md`](docs/adr/0022-historical-findings-hardening.md).

The completed Sprint 10 authority chain continues through
[ADR 0037](docs/adr/0037-architectural-effects-and-contract-reconciliation.md),
[ADR 0038](docs/adr/0038-patch051-corrective-effect-and-gate-hardening.md),
the [family coverage table](docs/design/sprint10-family-coverage.md), the
[exact-pattern catalog](docs/design/sprint10-exact-pattern-catalog.md), the
[scoring model](docs/scoring-model.md), the
[output contract](docs/contracts/output-contract.md), and the
[Patch 052 validation record](docs/sprints/sprint-10-patch-052-validation.md),
[ADR 0039](docs/adr/0039-benchmark-informed-capability-roadmap.md), and the
[Patch 053 validation record](docs/sprints/sprint-10-patch-053-validation.md),
[ADR 0040](docs/adr/0040-sprint10-closeout-and-diagnostic-benchmark-entry.md),
the [Patch 054 validation record](docs/sprints/sprint-10-patch-054-validation.md),
the [Sprint 10 retrospective](docs/sprints/sprint-10-retro.md),
[ADR 0041](docs/adr/0041-sprint11-diagnostic-runner-foundation.md), and the
[Patch 055 validation record](docs/sprints/sprint-11-patch-055-validation.md).

## Roadmap and release gates

The canonical twenty-two-sprint roadmap defines:

- Sprint 7 hostile-input hardening,
- Sprint 8 mitigation and metadata depth,
- Sprint 9 report identity, completeness, evidence provenance, and decoder-gap measurement,
- Sprint 10 evidence-aware primitive expansion and contract closure, complete through Patch 054,
- Sprint 11 diagnostic benchmark infrastructure and a provisional reproducible corpus,
- Sprints 12 through 14 loader/mitigation precision, semantic capability completion, and optional decoder/concurrency ablations,
- Sprint 15 corpus, schema, baseline, command, task-definition, and methodology freeze,
- Sprint 16 frozen preview pilot and `v0.1.0-rc1`,
- Sprint 17 publication-grade comparative campaign,
- Sprints 18 through 22 defensive triage, automation, infrastructure case study, replication freeze, and `v0.1.0`.

See [`docs/roadmap-22-sprints.md`](docs/roadmap-22-sprints.md), [`docs/design/benchmark-and-capability-stage-gates.md`](docs/design/benchmark-and-capability-stage-gates.md), and [`docs/research-release-plan.md`](docs/research-release-plan.md).

## Versioning

The current development version remains `0.1.0-dev`. The `v0.1.0-dev` tag
identifies the Sprint 6 integrated checkpoint; Patches 046 through 053 are later
pre-release work. Patch 054 closes Sprint 10 without moving a release tag.
Sprint 11 begins diagnostic measurement and a provisional corpus.

Planned release sequence:

```text
v0.1.0-dev   integrated development checkpoint
v0.1.0-rc1   research preview candidate
v0.1.0       first research release
```

Schema `0.2.0` is the current producer contract. Patch 040 added report identity and complete-analysis state; Patch 041 added candidate provenance compatibly while preserving Patch 040 and versioned `0.1.0` fixtures. Patches 046 through 049 add schema-compatible ordered-pop, clobber, side-effect, register-transfer, stack-adjust, and structured memory fields without redefining historical counts. Retained earlier `0.2.0` reports may omit those additive fields, while current producers must satisfy the stronger effect relationships. Patch 050 strengthens current-producer relationships for implicit return stack reads, syscall and pivot clobbers, and cross-family fixture promotion. Patch 051 adds compatible architectural effects and two validated score entries while keeping earlier `0.2.0` reports consumable. Patch 052 corrects the current effect and validation relationships without changing the field shape. Patch 053 changes planning and validation infrastructure only: it separates diagnostic measurement from the frozen confirmatory campaign and keeps decoder-backed facts and worker profiles optional. Patch 054 closes Sprint 10, reconciles public chronology and checksum-manifest rules, and activates Sprint 11 without changing the analyzer or schema. Decoder-backed facts remain additive rather than a mandatory default-runtime dependency.

See [`docs/versioning.md`](docs/versioning.md) and [`docs/design/schema-evolution.md`](docs/design/schema-evolution.md).

## Research and publication

The repository preserves the chain from implementation to evidence to paper:

```text
source and fixtures
  -> validators
  -> corpus manifest
  -> raw benchmark rows
  -> generated summaries
  -> claim-to-evidence matrix
  -> paper and release artifacts
```

See [`docs/publication-plan.md`](docs/publication-plan.md), [`docs/research-roadmap.md`](docs/research-roadmap.md), and [`docs/contracts/research-contract.md`](docs/contracts/research-contract.md).

## Ethics and safety

x64lens is intended for educational research, defensive binary triage, secure build validation, and authorized reverse engineering. It does not include exploit delivery, payload generation, remote scanning, or unauthorized target interaction.

See [`docs/ethics-and-safety.md`](docs/ethics-and-safety.md).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

## Optional analysis and review tools

The core build and validation path does not require `checksec`, `radare2`/`rabin2`, `strace`, or `shellcheck`. They are useful local review tools for mitigation comparison, ELF metadata comparison, syscall/cleanup inspection, and shell-helper linting. Treat their output as comparator evidence with version-specific semantics, not as authoritative replacement for x64lens contracts.

Example inventory commands:

```bash
command -v checksec && checksec --version || true
command -v rabin2 && rabin2 -v || true
command -v r2 && r2 -v || true
command -v strace && strace -V || true
command -v shellcheck && shellcheck --version || true
```

Repository targets:

```bash
make analysis-tools-check
make readelf-comparison-smoke
make optional-tool-comparison-smoke
make shellcheck-smoke
```

`readelf` comparison is part of the normal native validation aggregate.
`checksec`, `rabin2`, `strace`, and `shellcheck` remain optional local review
tools; absence should not block core build/test validation. The direct
comparison helpers accept either `<target> <tool>` or `<tool> <target>` and
print an explicit target identity line so optional review logs can be audited.
