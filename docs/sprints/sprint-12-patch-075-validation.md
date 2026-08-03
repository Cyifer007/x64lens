# Sprint 12 Patch 075 Validation

## Scope

Patch 075 corrects the remaining Patch 074 custody and validation findings,
keeps Sprint 12 active, and adds private bounded `DT_TEXTREL` / `DF_TEXTREL`
evidence through a separate dynamic-metadata side-car. Public CLI and schema
`0.2.0` remain unchanged.

## Source boundary

The patch applies only to the exact Patch 074 commit and tree recorded in the
delivery source-identity record. The guarded application script refuses a
different base, a dirty worktree, a second application, or a candidate tree
that does not match the delivery authority.

## Focused validation

```bash
make patch074-corrective-regression-smoke
make sprint12-dynamic-metadata-layout-smoke
make sprint12-textrel-smoke
make sprint12-continuation-smoke
```

Expected high-level results:

```text
patch074-corrective-regression-smoke: ok ...
sprint12-dynamic-metadata-layout-smoke: ok ...
sprint12-textrel-matrix-smoke: ok fixtures=24 ... carrier_cap=64 public_fields_added=0
sprint12-continuation-smoke: ok sprint=12 status=active patch=75 ...
```

The independent oracle path is available before a NASM build:

```bash
make sprint12-textrel-readelf-oracle
```

It generates 24 controlled layouts, retains 19 valid, four malformed, and one
unsupported class, and reconciles 12 eligible direct states against GNU
`readelf -dW`.

## Complete validation

```bash
make clean
make
make samples
make sprint-closeout-smoke
make docker-build
make docker-test
make docker-validation-smoke
make sprint12-p075-acceptance-smoke
```

Fresh native and Docker execution must preserve exit code 6 before stdout for
carrier 65 and candidate 4097, no partial stdout for malformed parser failures,
and byte/fact parity for unchanged public reports.

## Limitations

Text-relocation state is private static evidence. It does not prove that a
runtime relocation occurred, that code pages remain writable, that the binary
is vulnerable, or that exploitation is possible. Actual Patch 075 acceptance
requires fresh NASM, strict ShellCheck, Docker, and independent Lane A results.
