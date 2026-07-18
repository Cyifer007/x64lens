# Development Contract

## Purpose

This contract defines the rules x64lens development must follow to preserve research quality, production readiness, maintainability, and course alignment.

## Rule 1: correctness before speed

Performance matters, but not before safe parsing and correct classification.

## Rule 2: parser safety is mandatory

Every file-derived offset, size, count, and pointer must be validated before use.

## Rule 3: module boundaries must be preserved

Scanner logic, semantic classification, scoring, and reporting must remain separate.

## Rule 4: internal facts before output formatting

Sprint 1 may print directly. By Sprint 3, analysis facts must be stored in records before being reported.

## Rule 5: JSON output must be versioned

Every JSON report must include `schema_version` and `tool_version`.

## Rule 6: benchmarks must be reproducible

Every benchmark claim must include tool versions, commands, corpus description, host information, and repeated runs.

## Rule 7: research claims must be hypotheses until measured

Do not claim that x64lens is faster, more accurate, or more useful until the benchmark data supports it.

## Rule 8: enterprise adoption requires stable contracts

CLI behavior, exit codes, JSON schema, and release artifacts must be documented.

## Rule 9: avoid scope sprawl

Every new feature must fit a sprint goal, backlog item, research question, or explicit roadmap stage.

## Rule 10: update contracts regularly

Review this contract at the end of each two-week sprint.


## Rule 11: public repository voice

Public repository content must read as project documentation, not as private coordination notes. Do not include private discussion context, attachment history, tool-assisted workflow details, or informal back-and-forth wording in committed code, comments, docs, tests, or examples.

## Comment and documentation rule

Every source file and configuration file must carry human-readable comments explaining what the file is for, how it participates in the build or analysis pipeline, and what future work belongs there. Assembly comments are not decorative. They are part of the learning and review surface.

## Implementation completion rule

Every implementation change must include:

1. Build steps.
2. Test steps.
3. Expected success behavior.
4. Known limitations.
5. Next steps after success.
6. Troubleshooting direction if the test fails.

## Documentation parity rule

Markdown documentation is equal to code. If the code changes the CLI, output schema, parser assumptions, semantic taxonomy, scoring model, benchmark method, or sprint status, the relevant Markdown must be updated in the same sprint.

## Contract review cadence

Contracts must be reviewed at the end of every sprint. The sprint retrospective should explicitly state whether any contract changed or whether contract drift was detected.

## Reviewer-readiness rules

1. Implementation language is not a result. NASM is a design choice to evaluate.
2. Parser safety must be tested, not asserted.
3. Exact suffix matching must not be described as full decoding.
4. Raw candidate counts must not be treated as semantic primitive counts.
5. Future decoder support must be added through side-car records, not scanner rewrites.
6. Script executable bits are part of the repository contract for shell helpers.
7. New public claims must map to evidence, not optimism.

## Validation escalation rule

When a validation issue or near-miss appears, the next patch should strengthen the validation surface rather than only fixing the immediate symptom. Prefer reusable validators, regression fixtures, and clear environment checks over one-off command transcripts.

Current examples:

- JSON output is validated by `tools/validate-json-report.py`.
- Real-binary smoke coverage is validated by `tools/system-binary-smoke.sh`.
- Docker availability is checked separately through `make docker-available-check`.
- Patch ZIP contents are checked through `tools/check-patch-bundle-hygiene.sh`.


## Public validation transcript rule

Public validation snippets should use generic prompts and repository-relative paths where possible. Avoid committing personal hostnames, local usernames, local home-directory paths, private attachment names, or dialogue-style context. Prefer examples such as:

```text
$ make test
tests: ok
```

Use repository facts, reproducible commands, and observed technical outcomes instead of private workflow narration.


## Development environment checks

Development environment checks are part of the contract. Build, test, JSON validation, system-binary smoke tests, Docker checks, and benchmark smoke targets should fail with actionable messages when required tools are missing. Optional baseline tools should be reported clearly and should not block normal development unless explicitly required.

## Integrated reporter reuse rule

Integrated commands must consume internal records and reuse report-section implementations. They must not scrape focused command text output or copy formatter logic into a second path.

## Roadmap and release-gate rule

After the Sprint 6 checkpoint, feature work must map to the canonical eighteen-sprint roadmap or an explicit ADR. The current priority order is parser safety, mitigation depth, evidence provenance, primitive expansion, corpus reproducibility, benchmark infrastructure, comparative experiments, triage, and release.

