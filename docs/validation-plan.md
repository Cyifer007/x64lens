# Validation Plan

## Validation goals

x64lens must be correct enough to support research claims and safe enough to parse hostile binaries without crashing or reading out of bounds.

## Validation categories

### 1. Build validation

```bash
make fix-perms
make normalize-perms
make clean
make
make samples
make test
```

Docker path:

```bash
make docker-build
make docker-test
```

### 2. Invalid input validation

Test cases:

- empty file,
- text file,
- truncated ELF magic,
- wrong architecture,
- malformed program header offset,
- impossible header count,
- oversized section table.

Expected outcome: graceful failure and stable nonzero exit code.

Current expected codes:

| Input | Expected exit code |
|---|---:|
| plain text file | 4 |
| wrong-architecture ELF-like file | 4 |
| truncated ELF magic/header | 5 |
| malformed program-header range | 5 |
| malformed table-end overflow | 5 |
| empty file | 5 |

### 3. ELF metadata validation

Compare `x64lens info` against:

```bash
./build/x64lens info ./tests/bin/minimal_nopie
./build/x64lens info /bin/ls
readelf -h ./tests/bin/minimal_nopie
readelf -h /bin/ls
```

### 4. Program-header and mitigation validation

Compare `x64lens mitigations` against `readelf -l` first:

```bash
./build/x64lens mitigations ./tests/bin/minimal_nopie
./build/x64lens mitigations ./tests/bin/minimal_pie_canary
./build/x64lens mitigations ./tests/bin/minimal_execstack
readelf -l ./tests/bin/minimal_nopie
readelf -l ./tests/bin/minimal_pie_canary
readelf -l ./tests/bin/minimal_execstack
```

When available, compare hardening indicators against optional external tools:

```bash
make optional-tool-comparison-smoke
tools/compare-checksec.sh ./tests/bin/minimal_pie_canary ./build/x64lens
tools/compare-rabin2.sh ./tests/bin/minimal_pie_canary ./build/x64lens
```

These tools are comparators only; version-specific external labels do not override x64lens loader-fact contracts.

Sprint 2 validation expectations:

| Target | Expected signal |
| ------ | --------------- |
| `minimal_nopie` | PIE disabled, NX stack enabled |
| `minimal_pie_canary` | PIE enabled, NX stack enabled, RELRO reported under the current no/partial/full model |
| `minimal_execstack` | NX stack disabled |
| malformed PHDR copy | exit code `5` |


### Sprint 2 validation evidence

Sprint 2 validation succeeded locally and in Docker. The following high-level observations were confirmed:

| Target | x64lens observation | readelf comparison |
| ------ | ------------------- | ------------------ |
| `minimal_nopie` | PIE disabled, NX stack enabled, RELRO reported under the current no/partial/full model, dynamic linking yes, one executable region | `EXEC`, `GNU_STACK RW`, `GNU_RELRO`, `DYNAMIC`, one `LOAD R E` segment |
| `minimal_pie_canary` | PIE enabled, NX stack enabled, RELRO reported under the current no/partial/full model, dynamic linking yes, one executable region | `DYN`, `GNU_STACK RW`, `GNU_RELRO`, `DYNAMIC`, one `LOAD R E` segment |
| `minimal_execstack` | PIE disabled, NX stack disabled, RELRO reported under the current no/partial/full model, dynamic linking yes, one executable region | `EXEC`, `GNU_STACK RWE`, `GNU_RELRO`, `DYNAMIC`, one `LOAD R E` segment |
| `/bin/ls` | PIE enabled, NX stack enabled, RELRO reported under the current no/partial/full model, dynamic linking yes, one executable region | `DYN`, `GNU_STACK RW`, `GNU_RELRO`, `DYNAMIC`, one `LOAD R E` segment |

`make readelf-comparison-smoke` now parses and compares stable ELF header fields, file size, LOAD counts, executable LOAD counts, GNU_STACK NX state, PT_DYNAMIC presence, PT_GNU_RELRO presence, and RWX LOAD state against `readelf`. `tools/compare-readelf.sh` remains useful for side-by-side manual review.

### 5. Gadget validation

Sprint 3 validates raw scanner output first:

```bash
./build/x64lens gadgets ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
objdump -d -Mintel ./tests/bin/gadgets
```

Expected Sprint 3 signals:

| Target | Expected signal |
| ------ | --------------- |
| `tests/bin/gadgets` | reports `Raw gadget candidates:` |
| `tests/bin/gadgets` | reports at least one `terminator: ret` |
| `tests/bin/gadgets` | reports at least one `terminator: ret imm16` |
| `tests/bin/gadgets` | reports `Exact pattern count: 0x000000000000000b` |
| `tests/bin/gadgets` | reports exact patterns for `pop rdi; ret`, `leave; ret`, `syscall; ret`, and `ret imm16` |
| `--max-depth 4` | reports `Max depth: 0x0000000000000004` |

Later validation should compare `x64lens gadgets` against:

```bash
ROPgadget --binary <file>
ropper --file <file>
ropr <file>
objdump -d -Mintel <file>
```

