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
make docker-validation-smoke
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
make docker-validation-smoke
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

## Shell script executable bits changed unexpectedly

Symptom:

```text
modified: benchmarks/scripts/*.sh
modified: tools/*.sh
modified: tests/run-tests.sh
```

with no content diff except mode changes.

Cause: ZIP extraction, Windows filesystem handling, or a cross-platform file operation may drop executable bits.

Fix:

```bash
make normalize-perms
make script-perms-check
git status
```

Expected tracked shell helpers should be executable. If Git still shows mode-only changes, inspect with:

```bash
git diff --summary
```

## `make malformed-smoke` reports a failed case

Inspect the reported TSV and metadata paths under `tests/results/malformed/`. The failure row records expected and observed exit status, signal, timeout state, output sizes, and a diagnostic preview. Re-run only after preserving the evidence needed to understand the defect.

A signal, timeout, unexpected success, or unsafe bounds acceptance is a parser regression. Minimize the input and promote it into `tests/malformed/regressions/` with a documented expected result before treating the issue as closed.

## `make capacity-smoke` emits partial output

Candidate-capacity exhaustion must return exit code `6`, leave stdout empty, and emit exactly:

```text
error: unsupported binary feature
```

Any partial text or JSON output is a contract failure because the report would appear complete while omitting candidates.

## `make mitigation-matrix-smoke` reports a failed case

First identify the named valid or malformed case in stderr. For a valid case, compare focused `mitigations` text and `analyze --format json` output. The `non-executable-load` case must emit the exact region line `  none discovered from PT_LOAD + PF_X`; an expectation of only `  none` indicates stale harness text, not a Make dependency failure. For a malformed case, confirm all three command paths return exit code `5`, emit no stdout, and emit exactly `error: malformed or truncated ELF`. Do not weaken the expected matrix to accommodate an unexplained parser or reporter change.