A planned release date does not override an unmet evidence gate. `v0.1.0-rc1` and `v0.1.0` require the artifacts and checks defined in `docs/research-release-plan.md`.

## Schema transition rule

Schema `0.2.0` is the current producer contract. Compatible per-candidate provenance additions should remain within `0.2.x`; changed count meaning or incompatible required fields require another explicit transition with full validator and documentation parity. The retained representative final-shape `0.1.0` snapshot remains a versioned compatibility artifact; the project does not claim validation of every intermediate pre-release `0.1.0` emission.

## Planning-document validation rule

`make planning-docs-check` verifies the canonical roadmap, release plan, design seams, ADR, and Sprint 7 through Sprint 18 plans. It is a structural guardrail, not a substitute for technical review.

## Hostile-input regression rule

Any patch that changes ELF field validation, table arithmetic, executable-region derivation, candidate boundaries, or file-derived iteration must update the deterministic malformed-input catalog or add a durable regression fixture. The patch must pass `make malformed-smoke` and `make capacity-smoke` before merge.

Malformed parse failures must not emit partial stdout. A signal, timeout, unexpected success, or changed failure class is a blocking regression until explained and documented.

Generated mutations are development evidence and remain ignored. A stable defect discovered by mutation testing must be minimized and promoted into `tests/malformed/regressions/` with its original failure mode, fixed expected result, and affected commands.

## Resource-capacity rule

Bounded storage must fail closed when a complete report cannot be produced. Silent truncation is prohibited. Candidate-arena exhaustion returns `EXIT_UNSUPPORTED` and reporters emit no partial text or JSON document. Schema completeness fields describe successful reports; they do not authorize partial output.

## Mitigation-oracle rule

Changes to ELF type interpretation, GNU stack handling, RELRO presence, dynamic-linking evidence, bind-now evidence, dynamic-entry counting, load permissions, executable-region counting, or program-header rejection behavior must update and pass the deterministic mitigation matrix. Parser refactors must preserve the oracle unless an intentional output-contract change is separately documented.


## Private validation orchestration boundary rule

Local validation missions, operational reports, command logs, temporary probes, and advisory review notes are private workflow artifacts. They must remain ignored, must not be shipped in public patch bundles, and must not be described as public product features. Convert only the technical result into public code, tests, documentation, or release evidence.

## Sprint 8 Patch 036 evidence-hygiene rule

Development evidence must fail closed when its own inputs or metrics are invalid. Benchmark smoke scripts must reject non-positive run counts, invalid max-depth values, nonnumeric timing/RSS fields, negative metric values, and silent mixed-artifact summaries. Docker build contexts must exclude local environment files. Report adapters must preserve JSON validity for hostile byte values instead of replacing evidence with lossy placeholders.


## Patch 037 comparator checks

Normal native validation includes automated `readelf` comparison and benchmark
TSV integrity checks. Optional `checksec`, `rabin2`, `strace`, and `shellcheck`
tools may be inventoried through `make analysis-tools-check`, but their absence
must not block the core build/test path.

## Sprint 8 closeout helper rule

Optional comparison helpers must not silently compare a different file from the
one named by the caller. When a helper accepts more than one argument order, it
must validate which argument is the analyzer binary, which argument is the target
ELF, and print that resolved identity before producing comparator output. It
must not execute the target binary merely to infer argument order.

Strict shell-helper lint is an optional local gate. When enabled, intentional
literal examples or ordered boundary patterns must be explained in source rather
than ignored silently.

## Sprint 9 Patch 040 report-envelope rule

Command identity and analysis completeness are internal facts, not formatter
inferences. `gadgets` and `analyze` must construct the shared fixed-size analysis
summary only after scanner, exact-pattern, classifier, scoring, and annotation
stages succeed. Text and JSON adapters may render that record but must not decide
completion independently.

Schema `0.2.0` current-report validation must name the expected command.
Representative schema `0.1.0` output remains a compatibility fixture. Candidate-
capacity overflow remains fail-closed with no report; completeness fields do not
authorize silent or partial truncation.


## Candidate evidence side-car rule

Candidate provenance and future decoder facts must remain outside the
scanner-owned raw gadget record. Dense side-car arrays may use candidate index
as the implicit key. A provenance materializer may reconcile existing facts but
must not scan bytes, decide semantics, score candidates, or format output.

Formal Draft 2020-12 schema validation and the semantic cross-field validator
are complementary required gates. Current JSON-producing harnesses should apply
the canonical validator before specialty assertions.


## Portable artifact-boundary rule

