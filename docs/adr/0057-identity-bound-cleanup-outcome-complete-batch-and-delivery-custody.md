# ADR 0057: Identity-Bound Cleanup, Outcome-Complete Batch Oracle, and Delivery Custody

## Status

Historical accepted architecture for the first Sprint 12 Patch 071 corrective
implementation candidate. Patch 071 changed development, validation, and
delivery tooling only, but its review required the remaining Patch 072
correction recorded by ADR 0058. Product acceptance remains subject to native
and Docker validation against the exact candidate source.

## Context

Post-candidate validation of Patch 070 reproduced four acceptance blockers:

1. nested cleanup could inspect an owned file or directory and later unlink a
   foreign replacement at the same name;
2. the batch authority did not authenticate every case outcome and its success
   banner contained a fixed failure-position count rather than an observed,
   authority-derived total;
3. the 4 KiB stdout and stderr limits were classified only after
   `communicate()` had buffered complete child output; and
4. prior source and evidence delivery trees were not recursively closed over
   every referenced member and could carry private state, host-absolute links,
   or local environment files.

Those defects invalidate Patch 070 acceptance even though its analyzer runtime,
private role/property facts, and controlled comparator results remain useful.
Beginning external-natural acquisition before correcting the evidence plane
would compound the custody and oracle defects.

## Decision

Patch 071 was the first cohesive corrective boundary.

### Identity-bound nested cleanup

`tools/remove-owned-tree.py` now moves every observed member to a unique
no-replace quarantine before opening or clearing it. Final deletion uses a
second no-replace quarantine and verifies the expected device, inode, and file
type after the move. A late file or directory replacement is restored when
possible, never deleted, and causes cleanup to fail closed. An authenticated
object that cannot be safely restored remains under a unique quarantine name
for inspection.

The UUID quarantine namespace is private to one helper invocation. A hostile
same-UID process that can predict and race those random names is outside this
helper's stated trust boundary; the helper makes no filesystem-sandbox claim.
Cleanup is destructive rather than transactional rollback. If a later step
fails, an authenticated tree can remain partially cleared and directory modes
can remain changed under quarantine. The guarantee is that an unproven late
replacement is preserved within the stated random-name trust boundary, not that
the original tree is reconstructed.

### Outcome-complete batch authority

The Patch 070 authority is superseded by
`sprint12-batch-transaction-pilot-v2`. The new authority records the complete
expected result for all 27 cases, including member modes, states, exit codes,
per-stream retained byte counts, failure index, unstarted suffix, batch outcome,
publication state, signal result, residue, and child survival.

The runner compares every observed record byte-semantically with that authority
on each of three repetitions. Summary values are derived from verified records:
three successful normal batches, sixteen failed normal batches, failure-index
counts of eight at index zero, four at index one, and four at index two, plus
eight signal cases.

### Streaming output caps

Child stdout and stderr are read nonblockingly through a selector. Each stream
retains at most `limit + 1` bytes. As soon as a stream reaches 4,097 bytes for a
4,096-byte cap, the runner sends `SIGKILL` to the child process group, waits for
the direct child, and classifies the member as `stdout_limit` or `stderr_limit`.
Timeout and output-limit records use a null exit code because the harness, not
ordinary child completion, determines the outcome. This boundary does not claim
group-wide descendant reaping.

### Exact recursive delivery custody

`tools/verify-delivery-custody.py` creates and verifies a recursive manifest of
regular files by canonical relative path, SHA-256, byte size, and mode, together
with exact implied-directory membership. Missing, extra, duplicate, unsafe,
symbolic-link, special, or undeclared empty-directory members fail closed.
Patch 071 source delivery must be generated from the exact Git candidate tree,
not from the live worktree or ignored evidence hierarchy, and then verified.
Conforming source archives exclude `.git`, `.local`, local environment files,
generated build output, and host-absolute symbolic links.

## Consequences

The runtime analyzer remains unchanged. Patch 071 adds no `src/`, `include/`,
CLI, JSON schema, candidate, score, mitigation, mapping, or reporting behavior.
Program headers remain executable authority; candidate capacity remains 4,096;
candidate 4,097 still fails with exit 6 before stdout; malformed parse failures
still emit no partial report; and the dependency-free, decoder-free, one-worker
reference profile remains intact.

Patch 071 is corrective and does not perform outcome-blind external-natural
role/property acquisition. The Sprint 12 sequence is:

- Patch 071: first corrective boundary for the confirmed Patch 070 blockers;
- Patch 072: remaining Patch 071 correction plus outcome-blind external-natural
  acquisition and the initial native/container private-fact parity protocol;
  its returned review rejected current acceptance;
- Patch 073: reported custody/isolation correction and non-reinterpretive
  public-policy deferral; and
- Patch 074: Sprint 12 closeout and Sprint 13 handoff.

The batch pilot remains transaction-conformance evidence. It is not a timing
result, and no batch elapsed time may be divided into a single-run latency.

## Rejected alternatives

- Accepting Patch 070 because nominal batch and cleanup cases passed.
- Adding natural objects while known cleanup, oracle, and delivery defects
  remained unresolved.
- Raising output limits enough to hide complete buffering.
- Retaining a count-only or success-banner-only batch oracle.
- Deleting a pathname after checking an earlier inode without an identity-bound
  final operation.
- Packaging the live repository, `.local` evidence tree, or local environment
  files as a portable source archive.
