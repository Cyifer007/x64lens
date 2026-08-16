# Sprint 12 Retrospective: Loader and Mitigation Precision

## Retrospective status

Sprint 12 completed the semester's loader-precision and mitigation-evidence
engineering program. The implementation work spans Patches 062 through 077,
with later Sprint 13 corrective patches carrying forward acceptance and delivery
hardening identified during exact-source validation.

This retrospective records what was designed, implemented, tested, learned, and
deferred. It is a technical completion record for the sprint's engineering
scope. It does not replace exact-source native, Docker, parity, or independent
acceptance for a later corrective candidate.

## Sprint goal

The sprint began with one central question:

> Which loader, mapping, and mitigation facts must become precise before x64lens
> can safely freeze corpus labels, expand semantic interpretation, or make
> release-facing claims?

The answer required more than adding labels. The project had to preserve a
loader-correct view of ELF64 files, distinguish evidence from interpretation,
retain unknown and contradictory states, and prove that the same bounded facts
survive native and container workflows without leaking private state into the
public schema.

## Starting point

At Sprint 12 entry, x64lens already had:

- read-only file mapping;
- ELF64 x86_64 validation;
- program-header-derived executable regions;
- bounded raw candidate discovery;
- exact suffix recognition;
- conservative semantic classes;
- candidate provenance and effect side-cars;
- heuristic scoring;
- schema `0.2.0` JSON output; and
- a diagnostic benchmark foundation.

The unresolved loader and mitigation risks were significant:

- ordinary program-header edge cases needed stricter validation;
- ELF extended numbering needed an explicit bounded outcome;
- overlapping executable segments could duplicate work or obscure provenance;
- `ET_DYN` alone could not distinguish a PIE executable from a shared object;
- x86 IBT and SHSTK property evidence needed bounded note parsing;
- native and container private facts needed a trustworthy parity protocol;
- public projection needed a separate policy gate; and
- diagnostic evidence custody needed to be strong enough to support later
  research and release decisions.

## What Sprint 12 implemented

### 1. Program-header validity and extended numbering

Patch 062 strengthened the loader preconditions around:

- `p_align` validity;
- file-offset and virtual-address congruence;
- checked virtual ranges;
- executable entrypoint containment; and
- structurally validated ELF extended-numbering cases.

Extended numbering was not guessed or silently ignored. Structurally valid but
unsupported cases receive a stable unsupported outcome, while malformed cases
retain the malformed-input failure class. This preserved the distinction among
negative evidence, unsupported input, malformed input, and successful analysis.

### 2. Executable-region provenance and overlap policy

Patch 063 retained original program-header identity and added dense
candidate-to-contributor provenance. A candidate can therefore preserve which
executable program-header views contributed to its scan region without changing
public candidate counts or scan ordering.

Patch 064 then measured overlap incidence before changing behavior. The measured
sample did not justify executable-byte-union normalization, so normalization was
deferred under explicit reopening thresholds. This was an important negative
decision: x64lens did not change count meaning merely because normalization
looked architecturally elegant.

### 3. Private PIE-versus-DSO role evidence

The sprint introduced a fact-first private role lattice rather than
reinterpreting the existing public `mitigations.pie` Boolean.

The private lattice preserves:

- unknown;
- executable-like;
- shared-object-like;
- ambiguous; and
- contradictory states.

`ET_DYN` remains insufficient by itself. The role model consumes bounded ELF and
loader facts while staying outside the public schema. This avoids forcing a
binary into a false PIE-or-DSO dichotomy when the available evidence cannot
support one.

### 4. Bounded GNU-property evidence

The sprint added private bounded parsing for x86 GNU-property evidence relevant
to IBT and SHSTK. The implementation retains:

- canonical physical carrier views;
- original contributor provenance;
- bounded note and property iteration;
- explicit unknown, absent, present, and contradictory states; and
- malformed and capacity failures.

