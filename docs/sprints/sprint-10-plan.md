# Sprint 10 Plan

## Status

Active through the Patch 053 architecture and capability reassessment candidate. Patches 046 through 052 established and hardened ordered multi-pop, exact register-transfer, exact positive aligned stack-adjust, bounded qword base-plus-zero memory families, current-family effects, architectural effects, score policy, and fail-closed validation. Patch 053 corrects the remaining Patch 052 harness and planning defects, separates diagnostic measurement from the frozen campaign, and expands the canonical roadmap to twenty-two sprints. Patch 054 remains the Sprint 10 closeout.

Related documentation:

- [ADR 0032](../adr/0032-ordered-multi-pop-foundation.md)
- [ADR 0033](../adr/0033-exact-register-transfer-effects.md)
- [ADR 0034](../adr/0034-bounded-stack-adjust-and-public-artifact-content-policy.md)
- [ADR 0035](../adr/0035-bounded-memory-effect-sidecar-and-authenticated-public-overlay.md)
- [ADR 0036](../adr/0036-sprint10-effect-completion-and-fixture-gate-hardening.md)
- [ADR 0037](../adr/0037-architectural-effects-and-contract-reconciliation.md)
- [ADR 0038](../adr/0038-patch051-corrective-effect-and-gate-hardening.md)
- [ADR 0039](../adr/0039-benchmark-informed-capability-roadmap.md)
- [Benchmark and Capability Stage Gates](../design/benchmark-and-capability-stage-gates.md)
- [Primitive Effect Model](../design/primitive-effect-model.md)
- [Family Coverage Table](../design/sprint10-family-coverage.md)
- [Exact-Pattern Catalog](../design/sprint10-exact-pattern-catalog.md)
- [Scoring Model](../scoring-model.md)
- [Output Contract](../contracts/output-contract.md)
- [Patch 051 Validation Plan](sprint-10-patch-051-validation.md)
- [Patch 052 Validation Plan](sprint-10-patch-052-validation.md)
- [Patch 053 Validation Plan](sprint-10-patch-053-validation.md)
- [Canonical Roadmap](../roadmap-22-sprints.md)

## Sprint goal

Expand semantic primitive coverage without collapsing suffix evidence, decoded
validity, side effects, score meaning, or the defensive deployment profile.

## Planned deliverables

- [x] Add selected ordered multi-pop patterns with controlled-register facts.
- [x] Add a conservative register-transfer family with explicit source,
  destination, and destination clobber.
- [x] Add narrowly scoped memory-read and memory-write patterns with structured
  base, value, width, displacement, dereference, and direction facts.
- [x] Populate controlled and clobbered register facts for all implemented
  families.
- [x] Complete current-family side-effect modeling. Patch 050 records the return
  stack read for every supported return-ending semantic candidate, syscall
  clobbers for `rcx`/`r11`, and the `rbp` overwrite caused by `leave`.
- [x] Preserve known/unknown stack-delta representation.
- [x] Add controlled source fixtures and disassembly oracles for every Sprint 10
  family.
- [x] Add a machine-readable fixture coverage table and per-family
  false-positive boundaries.
- [x] Add score entries only after semantic/effect validation. Patch 051 adds reviewed scores for ordered two-pop argument control and positive aligned stack adjustment; transfer and memory families remain explicitly unscored.
- [x] Preserve candidate-index provenance and schema `0.2.x` compatibility.

## Patch sequence

1. **Patch 046:** ordered two-pop foundation and compatible effect fields.
2. **Patch 047:** exact register-direct transfers and stronger relational
   validation.
3. **Patch 048:** exact positive aligned stack adjustment plus JSON/public
   artifact corrections.
4. **Patch 049:** fixed memory-effect side-car and bounded qword base-plus-zero
   memory reads/writes.
5. **Patch 050:** current-family effect completion, cross-family fixture
   reconciliation, fail-fast recipe hardening, fixture coverage table, and
   explicit score deferral.
6. **Patch 051:** reconcile the committed Patch 050 foundation through one architectural-effect, score, exact-pattern, semantic-family, and fixture-suite contract.
7. **Patch 052:** resolve Patch 051 findings.
8. **Patch 053:** correct the Patch 052 harness/planning findings and establish the benchmark-informed capability roadmap, diagnostic/frozen evidence split, release gates, and twenty-two-sprint sequence.
9. **Patch 054:** Sprint 10 closeout or the smallest correction proved necessary by Patch 053 validation.

This sequence prevents the capability audit from being hidden inside a nominal
closeout patch and prevents Sprint 11 corpus work from freezing ambiguous facts.

## Entry criteria from Sprint 9

- Schema `0.2.0` identity, completeness, and provenance gates pass.
- `gadgets` and `analyze` remain command-only parity matches.
- Capacity and malformed-input paths remain fail-closed with no partial output.
- The decoder-free one-worker core remains the reference profile.
- External disassembly remains comparator evidence, not runtime authority.

## Acceptance criteria

- [x] Every implemented semantic family has a controlled fixture or explicit
  base-fixture coverage.
