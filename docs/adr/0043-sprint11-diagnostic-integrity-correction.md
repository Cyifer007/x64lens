# ADR 0043: Sprint 11 Diagnostic Integrity Correction

## Status

Implemented in Sprint 11 Patch 057 and subsequently strengthened by Patch 058
where later validation found additional evidence-integrity gaps.

## Context

Patch 055 established the diagnostic runner and Patch 056 added deterministic
corpus regeneration. Post-patch validation then demonstrated four defects in
that development evidence boundary:

1. a measured process could temporarily add execute mode to the supposedly
   non-executable target memfd and execute it directly;
2. corpus cleanup used an unbounded caller-selected recursive deletion path and
   was not phony;
3. undeclared compiler files could enter the checksummed published corpus; and
4. staging creation and best-effort cleanup could leave residue while hiding the
   cleanup failure.

The non-root corpus oracle also attempted to rewrite a retained mode-`0444`
checksum file without first making its copied fixture writable. These defects do
not change analyzer output, but they make diagnostic evidence untrustworthy and
therefore block baseline expansion.

## Decision

Patch 057 corrects the evidence infrastructure before adding another measured
condition.

### Execution input classes

The runner preserves two distinct immutable execution-input classes:

```text
tool and timer probe  executable write-sealed Linux memfd
target under analysis non-executable Linux memfd with an execution seal
```

Target creation requires `MFD_NOEXEC_SEAL`. The observed seal set must contain
`F_SEAL_EXEC` together with the seal, shrink, grow, and write seals. A host that
cannot provide this kernel contract fails the runner platform prerequisite; the
runner does not fall back to mode `0444` alone.

This is an object-level guarantee. It prevents a measured command from adding
execute permission to or directly executing the passed target memfd. It is not
a sandbox guarantee against a hostile tool copying the bytes to another object.
Baseline tools remain trusted measurement participants.

### Transaction and cleanup

Runner and corpus staging directories are created inside the protected
transaction. Failure cleanup:

- operates only on the exact same-parent staging directory;
- traverses through directory file descriptors;
- rejects changed directory identity and filesystem-boundary changes;
- does not follow symlinks;
- repairs restrictive directory modes needed for removal;
- verifies that the complete staging tree disappeared; and
- reports cleanup failure together with the originating failure.

### Corpus workspace and membership

Tool metadata commands use one otherwise-empty `command-workdir` and must leave
it empty. Each compiler command may leave only its one named regular output.
That output must satisfy the configured size limit before it is moved into the
retained target directory. Undeclared files, directories, links, devices, or
additional outputs reject the transaction.

Both construction and later verification reconstruct the exact expected file
and directory set. A checksum does not authorize an undeclared member.

### Safe explicit removal

`clean-provisional-corpus` is phony and delegates to the corpus builder. The
builder derives the only removable path from the validated specification's
`corpus_id` and the configured output root, requires a complete corpus verification with diagnostic, unfrozen, non-public
identity, removes through checked traversal, and
leaves unrelated siblings untouched. The Make recipe contains no recursive
shell deletion.

### Oracle parity

Checksum-regeneration tests make their copied checksum fixture writable only
for regeneration and restore mode `0444` afterward. The smoke therefore runs
under the same non-root permissions used by the container validation path.

## Architecture boundary

Patch 057 changes no analyzer assembly, CLI command, schema field, candidate
metric, semantic class, score, record size, arena size, decoder policy, or
worker policy. Program headers remain executable mapping authority. The
reference runtime remains dependency-free, decoder-free, one-worker, bounded,
and deterministic.

## Consequences

### Positive

- The passed target object cannot be made executable transiently.
- Published corpus membership is closed and reproducible.
- Failure paths cannot silently retain staging state.
- Overriding `PROVISIONAL_CORPUS_PATH` cannot redirect cleanup; the builder
  derives the removable member from the configured output root and validated
  `corpus_id`.
- Native and non-root container corpus oracles use the same permission model.

### Costs and limitations

- The diagnostic runner now requires Linux support for
  `MFD_NOEXEC_SEAL`/`F_SEAL_EXEC`.
- The runner still does not adversarially sandbox a measured tool.
- Compiler processes are trusted development inputs; exact workspace closure
  prevents undeclared retention but is not a filesystem quota system.
- Existing diagnostic rows from the weaker method remain development history
  and cannot be promoted.

## Rejected alternatives

- **Keep mode `0444` and recheck afterward:** rejected because a process can add
  execute mode, run the target, and restore the original state between checks.
- **Ignore cleanup errors:** rejected because absence of final publication does
  not make leaked staging state acceptable.
- **Trust every checksummed regular file:** rejected because compiler side
  effects are not declared corpus members.
- **Retain raw `rm -rf` with a path guard in Make:** rejected because the corpus
  builder already owns the identity and manifest needed for safe removal.
- **Proceed directly to baseline adapters:** rejected because measuring more
  tools on an unsound evidence foundation compounds rather than resolves the
  defect.