Static property evidence is not represented as runtime CET enforcement. That
boundary remains explicit in code, tests, documentation, and the public-policy
decision.

### 5. Private layout and fact-probe attestation

Because private facts cross an assembly/C validation boundary, the sprint added
C/NASM layout reconciliation. Assembly emits a layout authority; independent C
code checks each represented offset and size before interpreting private records.

This reduced a subtle evidence risk: a probe can appear to agree while reading
the wrong bytes if two sides silently disagree about structure layout.

### 6. Controlled and natural evidence strata

The sprint separated controlled metamorphic objects from held-out natural
objects. The maintained diagnostic plane uses:

- 48 natural objects;
- 48 controlled metamorphic objects;
- 288 private fact-probe executions;
- 384 public command executions; and
- explicit expected, observed, ambiguous, unavailable, malformed, unsupported,
  and inapplicable states.

The natural and metamorphic strata answer different questions. Controlled
objects test discriminating behavior; natural objects test whether the model
survives realistic ELF diversity. They are never pooled into an unlabeled
accuracy count.

### 7. Authenticated GNU `readelf` reconciliation

Patch 069 added field-scoped reconciliation against authenticated GNU
`readelf -hW`, `-lW`, `-dW`, and `-nW` evidence.

The comparator preserves:

- direct and derived authority classes;
- eligible match and mismatch denominators;
- ambiguous cells;
- unavailable cells; and
- fields that are not eligible for comparison.

The maintained 96-object reconciliation records 1,728 field dispositions, 1,224
eligible matches, and zero eligible unexplained mismatches in the retained
checkpoint. This is diagnostic evidence for the represented field model, not a
claim that GNU `readelf` becomes x64lens runtime authority.

### 8. Outcome-blind external-natural acquisition

The later Sprint 12 sequence froze an external-natural object stratum before
x64lens outcomes were inspected. Selection authenticated package lineage, path,
mode, ELF eligibility, target identity, analyzer identity, probe identity,
schema identity, and GNU `readelf` identity.

The retained acquisition contains 48 objects across four source lineages, 144
private probe processes, 192 public analyzer commands, 192 GNU `readelf`
processes, and 864 field dispositions. Ambiguous and unavailable facts remain
outside the eligible agreement denominator.

This protects the study from choosing favorable objects after seeing the
result.

### 9. Native/container parity protocol

Sprint 12 defined a corrected parity protocol over the same authenticated bytes.
The protocol requires:

- separately built native and container analyzers and probes;
- read-only authenticated source and target inputs;
- one dedicated empty writable result root;
- no live-repository mount;
- no completed native-plane mount into the container;
- retained native, container, and comparison planes; and
- explicit private-field and public-command denominators.

Same-host logic rehearsals validated the comparison machinery. Actual
native/container acceptance remains an environment-specific gate and must not be
inferred from a logic-only rehearsal.

### 10. Public-policy deferral

The non-reinterpretive public-policy gate evaluated whether the private role,
IBT, and SHSTK facts were ready for schema `0.2.x` projection.

The decision was **defer**:

- zero public role/property fields were added;
- the existing coarse PIE indicator retained its meaning;
- no runtime-CET claim was introduced; and
- private evidence remained private.

Deferral was a successful outcome because the gate prevented weak evidence from
becoming a stable automation contract.

### 11. Private text-relocation evidence

Patch 075 introduced a separate bounded dynamic-metadata side-car for static
text-relocation evidence. It records exact `DT_TEXTREL`, `DT_FLAGS`, and
`DF_TEXTREL` carrier provenance and derives private:

- unknown;
- absent;
- present; and
- contradictory states.

Carrier 65 fails with exit code 6 before public report emission. No public
mitigation field or schema change was added.

### 12. Distinct RPATH and RUNPATH evidence

Patch 076 extended the private dynamic side-car with separate `DT_RPATH` and
`DT_RUNPATH` carrier/value facts. The model preserves:

