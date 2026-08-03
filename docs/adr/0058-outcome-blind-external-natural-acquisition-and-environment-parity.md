# ADR 0058: Outcome-Blind External-Natural Acquisition and Environment Parity

## Status

Accepted architecture for the Sprint 12 Patch 072 implementation candidate.
Patch 072 combines the smallest Patch 071 corrective prerequisite with the
planned external-natural acquisition and same-byte native/container private-fact
parity gate. Product acceptance remains subject to the documented native and
Docker checks.

## Context

Patch 071 corrected the first Patch 070 cleanup, batch, output-cap, and delivery
findings. Follow-up validation then identified narrower but material gaps in
the development evidence plane:

- cleanup could still delete a foreign replacement at the last pathname
  boundary, accept device/inode reuse after object recreation, exceed
  `NAME_MAX` when hostile component names were copied into quarantine names, or
  leak an ancestor descriptor on a failed identity check;
- the batch pilot stopped its timeout after the direct leader exited, did not
  account for detached adopted descendants, inferred signal publication only
  from final absence, and cleaned transaction roots by pathname;
- JSON authorities and delivery manifests accepted duplicate object keys; and
- the complete application delivery omitted loose artifacts named by its own
  records.

Those prerequisites concern tooling and delivery rather than runtime analyzer
changes. The freestanding assembly analyzer, loader and mitigation paths,
capacity and malformed-input paths, schema `0.2.0`, and controlled 96-object
fact plane were unchanged by Patches 071 and 072. External-natural acquisition
could proceed only after its custody and process prerequisites were corrected
in the same cohesive patch.

## Decision

### Generation-aware owned cleanup

The cleanup token is version 3. It binds the owned root to Linux `statx`
birth time and mount identity in addition to device and inode. A recreated
object that reuses an inode therefore does not satisfy the original token.
Quarantine names are fixed-length random names independent of the caller's
component length, so a legal long member does not become an overlong generated
name. Ancestor traversal closes every descriptor opened before a failed
identity comparison.

Each final removal reauthenticates the held descriptor against the quarantined
name immediately inside the low-level unlink boundary. Files, directories, and
the transaction root use the same rule. The helper still does not claim a
filesystem sandbox or an impossible unlink-by-descriptor primitive: a hostile
same-UID process that can predict a 128-bit final quarantine name and win the
remaining final check-to-syscall interval is outside the stated trust boundary.
Foreign replacements observed by the maintained adversarial regressions are
preserved and cause fail-closed cleanup.

### Outcome-complete batch authority version 3

The version-2 batch authority is retained as history and superseded for current
validation by `sprint12-batch-transaction-pilot-v3.json`. Version 3 contains 29
cases and 87 executions. It adds:

- an explicit authenticated `case_order` that is independent of JSON object-member order;
- a leader-exit case whose inherited pipe remains open past the deadline;
- a detached descendant case observed through subreaper adoption;
- explicit publication-transition counts;
- descendant reaping and failure accounting; and
- identity-bound cleanup for normal and signal transaction roots.

The runner continues reading and enforcing its deadline after the direct leader
exits. It terminates and reaps same-group children and adopted descendants.
Signal acceptance consumes an inotify-backed publication-transition record; final
path absence alone cannot hide publish-then-delete behavior. The observer records
both direct creation and rename-into-place transitions before cleanup may remove the
result.

### Strict JSON authority and delivery parsing

Batch authorities and recursive delivery manifests reject duplicate keys at
every JSON object depth. Delivery custody continues to require exact regular
file and implied-directory membership, path safety, size, mode, and SHA-256.
Duplicate `root_label` values are rejected rather than accepted by last-key
wins semantics. The Patch 072 application delivery must also contain every
loose artifact named by its delivery records.

### Outcome-blind external-natural acquisition

The external-natural authority freezes selection after package, path, mode, and
ELF eligibility checks and before any x64lens, private fact-probe, or GNU
`readelf` outcome is consumed. The installed-package stratum uses four distinct
dpkg source lineages:

```text
binutils
glibc
systemd
util-linux
```

Each lineage contributes exactly twelve unique ELF64 little-endian x86_64
objects selected by bytewise lexical absolute path: seven executable paths
under `/usr/bin` or `/usr/sbin`, and five non-symlink shared-library paths under
`/lib` or `/usr/lib`. No lineage exceeds 25 percent of the 48-object set.
Selection retains binary and source package versions, package file-list hashes,
copyright hashes, requested and resolved paths, modes, sizes, and SHA-256
identities. Targets are copied read-only and never executed.

Every selected object receives:

- an independent 18-field expected vector;
- three byte-identical private fact-probe executions;
- all four public command paths with private-vocabulary rejection and formal
  schema validation where a JSON report is produced; and
- authenticated GNU `readelf -hW`, `-lW`, `-dW`, and `-nW` evidence with one
  disposition for every object/field cell.

Object, process, run-field, and object-field denominators remain separate.
Ambiguous, unavailable, malformed, unsupported, and inapplicable outcomes are
retained rather than coerced into matches. In particular, GNU `readelf -nW`
collapses canonical physical carrier views and cannot serve as authority for
x64lens `property_view_count`; that field is explicitly unavailable for this
natural-package stratum.

### Same-byte native/container parity

Environment parity is separate from package source/build-origin effects. One
authenticated 96-object held-out matrix and byte-identical analyzer, private
fact probe, and schema inputs are mounted read-only into native and container
planes. Each plane retains:

```text
96 objects
288 private probe processes
5,184 private field cells
384 public command closures
```

The parity comparator requires 10,368 combined private field records, 5,184
paired field agreements, 576 combined probe processes, 288 byte-identical
paired probe-output agreements, 768 combined public closures, and 384 paired
public tuples. Public outputs are compared only after replacing the
environment-specific target pathname; raw outputs remain retained. Docker is
an environment stratum, not a compiler/build-origin stratum.

## Consequences

Patch 072 changes no runtime `src/`, `include/`, or schema file. It adds no new
role-derived PIE/DSO field or IBT/SHSTK field and does not reinterpret the
existing coarse `mitigations.pie` indicator. Static GNU-property facts do not
prove runtime CET enforcement. Program headers remain executable authority.
Candidate capacity remains 4,096, candidate 4,097 returns exit 6 before stdout,
malformed inputs emit no partial report, and the dependency-free decoder-free
one-worker reference remains unchanged.

The Sprint 12 sequence is:

- Patch 072: this corrective prerequisite, external-natural acquisition, and
  same-byte environment parity;
- Patch 073: non-reinterpretive public-policy decision; and
- Patch 074: Sprint 12 closeout and Sprint 13 handoff.

External-natural and parity artifacts remain diagnostic, unfrozen, and
publication-ineligible. They cannot be relabeled as Sprint 15-frozen evidence.
Positive coordinate anchors, whole-batch workload qualification, process-tree
RSS, and deployment-envelope observation remain separate gates.

## Rejected alternatives

- Deferring every Patch 071 correction and beginning natural acquisition on a
  known-weak evidence plane.
- Treating device/inode equality alone as a generation identity.
- Copying hostile component names into generated quarantine names.
- Ending timeout enforcement when the direct child exits while output pipes or
  adopted descendants remain live.
- Inferring no publication from final absence.
- Allowing duplicate JSON keys because a standard parser chooses one value.
- Selecting natural objects after viewing x64lens role or property outcomes.
- Treating `readelf`'s collapsed note presentation as physical carrier-view
  authority.
- Mixing environment parity with compiler, package, or build-origin effects.
- Publishing private fields before the separate Patch 073 policy gate.
