# x64lens

**x64lens is an assembly-first ELF64 x86_64 binary analysis tool that maps executable regions, discovers return-oriented candidate windows, classifies supported semantic primitives, evaluates mitigation context, assigns bounded heuristic scores, and produces reproducible text and JSON reports for defensive triage and authorized security research.**

> Status: Sprint 9 is active. Patch 040 established schema `0.2.0`, report/command identity, explicit complete-analysis state, historical schema `0.1.0` compatibility, and `gadgets`/`analyze` parity. Patch 041 adds a dense candidate-index evidence side-car, per-candidate raw/exact/semantic provenance, formal-schema enforcement, ABI and validation-oracle corrections, root-independent bundle hygiene, and benchmark identity stratification. Decoder-gap measurement is next; primitive expansion remains deferred.
>
> Tool version: `0.1.0-dev`
>
> JSON schema version: `0.2.0`
>
> Canonical roadmap: [`docs/roadmap-18-sprints.md`](docs/roadmap-18-sprints.md)

## Why this project exists

Most gadget tools emphasize enumeration for exploit development. x64lens studies a different question: can a dependency-light, assembly-first engine turn deterministic ELF and code-reuse facts into a fast, reproducible, mitigation-aware report that is useful for defensive binary triage?

The project evaluates three research questions:

1. **Performance:** How do runtime, CPU cost, memory use, and throughput compare with established gadget tools under controlled conditions?
2. **Semantic value:** Does separating raw candidates, exact suffix observations, semantic primitives, unknown candidates, and scores provide more actionable evidence than a raw gadget dump?
3. **Operational use:** Can the resulting report support CI, vulnerability-management enrichment, or infrastructure-binary prioritization without claiming exploitability?

NASM is an implementation choice to evaluate, not a result. Performance and usefulness remain hypotheses until the fixed benchmark methodology and corpus support them.

## Current implemented pipeline

```text
read-only file mapping
  -> ELF64 x86_64 validation
  -> program-header analysis
  -> executable PT_LOAD + PF_X regions
  -> optional section-header metadata annotations
  -> raw ret and ret imm16 candidate windows
  -> exact suffix pattern IDs
  -> conservative semantic classes
  -> heuristic scores
  -> command-owned report identity and complete-analysis summary
  -> text or JSON reporting
  -> integrated analyze report
```

Implemented commands:

```text
x64lens help
x64lens version
x64lens info <file>
x64lens mitigations <file>
x64lens gadgets [--format text|json] [--max-depth N] <file>
x64lens analyze [--format text|json] [--max-depth N] <file>
```

A `bench` CLI command is deferred until after `v0.1.0`. Research measurement remains under repository Make targets and scripts so orchestration stays independent from the analyzer being measured.

## Scope

The current `0.1.x` research line targets:

- Linux ELF64,
- x86_64,
- static local analysis,
- direct-syscall NASM core,
- program-header-authoritative executable mappings,
- pattern-based candidate discovery,
- conservative semantic classification,
- text and JSON output,
- reproducible comparison tooling.

The current line does not implement exploit generation, payload generation, remote interaction, symbolic execution, dynamic tracing, automatic vulnerability discovery, a mandatory full decoder, multi-architecture support, PE, or Mach-O.

## Important interpretation boundaries

- A **raw candidate** is a terminator-centered byte window.
- An **exact pattern** is a recognized suffix, not proof that the full window is one decoded instruction sequence.
- A **semantic primitive** is assigned only when the current classifier has a supported rule.
- An **unknown candidate** is preserved rather than overclassified.
- A **score** is relative utility under the current heuristic model, not exploitability.
- A successful schema `0.2.0` report states command identity and bounded enumeration completeness. Candidate-capacity exhaustion still fails before output; it is not silently converted into a partial report.
- Per-candidate `evidence` identifies raw, exact-suffix, and semantic-exact provenance; `full_sequence_valid` remains `null` until decoder evidence exists.
- Analysis completeness is independent from decoder validity. `complete: true` means every loader-derived executable region was scanned within the current candidate capacity, not that every candidate is a decoded-valid instruction sequence.
- A mitigation result is a static indicator, not a final security verdict. The canary field is an indicator, not proof that every function is stack-protected. The stripped field and section labels are section-table metadata indicators, not runtime loader authority. Text section labels are escaped for single-line report stability, JSON labels are byte-safe escaped, and ambiguous or contradictory executable section metadata is left unlabeled.
- Exploitability requires an independent vulnerability and relevant runtime conditions.

See [`docs/design/metric-boundaries.md`](docs/design/metric-boundaries.md), [`docs/design/evidence-provenance-model.md`](docs/design/evidence-provenance-model.md), and [`docs/semantic-taxonomy.md`](docs/semantic-taxonomy.md).

## Quick start on Ubuntu 24.04

Install required development tools:

```bash
sudo apt update
sudo apt install -y nasm binutils gcc gdb make python3 python3-venv \
  python3-pip pipx time git curl ca-certificates unzip zip
pipx ensurepath
```

