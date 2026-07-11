# Sprint 09 Patch 041 validation

## Purpose

Patch 041 adds the candidate-index evidence side-car and closes the meaningful
contract, ABI, artifact-hygiene, test-oracle, and benchmark-identity findings
from Patch 040 validation. It preserves schema `0.2.0`, tool version
`0.1.0-dev`, historical metric meanings, and fail-closed capacity behavior.

## Implemented behavior

- Allocate a dense 48-byte `candidate_evidence_record[]` alongside
  `gadget_record[]` in the command-lifetime arena.
- Record raw-candidate, exact-suffix, semantic-exact, validator, suffix-range,
  and full-sequence-validity facts by candidate index.
- Emit per-candidate JSON `evidence` while keeping Patch 040 schema `0.2.0`
  reports consumable.
- Require evidence for every current-producer candidate through
  `--require-provenance`.
- Correct identified assembly stack-alignment defects before nested System V calls.
- Apply the actual Draft 2020-12 schemas in compatibility smoke tests and retain
  semantic validation for cross-field arithmetic.
- Make bundle-hygiene generated-path matching root-agnostic and regression-test
  multiple archive layouts.
- Compare capacity stderr byte-for-byte.
- Apply canonical report validation inside focused successful-JSON harnesses.
- Stratify benchmark summaries by tool version and schema version.

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
make patch-bundle-hygiene-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
make shellcheck-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

## Required provenance checks

```bash
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

./build/x64lens gadgets --format json --max-depth 4 \
  ./tests/bin/gadgets > "$tmp/gadgets.json"
./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/gadgets > "$tmp/analyze.json"

python3 tools/validate-json-report.py \
  --mode fixture \
  --require-schema 0.2.0 \
  --expected-command gadgets \
  --require-provenance \
  "$tmp/gadgets.json"

python3 tools/validate-json-report.py \
  --mode fixture \
  --require-schema 0.2.0 \
  --expected-command analyze \
  --require-provenance \
  "$tmp/analyze.json"

python3 tools/validate-report-parity.py \
  "$tmp/gadgets.json" "$tmp/analyze.json"
```

For the controlled fixture, every candidate must carry:

```text
kind = semantic_exact
raw_candidate = true
exact_suffix = true
semantic_source = exact
validator = x64lens-exact-suffix
full_sequence_valid = null
```

Each `matched_suffix_offset + matched_suffix_length` must equal the retained
candidate byte-window length. The suffix length must agree with the reported
pattern.

## Required schema and compatibility checks

```bash
make schema-compat-smoke
```

Expected result:

```text
schema-compat-smoke: ok legacy=0.1.0 patch040=0.2.0 current=0.2.0 formal_rejections=13 semantic_rejections=7
```

The formal schema must accept the historical `0.1.0` fixture, the Patch 040
`0.2.0` fixture without evidence, and the current provenance-bearing fixture.
Current-producer validation must reject the Patch 040 fixture when
`--require-provenance` is requested.

## Required artifact and benchmark checks

```bash
make patch-bundle-hygiene-smoke
make benchmark-integrity-smoke
```

Expected results:

```text
patch-bundle-hygiene-smoke: ok layouts=5
benchmark-integrity-smoke: ok identity_groups=3
```

The bundle smoke must reject generated test binaries and result files beneath
arbitrary archive roots. The benchmark smoke must keep otherwise identical
schema `0.1.0` and `0.2.0` rows in separate summary groups.

## Required capacity checks

```bash
make capacity-smoke
```

The 4096-candidate `gadgets` and `analyze` reports must both be complete, contain 4096 evidence objects, and match after removing only command identity.
All four 4097-candidate command/format variants must return exit code `6`, emit
zero stdout bytes, and produce stderr byte-identical to:

```text
error: unsupported binary feature
```

## Required ABI probe

Use GDB or equivalent local instrumentation to stop immediately before nested
calls in representative frames across the corrected assembly call graph:

- the first nested call in `x64lens_report_json_gadgets`;
- a nested call in `json_print_candidate_evidence`;
- a nested call in `json_print_regs_array`;
- the `x64_sys_mmap` call in `x64lens_arena_init`;
- a nested call in `print_hex64`;
- a nested call in `x64lens_report_text_mitigations`.

At every stop:

```text
RSP mod 16 = 0
```

Run the JSON probes through both `gadgets --format json` and
`analyze --format json`, and exercise text, error, help, and version paths at
least once. A top-level-only check is insufficient because every callee that
performs another call owns its own System V alignment obligation. The JSON
outputs must remain command-only parity matches and text bytes must remain
unchanged.

## Required Docker validation

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

A restricted Buildx activity-metadata write failure is an environment defect
only when the same image build and product validation pass with writable Buildx
metadata and no tracked source changes.

## Acceptance criteria

- Candidate evidence is dense, index-aligned, and emitted for every current
  candidate.
- Raw, exact, semantic, unknown, scored, and completion counts are unchanged.
- Full-sequence validity remains unknown until decoder evidence exists.
- Program headers remain executable-region authority.
- Patch 040 `0.2.0` and historical `0.1.0` fixtures remain consumable.
- Current report producers require provenance and maintain command-only parity.
- Every corrected nested-call frame obeys System V stack alignment.
- Capacity and malformed failures emit no partial report.
- Formal-schema, semantic-validator, focused-harness, artifact-hygiene, and
  benchmark-identity gates pass natively and in Docker.
