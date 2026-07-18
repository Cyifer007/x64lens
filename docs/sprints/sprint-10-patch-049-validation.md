# Sprint 10 Patch 049 Validation

## Status

Implementation candidate. Native and qualified Docker acceptance is required before the patch is accepted.

## Source base

Patch 049 is generated against committed Patch 048 source:

```text
8df29129d96861eb298e5e5aeb7209ab890ee936
```

The checkpoint tag remains pinned to:

```text
v0.1.0-dev -> 3d54275beb5207d23100d34541970ddc8bcbcead
```

## Scope

Patch 049:

- removes two tracked generated Sprint 10 ELF fixtures and ignores all generated Sprint 10 fixture outputs;
- removes the public-content checker self-exclusion;
- adds authenticated final-file public-overlay verification;
- reconciles Patch 046 through Patch 048 chronology and public repository voice;
- adds a fixed 16-byte candidate-index memory-effect side-car;
- adds exact qword base-plus-zero memory-write and memory-read families;
- adds controlled fixture, disassembly oracle, text/JSON validation, schema checks, and conservative fallback coverage;
- preserves the dependency-free, decoder-free, single-worker reference runtime.

## Required fixed model

```text
gadget_record:                    112 bytes
candidate_evidence_record:         48 bytes
memory_effect_record:              16 bytes
candidate capacity:              4096
analysis arena:                720896 bytes
```

The arena is a fixed command-lifetime implementation allocation. It is not a process-RSS measurement.

## Controlled fixture

`tests/toy-src/gadgets_sprint10_memory.S` contains:

- three exact qword memory writes;
- three exact qword memory reads;
- six unsupported forms that retain bare-return fallback;
- matching bytes in non-executable data, which must not be scanned.

Expected report facts:

```text
raw candidates:       12
exact patterns:       12
semantic candidates:  12
unknown candidates:    0
memory writes:          3
memory reads:           3
fallback candidates:    6
scored candidates:      6
```

Promoted memory candidates have known stack delta 8, `score:null`, and `full_sequence_valid:null`.

## Required native commands

```bash
make normalize-perms
make script-perms-check
make ownership-check
make scaffold-check
make diagrams-check
make public-docs-check
make public-docs-hygiene-smoke
make public-artifact-content-smoke
make public-overlay-verification-smoke
make planning-docs-check
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
make sprint10-primitive-smoke
make sprint10-register-transfer-smoke
make sprint10-stack-adjust-smoke
make sprint10-memory-smoke
make json-effect-consistency-smoke
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
make decoder-gap-hardening-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

## Focused report checks

```bash
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

./build/x64lens gadgets --format json --max-depth 4 \
  ./tests/bin/gadgets_sprint10_memory > "$tmp/gadgets.json"
./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/gadgets_sprint10_memory > "$tmp/analyze.json"

python3 tools/validate-json-report.py \
  --mode sprint10-memory-fixture \
  --require-schema 0.2.0 \
  --expected-command gadgets \
  --require-provenance \
  --require-sprint10-effects \
  --require-sprint10-transfer \
  --require-sprint10-memory \
  "$tmp/gadgets.json"

python3 tools/validate-report-parity.py \
  "$tmp/gadgets.json" "$tmp/analyze.json"

objdump -d -w -Mintel ./tests/bin/gadgets_sprint10_memory \
  > "$tmp/memory.objdump.txt"
python3 tools/validate-sprint10-memory-disassembly.py \
  ./tests/bin/gadgets_sprint10_memory "$tmp/memory.objdump.txt"
```

## Public overlay verification

The public final-file overlay must be authenticated as one complete archive:

```bash
PUBLIC_BUNDLE=/path/to/049-public-overlay.zip \
PUBLIC_BUNDLE_SHA256=<sha256> \
make public-overlay-verify
```

Acceptance requires outer-hash agreement, metadata-policy acceptance, textual-content acceptance, exact internal-manifest reconciliation, and exact member-set agreement.

## Docker validation

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

A Buildx metadata-path failure is classified separately only after the same product path passes with an isolated writable Buildx configuration.

## Acceptance criteria

- Native and qualified Docker aggregates pass.
- Historical Patch 046 through Patch 048 fixture facts remain unchanged.
- The memory fixture reports exactly 3 writes, 3 reads, 6 fallbacks, and 6 scored candidates.
- Text and JSON render memory facts from the side-car.
- `gadgets` and `analyze` remain command-only parity matches.
- Candidate 4,096 succeeds and candidate 4,097 fails before stdout with exit 6.
- No generated fixture executable is tracked.
- The public checker scans its own source and tampered-checker regressions fail.
- The authenticated public overlay passes both policy layers and its internal manifest.
- The tool and schema versions remain `0.1.0-dev` and `0.2.0`.
- The checkpoint tag remains unchanged.