Repository helpers:

```bash
make install-dev-deps-ubuntu
make dev-tools-check
make doctor
```

Build and validate:

```bash
make clean
make
make samples
make test
make validation-smoke
make patch-bundle-hygiene-smoke
```

Run the checkpoint demo:

```bash
make checkpoint-demo
DEMO_TARGET=/bin/ls MAX_DEPTH=4 make checkpoint-demo
```

See [`docs/onboarding.md`](docs/onboarding.md) for the full Make target tour and [`docs/demo.md`](docs/demo.md) for the checkpoint demonstration.

## Optional baseline tools

ROPgadget, Ropper, and ropr are comparison baselines. They are not runtime dependencies.

```bash
make install-baseline-tools-user
make baseline-tools-check
```

Manual setup:

```bash
pipx install ROPGadget
pipx install ropper
make install-rustup-user
. "$HOME/.cargo/env"
make install-ropr-user
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
```

Ubuntu's apt-provided Cargo may be too old for the current ropr release. The rustup helper installs a current user-local stable toolchain.

## Example usage

```bash
./build/x64lens version
./build/x64lens info /bin/ls
./build/x64lens mitigations /bin/ls
./build/x64lens gadgets --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --max-depth 4 /bin/ls
```

Generate and validate JSON:

```bash
./build/x64lens analyze --format json --max-depth 4 \
  ./tests/bin/gadgets > /tmp/x64lens-analysis.json
python3 -m json.tool /tmp/x64lens-analysis.json >/dev/null
python3 tools/validate-json-report.py \
  --mode fixture --require-schema 0.2.0 --expected-command analyze \
  --require-provenance /tmp/x64lens-analysis.json
```

The same flags are accepted in either documented order:

```bash
./build/x64lens analyze --max-depth 4 --format json <file>
./build/x64lens analyze --format json --max-depth 4 <file>
```

## Validation surface

Core checks:

```bash
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make build-tools-check
make sample-tools-check
make dev-tools-check
make test
make validate-gadget-fixture
make semantic-smoke
make schema-compat-smoke
make json-smoke
make analyze-smoke
make system-smoke
make capacity-smoke
make malformed-smoke
make mitigation-matrix-smoke
make section-label-smoke
make validation-smoke
make docker-test
make docker-validation-smoke
```

`make validation-smoke` is the local aggregate. It includes deterministic malformed-input and candidate-capacity checks. Docker remains a separate reproducibility check because engine availability is environment-dependent.

Hostile-input checks can also be run directly:

```bash
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
make section-label-smoke
make capacity-smoke
make docker-validation-smoke
```

The malformed-input runner records seed hashes, expected and observed exit codes, signals, timeout state, elapsed nanoseconds, and output sizes. Generated mutations are temporary by default. Compact result artifacts are written under `tests/results/malformed/` and remain ignored by Git. Patch 028 adds explicit program-header and section-header table-end wrap cases to keep checked arithmetic from regressing. Patch 030 preserves that baseline while adding dynamic-table malformed cases to the mitigation matrix. Patch 031 adds duplicate-`PT_DYNAMIC` rejection. Patch 032 keeps the malformed-smoke baseline unchanged while adding invalid dynamic string-table evidence to the mitigation matrix.


### Section-label hardening smoke

`make section-label-smoke` builds temporary ELF64 fixtures with controlled section-name metadata. It verifies that `.text` labels are preserved, newline-bearing section names are escaped in text output, high-bit section-name bytes remain JSON-safe, non-executable overlapping sections do not capture executable offsets, ambiguous overlapping executable sections remain unlabeled, and file-offset/virtual-address disagreement leaves records unlabeled. The target writes ignored JSON evidence under `tests/results/section-label/`.

The mitigation oracle creates controlled ELF64 program-header layouts independently of compiler defaults. It verifies exact loader-level mitigation and region facts, matching integrated JSON values, direct gadgets JSON values, and stable malformed failure behavior. Its ignored evidence is written under `tests/results/mitigation-matrix/`. Patch 034 expands the oracle to 24 valid cases, 14 malformed cases, and one unsupported fail-closed case; Patch 035 keeps those counts and adds a focused `section-label-smoke` harness; Patch 036 keeps the matrix counts while expanding the focused section-label harness to six cases. Coverage includes canary-present/canary-absent indicators, zero-length dynamic string-table negative evidence including the exact load-endpoint case, stripped and not-stripped section-table indicators, section-label fixture checks, valid non-`DT_NULL` dynamic tables, invalid dynamic string-table rejection, duplicate `DT_STRTAB` and `DT_STRSZ` rejection, over-cap string-table rejection, `DT_BIND_NOW`, `DT_FLAGS`, `DT_FLAGS_1`, full RELRO combinations, duplicate-`PT_DYNAMIC` rejection, and gadget command-path coverage for dynamic malformed inputs.

Patch bundle hygiene:

```bash
BUNDLE=/path/to/patch.zip make patch-bundle-hygiene
```

