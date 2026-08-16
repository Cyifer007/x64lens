# Sprint 12 Patch 069 Validation

## Status

Historical Sprint 12 corpus-integrity and authenticated external-reconciliation
implementation candidate. Patch 069 required the further Patch 070 evidence-
integrity correction. Patch 070 was rejected after acceptance validation.
Patch 071 required further correction, and Patch 072's returned review rejected
acceptance. Patches 070, 071, 072, and 073 were not accepted at their
respective first returned review boundaries. Patch 073 delivered the first
custody/isolation correction and policy deferral. Patch 074 was a superseded
Sprint 12 closeout candidate. Patch 075 introduced bounded private static
text-relocation evidence, and Patch 076 implemented distinct private `DT_RPATH`
and `DT_RUNPATH` carrier/value evidence. Patch 076 was superseded by Patch 077.
Patch 077 was superseded by Patch 078, whose review required the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080. Current validation expectations are
recorded in the
[Patch 087 validation record](sprint-13-patch-087-validation.md). The
[Patch 073 validation record](sprint-12-patch-073-validation.md) preserves the
first custody/isolation correction and policy-deferral boundary. The
[Patch 071 validation record](sprint-12-patch-071-validation.md) preserves that
historical boundary, and the
[Patch 070 validation record](sprint-12-patch-070-validation.md) preserves the
rejected boundary. The matrix and
`readelf` reconciliation remain diagnostic, unfrozen, and publication-
ineligible. Patch 072 added the environment-parity protocol, but corrected
actual native/container parity evidence and complete Patch 088 acceptance remain
pending.
Patch 073 records the public-policy decision as `defer`. Results below are
historical candidate contracts or
controlled diagnostic observations, not accepted publication outcomes.

## Purpose

Patch 069 corrects the remaining Patch 068 corpus-custody and private-fact
matrix defects, then reconciles the authenticated 96-object private role and
GNU-property result against exact GNU `readelf -hW`, `-lW`, `-dW`, and `-nW`
output.

The patch changes development evidence and validation infrastructure only. It
adds no runtime analyzer module, public field, schema change, candidate family,
score, decoder, worker, or dependency.

## Source precondition

Patch 069 is defined against exact committed Patch 068 source:

```text
a28731a74367cb14d464ccf5160257bda75c9689
```

## Exact focused commands

```bash
make provisional-corpus-ready
make provisional-corpus-verify
make patch068-corrective-regression-smoke
make sprint12-role-property-heldout-smoke
make sprint12-role-property-readelf-smoke
```

## Expected focused results

```text
patch068-corrective-regression-smoke: ok retained_semantics=1 signal_rollback=1 directory_size=2 authority_inputs=5 private_leaks=8 retained_vectors=36 edge_layouts=24 include_dependency=1
```

```text
sprint12-role-property-heldout-smoke: ok objects=96 natural=48 metamorphic=48 probe_runs=288 public_commands=384 fact_fields=18 expected_vectors=96 observed_vectors=96 unique_natural=48 provisional_targets=24 provisional_overlap=0 edge_layouts=24 malformed=12 schema=0.2.0
```

```text
sprint12-role-property-readelf-smoke: ok objects=96 commands=384 fields=1728 eligible_matches=1224 eligible_mismatches=0 ambiguous=96 unavailable=288 not_eligible=120 public_policy=deferred
```

Host-specific `readelf` version and executable hashes are retained in the
result. For this authenticated matrix, the observed field dispositions produce
1,224 eligible matches. The authority requires all 1,728 dispositions to be
retained and zero unexplained eligible mismatches; the 96 ambiguous, 288
unavailable, and 120 `not_eligible` cells remain outside the eligible denominator
and must not be discarded or relabeled.

## Corpus transaction acceptance

The corrective oracle requires:

- semantic verification from retained descriptor-authoritative bytes;
- complete root and nested-directory identity, including directory size;
- rejection of visible-path substitution;
- termination-safe rollback after a real mode change;
- restoration and verification of every original mode after failure; and
- no mutation of a foreign replacement.

Mode repair remains authorized only for an otherwise authenticated corpus.
Byte, manifest, membership, ownership, timestamp, type, symlink, or semantic
drift remains fail-closed.

## Private-fact matrix acceptance

The maintained 96-object gate must consume and authenticate:

```text
held-out task authority
analyzer executable
public schema authority
private fact probe
24-target provisional corpus
```

For every object it retains all 18 expected and observed private fields, the
object identity, raw public command outputs for `info`, `mitigations`,
`gadgets --format json`, and `analyze --format json`, stderr, and exact command
metadata. Private field names or namespaces in either output stream are a
failure.

Natural and metamorphic strata remain separate. The 24 edge objects must remain
24 parser-visible layouts rather than multiple names for fewer byte layouts.

## readelf reconciliation acceptance

The comparison authority assigns every private field one stable authority
class:

```text
direct
derived
ambiguous
unavailable
```

For each object/field cell, the retained crosswalk then records a separate
disposition:

```text
match
mismatch
ambiguous
unavailable
not_eligible
```

The last value covers fields that are inapplicable for that object because the
represented private fact was not reached or the comparator representation was
not usable. Only `match` or `mismatch` dispositions backed by direct or
reproducibly derived authority participate in the zero-unexplained-mismatch
gate. Raw `readelf` output and every field disposition are retained. `readelf`
does not become runtime authority, and comparator silence does not become a
negative x64lens fact.

## Full native validation

```bash
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make section-label-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
make system-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

## Docker and parity

Record the selected Docker context and daemon before running:

```bash
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

Native Ubuntu Docker and Docker Desktop remain separate evidence strata.

## Preserved contracts

- program headers remain executable mapping authority;
- candidate capacity remains 4,096;
- candidate 4,097 returns exit code 6 before stdout;
- malformed parse failures emit no partial stdout;
- raw, exact, semantic-exact, unknown, future decoder-backed, and scored facts
  remain separate;
- public schema remains `0.2.0`;
- public text and JSON expose no private role/property fields;
- static GNU properties do not establish runtime CET enforcement; and
- the reference analyzer remains dependency-free, decoder-free, one-worker,
  bounded, and deterministic.

## Deferred work

At the Patch 069 boundary, native/container private-fact parity and broader
outcome-blind external-natural acquisition remained separate gates; Patch 072
implements both, while qualified native/container parity evidence remains
pending. The public-policy decision, positive coordinate anchors, whole-batch
timing, and process-tree RSS remain separate gates. The matrix and reconciliation
results are diagnostic evidence and cannot support release-facing role, CET,
speed, RSS, or coverage claims.
