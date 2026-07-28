# Sprint 12 Patch 069 Validation

## Purpose

Patch 069 corrects the remaining Patch 068 corpus-custody and private-fact
matrix defects, then reconciles the authenticated 96-object private role and
GNU-property result against exact GNU `readelf -hW`, `-lW`, `-dW`, and `-nW`
output.

The patch changes development evidence and validation infrastructure only. It
adds no runtime analyzer module, public field, schema change, candidate family,
score, decoder, worker, or dependency.

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
result. The exact eligible total is a contract of the Patch 069 authority and
must not be recomputed by discarding ambiguous, unavailable, or inapplicable
cells.

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

The comparison authority classifies every private field as one of:

```text
direct
derived
ambiguous
unavailable
not eligible for this object
```

Only direct and reproducibly derived eligible fields participate in the
zero-unexplained-mismatch gate. Raw `readelf` output and every field disposition
are retained. `readelf` does not become runtime authority, and comparator
silence does not become a negative x64lens fact.

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

Native/container private-fact parity, broader outcome-blind external-natural
acquisition, the public-policy decision, positive coordinate anchors,
whole-batch timing, and process-tree RSS remain separate gates. Patch 069 is
diagnostic evidence and cannot support release-facing role, CET, speed, RSS, or
coverage claims.
