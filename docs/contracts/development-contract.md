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
