# Troubleshooting

This document captures known development-environment failures and the preferred fix path. It is intentionally practical because x64lens is being developed as both a research artifact and a production-grade tool.

## `make clean` fails with `Permission denied` under `build/`

### Symptom

```text
rm -rf build
rm: cannot remove 'build/main.o': Permission denied
rm: cannot remove 'build/x64lens': Permission denied
make: *** [Makefile: clean] Error 1
```

### Root cause

A Docker container was run as `root` while the repository was bind-mounted into the container. The container then created files in the host repository as UID `0`, so the normal WSL/Linux user cannot delete them.

This is not an assembly, NASM, linker, or Makefile compilation problem. It is a file ownership problem.

### Immediate repair

From the repository root in WSL/Linux:

```bash
sudo chown -R "$(id -u):$(id -g)" build tests/bin tests/toy-src
make clean
```

Alternative blunt repair for a local-only working tree:

```bash
sudo chown -R "$USER:$USER" .
make clean
```

Use the narrower command first when possible.

### Prevent recurrence

Use the repository Docker targets:

```bash
make docker-build
make docker-shell
make docker-test
```

These targets run the container with the caller's numeric UID/GID:

```bash
--user "$(id -u):$(id -g)"
```

When invoking Docker manually, use:

```bash
docker run --rm -it \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -v "$PWD":/work \
  -w /work \
  x64lens-dev bash
```

### Verification

After repair:

```bash
make ownership-check
make clean
make
make test
make docker-test
```

Expected result:

```text
ownership-check: ok
tests: ok
```

## Docker build context unexpectedly includes private or generated files

### Symptom

Docker build output shows a large build context, or private/local files appear inside the container image.

### Fix

Review `.dockerignore`. It should exclude:

- `.git/`,
- `.local/`,
- `build/`,
- `tests/bin/`,
- generated toy binaries,
- local course files,
- private/proprietary/malware sample directories,
- VM images and ZIP files.

Then rebuild:

```bash
make docker-build
```


## Source files are world-writable after extracting a patch ZIP

### Symptom

`ls -l` shows source or documentation files with modes such as `-rw-rw-rw-` or directories with `drwxrwxrwx`.

### Cause

Some ZIP extraction paths preserve permissive archive modes. Git usually tracks only the executable bit, but local world-writable source files are noisy and should be corrected.

### Fix

```bash
make normalize-perms
```

This target avoids `.git`, `.local`, `build`, and generated test binaries. It restores normal repository files to `0644`, directories to `0755`, and shell scripts to executable mode.