- distinct carrier identities;
- exact dynamic-entry and string provenance;
- a 64-record limit;
- a 4,096-byte retained-value limit;
- duplicate equality and conflict state; and
- unknown, absent, present, and contradictory states.

The parser does not split colon-separated paths, expand `$ORIGIN`, emulate the
loader, inspect referenced paths, or collapse RPATH and RUNPATH into one security
verdict.

### 13. Transaction, cleanup, and delivery hardening

Acceptance validation repeatedly exposed a broader engineering lesson: correct
analysis facts are not sufficient when the application, evidence, cleanup, and
delivery paths can mutate or misidentify bytes.

The Sprint 12 correction sequence therefore added or hardened:

- pinned patch bytes across dry-run and mutation;
- exact base and candidate tree authorities;
- no-replace publication;
- descriptor-bound source recovery;
- identity-bound cleanup;
- foreign-replacement preservation;
- bounded streaming child output;
- process-group and adopted-descendant cleanup;
- complete case-specific batch outcomes;
- recursive delivery membership, mode, size, and hash custody;
- exact candidate-source recovery under different umasks;
- tracked-only permission normalization with rollback; and
- Git-less Docker source construction from authenticated Git objects.

These changes are reusable infrastructure for later benchmark, release, and
replication work.

## What the sprint deliberately did not do

Sprint 12 did not:

- make section headers executable mapping authority;
- normalize overlapping executable ranges without measured activation;
- expose private PIE/DSO, IBT, SHSTK, textrel, RPATH, or RUNPATH fields publicly;
- infer runtime CET enforcement from static notes;
- open target-derived paths;
- introduce a mandatory decoder;
- introduce default concurrency;
- add JOP, COP, SROP, exploit generation, or chain synthesis;
- change the 4,096-candidate capacity; or
- weaken malformed-input no-partial-output behavior.

## Validation outcomes

The Sprint 12 development surface now includes deterministic controls for:

- ordinary and malformed PHDR cases;
- extended-numbering unsupported cases;
- overlap provenance;
- private role/property fixtures;
- GNU-property note carriers and conflicts;
- private ABI layouts;
- natural and metamorphic matrices;
- GNU `readelf` reconciliation;
- textrel and search-path matrices;
- exact capacity boundaries;
- malformed-input no-partial-output behavior;
- batch failures, timeouts, output limits, and signals;
- source and delivery custody; and
- native/container parity topology.

The diagnostic campaigns also preserved a critical limitation: all selected
x64lens single-process timing rows remained below their measured reliable timer
floor, and no positive coordinate anchor was established. The sprint therefore
supports no speed, RSS-superiority, generic coverage, or publication claim.

## What went well

### Architecture held under pressure

The project retained program-header executable authority and did not let
mitigation work leak into scanning, classification, scoring, or reporting.
Private side-cars allowed new facts to be evaluated without destabilizing public
schema `0.2.0`.

### Unknown and contradictory states stayed first-class

The role, GNU-property, textrel, RPATH, and RUNPATH models all preserve lack of
evidence and conflicting evidence instead of coercing those states into false
booleans.

### Negative decisions were recorded

Overlap normalization and public role/property projection were both deferred
because the evidence gate did not justify them. These decisions reduced scope
and protected metric and schema meaning.

### Review findings became durable regression tests

The correction sequence did not only patch individual symptoms. It promoted
cleanup races, path substitution, duplicate JSON keys, output-cap behavior,
manifest incompleteness, nonzero comparator exits, mount isolation, and recovery
semantics into reusable adversarial tests.

## What could be improved

### Acceptance scope grew too long

The sprint accumulated many corrective patches because evidence and delivery
infrastructure received increasingly adversarial review late in the sequence.
Future sprints should freeze the transaction and custody threat model earlier,
then reuse one accepted package/recovery framework.

### Product and evidence acceptance were too tightly coupled

