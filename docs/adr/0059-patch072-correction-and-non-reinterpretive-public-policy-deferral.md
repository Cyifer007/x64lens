# ADR 0059: Patch 072 Correction and Non-Reinterpretive Public-Policy Deferral

## Status

Accepted as the design record for the Sprint 12 Patch 073 implementation
candidate. Patch 073 was not accepted at its first returned review boundary; it
delivered the first custody/isolation correction and the non-reinterpretive
policy deferral. Patch 074 was the superseded Sprint 12 closeout candidate.
Patch 075 introduced bounded private static text-relocation evidence. Patch 076
preserved that private prefix and implemented distinct private `DT_RPATH` and
`DT_RUNPATH` carrier/value evidence, but its review required the Patch 077
correction. Patch 077 is the current final Sprint 12 reconciliation candidate,
pending complete acceptance. Current validation expectations are in the
[Patch 077 validation record](../sprints/sprint-12-patch-077-validation.md).

## Context

Patch 072 preserved the private binary-role and GNU-property fact model, added
outcome-blind external-natural acquisition, and introduced a same-byte
native/container parity protocol. Review confirmed that this direction remains
architecturally valid, but it also reproduced seven material acceptance gaps:

- cleanup could delete a pathname replacement after its last fingerprint;
- the frozen external-natural selection could change before outcome collection;
- delivery custody omitted root, directory, and manifest modes;
- delivery hashing did not bind metadata, bytes, and the final pathname to one
  retained descriptor;
- the container received write access to the parent that held the completed
  native evidence plane;
- default acquisition and parity paths did not retain their complete raw result
  planes; and
- the loose delivery omitted required public records.

The policy review also established that the available diagnostic evidence does
not justify a new public PIE-versus-DSO, IBT, or SHSTK field. The existing
`mitigations.pie` Boolean remains the coarse `ET_DYN` indicator described by the
current schema. Static GNU property notes remain static evidence and do not
establish runtime CET enablement or enforcement.

## Decision

Patch 073 is the first custody/isolation correction and policy-decision tranche.

### Evidence and custody correction

- Cleanup performs its final generation-qualified descriptor recheck after the
  controlled adversarial hook and retains that descriptor through the private
  libc `unlinkat` call. Linux still has no atomic compare-and-unlink primitive,
  so the remaining external same-UID race is documented rather than hidden.
- External-natural acquisition makes the selected object identities, candidate
  inventory, final selection, and freeze manifest read-only, then reauthenticates
  all of them before authority loading, before every object outcome, and after
  all outcomes.
- Delivery custody schema v2 authenticates root mode, manifest path and mode,
  every directory path and mode, and every regular file path, SHA-256, size, and
  mode. Files are hashed through the same retained descriptor whose metadata is
  checked, followed by a pathname identity check.
- Native/container parity gives the container one dedicated empty write root for
  its own plane only. The completed native plane is not mounted into the
  container. Inputs, held-out objects, both planes, the comparison, and the run
  manifest are retained and recursively sealed.
- The authoritative Make targets require retained result directories rather
  than deleting successful external-natural or parity planes.

### Public-policy result

The tracked policy authority executes a non-reinterpretive decision of
`defer`. It authenticates the current schema and reporter sources, proves that
no new role/property field or label was introduced, preserves the existing
coarse PIE field, and rejects authorization while any required prerequisite is
not exactly `passed`.

No public PIE/DSO, IBT, SHSTK, text-relocation, RPATH, or RUNPATH field is added
in Patch 073.

The open prerequisites are corrected isolated native/container parity in a
qualified environment, build-origin separation, held-out consumer task value,
and schema/default-output compatibility. Controlled and external-natural facts
remain diagnostic rather than being promoted into public policy.

### Competitive mitigation gap

Patch 073 also records the next bounded mitigation families without adding an
untested runtime field. The next selected tranche is:

1. text-relocation evidence from `DT_TEXTREL` or `DT_FLAGS & DF_TEXTREL`; and
2. separate validated `DT_RPATH` and `DT_RUNPATH` indicators.

Patch 075 implemented the first item as private static evidence, but its review
required correction. Patch 076 implements distinct private `DT_RPATH` and
`DT_RUNPATH` carrier/value evidence for the second item.

Each requires checked acquisition, malformed and contradiction fixtures,
focused/integrated report parity, external reconciliation, and a compatible
schema review. A fortify-source indicator remains later because it requires a
bounded dynamic-symbol view and cannot be inferred from arbitrary string-table
substrings.

## Consequences

- `src/`, `include/`, the public JSON schema, CLI syntax, candidate counts,
  capacity behavior, and analyzer output remain unchanged in Patch 073.
- Program headers remain executable authority, and private role/property facts
  remain outside the candidate provenance tiers and public report schema.
- Passing the portable Patch 073 gates supports the source-level correction and
  policy decision, but not actual native/container parity or current
  acceptance.
- Patch 074 was the superseded Sprint 12 closeout candidate. Patch 075
  introduced private static text-relocation evidence, and Patch 076 added
  distinct private RPATH/RUNPATH evidence. Patch 076's review required the
  Patch 077 correction. Complete Patch 077 acceptance remains pending.
- Public role/property fields remain a future evidence gate rather than a
  calendar commitment.

## Validation

```bash
make patch072-corrective-regression-smoke
make sprint12-role-property-public-policy-smoke
make sprint12-mitigation-competitive-gap-smoke
make validation-smoke
make sprint12-p073-acceptance-smoke
```

The last command is the complete local gate and therefore requires the retained
external-natural acquisition and corrected Docker parity environments.
