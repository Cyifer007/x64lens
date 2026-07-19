# ADR 0041: Sprint 11 Diagnostic Runner Foundation

## Status

Accepted for Sprint 11 Patch 055.

## Context

Sprint 11 begins diagnostic measurement before the confirmatory campaign is
frozen. The project needs timing and resource evidence that is more precise and
better authenticated than the existing GNU `time` smoke scripts, while keeping
all measurement infrastructure outside the freestanding analyzer binary.

Two Patch 054 validation weaknesses also require correction before new evidence
is trusted:

- the roadmap checker rejected broad chronology drift but accepted several exact
  stale phrases from superseded planning text;
- the Sprint 10 closeout checker compared mutually editable summary authorities
  and printed fixed success counts instead of the values it had actually
  observed.

The benchmark task model also needs a narrower statement than the roadmap's
original shorthand. The current public CLI does not expose a report-suppressed
scanner-only command. In addition, schema `0.2.0` JSON from `gadgets` and
`analyze` is produced from the same analysis records and differs by command
identity rather than by a second, broader analysis implementation. Treating
those commands as three independent workloads would create misleading evidence.

## Decision

1. Add a standard-library Python diagnostic runner under
   `benchmarks/scripts/`. It remains development and research infrastructure and
   adds no runtime dependency to x64lens. Its dedicated environment gate checks
   only the build tools, sample compiler, Make, and Python rather than requiring
   unrelated comparison or archive utilities.
2. Preserve the exact campaign specification and runner source, then snapshot
   every tool, target, and timer-floor probe before execution. Hash sources
   before and after copying, execute only tool/probe snapshots, and record
   snapshot size and SHA-256 identity. A source spec or runner change during a
   campaign fails closed.
3. Measure the direct tool child with `time.monotonic_ns()` and Linux `wait4`,
   recording wall, user, system, maximum RSS, faults, context switches, output
   size, output hashes, exit state, signal state, and timeout state. Descendant
   resources are not aggregated and remain an explicit methodology limitation.
4. Start every measured command in a distinct process group. Enable Linux
   subreaper behavior, terminate and reap both same-group helpers and descendants
   that create another session or process group, and retain the failed row
   instead of discarding it.
5. Publish a campaign only after all rows, outputs, timer-floor samples, and the
   manifest are complete. Reject symlinks and other non-regular members before
   flushing the result tree, then rename it with no-replace semantics so an
   existing campaign is never overwritten.
6. Require every campaign to declare `evidence_class: diagnostic`,
   `frozen: false`, and `publication_eligible: false`. Diagnostic rows cannot be
   promoted into the Sprint 15-frozen campaign by renaming them.
7. Measure and preserve a timer-floor distribution before the task conditions.
   A single-process row below the provisional floor is labeled accordingly and
   requires a larger target or a separately reviewed batch method before it can
   support a timing interpretation.
8. Counterbalance condition order through an explicit listed or alternating
   policy. Cache state is declared as warm or uncontrolled; a warm policy
   requires excluded warmup rows, which are still retained in the campaign.
   Every child receives fixed C/UTC/path settings and private per-command home,
   temporary, cache, configuration, and data roots. Campaigns cannot override
   those reserved environment keys.
9. Establish a machine-readable task authority:
   - `core_scanner` is unavailable because no truthful report-suppressed path
     exists;
   - `x64lens_gadget_json` is implemented;
   - `x64lens_integrated_analysis_json` is implemented but belongs to the same
     command-identity parity group as gadget JSON;
   - ROPgadget, Ropper, and ropr adapters remain planned until commands,
     versions, output scope, and candidate definitions are normalized.
10. Strengthen the Patch 054 gates. Roadmap validation receives path-specific
    stale-phrase regressions. Sprint 10 closeout state is reconciled against
    Makefile/version constants, assembly record definitions, the optional-
    profile stage authority, and the independent one-per-pattern JSON fixture.
    The success banner is generated from observed values.

## Architecture boundary

The analyzer pipeline is unchanged:

```text
file mapping and bounds
  -> loader facts and executable regions
  -> raw candidate scanning
  -> exact recognition
  -> semantic classification
  -> provenance and effect side-cars
  -> scoring
  -> text or JSON reporting
```

The diagnostic path surrounds that pipeline:

```text
campaign specification
  -> immutable tool/target snapshots
  -> timer-floor probes
  -> isolated child execution
  -> raw rows and output artifacts
  -> diagnostic manifest
```

The runner may observe public process and report outputs. It may not become a
source of analyzer facts, alter candidate records, infer semantic classes, or
change score policy.

## Consequences

- The reference binary remains dependency-free, decoder-free, one-worker,
  bounded, and suitable for constrained or air-gapped deployment.
- Failed commands, signals, timeouts, and extractor failures remain visible as
  evidence rather than silently reducing the sample count.
- Tool and target identity is bound to the bytes actually executed and analyzed,
  not merely to mutable source paths.
- The initial reference campaign can validate the runner and command parity, but
  it cannot establish scanner-only cost or baseline superiority.
- Provisional corpus construction, baseline adapters, summary statistics, and
  the Sprint 12-14 engineering gap register remain later Sprint 11 work.

## Rejected alternatives

### Add timing syscalls to the analyzer immediately

Rejected because instrumentation would alter the reference binary, complicate
runtime claims, and risk creating a special benchmark build before the task gap
is measured.

### Label `gadgets --format json` as raw scanner cost

Rejected because JSON generation occurs after parsing, scanning, matching,
classification, side-car materialization, scoring, annotation, and summary
construction.

### Treat `analyze --format json` as a distinct broader workload today

Rejected because the current command reuses the same report body and analysis
facts. Measuring both remains useful for command-path parity, but not as proof
of different work scope.

### Use a third-party benchmark framework

Rejected for the reference harness because a standard-library implementation is
portable into minimal and air-gapped development environments and keeps the
measurement dependency surface explicit.