- [x] Ambiguous forms retain a conservative fallback rather than unsupported
  promotion.
- [x] Exact suffix recognition and semantic promotion remain separate.
- [x] Controlled, clobbered, stack, register, flag, syscall, and memory effects
  are visible in records, text, and JSON for implemented families.
- [x] Score changes are documented and tested independently from classification. Ordered two-pop and stack-adjust scores require validated architectural effects; transfer and memory remain unscored.
- [x] New metrics preserve provenance and schema `0.2.x` compatibility.
- [x] No new mandatory runtime dependency is introduced.
- [x] One-worker output remains deterministic and bounded.

## Reference storage profile

```text
gadget_record:                    112 bytes
candidate_evidence_record:         48 bytes
memory_effect_record:              16 bytes
candidate_effect_record:           24 bytes
candidate capacity:              4096
combined analysis arena:       819200 bytes
```

These are fixed allocation and capacity facts, not measured comparative RSS or
performance results.

## Decoder and parallelism boundary

Sprint 10 does not make a decoder mandatory and does not add a parallel default.
A future decoder should validate retained candidate starts and write additive
side-car evidence. Target-level concurrency and candidate-validation workers remain optional measured profiles for Sprint 14 after Sprint 11 diagnostic evidence and Sprint 12-13 capability hardening. No acceleration profile may
change candidate order, capacity semantics, evidence layers, or score facts.

## Out of scope

- JOP, COP, or SROP coverage.
- Symbolic execution or exploit-chain generation.
- Unbounded pattern enumeration.
- Whole-image decoder integration.
- Default in-process multithreading.
- Displacement/SIB/RIP-relative memory coverage before the operand model and
  fixtures justify it.

## Handoff

Patch 052 corrects the Patch 051 effect encoding, ret-imm16 lower boundary, text separator, memory-sidecar reconciliation, score-policy gate, and strict-lint availability findings. Patch 053 corrects the remaining internal-harness and planning defects and records the expanded roadmap. Sprint 11 begins diagnostic measurement with a provisional corpus; Sprint 15—not Sprint 11—freezes the release campaign after loader, mitigation, semantic, decoder, and concurrency decisions are complete.

## Patch 046 boundary

Patch 046 recognizes two distinct System V argument-register pops before `ret`.
Unsupported or duplicate pairs fall back to the strongest existing single-pop
suffix. Ordered metadata reuses reserved bytes in the 112-byte candidate record.

## Patch 047 boundary

Patch 047 recognizes distinct non-`rsp` 64-bit register-direct moves ending in
`ret`. It records source, destination, destination clobber, known return delta,
and register-write effects without inferring source control.

## Patch 048 boundary

Patch 048 recognizes only `48 83 c4 imm8 c3` with a positive nonzero
8-byte-aligned immediate. It records total stack delta, stack adjustment, and
flag writes while leaving the family unscored.

## Patch 049 boundary

Patch 049 recognizes only exact qword `REX.W + 89/8b + ModRM.mod=00 + ret`
forms with one represented non-special base, no SIB/index, no displacement, and
no `rsp` value role. A 16-byte candidate-index memory side-car records direction,
base, value register, width, dereference, and known zero displacement.

## Patch 050 boundary

Patch 050 adds no primitive family. It completes implicit and architectural
effects already present in supported suffixes, fixes transfer-fixture
cross-family promotion counts, prevents Make recipes from masking failed
validators, isolates stale-manifest verification, and establishes the maintained
family coverage/false-positive table. New-family score calibration remained
open for the subsequent Patch 051 decision.

## Patch 051 boundary

Patch 051 adds no primitive family. It reconciles the completed coarse family model,
a dense 24-byte architectural-effect side-car, centralized fail-fast fixture
orchestration, one-per-pattern coverage, and selective score calibration into
one contract against the committed Patch 050 base.

The three maintained views are complementary:

```text
11 semantic-family contracts
25 exact-pattern contracts
5 fixture-suite groups
```

A reconciliation gate requires them to agree. Patch 052 resolves Patch 051
findings; Patch 053 performs the broader capability reassessment; Patch 054
closes Sprint 10.


## Patch 052 boundary

Patch 052 adds no primitive family. It corrects full-width syscall effect
encoding, accepts the valid zero-immediate return boundary, restores contracted
text separators, requires exact memory side-car reconciliation, and promotes
score and strict-lint availability into permanent negative gates. Patch 053 performs the planned architecture/capability reassessment and benchmark sequencing decision; Patch 054 closes the sprint.


## Patch 053 boundary

Patch 053 adds no primitive, record, schema, capacity, decoder, or worker change. It corrects the Patch 052 memory-harness size symbol, applies the accepted public documentation corrections, adds manifest-relative checksum verification, introduces machine-readable research stage gates, and replaces the canonical eighteen-sprint plan with a twenty-two-sprint roadmap.

The research decision is to measure early but freeze late: Sprint 11 diagnostic evidence may redirect development; Sprints 12 through 14 close capability questions; Sprint 15 freezes the confirmatory campaign; Sprint 16 runs the preview pilot; Sprint 17 runs publication-grade comparisons.