Existing tools should be validators and benchmark baselines, not runtime dependencies.

### 6. Controlled gadget validation

Use hand-written assembly binaries with known byte patterns.

### 7. Regression validation

Every bug fix should add a regression input or expected output file when practical.

## Validation artifact policy

Benchmark and validation outputs should be saved under `benchmarks/results/` only when they are small, reproducible, and non-sensitive. Large generated outputs should not be committed unless explicitly needed for a paper artifact.

### 5. Sprint 3 raw gadget scanner validation

Patch 008 validates the raw scanner against a hand-authored fixture and a real system binary.

Core commands:

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
./build/x64lens mitigations ./tests/bin/gadgets
./build/x64lens gadgets ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
objdump -d -Mintel ./tests/bin/gadgets
```

Explanatory fixture check:

```bash
make validate-gadget-fixture
```

Expected fixture signals:

| Signal | Expected value |
| ------ | -------------- |
| default max depth | `0x0000000000000008` |
| custom max depth | `0x0000000000000004` |
| candidate count | `0x000000000000000b` |
| `ret` count | `0x000000000000000a` |
| `ret imm16` count | `0x0000000000000001` |
| known bytes | `5f c3`, `0f 05 c3`, `c2 10 00` |

Scanner smoke benchmark:

```bash
make bench-scanner-smoke
```

The smoke benchmark records repeated local measurements but does not support publication claims until the benchmark corpus, baseline tools, environment metadata, and statistical summary are finalized.


### 6. Arena allocator validation

Sprint 3 Patch 010 moves raw gadget candidate records from static `.bss` storage to an mmap-backed arena. The scanner-visible behavior should remain unchanged. Validate with:

```bash
make arena-smoke
make validate-gadget-fixture
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 /bin/ls
```

Expected fixture signals:

| Signal | Expected |
| ------ | -------- |
| Candidate capacity | `0x0000000000001000` |
| Candidate count | `0x000000000000000b` |
| ret count | `0x000000000000000a` |
| ret imm16 count | `0x0000000000000001` |

The arena allocator does not change scanner semantics. It is infrastructure for command-lifetime analysis storage.


### Sprint 3 Phase D pattern validation

Patch 011 validates exact byte-template matching through the default regression suite and the objdump-backed fixture validator:

```bash
make test
make validate-gadget-fixture
make pattern-smoke
```

Expected fixture signals:

| Target | Expected signal |
| ------ | --------------- |
| `tests/bin/gadgets` | `Exact pattern count: 0x000000000000000b` |
| `tests/bin/gadgets` | `pattern: pop rdi; ret` |
| `tests/bin/gadgets` | `pattern: pop rsi; ret` |
| `tests/bin/gadgets` | `pattern: pop rdx; ret` |
| `tests/bin/gadgets` | `pattern: pop rax; ret` |
| `tests/bin/gadgets` | `pattern: leave; ret` |
| `tests/bin/gadgets` | `pattern: syscall; ret` |
| `tests/bin/gadgets` | `pattern: ret imm16` |

This validates exact byte templates only. It does not validate semantic classes, register control, scoring, or exploitability interpretation.

### 6. Sprint 3 scanner, arena, and pattern validation

Sprint 3 validation proved the raw scanner, arena-backed candidate storage, exact suffix pattern matcher, fixture validator, and scanner smoke benchmark path.

Validation commands:

```bash
make normalize-perms
make clean
make
make samples
make test
make docker-test
make validate-gadget-fixture
make pattern-smoke
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 /bin/ls | head -n 40
```

Expected controlled fixture signals:

| Signal | Expected value |
| ------ | -------------- |
| Candidate count | 7 |
| ret count | 6 |
| ret imm16 count | 1 |
| Exact pattern count | 7 |
| Known labels | `pop rdi; ret`, `pop rsi; ret`, `pop rdx; ret`, `pop rax; ret`, `leave; ret`, `syscall; ret`, `ret imm16` |

Sprint 3 validation evidence from local WSL2 and Docker runs:

```text
make test -> tests: ok
make docker-test -> tests: ok
make validate-gadget-fixture -> validate-gadget-fixture: ok
make pattern-smoke -> validate-gadget-fixture: ok
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke -> scanner-smoke benchmark complete
```

Interpretation rule: exact pattern labels describe the recognized suffix ending at the terminator. They are not full semantic classifications and they are not exploitability claims.

### 7. Sprint 4 semantic validation status

Patch 015 adds validation for:

- semantic class labels,
- controlled-register bitmaps,
- stack-delta values,
- primitive coverage summaries,
- preservation of `unknown_candidate` for unsupported windows.

Current commands:

```bash
make validate-gadget-fixture
make semantic-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
```

`analyze <file>` is implemented in Sprint 6 Patch 022 as the integrated checkpoint command. Validation now covers text and JSON `analyze` output against the controlled fixture and installed system binaries.


### 10. Sprint 6 analyze checkpoint validation status

Patch 022 adds validation for:

- `analyze --max-depth 4 <file>` text output,
- `analyze --format json --max-depth 4 <file>` JSON output,
- flag-order parity for `analyze --max-depth 4 --format json <file>`,
- invalid input rejection parity with `info`, `mitigations`, and `gadgets`,
- system-binary smoke coverage for text and JSON `analyze` reports.

Current commands:

```bash
make test
make analyze-smoke
make system-smoke
make validation-smoke
./build/x64lens analyze --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --format json --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-analyze.json
python3 tools/validate-json-report.py --mode fixture /tmp/x64lens-analyze.json
```

Validation remains shape-and-contract based for system binaries. Distro-specific candidate counts are intentionally not asserted.

## Parser safety and mutation smoke plan

Patch 025 implements the first deterministic malformed-input mutation harness before deeper parsing expands the trusted code surface.

Implemented command shape:

```bash
make malformed-smoke
make fuzz-mutated-elf-smoke
make capacity-smoke
```

Minimum acceptance criteria:

```text
no SIGSEGV, SIGBUS, or another signal
no timeout or unbounded runtime
stable nonzero exit code for malformed inputs
no partial stdout for malformed parse failures
successful valid controls and boundary probes
regression fixture added for every stable parser defect
explicit exit code 6 for candidate-capacity exhaustion
```

The first version is intentionally deterministic rather than coverage-guided. It establishes reproducible regression handling, result capture, and a durable fixture-promotion policy before instrumentation-dependent fuzzing is considered.

## Script permission validation

Patch extraction, Windows tooling, or cross-platform ZIP workflows can accidentally drop executable bits from shell helpers. `make scaffold-check` should validate that expected scripts remain executable through `make script-perms-check`.


### 8. Sprint 4 Patch 015 semantic classifier validation

Sprint 4 Patch 015 validates first-pass semantic classification through the controlled `tests/bin/gadgets` fixture.

Commands:

```bash
make validate-gadget-fixture
make semantic-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
```

Expected controlled fixture signals:

| Signal | Expected value |
| ------ | -------------- |
| Candidate count | `0x000000000000000b` |
| Exact pattern count | `0x000000000000000b` |
| Semantic primitive count | `0x000000000000000b` |
| unknown_candidate count | `0x0000000000000000` |
| arg_control count | `0x0000000000000006` |
| syscall_num_control count | `0x0000000000000001` |
| syscall_trigger count | `0x0000000000000001` |
| stack_pivot count | `0x0000000000000002` |
| alignment count | `0x0000000000000001` |
| Register coverage | `rax|rcx|rdx|rsi|rdi|rsp|r8|r9` |

This validation confirms classifier plumbing and fixture behavior. It is not a full decoder validation and does not establish exploitability.


### Sprint 4 semantic classifier validation

Patch 015 validation succeeded locally and in Docker. Required commands:

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make clean
make
make samples
make test
make docker-test
make validate-gadget-fixture
make semantic-smoke
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens gadgets --max-depth 4 /bin/ls | head -n 80
```

