# Benchmarks

This directory contains the reproducible benchmark harness for x64lens.

Benchmarking is a first-class research feature. Do not make performance claims without preserving:

- tool versions,
- exact commands,
- corpus manifest,
- host metadata,
- run count,
- raw results,
- summary statistics.

See `docs/benchmark-methodology.md`.

## Contract

Benchmark results must be reproducible. Record tool versions, exact commands, CPU/RAM/platform, run count, and corpus manifest before using results in the paper.

## Sprint 3 scanner smoke benchmark

The first scanner smoke benchmark can be run with:

```bash
make bench-scanner-smoke
```

or directly:

```bash
RUNS=5 MAX_DEPTH=4 benchmarks/scripts/bench-scanner-smoke.sh ./build/x64lens ./tests/bin/gadgets /bin/ls
```

The script writes TSV results and a metadata file into `benchmarks/results/`. These files are ignored by Git unless explicitly promoted into a documented benchmark artifact.

This benchmark is a development smoke test. It is not publication evidence by itself.


## Sprint 3 arena-backed candidate storage

Patch 010 moves raw gadget candidate records into an mmap-backed arena. The scanner smoke benchmark can be used as a development sanity check before and after allocator changes, but these runs are not publication-quality results by themselves. Publication benchmarks require a stable corpus, clean environment, repeated trials, and baseline tool comparisons.


## Sprint 3 exact pattern count

Patch 011 adds an `exact_pattern_count` column to scanner smoke TSV output. This metric counts raw candidates tagged by `patterns.asm` with exact byte-template IDs. It is not a semantic primitive count and should not be interpreted as exploitability evidence until the classifier and scoring layers are implemented.


## Sprint 5 Patch 019 baseline comparison smoke

Patch 019 adds a development-level baseline comparison harness:

```bash
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
python3 benchmarks/scripts/summarize.py benchmarks/results/baseline-smoke-*.tsv
```

The harness always runs x64lens and optionally runs ROPgadget, Ropper, and ropr when those tools are installed. Missing optional baseline tools are recorded in the metadata sidecar and skipped by default. Set `REQUIRE_BASELINES=1` only in environments where at least one optional baseline tool is expected.

The baseline smoke TSV records tool path, tool version, exact command, target size, target SHA256, run number, wall-clock time, max RSS, exit code, output size, and x64lens JSON-derived raw/exact/semantic/unknown/scored counts. It is not a publication benchmark by itself.


## Sprint 11 Patch 055 diagnostic runner

Validate the high-resolution measurement and task-definition contracts with:

```bash
make diagnostic-tools-check
make diagnostic-runner-smoke
make diagnostic-task-definitions-smoke
make sprint11-diagnostic-reference-smoke
```

Run the controlled x64lens reference conditions after building the analyzer and
fixtures:

```bash
make bench-diagnostic-smoke
```

Set `DIAGNOSTIC_CAMPAIGN_ID` to choose a stable local result identity. Campaigns
are written under `benchmarks/results/diagnostic/` and remain ignored until a
later evidence-promotion decision.

Each campaign retains hashed runner, exact-specification, tool, target, and
timer-probe files. The measured child receives byte-identical executable,
write-sealed Linux `memfd` copies of the tool and probe plus a non-executable,
execution-sealed target copy; recorded replay commands resolve
campaign-relatively to the retained files. Campaigns also retain
isolated per-command environment roots, observed tool version output,
timer-floor samples, warmup and measured rows, Linux `wait4` resource data for
the selected child, stdout/stderr artifacts, and a manifest. The runner
reconciles version, timer, and row artifact identities after the final measured
child exits. Resource counters include descendants the selected child waited
for, but not descendants reaped separately by the runner; maximum RSS is not a
process-tree sum. Failed rows are preserved. Campaigns are explicitly
diagnostic, mutable, and not publication eligible.

`make diagnostic-tools-check` executes a sealed executable-`memfd` preflight.
On kernels that support `MFD_EXEC`, the runner requests it explicitly; an
`EINVAL` retry without that flag supports older kernels. A host policy that
prohibits executable memfds fails this prerequisite rather than degrading to
mutable execution input.

