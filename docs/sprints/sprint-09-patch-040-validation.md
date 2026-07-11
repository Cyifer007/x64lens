# Sprint 09 Patch 040 validation

## Purpose

Patch 040 establishes the first Sprint 9 machine-readable report foundation:
command identity, complete-analysis state, schema `0.2.0`, and historical schema
`0.1.0` compatibility. It does not add candidate families, change metric
meanings, or introduce partial output.

## Implemented behavior

- Add a fixed-size `analysis_summary` record built only after the shared
  candidate pipeline succeeds.
- Identify JSON reports with `report_type: analysis` and command identity
  `gadgets` or `analyze`.
- Emit candidate capacity, candidate count, truncation, dropped-count knowledge,
  executable-region progress, selected maximum depth, and overall completion.
- Require successful current reports to state complete enumeration with no
  truncation and no dropped candidates.
- Preserve the 4097-candidate fail-closed contract: exit code `6`, empty stdout,
  and the stable unsupported-feature diagnostic.
- Introduce schema `0.2.0`, preserve a versioned schema `0.1.0` snapshot, and add
  representative compatibility fixtures.
- Add `make schema-compat-smoke` and require current `gadgets` and `analyze`
  reports to match their command identities.

## Required native validation

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make help
make print-vars
make dev-tools-check
make baseline-tools-check
make analysis-tools-check
make full-tools-check
make doctor
make clean
make
make samples
make test
make validate-gadget-fixture
make scanner-smoke
make arena-smoke
make pattern-smoke
make semantic-smoke
make schema-compat-smoke
make json-smoke
make analyze-smoke
make system-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make fuzz-mutated-elf-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
make section-label-smoke
make benchmark-integrity-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
make shellcheck-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

## Required targeted report checks

```bash
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

./build/x64lens gadgets --format json --max-depth 4 \
  ./tests/bin/gadgets > "$tmp/gadgets.json"
./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/gadgets > "$tmp/analyze.json"

python3 tools/validate-json-report.py \
  --mode fixture --require-schema 0.2.0 --expected-command gadgets \
  "$tmp/gadgets.json"
python3 tools/validate-json-report.py \
  --mode fixture --require-schema 0.2.0 --expected-command analyze \
  "$tmp/analyze.json"

python3 tools/validate-report-parity.py \
  "$tmp/gadgets.json" "$tmp/analyze.json"
```

## Required capacity checks

```bash
make capacity-smoke
```

The exact-capacity fixture must emit a valid schema `0.2.0` report with:

```text
candidate_capacity = 4096
candidate_count = 4096
candidate_truncated = false
candidate_dropped_count = 0
candidate_dropped_count_known = true
complete = true
```

The overflow fixture must continue to return exit code `6` in focused and
integrated text and JSON modes, emit no stdout, and print exactly:

```text
error: unsupported binary feature
```

## Required schema compatibility checks

```bash
make schema-compat-smoke
python3 -m json.tool schemas/x64lens-report-0.1.0.schema.json >/dev/null
python3 -m json.tool schemas/x64lens-report.schema.json >/dev/null
python3 -m json.tool tests/expected/x64lens-report-0.1.0.json >/dev/null
python3 -m json.tool tests/expected/x64lens-report-0.2.0.json >/dev/null
```

Expected result:

```text
schema-compat-smoke: ok legacy=0.1.0 current=0.2.0 rejection_cases=5
```

## Required Docker validation

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

A restricted-environment Docker Buildx metadata write failure is an environment
defect only when an unrestricted rerun of the same target passes and the failure
path is outside the repository.

## Acceptance criteria

- Tool version remains `0.1.0-dev`; current JSON schema version is `0.2.0`.
- `gadgets` and `analyze` emit identical shared analysis facts and differ only in
  their top-level command identity for the same target and options.
- Current successful reports are internally consistent and complete.
- The validator rejects candidate-count mismatch, complete-plus-truncated state,
  invalid dropped-count knowledge, impossible region progress, and command
  identity mismatch.
- Representative historical `0.1.0` output remains consumable.
- Existing raw, exact, semantic, unknown, and scored count meanings are unchanged.
- Program headers remain executable-region authority.
- Capacity and malformed-input failures emit no partial report.
- Native and Docker aggregate validation pass in supported environments.