Public ZIP validation must be independent of a preferred archive root. The
checker and its regression smoke must share one path-policy implementation and
must inspect metadata without extraction. Unsafe paths, private/local state,
environment or secret material, generated outputs, symlinks, case collisions,
and nested archives fail closed. Explicit public placeholders require narrow
allowlists rather than broad directory exceptions.


## External decoder-evidence rule

External disassemblers are development and research validators, not runtime
mapping or classification authority. Decoder-gap tooling may consume current
JSON records and canonical disassembly to produce side artifacts, but it must
not rewrite candidate records, semantic classes, scores, or report counts.

Every campaign must preserve exact commands, versions, executable and target
hashes, raw outputs, and categorized disagreement facts. Generic count deltas
are insufficient. A runtime decoder may be approved only through the documented
decision gate and must preserve raw-scanner operation and side-car metric
separation.

## Decoder-gap campaign integrity rule

A development comparison campaign must bind every tool invocation to immutable
input bytes and must publish result trees transactionally. `SIGINT`, `SIGTERM`,
timeout, parser failure, or child-process failure must leave either the prior
recognized result or one complete new result. External decoder/disassembler
facts remain adapters and may not alter analyzer runtime records.

## Candidate-scoped verification and acceleration rule

A future decoder must consume bounded candidate windows and emit side-car facts;
it must not replace loader mapping or raw scanning. A future parallel profile
must preserve deterministic output, global bounded capacity, cleanup, and a
one-worker mode. Neither becomes the default before fixed-corpus latency, RSS,
binary-size, and correctness evidence exists.

## Sprint closeout gate

A sprint that changes public shell helpers or validation tooling closes only after strict ShellCheck and the full native aggregate pass through `make sprint-closeout-smoke`. Docker validation remains separately required when the sprint acceptance plan names it.

The reference runtime must remain independently buildable and measurable without optional decoders or worker libraries. Candidate-scoped decoding and parallel execution are allowed only as explicit, evidence-backed profiles that preserve existing module and metric boundaries.

## Ordered primitive-effect rule

Expanded exact families must carry structural facts before semantic promotion.
When instruction order matters, an unordered register bitmap is insufficient.
Pattern recognition records order; classification records controlled,
clobbered, stack, and side-effect facts; scoring remains independent; reporters
render records without reconstructing semantics.

Every new family requires:

1. a controlled source fixture;
2. exact byte and fallback expectations;
3. text and JSON parity;
4. provenance and schema validation;
5. explicit score inclusion or deliberate unscored status;
6. unchanged fail-closed capacity and malformed-input behavior.

## Public artifact textual-content rule

Metadata-only archive validation and public textual-content validation are separate mandatory gates. Public source overlays must pass both. Textual patch and diff members are scanned as distributed content, including deleted lines. Local application packages may contain private context or local patch material only when they are clearly separated from public release artifacts.

## Exact stack-adjust family rule

An exact arithmetic stack family must validate opcode, operand, immediate domain, terminator, and candidate bounds before semantic promotion. Arithmetic flag modification must remain visible as an effect. Unsupported forms fall back to the strongest existing fact rather than receiving a broader semantic claim.

## Memory-effect side-car rule

Structured memory facts belong in a candidate-index side-car rather than in reporter inference or variable-length raw records. The materializer may reconcile exact and semantic facts but must not scan bytes, parse ELF, classify candidates, score them, or emit output. New address forms require controlled fixtures and exact operand semantics before promotion.

## Public overlay authentication rule

A final-file public patch archive must authenticate the complete object. Validation must bind a caller-supplied outer SHA-256 to the archive, apply metadata and textual-content policies, and reconcile every member against an internal manifest. The content policy must scan its own implementation rather than exempting the checker source.


## Cross-family fixture and fail-fast rule

A controlled fixture may exercise more than one implemented family. Validation must classify each candidate according to the strongest implemented exact rule rather than preserve stale expectations from the fixture's original patch. Multi-command Make recipes must use fail-fast shell semantics so an intermediate validator failure cannot be masked by a later successful command.

Every implemented family must identify its fixture, effect contract, fallback boundary, and score disposition in the maintained Sprint 10 family coverage table.

## Architectural-effect side-car rule

Architectural register, flag, control-flow, and stack-source facts belong in a
dense candidate-index side-car materialized after classification and structured
memory effects. The materializer may reconcile existing records but must not
scan target bytes, classify, score, or format output.

Scoring may consume the side-car only to validate facts required by a reviewed
score rule. A score mismatch must fail closed rather than causing the scorer to
infer or repair semantic state.
