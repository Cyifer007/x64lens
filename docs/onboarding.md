# Onboarding and Local Development Checklist

This document provides a reproducible path for setting up a new Ubuntu-based development environment, validating required tools, building x64lens, running the test suite, and exercising every public Make target.

## Supported baseline environment

The primary development target is Ubuntu 24.04 on x86_64. WSL2 Ubuntu 24.04, a native Ubuntu host, or an Ubuntu VM are all acceptable for development. Docker is used as a reproducibility layer, not as the only supported development environment.

## Install development dependencies on Ubuntu

Install the baseline development packages:

```bash
sudo apt update
sudo apt install -y nasm binutils gcc gdb make python3 python3-venv python3-pip pipx time git curl ca-certificates unzip zip
pipx ensurepath
```

The repository also provides an explicit helper target:

```bash
make install-dev-deps-ubuntu
```

This target uses `sudo apt` and should be run only on a development machine where installing packages is expected.

## Validate the local toolchain

Run the environment diagnostics before building:

```bash
make build-tools-check
make sample-tools-check
make dev-tools-check
make doctor
```

The build-only check verifies the tools needed to assemble and link x64lens. The development check verifies the broader local validation toolchain used by tests, JSON validation, system-binary smoke checks, and benchmark smoke runs.

## Optional baseline tools

The baseline comparison harness can optionally compare x64lens against ROPgadget, Ropper, and ropr. These tools are not required to build or test x64lens.

Install them for user-local benchmarking:

```bash
make install-baseline-tools-user
```

Manual equivalent:

```bash
pipx install ROPGadget
pipx install ropper
# ropr may require a newer Rust/Cargo than Ubuntu 24.04 apt provides.
# Prefer rustup stable for the ropr baseline.
make install-rustup-user
. "$HOME/.cargo/env"
make install-ropr-user
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
```

Validate optional baseline availability:

```bash
make baseline-tools-check
REQUIRE_BASELINES=1 make baseline-tools-check
```

The first command reports optional tool status and succeeds even when the tools are missing. The second command fails when none of the optional baseline tools are available. `REQUIRE_BASELINES=1` is enforced only by baseline-aware checks and benchmark targets; normal development checks do not fail because optional baseline tools are absent.

## First build and validation sequence

A new contributor should run the following sequence from the repository root:

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make dev-tools-check
make clean
make
make samples
make test
make validate-gadget-fixture
make semantic-smoke
make json-smoke
make analyze-smoke
make system-smoke
make capacity-smoke
make malformed-smoke
make validation-smoke
```

If Docker is available:

```bash
make docker-available-check
make docker-build
make docker-test
make docker-validation-smoke
```

`make docker-test` rebuilds the development image before running tests, so Dockerfile dependency changes are not accidentally validated against a stale local image. Docker layer caching keeps repeat runs fast once the image is current.

Run smoke benchmarks after the correctness path passes:

```bash
RUNS=5 MAX_DEPTH=4 make bench-scanner-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
make bench-summary
```

## Make target tour

The table below lists the public Make targets. A new development environment should exercise the checks first, then the build/test targets, then Docker and benchmark targets as needed.

| Target | Purpose |
|---|---|
| `make` or `make all` | Build `build/x64lens`. |
| `make check-tools` | Compatibility alias for build-only dependency checking. |
| `make build-tools-check` | Verify NASM and GNU ld are available. |
| `make sample-tools-check` | Verify sample-corpus build tools are available. |
| `make dev-tools-check` | Verify the normal local validation toolchain. |
| `make baseline-tools-check` | Report optional baseline tool availability. |
| `make full-tools-check` | Require development tools and optional baseline tools. |
| `make doctor` | Print a full local environment report. |
| `make install-dev-deps-ubuntu` | Install Ubuntu development packages through `apt`. |
| `make install-baseline-tools-user` | Install optional baseline tools through `pipx`; attempts ropr when Cargo is ready. |
| `make install-rustup-user` | Install or update the user-local Rust stable toolchain through rustup. |
| `make install-ropr-user` | Install the optional ropr baseline when Cargo is new enough. |
| `make samples` | Build controlled toy binaries under `tests/bin/`. |
| `make test` | Run the core regression suite. |
| `make validate-gadget-fixture` | Validate controlled gadget fixture output. |
| `make scanner-smoke` | Compatibility alias for fixture validation. |
| `make pattern-smoke` | Compatibility alias for fixture validation after pattern matching. |
| `make arena-smoke` | Validate arena-backed candidate storage invariants. |
| `make semantic-smoke` | Validate semantic and scoring facts for the controlled fixture. |
| `make json-smoke` | Validate JSON output for the controlled fixture. |
| `make analyze-smoke` | Validate integrated text and JSON analysis output. |
| `make system-smoke` | Validate installed system ELF64 binaries. |
| `make capacity-smoke` | Verify candidate-arena exhaustion returns exit `6` without partial output. |
| `make malformed-smoke` | Run the deterministic 29-case hostile-input regression campaign. |
| `make fuzz-mutated-elf-smoke` | Compatibility alias for `malformed-smoke`. |
| `make validation-smoke` | Run the local pre-commit validation bundle, including malformed and capacity gates. |
| `make bench-scanner-smoke` | Run development-level x64lens scanner smoke benchmarking. |
| `make bench-smoke` | Compatibility alias for `bench-scanner-smoke`. |
| `make bench-baselines-smoke` | Run development-level x64lens plus optional baseline smoke benchmarking. |
| `make bench-summary` | Summarize all generated benchmark TSV files. |
| `make bench-summary-latest` | Summarize only the newest baseline-smoke TSV artifact. |
| `make checkpoint-demo` | Run the integrated controlled or system-binary checkpoint demonstration. |
| `make checkpoint-tag-help` | Print non-mutating local annotated-tag guidance. |
| `make script-perms-check` | Verify executable bits on shell/Python helper scripts. |
| `make scaffold-check` | Verify required repository structure. |
| `make diagrams-check` | Verify diagram source files exist. |
| `make public-docs-check` | Reject private or dialogue-style wording in public repository files. |
| `make planning-docs-check` | Verify canonical roadmap, release gates, schema plan, and Sprint 7 through Sprint 18 planning structure. |
| `make patch-bundle-hygiene BUNDLE=<zip>` | Verify public patch bundle hygiene. |
| `make docker-available-check` | Verify Docker is installed and reachable. |
| `make docker-build` | Build the development Docker image. |
| `make docker-shell` | Open a Docker shell without root-owned bind-mount artifacts. |
| `make docker-test` | Rebuild the development Docker image, then run clean build and core tests in Docker. |
| `make docker-validation-smoke` | Rebuild the image, then run the full native-equivalent validation bundle in Docker. |
| `make ownership-check` | Detect root-owned generated artifacts. |
| `make fix-perms` | Repair generated artifact ownership. |
| `make normalize-perms` | Normalize local source/script file permissions after ZIP extraction. |
| `make print-vars` | Print build variables. |
| `make clean` | Remove generated build and test outputs. |

## Expected validation posture

A local implementation patch should generally pass:

```bash
make validation-smoke
make docker-test
make docker-validation-smoke
RUNS=1 MAX_DEPTH=4 make bench-baselines-smoke
BUNDLE=/path/to/patch.zip make patch-bundle-hygiene
```

A documentation-only patch may use the lighter path:

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
```