Expected controlled fixture semantic signals:

| Signal | Expected value |
|---|---:|
| Candidate count | `0x000000000000000b` |
| Exact pattern count | `0x000000000000000b` |
| Semantic primitive count | `0x000000000000000b` |
| unknown_candidate count | `0x0000000000000000` |
| arg_control count | `0x0000000000000006` |
| syscall_num_control count | `0x0000000000000001` |
| syscall_trigger count | `0x0000000000000001` |
| stack_pivot count | `0x0000000000000002` |
| alignment count | `0x0000000000000001` |
| Register coverage | `rax|rcx|rdx|rsi|rdi|rsp|r8|r9` |

`/bin/ls` is a smoke target only. Its exact counts can vary across systems, but it should complete without crashing and should preserve raw/exact/semantic/unknown metric separation.

Patch 017 expands the controlled fixture to include `pop rcx; ret`, `pop r8; ret`, `pop r9; ret`, and `pop rsp; ret` before score values are exposed.

## Sprint 5 scoring and JSON validation

Patch 017 adds scoring and initial JSON output. Validate both text and JSON paths:

```bash
make validate-gadget-fixture
make semantic-smoke
make json-smoke
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens gadgets --format json --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-gadgets.json
python3 -m json.tool /tmp/x64lens-gadgets.json >/dev/null
```

Expected controlled fixture signals:

| Field | Expected value |
|---|---:|
| candidate count | 11 |
| ret count | 10 |
| ret imm16 count | 1 |
| exact pattern count | 11 |
| semantic primitive count | 11 |
| scored candidate count | 11 |
| unknown candidate count | 0 |
| arg_control count | 6 |
| stack_pivot count | 2 |

The JSON output must include `schema_version`, `tool`, `tool_version`, `target`, `mitigations`, `counts`, `primitive_coverage`, `gadgets`, and `limitations`. Stack-pivot records should expose `stack_delta: null` and `stack_delta_known: false`.

### Sprint 5 Patch 018 validation hardening

Patch 018 adds reusable validation targets so scoring and JSON output are not validated only through inline shell checks.

Core local validation:

```bash
make script-perms-check
make scaffold-check
make diagrams-check
make test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
make analyze-smoke
make system-smoke
make validation-smoke
```

