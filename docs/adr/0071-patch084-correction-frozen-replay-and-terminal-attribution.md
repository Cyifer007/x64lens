# ADR 0071: Patch 084 Correction, Frozen-Input Replay Authority, and Terminal Attribution

## Status

Accepted as the Patch 085 implementation decision. Product acceptance remains
subject to the exact-source native, Docker, parity, replay, producer, delivery,
and independent validation gates.

## Context

Patch 084 preserved a complete 12-target natural-coordinate campaign and froze
private ABI-role and lifecycle authorities without changing analyzer runtime
behavior. Patch 084 did not complete acceptance: bounded defects remained in Git-less
source custody, source recovery, fixed-tree acceptance, ABI query isolation and
publication, natural-campaign target/result authentication, lifecycle-floor
validation, and delivery evidence.

The retained natural campaign is structurally complete but comparison-
unqualified:

```text
targets:      12
executions:   48
cells:         9
controls:    108
qualified:     0
insufficient:  5
unavailable:   4
```

The next strategic step must reuse those exact target hashes without rerolling
and must retain unsupported and unavailable outcomes rather than replacing them
with favorable inputs.

## Decision

Patch 085 is a runtime-neutral correction and evidence patch. Source, recovery,
exact-tree, ABI, lifecycle, and delivery changes harden existing validation
authorities. Frozen-input replay and layered terminal attribution are its only
new evidence authorities.

### Source and recovery custody

Git-less source verification authenticates full mode, link-count, ownership,
size, mtime, and ctime identity before and after hashing. Candidate-source
recovery removes an empty staging root when the first descriptor open fails and
rechecks file topology and metadata after every final hash.

### Exact acceptance authority

Historical Patch 082, Patch 083, and Patch 084 aggregate targets carry their
exact candidate-tree authorities. Producer, natural-campaign, ABI, and Docker
entry points require an explicitly supplied authenticated tree and do not fall
back to the caller's current index tree.

### ABI-role evidence

The private ABI contract verifies semantic disjointness between 24 development
and 12 confirmation queries. Its 96 disabled-output unchanged-public command
closures require a pinned analyzer copy, target reauthentication before and after
each command, and no-replace evidence publication when the closure runs.

### Lifecycle evidence

All 24 denominator floors are enforced. Patch 084 is represented by an explicit
zero-count successor delta. Event 88 and new canonical identities remain
unauthorized.

### Natural replay and attribution

Patch 085 defines a frozen-input authority over the exact predecessor targets and
five retained tool identities: GNU `readelf` and four execution tools. Each
execution tool runs once per target, yielding 48 no-reroll slots. Actual replay remains
pending. Any replay output remains diagnostic, `frozen=false`, and publication-
ineligible; Sprint 15 remains the confirmatory campaign freeze.

Terminal attribution is layered rather than flattened:

```text
execution outcomes: 48
relation outcomes:  48
observations:        36
cells:                9
```

Execution precedence is:

```text
timeout
output_limit
signal
success
unsupported
nonzero_exit
```

Each applicable record receives exactly one reason at its own layer. A single
output-limit reason is used unless a future replay retains additional limited-
stream evidence.

## Preserved boundaries

Patch 085 changes no tracked file under `src/`, `include/`, or `schemas/`. It
adds no public field, semantic class, score, decoder profile, worker profile, or
capacity change. Program headers and file-backed `PT_LOAD + PF_X` ranges remain
executable authority. Raw, exact-suffix, semantic-exact, unknown, future
decoder-backed, and scored facts remain separate.

## Consequences

- The exact frozen-input replay can fail or remain unavailable without target
  replacement.
- Terminal outcomes become more interpretable without becoming favorable
  comparison evidence.
- Docker and exact-source acceptance require one externally authenticated candidate
  tree.
- The retained natural campaign still authorizes no coverage, performance, RSS,
  exploitability, public-role, decoder, or concurrency claim.
