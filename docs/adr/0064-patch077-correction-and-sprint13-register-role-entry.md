# ADR 0064: Patch 077 Correction and Sprint 13 Register-Role Entry

## Status

Recorded as the Patch 078 implementation decision. Patch 078 did not complete
acceptance; Patch 079 supplied the resulting corrective and private task-value
candidate. Patch 079 was superseded by Patch 080, and Patch 080 by Patch 081. Patches
081 and 082 were not accepted. Patches 083 and 084 also did not complete acceptance;
Patch 085 is the current exact-source implementation candidate, pending independent
exact-source acceptance.

## Context

Patch 077 preserved the implemented private loader and mitigation fact model,
but acceptance validation identified blockers in the surrounding transaction
and validation surfaces. The confirmed defects covered repository-root rebinding
during patch
application and permission normalization, expected-failure JSON parsing,
parity-result publication through a replaced parent, final cleanup of a foreign
replacement, a wrong-digest negative oracle that stopped before digest
verification, Git-dependent validation inside the intended Git-less Docker
source, and delivered helper/source-membership inconsistencies.

Sprint 13 also needs a precise decision for all exact single-pop GPR patterns.
The existing effect records already distinguish register writes, stack effects,
and the `rsp` pivot. Treating every pop as the existing public `arg_control`
class would be incorrect because System V call arguments, Linux syscall
arguments, the syscall number, generic register control, and a stack pivot are
not the same role.

## Decision

Patch 078 is one cohesive corrective and entry patch.

### Transaction and custody correction

- Patch application and rollback retain authenticated repository-root, Git
  directory, and patch-byte descriptors across check and mutation.
- The transaction accepts either the reviewed staged Patch 077 tree or a later
  commit whose tree is byte-identical to that reviewed tree. It never guesses a
  base from branch names or remote state.
- Tracked-permission normalization binds the repository before reading the Git
  index and retains descriptor-backed rollback identity.
- Expected nonzero gadget/analyze outcomes require empty stdout and are not
  parsed as JSON.
- Parity publication reauthenticates both the result root and caller-visible
  parent after no-replace publication.
- Delivery and source-recovery cleanup reauthenticate the final object and
  retain an observed descriptor through the destructive operation. The Linux
  same-UID compare-and-unlink race remains an explicit limitation because the
  kernel offers no atomic unlink-by-file-descriptor primitive.
- Docker builds use an exact Git-less source context created from authenticated
  staged Git objects. Ignored, generated, and local files cannot enter `/work`.
- Wrong-digest negative tests must reach and fail the digest comparison itself.
- Loose and packaged helper bytes are one identity in the final delivery.

### Sprint 13 register-role entry

The private decision authority accounts for all 16 exact single-pop patterns
with additive role facets:

- generic register control: every exact pop except `pop rsp; ret`;
- System V call arguments: `rdi`, `rsi`, `rdx`, `rcx`, `r8`, and `r9`;
- Linux x86_64 syscall arguments: `rdi`, `rsi`, `rdx`, `r10`, `r8`, and `r9`;
- syscall number: `rax`;
- stack pivot: `rsp`.

`rcx` remains the fourth System V call argument. `r10` is the fourth Linux
syscall argument. These facets are not interchangeable.

Patch 078 does not change classifier output, scores, JSON, text output, schema
`0.2.0`, or public mitigation fields. Existing public semantic classes and
scores remain unchanged. The newly recorded role facets are private decision
facts and remain unscored. Patch 079 used deterministic presentation order as
non-causal display metadata before any runtime-semantic, public-field, or score
projection.

## Preserved boundaries

- Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable
  authority.
- Section and dynamic metadata remain bounded facts or annotations.
- Mapping, loader parsing, scanning, exact matching, classification, provenance
  and effect side-cars, scoring, and reporting remain separate.
- Raw, exact-suffix, semantic-exact, unknown, future decoder-backed, and scored
  facts remain distinct.
- Candidate capacity remains 4,096; candidate 4,097 returns exit code 6 before
  stdout.
- Malformed parser failures emit no partial report.
- The default runtime remains dependency-free, decoder-free, deterministic,
  and one-worker.

## Consequences

Patch 078 addressed the Patch 077 acceptance blockers without modifying the
analyzer runtime, but did not complete acceptance. Sprint 12 remains active and
Sprint 13 remains an entry candidate pending complete Patch 085 acceptance. The
authenticated entry decision alone does not qualify runtime or public projection
of the private role facets.

Patch 079 ran the deterministically presentation-ordered role-query task-value
gate. Three facets qualified only as private task-value evidence and two remained
deferred. Patch 080 subsequently retained the three facets in a private additive
side-car and deferred public-field and score changes; any future behavior change
must update fixtures, effects, validators, documentation, task definitions, and
diagnostic campaign identity.

## Validation

Required gates include:

```text
make patch077-corrective-regression-smoke
make sprint13-register-role-decision-smoke
make sprint12-closeout-smoke
make sprint12-continuation-smoke
make validation-smoke
make docker-validation-smoke
make sprint13-p078-acceptance-smoke
```

The historical Patch 078 acceptance boundary required an authenticated source,
native build and test
gates, strict ShellCheck, Docker aggregates, both private-fact parity planes,
the exact package lifecycle, and independent exact-source acceptance
against the exact Patch 078 source. Its review instead required Patch 079.
