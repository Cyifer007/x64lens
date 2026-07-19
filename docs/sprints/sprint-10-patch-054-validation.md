# Sprint 10 Patch 054 Validation

## Status

Sprint 10 is closed by Patch 054. Sprint 11 is active as the diagnostic
benchmark stage.

## Purpose

Patch 054 closes Sprint 10 by reconciling the public roadmap, adding maintained
closeout and checksum-manifest gates, recording the retrospective, and
activating Sprint 11 diagnostic measurement.

Patch 054 changes documentation and development/release validation only. It does
not change analyzer assembly, public record layouts, CLI behavior, schema
`0.2.0`, exact patterns, semantic classification, scoring, capacity, decoder
policy, or worker policy.

## Required invariants

- Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable
  authority.
- Raw, exact, semantic-exact, unknown, decoder-backed, and scored facts remain
  distinct.
- `gadget_record` remains 112 bytes and candidate capacity remains 4096.
- The fixed analysis arena remains 819200 bytes.
- Tool version remains `0.1.0-dev`; schema remains `0.2.0`.
- Candidate 4097 returns exit code 6 before text or JSON stdout.
- Malformed-input failures emit no partial stdout.
- The reference runtime remains dependency-free, decoder-free, and one-worker.
- Diagnostic benchmark evidence remains separate from the Sprint 15-frozen
  confirmatory campaign.

## Corrective findings

### Checksum-manifest co-location

Release checksum inventories may reference only co-located artifacts. If a
package manifest is listed, it must be present and authenticated beside the
inventory; verification must also succeed from an unrelated working directory.

### Roadmap chronology

Active public authorities must agree on this sequence:

```text
Sprint 11  diagnostic benchmark foundation
Sprints 12-14  capability hardening and optional-profile decisions
Sprint 15  campaign freeze
Sprint 16  frozen preview and v0.1.0-rc1 candidate
Sprint 17  publication comparative campaign
Sprints 18-20  defensive value and operational evidence
Sprints 21-22  replication, paper freeze, and v0.1.0 release
```

### Public repository voice

Public validation and roadmap documents describe repository facts, commands,
evidence, and limitations. They do not depend on private execution handoffs,
transfer history, or reviewer-specific acceptance narration.

## Focused gates

```bash
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
make research-stage-gates-smoke
make research-roadmap-consistency-smoke
make sprint10-closeout-smoke
make checksum-manifest-path-smoke
```

Expected focused results:

```text
public-docs-hygiene-smoke: ok cases=16 accepted=1 rejected=15
research-stage-gates-smoke: ok stages=7 capability_gates=9 conditional_profiles=3 release_sprint=22 completed_sprints=10 active_sprint=11
research-roadmap-consistency-smoke: ok documents=28 milestones=5 forbidden_patterns=9 path_claims=7 completed_sprints=10 active_sprint=11
sprint10-closeout-smoke: ok sprint=10 patches=9 families=11 exact_patterns=25 semantic=17 exact_only=8 scored=14 model_complete=23 model_partial=2 fixture_groups=5 next_sprint=11
planning-docs-check: ok plans=22 forward_plans=14 closed_sprints=10 active_sprint=11
checksum-manifest-path-smoke: ok cases=4 accepted=1 rejected=3
```

## Full validation matrix

```bash
make normalize-perms
make script-perms-check
make ownership-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make clean
make
make samples
make test
make memory-effect-reconciliation-smoke
make sprint10-family-coverage-smoke
make sprint10-contract-reconciliation-smoke
make sprint10-score-policy-smoke
make sprint10-closeout-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

Container validation remains a separate reproducibility gate:

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

## Validation criteria

- Every focused and aggregate gate exits 0.
- Strict ShellCheck is available and clean.
- Native and qualified container reports remain byte-identical for the controlled
  parity matrix.
- A public overlay passes metadata, content, outer-hash, and internal-
  manifest verification.
- Every checksum-listed package manifest is present beside the inventory.
- The checksum inventory verifies from its own directory and from an unrelated
  working directory.
- The checkpoint tag remains pinned to its original Sprint 6 commit.
- The final tracked worktree is clean.

## Sprint 11 entry

With Sprint 10 closed, Sprint 11 is active with diagnostic measurement over a
provisional corpus. The confirmatory corpus and method remain unfrozen until the
Sprint 15 campaign freeze.


## Patch 055 corrective supersession

Patch 055 preserves the Patch 054 closeout state and adds permanent regressions
for two post-closeout checker weaknesses. Seven exact stale chronology phrases
are now rejected by path-specific rules. The closeout checker now reads version,
record-size, capacity, arena, and optional-profile facts from maintained source
authorities and reconciles catalog counts against the independent one-per-
pattern JSON fixture. Its success banner renders observed counts.

Run:

```bash
make patch054-corrective-regression-smoke
```

Expected:

```text
patch054-corrective-regression-smoke: ok roadmap_cases=7 closeout_cases=3
```
