# Sprint 06 Plan

## Status

Implementation complete through Patch 023. Patch 024 is the final planning and architecture alignment candidate before Sprint 7.

## Sprint goal

Produce the first coherent integrated checkpoint: one `analyze` command, stable text and JSON paths, repeatable validation and demonstration commands, current-state paper framing, and a documented transition into evidence-driven hardening and research work.

## Delivered

- [x] Add `analyze` as the integrated `0.1.0-dev` checkpoint command.
- [x] Reuse internal analysis records instead of reparsing text output.
- [x] Reuse the Sprint 5 JSON report for integrated machine-readable output.
- [x] Emit one top-level version and target banner in integrated text output.
- [x] Preserve complete output for focused `info`, `mitigations`, and `gadgets` commands.
- [x] Add a repeatable controlled and system-binary demo path.
- [x] Document exact checkpoint commands in README and `docs/demo.md`.
- [x] Document conservative interpretation of current smoke benchmark data.
- [x] Align the IEEE paper scaffold with implemented behavior and limitations.
- [x] Add local `v0.1.0-dev` tag guidance.
- [x] Add public-documentation hygiene validation.
- [x] Write the Sprint 6 retrospective.
- [x] Reassess Sprints 7 through 12 against the implemented checkpoint.
- [x] Define Sprints 13 through 18 and evidence-based release milestones.
- [x] Define parser-safety, mitigation, provenance, decoder, primitive, corpus, benchmark, schema, and publication gates.
- [x] Add automated planning-document consistency validation.

## Acceptance criteria

- [x] Native build and automated tests pass for the Patch 023 checkpoint.
- [x] Fixture, semantic, JSON, analyze, and system-binary smoke targets pass for the Patch 023 checkpoint.
- [x] Docker remains a separate reproducibility check.
- [x] `analyze` contains one banner while retaining all report sections.
- [x] README usage matches actual CLI behavior.
- [x] Benchmark notes distinguish development evidence from research results.
- [x] Paper scaffold avoids claims not supported by measured evidence.
- [x] Remaining limitations are explicit.
- [ ] Patch 024 planning, documentation, and regression validation passes.

## Checkpoint commands

```bash
make validation-smoke
make checkpoint-demo
DEMO_TARGET=/bin/ls MAX_DEPTH=4 make checkpoint-demo
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
make docker-test
```

## Local checkpoint tag

The local annotated tag should identify the clean Patch 023 checkpoint commit:

```bash
make checkpoint-tag-help
git show --stat --decorate v0.1.0-dev
git rev-parse v0.1.0-dev^{}
git rev-parse HEAD
```

A normal branch push does not publish the tag. Tag publication remains a separate release decision.

## Transition

Patch 024 freezes the post-checkpoint roadmap and release gates. Once validated, Sprint 7 begins with hostile-input hardening, bounded parser infrastructure, and regression-corpus preservation. Additional presentation work is not the next priority.
