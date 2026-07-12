# Sprint 09 Patch 043 Validation

## Scope

Patch 043 corrects research-evidence and public-release boundary defects found
while validating Patch 042. It does not change assembly runtime code, public
record layouts, schema `0.2.0`, candidate capacity, semantic classification, or
score policy.

Patch-generation base:

```text
commit: 1d61523cb93e38700bf4c009eead960547aaf431
```

## Corrective surfaces

Patch 043 validates and corrects:

1. strict ShellCheck compatibility;
2. target identity races between campaign inventory and measurement;
3. interrupted result publication;
4. Windows-invalid ZIP component characters and device aliases;
5. raw/effective ZIP-name disagreement and unsupported extra metadata;
6. common ZIP-container suffixes such as JAR and wheel files;
7. prefixed-return and control-flow-barrier parsing in objdump evidence;
8. campaign identity and retained parse diagnostics;
9. timestamped private attachment-name leakage in public docs; and
10. the embedded-decoder decision and development-versus-publication evidence
    boundary.

## Required focused checks

```bash
make patch-bundle-hygiene-smoke
make public-docs-hygiene-smoke
make decoder-gap-hardening-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
```

Expected focused outputs:

```text
patch-bundle-hygiene-smoke: ok cases=55 accepted=6 rejected=49
public-docs-hygiene-smoke: ok cases=3 accepted=1 rejected=2
decoder-gap-hardening-smoke: ok parser=1 snapshots=2 publication_interruptions=8
shellcheck-smoke: ok
```

## Native analyzer regression

```bash
make normalize-perms
make script-perms-check
make scaffold-check
make diagrams-check
make public-docs-check
make planning-docs-check
make clean
make
make samples
MALFORMED_TIMEOUT=2 make validation-smoke
```

The runtime acceptance rule is no change to analyzer facts or failures:

- program headers and file-backed `PT_LOAD + PF_X` regions remain executable
  authority;
- raw, exact, semantic-exact, unknown, and scored counts retain their meanings;
- `gadgets` and `analyze` remain report-parity paths;
- candidate overflow remains exit `6`, empty stdout, and the stable diagnostic;
- malformed input remains fail-closed without partial stdout.

## Decoder-gap campaigns

```bash
rm -rf tests/results/decoder-gap
make decoder-gap-smoke
rm -rf tests/results/decoder-gap
make decoder-gap-campaign
```

The generated manifest format is `x64lens-decoder-gap-manifest-v2`. Every target
record must identify the source path and the retained immutable snapshot that
both x64lens and objdump analyzed. Command paths retained in each target
directory must continue to resolve after result publication.

The controlled fixture must retain zero exact-boundary disagreements. Selected
system counts remain observations because system binaries and objdump versions
vary by host.

## Transaction probes

Validation must interrupt publication before backup, after backup, before new
publication, and after new publication with both `SIGINT` and `SIGTERM`.
At every point, either the prior recognized result or one complete new result
must remain available. An unrelated destination must remain unchanged.

A two-target delayed-mutation probe must show that source mutation after snapshot
creation cannot change the bytes analyzed or the SHA-256 identity published for
the snapshot.

## ZIP policy probes

The production wrapper must reject under arbitrary roots:

- `<`, `>`, `"`, `|`, `?`, and `*` in Windows path components;
- `COM¹` through `COM³`, `LPT¹` through `LPT³`, `CONIN$`, and `CONOUT$`;
- raw/effective member-name disagreement such as a raw NUL suffix;
- Unicode-path metadata that disagrees with the visible member;
- unsupported or malformed extra fields;
- file/directory metadata contradictions;
- JAR, wheel, and other documented nested archive containers.

The checker must make its decision from ZIP metadata without extracting members.

## Docker checks

```bash
make docker-build
make docker-test
make docker-context-hygiene-smoke
MALFORMED_TIMEOUT=2 make docker-validation-smoke
```

A Buildx activity-metadata failure outside the repository is an environment
defect only after the complete product path passes with writable isolated
Buildx metadata.

## Acceptance

Patch 043 is accepted when all focused, native, campaign, interruption, archive,
public-boundary, and qualified Docker checks pass and the checkpoint tag remains
unchanged.

## Post-validation disposition

Authoritative local validation passed the analyzer, native aggregate, qualified
Docker aggregate, immutable snapshot binding, and decoder-free runtime boundary.
Patch 043 was not accepted as the final campaign-hardening state because focused
review found a post-rename signal window, measured-child process leakage,
incomplete objdump prefix/return normalization, local/central ZIP metadata and
ZIP64 gaps, and real transfer basenames in a public negative fixture.

Patch 044 is the required corrective patch. Its validation record supersedes
the focused case counts and transaction/parser acceptance claims above while
preserving the Patch 043 runtime and decoder decision.
