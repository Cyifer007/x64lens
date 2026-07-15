# Development Environment Plan

## Recommendation

Use a layered environment strategy:

1. **Primary daily development:** WSL2 Ubuntu 24.04 on Windows with VS Code Remote WSL.
2. **Reproducible build environment:** Docker/devcontainer using Ubuntu 24.04.
3. **Cloud/anywhere fallback:** GitHub Codespaces or another isolated Linux development container connected to the repository.
4. **Publication benchmarks:** native Ubuntu 24.04 or a clean dedicated VM with fixed CPU/RAM documentation.

## Why WSL2 first

WSL2 Ubuntu 24.04 is the documented primary development profile for contributors
working on Windows. It provides a Linux userspace with NASM, binutils, GDB, and
VS Code Remote WSL integration.

Recommended setup:

```powershell
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2
wsl -l -v
```

Then inside Ubuntu:

```bash
sudo apt update
sudo apt install -y nasm binutils gcc gdb make python3 python3-jsonschema python3-venv python3-pip pipx time git curl ca-certificates unzip zip
git clone <repo-url>
cd x64lens
make scaffold-check
make
make test
```

## Why Docker/devcontainer second

Docker is the reproducibility layer, not the only development layer. It lets the project define exactly what dependencies are needed and gives reviewers a fast way to build the project without manually configuring a system.

Recommended commands:

```bash
docker build -t x64lens-dev .
make docker-shell
make
make test
```

## Why not commit a VM image

Do not commit a VM image to this repository, public or private.

Reasons:

- VM images are large and hostile to Git history.
- They quickly become stale.
- They can accidentally contain credentials, shell history, SSH keys, proprietary files, or malware samples.
- They are harder for reviewers to inspect than a Dockerfile or devcontainer.
- They do not support reproducible research as well as declarative setup files.

If a VM is needed later, document how to build it rather than storing the VM itself. Future options include Vagrant, Packer, or a short manual `docs/vm-setup.md`.

## Benchmark caveat

WSL2 and Docker are excellent for development, but final publication benchmarks should be run on one stable, documented environment. Prefer native Ubuntu 24.04 or a clean VM where CPU model, RAM, storage, OS version, kernel version, and tool versions are recorded.


## Ubuntu dependency bootstrap

Install the standard development toolchain on Ubuntu 24.04 with:

```bash
sudo apt update
sudo apt install -y nasm binutils gcc gdb make python3 python3-jsonschema python3-venv python3-pip pipx time git curl ca-certificates unzip zip
pipx ensurepath
```

The repository provides explicit dependency-checking targets:

```bash
make build-tools-check
make sample-tools-check
make dev-tools-check
make baseline-tools-check
make doctor
```

Optional baseline tools are installed separately because they are not required to build or test x64lens. ROPgadget and Ropper are Python CLI tools installed through `pipx`; ropr is a Rust CLI tool and may require a newer Cargo than the Ubuntu 24.04 apt package provides:

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

Use `make install-dev-deps-ubuntu` and `make install-baseline-tools-user` only on development hosts where installing packages and user-local tools is expected. Use `make install-rustup-user` followed by `make install-ropr-user` when ropr is required and apt-provided Cargo is too old.

## Sprint 1 environment acceptance criteria

Sprint 1 is not complete until one reliable environment can run:

```bash
make clean
make
make samples
make test
./build/x64lens version
./build/x64lens help
```

After `info` is implemented, the environment must also run:

```bash
./build/x64lens info /bin/ls
```

## Docker bind-mount ownership rule

When running Docker against a bind-mounted repository, never run the development container as root if the container will create build artifacts in the mounted tree. A root container can create files such as `build/*.o`, `build/x64lens`, and generated toy binaries that the WSL/Linux user cannot later delete with `make clean`.

Preferred commands:

```bash
make docker-build
make docker-shell
```

or directly:

```bash
docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD":/work \
  -w /work \
  x64lens-dev bash
```

Run Docker validation with:

```bash
make docker-test
make docker-validation-smoke
```