Runtime facts, benchmark orchestration, package application, Docker provenance,
and loose-delivery custody sometimes failed in the same aggregate. Future
validation should continue separating product, source-state, Docker, toolchain,
evidence, and delivery strata so one class does not obscure another.

### Some gates initially tested summaries rather than discriminating behavior

Several early authorities passed nominal data but did not reject weakened or
mutated inputs. The corrected approach is to require independent negative
oracles and deliberate mutation of every policy cell.

### Documentation chronology required repeated reconciliation

The long corrective sequence made stale “current patch” language easy to leave
behind. The repository now treats final-file Markdown overlays and chronology
checks as first-class validation, but future status pages should minimize
patch-specific duplication.

## Technical lessons learned

1. **The loader maps segments, not sections.** Section metadata improves analyst
   readability but cannot replace program-header mapping authority.
2. **A file being fully mapped does not mean every format structure should be
   eagerly interpreted.** Bounded views should be added only for named facts and
   threat models.
3. **`ET_DYN` is a fact, not a complete role label.** PIE-versus-DSO
   interpretation requires multiple bounded observations and explicit unknowns.
4. **Static GNU properties are not runtime enforcement.** IBT/SHSTK note
   evidence must remain separate from operating-system and processor state.
5. **Exact carrier provenance matters.** A mitigation label without the source
   entry, offset, range, and conflict state is difficult to audit.
6. **Capacity is part of correctness.** A bounded analyzer must fail before
   output when it cannot produce a complete report.
7. **Evidence custody is part of research correctness.** Correct code cannot
   support a claim if the source, target, tool, output, or comparison bytes are
   not authenticated.
8. **Native/container equality requires independent builds and isolated result
   planes.** Reusing host-built binaries or exposing one plane to the other
   weakens the experiment.
9. **A deferred field is better than a misleading stable field.** Public schema
   contracts should follow evidence, not roadmap pressure.
10. **Negative experiments reduce future complexity.** The sprint's deferrals
    prevented unnecessary normalization, public projection, loader emulation,
    decoding, and concurrency work.

## Contract review

Sprint 12 preserved the public CLI and schema contracts:

```text
tool version:             0.1.0-dev
schema version:           0.2.0
candidate capacity:       4096
candidate 4097:           exit 6 before stdout
malformed parser failure: no partial stdout
executable authority:     file-backed PT_LOAD + PF_X
reference profile:        dependency-free, decoder-free, one worker
```

No contract was changed merely to make a test pass. The main contract growth was
internal: stronger source, transaction, evidence, parity, and delivery custody.

## Sprint 13 handoff

Sprint 13 inherits:

- a precise loader and mitigation fact foundation;
- private single-pop role facets;
- distinct System V and Linux syscall argument mappings;
- score/null governance that remains separate from task correctness;
- an accepted need for bounded, evidence-selected semantic work; and
- explicit deferrals for public projection, overlap normalization, FORTIFY
  joins, decoding, and concurrency.

System V argument 4 remains `rcx`; Linux syscall argument 4 remains `r10`.
Private role qualification does not automatically authorize a new semantic
class, public field, or score.

Patch 081 records the retrospective and executes a test-only ordered two-pop
role-tuple authority plus a complete score/null mutation authority. The tuple
manifest declares zero incremental gains, and its static checker therefore
records a policy deferral for redundant runtime state. It does not execute an
independent task consumer or provide confirmatory measured task-value evidence.

Patch 081 was not accepted. Its validation findings became correction inputs to
Patch 082, which implemented a producer-backed gate and a controlled coordinate
method-discrimination preflight. Patch 082 was also not accepted. A later
exact-source P082 run completed the three-build gate and a separate diagnostic
campaign, but that campaign's x64lens timings were 0/60 above floor and its
natural cells were 0/9 positive. P083 therefore requires a distinct producer
run and 12-target natural campaign; the P082 observations remain diagnostic,
unfrozen, publication-ineligible, and non-comparative.

## Final assessment

