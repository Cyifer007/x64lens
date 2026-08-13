# Publication Plan

## Candidate title

x64lens: An Assembly-First Semantic Gadget and Mitigation-Aware Analyzer for ELF64 x86_64 Binaries

## Paper shape

The initial target is an IEEE-style paper with a bounded systems-security contribution and a public replication package.

Planned sections:

1. Introduction.
2. Related work.
3. Design and implementation.
4. Safety and evidence model.
5. Evaluation methodology.
6. Results.
7. Defensive triage case study.
8. Discussion and threats to validity.
9. Future work.
10. Conclusion.

## Core contribution

The intended contribution is not simply that the implementation uses assembly. The contribution is an evaluated, dependency-light pipeline that separates:

- loader-relevant ELF facts,
- raw gadget candidate discovery,
- exact suffix evidence,
- semantic primitive coverage,
- candidate provenance,
- mitigation context,
- heuristic utility scores,
- reproducible measurement.

## Claim discipline

The paper may claim only what the preserved evidence supports.

Examples:

- Runtime and memory claims require fixed versions, commands, corpus hashes, repeated trials, raw rows, and generated statistics.
- Coverage claims require explicit gadget definitions and reconciliation with baseline tools.
- Parser robustness claims require hostile-input and regression evidence.
- Defensive usefulness claims require defined analyst tasks and a reproducible case study.
- The paper must not claim exploitability without an independent vulnerability and runtime context.

## Required artifacts

- public repository,
- release tag,
- source and Linux x86_64 artifacts,
- SHA-256 checksums,
- corpus manifest and build commands,
- baseline versions and exact commands,
- raw benchmark results,
- generated summaries, tables, and figures,
- JSON schema and validators,
- hostile-input regression evidence,
- case-study materials,
- reproduction instructions,
- IEEE source and bibliography,
- claim-to-evidence matrix.

## Milestones

| Sprint | Publication milestone |
|---|---|
| 7 | Deterministic hostile-input results, minimized parser regressions, explicit capacity behavior, and checked table-arithmetic foundation. |
| 8 | Mitigation accuracy fixtures and comparison evidence. |
| 9 | Complete: provenance model, schema `0.2.0`, completeness, decoder-gap evidence, and deployment-profile decision. |
| 11 | Diagnostic high-resolution runner, provisional corpus, task map, and engineering gap register. |
| 12-14 | Loader/mitigation precision, semantic capability completion, and optional profile ablations guided by diagnostic evidence. |
| 15 | Corpus, schema, runner, baseline, command, task-definition, and environment-stratum freeze. |
| 16 | Frozen pilot results and `v0.1.0-rc1` preview package. |
| 17 | Publication-grade comparative campaign and raw-result freeze. |
| 18-20 | Defensive triage, automation interfaces, and infrastructure case-study evidence. |
| 21 | Paper, figures, claim matrix, and independent replication freeze. |
| 22 | `v0.1.0` release and submission package. |


## Diagnostic versus confirmatory evaluation

Sprint 11 measurements are allowed to change the implementation and the eventual experimental design. They can identify bottlenecks, task mismatches, and material coverage gaps, but they are not final paper results. Sprint 15 freezes the confirmatory design. Only Sprint 16 and Sprint 17 rows may support preview and publication performance or coverage claims.

## Current robustness evidence

Patch 025 adds the first bounded robustness evidence surface: a deterministic 29-case malformed-input campaign, per-case signal and timeout capture, a minimized ELF64 section-entry-size regression, and an explicit candidate-capacity failure fixture. These are development and regression artifacts. They do not justify a formal memory-safety claim or a complete robustness result until the catalog, shared arithmetic layer, and later metadata parsers are evaluated.

## Reviewer-risk sections

The paper should address:

- why NASM is evaluated,
- parser safety without language-level memory safety,
- exact suffix versus decoded validity,
- evidence provenance,
- current `raw_only`, `exact_suffix`, and `semantic_exact` provenance separated
  from `unknown_candidate_count` and `scored_candidate_count`, with
  decoder-backed kinds treated as conditional,
- candidate truncation and completeness,
- baseline task and output differences,
- timing resolution and cache policy,
- corpus selection bias,
- x86_64 and ELF64 scope,
- future decoder and multi-architecture work.

## Evaluation split

Use separate evaluation questions:

1. **Engine cost:** raw or gadget-report runtime, CPU, RSS, and throughput.
2. **Coverage:** candidate and semantic differences under explicit definitions.
3. **Mitigation accuracy:** controlled fixture and external-tool agreement.
4. **Robustness:** malformed-input outcomes and regression coverage.
5. **Operational value:** analyst task performance or structured case-study interpretation.

