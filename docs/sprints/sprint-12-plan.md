# Sprint 12 Plan

## Status

Active at Patch 076. Patch 074 was a closeout candidate, but later review
required bounded corrections and the mitigation-gap review justified continuing
Sprint 12. Patch 075 introduced private bounded `DT_TEXTREL` / `DF_TEXTREL`
evidence. Patch 076 corrects its remaining transaction, oracle, recovery,
parity, and delivery findings and adds distinct bounded `DT_RPATH` and
`DT_RUNPATH` evidence. Sprint 13 remains planned, not active.

Patches 062 through 074 carry ordinary PHDR validity and explicit extended-
numbering outcomes, retained executable-overlap provenance, private PIE/DSO and
GNU-property evidence, authenticated natural and controlled strata, external
reconciliation, a corrected environment-parity protocol, a non-reinterpretive
public-policy deferral, and candidate evidence-custody corrections. Corrected
actual native/container parity and final closure remain pending. Public schema
`0.2.0` remains unchanged.

Related closeout records:

- [ADR 0048](../adr/0048-phdr-validity-and-extended-numbering-boundary.md)
- [ADR 0049](../adr/0049-executable-overlap-provenance-seam.md)
- [ADR 0050](../adr/0050-fact-first-binary-role-lattice.md)
- [ADR 0051](../adr/0051-bounded-private-gnu-property-evidence.md)
- [ADR 0052](../adr/0052-role-property-metamorphic-preflight.md)
- [ADR 0053](../adr/0053-corpus-custody-and-private-layout-attestation.md)
- [ADR 0054](../adr/0054-private-role-property-diagnostic-matrix.md)
- [ADR 0055](../adr/0055-authenticated-role-property-readelf-reconciliation.md)
- [ADR 0056](../adr/0056-whole-batch-transaction-and-external-evidence-custody.md)
- [ADR 0057](../adr/0057-identity-bound-cleanup-outcome-complete-batch-and-delivery-custody.md)
- [ADR 0058](../adr/0058-outcome-blind-external-natural-acquisition-and-environment-parity.md)
- [ADR 0059](../adr/0059-patch072-correction-and-non-reinterpretive-public-policy-deferral.md)
- [ADR 0060](../adr/0060-patch073-correction-and-sprint12-closeout.md)
- [Patch 074 validation](sprint-12-patch-074-validation.md)
- [ADR 0061](../adr/0061-private-dynamic-metadata-and-text-relocation-evidence.md)
- [Patch 075 validation](sprint-12-patch-075-validation.md)
- [ADR 0062](../adr/0062-distinct-private-rpath-runpath-evidence.md)
- [Patch 076 validation](sprint-12-patch-076-validation.md)

## Sprint goal

Resolve loader-identity, executable-region, and mitigation-evidence ambiguities
that would otherwise corrupt corpus labels or defensive triage.

## Completed deliverables

- [x] Validate `p_align`, offset/virtual congruence, virtual ranges, executable
  entrypoint containment, and structurally validated extended-numbering
  unsupported outcomes.
- [x] Preserve original executable-PHDR identity and dense per-candidate
  contributor provenance while retaining current scan, order, count, and
  capacity semantics.
- [x] Measure executable overlap and defer normalization under explicit reopening
  thresholds. No current target recovered capacity or changed an outcome.
- [x] Implement a private fact-first role lattice that keeps `ET_DYN` alone
  unknown and preserves executable-like, shared-object-like, ambiguous, and
  contradictory states.
- [x] Implement bounded private GNU-property IBT/SHSTK evidence with canonical
  physical views, original contributors, explicit unknown/absent/present/
  contradictory states, and malformed/cap fail-closed behavior.
- [x] Attest the C/NASM private fact-probe layout and retain separate natural and
  controlled metamorphic evidence strata.
- [x] Reconcile the authenticated 96-object matrix against exact GNU
  `readelf -hW/-lW/-dW/-nW` evidence with direct/derived/ambiguous/unavailable
  authority classes and separate eligibility denominators.
- [x] Add and harden the whole-batch transaction pilot without dividing batch
  time into synthetic per-invocation latency.
- [x] Freeze and reauthenticate a 48-object outcome-blind external-natural
  package stratum before and through analyzer, probe, and `readelf` outcomes.
- [x] Define corrected same-byte native/container private-fact parity with exact
  input and result custody, no native-plane exposure, retained planes, and
  explicit environment/build-origin separation.
