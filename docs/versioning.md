# Versioning Plan

## Independent versions

x64lens maintains two independent version lines:

```text
tool version:   0.1.0-dev
schema version: 0.2.0
```

Tool behavior can change while preserving the schema. Machine-readable contract changes require an explicit schema decision.

## Current version and roadmap state

Patch 087 retains tool version `0.1.0-dev` and schema `0.2.0`; no release tag
moves. Sprint 12 remains pending exact-source acceptance while Patch 087
corrects the Patch 086 transaction topology, wrapper signals, replay runtime,
terminal and ABI publication, exact-source evidence, and delivery findings. Patch 080's private additive role
side-car remains unchanged and unprojected.

Sprint 12’s internal role/property and GNU-property evidence remains private and
diagnostic. The public-policy authority records `defer`, adds zero fields, preserves the
coarse `mitigations.pie` meaning, and makes no runtime-CET claim. Patch 081 preserves
the same public fields, reference profile, private context sizes, and candidate-capacity
behavior. It adds no PIE reinterpretation or runtime-CET claim. Actual qualified parity,
replay-v2 execution and complete Patch 088 acceptance remain pending.

Measurements after Patch 082 require a distinct diagnostic campaign identity
and remain separate from Sprint 11 rows. The confirmatory corpus and method do
not freeze until Sprint 15.

## Release sequence

| Milestone | Version | Status |
|---|---|---|
| Integrated development checkpoint | `v0.1.0-dev` | Completed after Sprint 6 Patch 023. |
| Research preview candidate | `v0.1.0-rc1` | Planned after Sprint 16 preview gates. |
| First research release | `v0.1.0` | Planned after Sprint 22 release gates. |

## Checkpoint tag verification

```bash
git status --short
git show --stat --decorate v0.1.0-dev
git rev-parse v0.1.0-dev^{}
git rev-parse HEAD
```

The commit identifiers should match when verifying the original checkpoint commit. Later development naturally moves `HEAD` beyond the tag.

A normal branch push does not publish a tag. Publish a release tag explicitly only after its release checklist passes.

## Schema timeline

- `0.1.0`: retained representative final-shape historical target, mitigation,
  count, primitive, gadget, score, and limitations snapshot validated through a
  versioned compatibility schema.
- `0.2.0`: report and command identity plus bounded analysis-completeness
  contract introduced in Sprint 9 and retained as the current schema.
- `0.2.x`: compatible per-candidate provenance, validator, and evidence additions through the first research release.

The tool version remains `0.1.0-dev`; advancing the schema does not move the checkpoint tag. Do not introduce another breaking schema before `v0.1.0` unless a release-blocking correctness issue requires a documented migration and affected experiment restart.


## Historical schema compatibility

`schemas/x64lens-report.schema.json` names the current schema. The historical
`0.1.0` schema and representative final-shape report are preserved under
versioned file names. `make schema-compat-smoke` verifies those retained
artifacts while current producer validation requires schema `0.2.0` and command
identity. This is not a guarantee that every intermediate pre-release `0.1.0`
emission can be reconstructed or validated.

Schema version is part of benchmark provenance. Data from `0.1.0` and `0.2.0`
must not be merged without an explicit normalization procedure.

## Changelog rules

- Maintain exactly one `Unreleased` section.
- Record public behavior, schema, CLI, benchmark, contract, and release changes.
- Sprint retrospectives should state contract drift and update the changelog.
- Historical implementation notes may remain, but current status must appear first.

## Release tag rules

Before `v0.1.0-rc1` or `v0.1.0`:

1. working tree is clean,
2. native and Docker validation pass,
3. public documentation and planning checks pass,
4. schema and tool versions match documentation,
5. release artifacts and checksums verify,
6. benchmark and corpus identifiers are frozen,
7. tag message describes the release gate,
8. tag points to the validated commit.

See [`research-release-plan.md`](research-release-plan.md) and [`design/schema-evolution.md`](design/schema-evolution.md).


## Patch 041 schema compatibility note

Patch 041 remains schema `0.2.0`. Candidate evidence is optional in the formal
schema so initial Patch 040 reports stay valid, while current-producer tests
require it explicitly. This is a compatible addition within the `0.2.x` line,
not a redefinition of existing fields or counts.

## Patch 043 decoder-profile versioning note

