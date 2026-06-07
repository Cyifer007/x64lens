# Sprint 06 Plan

## Status

Planned.

## Sprint goal

Produce a coherent semester checkpoint: stable demo path, reproducible benchmark seed, updated paper scaffold, and a roadmap for the expanded Sprint 7 through Sprint 12 arc.

Sprint 6 should not be treated as the end of the project if the semester schedule allows more work. It should be the first major public-quality checkpoint: the repository should be understandable, buildable, testable, and ready for deeper research expansion.

## Planned deliverables

- [ ] Finalize current CLI behavior for the `0.1.0-dev` semester checkpoint.
- [ ] Finalize text report behavior for `info`, `mitigations`, `gadgets`, and possibly `analyze`.
- [ ] Finalize initial JSON report if Sprint 5 lands JSON.
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

- [ ] `make clean && make && make test` succeeds.
- [ ] `make docker-test` succeeds.
- [ ] All documented demo commands run successfully.
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
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
./build/x64lens version
./build/x64lens help
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens mitigations ./tests/bin/minimal_nopie
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
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