Docker environment triage:

```bash
make docker-available-check
make docker-test
```

`docker-available-check` distinguishes Docker Desktop/Engine availability from implementation failures. A missing `docker` command or unreachable daemon should be fixed as an environment issue before treating `docker-test` as a code failure.

JSON validation:

```bash
./build/x64lens gadgets --format json --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-gadgets.json
python3 tools/validate-json-report.py --mode fixture /tmp/x64lens-gadgets.json
```

System binary smoke:

```bash
make system-smoke
MAX_DEPTH=4 bash tools/system-binary-smoke.sh ./build/x64lens /bin/ls /bin/cat
```

The system smoke target validates output shape and internal count invariants against installed ELF64 x86_64 binaries. It must not assert exact candidate counts because those vary by distribution, compiler, and binary version.

Patch bundle hygiene:

```bash
BUNDLE=/path/to/patch.zip make patch-bundle-hygiene
```

Patch/release bundles should exclude `.git/`, `.local/`, `build/`, `tests/bin/`, generated benchmark results, generated toy binaries, object files, private/course documents, and nested ZIPs.


### Sprint 5 Patch 019 baseline comparison smoke validation

Patch 019 validates benchmark-comparison plumbing without making publication claims. Run:

```bash
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
python3 benchmarks/scripts/summarize.py benchmarks/results/baseline-smoke-*.tsv
```

Expected behavior:

- x64lens always runs through `gadgets --format json --max-depth <N>`.
- x64lens JSON is validated after timed execution.
- ROPgadget, Ropper, and ropr are run only when installed.
- Missing optional baselines are recorded in metadata and skipped by default.
- Generated TSV and metadata files remain ignored under `benchmarks/results/`.

Strict optional-baseline check:

```bash
REQUIRE_BASELINES=1 RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
```

This command should fail clearly when no optional baseline tool is installed.

## Sprint 5 Patch 020 development-environment validation

Patch 020 adds explicit dependency and onboarding checks so a new development environment can fail early with actionable installation guidance.

New checks:

```bash
make build-tools-check
make sample-tools-check
make dev-tools-check
make baseline-tools-check
make doctor
```

Expected behavior:

- `build-tools-check` fails if NASM or GNU ld are missing.
- `sample-tools-check` fails if the toy corpus cannot be built.
- `dev-tools-check` fails if the standard local validation toolchain is incomplete.
- `baseline-tools-check` reports optional ROPgadget, Ropper, and ropr availability without failing by default.
- `REQUIRE_BASELINES=1 make baseline-tools-check` fails when optional baseline tools are required but unavailable.
- `doctor` prints a full environment report suitable for setup troubleshooting.

Patch 020 also broadens `bench-baselines-smoke` default targets to include the controlled gadget fixture plus common system binaries:

```text
tests/bin/gadgets
/bin/ls
/bin/cat
/bin/sh
/usr/bin/env
/usr/bin/printf
```

The baseline smoke harness continues to validate measurement plumbing, not research claims. Optional baselines are skipped unless explicitly required.

## Sprint 5 closeout environment validation

Patch 021 adds two environment hardening requirements:

1. Docker validation must use a current development image. `make docker-test` therefore depends on `make docker-build` so Dockerfile dependency updates are not tested against stale cached images.
2. Optional baseline enforcement must happen only in baseline-aware checks. `REQUIRE_BASELINES=1` should not make `dev-tools-check` fail because ROPgadget, Ropper, and ropr are outside the required development toolchain.

ropr remains optional. If Cargo is too old, `make install-ropr-user` must fail with a clear rustup remediation path rather than exposing a long dependency-resolution failure from Cargo.

## Sprint 6 checkpoint validation

```bash
make public-docs-check
make analyze-smoke
make checkpoint-demo
DEMO_TARGET=/bin/ls MAX_DEPTH=4 make checkpoint-demo
make bench-summary-latest
```

The integrated text regression requires exactly one version line and one target line while preserving all major sections. Public-documentation validation is part of `make validation-smoke`.

## Sprint 6 Patch 024 planning and architecture validation

Patch 024 adds a structural planning check and preserves the entire runtime regression ladder:

```bash
make planning-docs-check
make validation-smoke
make docker-test
BUNDLE=/path/to/024_x64lens_sprint6_roadmap_architecture_review_patch.zip \
  make patch-bundle-hygiene
```

The planning check confirms that the canonical roadmap, evidence gates, schema transition, and Sprint 7 through Sprint 18 plans are present and internally connected. It does not replace editorial review or runtime testing.

The Patch 024 runtime acceptance rule is no regression from the validated Sprint 6 checkpoint. Fixture counts, JSON schema `0.1.0`, single-banner `analyze` text output, and system-binary smoke behavior remain unchanged.

## Sprint 7 Patch 025 hostile-input validation

Patch 025 introduces two required regression gates:

```bash
make malformed-smoke
make capacity-smoke
make validation-smoke
make docker-validation-smoke
```