Patch 043 does not change the tool version or schema. The default runtime remains
`0.1.0-dev` with schema `0.2.0`. A future decoder-enabled build or mode must carry
an explicit profile/build identity in release and benchmark metadata so its
results cannot be merged silently with the dependency-free core.

## Sprint 9 closeout version state

Patch 045 retains tool version `0.1.0-dev` and schema `0.2.0`. No release tag moves. Sprint 10 additions should remain compatible within schema `0.2.x` unless a new durable concept cannot be represented additively.

A future decoder-enabled or parallel build profile must have unambiguous artifact and benchmark provenance even if the CLI schema remains compatible. Different profiles must not be silently aggregated.

## Patch 048 compatibility note

Patch 048 retains tool version `0.1.0-dev` and schema version `0.2.0`. `stack_adjust` and `flags_write` are compatible additions to the existing side-effect enumeration; no required historical field or count meaning changes. A future required condition-flag structure or memory-operand object requires a separate schema decision.

## Sprint 10 Patch 053 milestone schedule

The evidence-gated roadmap now targets:

```text
Sprint 15  campaign freeze
Sprint 16  v0.1.0-rc1 candidate
Sprint 17  publication comparative campaign
Sprint 22  v0.1.0 research release
```

Diagnostic evidence from Sprint 11 remains development data. It does not carry
the release authority of a frozen Sprint 15 campaign.


## Historical Sprint 10 closeout version state

Patch 054 retains tool version `0.1.0-dev` and schema `0.2.0`. No release tag
moves. At that checkpoint, Sprint 10 was complete and Sprint 11 was the active
diagnostic benchmark stage. Diagnostic rows had no release authority before the
Sprint 15 campaign freeze. Optional decoder or worker profiles require distinct
build and benchmark identity even when they remain schema-compatible.

Patch 054 closed Sprint 10 without advancing the tool or schema version. Sprint
11 diagnostic artifacts retain `0.1.0-dev` and schema `0.2.0` provenance.
Neither `v0.1.0-rc1` nor `v0.1.0` is created during diagnostic work; those
remain evidence-gated milestones at Sprints 16 and 22.

## Sprint 12 Patch 071 version state

Patch 071 retains tool version `0.1.0-dev` and JSON schema `0.2.0`. The version-2
batch authority is a development-method authority, not a product schema. No CLI,
report field, candidate meaning, score, runtime profile, release tag, or campaign
freeze changes. External-natural acquisition and any compatible public
role/property decision remain later, separately identified patches: Patch 072
performs outcome-blind external-natural acquisition and native/container
private-fact parity, Patch 073 executes the non-reinterpretive public-policy gate
as an explicit deferral without changing tool or schema version, and Patch 074
implements the final custody/parity-protocol corrections without moving either
version. Sprint 12 closes and Sprint 13 becomes active only after complete
acceptance.


## Sprint 12 Patch 074 version state

Patch 074 retains tool version `0.1.0-dev`, JSON schema `0.2.0`, all public
fields, and the `v0.1.0-dev` checkpoint tag. Delivery custody version 3, retained
selection/parity authorities, tracked-only permission normalization, and the
Sprint 12 closeout authority are development and validation contracts, not
product or schema versions. Patch 074 was superseded as the closeout candidate;
Sprint 13 remains an entry candidate without a release tag or campaign freeze.

## Sprint 12 Patch 076 version state

Patch 076 retains tool version `0.1.0-dev`, JSON schema `0.2.0`, all public
fields, and the `v0.1.0-dev` checkpoint tag. Patch 075 private text-relocation
facts and Patch 076 distinct private RPATH/RUNPATH facts do not change a product
or schema version. Patch 076 was superseded by Patch 077; Patch 077's review
required Patch 078; and Patch 078 was superseded by the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080.

## Sprint 12 Patch 077 historical version state

Patch 077 changed no runtime analyzer source, NASM ABI include, public schema,
CLI syntax, output field, candidate population, or score. It retained the
private textrel/RPATH/RUNPATH facts and strengthened only their application,
recovery, custody, comparator, parity, Docker-build, and evidence authorities.
Its review required Patch 078.

## Sprint 13 Patch 078 version state

