# ADR 0045: Measurement Plane and Transaction Integrity

## Status

Implementation candidate for Sprint 11 Patch 059; empirical acceptance is
pending.

## Context

Patch 058 introduced task-normalized adapters for ROPgadget, Ropper, and ropr,
but the next diagnostic campaign needs stronger evidence binding than a
standalone parser can provide. A normalized relation is useful only when it is
bound to one authenticated runner row, the exact tool and target snapshots, the
retained version output, and the native stdout and stderr produced by that row.

Validation also identified transaction-boundary failures in the diagnostic
runner and provisional-corpus builder. Unsafe future member paths, stage
substitution, post-rename verification failure, repeated interruption, and
partial stage creation could otherwise modify unrelated objects, publish a
foreign tree, report success after failed authentication, or retain owned
residue.

The baseline comparison design also lacked three preconditions required for a
meaningful cross-tool experiment:

1. matched x64lens relation artifacts under the same narrow represented-text
   relation used for baseline adapters;
2. address-coordinate calibration across `ET_EXEC`, PIE-intended `ET_DYN`, and
   shared-object `ET_DYN` roles; and
3. runtime-closure identity for native and interpreted tools rather than only
   entrypoint hashes.

## Decision

Patch 059 establishes a stage-zero diagnostic measurement plane. It does not
execute the provisional comparative campaign, publish corpus-wide summaries, or
produce performance, RSS, coverage, or superiority evidence.

### Campaign-bound derived artifacts

All relation and provenance tools consume an authenticated Sprint 11 campaign
directory and one measured row. The shared helper:

- opens campaign members without following symlinks;
- rejects duplicate run, tool, and target identities;
- reconciles manifest, row, command, tool, target, version, and stream identity;
- reauthenticates selected inputs after processing; and
- publishes JSON through a same-directory no-replace transaction with
  post-commit authentication.

The standalone baseline adapter is upgraded to this campaign-bound interface.
It preserves native output, native instruction text, duplicate records, and the
canonicalized relation separately. Raw line limits apply before ANSI removal.
Version evidence is compared as one exact trimmed first line under a
baseline-specific syntax rule.

Baseline native and unique records, duplicate records, return-terminator records
and sites, canonical normalized records and relations, and binary presence
remain distinct. None is renamed to a generic cross-tool `gadget_count`.

### Matched x64lens relation artifact

The x64lens relation extractor consumes the retained complete schema `0.2.0`
report from a successful measured `gadgets` row. It preserves the report's raw,
exact, semantic, unknown, and scored populations and emits only the current
narrow relations:

```text
canonical_exact_pop_rdi_ret
binary_fact_arg_control_rdi_present
```

Each relation carries both virtual-address and file-offset start and terminator
coordinates. The extractor does not rescan target bytes, parse ELF as runtime
authority, create or classify candidates, assign scores, alter runtime JSON, or
reinterpret analyzer facts.

### Address-coordinate calibration

The coordinate calibrator requires one controlled target for each role:

```text
ET_EXEC
PIE-intended ET_DYN
shared-object ET_DYN
```

It compares baseline displayed addresses with matched x64lens virtual-address
and file-offset coordinates. Outcomes remain explicit:

```text
virtual_address
file_offset
ambiguous
mismatch
insufficient_relation_evidence
```

No cross-tool address intersection is generated before role-specific
calibration succeeds. Role identity comes from the verified provisional-corpus
manifest and recorded build intent; `ET_DYN` alone does not distinguish a PIE
executable from a shared object.

### Runtime-closure provenance

The runtime-closure generator records one of these bounded modes:

```text
native_elf
python_console_entrypoint
script_interpreter
```

For native ELF tools it records the interpreter and bounded recursive
`DT_NEEDED` closure using authenticated platform tools. For Python entrypoints it
observes the retained version command under the declared interpreter and records
imported modules, installed distributions, extension modules, and mapped native
libraries. Closure state is `complete` or `partial`; unresolved dependencies
remain visible. `complete` means that no dependency was unresolved within the
bounded observation. It is not a universal dependency guarantee, and the
observed Python version-command path may be narrower than a later analysis
command.

### Corrected provisional campaign plan

The maintained pre-execution plan selects six provisional targets, two per ELF
role, balanced across GCC/Clang, `O0`/`O2`, and minimal/hardened profiles. It
requires:

```text
24 comparative conditions
  6 targets × (x64lens gadgets + ROPgadget + Ropper + ropr)

6 separate x64lens analyze controls

30 accounted conditions total
```

A baseline-only campaign is invalid. The six integrated-analysis controls do not
enter gadget-report comparisons.

### Transaction ownership

The runner and corpus builder now treat stage creation, child execution,
publication, and cleanup as one owned transaction:

- future output members are created exclusively through checked parent-owned
  paths;
- symlink and special-file substitutions fail before external objects are
  modified;
- cleanup follows the owned stage by device and inode after a rename;
- foreign replacements are preserved rather than deleted;
- post-rename verification failure remains failure;
- repeated signals retain the first interruption identity and cannot bypass
  cleanup;
- an interruption delivered while stage ownership is being registered is
  deferred until the creation-time device/inode record is available; and
- partial stage creation is removed or reported as a cleanup failure.

Corpus verification also rejects duplicate authenticated tool records.

## Consequences

### Positive

- Normalized output can be traced to one measured execution rather than a set of
  caller-supplied files.
- x64lens and baseline relations use the same narrow comparison vocabulary.
- Address coordinates are calibrated instead of assumed.
- Python and native dependency surfaces are measurable diagnostic facts.
- Transaction failures cannot be converted into success solely because a final
  path exists.
- A 24-condition comparative design plus six controls is fixed before tool
  installation and execution.

### Costs and limitations

- The stage-zero smoke is intentionally small and does not produce a performance
  or coverage conclusion.
- Runtime closure is an observed bounded closure and may be partial.
- Represented baseline instruction text is not decoded target-byte truth.
- Address calibration may remain mismatch or insufficient evidence.
- Target nonexecution protects the supplied target object; it is not a sandbox
  for a hostile same-UID tool.
- The corpus-wide campaign, generated summaries, and engineering gap register
  move to planned Patch 060 so they are built on the corrected plane. Planned
  Patch 061 owns Sprint 11 closeout.

## Rejected alternatives

### Continue directly to summaries

Rejected because unbound adapter artifacts and uncalibrated address coordinates
could make precise-looking but unsupported comparison tables.

### Treat entrypoint hashes as complete runtime identity

Rejected for Python tools and dynamically linked native executables because the
entrypoint does not identify imported packages, extension modules,
interpreters, or native libraries.

### Compare a generic gadget count

Rejected because x64lens and the baseline tools expose different discovery,
duplicate, canonicalization, and work-scope populations.

### Make a decoder or concurrency profile mandatory

Rejected. Patch 059 changes development evidence infrastructure only. The
bounded dependency-free one-worker analyzer remains the reference profile.

## Validation

Focused validation includes:

```bash
make diagnostic-runner-smoke
make diagnostic-transaction-smoke
make provisional-corpus-smoke
make diagnostic-task-definitions-smoke
make baseline-output-adapter-smoke
make sprint11-measurement-plane-smoke
make sprint11-campaign-plan-smoke
```

The complete native, strict ShellCheck, Docker, capacity, malformed-input, and
native/container parity gates remain required before acceptance.
