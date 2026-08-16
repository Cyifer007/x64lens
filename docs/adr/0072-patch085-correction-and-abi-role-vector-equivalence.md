# ADR 0072: Patch 085 Correction and Private ABI-Role Vector Equivalence

## Status

Decision accepted for inclusion in the historical Patch 086 implementation
candidate. Patch 086 did not complete exact-source acceptance; Patch 087 is the
current implementation candidate.

## Context

Patch 085 preserved the analyzer runtime while adding frozen-target replay and
layered terminal-attribution authorities. The active Make path supplied replay
output to an input-oriented consumer, raw replay members were not fully
authenticated by the attribution gate, the expected terminal result was
optional, and several denominator fields were trusted rather than recomputed.
The correction also covers hard-link topology and catchable-signal recovery
gaps in the patch, source-recovery, and delivery-custody helpers.

No evidence authorized public role fields or score changes. The next bounded
Sprint 13 experiment was a private equivalence check over the candidate-role
side-car.

## Decision

Patch 086 implements one cohesive correction and experiment boundary:

1. Bind the Patch 085 acceptance aggregate to the exact Patch 085 tree.
2. Add a versioned replay result that seals the 12 selected targets, 48 execution records, 96 raw streams, tool/runtime identities, isolated HOME/cache policy, selection freeze, and complete checksum membership.
3. Require exact terminal-attribution expectations and recompute every execution, relation, observation, cell, and control denominator.
4. Honor the caller-supplied ABI expected-result authority.
5. Treat added hard-link aliases as a recoverable topology violation: detach only the patch pathname, preserve the foreign alias and its bytes, and restore the authenticated tree.
6. Convert HUP, INT, and TERM into recoverable exceptions during patch, source-recovery, and custody-publication transactions. Uncatchable termination remains outside the contract.
7. Add a fixture-derived private ABI-role vector oracle that does not reuse the production role tables. It exercises 48 internal dispositions and compares every occupied candidate index across 24 controlled targets, while retaining 36 role queries and 96 unchanged-public closures.

## Preserved boundaries

Patch 086 changes no file under `src/`, `include/`, or `schemas/`. It adds no public field, semantic class, score, decoder fact, concurrency profile, or candidate-count change. Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable authority. Raw, exact-suffix, semantic-exact, unknown, future decoder-backed, and scored facts remain distinct.

## Evidence classification

The replay and ABI-role vector results are private diagnostic evidence. They do not authorize comparative coverage, performance, RSS, exploitability, or publication claims. The replay permits no target reroll, and terminal-state drift is a failed expected-result gate rather than a reason to weaken the oracle.

## Consequences

Patch 086 may proceed to local NASM, ShellCheck, Docker, producer, replay, external-natural, and native/container parity validation. Public role projection and score changes remain deferred. Later Sprint 13 work must select another bounded evidence-backed consumer or family rather than treating equivalence alone as new user-facing utility.