The campaign-integrity boundary covers the runner and measured descendants.
Concurrent external processes with the same user identity are outside that
boundary and can mutate diagnostic evidence, including after publication.
Run campaigns in a workspace not shared with such writers and authenticate any
evidence again before promotion.

The initial reference specification contains gadget JSON and analyze JSON
command conditions. It deliberately contains no scanner-only condition because
the current CLI has no report-suppressed scanner path. The two JSON commands
share the current analysis body and remain a command-identity parity pair rather
than independent work scopes.

## Sprint 11 Patch 056 provisional corpus

Patch 056 adds a versioned 24-target GCC/Clang corpus that is generated outside
the analyzer and ignored by Git:

```bash
make corpus-tools-check
make provisional-corpus-smoke
make provisional-corpus-build
make provisional-corpus-verify
```

The matrix covers `O0`/`O2`, requested non-PIE executable, PIE-style
executable, and shared-object roles, plus minimal and hardened profiles. The
builder retains source, license, specification, builder, compiler/linker,
command, environment, output, checksum, and bounded ELF facts. It never
executes a target and publishes only after late reauthentication, metadata
normalization, fsync, and `renameat2(RENAME_NOREPLACE)`.

Generated files live under `benchmarks/corpus/generated/` and are excluded from
normal public source bundles and Docker contexts. They are mutable diagnostic
evidence, not the Sprint 15-frozen corpus. See
[`corpus/README.md`](corpus/README.md).

## Sprint 11 Patch 057 diagnostic-integrity correction

Patch 057 makes the target execution boundary explicit. Tool and timer-probe
snapshots remain executable write-sealed memfds. Target snapshots require Linux
`MFD_NOEXEC_SEAL` plus `F_SEAL_EXEC`, remain mode `0444`, and are rejected when
the host cannot enforce that property. This prevents the measured command from
adding execute bits to, or directly executing, the passed target object. It is
not a general sandbox against a hostile tool copying bytes into a different
object.

Both the runner and corpus builder create staging trees inside their protected
transaction and remove them through checked file-descriptor-relative cleanup.
Cleanup failures are reported with the originating failure rather than hidden.
The corpus builder uses one otherwise-empty command workspace, accepts only the
named output after a successful compiler command, and verifies the exact final
member set. The Make clean target delegates to the manifest-aware builder and
never recursively deletes a caller-selected corpus path.

## Sprint 11 Patch 058 task-normalized baseline adapters

Validate the versioned baseline task authority and all three adapters with:

```bash
make diagnostic-task-definitions-smoke
make baseline-output-adapter-smoke
```

`benchmarks/scripts/baseline-output-adapter.py` consumes caller-supplied retained
native output; it does not invoke the baseline tool. Before parsing it reconciles
the supplied task command and authenticates the tool executable, target, retained
version-output file and declared version text, stdout, stderr, and adapter source
against the task authority. Native output remains the primary artifact. The
standalone adapter does not consume a runner row, campaign manifest, or execution
outcome, so a campaign must bind those inputs before treating a normalized
artifact as the result of a particular invocation.

The initial common relation is canonical `pop rdi; ret` over represented
instruction text; it does not decode target bytes. Tool-native totals,
unique-native totals, duplicate counts, return-terminated populations, and the
canonical exact relation remain separate. No normalized artifact contains an
unlabeled `gadget_count` field. Uncategorized or over-limit native output is a
failed diagnostic condition rather than a guessed zero result.

Patch 058 also moves runner and corpus output capture to bounded parent-owned
pipes, follows owned staging objects after same-parent renames, preserves
unrelated replacements, rechecks retained corpus limits, and records a completed
no-replace publication as committed when interruption follows the commit.

## Sprint 11 Patch 059 stage-zero measurement plane

Patch 059 upgrades the task authority to version 3 and makes baseline
normalization campaign-bound. The adapter now consumes one authenticated runner
manifest and row, verifies the child outcome plus retained tool, target, exact
version, stdout, and stderr objects, and preserves native records separately from
normalized relations. File hashes without that binding are not execution
provenance.