- [x] Execute the public-policy gate as `defer`: add zero role/property fields,
  preserve the coarse `mitigations.pie` meaning, and make no runtime-CET claim.
- [x] Select text-relocation and separate RPATH/RUNPATH evidence as bounded
  future mitigation tranches without adding unvalidated runtime output.
- [x] Correct final custody, hardlink, late-subtree, selection-inode, parity
  membership/publication, tracked-permission, and negative-oracle defects in
  Patch 074.

## Active continuation deliverables

- [x] Reject untracked hardlink mutation and include final permission
  verification inside rollback.
- [x] Bind custody publication to one retained root descriptor, close rejected
  scans, and support exactly 511 payload files plus the custody manifest.
- [x] Reject alternate container mount syntax outside the reviewed parity
  grammar and reject duplicate JSON keys and Boolean-as-integer authority data.
- [x] Add a private 2,128-byte bounded dynamic-metadata side-car after the
  existing GNU-property context without changing earlier property offsets.
- [x] Retain exact `DT_TEXTREL` and `DT_FLAGS` carrier provenance and derive
  private unknown, absent, present, or contradictory text-relocation state.
- [x] Preserve public schema `0.2.0`, public mitigation output, program-header
  executable authority, candidate capacity, and no-partial-output behavior.
- [x] Harden the textrel oracle against path-value false positives, exact
  aggregate mutations, unconsumed schema authority, and stale public-field
  assumptions.
- [x] Bind permission normalization, custody publication, and candidate-source
  recovery to retained identities with complete rollback and derived tree
  verification.
- [x] Add distinct private `DT_RPATH` and `DT_RUNPATH` carrier/value records,
  exact byte provenance, separate states, a 64-record cap, and a 4,096-byte cap.
- [x] Add tracked native/container parity over all private dynamic fields and
  public command closures without exposing the native result plane.
- [ ] Complete fresh native, Docker, actual parity, and independent acceptance
  for Patch 076.


## Patch sequence

1. **Patch 062:** ordinary PHDR validity and explicit extended-numbering
   outcomes.
2. **Patch 063:** original executable-PHDR and candidate-contributor provenance.
3. **Patch 064:** measured overlap-normalization deferral and internal role
   evidence.
4. **Patch 065:** bounded private GNU-property evidence.
5. **Patch 066:** controlled 28-object role/property metamorphic preflight.
6. **Patch 067:** corpus custody and private fact-probe layout attestation.
7. **Patch 068:** 48-natural plus 48-metamorphic private-fact matrix.
8. **Patch 069:** authenticated field-scoped GNU `readelf` reconciliation.
9. **Patch 070:** first evidence-custody and whole-batch transaction candidate;
   review required correction.
10. **Patch 071:** first cleanup, batch authority, streaming-limit, and delivery
    correction.
11. **Patch 072:** remaining correction plus external-natural acquisition and
    initial parity protocol; review required correction.
12. **Patch 073:** policy deferral and first parity/custody correction; review
    required the final closeout correction.
13. **Patch 074:** final custody, parity, permission, authority, documentation,
    and a superseded Sprint 12 closeout candidate.
14. **Patch 075:** remaining P074 correction plus private bounded
    text-relocation carrier and state evidence.
15. **Patch 076:** remaining Patch 075 correction plus distinct bounded
    `DT_RPATH` and `DT_RUNPATH` carrier/value evidence and complete private
    dynamic-metadata parity.
16. **Patch 077 (planned):** reconcile Patch 076 acceptance evidence and decide
    Sprint 12 closeout without adding unreviewed mitigation fields.

## Current continuation disposition

```text
program-header executable authority: preserved
extended numbering:                  explicit malformed/unsupported behavior
overlap normalization:               deferred under measured threshold
private PIE/DSO lattice:             retained
private IBT/SHSTK facts:             retained; static only
public role/property fields:         deferred; zero added
schema version:                       0.2.0 unchanged
candidate capacity:                   4096 unchanged
reference runtime:                    dependency-free, decoder-free, one worker
external-natural evidence:            diagnostic and publication-ineligible
performance/coverage claims:          not authorized
```

## Handoff

After Patch 076 and the planned Patch 077 closeout reconciliation pass acceptance, Sprint 13 owns
generic exact-pop semantics, the Linux syscall `r10` role, release-facing
score/null policy, and only bounded family additions supported by measured task
value. Any changed task definition receives a new diagnostic campaign identity.
Sprint 14 remains the optional decoder/concurrency ablation stage, and Sprint 15
remains the confirmatory campaign freeze.
