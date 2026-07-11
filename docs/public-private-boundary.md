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