Do not combine these into a single superiority claim.

## Release relationship

`v0.1.0-rc1` is a research preview suitable for faculty and external feedback. `v0.1.0` is the first research release intended to accompany the final replication and submission package.

See [`research-release-plan.md`](research-release-plan.md) and [`roadmap-22-sprints.md`](roadmap-22-sprints.md).

## Mitigation-oracle evidence

The implementation now has a compiler-independent mitigation truth table. Patch 030 expands it with bounded dynamic-table evidence for bind-now indicators and malformed dynamic-table rejection. Patch 031 adds no, partial, and full RELRO labels backed by that bounded evidence. Patch 032 adds canary-present and canary-absent indicator rows backed by bounded dynamic-string evidence. Patch 033 adds stripped and not-stripped rows backed by bounded section-header evidence and strict duplicate dynamic string-table singleton rejection. Patch 034 adds section-label annotations and a zero-length dynamic string-table endpoint oracle case. The paper may describe represented program-header, dynamic-table, and section-table combinations plus consistent malformed rejection as deterministic validation evidence. It must not generalize the matrix into full mitigation coverage, full stack-protector proof, complete symbol recovery, or memory-safety proof.

## Sprint 8 Patch 032 publication note

Canary reporting is a static indicator only. Any paper text must describe it as exact `__stack_chk_fail` evidence from a validated dynamic string table, not as proof that the binary or every function is protected by stack canaries.

## Sprint 8 Patch 034 publication note

Stripped reporting is a static section-table metadata indicator only. Any paper text must describe it as bounded `SHT_SYMTAB` evidence, not as proof of source availability, complete symbol recovery, or loader behavior.


## Sprint 9 Patch 040 publication note

Schema `0.2.0` now records which command produced the report and whether bounded
candidate enumeration completed over all loader-derived executable regions.
Publication text may describe this as explicit report identity and enumeration
completeness. It must not describe `analysis.complete` as decoder validation,
complete gadget coverage, exploitability, or memory-safety evidence.

Per-candidate evidence provenance and decoder-gap measurement remain required
before coverage claims are frozen.


## Sprint 9 Patch 041 publication note

The repository can now support a bounded claim that every current JSON candidate
identifies whether its semantic classification is based on raw, exact-suffix,
or semantic-exact evidence. It cannot yet claim full instruction-sequence
validity. `full_sequence_valid: null` is the required current representation.

Benchmark summaries must identify tool and schema versions as grouping keys.
This is evidence-integrity plumbing, not a comparative performance result.


## Sprint 9 Patch 042 publication note

Patch 042 adds a reproducible development campaign for comparing x64lens raw
terminators and exact suffixes with canonical GNU objdump boundaries. The paper
may use the retained artifacts to explain candidate-definition differences and
to justify the embedded-decoder decision. It must not present this smoke
campaign as publication-grade performance evidence, treat objdump as ground
truth for loader mappings, or label every boundary disagreement a false
positive without manual reconciliation.

The campaign records duplicate/canonicalization facts, supported suffixes not
selected by the one-record-per-terminator model, and unsupported canonical
return-ending sequences separately. These categories should remain separate in
future coverage tables rather than being collapsed into one gadget-count delta.

## Sprint 9 Patch 043 publication note

Patch 043 records a defensible negative architecture decision: the available
Sprint 9 evidence does not justify making a decoder mandatory in the default
runtime. The paper may describe this as a measured scope decision, not as proof
that decoding has no value.

The paper should evaluate the dependency-free core and any future optional
verification profile separately. It should report raw byte discovery,
canonical-boundary reconciliation, semantic coverage, runtime, RSS, dependency
surface, and threats to validity as distinct dimensions. Sprint 9 campaign
measurements remain development evidence until the fixed corpus and publication
methodology are frozen.

## Candidate-scoped decoder and parallelism claim discipline

The paper may describe candidate-scoped decoding and deterministic parallel
profiles as architecture or measured ablations only. It may not claim zero
false negatives from a small system sample, invisibility from anti-analysis, or
parallel speedup without fixed-corpus timing and RSS evidence. Defensive value
should be framed as low deployment friction, small dependency surface, bounded
resource use, and explicit provenance.

## Sprint 9 publication posture

Sprint 9 supports claims about explicit report identity, bounded analysis completeness, candidate provenance, and a reproducible external decoder-gap method. It does not support claims of complete decoded gadget coverage, universal false-positive elimination, superiority over baseline tools, or anti-analysis invisibility.

