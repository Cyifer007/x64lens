# Release Contract

## Release classes

x64lens uses three release classes in the current roadmap:

| Class | Tag | Meaning |
|---|---|---|
| Development checkpoint | `v0.1.0-dev` | Known-good integrated prototype. May remain local. |
| Research preview candidate | `v0.1.0-rc1` | Hardened preview suitable for structured faculty and external feedback. |
| First research release | `v0.1.0` | Reproduced comparative evidence, case study, replication package, and publication-ready artifact. |

## Universal release checklist

Before any publishable tag:

- [ ] working tree is clean,
- [ ] `make clean && make` passes,
- [ ] `make test` passes,
- [ ] `make validation-smoke` passes,
- [ ] `make docker-test` passes on the release environment,
- [ ] `make docker-validation-smoke` passes when malformed-input and capacity gates are release-relevant,
- [ ] `make public-docs-check` passes,
- [ ] `make planning-docs-check` passes,
- [ ] README and CLI documentation are current,
- [ ] `CHANGELOG.md` has one current `Unreleased` section,
- [ ] tool and schema versions match output and docs,
- [ ] benchmark and corpus identifiers are recorded,
- [ ] security, ethics, limitations, and threats-to-validity docs are current,
- [ ] release artifacts and SHA-256 checksums verify.

## Research preview gate

Before `v0.1.0-rc1`:

- [ ] hostile-input mutation smoke has no crashes, signals, timeouts, unexpected success, or partial malformed-output reports,
- [ ] parser regressions are committed,
- [ ] candidate-capacity exhaustion is explicit and any intentional partial analysis exposes machine-readable completeness and truncation,
- [ ] mitigation fixtures cover no, partial, and full RELRO plus canary indicators,
- [ ] evidence provenance is machine-readable,
- [ ] schema `0.2.0` validators pass,
- [ ] preview corpus is reproducible and hashed,
- [ ] high-resolution benchmark runner is validated,
- [ ] pilot baseline comparison is preserved,
- [ ] preview reproduction instructions are complete.

## First research release gate

Before `v0.1.0`:

- [ ] fixed comparative campaign is complete,
- [ ] raw rows and generated summaries are preserved,
- [ ] coverage definitions are reconciled,
- [ ] infrastructure case study is reproducible,
- [ ] schema and CLI are frozen for the release,
- [ ] clean-environment reproduction rehearsal passes,
- [ ] claim-to-evidence matrix is complete,
- [ ] paper and repository limitations agree.

## Artifact expectations

```text
x64lens-<version>-linux-x86_64
x64lens-<version>-source.zip
x64lens-<version>-checksums.sha256
x64lens-<version>-version.txt
x64lens-<version>-benchmark-smoke.tsv
x64lens-<version>-benchmark-smoke.meta
x64lens-<version>-reproduction.md
```

Research data and paper source may be separate archives when size or review workflow makes that clearer.

## Patch and release bundle hygiene

Public source bundles must exclude:

- `.git/`,
- `.local/`,
- `build/`,
- `tests/bin/`,
- generated toy binaries,
- generated benchmark results unless the artifact explicitly packages approved results,
- object files,
- private/course documents,
- nested ZIP files.

Validate source patches with:

```bash
BUNDLE=/path/to/patch.zip make patch-bundle-hygiene
```

Project context bundles remain separate from public source patches.

## Tag and checksum rule

Tags point to the exact validated commit. Checksums are generated after artifacts are final. Any artifact change requires checksum regeneration. Signed releases remain future work.

## Mitigation-oracle release gate

A research preview or release candidate must pass the deterministic mitigation matrix in the documented native and Docker environments. The retained evidence must identify the seed and generated fixtures by SHA-256, report all case outcomes, and contain no failed record.

## Sprint 8 Patch 036 release-hygiene note

Release candidates must not be cut from evidence that contains invalid JSON, local environment files in Docker contexts, empty benchmark artifacts, negative timing/RSS values, or silently mixed benchmark summaries. Patch 036 hardens these development checks, but the research preview still requires the planned schema/provenance and publication-benchmark gates before public performance or coverage claims.


## Patch 037 release note

Release candidates must pass `make readelf-comparison-smoke` and
`make benchmark-integrity-smoke`. Optional `checksec` and `rabin2 -I` evidence
can support reviewer confidence, but release claims must identify them as
external comparator output with version-specific semantics.

## Sprint 8 closeout release note

Sprint 8 closes after Patch 038. Release candidates after this point must keep
Patch 036 through Patch 038 evidence-hygiene gates in the normal validation
path: byte-safe JSON, Docker context hygiene, benchmark TSV integrity,
section-label trust rules, `readelf` comparison, optional comparator identity
checks, and planning-document consistency.

The next release-blocking design work is Sprint 9 schema and provenance. Do not
promote performance, coverage, or decoded-gadget parity claims until schema
`0.2.0`, completeness metadata, decoder-gap measurement, and publication-grade
benchmark methodology are complete.
