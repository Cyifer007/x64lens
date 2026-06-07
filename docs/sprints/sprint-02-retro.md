# Sprint 02 Retrospective

## Status

In progress.

## Sprint goal

Map the binary as the Linux loader would and report first-order executable-region and mitigation metadata.

## Patch 006 summary

Patch 006 adds the initial Sprint 2 implementation for program-header analysis and baseline mitigation reporting. The patch is pending local validation.

## Validation to capture

After applying Patch 006, capture output for:

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
./build/x64lens mitigations ./tests/bin/minimal_nopie
./build/x64lens mitigations ./tests/bin/minimal_pie_canary
./build/x64lens mitigations ./tests/bin/minimal_execstack
readelf -l ./tests/bin/minimal_nopie
readelf -l ./tests/bin/minimal_pie_canary
readelf -l ./tests/bin/minimal_execstack
```

## Expected observations

- `minimal_nopie` should report PIE disabled and NX stack enabled.
- `minimal_pie_canary` should report PIE enabled, NX stack enabled, and RELRO present.
- `minimal_execstack` should report NX stack disabled.
- At least one executable region should be reported from `PT_LOAD + PF_X`.
- Malformed program-header offsets should fail safely with exit code `5`.

## Contract review

To be completed after local validation.