The paper should evaluate the dependency-free scanner as the reference profile and may later compare candidate-scoped decoder validation and deterministic parallel profiles as ablations. Runtime, CPU, max RSS, coverage, and output-definition differences must remain separate results.

## Sprint 10 Patch 048 publication note

The paper may describe Patch 048 as a compatible semantic-exact extension for positive aligned stack adjustment with explicit stack and condition-flag effects. It may not describe the family as full decoded validity, universal stack-adjust coverage, or evidence that x64lens is faster or lower-RSS than baseline tools.

Public replication archives must be evaluated as distributed bytes. Metadata-safe archives can still preserve prohibited text inside patch or diff members, so both archive metadata and bounded public-content gates are required.

## Sprint 10 Patch 049 publication note

The paper may describe Patch 049 as the first structured semantic-exact memory-effect family: qword base-plus-zero loads and stores with explicit direction, base, value register, width, dereference, clobber, and score state. It may not generalize this family to arbitrary memory operands, claim decoder validity, or infer address controllability.

Patch 051 increases the fixed command arena to 819,200 bytes by adding one 24-byte architectural-effect record for each of 4,096 candidate slots. This allocation arithmetic is not evidence of process RSS, speed, or superiority until measured under the publication methodology.


## Sprint 10 Patch 050 publication note

Patch 050 supports a bounded claim that every implemented Sprint 10 family has a maintained controlled-fixture, effect, fallback, false-positive, and score-disposition record. It does not support a claim of complete gadget-family coverage, decoder validity, or comparative superiority. Fixed arena size is an implementation fact; runtime and RSS claims still require the frozen benchmark methodology.

## Sprint 10 Patch 053 publication sequencing note

The benchmark system is designed and exercised before feature freeze because an
early null or negative result is useful engineering evidence. Those diagnostic
rows may redirect the implementation, but they are not publication results.

The publication dataset begins only after the Sprint 15 freeze. Preview and
publication claims use the frozen Sprint 16 and Sprint 17 campaigns, not earlier
smoke or diagnostic rows.

## Sprint 10 Patch 054 publication note

Patch 054 closes Sprint 10 and begins the diagnostic measurement stage. The paper may describe Sprint 10 as completing the current bounded primitive, effect, provenance, fixture, false-positive, and score-policy foundations. It must not treat Sprint 11 diagnostic rows as publication evidence or imply that the corpus and method are frozen before Sprint 15.

## Sprint 11 Patch 061 publication note

Sprint 11 closes with two distinct diagnostic evidence strata. The earlier
authenticated cloud checkpoint accounted for 30 conditions but executed only
the 12 x64lens conditions because 18 baseline conditions were unavailable. A
later WSL2 all-tools replay, qualified only for an evidence-local correction to
the official ROPgadget 7.7 banner, executed 30/30 conditions and retained
180/180 successful process rows. All 12 x64lens conditions were below the
6,361,100 ns reliable floor. The replay produced 24 normalized relations, but
two Python task-path closures failed and coordinate calibration failed, so it
was not comparison-qualified and does not replace the fresh, unmodified Patch
061 campaign required for empirical acceptance.

Neither stratum is frozen or publication-eligible. The paper must not report
below-floor x64lens observations as zero or as a speed result, collapse
tool-native populations into a generic cross-tool gadget count, or treat native
execution, normalization, runtime closure, coordinate qualification, and
comparison status as interchangeable.

## Sprint 12 Patch 062 publication boundary

The paper may describe deterministic ordinary-PHDR validity and explicit extended-numbering unsupported outcomes for the reviewed fixtures. It may not claim complete ELF extended-numbering support, complete loader correctness, PIE-versus-DSO precision, CET evidence, or universal parser safety from this patch.

## Sprint 12 Patch 074 through Patch 082 publication boundary

Patch 074 was a superseded Sprint 12 closeout candidate. Patch 075 introduced
bounded private static text-relocation evidence, but its review required the
Patch 076 correction. Patch 076 implements distinct bounded private RPATH and
RUNPATH evidence. None of these candidate dispositions becomes accepted
authority before the active native, container, delivery, and independent
acceptance gates complete on the same source. Patch 076's review required the
Patch 077 correction. Patch 077 was superseded by Patch 078, whose review
required the Patch 079 corrective and private task-value candidate, whose review
required Patch 080; Patch 080 was superseded by Patch 081, which was not
accepted. Independent exact-source Patch 085 acceptance remains pending. Sprint
13 remains an entry candidate and activates
only after complete Patch 085 acceptance.

