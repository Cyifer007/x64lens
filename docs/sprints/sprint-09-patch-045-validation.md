# Sprint 09 Patch 045 Validation

## Status

Accepted Sprint 9 closeout matrix; Sprint 10 is next.

## Purpose

Patch 045 closed Sprint 9 by correcting the strict public-document lint defect,
removing documentation drift, reconciling schema and metric status, recording
the defensive deployment profile, and advancing Sprint 10 to the next
implementation tranche.

Patch 045 changes development/release tooling and documentation only. It does
not change analyzer assembly, internal record layouts, CLI behavior, JSON schema,
pattern recognition, semantic classification, scoring, or capacity semantics.

## Required invariants

- Program headers and file-backed `PT_LOAD + PF_X` ranges remain executable
  authority.
- Section and dynamic metadata remain bounded evidence or annotations.
- Raw, exact, semantic-exact, unknown, decoder-backed, and scored facts remain
  distinct.
- Schema `0.2.0` remains the current producer contract.
- Candidate overflow remains exit code `6` with empty stdout and the stable
  unsupported-feature diagnostic.
- Malformed parse failures emit no partial stdout.
- The default runtime remains static, dependency-free, decoder-free, and
  single-worker.
- Public artifacts contain no local paths, transfer history, private state, or
  generated evidence.

## Review-finding disposition

### Strict shell lint

The WSL UNC path expression in `tools/check-public-docs.sh` must be quote-safe
under strict ShellCheck while preserving the functional rejection fixture. The
smoke also adds a direct Linux home-path case.

Expected:

```text
public-docs-hygiene-smoke: ok cases=10 accepted=1 rejected=9
shellcheck-smoke: ok
```

### Docker Buildx metadata

The default and qualified Docker paths must be classified separately. A failure
to write Buildx activity metadata is an environment failure when the same build,
test, context-hygiene, and aggregate commands pass with a writable
`BUILDX_CONFIG`.

### Historical archive diagnostics

Archive allow/reject outcome is the durable policy contract. Exact reason text
is compared only by tests that explicitly declare it stable. Stronger diagnostic
wording does not become a policy regression when the expected outcome remains
correct.

## Static and documentation commands

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make public-docs-hygiene-smoke
make planning-docs-check
git diff --check
```

## Native closeout commands

```bash
make clean
make
make samples
make test
make schema-compat-smoke
make capacity-smoke
MALFORMED_TIMEOUT=2 make malformed-smoke
MALFORMED_TIMEOUT=2 make mitigation-matrix-smoke
make section-label-smoke
make benchmark-integrity-smoke
make patch-bundle-hygiene-smoke
make decoder-gap-hardening-smoke
make decoder-gap-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
MALFORMED_TIMEOUT=2 make validation-smoke
make sprint-closeout-smoke
```

## Docker commands

```bash
make docker-available-check
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

When the default Buildx activity path is not writable, rerun the complete Docker
sequence with a temporary writable `BUILDX_CONFIG` and retain both the default
failure and qualified result.

## Expected stable results

```text
schema-compat-smoke: ok legacy=0.1.0 patch040=0.2.0 current=0.2.0 formal_rejections=13 semantic_rejections=7
public-docs-hygiene-smoke: ok cases=10 accepted=1 rejected=9
patch-bundle-hygiene-smoke: ok cases=64 accepted=7 rejected=57 wrapper_replays=64
decoder-gap-hardening-smoke: ok parser=2 snapshots=2 publication_interruptions=10 measured_signal_cleanup=2
benchmark-integrity-smoke: ok identity_groups=3
shellcheck-smoke: ok
validation-smoke: ok
sprint-closeout-smoke: ok
```

The exact-capacity fixture must retain 4,096 candidates. The 4,097th candidate
must return exit code `6`, write zero stdout bytes, and emit exactly:

```text
error: unsupported binary feature
```

## Artifact acceptance

The raw patch, patch ZIP, source identity, changed-file manifest, internal ZIP
manifest, delivery manifest, and checksum list must agree. Public ZIP validation
runs before extraction. Any artifact regeneration requires checksum
regeneration.

## Sprint decision

This matrix is the Sprint 9 closeout gate. Patch 045 records it as satisfied:
Sprint 9 is closed, and Sprint 10 begins with bounded primitive expansion.
Decoder integration and in-process parallelism remain optional profiles to be
measured separately rather than Sprint 10 defaults.
