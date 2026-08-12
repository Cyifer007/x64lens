# Sprint 12 Patch 063 Validation

## Status

Historical record for the exact Patch 063 source. Its 33-fixture/132-execution
PHDR banner and four rejected mapping cases apply only to that source boundary.
Patch 064 expands the same gates to 49 fixtures/196 executions and nine rejected
mapping cases, but did not pass validation. Use the
[Patch 064 validation record](sprint-12-patch-064-validation.md) for that
intermediate boundary, the
[Patch 065 validation record](sprint-12-patch-065-validation.md) for the next
historical boundary, and the
[Patch 066 validation plan](sprint-12-patch-066-validation.md) for a subsequent
historical boundary, the
[Patch 067 validation plan](sprint-12-patch-067-validation.md) for the next
historical boundary, and the
[Patch 068 validation plan](sprint-12-patch-068-validation.md) for the next
historical boundary. The
[Patch 069 validation plan](sprint-12-patch-069-validation.md) preserves the final
pre-Patch-070 historical candidate boundary. Patch 070 was rejected after
acceptance validation. Patches 070, 071, 072, and 073 were not accepted at their
respective first returned review boundaries. Patch 073 delivered the first
custody/isolation correction and policy deferral. Patch 074 was a superseded
Sprint 12 closeout candidate. Patch 075 introduced bounded private static
text-relocation evidence, and Patch 076 implemented distinct private `DT_RPATH`
and `DT_RUNPATH` carrier/value evidence. Patch 076 was superseded by Patch 077.
Patch 077 was superseded by Patch 078, whose review required the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080. Use the
[Patch 083 validation record](sprint-13-patch-083-validation.md) for current
validation expectations; the
[Patch 073 validation record](sprint-12-patch-073-validation.md) preserves the
first custody/isolation correction and policy-deferral boundary; the
[Patch 071 validation record](sprint-12-patch-071-validation.md) preserves its
historical boundary; the
[Patch 070 validation record](sprint-12-patch-070-validation.md) preserves the
rejected boundary.

## Purpose

Patch 063 addresses the confirmed Patch 062 parser, transaction, and Make
validation defects, then adds the internal executable-overlap
provenance seam required before any scan/deduplication policy changes.

## Source boundary

Patch 063 is generated against exact Patch 062 commit:

```text
7c45022bf2857eca12515d1cd5d12ce331319ce5
```

Until the gates below pass, this document records required outcomes rather than
an acceptance result.

The patch changes no public command, exit-code meaning, schema field, semantic
class, score, decoder profile, worker profile, or candidate limit.

## Corrective requirements

- zero PHDR count requires both zero entrypoint and zero `e_phoff`;
- an ordinary section table, when present, has a canonical all-zero `SHT_NULL`
  entry zero;
- extended-numbering section zero rejects noncanonical common fields and
  inactive carriers;
- invalid runner specifications release all authenticated descriptors;
- runner, corpus, and derived-artifact cleanup cannot remove a
  substituted foreign object;
- corpus publication retains authenticated output-root descriptor authority;
- a clean validation aggregate builds a missing standard corpus before use;
- permission normalization does not mutate authenticated generated evidence;

## Overlap-provenance requirements

- `executable_region` remains 64 bytes and retains the original PHDR index;
- `candidate_evidence_record` is 56 bytes and carries one 64-bit dense-region
  contributor mask;
- fixed candidate capacity remains 4,096;
- fixed command arena becomes 851,968 bytes;
- same-slope overlaps may contribute together;
- different-slope mappings are not conflated;
- valid zero-region/zero-candidate analysis remains successful;
- no normalization, deduplication, public count, or schema change occurs.

## Focused commands

```bash
make patch062-corrective-regression-smoke
make sprint12-phdr-validity-smoke
make sprint12-overlap-provenance-smoke
make diagnostic-runner-smoke
make diagnostic-transaction-smoke
make provisional-corpus-smoke
make provisional-corpus-ready
make provisional-corpus-repair-modes  # only for authenticated mode-only drift
```

Expected focused banners:

```text
patch062-corrective-regression-smoke: ok fd_lifetime=20 cleanup_cas=3 output_root_continuity=1 mode_repair=1 aggregate_readiness=1 authenticated_modes=1
sprint12-phdr-validity-smoke: ok cases=33 executions=132 ordinary_valid=5 ordinary_malformed=9 extended_unsupported=3 extended_malformed=16
sprint12-overlap-provenance-smoke: ok phdr_indexes=5 dense_masks=1 empty=1 rejected=4 region_stride=64 evidence_stride=56
```

## Full native acceptance

```bash
make normalize-perms
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make section-label-smoke
make readelf-comparison-smoke
make system-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

## Docker and parity acceptance

Record the selected Docker context and daemon before execution. Native Ubuntu
Docker and Docker Desktop are separate environment strata.

```bash
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

## Strace troubleshooting probe

Use a real controlled fixture, not a literal placeholder:

```bash
strace -f -e trace=openat,mmap,mprotect,munmap,close,write \
  ./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/minimal_nopie
```

## Acceptance boundary

Patch 063 is acceptable only when the new assembly is built and all focused,
native, Docker, capacity, malformed-input, no-partial-output, and parity gates
pass. Static review and analyzer runs from earlier patches do not validate the
new PHDR or overlap implementation.
