
# Sprint 06 Plan

## Status

Complete through Patch 023.

## Sprint goal

Produce the first coherent integrated checkpoint: one `analyze` command, stable text and JSON paths, repeatable validation and demonstration commands, current-state paper framing, and a documented transition into the expanded roadmap.

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

## Acceptance criteria

- [x] Native build and automated tests pass.
- [x] Fixture, semantic, JSON, analyze, and system-binary smoke targets pass.
- [x] Docker remains a separate reproducibility check.
- [x] `analyze` contains one banner while retaining all report sections.
- [x] README usage matches actual CLI behavior.
- [x] Benchmark notes distinguish development evidence from research results.
- [x] Paper scaffold avoids claims not supported by measured evidence.
- [x] Remaining limitations are explicit.

## Checkpoint commands

```bash
make validation-smoke
make checkpoint-demo
DEMO_TARGET=/bin/ls MAX_DEPTH=4 make checkpoint-demo
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
make docker-test
```

## Local tag

After Patch 023 is committed:

```bash
make checkpoint-tag-help
git tag -a v0.1.0-dev   -m "x64lens v0.1.0-dev integrated checkpoint"
git show --stat --decorate v0.1.0-dev
```

The tag remains local until explicitly pushed.

## Transition

Patch 024 performs the architecture and roadmap review for Sprints 7 through 18. Sprint 7 implementation then begins with mitigation and hostile-input hardening.