The deterministic malformed-input runner initially derived 29 cases from the controlled `minimal_nopie` seed. After Patch 028, it derives 31 cases: 28 malformed structures, two valid controls, and one valid executable-region boundary probe. Each row captures the seed hash, mutation, command shape, expected and observed exit code, signal, timeout state, elapsed nanoseconds, stdout size, stderr size, result, and diagnostic preview.

Acceptance requires:

- no SIGSEGV, SIGBUS, or another signal,
- no timeout,
- no unexpected success for malformed input,
- no partial stdout for malformed parse failures,
- stable exit code `4` or `5` according to the documented failure class,
- successful valid control and boundary cases,
- a TSV result artifact and JSON metadata artifact,
- native and Docker agreement.

The candidate-capacity fixtures exercise both the exact 4096-record boundary and a 4097th candidate while the current arena holds 4096 records. The exact-boundary JSON report must contain all 4096 records. For the overflow fixture, `gadgets` and `analyze`, in text and JSON modes, must return exit code `6`, emit no stdout, and print exactly `error: unsupported binary feature` on stderr. This is a fail-closed completeness contract, not truncation.

Patch 025 also adds a direct regression for `e_shentsize=63`. An ELF64 file with a nonzero section count must use the fixed 64-byte section-header entry size. This closes an unsafe future-stride assumption before section-table parsing expands.

Generated mutations remain temporary by default. A stable crash, timeout, unsafe bounds acceptance, or other parser defect must be minimized, documented, and promoted into `tests/malformed/regressions/` in a follow-on patch.

## Higher-resolution benchmark validation direction

The publication runner planned for Sprint 12 must validate its own measurement contract:

- monotonic nanosecond wall-clock timestamps,
- per-child user CPU, system CPU, and maximum RSS,
- documented warmup and cache policy,
- tool and target hashes,
- randomized or counterbalanced tool order,
- batching or larger targets when the timer floor dominates,
- separation of raw scanner, JSON gadget, and integrated analysis modes,
- raw rows preserved before summaries are generated.

Smoke benchmark rows remain development evidence and must not be merged with frozen research-campaign rows.

## Sprint 7 Patch 026 mitigation-oracle validation

Run `MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke`. The original Patch 026 oracle established 11 valid cases and five malformed cases; Patch 028 expands the malformed matrix to seven cases; Patch 031 expands the matrix to 17 valid cases and 11 malformed cases by adding full RELRO evidence combinations, duplicate-`PT_DYNAMIC` rejection, and gadget command-path coverage for dynamic malformed probes; Patch 032 expands the matrix to 20 valid cases and 12 malformed cases by adding canary-present/canary-absent indicators, valid non-`DT_NULL` dynamic coverage, direct gadgets JSON validation for valid cases, and invalid dynamic string-table rejection. Patch 033 expands the matrix to 23 valid cases, 14 malformed cases, and one unsupported fail-closed case by adding stripped/not-stripped indicators, zero-length dynamic string-table negative evidence, duplicate dynamic string-table singleton rejection, and string-table scan-cap rejection. Patch 034 expands the matrix to 24 valid cases, 14 malformed cases, and one unsupported fail-closed case by adding the zero-length dynamic string-table endpoint case and section-label assertions. Patch 035 preserves those matrix counts and adds `make section-label-smoke` with four focused hostile section-label cases. Patch 036 preserves the mitigation-matrix counts and expands `make section-label-smoke` to six cases by adding high-bit JSON escaping and file-offset/virtual-address mismatch omission. Current acceptance requires exact focused text, matching integrated JSON mitigation values, no stderr for successful commands, and exact exit code `5` plus the stable malformed diagnostic for every malformed case through the relevant command paths. The generated JSON artifact under `tests/results/mitigation-matrix/` must remain ignored by Git. This target is included in `make validation-smoke` and `make docker-validation-smoke`.

## Sprint 7 Patch 027 mitigation-oracle correction validation

Patch 027 preserves runtime text and updates the oracle's no-executable-region expectation to `  none discovered from PT_LOAD + PF_X`. Acceptance requires `MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke`, `MALFORMED_TIMEOUT=2 make validation-smoke`, and `MALFORMED_TIMEOUT=2 make docker-validation-smoke` to pass. The evidence artifact must contain 11 valid records, five malformed records, and the exact zero-region line for `non-executable-load`. A Make target failure remains a valid fail-fast signal and must not be masked.

## Sprint 7 Patch 028 checked parser-arithmetic validation

Patch 028 centralizes checked multiplication, checked addition, offset-plus-length
end validation, table-extent validation, and bounded per-entry table offsets in
`src/bounds.asm`. `src/elf64.asm` and `src/phdr.asm` must consume those helpers
before forming program-header pointers or trusting file-backed `PT_LOAD` ranges.

Acceptance requires the normal aggregate gates plus focused checked-arithmetic
coverage:

```bash
make test
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected matrix summary after Patch 028:

```text
mitigation-matrix-smoke: ok
  valid cases: 11
  malformed cases: 7
