# Development Environment Plan

## Recommendation

Use a layered environment strategy:

1. **Primary daily development:** WSL2 Ubuntu 24.04 on Windows with VS Code Remote WSL.
2. **Reproducible build environment:** Docker/devcontainer using Ubuntu 24.04.
3. **Cloud/anywhere fallback:** GitHub Codespaces or Codex connected to the repository.
4. **Publication benchmarks:** native Ubuntu 24.04 or a clean dedicated VM with fixed CPU/RAM documentation.

## Why WSL2 first

WSL2 is the best daily development environment for this project if the main workstation is Windows. It gives a Linux userspace, clean access to NASM/binutils/GDB, fast edit-build-test loops, and excellent VS Code integration.

Recommended setup:

```powershell
wsl --install -d Ubuntu-24.04
wsl --set-default-version 2
wsl -l -v
```

Then inside Ubuntu:

```bash
sudo apt update
sudo apt install -y nasm binutils gcc gdb make python3 time git curl ca-certificates
git clone <repo-url>
cd x64lens
make scaffold-check
make
make test
```

## Why Docker/devcontainer second

Docker is the reproducibility layer, not the only development layer. It lets the project define exactly what dependencies are needed and gives professors or reviewers a fast way to build the project without manually configuring a system.

Recommended commands:

```bash
docker build -t x64lens-dev .
docker run --rm -it -v "$PWD":/work x64lens-dev bash
make
make test
```

## Why not commit a VM image

Do not commit a VM image to this repository, public or private.

Reasons:

- VM images are large and hostile to Git history.
- They quickly become stale.
- They can accidentally contain credentials, shell history, SSH keys, proprietary files, or malware samples.
- They are harder for professors and reviewers to inspect than a Dockerfile or devcontainer.
- They do not support reproducible research as well as declarative setup files.

If a VM is needed later, document how to build it rather than storing the VM itself. Future options include Vagrant, Packer, or a short manual `docs/vm-setup.md`.

## Benchmark caveat

WSL2 and Docker are excellent for development, but final publication benchmarks should be run on one stable, documented environment. Prefer native Ubuntu 24.04 or a clean VM where CPU model, RAM, storage, OS version, kernel version, and tool versions are recorded.

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
```

If root-owned generated files already exist, repair them once from WSL/Linux:

```bash
sudo chown -R "$(id -u):$(id -g)" build tests/bin tests/toy-src
make clean
```

The repository also provides:

```bash
make ownership-check
make fix-perms
```

`make fix-perms` is for local development convenience only. It should not be used in CI and it intentionally avoids changing `.git` ownership.

## Docker context hygiene

The `.dockerignore` file excludes `.git/`, `.local/`, generated build outputs, generated toy binaries, local course files, private context, proprietary samples, malware samples, and large VM artifacts. This keeps Docker images reproducible and prevents local-only project context from being copied into a container image.
