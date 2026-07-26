# ADR 0049: Executable-Overlap Provenance Seam Before Normalization

## Status

Accepted for Sprint 12 Patch 063.

## Context

ELF64 permits multiple executable `PT_LOAD` program headers whose file-backed
ranges overlap. The existing scanner receives one bounded `executable_region`
record per executable program header and therefore may revisit the same file
bytes. Before x64lens can normalize, deduplicate, or redefine region and
candidate counts, it needs durable internal facts that identify which original
program headers justify each retained candidate.

A direct normalization change in Patch 063 would be premature. It could alter
candidate populations, capacity behavior, ordering, benchmark denominators, and
public reports before the project has measured same-slope and different-slope
overlap cases. Sprint 12 therefore separates provenance from policy.

## Decision

Patch 063 adds an internal-only overlap-provenance seam:

1. Each 64-byte `executable_region` retains the original program-header index
   in existing padding. The existing internal region stride does not grow.
2. Each candidate-evidence record gains one 64-bit dense-region contributor
   mask. Bit `N` names executable-region slot `N`; it does not encode the
   original program-header index.
3. A new `candidate_mapping.asm` materializer runs after candidate provenance
   and before memory/architectural effects. It reconciles the complete retained
   candidate window and terminator virtual address against every loader-derived
   executable region.
4. Same-slope overlapping mappings may contribute multiple dense bits. A
   different file-to-virtual slope does not contribute to a candidate whose
   retained virtual address disagrees.
5. A nonempty candidate set without at least one justified contributor fails
   closed as an internal bounds contradiction. A valid empty analysis remains
   successful.
6. The current scanner still visits the existing region list. Patch 063 does
   not merge regions, deduplicate candidates, change candidate order, change
   public counts, or emit the contributor mask in schema `0.2.0`.

The fixed candidate capacity remains 4,096. Growing the evidence record from 48
to 56 bytes increases the fixed command arena from 819,200 to 851,968 bytes.
This is allocation arithmetic, not measured RSS.

## Alternatives considered

### Normalize executable byte unions immediately

Rejected for Patch 063. The policy would change scan work and candidate/count
semantics before positive overlap fixtures and diagnostic measurements establish
which representation is least misleading.

### Store only the original program-header index per candidate

Rejected. One candidate can be justified by more than one same-slope mapping.
A single index would lose contributing provenance.

### Use a 64-bit original-PHDR mask

Rejected. ELF program-header indexes are not limited to 64. Dense executable
region slots are bounded at 64, while each region separately retains its
original bounded ordinary PHDR index.

## Consequences

Positive:

- overlap evidence becomes reviewable before policy changes;
- original PHDR identity survives region compaction;
- same-slope and different-slope mappings can be distinguished;
- scanner, classifier, scoring, and reporting contracts remain unchanged;
- later normalization can be measured against the existing one-region-per-PHDR
  reference behavior.

Costs and limits:

- the fixed arena grows by 32,768 bytes;
- the contributor mask is internal and limited to the existing 64-region bound;
- current candidate counts may still reflect repeated scan work until the later
  normalization decision;
- no PIE/DSO, GNU-property, decoder, or concurrency conclusion follows from the
  new provenance.

## Validation

`make sprint12-overlap-provenance-smoke` validates:

- original PHDR indexes `0`, `63`, `64`, `255`, and `65533`;
- unchanged 64-byte executable-region stride;
- one valid empty analysis;
- same-slope multi-contributor masks;
- different-slope exclusion;
- fail-closed region, candidate-capacity, and sentinel-index contradictions.

The normal malformed, capacity, native, Docker, and native/container parity
contracts remain required.

## Next decision

A later Sprint 12 patch may define executable-byte-union normalization,
deduplication, public region counts, and contributing-PHDR reporting only after
controlled overlap fixtures and diagnostic evidence compare the available
policies.