The matched x64lens relation extractor consumes the retained complete schema
`0.2.0` `gadgets` report. It does not rescan target bytes, parse ELF as runtime
authority, classify or score candidates, or modify analyzer facts. The extractor
preserves x64lens raw, exact, semantic, unknown, and scored populations while
emitting only the narrow represented `pop rdi; ret` relation and binary-presence
fact. Baseline native records, unique and duplicate records, return-terminator
sites, normalized relations, and binary presence remain separate, and baseline
raw executable-byte presence remains unavailable.

Address calibration uses manifest-bound `ET_EXEC`, PIE-intended `ET_DYN`, and
shared-object `ET_DYN` roles; `ET_DYN` alone is not PIE/DSO identity. Runtime
closure records a bounded observation of native dependencies or the retained
version-command path. `complete` means no unresolved dependency within that
observation, not a universal dependency guarantee.

```bash
make diagnostic-transaction-smoke
make sprint11-measurement-plane-smoke
make sprint11-campaign-plan-smoke
```

At the Patch 059 boundary, the 24-comparison plus six-control plan was
pre-execution authority. Patch 059 supplied no comparative performance, RSS,
coverage, or superiority result; Patch 060 and Patch 061 were the subsequent
campaign and closeout tranches recorded below.


## Sprint 11 Patch 060 cloud checkpoint

Patch 060 accounts for the complete 30-condition authority through
`benchmarks/scripts/sprint11-provisional-campaign.py`. Available authenticated
tools execute through the runner; absent optional baselines remain explicit
`unavailable_tool` conditions with zero native rows. The retained cloud
checkpoint executed 12 x64lens conditions and accounted for 18 unavailable
baseline conditions. It preserved 72 native rows—12 warmups and 60 measured
rows—while keeping condition accounting, primary-summary eligibility,
normalized relation artifacts, task-path runtime closures, address-coordinate
status, task-scoped summaries, and the engineering gap register separate.

All 60 measured rows were below the timer floor, leaving zero primary summary
rows. Six x64lens relation artifacts and two bounded x64lens task-path closure
artifacts were generated. Coordinate status remained unavailable, so cross-tool
address intersections remain blocked pending authenticated role-controlled
calibration.

```bash
make provisional-corpus-verify
make sprint11-p060-campaign-smoke
make bench-sprint11-provisional-campaign
```

Optional baselines are never substituted. Missing executables remain explicit
`unavailable_tool` conditions. Successful rows below the measured timer floor
remain `below_timer_floor`; they are not divided into synthetic per-run values.
The six selected targets are a diagnostic screen and cannot identify causal
compiler, optimization, linkage, or hardening effects. All Patch 060 artifacts
remain diagnostic, unfrozen, and publication-ineligible.


## Sprint 11 Patch 061 closeout and campaign operation

Patch 061 separates native execution, normalized comparison, runtime closure, and coordinate qualification. A successful process is not automatically a qualified cross-tool comparison. The campaign rejects recursive generic gadget-count fields, authenticates every imported generator, preserves isolated Python launcher context, rejects stale staging paths, and counts below-floor successful rows correctly.

A later, separately qualified WSL2 replay used the exact pinned baselines and,
after one narrow evidence-local correction to the ROPgadget 7.7 banner
authority, executed all 30 conditions, retained 180 successful process rows,
and generated 24 normalized relations. Seventeen conditions were above that
host's 6,361,100 ns reliable single-process floor and 13 were below it; all 12
x64lens conditions were below it. Two Python task-path closures and coordinate
calibration failed, so the replay was not comparison-qualified and does not
replace the fresh unmodified Patch 061 empirical campaign.

Use [`docs/sprints/sprint-11-diagnostic-campaign-guide.md`](../docs/sprints/sprint-11-diagnostic-campaign-guide.md) to install exact baselines, regenerate the corpus, run a new 30-condition campaign, verify the result tree, and interpret timer-floor, relation, coordinate, closure, and tool-native evidence. Sprint 11 is closed; all retained rows remain diagnostic, unfrozen, and publication-ineligible.

## Sprint 12 behavior-change boundary

Patch 062 changes accepted ELF loader structure rather than the measurement method. Sprint 11 diagnostic rows remain preserved, but new measurements after PHDR validity and extended-numbering enforcement require a distinct diagnostic campaign identity. They must not be merged with the Sprint 11 checkpoint or the later Sprint 15-frozen dataset.