```

The public-docs gate must continue to pass after generated ignored result
artifacts exist under `tests/results/`.


## Sprint 7 Patch 029 closeout validation

Patch 029 is a public planning and closeout patch. It must not change runtime behavior. Acceptance requires the same full command matrix as Patch 028, with `planning-docs-check` accepting Sprint 7 as closed and Sprint 8 as the next implementation tranche.

Expected closeout state:

```text
make planning-docs-check
planning-docs-check: ok plans=18 forward_plans=11

MALFORMED_TIMEOUT=2 make validation-smoke
validation-smoke: ok
```

The `v0.1.0-dev` tag must remain pinned to the Sprint 6 integrated checkpoint.


## Sprint 7 closeout validation baseline

After Patch 029, Sprint 8 starts from the following required local aggregate baseline:

```bash
make test
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected Sprint 7 closeout evidence includes 31 malformed-smoke cases, 28 malformed cases, 11 valid mitigation-matrix cases, seven malformed mitigation-matrix cases, and stable 4096/4097 candidate-capacity behavior. Patch 031 intentionally expands the mitigation-matrix expectation to 17 valid cases and 11 malformed cases. Patch 032 expands it again to 20 valid cases and 12 malformed cases. Patch 033 expands it to 23 valid cases, 14 malformed cases, and one unsupported fail-closed case while preserving the malformed-smoke and capacity baselines. Patch 034 expands it to 24 valid cases, 14 malformed cases, and one unsupported fail-closed case while preserving those same baselines. Patch 035 preserves those counts and adds four section-label smoke cases. Patch 036 keeps the mitigation-matrix counts and expands the focused section-label smoke harness to six cases.

## Sprint 8 Patch 030 bounded dynamic-table validation

Patch 030 adds a bounded `PT_DYNAMIC` table view and compatible mitigation fields for bind-now evidence, dynamic-entry count, and dynamic terminator state. Acceptance requires the full aggregate gates plus focused mitigation-matrix expansion:

```bash
make test
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected matrix summary after Patch 030:

```text
mitigation-matrix-smoke: ok
  valid cases: 14
  malformed cases: 10
```

Expected report behavior for a binary without `PT_DYNAMIC` is `Bind now: not applicable`, zero dynamic entries, and `Dynamic terminator: not applicable`. Dynamic bind-now fixtures must prove `DT_BIND_NOW`, `DT_FLAGS & DF_BIND_NOW`, and `DT_FLAGS_1 & DF_1_NOW` evidence paths independently.

## Sprint 8 Patch 031 RELRO refinement validation

Patch 031 refines RELRO reporting by combining `PT_GNU_RELRO` with bounded bind-now evidence from Patch 030. Acceptance requires the full aggregate gates plus the expanded mitigation matrix:

```bash
make test
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected matrix summary after Patch 031:

```text
mitigation-matrix-smoke: ok
  valid cases: 17
  malformed cases: 11
```

Expected RELRO behavior is `RELRO: not found` with JSON `none` when `PT_GNU_RELRO` is absent, `RELRO: partial` with JSON `partial` when `PT_GNU_RELRO` is present without bind-now evidence, and `RELRO: full` with JSON `full` when `PT_GNU_RELRO` and bounded bind-now evidence are both present. Duplicate `PT_DYNAMIC` headers are malformed and must fail closed before stdout.

## Sprint 8 Patch 032 canary indicator validation

Patch 032 adds evidence-qualified canary reporting and expands the mitigation matrix. Acceptance requires the full aggregate gates plus focused matrix counts:

```bash
make test
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected matrix summary after Patch 032:

```text
mitigation-matrix-smoke: ok
  valid cases: 20
  malformed cases: 12
```

Expected canary behavior is `Canary indicator: unknown` when bounded dynamic string metadata is unavailable, `Canary indicator: absent` when the checked dynamic string table does not contain exact `__stack_chk_fail`, and `Canary indicator: present` when the exact null-terminated symbol is found. JSON mirrors this as `mitigations.canary` values `unknown`, `absent`, and `present`.

## Sprint 8 Patch 033 stripped indicator validation

Patch 033 adds evidence-qualified stripped reporting, rejects duplicate dynamic string-table singleton entries, and promotes zero-length and over-cap string-table cases into the mitigation matrix. Acceptance requires the full aggregate gates plus focused matrix counts:

```bash
make test
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected matrix summary after Patch 033:

```text
mitigation-matrix-smoke: ok
  valid cases: 23
  malformed cases: 14
  unsupported cases: 1
```

Expected stripped behavior is `Stripped indicator: unknown` when bounded section-table evidence is unavailable, `Stripped indicator: stripped` when a validated section table contains no `SHT_SYMTAB`, and `Stripped indicator: not stripped` when a validated section table contains `SHT_SYMTAB`. JSON mirrors this as `mitigations.stripped` values `unknown`, `stripped`, and `not_stripped`. Section-derived metadata must not change executable-region boundaries or gadget scanning.

## Sprint 8 Patch 034 validation additions

Patch 034 adds section-label assertions to the core suite for `mitigations`, `gadgets`, and `analyze` output against the controlled gadget fixture. It also adds a mitigation-matrix case for zero-length dynamic string-table evidence whose pointer is exactly at the end of its file-backed load. The expected mitigation-matrix summary is 24 valid cases, 14 malformed cases, and one unsupported fail-closed case.


