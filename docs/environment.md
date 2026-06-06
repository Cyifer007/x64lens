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
