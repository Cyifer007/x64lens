# Sprint 11 Patch 057 Validation

## Purpose

Patch 057 is the smallest corrective patch for the diagnostic-runner, corpus,
cleanup, and non-root-oracle defects discovered after Patch 056. It deliberately
defers baseline adapters until the measurement foundation is trustworthy.

No analyzer assembly, CLI, JSON schema, semantic class, score, candidate
capacity, arena size, decoder policy, or worker policy changes.

## Changed public implementation surface

```text
benchmarks/scripts/diagnostic-runner.py
benchmarks/scripts/build-provisional-corpus.py
tools/diagnostic-runner-smoke.py
tools/sprint11-diagnostic-reference-smoke.py
tools/provisional-corpus-smoke.py
Makefile
```

## Focused runner validation

```bash
make diagnostic-tools-check
make diagnostic-runner-smoke
make sprint11-diagnostic-reference-smoke
```

Expected smoke banner:

```text
diagnostic-runner-smoke: ok success_rows=6 failure_rows=2 overwrite_rejected=1 descendants_cleaned=1 invalid_specs_rejected=2 source_mutations_rejected=1 unsafe_artifacts_rejected=1 target_nonexecution=1 locked_cleanup=1
```

The platform check must confirm an executable sealed tool/probe memfd and an
explicit `MFD_NOEXEC_SEAL` target memfd. The smoke must prove:

- a measured process cannot change the target from `0444` to executable mode;
- direct execution of the target memfd fails;
- the target retains `F_SEAL_EXEC` plus write/size/seal protection;
- tool, target, and timer-probe identities still match retained hashes;
- successful, nonzero, timeout, extractor, interruption, no-replace, and unsafe-
  artifact outcomes retain their existing contracts; and
- a staging tree containing a mode-`000` directory is removed completely.

On a kernel without `MFD_NOEXEC_SEAL`, the focused runner gate must fail as an
environment prerequisite rather than claim weaker protection.

## Focused corpus validation

```bash
make corpus-tools-check
make provisional-corpus-smoke
```

Expected smoke banner:

```text
provisional-corpus-smoke: ok targets=24 rebuilds=2 invalid_specs=8 tamper_cases=5 interruption_cleanup=3 capture_limits=1 clean_guards=1 make_clean_guards=1 membership_rejections=1
```

The smoke retains the Patch 056 two-build 24-target reproducibility matrix and
adds required proof that:

- tool metadata commands leave `command-workdir` empty;
- a compiler-created undeclared side member rejects publication;
- the exact retained file and directory set is enforced after checksum
  regeneration;
- early interruption and a failed compiler with mode-locked staging content
  leave no stage or final result;
- `clean-provisional-corpus` is phony;
- overriding `PROVISIONAL_CORPUS_PATH` cannot redirect deletion;
- only the specification-derived, fully verified corpus is removed; and
- checksum tamper probes pass as the non-root validation user.

## Full native acceptance

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make corpus-tools-check
make provisional-corpus-smoke
make diagnostic-tools-check
make diagnostic-runner-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make clean
make
make samples
make test
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

The complete native gate must preserve:

```text
candidate capacity: 4096
candidate 4097: exit 6 before stdout
malformed parse failure: no partial stdout
schema: 0.2.0
command arena: 819200 bytes
```

## Container and parity acceptance

```bash
make docker-available-check
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make native-docker-json-parity-smoke
```

The provisional corpus smoke must pass under the configured non-root container
user. A default Buildx metadata-path failure is an environment result only when
a qualified writable-metadata rerun completes the full Docker matrix.

## Public artifact acceptance

The final-file public overlay must pass:

```bash
BUNDLE=/path/to/public-overlay.zip make patch-bundle-hygiene
PUBLIC_BUNDLE=/path/to/public-overlay.zip make public-bundle-content-check
PUBLIC_BUNDLE=/path/to/public-overlay.zip \
PUBLIC_BUNDLE_SHA256=<sha256> \
  make public-overlay-verify
```

## Expected next step

After Patch 057 is empirically accepted, Patch 058 may add normalized ROPgadget,
Ropper, and ropr adapters. It must preserve baseline-specific task definitions,
version identity, command scope, duplicate/canonicalization policy, and failed
rows. Patch 059 then produces development summaries and the engineering gap
register.
