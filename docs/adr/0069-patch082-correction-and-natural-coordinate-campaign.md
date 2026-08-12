# ADR 0069: Patch 082 Correction and Natural Coordinate Campaign

## Status

Accepted as the Patch 083 implementation decision; exact-source acceptance remains pending.

## Context

Patch 082 established a controlled coordinate-method preflight and a
three-generation producer authority. Review confirmed that the analyzer runtime
and public schema remained stable, but found localized defects in package
consistency, provisional-corpus `.PHONY` inspection, Docker run-root ownership,
transaction base/path binding, producer source/mode custody, and extreme-umask
source recovery. The controlled coordinate preflight also could not substitute
for natural tool-native evidence.

## Decision

Patch 083 combines the smallest cohesive correction with one new diagnostic
campaign:

1. Require the exact committed Patch 082 HEAD and tree before guarded patch
   application or rollback. A different commit with byte-identical tree content
   is not an accepted package base.
2. Retain patch bytes, repository roots, patch-path parents, and patch-path
   identities through the check-to-effect boundary. Status publication is part
   of the mutation transaction so a failed status write restores the prior
   exact state.
3. Parse every `.PHONY` declaration, including continued logical lines, before
   deciding whether corpus cleanup has the expected Make contract.
4. Make candidate-source staging usable under all conventional caller umasks by
   creating required traversal directories with an explicit initial mode and
   then applying manifest modes through retained descriptors.
5. Bind the three-generation producer authority to one caller-declared
   candidate tree and authenticate exact modes for the retained analyzer,
   fixtures, reports, source manifest, and build logs.
6. Keep `/work` as immutable Git-less source while all mutable container work
   uses the non-root-owned `${X64LENS_RUN_ROOT}` beneath ``${HOME}``.
7. Execute an outcome-blind natural coordinate campaign over twelve installed
   package objects: four `ET_EXEC`, four PIE-intended `ET_DYN`, and four
   shared-object `ET_DYN`, each from a distinct source-package lineage when the
   environment supplies the complete stratum.

## Natural selection and execution contract

The campaign enumerates the complete installed dpkg package/file universe,
filters regular non-symlink ELF64 little-endian x86_64 objects, derives roles
from authenticated GNU `readelf -hW -lW -dW` evidence, and freezes the complete
ordered eligible pool before any x64lens or baseline target outcome is read.

Selection is deterministic:

```text
role order
  -> source-package lineage byte order
  -> path byte order
  -> first object from each of the first four distinct lineages
```

There is no outcome-based target replacement. Missing packages, tools, role
strata, nonzero exits, parse failures, empty relations, ambiguous coordinates,
and mismatches remain explicit terminal evidence.

A complete stratum executes:

```text
12 targets
x 4 tools (x64lens, ROPgadget, Ropper, ropr)
= 48 target/tool processes
```

The nine baseline-by-role cells retain all four observations. A cell qualifies
only when the first two deterministic positive observations use distinct target
hashes, agree on virtual-address or file-offset coordinates, and no observation
is a mismatch or ambiguous. The campaign also executes twelve classifier
controls per cell, for 108 empty, ambiguous, and mismatch controls.

## Public boundary

Patch 083 adds no runtime record, semantic class, score, public field, schema
change, decoder, worker, or exploitability judgment. The natural campaign is
mutable diagnostic evidence and remains outside the Sprint 15-frozen campaign.
Coordinate qualification does not establish cross-tool coverage equivalence or
performance superiority.

## Consequences

- Package application now has one exact committed base instead of a same-tree
  compatibility shortcut.
- Docker validation can run as the configured non-root image user without
  writing beneath `/work` or attempting to recreate a root-owned path beneath
  `/`.
- Producer evidence can no longer be replayed against a foreign candidate tree
  or mode-mutated executable.
- The controlled preflight remains useful as a method oracle, while natural
  evidence receives a separate campaign identity and retained raw outputs.
- Public role projection, score changes, decoder integration, and concurrency
  remain separate evidence gates.