## Benchmark smoke workflow

Development smoke comparison:

```bash
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary-latest
```

These results verify measurement plumbing. They are not publication results. Patch 036 rejects non-positive run counts, invalid max-depth values, nonnumeric or negative timing/RSS fields, and mixed benchmark summaries by default. Small x64lens runs can still fall below GNU `time` display resolution. Sprint 12 replaces this with a higher-resolution runner before the research preview candidate.

See [`docs/benchmark-methodology.md`](docs/benchmark-methodology.md) and [`docs/benchmark-smoke-interpretation.md`](docs/benchmark-smoke-interpretation.md).

## Architecture

The core separation is mandatory:

```text
file mapping and bounds
  -> ELF and loader facts
  -> raw scanner
  -> exact pattern matcher
  -> semantic classifier
  -> scoring
  -> report identity and completeness facts
  -> text/JSON adapters
```

Future decoder facts, mitigation evidence, and output adapters must be added through bounded views or side-car records. They must not replace raw candidate facts or duplicate the analysis pipeline.

See [`docs/architecture.md`](docs/architecture.md), [`docs/design/decoder-roadmap.md`](docs/design/decoder-roadmap.md), [`docs/adr/0012-roadmap-expansion-and-research-release-gates.md`](docs/adr/0012-roadmap-expansion-and-research-release-gates.md), [`docs/adr/0013-deterministic-hostile-input-regression-harness.md`](docs/adr/0013-deterministic-hostile-input-regression-harness.md), [`docs/adr/0016-bounded-dynamic-table-view.md`](docs/adr/0016-bounded-dynamic-table-view.md), and [`docs/adr/0022-historical-findings-hardening.md`](docs/adr/0022-historical-findings-hardening.md).

## Roadmap and release gates

The canonical eighteen-sprint roadmap defines:

- Sprint 7 hostile-input hardening,
- Sprint 8 mitigation and metadata depth,
- Sprint 9 report identity, completeness, evidence provenance, and decoder-gap measurement,
- Sprint 10 primitive expansion,
- Sprint 11 reproducible corpus,
- Sprint 12 high-resolution benchmark infrastructure and `v0.1.0-rc1`,
- Sprints 13 through 18 comparative experiments, triage modeling, automation stabilization, infrastructure case study, replication freeze, and `v0.1.0`.

See [`docs/roadmap-18-sprints.md`](docs/roadmap-18-sprints.md) and [`docs/research-release-plan.md`](docs/research-release-plan.md).

## Versioning

The current integrated checkpoint is `v0.1.0-dev`. The tag remains local unless explicitly pushed.

Planned release sequence:

```text
v0.1.0-dev   integrated development checkpoint
v0.1.0-rc1   research preview candidate
v0.1.0       first research release
```

Schema `0.2.0` is the current producer contract. Patch 040 added report identity and complete-analysis state; Patch 041 adds candidate provenance compatibly while preserving Patch 040 and versioned `0.1.0` fixtures. Decoder-backed facts remain additive future Sprint 9 work.

See [`docs/versioning.md`](docs/versioning.md) and [`docs/design/schema-evolution.md`](docs/design/schema-evolution.md).

## Research and publication

The repository preserves the chain from implementation to evidence to paper:

```text
source and fixtures
  -> validators
  -> corpus manifest
  -> raw benchmark rows
  -> generated summaries
  -> claim-to-evidence matrix
  -> paper and release artifacts
```

See [`docs/publication-plan.md`](docs/publication-plan.md), [`docs/research-roadmap.md`](docs/research-roadmap.md), and [`docs/contracts/research-contract.md`](docs/contracts/research-contract.md).

## Ethics and safety

x64lens is intended for educational research, defensive binary triage, secure build validation, and authorized reverse engineering. It does not include exploit delivery, payload generation, remote scanning, or unauthorized target interaction.

See [`docs/ethics-and-safety.md`](docs/ethics-and-safety.md).

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

## Optional analysis and review tools

The core build and validation path does not require `checksec`, `radare2`/`rabin2`, `strace`, or `shellcheck`. They are useful local review tools for mitigation comparison, ELF metadata comparison, syscall/cleanup inspection, and shell-helper linting. Treat their output as comparator evidence with version-specific semantics, not as authoritative replacement for x64lens contracts.

Example inventory commands:

```bash
command -v checksec && checksec --version || true
command -v rabin2 && rabin2 -v || true
command -v r2 && r2 -v || true
command -v strace && strace -V || true
command -v shellcheck && shellcheck --version || true
```

Repository targets:

```bash
make analysis-tools-check
make readelf-comparison-smoke
make optional-tool-comparison-smoke
make shellcheck-smoke
```

`readelf` comparison is part of the normal native validation aggregate.
`checksec`, `rabin2`, `strace`, and `shellcheck` remain optional local review
tools; absence should not block core build/test validation. The direct
comparison helpers accept either `<target> <tool>` or `<tool> <target>` and
print an explicit target identity line so optional review logs can be audited.
