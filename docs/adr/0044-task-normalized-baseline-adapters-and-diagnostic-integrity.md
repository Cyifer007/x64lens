# ADR 0044: Task-Normalized Baseline Adapters and Diagnostic Integrity

## Status

Implementation candidate for Sprint 11 Patch 058; empirical acceptance is
pending.

## Context

Patch 055 introduced the high-resolution diagnostic runner, Patch 056 added the
provisional compiler matrix, and Patch 057 strengthened target nonexecution,
corpus membership, cleanup, and publication behavior. Subsequent validation
found additional evidence-integrity gaps in the development tooling:

- retained output and log limits were not fully reauthenticated;
- a staging directory renamed during cleanup could escape ownership tracking;
- a future capture path could be replaced with a symbolic link before opening;
- early interruption and post-publication signal windows were not represented
  precisely; and
- corpus negative tests did not always inspect the corpus identifier used by the
  probe.

The Sprint 11 task authority also still described ROPgadget, Ropper, and ropr as
planned conditions. Measuring their native output without explicit adapters
would collapse incompatible candidate definitions into an ambiguous count.

## Decision

Patch 058 completes the next diagnostic tranche in two parts.

### Evidence-integrity correction

Runner and corpus staging objects retain creation-time device and inode
identity. Cleanup follows the owned object after a same-parent rename and
preserves any unrelated replacement at the original pathname. Signal handlers
are installed before staging creation, ordinary termination signals are deferred
across commit transitions, and a completed no-replace publication is reported as
committed even when an interruption arrives immediately afterward.

The diagnostic runner captures child stdout and stderr through parent-owned,
nonblocking pipes with explicit per-stream limits. It does not pre-open future
result paths. Exceeding a limit terminates and reaps the measured process tree,
retains a failed row with `output_limit` outcome, and preserves exactly the
configured prefix. Corpus compiler capture uses the same bounded-parent model.
Later corpus verification rechecks the retained maximum output and log limits in
addition to hashes, modes, and membership.

### Versioned baseline adapters

Patch 058 adds one standard-library adapter implementation for three declared
baseline identities:

```text
ROPgadget
Ropper
ropr
```

The adapter consumes retained native stdout and stderr after execution. It does
not invoke a baseline tool, select executable regions, reinterpret target bytes,
or mutate x64lens analysis facts. Before normalization it authenticates:

- the task-authority file and condition identifier;
- the exact command against the versioned command template;
- tool executable path, mode, SHA-256, and retained version evidence;
- target path, mode, and SHA-256;
- native stdout and stderr path, size, and SHA-256; and
- adapter identity and source SHA-256.

After parsing and artifact construction, every retained path and the command
working directory are reauthenticated. A late replacement therefore fails the
normalization transaction instead of leaving an artifact bound only to stale
in-memory bytes.

Native output remains the primary baseline artifact. The normalized artifact
adds only explicitly named, task-scoped relations:

```text
tool_native_record_count
unique_tool_native_record_count
tool_reported_return_terminator_record_count
unique_tool_reported_return_terminator_site_count
canonical_exact_pop_rdi_ret_record_count
unique_canonical_exact_pop_rdi_ret_relation_count
binary_fact_arg_control_rdi_present
```

No field is named `gadget_count`. Baseline totals remain tool-specific until the
Sprint 15 task authority and Sprint 17 coverage reconciliation freeze their
meaning.

The external baselines do not expose the loader-authoritative raw executable-byte
observation represented by x64lens raw scanning. That cross-tool relation is
therefore explicitly unavailable and cannot be substituted with decoder-backed
baseline output. The implemented common relations begin at retained
return-terminated records and the exact `pop rdi; ret` relation.

### Conservative parser policy

The adapter rejects rather than guesses when native output contains:

- invalid UTF-8 after bounded ANSI-sequence removal;
- an uncategorized non-record line;
- an address-bearing sequence outside the return-terminated task;
- an unrecognized command or condition;
- stale version, tool, target, or native-output identity;
- an over-limit retained stream; or
- an unsafe input or output filesystem object.

The parser also caps each line, record count, instruction count, retained stream,
and address width. The controlled fixtures establish exact `pop rdi; ret`
precision and recall for the represented syntax, including late-input mutation
rejection. They do not establish universal baseline-parser coverage.

## Architecture boundary

The adapters are development and research infrastructure outside the x64lens
runtime. They do not change:

- program-header executable authority;
- raw, exact, semantic-exact, unknown, decoder-backed, or scored facts;
- analyzer CLI or schema `0.2.0`;
- candidate capacity or the 819,200-byte command arena;
- decoder or worker policy; or
- the dependency-free one-worker reference artifact.

Baseline tools remain trusted measurement participants. Their output is external
evidence, not runtime classification authority.

## Consequences

### Positive

- Baseline commands and native artifacts are authenticated before parsing.
- Output limits apply during capture and again during later verification.
- Tool-specific totals cannot silently become an unlabeled cross-tool metric.
- Duplicate native records and canonical exact relations remain separately
  visible.
- Parser disagreement is retained as a failed diagnostic condition instead of a
  guessed normal result.
- The next diagnostic campaign can measure all declared baseline tasks without
  adding a runtime dependency to x64lens.

### Costs and limitations

- Baseline adapters are version-sensitive and must be reevaluated when native
  syntax changes.
- The initial common relation is intentionally narrow: exact `pop rdi; ret`.
- The adapters do not make ROPgadget, Ropper, and ropr task-equivalent to
  x64lens; they make the remaining differences explicit.
- Sprint 11 results remain diagnostic, mutable, unfrozen, and ineligible for
  publication claims.

## Rejected alternatives

- **Parse baseline text directly inside the timing runner:** rejected because it
  couples measurement, normalization, and failure interpretation.
- **Use one generic total:** rejected because each tool has different alignment,
  depth, filtering, duplicate, and canonicalization rules.
- **Discard duplicate records before retention:** rejected because native
  duplicate behavior is part of the task evidence.
- **Treat parser failures as zero coverage:** rejected because absence of parsed
  records is not evidence of absence in the native output.
- **Add baseline libraries to the runtime:** rejected because comparison tools
  are optional research dependencies and must not alter the reference product
  profile.
