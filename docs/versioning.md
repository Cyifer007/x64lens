# Versioning Plan

## Independent versions

x64lens maintains two independent version lines:

```text
tool version:   0.1.0-dev
schema version: 0.2.0
```

Tool behavior can change while preserving the schema. Machine-readable contract changes require an explicit schema decision.

## Current version and roadmap state

Patch 078 retains tool version `0.1.0-dev` and schema `0.2.0`; no release tag
moves. Sprint 12 remains pending acceptance while Patch 078 corrects the
remaining Patch 077 transaction, parity-publication, cleanup, Git-less Docker
source, digest-oracle, and delivery boundaries. The private textrel, RPATH, and
RUNPATH facts remain unchanged. Patch 078 also freezes a private exact-pop role
authority without changing the runtime report, scores, or public schema.

Sprint 12’s internal role/property and GNU-property evidence remains private and
diagnostic. The public-policy authority records `defer`, adds zero fields,
preserves the coarse `mitigations.pie` meaning, and makes no runtime-CET claim.
Patch 078 preserves the same public fields, reference profile, private context
sizes, and candidate-capacity behavior. It adds no PIE reinterpretation or
runtime-CET claim. Actual qualified parity and complete Patch 078 acceptance
remain pending.

Measurements after Patch 078 require a distinct diagnostic campaign identity
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
Sprint 13 remains planned without a release tag or campaign freeze.

## Sprint 12 Patch 076 version state

Patch 076 retains tool version `0.1.0-dev`, JSON schema `0.2.0`, all public
fields, and the `v0.1.0-dev` checkpoint tag. Patch 075 private text-relocation
facts and Patch 076 distinct private RPATH/RUNPATH facts do not change a product
or schema version. Patch 076's review required the Patch 077 correction, whose
review required the Patch 078 closeout correction, whose review required the current Patch 079 corrective and task-value candidate and Sprint 13 entry
candidate.

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
runtime or score. Patch 079 executes blinded task-value qualification before any
runtime-semantic, public-field, or score projection.

## Sprint 13 Patch 079 version state

Patch 079 retains tool version `0.1.0-dev`, schema `0.2.0`, all public fields,
all current scores, candidate capacity 4,096, and the dependency-free, decoder-
free, one-worker reference profile. It adds a private diagnostic authority and
corrective tooling only. Qualified role facets remain private and unscored; an
LC-08B decision is required before any compatible public or runtime change.
