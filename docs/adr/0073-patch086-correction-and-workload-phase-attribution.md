# ADR 0073: Patch 086 Correction and Workload/Phase Attribution Authority

## Status

Decision accepted for inclusion in the historical Patch 087 implementation
candidate. Patch 087 did not complete exact-source acceptance and was
superseded by Patch 088.

## Context

Patch 086 preserved the analyzer runtime while adding replay-v2 sealing and a
private ABI-role vector-equivalence result. It did not complete exact-source
acceptance because several acceptance surfaces remained incomplete:

- base and candidate states could be classified without authenticating changed-path hard-link topology;
- package wrappers retained a post-helper signal window;
- source-recovery and custody publication had effect-before-bookkeeping signal windows;
- replay runtime and Python distribution closures were not pinned tightly enough;
- the replay result omitted its selection-freeze summary;
- terminal attribution and ABI publication could leave or replace final artifacts;
- current ABI evidence was not bound to the Patch 086 candidate source; and
- the loose delivery checksum authority did not close.

The diagnostic portfolio also lacked a qualified workload and phase-attribution
authority. Existing single-process rows were below the reliable timer floor and
could not select an optimization.

## Decision

Patch 087 implements one cohesive corrective and measurement-design boundary:

1. Authenticate changed-path topology before classifying base, candidate, or already-applied states.
2. Execute package mutation helpers as the final wrapper process so no shell suffix can fail after a committed mutation.
3. Block catchable termination across source-recovery and custody filesystem effects plus their ownership bookkeeping.
4. Preserve pipx launcher identity while separately pinning the resolved Python interpreter and five exact package-root closures.
5. Require the replay result to retain the complete selection-freeze summary, isolated runtime policy, twelve target identities, forty-eight execution records, and ninety-six raw streams.
6. Publish terminal attribution and ABI evidence through complete-or-absent no-replace transactions.
7. Regenerate private ABI evidence from the exact Patch 087 candidate source authority.
8. Freeze an eight-fixture, two-profile workload and phase-attribution method over 160 planned executions without selecting any optimization.

The phase authority requires a retained median of at least five timer floors,
MAD/median no greater than 0.10, phase-sum residual no greater than 0.05,
instrumentation overhead no greater than 1.03, identical normalized public
output, and at least six qualifying fixtures. The private instrumentation budget
is 64 KiB.

## Preserved boundaries

Patch 087 changes no file under `src/`, `include/`, or `schemas/`. It adds no
public field, semantic class, score, decoder fact, concurrency profile, or
candidate-count change. Program headers and file-backed `PT_LOAD + PF_X` ranges
remain executable authority. Raw, exact-suffix, semantic-exact, unknown, future
decoder-backed, and scored facts remain distinct.

## Evidence classification

Replay, terminal-attribution, and ABI-vector artifacts remain private,
diagnostic, mutable, and publication-ineligible. The private workload/phase
authority is a frozen method, not an executed timing result. Even a later
qualified result may only motivate a separate bounded experiment; it does not
select an optimization or establish speed, RSS, comparative coverage, baseline
equivalence, exploitability, decoder, concurrency, or resource superiority.

## Consequences

Patch 087 did not complete its fresh native, strict-shell, Docker, producer,
replay, external-natural, parity, ABI, package, or independent acceptance gates.
Patch 089 carries the current acceptance boundary and keeps the paired
workload/phase authority frozen and unexecuted.