`make docker-test` rebuilds the development image and runs the core suite. `make docker-validation-smoke` runs the full native-equivalent aggregate, including deterministic malformed-input and candidate-capacity gates. Both rebuild first so Dockerfile dependency changes are not tested against a stale image.

If root-owned generated files already exist, repair them once from WSL/Linux:

```bash
sudo chown -R "$(id -u):$(id -g)" build tests/bin tests/toy-src
make clean
```

The repository also provides:

```bash
make ownership-check
make fix-perms
make normalize-perms
```

`make fix-perms` is for generated-artifact ownership repair. It should not be used in CI and it intentionally avoids changing `.git` ownership. `make normalize-perms` is a local hygiene target for correcting overly permissive file modes after ZIP patch extraction; it avoids `.git`, `.local`, `build`, and generated test binaries.

## Docker context hygiene

The `.dockerignore` file excludes `.git/`, `.local/`, generated build outputs, generated toy binaries, local course files, private context, proprietary samples, malware samples, and large VM artifacts. This keeps Docker images reproducible and prevents local-only project context from being copied into a container image.


## Analyze command environment requirements

`analyze` has no additional runtime dependency beyond the existing x64lens binary. It reuses the same build tools, fixture tools, JSON validation helper, and optional baseline tooling already documented for Sprint 5. The command is covered by:

```bash
make analyze-smoke
make system-smoke
make capacity-smoke
make malformed-smoke
make validation-smoke
```

## Local environment files and Docker context

Patch 036 excludes `.env` and `.env.*` from the Docker build context so local environment files do not enter development images. Future sample files should use `.env.example`, which is explicitly allowlisted. Do not place secrets in repository files or Docker contexts.

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
tools; absence should not block core build/test validation.

## Strict shell-helper lint

`make shellcheck-smoke` is optional and advisory by default. When `shellcheck` is
installed, `SHELLCHECK_STRICT=1 make shellcheck-smoke` can be used as a local
pre-commit gate. Intentional literal shell snippets in install hints and ordered
path-boundary rules in bundle hygiene checks should be documented in source when
they need lint suppression.

The optional comparison helpers accept both argument orders below and print the
resolved target identity before output:

```bash
bash tools/compare-checksec.sh ./tests/bin/minimal_pie_canary ./build/x64lens
bash tools/compare-checksec.sh ./build/x64lens ./tests/bin/minimal_pie_canary
bash tools/compare-rabin2.sh ./tests/bin/minimal_pie_canary ./build/x64lens
bash tools/compare-rabin2.sh ./build/x64lens ./tests/bin/minimal_pie_canary
```


## Formal report-schema validation

The development environment includes `python3-jsonschema` so schema compatibility tests can apply Draft 2020-12 rules to retained fixtures. This package is not linked into or invoked by the x64lens runtime.


## Sprint 9 decoder-gap development tools

`objdump` from GNU binutils and `/usr/bin/time` are required development tools
for the controlled decoder-gap gate. The campaign also uses the canonical JSON
validator and `python3-jsonschema`; none of these become runtime dependencies of
the x64lens binary.

```bash
make decoder-gap-smoke
make decoder-gap-campaign
```

The controlled command is part of aggregate validation. The system campaign is
host-dependent evidence and remains separate. Generated artifacts live under
`tests/results/decoder-gap/` and are removed by `make clean-results`.

## Buildx metadata in restricted environments

Some managed environments permit Docker daemon access but prevent Buildx from updating its default activity metadata directory. Treat this separately from a Dockerfile or analyzer failure. A qualified validation run may use a writable, per-run Buildx configuration:

```bash
export BUILDX_CONFIG="$(mktemp -d "${TMPDIR:-/tmp}/x64lens-buildx.XXXXXX")"
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
rm -rf "$BUILDX_CONFIG"
```

Retain the default failure and qualified rerun as separate evidence. Do not weaken Docker context hygiene or product validation to accommodate a metadata-path restriction.

## Sprint 10 Patch 046 dependency surface

The ordered multi-pop family uses existing NASM source modules and fixed records.
It adds no runtime package, shared library, decoder, worker runtime, or helper
process. Python and `jsonschema` remain development/CI validation dependencies,
not x64lens runtime dependencies.
