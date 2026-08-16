# Sprint 12 Patch 072 Validation

## Status

Historical implementation candidate. Its returned review rejected acceptance
after reproducing custody and isolation defects. Patch 073 delivered the first
custody/isolation correction and policy deferral but was not accepted at its
first returned review boundary. Patch 074 was a superseded Sprint 12 closeout
candidate. Patch 075 introduced bounded private static text-relocation evidence,
and Patch 076 implemented distinct private `DT_RPATH` and `DT_RUNPATH`
carrier/value evidence. Patch 076 was superseded by Patch 077. Patch 077's
review required Patch 078, whose review required the Patch 079 corrective and private task-value candidate, which was superseded by Patch 080. Current validation expectations are
in the [Patch 088 validation record](sprint-13-patch-088-validation.md).
Patch 072 addressed the remaining confirmed Patch 071 tooling and
delivery prerequisites and implemented the planned outcome-blind
external-natural acquisition plus same-byte environment-parity gate. It changes
no runtime assembly, include, or JSON schema file.

Retained diagnostic evidence completed the external-natural acquisition but did
not include a fresh native runtime build. Retained same-host parity evidence is
logic-only, not native/container parity. Corrected native/container parity and
complete Patch 089 acceptance remain pending.

## Source precondition

Patch 072 applies to the exact committed Patch 071 source:

```text
HEAD:   d1c1f910e9bc925e01467e1449e65a2d36ad6f0f
parent: ac26a3c39923f05cbfc14bcb332ad5952174fbaa
base tree: 73e54da25224f991178ec7b3083cf465eb1bd362
```

The worktree and index must be clean before application.

## Corrective behavior

- Owned-root tokens use version-3 device, inode, `statx` birth-time, and mount
  identity.
- Fixed-length random quarantine names do not inherit hostile component length.
- Ancestor identity failures close newly opened descriptors.
- Final file, directory, and root removals reauthenticate the held object inside
  the low-level unlink boundary.
- Batch authority version 3 contains 29 cases and 87 executions, including
  leader-exit/inherited-pipe and detached-descendant cases.
- Deadline enforcement continues after direct-leader exit while output or
  adopted descendants remain live.
- Normal and signal transaction roots use identity-bound cleanup.
- Signal publication acceptance consumes an inotify-backed transition record.
- Batch execution follows explicit authenticated `case_order`; JSON object-member order is non-semantic.
- Batch and delivery JSON reject duplicate keys recursively.
- Recursive delivery custody rejects duplicate `root_label` and retains exact
  membership, hash, size, and mode checks.

Focused corrective validation:

```bash
make script-perms-check
make scaffold-check
make sprint12-batch-transaction-smoke
make patch071-corrective-regression-smoke
git diff --check
```

Expected banners:

```text
sprint12-batch-transaction-smoke: ok cases=29 executions=87 stable_hashes=87 successful_batches=3 failed_batches=18 failure_index_0=10 failure_index_1=4 failure_index_2=4 process_tree_cases=2 descendant_failures=1 signals=8 stage_residue=0 survivors=0 fd_growth=0 timing_claims=0

patch071-corrective-regression-smoke: ok cleanup_long_name=1 final_file=1 final_directory=1 final_root=1 generation_identity=1 ancestor_fd=1 duplicate_json=2 case_order=1 leader_exit_deadline=1 detached_descendant=1 normal_root_cas=1 signal_root_cas=1 publication_transition=1 custody_duplicate=1
```

## External-natural acquisition

The host must provide GNU `readelf`, `dpkg-query`, the development toolchain,
and the exact installed source lineages named by the authority.

```bash
make sprint12-external-natural-acquisition-smoke
```

The gate freezes selection after package, path, mode, and ELF eligibility checks
and before any x64lens, private fact-probe, or GNU `readelf` outcome is consumed.
It then requires:

```text
4 source lineages
12 objects per lineage
28 executable-path objects
20 shared-library-path objects
144 private probe processes
2,592 private run-field records
864 object-field summaries
192 public commands
192 readelf processes
864 readelf field dispositions
0 eligible readelf mismatches
```