Sprint 12 substantially improved x64lens as both a binary-analysis tool and a
research artifact. The most important outcome was not the number of mitigation
labels added. It was the creation of a disciplined evidence path from hostile
ELF bytes, through bounded loader facts and private side-cars, to controlled
comparators, parity experiments, public-policy deferral, and authenticated
delivery.

The sprint leaves x64lens better prepared for Sprint 13 semantic completion and
the later Sprint 15 campaign freeze. Remaining corrective acceptance work can
continue without erasing the completed semester contribution or weakening the
architecture established here.

## Post-retrospective Patch 084 acceptance update

The semester engineering record remains complete. Patch 084 carries exact-source
acceptance debt forward without revising the completed Sprint 12 technical work.
It preserves the complete P083 natural campaign as diagnostic terminal evidence
with zero qualified, five insufficient, and four unavailable cells; corrects the
transaction, recovery, Docker, authority, and delivery findings; and freezes a
private ABI-role query contract. Fresh native, Docker, parity, producer, strict
ShellCheck, delivery, and independent acceptance remain separate from the
retrospective’s semester-completion claim.

## Post-retrospective Patch 085 acceptance update

The completed semester engineering record remains unchanged. Patch 085 carries
forward the remaining exact-source acceptance debt from the Patch 084 review.
It defines a frozen-input, no-reroll authority over the same twelve natural
target hashes and 48 execution slots, plus layered terminal-attribution
denominators without favorable reinterpretation, and strengthens Git-less
source, recovery, lifecycle, ABI-query, and delivery authorities. Actual replay
and generated attribution evidence remain pending. Fresh native, Docker, replay,
parity, producer, strict
ShellCheck, delivery, and independent acceptance remain separate from the
retrospective's semester-completion claim.

## Historical post-semester Patch 086 acceptance continuation

Patch 086 carried the remaining Patch 085 replay, evidence-custody, transaction,
recovery, ABI expected-result, exact-tree, and delivery corrections into Sprint
13. Replay-v2 defines sealing and mandatory terminal attribution but does not
claim that local replay completed. The private ABI-vector equivalence record
does not authorize public role projection. A separate private Patch 085
diagnostic campaign completed 30/30 conditions and 180/180 rows, but all 60
x64lens rows were below the 5,515,395 ns floor and 0/9 coordinate cells were
positive; it remains unfrozen and comparison-unqualified. Patch 086 did not
complete exact-source acceptance. This does not change the Sprint 12 semester
engineering scope or retroactively claim acceptance.

## Post-semester Patch 087 acceptance continuation

Patch 087 correction and paired workload/phase-attribution authority candidate
carries forward the Patch 086 review findings and current exact-source
acceptance debt without changing the completed Sprint 12 semester engineering
record. It rejects
hard-linked patch state, removes package-wrapper post-helper signal windows,
closes source-recovery and custody publication bookkeeping gaps, pins replay
launcher/interpreter/package closures, publishes terminal and ABI evidence
complete-or-absent, and binds ABI evidence to the exact candidate source.

The private diagnostic paired workload/phase authority freezes a method over
eight fixtures, two profiles, and 160 planned executions. It has not run and
selects no optimization. Runtime, public schema, semantic classes, scores,
candidate capacity, and malformed no-partial-output behavior remain unchanged;
no speed, RSS, comparative coverage, baseline equivalence, exploitability,
decoder, or concurrency claim follows. Fresh native, Docker, producer, replay,
parity, strict ShellCheck, delivery, and independent acceptance remain separate
from the retrospective's semester-completion claim.

## Post-semester Patch 088 acceptance continuation

Patch 088 carries exact-source acceptance work forward without changing the
Sprint 12 loader or mitigation product facts. It corrects transaction, recovery,
replay, ABI-stage, oracle, evidence, and delivery authorities discovered during
Patch 087 review. Its only new experiment is a diagnostic two-build split-debug
packaging study. No public mitigation field, runtime semantic class, score,
schema, decoder, concurrency, or release claim changes.