## Sprint 8 Patch 035 section-label hardening validation

Patch 035 adds `make section-label-smoke` and includes it in `make validation-smoke` and Docker aggregate validation. Acceptance requires:

```bash
MALFORMED_TIMEOUT=2 make section-label-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Expected section-label summary:

```text
section-label-smoke: ok
  cases: 4
```

The four Patch 035 cases cover baseline `.text` labels, escaped newline-bearing labels, non-executable overlap rejection, and ambiguous executable overlap omission. Patch 036 expands the target to six cases by adding high-bit JSON escaping and file-offset/virtual-address mismatch omission.

## Sprint 8 Patch 036 historical findings hardening validation

Patch 036 acceptance requires the full native aggregate, focused section-label smoke, malformed smoke, mitigation matrix, capacity smoke, benchmark input-failure probes, and Docker validation when Docker is available. The focused evidence requirements are:

- high-bit section-name bytes must not produce invalid JSON,
- target paths and section labels must preserve byte evidence through JSON escapes rather than lossy placeholders,
- section labels must be omitted when section file offset and section virtual-address evidence disagree,
- `.env` and `.env.*` must not enter Docker images from the build context,
- benchmark scripts must reject `RUNS=0`, invalid max-depth values, nonnumeric timing/RSS values, and negative timing/RSS values,
- `bench-summary` must not silently aggregate unrelated TSV files,
- JSON validation must reject `primitive_coverage.registers` values that omit registers present in candidate control lists,
- validation helpers must avoid fixed temporary-output names.

Required commands are documented in `docs/sprints/sprint-08-patch-036-validation.md`.


### Patch 037 comparator gates

Patch 037 closes the remaining Sprint 8 comparator deliverables:

```bash
make benchmark-integrity-smoke
make readelf-comparison-smoke
make optional-tool-comparison-smoke
```

The first target rejects empty, malformed, negative, and non-finite benchmark
rows. The second target is part of `validation-smoke`. The third target skips
missing optional tools but executes `checksec` and `rabin2 -I` when present.

## Sprint 8 Patch 039 closeout validation

Patch 039 closes Sprint 8 and validates the remaining Patch 037 follow-ups:
optional comparator helper argument identity, benchmark-integrity RSS coverage,
strict shell-helper lint documentation, Sprint 8 retrospective documentation,
and Sprint 9 handoff.

Required targeted probes:

```bash
make benchmark-integrity-smoke
make optional-tool-comparison-smoke
make readelf-comparison-smoke
make shellcheck-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

When optional comparators are installed, both direct helper argument orders must
resolve to the same analyzer and target identity:

```bash
bash tools/compare-checksec.sh ./tests/bin/minimal_pie_canary ./build/x64lens
bash tools/compare-checksec.sh ./build/x64lens ./tests/bin/minimal_pie_canary
bash tools/compare-rabin2.sh ./tests/bin/minimal_pie_canary ./build/x64lens
bash tools/compare-rabin2.sh ./build/x64lens ./tests/bin/minimal_pie_canary
```

The complete local gate remains:

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
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
MALFORMED_TIMEOUT=2 make validation-smoke
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

Acceptance requires Sprint 8 public planning to be closed and Sprint 9 to be
identified as the next implementation tranche.


## Sprint 8 Patch 039 correction

Patch 039 is the final Sprint 8 closeout correction. It requires `make benchmark-integrity-smoke` to generate and reject `nan-rss.tsv`, `inf-rss.tsv`, and `neg-inf-rss.tsv`, requires strict shell lint to pass when `shellcheck` is installed, and keeps the context refresh outside public tracked source.

## Sprint 9 Patch 040 report identity and completeness validation

Patch 040 advances current JSON output to schema `0.2.0` and adds one
command-owned analysis-summary record. Validation must prove command identity,
shared `gadgets`/`analyze` facts, complete-success state, historical `0.1.0`
compatibility, and unchanged fail-closed capacity behavior.

Required focused commands:

```bash
make schema-compat-smoke
make json-smoke
make analyze-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
```

Current producer validation requires:

```bash
python3 tools/validate-json-report.py \
  --require-schema 0.2.0 --expected-command gadgets <gadgets-report.json>
python3 tools/validate-json-report.py \
  --require-schema 0.2.0 --expected-command analyze <analyze-report.json>
```

For the same fixture and maximum depth, the two reports must have identical
`analysis`, `target`, `mitigations`, `counts`, `primitive_coverage`, and
`gadgets` values. Their top-level `command` values must differ as named.

Successful current reports must satisfy:

```text
analysis.complete = true
analysis.candidate_truncated = false
analysis.candidate_dropped_count_known = true
analysis.candidate_dropped_count = 0
analysis.candidate_count = counts.raw_candidate_count
analysis.regions_scanned = analysis.regions_total
```

The exact-capacity fixture remains a complete 4096-record report for both `gadgets` and `analyze`; the two JSON documents must match after removing only command identity. The overflow
fixture remains exit code `6` with empty stdout for `gadgets` and `analyze` in
text and JSON modes. No partial report is accepted.

