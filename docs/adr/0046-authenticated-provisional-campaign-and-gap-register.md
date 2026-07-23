# ADR 0046: Authenticated Provisional Campaign and Engineering Gap Register

## Status

Accepted for the Sprint 11 Patch 060 implementation candidate. Empirical patch
acceptance remains subject to the full native, Docker, parity, and post-patch
review gates.

## Context

Patch 059 established the stage-zero measurement plane: runner-bound baseline
normalization, matched x64lens relations, address-coordinate calibration,
runtime-closure evidence, and a 30-condition authority. Its review identified
remaining integrity defects in version-command authority, path ancestry,
derived-relation authenticity, retained executable selection, transactional
publication, and private rollback identity. Running a comparative campaign
before correcting those defects would create apparently precise but
insufficiently authenticated development evidence.

Sprint 11 requires diagnostic rows, task-scoped summaries, and an engineering
gap register. These artifacts may direct Sprints 12 through 14, but they remain
mutable development evidence and cannot be promoted into preview or publication
claims.

## Decision

Patch 060 corrects the Patch 059 evidence-integrity findings and adds one
external diagnostic orchestrator:

```text
verified provisional corpus
  + exact task authority
  + available authenticated tool executables
  -> high-resolution native runner rows
  -> retained success, failure, timeout, output-limit, below-floor,
     normalization-failure, and unavailable-tool conditions
  -> task-bound x64lens and baseline relation artifacts
  -> task-path runtime-closure manifests
  -> same-target address-coordinate calibration when evidence is complete
  -> generated task summaries
  -> generated engineering capability/performance gap register
```

The authority contains 24 comparative gadget-report conditions and six
independent x64lens integrated-analysis controls. Missing optional baselines are
not replaced or silently dropped. They remain explicit `unavailable_tool`
conditions while available tools execute normally.

The selected six-target screen intentionally balances compiler, optimization,
requested linkage role, and hardening dimensions; it does not independently
cross every factor. Patch 060 therefore reports factor attribution as
unidentifiable from the selected screen. A later full-factor experiment is
required before attributing an observed difference to one build factor.

## Integrity corrections

Patch 060 requires:

- authority-bound baseline version commands;
- component-wise no-follow resolution for every artifact ancestor;
- deterministic reproduction of normalized relations from retained native rows;
- runtime closure derived from retained execution snapshots and task commands;
- creation-time stage identity preserved through reserve-and-exchange
  publication for runner and corpus results;
- exact directory identity during private-package rollback;
- relative, caller-independent delivery checksum records.

## Metric and claim boundaries

The campaign keeps these populations separate:

- tool-native records and duplicates;
- tool-reported return-ending records and sites;
- normalized exact relations;
- x64lens raw, exact, semantic-exact, unknown, and scored candidates;
- binary-level relation presence;
- runtime, CPU, RSS, output, failure, and below-floor observations.

No generic cross-tool `gadget_count` is produced. No address join is allowed
until same-target calibration succeeds across `ET_EXEC`, PIE-intended `ET_DYN`,
and shared-object `ET_DYN` roles. `ET_DYN` itself remains insufficient to infer
PIE versus DSO identity.

Patch 060 evidence is always:

```text
evidence_class: diagnostic
frozen: false
publication_eligible: false
```

It cannot support release-facing performance, memory, coverage, superiority,
or defensive-utility claims.

## Analyzer boundary

No analyzer assembly, command, exit code, schema field, semantic class, score,
record layout, candidate capacity, arena allocation, decoder policy, worker
policy, or runtime dependency changes. Program headers remain executable-region
authority. The campaign, adapters, calibrator, closure generator, summaries, and
gap register remain external development infrastructure.

## Consequences

Positive:

- the complete 30-condition plan is accounted for even when optional tools are
  absent;
- failed and unavailable conditions remain visible;
- summaries regenerate from authenticated native rows and derived artifacts;
- Sprint 12 through 14 priorities are traceable to named diagnostic evidence;
- the dependency-free one-worker analyzer remains the reference profile.

Costs and limitations:

- baseline installation remains environment-specific;
- small targets may remain below the single-process timing floor;
- the six-target screen cannot identify causal build-factor effects;
- runtime closure is bounded observed task-path provenance, not universal future
  process behavior;
- diagnostic priorities remain revisable before the Sprint 15 freeze.

## Validation

Focused gates:

```bash
make patch059-corrective-regression-smoke
make sprint11-campaign-plan-smoke
make sprint11-p060-campaign-smoke
make sprint11-measurement-plane-smoke
```

The complete native, strict ShellCheck, Docker, capacity, malformed-input,
public-overlay, and native/container parity gates remain mandatory before
acceptance.

## Handoff

Patch 061 performs Sprint 11 closeout, reconciles the accepted diagnostic gap
register with Sprint 12 entry, and does not add loader or mitigation capability.