Benchmark smoke results are development evidence only. Publication claims require the full benchmark methodology, controlled corpus documentation, repeated runs, baseline tool versions, exact commands, host metadata, raw result preservation, and explicit limitations.


## Hostile-input validation tour

Sprint 7 adds two explicit safety gates:

```bash
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make fuzz-mutated-elf-smoke
```

A successful malformed campaign reports 31 total cases and 28 malformed cases after Patch 028, with no signal or timeout. It writes ignored result and metadata artifacts under `tests/results/malformed/`. A successful capacity check confirms that exactly 4096 candidates produce a complete report and that the 4097th candidate triggers exit code `6` with no partial report.

Use the full Docker-equivalent gate after native validation:

```bash
make docker-validation-smoke
```

## Integrated analyze checkpoint

After the base validation path succeeds, run the checkpoint command directly:

```bash
./build/x64lens analyze --max-depth 4 ./tests/bin/gadgets
./build/x64lens analyze --format json --max-depth 4 ./tests/bin/gadgets > /tmp/x64lens-analyze.json
python3 tools/validate-json-report.py --mode fixture /tmp/x64lens-analyze.json
```

Use `analyze` for demos and end-to-end defensive triage examples. Use `gadgets --format json` when comparing directly against gadget enumeration baselines.

## Integrated checkpoint tour

After the normal build and validation tour, run:

```bash
make checkpoint-demo
DEMO_TARGET=/bin/ls MAX_DEPTH=4 make checkpoint-demo
make checkpoint-tag-help
```

The demo validates both human-readable and JSON integrated output. `checkpoint-tag-help` prints the local annotated tag commands without mutating the repository.


## Roadmap orientation

The canonical development plan is `docs/roadmap-18-sprints.md`. The earlier twelve-sprint file is retained only as a superseded compatibility reference. New implementation work should be checked against the active sprint plan, the research release plan, and the relevant design contracts before code changes begin.

## Mitigation oracle tour

After the broad malformed and capacity gates, run:

```bash
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
```

Expect 23 valid cases, 14 malformed cases, and one unsupported fail-closed case after Patch 033. Inspect the newest ignored JSON artifact under `tests/results/mitigation-matrix/`, then run `make validation-smoke` and `make docker-validation-smoke` to confirm aggregate integration. `make help` lists the principal development targets.

## Patch 032 validation addition

After Patch 033, `make mitigation-matrix-smoke` should report 23 valid cases, 14 malformed cases, and one unsupported fail-closed case. Use `make clean-results` before broad local text searches or release-package review when old ignored validation artifacts could confuse interpretation.
