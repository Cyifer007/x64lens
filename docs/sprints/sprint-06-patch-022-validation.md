# Sprint 6 Patch 022 Validation Plan

## Patch purpose

Patch 022 introduces the first integrated `analyze` checkpoint command.

The patch adds:

- `src/analyze.asm`,
- `analyze [--format text|json] [--max-depth N] <file>` CLI dispatch,
- `make analyze-smoke`,
- system-binary smoke coverage for text and JSON `analyze`,
- documentation and diagram updates for the integrated command.

## Expected behavior

`analyze` should run the current validated pipeline once and emit either text or JSON:

```bash
./build/x64lens analyze --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --format json --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --max-depth 4 --format json ./tests/bin/gadgets
```

Text output should include:

```text
Format:
Mitigations:
Raw gadget candidates:
Semantic primitive count:
Scored candidate count:
```

JSON output should validate with the existing report validator.

## Validation commands

Run from the repository root:

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make build-tools-check
make sample-tools-check
make dev-tools-check
make baseline-tools-check
make doctor

make clean
make
make samples
make test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
make analyze-smoke
make system-smoke
make validation-smoke

./build/x64lens analyze --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --format json --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-analyze.json
python3 -m json.tool /tmp/x64lens-analyze.json >/dev/null
python3 tools/validate-json-report.py --mode fixture /tmp/x64lens-analyze.json

RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary
make docker-available-check
make docker-test
BUNDLE=/path/to/022_x64lens_sprint6_analyze_checkpoint_patch.zip make patch-bundle-hygiene
```

## Acceptance criteria

- `help` lists `analyze` as implemented usage.
- Invalid analyze usage exits with code 2.
- Non-ELF, wrong architecture, truncated ELF, and malformed program-header inputs fail with the same stable codes as the other analysis commands.
- Text `analyze` output includes target metadata, mitigation facts, and gadget facts.
- JSON `analyze` output validates in fixture mode and system mode.
- `make analyze-smoke` succeeds.
- `make system-smoke` validates `analyze` on installed ELF64 x86_64 system binaries.
- Existing `info`, `mitigations`, `gadgets`, scoring, and JSON behavior remains stable.

## Non-goals

Patch 022 does not add a full decoder, full RELRO/canary hardening, SARIF output, bad-byte scoring, exploit-chain generation, or a new JSON schema major version.

## Patch 023 follow-on

Patch 022 established functional integrated output. Patch 023 preserves the same analysis facts and JSON shape while collapsing repeated text banners through shared report-section wrappers.
