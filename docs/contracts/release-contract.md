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
- [ ] `make patch-bundle-hygiene-smoke` passes,
- [ ] the actual source/release ZIP passes `make patch-bundle-hygiene`,
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
- [ ] controlled decoder-gap reconciliation passes and the decoder decision is
      documented,
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

The exclusion policy applies under every archive-root layout. Bundle validation
must also reject unsafe or non-portable member paths, duplicate/case-colliding
members, symbolic links, encrypted members, local environment files except an
explicit public example, secret-bearing directories, and nested archives. The
checker inspects ZIP metadata without extraction. Arbitrary archive/member
comments and special-file entries are also prohibited; an archive-level
40/64-character hexadecimal source identity is permitted.

Validate source patches with:

```bash
make patch-bundle-hygiene-smoke
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

Sprint 8 closes after Patch 039. Release candidates after this point must keep
Patch 036 through Patch 039 evidence-hygiene gates in the normal validation
path: byte-safe JSON, Docker context hygiene, benchmark TSV integrity,
section-label trust rules, `readelf` comparison, optional comparator identity
checks, and planning-document consistency.

Patch 040 completes the initial schema `0.2.0` report-identity and successful-
analysis completeness foundation. Do not promote performance, coverage, or
decoded-gadget parity claims until per-candidate provenance, decoder-gap
measurement, target/corpus provenance, and publication-grade benchmark
methodology are complete.


## Sprint 9 Patch 040 release note

Current release-candidate validation must include `make schema-compat-smoke` and
must require schema `0.2.0` plus expected command identity for current
`gadgets` and `analyze` reports. The retained historical `0.1.0` schema is a
compatibility artifact, not the current producer contract.

A release artifact must not describe capacity failure as an emitted truncated
report. The existing 4097-candidate case returns exit code `6` before stdout.
Any future partial-report mode requires a separate reviewed contract and release
gate.


## Sprint 9 Patch 041 release-hygiene update

Research-preview candidates must preserve candidate provenance on every current
report, validate both formal schema and semantic cross-field rules, reject
prefixed generated paths in source bundles, compare stable diagnostics
byte-for-byte, and stratify benchmark summaries by tool and schema identity.
Patch 040 reports remain compatibility fixtures; they are not current-producer
fixtures after Patch 041.


## Sprint 9 Patch 042 release-hygiene update

Patch and source archives must pass the portable bundle-policy regression gate
and the actual artifact check. A clean repository tree does not substitute for
archive inspection because archive roots, case behavior, symlinks, and injected
members can differ from the worktree.

`make decoder-gap-smoke` is a release-preview development gate for the
controlled fixture. `make decoder-gap-campaign` preserves host-dependent
comparison evidence but remains separate from publication-grade benchmarks.
The campaign informs the embedded-decoder decision and must not alter runtime
facts or be treated as decoded-valid candidate output.

## Sprint 9 Patch 043 release-hygiene update

Public ZIP checks must run before extraction and validate raw/effective member
names, recognized extra metadata, portable path semantics, file-type metadata,
duplicate and case-colliding names, encryption, comments, nested containers,
and private/generated paths independently of archive-root depth.

Decoder-gap artifacts used for a release decision must identify immutable bytes
actually analyzed and must survive interrupted replacement without losing a
recognized prior result. The default release artifact remains decoder-free; a
future decoder-enabled profile requires separate identity, dependencies,
validation, and benchmark evidence.

## Local and central ZIP metadata rule

A public ZIP is accepted only when bounded local-header metadata agrees with the
central directory and recognized extra fields have valid semantics. Release
checks remain non-extracting. Artifact checksum manifests are siblings of the
final artifacts; any regeneration changes the authoritative hash set.

## Sprint 9 closeout release rule

Before a sprint closeout artifact is accepted:

- strict shell lint and the complete native aggregate must pass;
- required checksum manifests must be supplied next to the final artifacts;
- public documentation and archive-policy gates must pass;
- environment-only Docker metadata failures must be separated from Dockerfile or product failures and followed by a qualified writable-metadata rerun;
- optional decoder or parallel profiles must not replace the dependency-free reference artifact.

Exact diagnostic wording from development validators is stable only when a contract or fixture explicitly version-controls it. Allow/reject outcomes remain the primary archive-policy compatibility surface.

## Public textual-content gate

A publishable source or patch archive must pass both:

```bash
BUNDLE=/path/to/public.zip make patch-bundle-hygiene
PUBLIC_BUNDLE=/path/to/public.zip make public-bundle-content-check
```

The first gate validates ZIP metadata without extraction. The second reads bounded eligible text members in memory and rejects prohibited host paths, attachment-history identifiers, workflow narration, and unsafe deleted or added lines in `.patch` and `.diff` members. A local application package that contains private context is not a public release archive.