The exact `match`, `ambiguous`, `unavailable`, `not_eligible`, and public exit
counts are observed results, not a selection criterion. Capacity exit 6 remains
a valid retained public-command outcome only when stdout is empty and the stable
fail-closed contract is preserved.

A retained diagnostic acquisition completed the intended denominators over four
installed lineages. It retained 624 eligible matches, 48 ambiguous
cells, 192 unavailable cells, and zero eligible mismatches. Forty-six `gadgets`
and `analyze` pairs succeeded; two pairs returned capacity exit 6 with empty
stdout. Both `ibt_state` and `shstk_state` remained unknown for every selected
object, or 96 object-field cells. The evidence is diagnostic, unfrozen, and
publication-ineligible; these observations are not prevalence or runtime-CET
claims.

## Native/container same-byte parity

```bash
make sprint12-role-property-environment-parity-smoke
```

The target mounts one held-out matrix and the same analyzer, probe, and schema
bytes into both planes. Acceptance requires:

```text
96 objects
5,184 private fields per environment
10,368 combined private fields
5,184 paired private-field agreements
288 private probe processes per environment
576 combined private probe processes
288 paired byte-identical probe-output agreements
768 combined public command closures
384 paired path-normalized public tuples
0 mismatches
```

Retained evidence includes two same-host logic planes that completed these
denominators. That evidence is diagnostic, unfrozen, publication-ineligible,
and logic-only; qualified native/container parity remains required.

## Complete Patch 072 acceptance

```bash
make clean
make
make samples
MALFORMED_TIMEOUT=2 make validation-smoke
SHELLCHECK_STRICT=1 make shellcheck-smoke
make sprint-closeout-smoke
make docker-build
make docker-test
MALFORMED_TIMEOUT=2 make docker-validation-smoke
make sprint12-p072-acceptance-smoke
```

`make sprint12-p072-acceptance-smoke` deliberately keeps package-specific
external acquisition and Docker parity outside the portable native aggregate.
It runs the normal aggregate first, then both Patch 072 acquisition and
environment-parity gates.

## Unchanged product contracts

- tool version `0.1.0-dev`;
- JSON schema `0.2.0`;
- program-header and file-backed `PT_LOAD + PF_X` executable authority;
- separate scanner, matcher, classifier, provenance/effect side-cars, scorer,
  and reporters;
- distinct raw, exact-suffix, semantic-exact, unknown, future decoder-backed,
  and scored facts;
- candidate capacity 4,096 and candidate-4,097 exit 6 before stdout;
- malformed-input no-partial-output behavior;
- read-only targets and no target execution;
- dependency-free, decoder-free, one-worker reference runtime; and
- no new role-derived PIE/DSO field or IBT/SHSTK field; the existing coarse
  `mitigations.pie` field remains unchanged.

## Interpretation and next gate

The Patch 072 gates were intended to support a bounded claim that the maintained
private fact plane agrees with independent vectors and eligible GNU `readelf`
evidence on the selected natural package stratum. Retained same-host logic-only
evidence did not establish actual native/container parity. Neither evidence
class proves runtime CET enforcement, representativeness, mitigation prevalence,
complete loader semantics, publication readiness, or exploitability.

Patch 073 executed the non-reinterpretive public-policy gate as `defer`; it
added no public field and preserved the existing coarse `mitigations.pie`
meaning. Corrected native/container parity and independent acceptance remain
pending. Any future compatible `0.2.x` indicator requires a new separately
reviewed decision. Patch 074 was a superseded Sprint 12 closeout candidate.
Patch 075 introduced private static text-relocation evidence, but its review
required the Patch 076 correction. Patch 076 implemented distinct private
RPATH/RUNPATH evidence, but its review required Patch 077. Patch 077 was a
reconciliation candidate. Patch 078 corrected its remaining blockers, but its
review required the Patch 079 corrective and private task-value candidate, whose
review required Patch 080, which was superseded by Patch 081. Patch 081 was not
accepted; complete Patch 089 acceptance remains pending, so Sprint 12 remains open.
