# ADR 0063: Patch 076 Correction and Sprint 12 Final Reconciliation

## Status

Recorded as the Patch 077 implementation decision. Patch 077 did not complete
acceptance; its review required Patch 078. Patch 078's review then required the
Patch 079 corrective and private task-value candidate, whose review required Patch 080.

## Context

Patch 076 completed the bounded private dynamic-metadata model for static text
relocation, `DT_RPATH`, and `DT_RUNPATH` evidence. Validation supported the
assembly-owned carrier and value facts, the 9,904-byte private dynamic context,
and the unchanged public schema boundary. It also found acceptance defects in
surrounding application, recovery, permission, custody, comparator, parity, and
evidence transactions.

Those defects do not justify another ELF parser tranche. They require a final
reconciliation patch that preserves the implemented private facts while making the
supporting transactions and oracles discriminating enough for closeout.

## Decision

Patch 077 was corrective and reconciliatory. It added no analyzer field, parser
family, CLI option, schema property, candidate population, semantic class, or
score rule.

The patch makes these decisions:

1. **Pinned patch bytes.** Apply and rollback use one bounded, authenticated
   patch byte sequence for both dry-run and mutation. Replacing the pathname
   after the check cannot redirect the transaction.
2. **Descriptor-bound source recovery.** Recovery traverses a real retained
   parent, extracts into a sibling staging root, authenticates every member and
   the derived Git tree, and publishes with no-replace rename. Failure cleanup
   preserves a foreign replacement rather than deleting by stale pathname.
3. **Retained-inode permission rollback.** Rollback applies to the opened file
   descriptor even when unrelated directory link counts change. File and parent
   replacement still fail closed.
4. **Custody cleanup preservation.** Manifest rollback quarantines with
   no-replace renames and verifies the retained inode before unlink. A foreign
   replacement is preserved and reported as a failed cleanup.
5. **Successful external comparator requirement.** Eligible GNU `readelf`
   agreement requires both valid output and process exit status zero.
6. **Deterministic private failure snapshots.** Malformed or unsupported
   dynamic metadata may retain only the deterministic parse prefix observed
   before failure. These private snapshots are diagnostic records, never public
   mitigation negatives or policy inputs.
7. **Git-independent parity source.** Dynamic-metadata parity derives one
   authenticated staged source tree without requiring `.git` in the container,
   builds native and container artifacts in separate writable copies, exposes
   neither the live repository nor completed native plane to the container, and
   publishes results with no-replace semantics.
8. **Host build isolation.** Docker test and validation targets use image-owned
   source and build outputs rather than overwriting the host native build tree.
9. **Closeout remains evidence-gated.** Patch 077 was a closeout candidate, not
   automatic Sprint 12 acceptance. Patch 078 was the Sprint 13 entry candidate
   and required correction. Patch 079 was the corrective and private task-value
   candidate; its review required Patch 080. Activation still requires complete
   acceptance against the exact Patch 080 source.

## Preserved architecture

Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable
authority. Mapping, ELF/loader parsing, dynamic metadata, scanner, exact
matcher, classifier, candidate side-cars, scoring, and reporters remain
separate. Raw, exact-suffix, semantic-exact, unknown, future decoder-backed,
and scored facts remain distinct.

The private dynamic context remains 9,904 bytes and the combined GNU-property
plus dynamic-metadata context remains 13,064 bytes. Mixed carriers and search
records remain capped at 64, exact search-path bytes remain capped at 4,096,
and candidate capacity remains 4,096. Capacity overflow and malformed input
continue to fail before partial stdout.

## Public boundary

Patch 077 retained tool version `0.1.0-dev` and schema `0.2.0`. It added no
public PIE/DSO, IBT, SHSTK, text-relocation, RPATH, or RUNPATH field. Static
property or dynamic metadata does not prove runtime CET enforcement, loader
path choice, path safety, vulnerability, or exploitability.

## Validation consequences

Acceptance requires:

- the Patch 076 corrective regression;
- the complete textrel and search-path matrices;
- exact C/NASM private-layout reconciliation;
- fresh native and Docker aggregates;
- fresh external-natural acquisition;
- corrected role/property and dynamic-metadata native/container parity;
- strict ShellCheck;
- exact package application, double-application rejection, rollback, and source
  recovery; and
- independent exact-source acceptance.

## Consequences

Sprint 12 may close with the public role/property and dynamic-metadata policies
still deferred. Patch 079 qualified three role facets only as private task-value
evidence and deferred `syscall_number` and `stack_pivot`; Patch 080 retained the
three qualified facets privately while deferring public and score projection. A
changed task definition still requires a new diagnostic campaign identity.
