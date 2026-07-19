# Sprint 10 Retrospective

## Status

Closed by Patch 054 after closeout validation.

## Sprint goal recap

Sprint 10 expanded semantic-exact primitive coverage while preserving evidence
provenance, bounded storage, explicit uncertainty, independent scoring, and the
dependency-free defensive deployment profile.

## Delivered outcomes

- Patch 046 added ordered two-pop argument-control patterns and ordered stack-pop
  facts without growing the raw candidate record.
- Patch 047 added exact register-direct transfer semantics and relational JSON
  validation.
- Patch 048 added positive aligned stack-adjust semantics and explicit arithmetic
  flag effects.
- Patch 049 added a dense memory-effect side-car and bounded qword base-plus-zero
  memory reads and writes.
- Patch 050 completed current-family coarse effects, cross-family fixture
  expectations, fail-fast recipes, and family-level false-positive policy.
- Patch 051 reconciled three implementation passes into a 24-byte architectural-
  effect side-car, one-per-pattern fixture, centralized fixture suite, and
  selective scores.
- Patch 052 corrected effect encoding, `ret imm16 0`, text-list formatting,
  memory-sidecar reconciliation, score-policy gates, and native/container parity.
- Patch 053 corrected the remaining harness issue and established diagnostic
  measurement before confirmatory campaign freeze.
- Patch 054 reconciled roadmap chronology, public repository voice, closeout
  contracts, and complete delivery authentication.

## Architecture review

Sprint 10 preserved the analysis pipeline:

```text
read-only mapping and bounds
  -> ELF and loader facts
  -> executable regions
  -> raw candidate scanning
  -> exact suffix recognition
  -> conservative semantic classification
  -> candidate provenance
  -> memory effects
  -> architectural effects
  -> independent scoring
  -> text and JSON adapters
```

The scanner-owned record remains fixed at 112 bytes. Later facts use dense
candidate-indexed side-cars. No variable-length decoder state, per-candidate
heap allocation, or reporting-time semantic inference was introduced.

## Capability review

The Sprint 10 exact catalog contains 25 pattern identities, including:

- all 16 single-pop GPR suffixes;
- ordered two-register argument-pop combinations;
- exact non-RSP qword register transfers;
- positive aligned `add rsp, imm8; ret` forms;
- exact qword base-plus-zero memory reads and writes;
- return, pivot, leave, and syscall forms inherited from earlier sprints.

The maintained contracts record:

```text
11 semantic-family contracts
25 exact-pattern contracts
5 fixture-suite groups
17 semantic patterns
8 exact-only patterns
14 scored patterns
23 complete represented effect models
2 partial represented effect models
```

The two partial models remain `pop rsp; ret` and `syscall; ret`, where the current
compact static model cannot honestly represent all dynamic behavior.

## Metric and scoring review

Raw, exact, semantic, unknown, decoder-backed, and scored populations remain
separate. Exact-only single-pop forms retain deterministic architectural effects
without receiving unsupported semantic roles.

Sprint 10 added score 95 for validated ordered two-pop argument control and score
35 for validated positive aligned stack adjustment. Register-transfer and memory
families remain unscored because source-value, address, and content
controllability are not represented.

Scores remain relative utility hypotheses, not exploitability probabilities,
vulnerability severity, or binary-level risk.

## Resource and deployment review

The reference profile remains:

```text
gadget_record                    112 bytes
candidate_evidence_record         48 bytes
memory_effect_record              16 bytes
candidate_effect_record           24 bytes
candidate capacity              4096
fixed command arena           819200 bytes
```

No mandatory decoder, dynamic interpreter, shared library, helper process, or
thread runtime was added. This preserves a bounded reference artifact for later
air-gapped, incident-response, minimal-container, defensive-triage, and CI/CD
evaluation.

These are architecture and fixed-allocation facts. Sprint 10 does not claim
measured speed, RSS superiority, universal coverage, invisibility, or guaranteed
anti-analysis evasion.

## Validation lessons

- A successful aggregate is meaningful only when intermediate validators cannot
  be masked by later commands.
- Cross-family promotion is expected when the strongest implemented exact rule
  changes; fixtures must model current semantics rather than historical labels.
- Side-car materializers require exact same-index reconciliation, including
  reserved bits and inapplicable fields.
- Public final-file overlays and local Git patches serve different purposes.
- Delivery manifests and checksum inventories are part of acceptance, not an
  afterthought.
- Machine-readable stage gates need cross-document narrative checks because file
  presence alone cannot detect contradictory schedules.

## Research decision

Measurement begins in Sprint 11 as diagnostic engineering evidence. The
provisional corpus and runner may change as they reveal bottlenecks, task
mismatches, or capability gaps. Sprint 15 freezes the confirmatory method;
Sprints 16 and 17 run the frozen preview and publication campaign.

This design lets benchmarking improve the implementation before it is used to
test the final hypotheses.

## Remaining limitations

- No runtime decoder or full disassembler.
- No JOP, COP, SROP, symbolic execution, or chain generation.
- Memory support is limited to exact qword base-plus-zero forms.
- PIE-versus-shared-object distinction and CET/IBT/SHSTK property evidence remain
  planned capability gates.
- Executable-segment overlap and extended-numbering behavior require explicit
  pre-freeze decisions.
- Generic semantic roles for all exact single-pop GPR forms remain a Sprint 13
  decision.

## Sprint 11 handoff

Sprint 11 begins with these rules:

1. build a high-resolution diagnostic runner before making performance claims;
2. preserve immutable tool and target identities for every row;
3. retain failed rows rather than dropping them;
4. define task equivalence separately for scanner, gadget-report, and integrated
   analysis conditions;
5. keep diagnostic evidence separate from the Sprint 15-frozen campaign;
6. use the gap register to prioritize Sprints 12 through 14;
7. preserve the dependency-free one-worker reference profile for every ablation.
