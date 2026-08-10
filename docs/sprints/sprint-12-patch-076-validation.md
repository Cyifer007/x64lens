# Sprint 12 Patch 076 Validation

## Scope

Patch 076 corrects the remaining Patch 075 transaction, oracle, recovery,
parity, and loose-delivery findings. It extends the existing private dynamic-
metadata side-car with distinct bounded `DT_RPATH` and `DT_RUNPATH` carrier and
exact-value evidence. No CLI option, public report field, schema revision,
executable mapping rule, gadget population, or score changes.

## Source boundary

The guarded package applies only to the exact committed Patch 075 base recorded
in the delivery source-identity authority. Application refuses a dirty tree, a
wrong branch/base/tree, a second application, or a result that does not match
the recorded Patch 076 candidate tree.

## Focused validation

```bash
make patch075-corrective-regression-smoke
make sprint12-dynamic-metadata-layout-smoke
make sprint12-textrel-smoke
make sprint12-search-path-smoke
make sprint12-continuation-smoke
```

Expected high-level results:

```text
patch075-corrective-regression-smoke: ok ...
sprint12-dynamic-metadata-layout-smoke: ok ... context_bytes=9904 private_context_bytes=13064 ...
sprint12-textrel-matrix-smoke: ok fixtures=24 ... public_fields_added=0
sprint12-search-path-matrix-smoke: ok fixtures=36 ... distinct_families=2 public_fields_added=0 target_derived_opens=0
sprint12-continuation-smoke: ok sprint=12 status=active patch=76 ... next_patch=77
```

The independent external-presence oracles can run before a NASM build:

```bash
make sprint12-textrel-readelf-oracle
make sprint12-search-path-readelf-oracle
```

The search-path oracle covers 36 controlled objects: 22 valid, ten malformed,
and four unsupported. It exercises mixed-carrier counts 0, 1, 32, 63, 64, and
65; exact-value byte totals 0, 1, 4,096, and 4,097; duplicate equality and
contradiction; empty and hostile bytes; `$ORIGIN`; colon-bearing values; and
missing, unmapped, duplicate, oversized, or unterminated string metadata.

## Complete validation

```bash
make clean
make
make samples
make sprint-closeout-smoke
make docker-build
make docker-test
make docker-validation-smoke
make sprint12-dynamic-metadata-environment-parity-smoke
make sprint12-p076-acceptance-smoke
```

The parity gate compares the complete private textrel/RPATH/RUNPATH record plane
and all four public command closures across separately built native and
container environments. The container receives authenticated source and
fixtures read-only plus one empty writable result root; it never receives the
completed native result plane.

## Required failure behavior

- Mixed private carrier 65 returns exit code 6 before public stdout on commands
  that parse `PT_DYNAMIC`.
- Search record 65 and aggregate exact-value byte 4,097 return exit code 6
  before public stdout.
- Missing or contradictory singleton string-table metadata, unmapped or
  out-of-range values, malformed table extents, and unterminated strings fail
  with stable malformed status and no partial stdout.
- Candidate 4,097 retains the independent exit-6/no-stdout contract.
- `info` remains outside `PT_DYNAMIC` parsing.

## Limitations

RPATH and RUNPATH facts are separate private static metadata. They do not
establish which path a runtime loader will select, whether a referenced location
exists, whether an attacker can modify it, or whether a binary is vulnerable.
Patch 076 does not expand `$ORIGIN`, split values, emulate the loader, open
target-derived paths, or claim exploitability.

Patch 076 did not establish complete acceptance. Fresh NASM, strict ShellCheck,
Docker, actual native/container parity, and independent exact-source acceptance
remain required for the current candidate. These requirements remain separate;
none substitutes for another. Patch 080's review required Patch 081, which
remains pending complete acceptance.
