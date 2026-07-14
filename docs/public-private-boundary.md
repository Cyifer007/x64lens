# Public and Private Boundary

## Purpose

x64lens is intended to be a public research and engineering artifact. Public repository content must be useful to external readers without exposing private planning context, course logistics, unpublished coordination notes, or tool-assisted development session details.

## Public repository content

The public repository may include:

- source code,
- build scripts,
- test corpus source,
- benchmark scripts,
- public research methodology,
- public architecture documentation,
- CLI and JSON contracts,
- ethical use guidance,
- release notes,
- reproducibility instructions.

## Local-only private content

The following content belongs outside public commits:

- local project context files,
- private project state notes,
- private coordination notes,
- course assignment PDFs or DOCX files,
- unreleased personal planning notes,
- proprietary binaries,
- malware samples,
- private benchmark data,
- credentials, tokens, or secrets.

Use `.local/project-context/` for local-only context files. The repository `.gitignore` excludes `.local/`.

## Public archive enforcement

Public ZIPs are inspected before distribution:

```bash
make patch-bundle-hygiene-smoke
BUNDLE=/path/to/archive.zip make patch-bundle-hygiene
```

The archive policy is root-independent and metadata-only. It rejects unsafe or
non-portable paths, `.git`, `.local`, agent state, project-context files,
environment files other than `.env.example`, secrets, private/course material,
generated build/test/benchmark outputs, symbolic links, duplicate or case-
colliding members, and nested archives. This check is required even when the
source worktree is clean because the archive can contain members that do not
exist in Git.


## Local validation orchestration

Local validation missions, operational reports, raw command logs, temporary probes, and advisory notes are private coordination artifacts. They may inform public fixes, tests, and documentation, but their transcripts and session details should stay in ignored local-only directories. Public documents should summarize the technical behavior that was validated, not the private workflow used to validate it.

## Existing tracked files warning

Adding a path to `.gitignore` does not remove files that Git already tracks. If a private context file was already committed, remove it from tracking with `git rm --cached <path>` and commit that removal.

## Patch 043 transfer-artifact and ZIP metadata rule

Public documentation must not record timestamped private transfer-artifact
basenames or local transfer hashes as repository history. Repository-facing
validation records identify commits, public paths, reproducible commands, and
technical outcomes.

Public ZIP validation is metadata-first and non-extracting. It rejects raw and
effective name disagreement, traversal and cross-platform path ambiguity,
unsupported name/type extra fields, special files, encryption, comments, nested
containers, duplicates, case collisions, and private or generated paths under
any archive root. Explicit public samples such as `.env.example` remain narrow
allowances.

## Patch 044 local-header and synthetic-fixture rule

Public ZIP acceptance reconciles bounded local-file headers with central-
directory names, flags, compression, timestamps, checksums, sizes, and
recognized extra-field semantics. A clean central record cannot hide an unsafe
local name, encryption bit, Unicode override, or unsupported extra field.
Malformed or unnecessary ZIP64 metadata is rejected.

Public negative tests use synthetic timestamps, user names, hosts, and transfer
names. Tests must never preserve a real private attachment basename simply to
prove that the checker would reject it.

## Sprint 9 closeout boundary

Public closeout records describe architecture, contracts, reproducible commands, technical outcomes, known limitations, and future roadmap decisions. Local command transcripts, workstation-specific configuration, transfer filenames, private planning bundles, and platform-specific workflow notes remain outside the public tree.

Public smoke fixtures must use synthetic identifiers. A validator may be strengthened by locally observed evidence, but the committed regression must express the general policy rather than reconstructing a private basename or path.