The Patch 073 diagnostic campaign had every x64lens row below the timer floor
and zero positive coordinate anchors. It remains diagnostic, unfrozen, and
publication-ineligible and supports no speed, RSS, superiority, parity, or
normalized-coverage claim. Patch 076 does not authorize a public PIE/DSO, IBT,
SHSTK, runtime-CET, text-relocation, RPATH/RUNPATH, performance, RSS, normalized
coverage, or prevalence claim. Patch 075 text-relocation evidence and Patch 076
RPATH/RUNPATH evidence remain private static facts, not runtime or loader-policy
conclusions. All Sprint 11-12 measurements remain outside the Sprint 15-frozen
confirmatory campaign.


## Patch 076 publication note

The paper may describe separate bounded acquisition of exact `DT_RPATH` and
`DT_RUNPATH` carrier/value evidence for the reviewed fixture domain. It must not
claim loader path selection, `$ORIGIN` resolution, filesystem exposure,
misconfiguration, vulnerability, or exploitability from static carrier bytes.
The private matrix remains development evidence and adds no public schema field.

## Sprint 12 Patch 077 publication note

Patch 077 supports a bounded engineering claim that the private dynamic-metadata evidence and its supporting transactions have explicit failure, custody, comparator, and parity contracts. It does not support mitigation-prevalence, runtime loader, performance, exploitability, or publication-grade coverage claims.

## Sprint 13 Patch 078 publication note

Patch 078 supports a bounded engineering claim that all 16 exact single-pop
patterns are accounted for by distinct private role facets and that the
supporting source/delivery transactions have adversarial regression coverage.
It does not support a public role field, score change, semantic-coverage,
task-value, performance, exploitability, or publication-grade claim.
Patch 079 used deterministic presentation order as non-causal display metadata
before any runtime-semantic, public-field, or score projection.

## Historical Sprint 13 Patch 079 publication boundary

The Patch 079 role-task result was diagnostic and publication-ineligible. The
paper may later describe the preregistered method and the distinction between
System V `rcx` argument 4 and Linux syscall `r10` argument 4, but it may not
claim analyst benefit, coverage superiority, public semantic support, or score
validity from this candidate alone. Any release-facing task claim requires the
frozen campaign and preserved raw task evidence.

## Sprint 13 Patch 080 publication boundary

Patch 080 supports a bounded engineering claim that three contextual register
role facets are represented in a private side-car after a corrected diagnostic
task gate. It does not support a public-role, score, performance, coverage,
analyst-utility, or exploitability claim. The task rows remain diagnostic and
publication-ineligible.

## Patch 081 publication note

The test-only ordered two-pop manifest may be reported as a policy deferral. It
declares existing and proposed correctness with zero incremental gains, while
the smoke validates structure and declarations without executing an independent
task consumer. It is not confirmatory measured task-value or publication-grade
comparative evidence and supports no performance, coverage, or exploitability
claim.

## Patch 082 publication boundary

Patch 082's artifact-backed implementation and later exact-source execution
support a bounded statement that three producer builds checked the retained
ordered-pair and score/null facts. This is gate-execution accounting, not
publication evidence. The separate P082 diagnostic campaign had 0/60 x64lens
timing rows above its floor and 0/9 positive natural coordinate cells; it remains
unfrozen, publication-ineligible, and non-comparative. The controlled coordinate
preflight may be described only as method discrimination over six generated
targets, nine tool-label-by-role cells, and 18 modeled observations. The named
tools are not executed natural baselines. Neither artifact is publication-grade
comparative evidence. Natural baseline runs, frozen commands, target identities,
and the Sprint 15 campaign authority remain required before coverage
interpretation.


## Patch 083 publication boundary

Natural coordinate results may document whether address-coordinate calibration
is available for the selected installed-package stratum. They are not a coverage
comparison, prevalence estimate, or performance result and cannot be merged into
the Sprint 15-frozen campaign.

## Patch 084 publication boundary

Patch 084 adds no publication claim. The retained natural campaign is complete
for its diagnostic denominator but has zero qualified cells; five cells are
insufficient and four are unavailable. It cannot support comparative coverage,
performance, parity, prevalence, or superiority claims. The ABI-role query and
lifecycle authorities are private engineering evidence and are not paper result
tables.

## Patch 085 publication boundary

Patch 085 adds no publication result. It defines frozen-input replay and layered
terminal-attribution authorities over the unchanged 12-target, 48-execution,
nine-cell, 108-control predecessor denominator. The predecessor remains zero
qualified, five insufficient, and four unavailable cells. Actual replay remains
pending; any replay evidence is diagnostic, `frozen=false`, and publication-
ineligible. No comparative coverage, performance, RSS, parity, prevalence,
superiority, exploitability, public-role, decoder, or concurrency claim follows.