Patch 078 retains tool version `0.1.0-dev`, schema `0.2.0`, the public field
set, candidate-capacity and no-partial-output contracts, and the dependency-
free, decoder-free, one-worker reference profile. It changes no analyzer
runtime or score. Patch 079 executes deterministically presentation-ordered
task-value qualification before any runtime-semantic, public-field, or score
projection.

## Historical Sprint 13 Patch 079 version state

Patch 079 retains tool version `0.1.0-dev`, schema `0.2.0`, all public fields,
all current scores, candidate capacity 4,096, and the dependency-free, decoder-
free, one-worker reference profile. It records private task-value evidence and
corrective tooling only. `generic_control`, `sysv_call_arguments`, and
`linux_syscall_arguments` qualify only as private task-value evidence;
`syscall_number` and `stack_pivot` remain deferred, with existing runtime
semantics and scores unchanged. Patch 080 subsequently retained the three
qualified facets privately and deferred compatible public and score changes.

## Historical Sprint 13 Patch 080 version state

Patch 080 retains tool version `0.1.0-dev` and schema `0.2.0`. The private role
record is not a public schema field. It changes no release tag, required JSON
property, semantic class, candidate count, or score.

## Patch 081 version boundary

Patch 081 retains tool version `0.1.0-dev` and schema `0.2.0`. No public field,
required property, count meaning, semantic class, or score changes. Patch 080's
review required this corrective candidate; independent exact-source Patch 088 acceptance remains
pending.


## Patch 082 version boundary

Patch 082 retains tool version `0.1.0-dev`, schema `0.2.0`, all public fields,
semantic classes, scores, candidate populations, and the dependency-free,
decoder-free, one-worker reference profile. The producer and coordinate
authorities are development-validation contracts, not product or schema
versions. Natural coordinate qualification remains a separate diagnostic gate.


## Patch 083 compatibility note

Patch 083 leaves tool version `0.1.0-dev` and schema `0.2.0` unchanged. Its new
artifacts are diagnostic campaign authorities, not public report fields.

## Patch 084 compatibility note

Patch 084 retains tool version `0.1.0-dev` and schema `0.2.0`. It changes no
assembly runtime, include contract, public field, semantic class, score, count
meaning, candidate capacity, decoder profile, or worker policy. The new ABI-role
query and lifecycle authorities are private validation artifacts. The retained
P083 natural campaign remains diagnostic and comparison-unqualified.

## Patch 085 compatibility note

Patch 085 retains tool version `0.1.0-dev` and schema `0.2.0`. It changes no
assembly runtime, include contract, public field, semantic class, score, count
meaning, candidate capacity, decoder profile, or worker policy. No tracked file
under `src/`, `include/`, or `schemas/` changes. Frozen-input replay and layered
terminal attribution are the only new evidence authorities; lifecycle, ABI-query,
source, recovery, exact-tree, and delivery changes harden existing authorities.
Actual replay and generated attribution evidence remain pending; any result is
diagnostic, `frozen=false`, and publication-ineligible.

## Patch 086 compatibility note

Patch 086 retains tool version `0.1.0-dev` and schema `0.2.0`. It changes no
runtime `src/`, `include/`, or `schemas/` file, public field, semantic class,
score, count meaning, candidate capacity, decoder profile, concurrency profile,
or output contract. Replay-v2 and the private ABI-vector equivalence authority
are validation evidence, not product or schema versions. No completed local
replay, public role projection, release tag, FORTIFY fact, or publication result
is claimed.

## Patch 087 compatibility note

Patch 087 is an implementation candidate pending complete exact-source
acceptance. It retains tool version `0.1.0-dev`, schema `0.2.0`, runtime
behavior, public fields, semantic classes, scores, count meanings, candidate
capacity, malformed no-partial-output behavior, decoder policy, and the
one-worker reference profile. Replay, terminal-attribution, ABI-vector, and
workload/phase evidence remains private and diagnostic. The phase method is
frozen but unexecuted and non-selecting; it authorizes no speed, RSS,
comparative coverage, baseline equivalence, exploitability, decoder,
concurrency, release, or publication claim.

## Patch 088 compatibility note

Patch 088 retains tool version `0.1.0-dev` and schema `0.2.0`. It adds no CLI,
public field, semantic, score, count, or compatibility change. Split-debug
artifacts belong to a diagnostic packaging experiment and are not current
release artifacts.
