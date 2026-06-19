# Sprint 06 Plan

## Status

In progress through Patch 022.

## Sprint goal

Produce a coherent semester checkpoint: integrated `analyze` command, stable demo path, reproducible benchmark seed, updated paper scaffold, and a roadmap for the expanded Sprint 7 through Sprint 12 arc.

Sprint 6 should not be treated as the end of the project if the semester schedule allows more work. It should be the first major public-quality checkpoint: the repository should be understandable, buildable, testable, and ready for deeper research expansion.

## Planned deliverables

- [x] Add `analyze` as the first integrated `0.1.0-dev` checkpoint command.
- [ ] Polish text report behavior for `info`, `mitigations`, `gadgets`, and `analyze`.
- [x] Reuse the Sprint 5 JSON report for `analyze --format json` checkpoint output.
- [ ] Produce development benchmark summary table from controlled fixtures and selected system binaries.
- [ ] Produce a repeatable demo script.
- [ ] Polish README.
- [ ] Polish architecture document.
- [ ] Polish validation plan.
- [ ] Polish benchmark methodology.
- [ ] Polish ethics and safety documentation.
- [ ] Update IEEE paper scaffold and related notes.
- [ ] Update future roadmap, including Sprint 7 through Sprint 12 if the expanded plan is adopted.
- [ ] Write Sprint 6 retrospective.

## Acceptance criteria

- [ ] `make clean && make && make test` succeeds after Patch 022.
- [ ] `make docker-test` succeeds.
- [ ] All documented demo commands, including `analyze`, run successfully.
- [ ] README usage matches actual CLI behavior.
- [ ] CHANGELOG reflects all completed sprint work.
- [ ] Benchmark methodology reflects what was actually measured.
- [ ] Paper scaffold is aligned with the implemented tool, not aspirational features.
- [ ] Release-readiness gaps are explicitly documented.

## Suggested validation commands

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
make validate-gadget-fixture
make pattern-smoke
make semantic-smoke
make json-smoke
make analyze-smoke
make system-smoke
make validation-smoke
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
./build/x64lens version
./build/x64lens help
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens mitigations ./tests/bin/minimal_nopie
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --format json --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-analyze.json
python3 tools/validate-json-report.py --mode fixture /tmp/x64lens-analyze.json
```

## Design constraints

- Finalize what exists. Do not imply unsupported features are complete.
- Public documentation must not depend on local/private context files.
- Research claims must be backed by captured benchmark data.
- Future work should be clear enough that Sprints 7 through 12 can proceed without large refactors.

## Stretch goals

- Create a tagged `v0.1.0-dev-checkpoint` release candidate.
- Generate checksums for a local release artifact.
- Add an artifact generation script that does not require private files.

## Patch 14 reviewer-readiness additions

Sprint 6 checkpoint documentation should include:

- an assembly-first rationale section,
- a pattern-scanner limitation section,
- a malformed-input safety status section,
- a metric-boundary summary,
- an explicit list of unsupported features,
- a reviewer-facing threats-to-validity draft for the paper scaffold.


## Patch 022 scope

Patch 022 introduces `analyze` now instead of deferring it until later mitigation hardening. The reason is practical: Sprint 5 already delivered scoring, JSON, validation hardening, baseline smoke comparisons, and onboarding checks. A checkpoint command makes the current tool usable as a single defensive triage report while preserving explicit limitations.

The command does not overclaim. It is a static report over the current facts. Sprint 7 remains responsible for mitigation and parser-safety hardening.
