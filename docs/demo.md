
# Integrated Checkpoint Demonstration

## Purpose

This guide provides a repeatable Sprint 6 demonstration of the implemented x64lens pipeline. It exercises target metadata, mitigation facts, executable-region discovery, raw candidate scanning, exact pattern matching, semantic classification, scoring, and JSON validation.

## Prepare the repository

```bash
make doctor
make clean
make
make samples
make validation-smoke
```

## Run the controlled demonstration

```bash
make checkpoint-demo
```

The default target is `./tests/bin/gadgets` with `MAX_DEPTH=4`. The final line should be:

```text
checkpoint-demo: ok target=./tests/bin/gadgets max_depth=4
```

## Run the demonstration against a system binary

```bash
DEMO_TARGET=/bin/ls MAX_DEPTH=4 make checkpoint-demo
```

System-binary results are validated by invariant shape rather than fixture-specific candidate counts.

## Run the integrated command directly

```bash
./build/x64lens analyze --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --format json --max-depth 4   ./tests/bin/gadgets > /tmp/x64lens-analyze.json
python3 -m json.tool /tmp/x64lens-analyze.json >/dev/null
python3 tools/validate-json-report.py   --mode fixture /tmp/x64lens-analyze.json
```

## Demonstration boundaries

This checkpoint is a static triage report, not an exploitability proof. Exact suffix labels are not full instruction decoding. Mitigation coverage is intentionally limited to the facts implemented at this checkpoint. Performance observations from smoke runs remain development evidence until the controlled research benchmark campaign is complete.
