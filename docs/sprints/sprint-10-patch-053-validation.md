# Sprint 10 Patch 053 Validation

## Purpose

Patch 053 corrects the remaining Patch 052 harness, documentation, planning,
and checksum-verification defects and records the benchmark-informed
capability roadmap. It adds no analyzer primitive, record, schema, capacity,
decoder, or concurrency change.

## Expected source scope

- two-token internal harness correction;
- one manifest-relative checksum verifier and regression;
- one research-stage/capability-gate specification and regression;
- canonical twenty-two-sprint roadmap and Sprint 11-22 plan reconciliation;
- public documentation and planning updates;
- no change to analyzer output facts.

## Required validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make checksum-manifest-path-smoke
make research-stage-gates-smoke
make memory-effect-reconciliation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

Docker:

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

## Expected focused results

```text
memory-effect-reconciliation-smoke: ok cases=7 accepted=2 rejected=5
checksum-manifest-path-smoke: ok cases=4 accepted=1 rejected=3
research-stage-gates-smoke: ok stages=7 capability_gates=9 conditional_profiles=3 release_sprint=22
planning-docs-check: ok plans=22 forward_plans=14
```

## Regression requirements

- The memory harness must use `GADGET_SUMMARY_RECORD_SIZE` at both allocation
  sites.
- Checksum entries must resolve relative to the manifest location regardless of
  the caller's current directory.
- The canonical roadmap must be `docs/roadmap-22-sprints.md`.
- The eighteen-sprint file must be explicitly superseded.
- Diagnostic, frozen preview, and publication datasets must remain separate.
- Candidate-scoped decoding and parallelism must remain optional profiles.
- No public documentation may claim measured speed, RSS superiority,
  invisibility, or anti-analysis evasion without evidence.

## Deferred validation

The cloud environment may not provide NASM, ShellCheck, Docker, GDB, or strace.
Those checks remain mandatory in WSL2 and must be classified separately from
source defects.

## Handoff

Patch 054 closes Sprint 10 after Patch 053 receives an authoritative local
acceptance decision. Sprint 11 then begins diagnostic measurement rather than a
publication corpus freeze.
