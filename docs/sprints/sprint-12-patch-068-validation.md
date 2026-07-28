# Sprint 12 Patch 068 Validation Plan

## Status

Current corrective and held-out-confirmation implementation candidate. Patch 068
remains pending clean native, Docker, parity, and independent Lane A acceptance.

## Scope

Patch 068 resolves the Patch 067 corpus/private transaction, Make dependency,
and oracle findings, then adds a 96-object development-only private binary-role
and GNU-property confirmation. It changes no public CLI, JSON field, schema
version, candidate metric, semantic class, score, or runtime dependency.

## Source precondition

Patch 068 is defined against exact committed Patch 067 source:

```text
679c1b9c7383a20ba11f79f194b3eecbca2beb08
```

## Focused validation

```bash
make provisional-corpus-ready
make provisional-corpus-verify
make patch067-corrective-regression-smoke
make patch066-corrective-regression-smoke
make patch065-corrective-regression-smoke
make sprint12-role-property-layout-smoke
make sprint12-binary-role-smoke
make sprint12-gnu-property-oracle-smoke
make sprint12-gnu-property-smoke
make sprint12-role-property-metamorphic-smoke
make sprint12-role-property-heldout-smoke
```

Expected Patch 068 banners:

```text
patch067-corrective-regression-smoke: ok first_fchmod=1 ancestor_chain=1 rollback_retry=1 stale_oracle=1 make_dependency=1 abi_comments=1
sprint12-role-property-metamorphic-smoke: ok objects=28 pairs=12 mutants=4 roles=3 property_states=4 deterministic=28 public_commands=112 schema=unchanged
sprint12-role-property-heldout-smoke: ok objects=96 natural=48 metamorphic=48 probe_runs=288 unique_natural=48 provisional_overlap=0 malformed=12 schema=unchanged
```

## Corpus transaction acceptance

The corrective gate must prove:

1. a member inserted at the first `fchmod` boundary is rejected before any
   authenticated mode changes;
2. caller-visible ancestor-chain substitution is rejected while both the
   displaced authenticated corpus and foreign replacement remain unchanged;
3. a transient rollback `fchmod` failure is retried and every original mode is
   restored;
4. the obsolete Patch 063 displaced-root success expectation is replaced by the
   current fail-closed contract; and
5. ordinary authenticated mode-only drift still repairs and fully verifies.

## Held-out fact acceptance

The held-out gate requires:

- 48 natural objects from GCC and Clang, two source variants, three role
  constructions, and four GNU-property states;
- 48 metamorphic objects split into 24 positive canonical/alias objects and 24
  edge objects;
- 96 exact independently authored private fact-vector matches;
- three byte-identical fact-probe runs per object;
- 48 unique natural SHA-256 identities;
- zero natural-object hash overlap with the provisional corpus;
- exact separation of unknown, absent, present, contradictory, malformed, and
  unsupported states; and
- no public schema or private-field exposure.

Natural and metamorphic strata must be reported separately. Controlled
metamorphic evidence must not be represented as natural toolchain prevalence.

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

Native Ubuntu Docker and Docker Desktop remain separate environment strata.

## Preserved contracts

- program headers remain executable mapping authority;
- candidate capacity remains 4,096;
- candidate 4,097 returns exit code 6 before stdout;
- malformed parse failures emit no partial stdout;
- raw, exact, semantic-exact, unknown, future decoder-backed, and scored facts
  remain separate;
- private role/property facts remain absent from public text and JSON;
- the analyzer remains dependency-free, decoder-free, one-worker, bounded, and
  deterministic.

## Deferred work

Authenticated `readelf -h -l -d -n` reconciliation, native/container private
fact parity over the held-out corpus, the public-policy decision, positive
coordinate anchors, whole-batch timing, and process-tree RSS remain separate
future gates. Patch 068 evidence is diagnostic and cannot support publication or
runtime-CET claims.