The schema compatibility target must reject at least candidate-count mismatch,
complete-plus-truncated state, invalid dropped-count knowledge, impossible
region progress, and expected-command mismatch.


## Sprint 9 Patch 041 candidate provenance and contract validation

Patch 041 acceptance adds these focused gates:

```bash
make schema-compat-smoke
make patch-bundle-hygiene-smoke
make benchmark-integrity-smoke
make capacity-smoke
```

Current `gadgets` and `analyze` JSON must be validated with
`--require-provenance`. Every candidate must have evidence whose suffix range
ends at the retained terminator and whose semantic source agrees with the
candidate class. Controlled fixture reports remain command-only parity matches.

The schema compatibility gate applies both retained formal schemas and the
semantic cross-field validator. The bundle smoke rejects generated files under
arbitrary archive roots. The benchmark smoke produces two groups for rows that
differ only by schema identity. Capacity stderr is compared byte-for-byte.

Local ABI validation must confirm `RSP mod 16 == 0` immediately before nested
calls in `x64lens_report_json_gadgets` for both JSON-producing commands.


## Sprint 9 Patch 042 portable bundle and decoder-gap validation

Patch 042 does not change the analyzer runtime. Its acceptance surface is the
public artifact boundary plus external decoder-gap evidence generated from
current schema `0.2.0` reports.

Required focused commands:

```bash
make patch-bundle-hygiene-smoke
BUNDLE=/path/to/public-source-or-patch.zip make patch-bundle-hygiene
make decoder-gap-smoke
make schema-compat-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

The bundle-policy smoke must exercise zero-root, one-root, and arbitrary-root
layouts and reject the reviewed private-path cases together with unsafe paths,
case collisions, symlinks, generated outputs, and nested archives. The actual
public artifact must pass the same checker implementation without extraction.

The controlled decoder-gap fixture must report 11 x64lens candidates and 11
canonical return terminators, zero raw-boundary disagreement in either
direction, 11 exact-boundary matches, zero exact-boundary disagreement, zero
candidate-byte mismatch, and zero duplicate candidate/evidence/canonical keys.
The generated manifest must record analyzer, campaign implementation,
controlled expectation, canonical validator, Python, GNU time, objdump, and
target SHA-256 hashes plus exact commands and versions.

The broader command:

```bash
make decoder-gap-campaign
```

runs the same comparison over selected installed system binaries. These counts
are host-dependent observations. Acceptance requires preserved raw JSON,
objdump disassembly, command and metric files, categorized comparison JSON, and
summary artifacts; it does not require equality with objdump or authorize a
runtime decoder.

Regeneration may replace only an existing result directory carrying the
campaign's own `x64lens-decoder-gap-manifest-v1` marker. An unrelated directory
must be refused without deletion.

## Sprint 9 Patch 043 campaign hardening validation

Required focused commands:

```bash
make patch-bundle-hygiene-smoke
make public-docs-hygiene-smoke
make decoder-gap-hardening-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make decoder-gap-smoke
```

Expected focused results:

```text
patch-bundle-hygiene-smoke: ok cases=55 accepted=6 rejected=49
public-docs-hygiene-smoke: ok cases=3 accepted=1 rejected=2
decoder-gap-hardening-smoke: ok parser=1 snapshots=2 publication_interruptions=8
```

The campaign must prove that both comparison tools consume the same immutable
target snapshot, retain parser diagnostics, and keep resolvable command paths
after publication. `SIGINT` and `SIGTERM` probes cover before-backup,
after-backup, before-publish, and after-publish states. Archive probes cover
cross-platform invalid characters and device aliases, raw/effective name
ambiguity, Unicode-name metadata, unknown or malformed extra fields, file/type
contradictions, and common nested ZIP containers.

Patch 043 changes no runtime or schema path. The full native and qualified
Docker aggregates remain mandatory no-regression gates.

## Sprint 9 Patch 044 corrective validation

Patch 044 preserves the analyzer runtime and adds focused acceptance for the
research and release tooling. Required focused commands are:

```bash
make public-docs-hygiene-smoke
make patch-bundle-hygiene-smoke
make decoder-gap-hardening-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

The public fixture gate rejects eight synthetic attachment/path variants. The
archive gate exercises 64 layouts through both the Python implementation and
production shell wrapper. The decoder hardening gate covers all 27 reviewed
prefix/near-return forms, prefixed control-flow barriers, ten transaction
interruptions including the post-rename window, and both measured-child signal
cleanup cases. Full native and qualified Docker aggregates remain mandatory.
See `docs/sprints/sprint-09-patch-044-validation.md`.

## Sprint 9 Patch 045 closeout validation

Patch 045 closes Sprint 9 with no analyzer assembly or schema change. Run:

```bash
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

The closeout target requires strict ShellCheck to be installed, reruns strict shell lint, then runs the complete native aggregate. Docker remains a separate environment-qualified reproducibility gate. Current capacity behavior remains exact at 4096 candidates and fail-closed at 4097 with exit 6, empty stdout, and the stable unsupported-feature diagnostic.
